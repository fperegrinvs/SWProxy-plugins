import SWPlugin
import threading
import json


class CollectorPlugin(SWPlugin.SWPlugin):
    def __init__(self):
        with open('swproxy.config') as f:
            self.config = json.load(f)

    def process_csv_row(self, csv_type, data_type, data):
        if csv_type not in ['run_logger', 'summon_logger']:
            return

        t = threading.Thread(target=self.save_row, args = (csv_type, data_type, data))
        t.start()
        return

    def save_row(self, csv_type, data_type, data):
        if data_type == 'entry':
            if csv_type == 'run_logger' or csv_type == 'summon_logger':
                if len(data) == 2:
                    _, row = data
                else:
                    _, row, _ = data

                with open('demo.json', 'ab') as f:
                    json.dump(row, f)
