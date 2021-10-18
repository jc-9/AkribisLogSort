import datetime
import re
import csv
import sys

from collections import OrderedDict

p = re.compile(r'\[\w+\]')
q = re.compile(r'\w+\d=FAIL')

# START_TIME = "2019-04-23 15:16:46.2775"
# END_TIME = "2019-04-23 16:22:07.5131"
START_TIME = ""
END_TIME = ""

if len(sys.argv) > 1:
    LOG_FILE_PATH = sys.argv[1]
    if len(sys.argv) > 2:
        START_TIME = sys.argv[2]
        END_TIME = sys.argv[3]
else:
    raise Exception("Log file path is mandatory to process.")

RUNNING_STATUS = "Running"
STOPPING_STATUS = "Stopped"


with open(LOG_FILE_PATH) as f:
    lines = f.readlines()
log_csv_name = LOG_FILE_PATH.split("/")[-1]
log_csv_name = log_csv_name.split(".")[-2] + ".csv"


def get_timedelta(log_time_obj):
    date_time_delta = datetime.timedelta(
        seconds=log_time_obj.hour * 60 * 60 + log_time_obj.minute * 60 + log_time_obj.second,
        microseconds=log_time_obj.microsecond)
    return date_time_delta


def get_date_time_obj(datetime_str):
    datetime_obj = datetime.datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S.%f')
    return datetime_obj


def categorize_time(up_time, time_00, time_02_03, time_above_03):
    total_minutes = up_time.total_seconds()/60
    if total_minutes < 1:
        time_00 += 1
    elif 1 <= total_minutes <= 3:
        time_02_03 += 1
    elif total_minutes > 3:
        time_above_03 += 1
    return time_00, time_02_03, time_above_03

# Original code
# def write_csv_data(temp, output_log_csv_name, output_yield_value, uph,
#                   stn_1, stn_2, stn_3, stn_4, stn_5_1, stn_5_2, stn_6, stn_9, stn_10, errors_parsed, display_counts,
#                   resistance_values, display_material_loss, time_diff_mins, log_start_time, log_end_time, new_counts):

def write_csv_data(temp, output_log_csv_name,
                   errors_parsed,
                   resistance_values, time_diff_mins, log_start_time, log_end_time, new_counts):
# stn_19 = Accumulation


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

    with open(output_log_csv_name.split(".")[0]+"_new_counts.csv", 'w') as out_file:
        writer = csv.writer(out_file, dialect='excel')
        header = list()
        header_value = list()
        for k, v in new_counts.items():
            header.append(k)
            header_value.append(v)
        writer.writerow(header)
        writer.writerow(header_value)

    print("UP Time :" + str(Up_time))

    error_csv_data = [["Time Stamp", "Error"]]
    for error in range(len(errors_parsed)):
        error_csv_data.append([str(errors_parsed[error]["date_time_obj"]), str(errors_parsed[error]["error"])])
    with open(output_log_csv_name.split(".")[0]+"_errors.csv", 'w') as error_csv_file:
        writer = csv.writer(error_csv_file)
        writer.writerows(error_csv_data)

    csvData = [["Cycle_id", "Start", "End", "Failure Mode", "Time(min)", "MTBA(min)"]]
    for i in range(len(session_up_time)):
        csvData.append(
            [str(i + 1), str(session_up_time[i]["start_time"]), str(session_up_time[i]["end_time"]),
             session_up_time[i]["errors"], str(session_up_time[i]["down"]), str(session_up_time[i]["up"])])
    csvData.append(["      "])
    csvData.append(["      "])
#    csvData.append(["Yield", output_yield_value])
    csvData.append(["Total_Up_time", str(Up_time)])
#    csvData.append(["Units Per Hour", str(uph)])
    csvData.append(["      "])
