import os
import re
import log_to_csv_module1 as m1
import log_to_csv_module2 as m2
import log_to_csv_module3 as m3
import log_to_csv_module4 as m4
import pandas as pd
from openpyxl import load_workbook

listOfFiles = []
path = '/Users/justinclay/Downloads/AKB Log files'
LOG_FILE_PATH = '/Users/justinclay/Downloads/AKB Log files/AKB M1/2021-10-12_History.log'
m1_finallist = []
m2_finallist = []
m3_finallist = []
m4_finallist = []

wb = load_workbook(filename='/Users/justinclay/Downloads/Steam Akribis Data Lot 10-11 to 10-14.xlsx')
sheet_names = wb.sheetnames
sheet_m1 = wb[sheet_names[7]]
sheet_m2 = wb[sheet_names[8]]
sheet_m3 = wb[sheet_names[9]]
sheet_m4 = wb[sheet_names[10]]


def scandirectory(path):
    global listOfFiles
    for (dirpath, dirnames, filenames) in os.walk(path):
        listOfFiles += [os.path.join(dirpath, file) for file in filenames]


if __name__ == '__main__':
    scandirectory(path)

    for i in listOfFiles:
        if i.split("/")[-1] == '.DS_Store':
            listOfFiles.remove(i)
            pass

for i in listOfFiles:
    if re.findall('AKB M1', i):
        try:
            _, _, _, _, _, _, M1_new_all_counts = m1.main(i)
            M1_new_all_counts.update({'Build': _})
            M1_new_all_counts.move_to_end('Build', last=False)
            M1_new_all_counts.update({'Date': i.split("/")[-1].split("_")[0]})
            M1_new_all_counts.move_to_end('Date', last=False)
            # m1_finallist.append(M1_new_all_counts)
            # m1_finallist.append(list(M1_new_all_counts.values()))
            sheet_m1.append(list(M1_new_all_counts.values()))
        except ValueError:
            pass

    if re.findall('AKB M2', i):
        try:
            _, _, _, _, _, _, M2_new_all_counts = m2.main(i)
            M2_new_all_counts.update({'Build': _})
            M2_new_all_counts.move_to_end('Build', last=False)
            M2_new_all_counts.update({'Date': i.split("/")[-1].split("_")[0]})
            M2_new_all_counts.move_to_end('Date', last=False)
            # m2_finallist.append(M2_new_all_counts)
            # m2_finallist.append(list(M2_new_all_counts.values()))
            sheet_m2.append(list(M2_new_all_counts.values()))
        except ValueError:
            pass
    if re.findall('AKB M3', i):
        try:
            _, _, _, _, _, _, M3_new_all_counts = m3.main(i)
            M3_new_all_counts.update({'Build': _})
            M3_new_all_counts.move_to_end('Build', last=False)
            M3_new_all_counts.update({'Date': i.split("/")[-1].split("_")[0]})
            M3_new_all_counts.move_to_end('Date', last=False)
            # m3_finallist.append(M3_new_all_counts)
            # m3_finallist.append(list(M3_new_all_counts.values()))
            sheet_m3.append(list(M3_new_all_counts.values()))
        except ValueError:
            pass
    if re.findall('AKB M4', i):
        try:
            _, _, _, _, _, _, M4_new_all_counts = m4.main(i)
            M4_new_all_counts.update({'Build': _})
            M4_new_all_counts.move_to_end('Build', last=False)
            M4_new_all_counts.update({'Date': i.split("/")[-1].split("_")[0]})
            M4_new_all_counts.move_to_end('Date', last=False)
            # m4_finallist.append(list(M4_new_all_counts.values()))
            sheet_m4.append(list(M4_new_all_counts.values()))
        except ValueError:
            pass


wb.save(filename='/Users/justinclay/Downloads/Steam Akribis Data Lot 10-11 to 10-14_2.xlsx')
