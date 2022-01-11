# /usr/local/bin python3
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
        parsed_temp, errors_parsed, resistance_values, time_diff_mins, log_start_time, log_end_time, new_counts = parse_log(
            lines)
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
    resistance_csv_data = [["Timestamp", "Resistance(ohm)"]]


def parse_log(read_lines):
    machine_start_message = 'INFO Machine status changed to Running'
    errors_parsed = []
    parsed_temp = []
    infeed_pick_ok = 0
    infeed_place_ok = 0
    infeed_reject_ok = 0
    wick1_pick_ok = 0
    wick1_pick_error = 0
    wick2_pick_ok = 0
    wick2_pick_error = 0
    wick_place_ok = 0
    wick_place_error = 0
    wick_reject = 0
    wick_transfer_pick_ok = 0
    wick_transfer_pick_error = 0
    wick_transfer_place_ok = 0
    wick_transfer_place_error = 0
    wick_transfer_reject = 0
    wick_transfer_vision_ok = 0
    wick_transfer_vision_fail = 0
    wick_insert_ok = 0
    wick_insert_error = 0
    fg_vision1_ok = 0
    fg_vision1_fail = 0
    fg_vision2_ok = 0
    fg_vision2_fail = 0
    transfer_pick_ok = 0
    transfer_place_ok = 0
    transfer_reject_ok = 0
    invert_ok = 0
    invert_error = 0
    invert_vision_ok = 0
    invert_vision_fail = 0
    outfeed_pick_ok = 0
    outfeed_place_ok = 0
    outfeed_reject_ok = 0
    log_start_time = ''
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
        infeed_pick_ok = counter(i, "InfeedPick=1[Ok]", infeed_pick_ok)
        infeed_place_ok = counter(i, "InfeedPlace=1[Ok]", infeed_place_ok)
        infeed_reject_ok = counter(i, "InfeedReject=1[Ok]", wick1_pick_ok)
        wick1_pick_ok = counter(i, "Wick1Pick=1[Ok]", wick1_pick_ok)
        wick1_pick_error = counter(i, "Wick1Pick=1[E", wick1_pick_error)
        wick2_pick_ok = counter(i, "Wick2Pick=1[Ok]", wick2_pick_ok)
        wick2_pick_error = counter(i, "Wick2Pick=1[E", wick2_pick_error)
        wick_place_ok = counter(i, "WickPlace=1[Ok]", wick_place_ok)
        wick_place_error = counter(i, "WickPlace=1[E", wick_place_error)
        wick_reject = counter(i, "WickReject=1[Ok]", wick_reject)
        wick_transfer_pick_ok = counter(i, "Insert1Pick=1[Ok]", wick_transfer_pick_ok)
        wick_transfer_pick_error = counter(i, "Insert1Pick=1[E", wick_transfer_pick_error)
        wick_transfer_place_ok = counter(i, "Insert1Place=1[Ok]", wick_transfer_place_ok)
        wick_transfer_place_error = counter(i, "Insert1Place=1[E", wick_transfer_place_error)
        wick_transfer_reject = counter(i, "Insert1Reject=1[Ok]", wick_transfer_reject)
        wick_transfer_vision_ok = counter(i, "Camera1=PASS", wick_transfer_vision_ok)
        wick_transfer_vision_fail = counter(i, "Camera1=FAIL", wick_transfer_vision_fail)
        wick_insert_ok = counter(i, "WickPress=1[Ok]", wick_insert_ok)
        wick_insert_error = counter(i, "WickPress=1[E", wick_insert_error)
        fg_vision1_ok = counter(i, "Camera2=PASS", fg_vision1_ok)
        fg_vision1_fail = counter(i, "Camera2=FAIL", fg_vision1_fail)
        fg_vision2_ok = counter(i, "Camera3=PASS", fg_vision2_ok)
        fg_vision2_fail = counter(i, "Camera3=FAIL", fg_vision2_fail)
        transfer_pick_ok = counter(i, "TransferPick=1[Ok]", transfer_pick_ok)
        transfer_place_ok = counter(i, "TransferPlace=1[Ok]", transfer_place_ok)
        transfer_reject_ok = counter(i, "TransferReject =1[Ok]", transfer_reject_ok)
        invert_ok = counter(i, "InvertZUpDown=1[Ok]", invert_ok)
        invert_error = counter(i, "InvertZUpDown=1[E", invert_error)
        invert_vision_ok = counter(i, "Camera4=PASS", invert_vision_ok)
        invert_vision_fail = counter(i, "Camera4=FAIL", invert_vision_fail)
        outfeed_pick_ok = counter(i, "OutfeedPick=1[Ok]", outfeed_pick_ok)
        outfeed_place_ok = counter(i, "OutfeedPlace=1[Ok]", outfeed_place_ok)
        outfeed_reject_ok = counter(i, "OutfeedReject=1[Ok]", outfeed_reject_ok)

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
                # print('P1 - No Start Time: ', log_start_time)

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
            elif "INFO Machine status changed to Paused" in i:
                date_time_obj = get_date_time_obj(i[:23])
                parsed_temp.append(
                    {"date_time_obj": date_time_obj,
                     "log_status": STOPPING_STATUS, "errors": "Machine status changed to Paused"})
            elif "INFO Machine status changed to Stop" in i:
                date_time_obj = get_date_time_obj(i[:23])
                parsed_temp.append(
                    {"date_time_obj": date_time_obj,
                     "log_status": STOPPING_STATUS, "errors": "Machine status changed to Stop"})
        except IndexError:
            pass

    if not log_start_time:
        raise Exception("Invalid start time/end time")
    print(f'{os.path.basename(__file__)} log_start_time', log_start_time)
    log_end_time = get_date_time_obj(log_end_obj[:23])
    time_diff = log_end_time - log_start_time
    hours = (time_diff.total_seconds()) / 60 / 60
    time_diff_mins = round((time_diff.total_seconds()) / 60, 2)

    new_counts = OrderedDict(
        [("Start", 0), ("End", 0), ("Output", fg_vision1_ok + fg_vision1_fail),  # incoming parts for vision inspection
         ("Pass", invert_vision_ok),  # output at final inspection 2
         ("Fail", fg_vision1_fail + fg_vision2_fail + invert_vision_fail + (
                 fg_vision2_ok - invert_vision_fail - invert_vision_ok)),
         ("DT", 0), ("Run Time", 0), ("Assist", 0),
         ("Stn5 Fail", infeed_pick_ok - infeed_place_ok),
         ("Stn6D Fail", wick_transfer_vision_fail),
         ("Stn6 Fail", wick_insert_error),
         ("Stn7_1 Fail", fg_vision1_fail),
         ("Stn7_2 Fail", fg_vision2_fail),
         ("Stn8 Fail", fg_vision2_ok - invert_vision_fail - invert_vision_ok),
         ("Stn9 Fail", invert_vision_fail),
         ("Stn10 Fail", outfeed_pick_ok - outfeed_place_ok),
         ("Stn5 Pass", infeed_place_ok),
         ("Stn6 Pass", wick_insert_ok),
         ("Stn6D Pass", wick_transfer_vision_ok),
         ("Stn7_1 Pass", fg_vision1_ok),
         ("Stn7_2 Pass", fg_vision2_ok),
         ("Stn8 Pass", invert_vision_ok + invert_vision_fail),
         ("Stn9 Pass", invert_vision_ok),
         ("Stn10 Pass", outfeed_place_ok),
         ("Wick1 Toss", wick1_pick_error),
         ("Wick2 Toss", wick2_pick_error),
         ("Total Wick Toss", wick2_pick_error + wick1_pick_error + wick_transfer_vision_fail),
         ("HSA Toss", infeed_pick_ok - infeed_place_ok),
         ("Wick1 Pass", wick1_pick_ok),
         ("Wick2 Pass", wick2_pick_ok),
         ("Total Wick Pass", wick_transfer_place_ok),
         ("HSA Pass", infeed_place_ok),
         ])

    return parsed_temp, errors_parsed, resistance_values, time_diff_mins, log_start_time, log_end_time, new_counts


# if __name__ == '__main__':
#     main('/Users/justinclay/Downloads/AKB Log files/AKB M2/2021-10-11_History.log')
