import json
import os
import time
from SWParser import *
from SWPlugin import SWPlugin
import threading

rival_name = { #there may be more, given alt versions of rivals
    '5001': "(R) Gready",
    '5002': "(R) Razak",
    '5003': "(R) Edmund",
    '5004': "(R) Volta",
    '5006': "(R) Taihan",
    '5007': "(R) Shai",
    '5009': "(R) Morgana",
    '5010': "(R) Kellan",
    '5011': "(R) Kiyan"
}

class ArenaLogger(SWPlugin):
    def __init__(self):
        with open('swproxy.config') as f:
            self.config = json.load(f)

    def process_request(self, req_json, resp_json):
        config = self.config
        if 'log_arena' not in config or not config['log_arena']:
            return

        command = req_json['command']
        if command == 'GetArenaLog' or command == 'GetArenaWizardList' or command == 'BattleArenaStart':
            if 'arena-logger-data' not in config:
                config['arena-logger-data'] = {}		
            plugin_data = config['arena-logger-data']
            wizard_id = str(req_json['wizard_id'])
            if wizard_id not in plugin_data:
                plugin_data[wizard_id] = {}

        if command == 'GetArenaLog':
            revenge_list = {}
            for opp in resp_json['arena_log']:
                revenge_list[str(opp['wizard_id'])] = opp['wizard_name']
            plugin_data[wizard_id].update({'revenge_list' : revenge_list})

        if command == 'GetArenaWizardList':
            arena_list = {}
            for opp in resp_json['arena_list']:
                arena_list[str(opp['wizard_id'])] = opp['wizard_name']
            plugin_data[wizard_id].update({'arena_list' : arena_list})

        if command == 'BattleArenaStart':
            start = int(time.time())
            opp_monster_list = {}
            for opp_mon in resp_json['opp_unit_list']:
                opp_monster_list[opp_mon['pos_id']] = opp_mon['unit_info']['unit_master_id']
            opponent_id = req_json['opp_wizard_id']
            plugin_data[wizard_id].update({'start' : start, 'opp_monster_list' : opp_monster_list, 'opponent_id' : opponent_id})

        if command == 'BattleArenaResult':
            return self.log_end_battle(req_json, resp_json, config)

    def build_unit_dictionary(self, wizard_id):
        with open('%s-optimizer.json' % wizard_id) as f:
            user_data = json.load(f)
            mon_dict = {}
            for mon in user_data["mons"]:
                mon_dict[mon['unit_id']] = mon['name']
            return mon_dict

    def log_end_battle(self, req_json, resp_json, config):
        if not config["log_arena"]:
            return

        command = req_json['command']

        if command == 'BattleArenaResult':
            wizard_id = str(resp_json['wizard_info']['wizard_id'])
            if 'arena-logger-data' in config and wizard_id in config['arena-logger-data'] \
                    and 'start' in config['arena-logger-data'][wizard_id]:
                start = config['arena-logger-data'][wizard_id]['start']
                delta = int(time.time()) - start
                m = divmod(delta, 60)
                s = m[1]  # seconds
                elapsed_time = '%s:%02d' % (m[0], s)
                opp_monster_list = config['arena-logger-data'][wizard_id]['opp_monster_list']
            else:
                elapsed_time = 'N/A'

        wizard_id = str(resp_json['wizard_info']['wizard_id'])
        user_mons = self.build_unit_dictionary(wizard_id)
        win_lost = 'Win' if resp_json["win_lose"] == 1 else 'Lost'

        reward = resp_json['reward'] if 'reward' in resp_json else {}
        mana = reward['mana'] if 'mana' in reward else 0
        crystal = reward['crystal'] if 'crystal' in reward else 0
        energy = reward['energy'] if 'energy' in reward else 0
        honor = reward['honor_point'] if 'honor_point' in reward else 0

        opponent_list = {}
        if 'arena-logger-data' in config and wizard_id in config['arena-logger-data'] \
                and 'arena_list' in config['arena-logger-data'][wizard_id]:
            opponent_list.update(config['arena-logger-data'][wizard_id]['arena_list'])
        if 'arena-logger-data' in config and wizard_id in config['arena-logger-data'] \
                and 'revenge_list' in config['arena-logger-data'][wizard_id]:
            opponent_list.update(config['arena-logger-data'][wizard_id]['revenge_list'])
        opponent_list.update(rival_name)
        opponent_id = str(config['arena-logger-data'][wizard_id]['opponent_id'])

        if opponent_list.has_key(opponent_id):
            opponent = opponent_list[opponent_id]
        else:
            opponent = opponent_id

        del config['arena-logger-data'][wizard_id]['start'] # make sure start time doesn't persist
        del config['arena-logger-data'][wizard_id]['opp_monster_list'] # make sure opp_mons doen't persist				
        del config['arena-logger-data'][wizard_id]['opponent_id'] # make sure opponent_id doesn't persist
        # don't delete arena_list or revenge_list as they are needed for future battles
        filename = "%s-arena.csv" % wizard_id
        is_new_file = not os.path.exists(filename)

        with open(filename, "ab") as log_file:
            field_names = ['date', 'result', 'time', 'mana', 'crystal', 'energy', 'honor', 'opponent', 
			               'team1', 'team2', 'team3', 'team4', 'opteam1', 'opteam2', 'opteam3', 'opteam4']

            header = {'date': 'Date', 'result': 'Result', 'time':'Clear time', 'mana':'Mana',
                      'crystal': 'Crystal', 'energy': 'Energy', 'honor': 'Honor', 'opponent': 'Opponent', 
                      'team1': 'Team1', 'team2': 'Team2', 'team3': 'Team3', 'team4': 'Team4',
                      'opteam1': 'OpTeam1', 'opteam2': 'OpTeam2', 'opteam3': 'OpTeam3', 'opteam4': 'OpTeam4'}

            SWPlugin.call_plugins('process_csv_row', ('arena_logger', 'header', (field_names, header)))

            log_writer = DictUnicodeWriter(log_file, fieldnames=field_names)
            if is_new_file:
                log_writer.writerow(header)

            log_entry = {'date': time.strftime("%Y-%m-%d %H:%M"), 'result': win_lost, 'time': elapsed_time,
                         'mana': mana, 'crystal': crystal, 'energy': energy, 'honor' : honor}

            log_entry['opponent'] = opponent
            if 'unit_list' in resp_json and len(resp_json['unit_list']) > 0:
                for i in range(1, len(resp_json['unit_list']) + 1):
                    log_entry['team%s' % i] = monster_name(resp_json['unit_list'][i-1]['unit_master_id'])
            else:
                for i in range(1, len(req_json['unit_id_list']) + 1):
                    id = req_json['unit_id_list'][i-1]['unit_id']
                    log_entry['team%s' % i] = user_mons[id]
            for i in range(1, len(opp_monster_list) + 1):
                log_entry['opteam%s' % i] = monster_name(opp_monster_list[i])

            SWPlugin.call_plugins('process_csv_row', ('arena_logger', 'entry', (field_names, log_entry)))
            log_writer.writerow(log_entry)
            return
