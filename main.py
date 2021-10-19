import os
import re
import log_to_csv_module1 as m1

listOfFiles = []
path = '/Users/justinclay/Downloads/AKB Log files'
LOG_FILE_PATH = '/Users/justinclay/Downloads/AKB Log files/AKB M1/2021-10-11_History.log'


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

    _, _, _, _, _, _, new_all_counts = m1.main(
        LOG_FILE_PATH)

# for i in listOfFiles:
#     if re.findall('AKB M1', i):
#         try:
#             temp_data, errors_parsed_list, ohms, total_time_mins, log_start_time, log_end_time, new_all_counts = \
#                 m1.parse_log(lines)
#         except ValueError:
#             pass
