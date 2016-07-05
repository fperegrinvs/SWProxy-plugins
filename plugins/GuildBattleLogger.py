import json
import os
import time
from SWProxyVanilla.SWParser import *
from SWPlugin import SWPlugin
import threading

win_lose_round = {
    1 : 'Win',
    2 : 'Lose',
    3 : 'Draw',
}

win_lose_battle = {
    1 : 'Win',
    2 : 'Draw',
    3 : 'Win',
    4 : 'Lose',
    6 : 'Lose',
    9 : 'Draw',
}

class GuildBattleLogger(SWPlugin):
    def __init__(self):
        with open('swproxy.config') as f:
            self.config = json.load(f)

    def process_request(self, req_json, resp_json):
        config = self.config
        if 'log_guild_battle' not in config or not config['log_guild_battle']:
            return

        command = req_json['command']
        if command == 'GetGuildWarMatchupInfo' or command == 'BattleGuildWarStart':
            if 'guild-battle-logger-data' not in config:
                config['guild-battle-logger-data'] = {}		
            plugin_data = config['guild-battle-logger-data']
            wizard_id = str(req_json['wizard_id'])
            if wizard_id not in plugin_data:
                plugin_data[wizard_id] = {}

        if command == 'GetGuildWarMatchupInfo':
            guild_opponent_list = {}
            for opp in resp_json['opp_guild_member_list']:
                guild_opponent_list[str(opp['wizard_id'])] = opp['wizard_name']
            guildname = resp_json['opp_guild_info']['name']
            plugin_data[wizard_id].update({'guild_opponent_list' : guild_opponent_list, 'guildname' : guildname})

        if command == 'BattleGuildWarStart':
            start = int(time.time())
            opp_monster_list = {}
            for battle in resp_json['guildwar_opp_unit_list']:
				for opp_mon in battle:
					opp_monster_list[opp_mon['pos_id']] = opp_mon['unit_info']['unit_master_id']
            i = 1
            monster_list = {}
            for battle in resp_json['guildwar_my_unit_list']:
                for mon in battle:
                    monster_list[i] = mon['unit_master_id']
                    i += 1
            opponent_id = req_json['opp_wizard_id']
            plugin_data[wizard_id].update({'start' : start, 'opp_monster_list' : opp_monster_list, 'opponent_id' : opponent_id, 'monster_list' : monster_list,})

        if command == 'BattleGuildWarResult':
            return self.log_end_battle(req_json, resp_json, config)

    def build_unit_dictionary(self, wizard_id):
        with open('%s-optimizer.json' % wizard_id) as f:
            user_data = json.load(f)
            mon_dict = {}
            for mon in user_data["mons"]:
                mon_dict[mon['unit_id']] = mon['name']
            return mon_dict

    def log_end_battle(self, req_json, resp_json, config):
        if not config["log_guild_battle"]:
            return

        command = req_json['command']

        if command == 'BattleGuildWarResult':
            wizard_id = str(resp_json['wizard_info']['wizard_id'])
            if 'guild-battle-logger-data' in config and wizard_id in config['guild-battle-logger-data'] \
                    and 'start' in config['guild-battle-logger-data'][wizard_id]:
                start = config['guild-battle-logger-data'][wizard_id]['start']
                delta = int(time.time()) - start
                m = divmod(delta, 60)
                s = m[1]  # seconds
                elapsed_time = '%s:%02d' % (m[0], s)
                opp_monster_list = config['guild-battle-logger-data'][wizard_id]['opp_monster_list']
                monster_list = config['guild-battle-logger-data'][wizard_id]['monster_list']
            else:
                elapsed_time = 'N/A'

        wizard_id = str(resp_json['wizard_info']['wizard_id'])
        user_mons = self.build_unit_dictionary(wizard_id)

        guildpoints = 0
        for reward in resp_json['reward_list']:
            guildpoints += reward['guild_point_var']
            guildpoints += reward['guild_point_bonus']

        round1 = win_lose_round[resp_json['win_lose_list'][0]]
        round2 = win_lose_round[resp_json['win_lose_list'][1]]
        result = win_lose_battle[resp_json['win_lose_list'][0]*resp_json['win_lose_list'][1]]

        oppguild = config['guild-battle-logger-data'][wizard_id]['guildname']

        opponent_list = {}
        if 'guild-battle-logger-data' in config and wizard_id in config['guild-battle-logger-data'] \
                and 'guild_opponent_list' in config['guild-battle-logger-data'][wizard_id]:
            opponent_list.update(config['guild-battle-logger-data'][wizard_id]['guild_opponent_list'])
        opponent_id = str(config['guild-battle-logger-data'][wizard_id]['opponent_id'])

        if opponent_list.has_key(opponent_id):
            opponent = opponent_list[opponent_id]
        else:
            opponent = opponent_id

        del config['guild-battle-logger-data'][wizard_id]['start'] # make sure start time doesn't persist
        del config['guild-battle-logger-data'][wizard_id]['opp_monster_list'] # make sure opp_mons doen't persist				
        del config['guild-battle-logger-data'][wizard_id]['opponent_id'] # make sure opponent_id doesn't persist
        filename = "%s-guildbattle.csv" % wizard_id
        is_new_file = not os.path.exists(filename)

        with open(filename, "ab") as log_file:
            field_names = ['date', 'oppguild', 'opponent', 'round1', 'team1', 'team2', 'team3', 'opteam1', 'opteam2', 'opteam3',
						   'round2', 'team4', 'team5', 'team6', 'opteam4', 'opteam5', 'opteam6', 'result', 'guildpoints']

            header = {'date': 'Date', 'oppguild': 'Enemy Guild', 'opponent': 'Opponent', 
					  'round1': 'Round 1', 'team1': 'Team1', 'team2': 'Team2', 'team3': 'Team3', 'opteam1': 'OpTeam1', 'opteam2': 'OpTeam2', 'opteam3': 'OpTeam3', 
					  'round2': 'Round 2', 'team4': 'Team4', 'team5': 'Team5', 'team6': 'Team6', 'opteam4': 'OpTeam4', 'opteam5': 'OpTeam5', 'opteam6': 'OpTeam6', 
					  'result': 'Result', 'guildpoints': 'Guild Points'}

            SWPlugin.call_plugins('process_csv_row', ('guild_battle_logger', 'header', (field_names, header)))

            log_writer = DictUnicodeWriter(log_file, fieldnames=field_names)
            if is_new_file:
                log_writer.writerow(header)

            log_entry = {'date': time.strftime("%Y-%m-%d %H:%M"), 'oppguild': oppguild, 'opponent': opponent,
                         'round1': round1, 'round2': round2, 'result': result, 'guildpoints' : guildpoints}

            for i in range(1, len(monster_list) + 1):
                log_entry['team%s' % i] = monster_name(monster_list[i])
            for i in range(1, len(opp_monster_list) + 1):
                log_entry['opteam%s' % i] = monster_name(opp_monster_list[i])

            SWPlugin.call_plugins('process_csv_row', ('guild_battle_logger', 'entry', (field_names, log_entry)))
            log_writer.writerow(log_entry)
            return
