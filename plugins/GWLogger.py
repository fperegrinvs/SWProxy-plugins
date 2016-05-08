import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import threading
import json
import os
import time
from SWParser import *
import SWPlugin
from itertools import groupby

result_map = {
    1: 'win',
    2: 'lost',
    3: 'draw'
}

def get_match_id(data):
    return data['match_id']

class GWLogger(SWPlugin.SWPlugin):
    def __init__(self):
        if not os.path.exists('swproxy.config'):
            self.config = {}
            return

        with open('swproxy.config') as f:
            self.config = json.load(f)

    def group_battles(self, cache):
        list = sorted(cache.values(), key=get_match_id)
        grouped = groupby(list, lambda x: x['match_id'])
        groups = []
        for key, group in grouped:
            matches = []
            battle = {}
            first = True
            for item in group:
                if first:
                    first = False
                    battle['guild'] = item['op_guild']
                    battle['type'] = item['type']
                    battle['match_id'] = item['match_id']
                matches.append(item)
            battle['matches'] = matches
            groups.append(battle)
        return groups

    def get_worksheet(self, key, sheet, tab, battle):
        scope = ['https://spreadsheets.google.com/feeds']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(key, scope)
        gc = gspread.authorize(credentials)
        wks = gc.open(sheet).worksheet(tab)
        line = (battle * 33) + 1
        cells = wks.range('A%s:AY%s' % (line, line + 32))
        return wks, cells

    def gp_values(self, atk1, atk2, gp):
        if atk1 == 'win' and atk2 == 'win':
            return gp / 2, gp/2

        if gp == 0:
            return 0, 0

        if atk1 == 'draw':
            return 1, gp - 1
        else:
            return gp - 1, 1

    def write_battle(self, data, members_list, opponent_list, cells):
        for i, cell in enumerate(cells):
            if i > 101:
                cell.value = ''

        cells[1].value = data['guild']
        for i, name in enumerate(members_list):
            cells[(i * 51) + 102].value = name

        for match in data['matches']:
            index_member = members_list.index(match['member_name'])
            index_opponent = opponent_list.index(match['op_name'])
            cell = (index_member *51) + 103 + index_opponent * 2
            round1, round2 = self.gp_values(match['result_1'], match['result_2'], match['gp'])
            cells[cell].value = round1
            cells[cell + 1].value = round2

    def get_opponent_list(self, battle_data):
        members = {}
        for entry in battle_data:
            member = entry['op_name']
            if member not in members:
                members[member] = 0
            gp = entry['gp']
            if gp > members[member]:
                members[member] = gp
        member_list = []
        for member in members:
            member_list.append({'id': member, 'gp': members[member]})
        s = sorted(member_list, key=lambda item: item['gp'], reverse=True)
        members = []
        for item in s:
            members.append(item['id'])
        return members

    def create_members_list(self, cache):
        members = {}
        for entry in cache:
            member = cache[entry]['member_name']
            if member not in members:
                members[member] = 0
            members[member] += cache[entry]['gp']
        member_list = []
        for member in members:
            member_list.append({'id': member, 'gp': members[member]})
        s = sorted(member_list, key=lambda item: item['gp'], reverse=True)
        members = []
        for item in s:
            members.append(item['id'])
        return members

    def process_request(self, req_json, resp_json):
        config = self.config
        if 'log_guildwar' not in config or not config['log_guildwar'] or 'enable_google_sheet_writer' not in config\
                or not config['enable_google_sheet_writer']:
            return

        command = req_json['command']
        if command == 'GetGuildWarBattleLogByGuildId':
            return self.log_guildwar(req_json, resp_json, config)

    def read_log(self, filename):
        with open(filename, 'rb') as f:
            return json.load(f)

    def process_input_json(self, resp_json):
        # read previous data
        week = datetime.date.today().strftime("%U")
        cache_name = "guildwar-%s.json" % week
        is_new_file = not os.path.exists(cache_name)
        cache = {} if is_new_file else self.read_log(cache_name)

        log_type = 'attack' if resp_json['log_type'] == 1 else 'defense'
        for guild in resp_json['battle_log_list_group']:
            for battle in guild['battle_log_list']:
                id = battle['rid']

                if id in cache:
                    continue

                log_entry = {'id': id, 'type': log_type, 'member_name': battle['wizard_name'],
                             'op_name': battle['opp_wizard_name'], 'op_guild': battle['opp_guild_name'],
                             'match_id' : battle['match_id'],
                             'result_1': result_map[battle['result'][0]],
                             'result_2': result_map[battle['result'][1]],
                             'gp': battle['guild_point_var'],
                             'end': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(battle['battle_end']))}

                cache[id] = log_entry
        return cache

    def save_cache(self, cache):
        week = datetime.date.today().strftime("%U")
        cache_name = "guildwar-%s.json" % week
        with open(cache_name, 'wb') as f:
            json.dump(cache, f)

    def get_tab_name(self, battle_type):
        week = datetime.date.today().strftime("%U")
        type = 'Attack' if battle_type == 'attack' else 'Defense'
        return 'GW - %s (%s)' % (type, week)

    def log_guildwar(self, req_json, resp_json, config):
        cache = self.process_input_json(resp_json)
        self.save_cache(cache)

        member_list = self.create_members_list(cache)
        battle_list = self.group_battles(cache)

        index = {'attack': 0, 'defense': 0}
        for battle in battle_list:
            op_members = self.get_opponent_list(battle['matches'])
            type = battle['type']
            battle_index = index[type]
            index[type] += 1
            wks, cells = self.get_worksheet(self.config['google_key'], self.config['sheet_name'],
                                            self.get_tab_name(type), battle_index)

            self.write_battle(battle, member_list, op_members, cells)
