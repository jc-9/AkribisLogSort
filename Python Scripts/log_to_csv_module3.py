import datetime
import re
import csv
import os
import sys

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
    new_counts["DT"] = total_down_time
    new_counts["Run Time"] = Up_time

    with open(output_log_csv_name.split(".")[0] + "_new_counts.csv", 'w') as out_file:
        writer = csv.writer(out_file, dialect='excel')
        header = list()
        header_value = list()
        for k, v in new_counts.items():
            header.append(k)
            header_value.append(v)
        writer.writerow(header)
        writer.writerow(header_value)

    error_csv_data = [["Time Stamp", "Error"]]
    for error in range(len(errors_parsed)):
        error_csv_data.append([str(errors_parsed[error]["date_time_obj"]), str(errors_parsed[error]["error"])])
    with open(output_log_csv_name.split(".")[0] + "_errors.csv", 'w') as error_csv_file:
        writer = csv.writer(error_csv_file)
        writer.writerows(error_csv_data)

    csvData = [["Cycle_id", "Start", "End", "Failure Mode", "Time(min)", "MTBA(min)"]]
    for i in range(len(session_up_time)):
        csvData.append(
            [str(i + 1), str(session_up_time[i]["start_time"]), str(session_up_time[i]["end_time"]),
             session_up_time[i]["errors"], str(session_up_time[i]["down"]), str(session_up_time[i]["up"])])
    csvData.append(["      "])
    csvData.append(["      "])
    csvData.append(["Total_Up_time", str(Up_time)])
    csvData.append(["      "])

    if time_00 and time_02_03 and time_above_03:
        total_up_time_cycles = time_00 + time_02_03 + time_above_03
        csvData.append(["Percentage of cycles with Run Time below 1 minute",
                        str(round(float(division_handler(time_00, total_up_time_cycles)) * 100, 2))])
        csvData.append(["Percentage of cycles with Run Time from 1 to 3 minutes",
                        str(round(float(division_handler(time_02_03, total_up_time_cycles)) * 100, 2))])
        csvData.append(["Percentage of cycles with Run Time above 3 minutes",
                        str(round(float(division_handler(time_above_03, total_up_time_cycles)) * 100, 2))])
    csvData.append(["      "])
    csvData.append(["      "])
    csvData.append(["", "Good", "Bad", "Material loss percentage"])
    total_down_time_mins = 0
    total_up_time_mins = round(float(Up_time.total_seconds()) / 60, 2)
    try:

        down_time_list = [x["down"] for x in session_up_time if x["down"]]
        total_down_time_mins = round(float(sum(down_time_list, datetime.timedelta(0)).total_seconds()) / 60, 2)
        mtbf = division_handler(sum(down_time_list, datetime.timedelta(0)), len(down_time_list))
        csvData.append(["MTBF", str(mtbf)])
    except:
        pass
    csvData.append(["Longest Up time", longest_up_time])
    with open(output_log_csv_name, 'w') as csvFile:
        writer = csv.writer(csvFile)
        writer.writerows(csvData)
    count_csv_data = [["Name", "Count"]]
    with open(output_log_csv_name.split(".")[0] + "_counts.csv", 'w') as count_csv_file:
        count_writer = csv.writer(count_csv_file)
        count_writer.writerows(count_csv_data)
    resistance_csv_data = [["Timestamp", "Resistance(ohm)"]]
    for resistance in range(len(resistance_values)):
        resistance_csv_data.append([str(resistance_values[resistance]["timestamp"]),
                                    str(resistance_values[resistance]["resistance"])])
    with open(output_log_csv_name.split(".")[0] + "_resistance.csv", 'w') as resistance_csv_file:
        resistance_writer = csv.writer(resistance_csv_file)
        resistance_writer.writerows(resistance_csv_data)


def counter(log_obj, search_key, current_count):
    if search_key in log_obj:
        current_count += 1
    return current_count


def division_handler(numerator, denominator):
    try:
        return numerator / denominator
    except ZeroDivisionError:
        return 0


