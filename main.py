import os
import re
import log_to_csv_module1 as m1
import pandas as pd

listOfFiles = []
path = '/Users/justinclay/Downloads/AKB Log files'
LOG_FILE_PATH = '/Users/justinclay/Downloads/AKB Log files/AKB M1/2021-10-12_History.log'
finallist = []


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
            _, _, _, _, _, _, new_all_counts = m1.main(i)
            finallist.append(new_all_counts)
        except ValueError:
            pass
df_m1 = pd.DataFrame(finallist, dtype=int)
# df_finalExcel = pd.read_excel('/Users/justinclay/Downloads/Steam Akribis Data Lot 10-11 to 10-14.xlsx',
#                               sheet_name="Summary M1",
#                               usecols=df_m1.columns, skiprows=2)
df_finalExcel = pd.read_excel('/Users/justinclay/Downloads/Steam Akribis Data Lot 10-11 to 10-14.xlsx',
                              sheet_name="Summary M1",
                              skiprows=2,
                              nrows=56
                              )
df_final = df_finalExcel.append(df_m1)
m1_colList = df_m1.columns
df_finalExcel[m1_colList].append(df_m1)