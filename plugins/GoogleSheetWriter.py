import SWPlugin
import gspread
import threading
import json
import os
from oauth2client.service_account import ServiceAccountCredentials


class GoogleSheetWriter(SWPlugin.SWPlugin):
    def __init__(self):
        config_name = 'swproxy.config'
        if not os.path.exists(config_name):
            self.config = {}
            return

        with open('swproxy.config') as f:
            self.config = json.load(f)

    def process_csv_row(self, csv_type, data_type, data):
        if  not 'enable_google_sheet_writer' in self.config or self.config['enable_google_sheet_writer']:
            return

        if csv_type not in ['run_logger', 'arena_logger', 'summon_logger', 'raid_logger', 'worldboss_logger', 'toa_logger']:
            return

        t = threading.Thread(target=self.save_row, args = (csv_type, data_type, data))
        t.start()
        return

    def save_row(self, csv_type, data_type, data):
        if data_type == 'entry':
            if csv_type == 'run_logger':
                tab = 'Runs'
                last_column = 'T'
                total = 'V1'
            elif csv_type == 'arena_logger':
                tab = 'Arena'
                last_column = 'P'
                total = 'R1'
            elif csv_type == 'summon_logger':
                tab = 'Summon'
                last_column = 'F'
                total = 'H1'
            elif csv_type == 'raid_logger':
                tab = 'Raid'
                last_column = 'K'
                total = 'M1'
            elif csv_type == 'worldboss_logger':
                tab = 'World Boss'
                last_column = 'AA'
                total = 'AC1'
            elif csv_type == 'toa_logger':
                tab = 'ToA'
                last_column = 'O'
                total = 'Q1'

            names, row = data
            key_file = self.config['google_key']
            sheet_name = self.config['sheet_name']
            scope = ['https://spreadsheets.google.com/feeds']
            credentials = ServiceAccountCredentials.from_json_keyfile_name(key_file, scope)
            gc = gspread.authorize(credentials)
            wks = gc.open(sheet_name).worksheet(tab)
            line = int(wks.acell(total).value) + 2
            cl = wks.range('A%s:%s%s' % (line, last_column, line))
            for (i, name) in enumerate(names):
                if name in row:
                    cl[i].value = row[name]

            wks.update_cells(cl)
