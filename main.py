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