def parse_log(read_lines):
    machine_start_message = 'INFO Machine status changed to Running'
    errors_parsed = []
    parsed_temp = []
    infeed_pick_ok = 0
    infeed_pick_error = 0
    infeed_place_ok = 0
    infeed_reject_ok = 0
    collector_pick_ok = 0
    collector_pick_error = 0
    collector_place_ok = 0
    collector_place_error = 0
    collector_reject_ok = 0
    collector_pick_vision_ok = 0
    collector_pick_vision_fail = 0
    collector_place_vision_ok = 0
    collector_place_vision_fail = 0
    assembly_vision_ok = 0
    assembly_vision_fail = 0
    press_weld_ok = 0
    press_weld_error = 0
    weld_vision_ok = 0
    weld_vision_fail = 0
    resistance_fail = 0
    resistance_total = 0
    outfeed_pick_ok = 0
    outfeed_place_ok = 0
    outfeed_reject_ok = 0
    fg_vision_new_ok = 0
    fg_vision_new_fail = 0
    fg_vision_ok = 0
    fg_vision_fail = 0
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
        infeed_pick_ok = counter(i, "InfeedPick=1[Ok]", infeed_pick_ok)
        infeed_pick_error = counter(i, "InfeedPick=1[E", infeed_pick_error)
        infeed_place_ok = counter(i, "InfeedPlace=1[Ok]", infeed_place_ok)
        infeed_reject_ok = counter(i, "InfeedReject=1[Ok]", infeed_reject_ok)
        collector_pick_ok = counter(i, "Insert1Pick=1[Ok]", collector_pick_ok)
        collector_pick_error = counter(i, "Insert1Pick=1[E", collector_pick_error)
        collector_place_ok = counter(i, "Insert1Place=1[Ok]", collector_place_ok)
        collector_place_error = counter(i, "Insert1Place=1[E", collector_place_error)
        collector_reject_ok = counter(i, "Insert1Reject=1[Ok]", collector_reject_ok)
        collector_pick_vision_ok = counter(i, "Camera1=PASS", collector_pick_vision_ok)
        collector_pick_vision_fail = counter(i, "Camera1=FAIL", collector_pick_vision_fail)
        collector_place_vision_ok = counter(i, "Camera2=PASS", collector_place_vision_ok)
        collector_place_vision_fail = counter(i, "Camera2=FAIL", collector_place_vision_fail)
        assembly_vision_ok = counter(i, "Camera3=PASS", assembly_vision_ok)
        assembly_vision_fail = counter(i, "Camera3=FAIL", assembly_vision_fail)
        press_weld_ok = counter(i, "LinearPresserandLaserWeld=1[Ok]", press_weld_ok)
        press_weld_error = counter(i, "LinearPresserandLaserWeld=1[E", press_weld_error)
        weld_vision_ok = counter(i, "Camera4=PASS", weld_vision_ok)
        weld_vision_fail = counter(i, "Camera4=FAIL", weld_vision_fail)
        resistance_total = counter(i, "ResistanceMeasure1=1[Ok]", resistance_total)
        resistance_fail = counter(i, "ResistanceFailed", resistance_fail)
        outfeed_pick_ok = counter(i, "OutfeedPick=1[Ok]", outfeed_pick_ok)
        outfeed_place_ok = counter(i, "OutfeedPlace=1[Ok]", outfeed_place_ok)
        outfeed_reject_ok = counter(i, "OutfeedReject=1[Ok]", outfeed_reject_ok)
        fg_vision_new_ok = counter(i, "Camera5=PASS", fg_vision_new_ok)
        fg_vision_new_fail = counter(i, "Camera5=FAIL", fg_vision_new_fail)
        fg_vision_ok = counter(i, "Camera6=PASS", fg_vision_ok)
        fg_vision_fail = counter(i, "Camera6=FAIL", fg_vision_fail)

        if (" EContact1=" in i) or (" EContact2=" in i):
            continue
        log_end_obj = i
        if "Res = " in i:
            ohm_value = (i.split("Res = ")[1]).rsplit(",")[0]
            resistance_values.append({"timestamp": get_date_time_obj(i[:23]), "resistance": ohm_value})
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

    new_counts = OrderedDict([("Start", 0), ("End", 0), ("Output", assembly_vision_ok + assembly_vision_fail),
                              # incoming parts at assembly vision
                              ("Pass", fg_vision_ok),  # output at final inspection
                              ("Fail",
                               fg_vision_fail + resistance_fail + fg_vision_new_fail + weld_vision_fail + assembly_vision_fail),
                              # total failure in fg_vision and resistance_fail weld_vision + assy_vision
                              ("DT", 0), ("Run Time", 0), ("Assist", 0),
                              ("Stn11 Fail", collector_place_vision_fail),
                              ("Stn12B Fail", collector_pick_error),
                              ("Stn12C Fail", collector_pick_vision_fail),
                              ("Stn12 Fail", infeed_pick_ok - infeed_place_ok),
                              ("Stn13 Fail", assembly_vision_fail),
                              ("Stn14 Fail", press_weld_error),
                              ("Stn15 Fail", weld_vision_fail),
                              ("Stn15a Fail", fg_vision_new_fail),
                              ("Stn16 Fail", resistance_fail),
                              ("Stn17 Fail", fg_vision_fail),
                              ("Stn11 Pass", collector_place_vision_ok),
                              ("Stn12B Pass", collector_pick_ok),
                              ("Stn12C Pass", collector_pick_vision_ok),
                              ("Stn12 Pass", infeed_place_ok),
                              ("Stn13 Pass", assembly_vision_ok),
                              ("Stn14 Pass", press_weld_ok),
                              ("Stn15 Pass", weld_vision_ok),
                              ("Stn15a Pass", fg_vision_new_ok),
                              ("Stn16 Pass", resistance_total - resistance_fail),
                              ("Stn17 Pass", fg_vision_ok),
                              ("ASA Toss", infeed_pick_ok - infeed_place_ok),
                              ("ASA Pass", infeed_place_ok),
                              ("Collector Toss",
                               collector_pick_error + collector_pick_vision_fail + collector_place_vision_fail),
                              ("Collector Pass", collector_place_vision_ok),
                              ])

    return parsed_temp, errors_parsed, resistance_values, time_diff_mins, log_start_time, log_end_time, new_counts
