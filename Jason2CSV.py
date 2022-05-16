import pandas as pd
from datetime import datetime

"""https://amiradata.com/parse-and-convert-json-to-csv-python/"""

now = datetime.now()
current_date = f'{now.day}_{now.month}_{now.year}_{now.hour}_{now.minute}_{now.second}'


class Converter:
    """Преобразовывает json файл в CSV, кодировка utf-8, разделитель - запятая"""
    def __init__(self,
                 file_name,
                 json_file_path,
                 csv_file_path='/Users/vikentijzerebov/PycharmProjects/Job_Boards_Parser/SavedData/CSVFiles/',
                 date=current_date):
        self.file_name = file_name
        self.csv_file_path = csv_file_path
        self.json_file_path = json_file_path
        self.date = date

    def convert_json_to_csv(self):
        pd.set_option('display.max_columns', 50)
        df = pd.read_json(self.json_file_path)
        df.to_csv(f'{self.csv_file_path}hh_{self.date}.csv')


converter = Converter(file_name='test', json_file_path='/Users/vikentijzerebov/PycharmProjects/job_boards_parser/SavedData/JsonFiles/parsed_hh_companies.json', )
converter.convert_json_to_csv()


def remove_duplicate(it):
    seen = []
    for x in it:
        if x not in seen:
            yield x
            seen.append(x)


remove_duplicate(te)