#    csvData.append(["Defects by station: WH Station 1", str(stn_1)])
#    csvData.append(["Defects by station: EC Station 4", str(stn_4)])
#    csvData.append(["Defects by station: WC Station 6", str(stn_6)])
#    csvData.append(["Defects by station: Overall Station 9", str(stn_9)])
#    csvData.append(["Defects by station: RM Station 10", str(stn_10)])
#    csvData.append(["Defects by station: AH Infeed M1-1", str(stn_1)])
#    csvData.append(["Defects by station: Heater Insert M1-3", str(stn_3)])
#    csvData.append(["Defects by station: Inspection M1-4-1", str(stn_4_1)])
#    csvData.append(["Defects by station: Inspection M1-4-2", str(stn_4_2)])
#    csvData.append(["Defects by station: Transfer M1-5", str(stn_5)])
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
#    csvData.append(["WH", str(display_material_loss.get("wh_good")), str(display_material_loss.get("wh_bad")),
#                    stn_1*100])
#    csvData.append(["EC1", str(display_material_loss.get("ec1_good")), str(display_material_loss.get("ec1_bad")),
#                    stn_2*100])
#    csvData.append(["EC2", str(display_material_loss.get("ec2_good")), str(display_material_loss.get("ec2_bad")),
#                    stn_3*100])
#    csvData.append(["WC1", str(display_material_loss.get("wc1_good")), str(display_material_loss.get("wc1_bad")),
#                    stn_5_1*100])
#    csvData.append(["WC2", str(display_material_loss.get("wc2_good")), str(display_material_loss.get("wc2_bad")),
#                    stn_5_2*100])
#    csvData.append(["AH", str(display_material_loss.get("ah_good")), str(display_material_loss.get("ah_bad")),
#                    stn_1*100])
#    csvData.append(["Heater1", str(display_material_loss.get("heater1_good")), str(display_material_loss.get("heater1_bad")),
#                    stn_3e_1*100])
#    csvData.append(["Heater2", str(display_material_loss.get("heater2_good")), str(display_material_loss.get("heater2_bad")),
#                    stn_3e_2*100])
    total_down_time_mins = 0
#    stn_1_4_6 = display_counts.get("OutfeedReject=1[Ok]") + display_counts.get("EContact2=FAIL") + \
#                display_counts.get("WickCoilPlaced=FAIL")
#    time_log_op = display_counts.get("PickAtomizerFromTurret=1[Ok]") - stn_1_4_6
#    tossing_stn_1_4_6 = display_counts.get("PunchEContact2=1[E1002]") + stn_1_4_6
    total_up_time_mins = round(float(Up_time.total_seconds()) / 60, 2)
#    actual_ppm = division_handler((time_log_op + tossing_stn_1_4_6), total_up_time_mins)
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
#    for key, value in display_counts.items():
#        count_csv_data.append([str(key), str(value)])
    with open(output_log_csv_name.split(".")[0]+"_counts.csv", 'w') as count_csv_file:
        count_writer = csv.writer(count_csv_file)
        count_writer.writerows(count_csv_data)
    resistance_csv_data = [["Timestamp", "Resistance(ohm)"]]
#    for resistance in range(len(resistance_values)):
#        resistance_csv_data.append([str(resistance_values[resistance]["timestamp"]),
#                                    str(resistance_values[resistance]["resistance"])])
#    with open(output_log_csv_name.split(".")[0] + "_resistance.csv", 'w') as resistance_csv_file:
#        resistance_writer = csv.writer(resistance_csv_file)
#        resistance_writer.writerows(resistance_csv_data)

#    chart_csv_data = list()
#    chart_csv_data.append(["Name", "Value"])
#    chart_csv_data.append(["    "])
#    chart_csv_data.append(["    "])

#    chart_csv_data.append(["Time Log"])
#    chart_csv_data.append(["    "])
#    chart_csv_data.append(["Date", output_log_csv_name.split(".")[0].split("_")[0]])
#    chart_csv_data.append(["Start Time", str(log_start_time)])
#    chart_csv_data.append(["End Time", str(log_end_time)])
#    chart_csv_data.append(["Speed", "100%"])
#    chart_csv_data.append(["Output", str(time_log_op)])
#    chart_csv_data.append(["Good", str(display_counts.get("PlaceAtomierToPentagon=1[Ok]"))])
#    chart_csv_data.append(["Reject", str(time_log_op-display_counts.get("PlaceAtomierToPentagon=1[Ok]"))])
#    chart_csv_data.append(["Stn 1 Fail Count", str(display_counts.get("FinishedPart=FAIL"))])
#    chart_csv_data.append(["Stn 4 Fail Count", str(display_counts.get("EContactsPlaced=FAIL"))])
#    chart_csv_data.append(["Stn 6 Fail Count", str(display_counts.get("WickCoilPlaced=FAIL"))])
#    chart_csv_data.append(["Stn 9 Fail Count", str(display_counts.get("FinishedPart=FAIL"))])  # TODO
#    chart_csv_data.append(["Stn 10 Fail Count", str(display_counts.get("Resistance measurement failed!"))])
#    chart_csv_data.append(["    "])
#    chart_csv_data.append(["    "])


