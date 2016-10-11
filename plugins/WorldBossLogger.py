import json
import os
import time
from SWParser import *
import SWPlugin

class WorldBossLogger(SWPlugin.SWPlugin):
    def __init__(self):
        with open('swproxy.config') as f:
            self.config = json.load(f)

    def process_request(self, req_json, resp_json):
        config = self.config
        if 'log_world_boss' not in config or not config['log_world_boss']:
            return

        command = req_json['command']
        if command == 'BattleWorldBossStart':
            return self.log_world_boss(req_json, resp_json, config)

    def build_unit_dictionary(self, wizard_id):
        with open('%s-optimizer.json' % wizard_id) as f:
            user_data = json.load(f)
            mon_dict = {}
            for mon in user_data["mons"]:
                mon_dict[mon['unit_id']] = mon['name']
            return mon_dict

    def log_world_boss(self, req_json, resp_json, config):
        if not config["log_world_boss"]:
            return

        wizard_id = str(req_json['wizard_id'])
        user_mons = self.build_unit_dictionary(wizard_id)
        result = resp_json['worldboss_battle_result']

        filename = "%s-worldboss.csv" % wizard_id
        is_new_file = not os.path.exists(filename)

        with open(filename, "ab") as log_file:
            field_names = ['date', 'boss_n', 'atk_power', 'elem_bonus', 'damage', 'grade']
            header = {'date': 'Date', 'boss_n': 'Boss #', 'atk_power': 'Attack Power',
                      'elem_bonus': 'Elemental Bonus', 'damage': 'Damage', 'grade': 'Grade'}

            for i in range(1, 21):
                field = 'mob%s' % i
                field_names.append(field)
                header[field] = 'Mob %s' % i

            SWPlugin.SWPlugin.call_plugins('process_csv_row', ('worldboss_logger', 'header', (field_names, header)))

            log_writer = DictUnicodeWriter(log_file, fieldnames=field_names)
            if is_new_file:
                log_writer.writerow(header)

            log_entry = {'date': time.strftime("%Y-%m-%d %H:%M"), 'boss_n': req_json['worldboss_id'] - 10000,
                         'atk_power': result['total_battle_point'], 'elem_bonus': result['bonus_battle_point'],
                         'damage': result['total_damage'], 'grade': resp_json['reward_info']['name']}

            for i in range(1, len(req_json['unit_id_list']) + 1):
                id = req_json['unit_id_list'][i-1]['unit_id']
                log_entry['mob%s' % i] = user_mons[id]

            SWPlugin.SWPlugin.call_plugins('process_csv_row', ('worldboss_logger', 'entry', (field_names, log_entry)))
            log_writer.writerow(log_entry)
            return
