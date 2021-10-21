import datetime
import re
import csv
import sys
import os

from collections import OrderedDict

p = re.compile(r'\[\w+\]')
q = re.compile(r'\w+\d=FAIL')

# START_TIME = "2019-04-23 15:16:46.2775"
# END_TIME = "2019-04-23 16:22:07.5131"
START_TIME = ""
END_TIME = ""


def main(path: str):
    global parsed_temp, errors_parsed, resistance_values, time_diff_mins, log_start_time, log_end_time, new_counts
    with open(path) as f:
        lines = f.readlines()
    try:
        parsed_temp, errors_parsed, resistance_values, time_diff_mins, log_start_time, log_end_time, new_counts = \
            parse_log(lines)
        gettime(parsed_temp, log_start_time, log_end_time, new_counts)
        return parsed_temp, errors_parsed, resistance_values, time_diff_mins, log_start_time, log_end_time, new_counts
    except TypeError:
        print('Skip File:', f'{path}')


RUNNING_STATUS = "Running"
STOPPING_STATUS = "Stopped"


def get_timedelta(log_time_obj):
    date_time_delta = datetime.timedelta(
        seconds=log_time_obj.hour * 60 * 60 + log_time_obj.minute * 60 + log_time_obj.second,
        microseconds=log_time_obj.microsecond)
    return date_time_delta


def get_date_time_obj(datetime_str):
    global datetime_obj
    try:
        datetime_obj = datetime.datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S.%f')
    except Exception as e:
        print(e)
        pass
    return datetime_obj


def categorize_time(up_time, time_00, time_02_03, time_above_03):
    total_minutes = up_time.total_seconds() / 60
    if total_minutes < 1:
        time_00 += 1
    elif 1 <= total_minutes <= 3:
        time_02_03 += 1
    elif total_minutes > 3:
        time_above_03 += 1
    return time_00, time_02_03, time_above_03


def counter(log_obj, search_key, current_count):
    if search_key in log_obj:
        current_count += 1
    return current_count


def division_handler(numerator, denominator):
    try:
        return numerator / denominator
    except ZeroDivisionError:
        return 0


def gettime(temp, log_start_time, log_end_time, new_counts):
    previous_state = STOPPING_STATUS
    session_flag = False
    session_up_time = []
    Up_time_session = datetime.timedelta(seconds=0)
    longest_up_time = datetime.timedelta(seconds=0)
    Up_time = datetime.timedelta(seconds=0)
    total_down_time = datetime.timedelta(seconds=0)
    error_log_list = []
    errors = []
    time_00 = 0
    time_02_03 = 0
    time_above_03 = 0
    assist_count = 0
    k = ""
    for i in temp:
        if i['log_status'] == RUNNING_STATUS:
            if previous_state == RUNNING_STATUS:
                Up_time = Up_time + (
                        get_timedelta(i['date_time_obj']) - get_timedelta(previous_running_time))
                Up_time_session = Up_time_session + (
                        get_timedelta(i['date_time_obj']) - get_timedelta(previous_running_time))
            elif previous_state == STOPPING_STATUS and session_flag:
                down_time = (get_timedelta(i['date_time_obj']) - get_timedelta(k)) - Up_time_session
                total_down_time += down_time
                session_up_time.append({"up": "", "down": down_time,
                                        "error_log_list": error_log_list, "start_time": k + Up_time_session,
                                        "end_time": i['date_time_obj'], "errors": ",".join(errors),
                                        "error_logs": error_log_list})
                assist_count += 1
                errors = []
                error_log_list = []
                Up_time_session = datetime.timedelta(seconds=0)
                k = i['date_time_obj']
            else:
                session_flag = True

            previous_state = RUNNING_STATUS
            previous_running_time = i['date_time_obj']
            if not k:
                k = i['date_time_obj']
        elif i['log_status'] == STOPPING_STATUS and previous_state == RUNNING_STATUS and session_flag:
            previous_state = STOPPING_STATUS
            if i.get('Error_Log'):
                for n in i['Error_Log']:
                    error_log_list.append(n)
            if i.get('errors'):
                errors.append(i.get('errors'))
            Up_time = Up_time + (get_timedelta(i['date_time_obj']) - get_timedelta(previous_running_time))
            Up_time_session = Up_time_session + (get_timedelta(i['date_time_obj']) - get_timedelta(
                previous_running_time))
            session_up_time.append({"up": Up_time_session, "down": "", "error_log_list": error_log_list,
                                    "start_time": k, "end_time": i['date_time_obj'], "errors": "",
                                    "error_logs": error_log_list})
            if Up_time_session > longest_up_time:
                longest_up_time = Up_time_session
            time_00, time_02_03, time_above_03 = categorize_time(Up_time_session, time_00, time_02_03,
                                                                 time_above_03)
        elif i['log_status'] == STOPPING_STATUS and previous_state == STOPPING_STATUS and session_flag:
            if i.get('Error_Log'):
                for n in i['Error_Log']:
                    error_log_list.append(n)
            if i.get('errors'):
                errors.append(i.get('errors'))
    new_counts["Start"] = log_start_time
    new_counts["End"] = log_end_time
    new_counts["Assist"] = assist_count
    new_counts["DT"] = str(datetime.timedelta(seconds=total_down_time.total_seconds()))
    new_counts["Run Time"] = str(datetime.timedelta(seconds=Up_time.total_seconds()))
    total_down_time_mins = 0
    total_up_time_mins = round(float(Up_time.total_seconds()) / 60, 2)
    try:
        down_time_list = [x["down"] for x in session_up_time if x["down"]]
        total_down_time_mins = round(float(sum(down_time_list, datetime.timedelta(0)).total_seconds()) / 60, 2)
        mtbf = division_handler(sum(down_time_list, datetime.timedelta(0)), len(down_time_list))
    except:
        pass