#    chart_csv_data.append(["Total Parts Input"])
#    chart_csv_data.append(["    "])
#    chart_csv_data.append(["Time Elapsed [min]", str(time_diff_mins)])
#    chart_csv_data.append(["Total DT [min]", str(total_down_time_mins)])
#    chart_csv_data.append(["Run Time [min]:", str(total_up_time_mins)])
#    chart_csv_data.append(["# of Assists", str(len(session_up_time))])
#    chart_csv_data.append(["Calculated Ideal UPH @ Speed", "12000"])
#    chart_csv_data.append(["Machine UPH", str(round(division_handler(time_log_op, total_up_time_mins/60), 0))])
#    chart_csv_data.append(["Theoretical UPH", "12000"])
#    chart_csv_data.append(["Observed UPH", str(round(division_handler(display_counts.get(
#        "PlaceAtomierToPentagon=1[Ok]"), time_diff_mins) * 60, 0))])
#    chart_csv_data.append(["Delta UPH loss", str(12000-round(division_handler(time_log_op, total_up_time_mins/60), 0))])
#    chart_csv_data.append(["Tossing + Stn 1/4/6", str(tossing_stn_1_4_6)])
#    chart_csv_data.append(["Availability", str(time_log_op + tossing_stn_1_4_6)])
#    chart_csv_data.append(["UPH", str(round(division_handler((time_log_op + tossing_stn_1_4_6),
#                                                             total_up_time_mins) * 60, 0))])
#    chart_csv_data.append(["Delta UPH loss inc toss", str(round(12000-division_handler(
#        (time_log_op + tossing_stn_1_4_6), total_up_time_mins) * 60, 0))])
#    chart_csv_data.append(["    "])
#    chart_csv_data.append(["    "])


#    chart_csv_data.append(["Machine Metrics"])
#    chart_csv_data.append(["     "])
#    chart_csv_data.append(["DT %", str(division_handler(total_down_time_mins, time_diff_mins))])
#    chart_csv_data.append(["Max Uninterrupted Time [min]", str(round(longest_up_time.total_seconds()/60, 2))])
#    chart_csv_data.append(["UPH", str(round(division_handler(time_log_op, total_up_time_mins / 60), 0))])
#    yield_value = round(division_handler(display_counts.get("PlaceAtomierToPentagon=1[Ok]"),
#                                                             time_log_op), 4)
#    availability = round(division_handler(total_up_time_mins, time_diff_mins), 4)
#    performance = round(division_handler(round(division_handler(
#        time_log_op, total_up_time_mins/60), 0), 12000), 4)
#    chart_csv_data.append(["Yield %", str(yield_value * 100)])
#    chart_csv_data.append(["Availability", str(availability * 100)])
#    chart_csv_data.append(["Performance", str(performance * 100)])
#    chart_csv_data.append(["OEE", str(round(yield_value * availability * performance, 4) * 100)])
#    chart_csv_data.append(["Observed PPM", str(round(division_handler(time_log_op, time_diff_mins), 0))])
#    chart_csv_data.append(["CT [s]", str(round(60/division_handler(time_log_op, time_diff_mins), 2))])
#    chart_csv_data.append(["Actual PPM", str(actual_ppm)])
#    chart_csv_data.append(["Actual CT [s]", str(round(60/actual_ppm, 4)), round(3600/(60/actual_ppm), 4)])
#    chart_csv_data.append(["Actual Speed", str(round(actual_ppm * 60/12000, 4) * 100)])
#    with open(output_log_csv_name.split(".")[0] + "_chart.csv", 'w') as chart_csv_file:
#        chart_writer = csv.writer(chart_csv_file)
#        chart_writer.writerows(chart_csv_data)


