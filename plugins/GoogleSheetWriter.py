import SWPlugin
import gspread
import threading
import json
from oauth2client.service_account import ServiceAccountCredentials


class GoogleSheetWriter(SWPlugin.SWPlugin):
    def __init__(self):
        with open('swproxy.config') as f:
            self.config = json.load(f)

    def process_csv_row(self, csv_type, data_type, data):
        if csv_type not in ['run_logger', 'arena_logger']:
            return
        t = threading.Thread(target=self.save_row, args = (csv_type, data_type, data))
        t.daemon = True
        t.start()
        return

    def save_row(self, csv_type, data_type, data):
        if data_type == 'entry':
            if csv_type == 'run_logger':
                tab = 'Runs'
            elif csv_type == 'arena_logger':
                tab = 'Arena'

            names, row = data
            key_file = self.config['google_key']
            sheet_name = self.config['sheet_name']
            scope = ['https://spreadsheets.google.com/feeds']
            credentials = ServiceAccountCredentials.from_json_keyfile_name(key_file, scope)
            gc = gspread.authorize(credentials)
            wks = gc.open(sheet_name).worksheet(tab)
            line = int(wks.acell('V1').value) + 2
            cl = wks.range('A%s:U%s' % (line, line))
            for (i, name) in enumerate(names):
                if name in row:
                    cl[i].value = row[name]

            wks.update_cells(cl)