def parse_log(read_lines):
    machine_start_message = 'INFO Machine status changed to Running'
    errors_parsed = []
    parsed_temp = []

    infeed_pick1_ok = 0
    infeed_pick2_ok = 0
    infeed_pick3_ok = 0
    infeed_pick4_ok = 0
    infeed_place1_ok = 0
    infeed_place2_ok = 0
    infeed_place3_ok = 0
    infeed_place4_ok = 0
    infeed_reject1_ok = 0
    infeed_reject2_ok = 0
    infeed_reject3_ok = 0
    infeed_reject4_ok = 0
    infeed_pick1_error = 0
    infeed_pick2_error = 0
    infeed_pick3_error = 0
    infeed_pick4_error = 0
    infeed_place1_error = 0
    infeed_place2_error = 0
    infeed_place3_error = 0
    infeed_place4_error = 0

    log_start_time = ""
    log_end_obj = read_lines[-1]
    resistance_values = list()
    for i in read_lines:
        splitted_values = i.split(" ")
        updated_date_time = get_date_time_obj(i[:23])
        errors_parsed.extend([{"date_time_obj": updated_date_time, "error": value.strip(",")}
                              for value in splitted_values if ("[E" in value) or ("=FAIL" in value)])
        if (START_TIME and get_date_time_obj(i[:23]) <= get_date_time_obj(START_TIME)) or (
                END_TIME and get_date_time_obj(i[:23]) >= get_date_time_obj(END_TIME)):
            continue

        infeed_pick1_ok = counter(i, "InfeedPick=1[Ok]", infeed_pick1_ok)
        infeed_pick2_ok = counter(i, "InfeedPick=2[Ok]", infeed_pick2_ok)
        infeed_pick3_ok = counter(i, "InfeedPick=3[Ok]", infeed_pick3_ok)
        infeed_pick4_ok = counter(i, "InfeedPick=4[Ok]", infeed_pick4_ok)
        infeed_place1_ok = counter(i, "InfeedPlace=1[Ok]", infeed_place1_ok)
        infeed_place2_ok = counter(i, "InfeedPlace=2[Ok]", infeed_place2_ok)
        infeed_place3_ok = counter(i, "InfeedPlace=3[Ok]", infeed_place3_ok)
        infeed_place4_ok = counter(i, "InfeedPlace=4[Ok]", infeed_place4_ok)
        infeed_reject1_ok = counter(i, "InfeedReject=1[Ok]", infeed_reject1_ok)
        infeed_reject2_ok = counter(i, "InfeedReject=2[Ok]", infeed_reject2_ok)
        infeed_reject3_ok = counter(i, "InfeedReject=3[Ok]", infeed_reject3_ok)
        infeed_reject4_ok = counter(i, "InfeedReject=4[Ok]", infeed_reject4_ok)
        infeed_pick1_error = counter(i, "InfeedPick=1[E", infeed_pick1_error)
        infeed_pick2_error = counter(i, "InfeedPick=2[E", infeed_pick2_error)
        infeed_pick3_error = counter(i, "InfeedPick=3[E", infeed_pick3_error)
        infeed_pick4_error = counter(i, "InfeedPick=4[E", infeed_pick4_error)
        infeed_place1_error = counter(i, "InfeedPlace=1[E", infeed_place1_error)
        infeed_place2_error = counter(i, "InfeedPlace=2[E", infeed_place2_error)
        infeed_place3_error = counter(i, "InfeedPlace=3[E", infeed_place3_error)
        infeed_place4_error = counter(i, "InfeedPlace=4[E", infeed_place4_error)

        if (" EContact1=" in i) or (" EContact2=" in i):
            continue
        log_end_obj = i
        if "Ohm=" in i:
            ohm_value = (i.split("Ohm=")[1]).strip("\n")
            resistance_values.append({"timestamp": get_date_time_obj(i[:24]), "resistance": ohm_value})
        if machine_start_message in i:
            parsed_temp.append(
                {"date_time_obj": get_date_time_obj(i[:23]),
                 "log_status": RUNNING_STATUS})
            if not log_start_time:
                log_start_time = get_date_time_obj(i[:23])
        try:
            if i[24] == 'E' and i[30] != "O":
                date_time_obj = get_date_time_obj(i[:23])
                if i[30] == "[":
                    errors = i[37:]
                else:
                    errors = i[30:]
                errors = errors.split("\n")[0]
                parsed_temp.append(
                    {"date_time_obj": date_time_obj,
                     "log_status": STOPPING_STATUS, "errors": errors})
            elif "INFO Machine status changed to Paused." in i:
                date_time_obj = get_date_time_obj(i[:23])
                parsed_temp.append(
                    {"date_time_obj": date_time_obj,
                     "log_status": STOPPING_STATUS, "errors": "Machine status changed to Paused."})
            elif "INFO Machine status changed to Stop." in i:
                date_time_obj = get_date_time_obj(i[:23])
                parsed_temp.append(
                    {"date_time_obj": date_time_obj,
                     "log_status": STOPPING_STATUS, "errors": "Machine status changed to Stop."})
            elif "INFO Machine status changed to IdleDown." in i:
                date_time_obj = get_date_time_obj(i[:23])
                parsed_temp.append(
                    {"date_time_obj": date_time_obj,
                     "log_status": STOPPING_STATUS, "errors": "Machine status changed to IdleDown."})

        except IndexError:
            pass
    try:
        if not log_start_time:
            raise Exception("Invalid start time/end time")
        print(f'{os.path.basename(__file__)} log_start_time', log_start_time)
        log_end_time = get_date_time_obj(log_end_obj[:23])
        time_diff = log_end_time - log_start_time
        hours = (time_diff.total_seconds()) / 60 / 60
        time_diff_mins = round((time_diff.total_seconds()) / 60, 2)
    except Exception as e:
        print(e)
        pass

    new_counts = OrderedDict(
        [("Start", 0), ("End", 0), ("Output", infeed_pick1_ok + infeed_pick2_ok + infeed_pick3_ok + infeed_pick4_ok),
         # incoming parts
         ("Pass", infeed_place1_ok + infeed_place2_ok + infeed_place3_ok + infeed_place4_ok),
         # successful placement on accumulator
         ("Fail", infeed_place1_error + infeed_place2_error + infeed_place3_error + infeed_place4_error),
         # total rejects
         ("DT", 0), ("Run Time", 0), ("Assist", 0),
         ("CSA Toss", infeed_pick1_error + infeed_pick2_error + infeed_pick3_error + infeed_pick4_error),
         # pick failures
         ("CSA Pass", infeed_pick1_ok + infeed_pick2_ok + infeed_pick3_ok + infeed_pick4_ok),
         ])

    try:
        return parsed_temp, \
               errors_parsed, resistance_values, time_diff_mins, \
               log_start_time, log_end_time, new_counts
    except UnboundLocalError:
        pass

# if __name__ == '__main__':
#     main(path='/Users/justinclay/Downloads/AKB Log files/AKB M4/2021-10-11_History.log')