def counter(log_obj, search_key, current_count):
    if search_key in log_obj:
        current_count += 1
    return current_count


def division_handler(numerator, denominator):
    try:
        return numerator/denominator
    except ZeroDivisionError:
        return 0


def parse_log(read_lines):
    machine_start_message = 'INFO Machine status changed to Running'
    errors_parsed = []
    parsed_temp = []
#    place_wick_house_ok = 0
#    pick_wick_house_ok = 0
#    pick_wick_house_e1003 = 0
#    wick_coil_placed_pass = 0
#    wick_coil_placed_fail = 0
#    reject_wick_coil_ok = 0
#    e_contacts_placed_fail = 0
#    e_contacts_placed_pass = 0
#    finished_part_fail = 0
#    finished_part_pass = 0
#    resistance_measure_fail = 0
#    resistance_measure_ok = 0
#    reject_atomizer_ok = 0
#    pick_atomizer_from_turret_ok = 0
#    place_atomier_to_pentagon = 0
#    punch_e_contact1_e1002 = 0
#    punch_e_contact2_e1002 = 0
#    punch_e_contact1_ok = 0
#    punch_e_contact2_ok = 0
#    pick_wick_coil1_e1003 = 0
#    pick_wick_coil2_e1003 = 0
#    pick_wick_coil1_ok = 0
#    pick_wick_coil2_ok = 0
#    e_contact_1_pass = 0
#    e_contact_1_fail = 0
#    e_contact_2_pass = 0
#    e_contact_2_fail = 0
#    wc1_toss = 0
#    wc2_toss = 0
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
    
# stn_19 = Accumulation

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
#        place_wick_house_ok = counter(i, "PlaceWickHousing=1[Ok]", place_wick_house_ok)
#        pick_wick_house_ok = counter(i, "PickWickHousing=1[Ok]", pick_wick_house_ok)
#        pick_wick_house_e1003 = counter(i, "PickWickHousing=1[E", pick_wick_house_e1003)
#        wick_coil_placed_pass = counter(i, "WickCoilPlaced=PASS", wick_coil_placed_pass)
#        wick_coil_placed_fail = counter(i, "WickCoilPlaced=FAIL", wick_coil_placed_fail)
#        reject_wick_coil_ok = counter(i, "RejectWickCoil=1[Ok]", reject_wick_coil_ok)
#        e_contacts_placed_fail = counter(i, "EContactsPlaced=FAIL", e_contacts_placed_fail)
#        e_contacts_placed_pass = counter(i, "EContactsPlaced=PASS", e_contacts_placed_pass)
#        finished_part_fail = counter(i, "FinishedPart=FAIL", finished_part_fail)
#        finished_part_pass = counter(i, "FinishedPart=PASS", finished_part_pass)
#        resistance_measure_fail = counter(i, "Resistance measurement failed!", resistance_measure_fail)
#        resistance_measure_ok = counter(i, "ResistanceMeasure=1[Ok]", resistance_measure_ok)
#        reject_atomizer_ok = counter(i, "RejectAtomizer=1[Ok]", reject_atomizer_ok)
#        pick_atomizer_from_turret_ok = counter(i, "PickAtomizerFromTurret=1[Ok]", pick_atomizer_from_turret_ok)
#        place_atomier_to_pentagon = counter(i, "PlaceAtomierToPentagon=1[Ok]", place_atomier_to_pentagon)
#        punch_e_contact1_e1002 = counter(i, "PunchEContact1=1[E", punch_e_contact1_e1002)
#        punch_e_contact2_e1002 = counter(i, "PunchEContact2=1[E", punch_e_contact2_e1002)
#        punch_e_contact1_ok = counter(i, "PunchEContact1=1[Ok]", punch_e_contact1_ok)
#        punch_e_contact2_ok = counter(i, "PunchEContact2=1[Ok]", punch_e_contact2_ok)
#        pick_wick_coil1_e1003 = counter(i, "PickWickCoil1=1[E", pick_wick_coil1_e1003)
#        pick_wick_coil2_e1003 = counter(i, "PickWickCoil2=1[E", pick_wick_coil2_e1003)
#        pick_wick_coil1_ok = counter(i, "PickWickCoil1=1[Ok]", pick_wick_coil1_ok)
#        pick_wick_coil2_ok = counter(i, "PickWickCoil2=1[Ok]", pick_wick_coil2_ok)
#        e_contact_1_pass = counter(i, "EContact1=PASS", e_contact_1_pass)
#        e_contact_1_fail = counter(i, "EContact1=FAIL", e_contact_1_fail)
#        e_contact_2_pass = counter(i, "EContact2=PASS", e_contact_2_pass)
#        e_contact_2_fail = counter(i, "EContact2=FAIL", e_contact_2_fail)
#        wc1_toss = counter(i, "PickWickCoil1=1[E1", wc1_toss)
#        wc2_toss = counter(i, "PickWickCoil2=1[E1", wc2_toss)
        
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
    log_end_time = get_date_time_obj(log_end_obj[:23])
    time_diff = log_end_time-log_start_time
    hours = (time_diff.total_seconds())/60/60
    time_diff_mins = round((time_diff.total_seconds())/60, 2)
