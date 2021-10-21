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
    global session_up_time
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
    # new_counts["Start"] = f'{log_start_time.hour}:{log_start_time.minute}:{log_start_time.second}'
    # new_counts["End"] = f'{log_end_time.hour}:{log_end_time.minute}:{log_end_time.second}'
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
    except Exception as e:
        print(e)


def parse_log(read_lines):
    machine_start_message = 'INFO Machine status changed to Running'
    errors_parsed = []
    parsed_temp = []
    ah_infeed_pick_ok = 0
    ah_infeed_place_ok = 0
    ah_infeed_reject_ok = 0
    heater1_punch_ok = 0
    heater1_punch_error = 0
    heater2_punch_ok = 0
    heater2_punch_error = 0
    heater1_pick_ok = 0
    heater1_reject_ok = 0
    heater1_place_ok = 0
    heater2_pick_ok = 0
    heater2_reject_ok = 0
    heater2_place_ok = 0
    ah_outfeed_pick_ok = 0
    ah_outfeed_place_ok = 0
    ah_outfeed_reject_ok = 0
    ah_vision_ok = 0
    ah_vision_fail = 0
    heater1_vision_ok = 0
    heater1_vision_fail = 0
    heater2_vision_ok = 0
    heater2_vision_fail = 0
    heater_turret_vision_ok = 0
    heater_turret_vision_fail = 0
    heater_spread_vision_ok = 0
    heater_spread_vision_fail = 0
    heater_insert_ok = 0
    heater_insert_error = 0
    fg_vision1_ok = 0
    fg_vision1_fail = 0
    fg_vision2_ok = 0
    fg_vision2_fail = 0

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

        ah_infeed_pick_ok = counter(i, "TransferPick=1[Ok]", ah_infeed_pick_ok)
        ah_infeed_place_ok = counter(i, "TransferPlace=1[Ok]", ah_infeed_place_ok)
        ah_infeed_reject_ok = counter(i, "TransferReject=1[Ok]", ah_infeed_reject_ok)
        heater1_punch_ok = counter(i, "Reel1PunchandPick=1[Ok]", ah_infeed_place_ok)
        heater1_punch_error = counter(i, "Reel1PunchandPick=1[E", ah_infeed_pick_ok)
        heater2_punch_ok = counter(i, "Reel2PunchandPick=1[Ok]", heater1_punch_error)
        heater2_punch_error = counter(i, "Reel2PunchandPick=1[E", heater2_punch_error)
        heater1_pick_ok = counter(i, "Insert1Pick=1[Ok]", heater1_pick_ok)
        heater1_reject_ok = counter(i, "Insert1Reject=1[Ok]", heater1_reject_ok)
        heater1_place_ok = counter(i, "Insert1Place=1[Ok]", heater1_place_ok)
        heater2_pick_ok = counter(i, "Insert2Pick=1[Ok]", heater2_pick_ok)
        heater2_reject_ok = counter(i, "Insert2Reject=1[Ok]", heater2_reject_ok)
        heater2_place_ok = counter(i, "Insert2Place=1[Ok]", heater2_place_ok)
        ah_outfeed_pick_ok = counter(i, "OutfeedPick=1[Ok]", ah_outfeed_pick_ok)
        ah_outfeed_place_ok = counter(i, "OutfeedPlace=1[Ok]", ah_outfeed_place_ok)
        ah_outfeed_reject_ok = counter(i, "OutfeedReject=1[Ok]", ah_outfeed_reject_ok)
        ah_vision_ok = counter(i, "Camera1=PASS", ah_vision_ok)
        ah_vision_fail = counter(i, "Camera1=FAIL", ah_vision_fail)
        heater1_vision_ok = counter(i, "Camera2=PASS", heater1_vision_ok)
        heater1_vision_fail = counter(i, "Camera2=FAIL", heater1_vision_fail)
        heater2_vision_ok = counter(i, "Camera3=PASS", heater2_vision_ok)
        heater2_vision_fail = counter(i, "Camera3=FAIL", heater2_vision_fail)
        heater_turret_vision_ok = counter(i, "Camera4=PASS", heater_turret_vision_ok)
        heater_turret_vision_fail = counter(i, "Camera4=FAIL", heater_turret_vision_fail)
        heater_spread_vision_ok = counter(i, "Camera5=PASS", heater_spread_vision_ok)
        heater_spread_vision_fail = counter(i, "Camera5=FAIL", heater_spread_vision_fail)
        heater_insert_ok = counter(i, "Insert2Place=1[Ok]", heater_insert_ok)
        heater_insert_error = counter(i, "Insert2Place=1[E", heater_insert_error)
        fg_vision1_ok = counter(i, "Camera6=PASS", fg_vision1_ok)
        fg_vision1_fail = counter(i, "Camera6=FAIL", fg_vision1_fail)
        fg_vision2_ok = counter(i, "Camera7=PASS", fg_vision2_ok)
        fg_vision2_fail = counter(i, "Camera7=FAIL", fg_vision2_fail)
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
         ("Pass", fg_vision2_ok),  # output at final inspection 2
         ("Fail", fg_vision1_fail + fg_vision2_fail),  # total failure in fg_vision1 and fg_vision2
         ("DT", 0), ("Run Time", 0), ("Assist", 0),
         ("Stn1 Fail", ah_infeed_pick_ok - ah_infeed_place_ok),
         ("Stn2 Fail", ah_vision_fail),
         ("Stn3D Fail", heater1_vision_fail + heater2_vision_fail),
         ("Stn3F Fail", heater_turret_vision_fail),
         ("Stn3G Fail", heater_spread_vision_fail),
         ("Stn4_1 Fail", fg_vision1_fail),
         ("Stn4_2 Fail", fg_vision2_fail),
         ("Stn5 Fail", ah_outfeed_pick_ok - ah_outfeed_place_ok),
         ("Stn1 Pass", ah_infeed_place_ok),
         ("Stn2 Pass", ah_vision_ok),
         ("Stn3D Pass", heater1_vision_ok + heater2_vision_ok),
         ("Stn3F Pass", heater_turret_vision_ok),
         ("Stn3G Pass", heater_spread_vision_ok),
         ("Stn4_1 Pass", fg_vision1_ok),
         ("Stn4_2 Pass", fg_vision2_ok),
         ("Stn5 Pass", ah_outfeed_place_ok),
         ("AH Toss", ah_vision_fail),
         ("Heater1 Toss", heater1_vision_fail),
         ("Heater2 Toss", heater2_vision_fail),
         ("Total Heater Toss",
          heater1_vision_fail + heater2_vision_fail + heater_turret_vision_fail + heater_spread_vision_fail),
         ("AH Pass", ah_vision_ok),
         ("Heater1 Pass", heater1_vision_ok),
         ("Heater2 Pass", heater2_vision_ok),
         ("Total Heater Pass", heater_spread_vision_ok),
         ])
    return parsed_temp, errors_parsed, resistance_values, time_diff_mins, log_start_time, log_end_time, new_counts

#
# if __name__ == '__main__':
#     main('/Users/justinclay/Downloads/AKB Log files/AKB M1/2021-10-11_History.log')
