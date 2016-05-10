# template : https://docs.google.com/spreadsheets/d/1KPt_KE_Z_RcJh6Wz-VCuU14HEQusKxBeCUzO99SpE2c/edit?usp=sharing
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from threading import Thread
import json
import os
import time
from SWParser import *
import SWPlugin
from itertools import groupby
from string import ascii_uppercase

result_map = {
    1: 'win',
    2: 'lost',
    3: 'draw'
}

summary_battle_columns = {
    1 : ('B', 'G'),
    2 : ('H', 'M'),
    3 : ('N', 'S'),
    4 : ('T', 'Y'),
    5 : ('Z', 'AE'),
    6 : ('AF', 'AK'),
    7 : ('AL', 'AQ'),
    8 : ('AR', 'AW'),
    9 : ('AX', 'BC'),
    10 : ('BD', 'BI'),
    11 : ('BJ', 'BO'),
    12 : ('BP', 'BU'),
}

column_names = []
for p in range(5):
    for c in ascii_uppercase:
        prefix = ascii_uppercase[p - 1] if p > 0 else ''
        column_names.append(prefix + c)

attack_tab = 'Attack'
attack_summary = 'Attack Summary'
log_tab = 'Log'
defense_tab = 'Defense Summary'
sheet_name = 'Guildwar %s'

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

    def get_worksheet(self, key, sheet):
        date = datetime.date.today()
        days_until_saturday = 5 - date.weekday()
        next_saturday = date + datetime.timedelta(days_until_saturday)

        scope = ['https://spreadsheets.google.com/feeds']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(key, scope)
        gc = gspread.authorize(credentials)
        sheet_name = 'Guildwar %s' % next_saturday.strftime('%m-%d-%Y')
        return gc.open(sheet_name)

    def gp_values(self, atk1, atk2, gp):
        if atk1 == 'win' and atk2 == 'win':
            return gp / 2, gp/2

        if gp == 0:
            return 0, 0

        if atk1 == 'draw':
            return 1, gp - 1
        else:
            return gp - 1, 1

    def write_attack_tab(self, sheet, data, members_list, opponent_list, battle_index):
        wks = sheet.worksheet(attack_tab)
        line = (battle_index * 33) + 1
        cells = wks.range('A%s:AY%s' % (line, line + 32))

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

        wks.update_cells(cells)

    def write_attack_summary_members(self, sheet, members_list):
        wks = sheet.worksheet(attack_summary)

        cells = wks.range('A4:A33')
        for i, name in enumerate(members_list):
            cells[i].value = name
        wks.update_cells(cells)

    def write_attack_summary(self, sheet, data, members_list, opponent_list, battle_index):
        wks = sheet.worksheet(attack_summary)
        start_col, end_col = summary_battle_columns[battle_index +1]

        cells = wks.range('%s2:%s33' % (start_col, end_col))

        # clean everything
        for i, cell in enumerate(cells):
            if i > 12 and i % 32 > 1:
                cell.value = ''

        # guild name
        cells[0].value = data['guild']

        sword_counter = {}
        for match in data['matches']:
            member = match['member_name']

            if member not in sword_counter:
                sword_counter[member] = 0

            swords = sword_counter[member]
            sword_counter[member] += 1

            index_member = members_list.index(member)
            cell = (6*index_member) + (swords * 2) + 12
            round1, round2 = self.gp_values(match['result_1'], match['result_2'], match['gp'])
            cells[cell].value = round1
            cells[cell + 1].value = round2

        wks.update_cells(cells)

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
            thread = Thread(target = self.log_guildwar, args = (req_json, resp_json, config))
            thread.start()

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
                id = str(battle['rid'])

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
        date = datetime.date.today()
        days_until_saturday = 5 - date.weekday()
        next_saturday = date + datetime.timedelta(days_until_saturday)


        week = next_saturday.strftime("%U")
        cache_name = "guildwar-%s.json" % week
        with open(cache_name, 'wb') as f:
            json.dump(cache, f)

    def get_sheet_name(self, battle_type):
        week = datetime.date.today().strftime("%U")
        type = 'Attack' if battle_type == 'attack' else 'Defense'
        return 'GW - %s (%s)' % (type, week)

    def write_log(self, battle_list, sheet):
        count = 0
        for battle in battle_list:
            count += len(battle['matches'])

        wks = sheet.worksheet(log_tab)
        cells = wks.range('A2:I%s' % (count+2))
        pos = 0
        for battle in battle_list:
            for match in battle['matches']:
                cells[pos].value = match['id']
                cells[pos+1].value = match['type']
                cells[pos+2].value = match['member_name']
                cells[pos+3].value = match['op_name']
                cells[pos+4].value = match['op_guild']
                cells[pos+5].value = match['result_1']
                cells[pos+6].value = match['result_2']
                cells[pos+7].value = match['gp']
                cells[pos+8].value = match['end']
                pos += 9
        wks.update_cells(cells)

    def write_defense_summary(self, battle_list, member_list, sheet):
        wks = sheet.worksheet(defense_tab)

        counters = {}
        guilds = []
        guild_info = []

        # write members names
        cells = wks.range('B1:CK1')
        for i, member in enumerate(member_list):
            cells[i*3].value = member
            counters[member] = 0
        wks.update_cells(cells)

        # write defense data
        cells = wks.range('B5:CM49')

        for battle in battle_list:
            if battle['type'] == 'attack':
                continue

            guilds.append(battle['guild'])
            guild_info.append({"name": battle['guild'], "date": battle['matches'][0]['end']})

            for match in battle['matches']:
                member = match['member_name']
                count = counters[member]
                cell = (90 * count) + (member_list.index(member) * 3)
                cells[cell].value = '#%s' % str(len(guilds))
                cells[cell + 1].value = match['result_1'].upper()[0]
                cells[cell + 2].value = match['result_2'].upper()[0]
                counters[member] += 1
        wks.update_cells(cells)

    def log_guildwar(self, req_json, resp_json, config):
        cache = self.process_input_json(resp_json)
        self.save_cache(cache)

        member_list = self.create_members_list(cache)
        battle_list = self.group_battles(cache)

        sheet = self.get_worksheet(self.config['google_key'], self.config['sheet_name'])
        self.write_attack_summary_members(sheet, member_list)
        self.write_log(battle_list, sheet)
        self.write_defense_summary(battle_list, member_list, sheet)

        index = {'attack': 0, 'defense': 0}
        for battle in battle_list:
            op_members = self.get_opponent_list(battle['matches'])
            type = battle['type']
            battle_index = index[type]
            index[type] += 1
            if type == 'attack':
                self.write_attack_tab(sheet, battle, member_list, op_members, battle_index)
                self.write_attack_summary( sheet, battle, member_list, op_members, battle_index)