#    uph = division_handler(pick_atomizer_from_turret_ok, hours)

#    stn_1 = division_handler((place_wick_house_ok-e_contacts_placed_pass-e_contacts_placed_fail), place_wick_house_ok)
#    stn_4 = division_handler(e_contacts_placed_fail, (e_contacts_placed_pass+e_contacts_placed_fail))
#    stn_6 = division_handler(wick_coil_placed_fail, (wick_coil_placed_pass+wick_coil_placed_fail))
#    stn_9 = division_handler(finished_part_fail, (finished_part_pass+finished_part_fail))
#    stn_10 = division_handler(resistance_measure_fail, resistance_measure_ok)
#    stn_12 = division_handler(reject_atomizer_ok, pick_atomizer_from_turret_ok)
#    stn_2 = division_handler(punch_e_contact1_e1002, (punch_e_contact1_ok+punch_e_contact1_e1002))
#    stn_3 = division_handler(punch_e_contact2_e1002, (punch_e_contact2_ok+punch_e_contact2_e1002))
#    stn_5_1 = division_handler(pick_wick_coil1_e1003, (pick_wick_coil1_ok+pick_wick_coil1_e1003))
#    stn_5_2 = division_handler(pick_wick_coil2_e1003, (pick_wick_coil2_ok+pick_wick_coil2_e1003))
#    output_yield_value = (1-stn_9)*(1-stn_10)

#    new_counts = OrderedDict([("Start", 0), ("End", 0), ("Output", finished_part_pass + finished_part_fail),
#                              ("Pass", resistance_measure_ok-resistance_measure_fail),
#                              ("Fail", resistance_measure_fail + finished_part_fail),
#                              ("DT", 0), ("Run Time", 0), ("Assist", 0),
#                              ("Stn1 Fail", place_wick_house_ok-e_contacts_placed_pass-e_contacts_placed_fail),
#                              ("Stn2 Fail", e_contact_1_fail), ("Stn3 Fail", e_contact_2_fail),
#                              ("Stn4 Fail", e_contacts_placed_fail), ("Stn6 Fail", wick_coil_placed_fail),
#                              ("Stn9 Fail", finished_part_fail), ("Stn10 Fail", resistance_measure_fail),
#                              ("Stn1 Pass", place_wick_house_ok), ("Stn2 Pass", e_contact_1_pass),
#                              ("Stn3 Pass", e_contact_2_pass), ("Stn4 Pass", e_contacts_placed_pass),
#                              ("Stn6 Pass", wick_coil_placed_pass), ("Stn9 Pass", finished_part_pass),
#                              ("Stn10 Pass", resistance_measure_ok), ("EC1 Toss", punch_e_contact1_e1002),
#                              ("EC2 Toss", punch_e_contact2_e1002), ("WC1 Toss", wc1_toss),
#                              ("WC2 Toss", wc2_toss), ("EC1 Pass", punch_e_contact1_ok),
#                              ("EC2 Pass", punch_e_contact2_ok), ("WC1 Pass", pick_wick_coil1_ok),
#                              ("WC2 Pass", pick_wick_coil2_ok)
#                              ])

    new_counts = OrderedDict([("Start", 0), ("End", 0), ("Output", infeed_pick1_ok+infeed_pick2_ok+infeed_pick3_ok+infeed_pick4_ok), #incoming parts 
                              ("Pass", infeed_place1_ok+infeed_place2_ok+infeed_place3_ok+infeed_place4_ok), #successful placement on accumulator
                              ("Fail", infeed_place1_error+infeed_place2_error+infeed_place3_error+infeed_place4_error  ), #total rejects
                              ("DT", 0), ("Run Time", 0), ("Assist", 0),
                              ("CSA Toss", infeed_pick1_error+infeed_pick2_error+infeed_pick3_error+infeed_pick4_error), #pick failures
                              ("CSA Pass", infeed_pick1_ok+infeed_pick2_ok+infeed_pick3_ok+infeed_pick4_ok),                              
                              ])

