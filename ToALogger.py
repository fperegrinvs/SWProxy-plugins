import json
import os
import time
from SWParser import *
import SWPlugin

class ToALogger(SWPlugin.SWPlugin):
    def __init__(self):
        with open('swproxy.config') as f:
            self.config = json.load(f)

    def process_request(self, req_json, resp_json):
        config = self.config
        if 'log_toa' not in config or not config['log_toa']:
            return

        command = req_json['command']
        if command == 'BattleTrialTowerResult_v2':
            return self.log_end_battle(req_json, resp_json, config)

        if command == 'BattleTrialTowerStart_v2':
            if 'toa-logger-data' not in config:
                config['toa-logger-data'] = {}

            plugin_data = config['toa-logger-data']
            wizard_id = str(resp_json['wizard_info']['wizard_id'])
            start = int(time.time())
            monsters = resp_json['trial_tower_unit_list'][2]
            plugin_data[wizard_id] = {'start': start, 'monsters': monsters}

    def build_unit_dictionary(self, wizard_id):
        with open('%s-optimizer.json' % wizard_id) as f:
            user_data = json.load(f)
            mon_dict = {}
            for mon in user_data["mons"]:
                mon_dict[mon['unit_id']] = mon['name']
            return mon_dict

    def log_end_battle(self, req_json, resp_json, config):
        if not config["log_toa"]:
            return

        wizard_id = str(resp_json['wizard_info']['wizard_id'])
        if 'toa-logger-data' in config and wizard_id in config['toa-logger-data'] \
                and 'start' in config['toa-logger-data'][wizard_id]:

            start_data = config['toa-logger-data'][wizard_id]

            delta = int(time.time()) - start_data['start']
            m = divmod(delta, 60)
            s = m[1]  # seconds
            elapsed_time = '%s:%02d' % (m[0], s)
        else:
            elapsed_time = 'N/A'

        win_lost = 'Win' if resp_json["win_lose"] == 1 else 'Lost'
        stage = req_json['floor_id']
        if req_json['difficulty'] == 1:
            difficulty = 'Normal'
        elif req_json['difficulty'] == 2:
            difficulty = 'Hard'
        else: 
            difficulty = 'N/A'
        user_mons = self.build_unit_dictionary(wizard_id)

        filename = "%s-toa.csv" % wizard_id
        is_new_file = not os.path.exists(filename)

        with open(filename, "ab") as log_file:
            field_names = ['date', 'stage', 'difficulty', 'result', 'time', 'team1', 'team2', 'team3', 'team4', 'team5',
                           'opteam1', 'opteam2', 'opteam3', 'opteam4', 'opteam5']

            header = {'date': 'Date', 'stage': 'Stage', 'difficulty': 'Difficulty', 'result': 'Result', 'time': 'Clear time',
                      'team1': 'Team 1', 'team2': 'Team 2', 'team3': 'Team 3', 'team4': 'Team 4', 'team5': 'Team 5',
                      'opteam1': 'Op Team 1', 'opteam2': 'Op Team 2', 'opteam3': 'Op Team 3', 'opteam4': 'Op Team 4', 'opteam5': 'Op Team 5'}

            SWPlugin.SWPlugin.call_plugins('process_csv_row', ('toa_logger', 'header', (field_names, header)))

            log_writer = DictUnicodeWriter(log_file, fieldnames=field_names)
            if is_new_file:
                log_writer.writerow(header)

            log_entry = {'date': time.strftime("%Y-%m-%d %H:%M"), 'stage': stage, 'difficulty': difficulty,
                         'result': win_lost, 'time': elapsed_time}

            for i in range(1, len(req_json['unit_id_list']) + 1):
                id = req_json['unit_id_list'][i-1]['unit_id']
                log_entry['team%s' % i] = user_mons[id]

            for i in range(1, len(start_data['monsters']) + 1):
                log_entry['opteam%s' % i] = monster_name(start_data['monsters'][i-1]['unit_master_id'])

            SWPlugin.SWPlugin.call_plugins('process_csv_row', ('toa_logger', 'entry', (field_names, log_entry)))
            log_writer.writerow(log_entry)
            return