# stn_19 = Accumulation

#    display_counts = {"PunchEContact1=1[OK]": punch_e_contact1_ok, "PunchEContact1=1[E1002]": punch_e_contact1_e1002,
#                      "PunchEContact2=1[OK]": punch_e_contact2_ok, "PunchEContact2=1[E1002]": punch_e_contact2_e1002,
#                      "PickWickCoil1=1[Ok]": pick_wick_coil1_ok, "PickWickCoil1=1[E1003]": pick_wick_coil1_e1003,
#                      "PickWickCoil2=1[Ok]": pick_wick_coil2_ok, "PickWickCoil2=1[E1003]": pick_wick_coil2_e1003,
#                      "RejectWickCoil=1[Ok]": reject_wick_coil_ok, "EContactsPlaced=PASS": e_contacts_placed_pass,
#                      "EContactsPlaced=FAIL": e_contacts_placed_fail, "WickCoilPlaced=PASS": wick_coil_placed_pass,
#                      "WickCoilPlaced=FAIL": wick_coil_placed_fail, "PlaceWickHousing=1[Ok]": place_wick_house_ok,
#                      "PickWickHousing=1[OK]": pick_wick_house_ok, "PickWickHousing=1[E1003]": pick_wick_house_e1003,
#                      "ResistanceMeasure=1[OK]": resistance_measure_ok, "RejectAtomizer=1[OK]": reject_atomizer_ok,
#                      "PickAtomizerFromTurret=1[Ok]": pick_atomizer_from_turret_ok,
#                      "PlaceAtomierToPentagon=1[Ok]": place_atomier_to_pentagon,
#                      "FinishedPart=PASS": finished_part_pass, "FinishedPart=FAIL": finished_part_fail,
#                      "EContact1=PASS": e_contact_1_pass, "EContact1=FAIL": e_contact_1_fail,
#                      "EContact2=PASS": e_contact_2_pass, "EContact2=FAIL": e_contact_2_fail,
#                      "Resistance measurement failed!": resistance_measure_fail}
#    wh_good = e_contacts_placed_fail + e_contacts_placed_pass
#    wh_bad = place_wick_house_ok - e_contacts_placed_fail - e_contacts_placed_pass
#    display_material_loss = dict(wh_good=wh_good, wh_bad=wh_bad, ec1_good=punch_e_contact1_ok,
#                                 ec1_bad=punch_e_contact1_e1002, ec2_good=punch_e_contact2_ok,
#                                 ec2_bad=punch_e_contact2_e1002, wc1_good=pick_wick_coil1_ok,
#                                 wc1_bad=pick_wick_coil1_e1003, wc2_good=pick_wick_coil2_ok,
#                                 wc2_bad=pick_wick_coil2_e1003)
#    total = pick_atomizer_from_turret_ok
#    passed = place_atomier_to_pentagon
    return parsed_temp,\
        errors_parsed, resistance_values, time_diff_mins, \
           log_start_time, log_end_time, new_counts


temp_data, errors_parsed_list, \
  ohms, total_time_mins, log_start_time, log_end_time, new_all_counts = parse_log(lines)
write_csv_data(temp_data, log_csv_name, errors_parsed_list,
               ohms, total_time_mins, log_start_time, log_end_time, new_all_counts)
               
               