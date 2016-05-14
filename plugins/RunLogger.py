import json
import os
import time
from SWParser import *
from SWPlugin import SWPlugin
import threading
import logging
logger = logging.getLogger()

scenario_map = {
    1: 'Garen Forest',
    2: 'Mt. Siz',
    3: 'Kabir Ruins',
    4: 'Mt. White Ragon',
    5: 'Telain Forest',
    6: 'Hydeni Ruins',
    7: 'Tamor Desert',
    8: 'Vrofagus Ruins',
    9: 'Faimon Volcano',
    10: 'Aiden Forest',
    11: 'Ferun Castle',
    12: 'Mt Runar',
    13: 'Chiruka Remains'
}

rune_class_map = {
    0: 'Common',
    1: 'Magic',
    2: 'Rare',
    3: 'Hero',
    4: 'Legendary'
}

dungeon_map = {
    1001: "Hall of Dark",
    2001: "Hall of Fire",
    3001: "Hall of Water",
    4001: "Hall of Wind",
    5001: "Hall of Magic",
    6001: "Necropolis",
    7001: "Hall of Light",
    8001: "Giant's Keep",
    9001: "Dragon's Lair"
}

difficulty_map = {
    1: 'Normal',
    2: 'Hard',
    3: 'Hell'
}

grade_multiplier_map = {
    1: 0.286,
    2: 0.31,
    3: 0.47,
    4: 0.68,
    5: 0.8,
    6: 1
}

sub_max_value_map = {
    'HP%': 40.0,
    'ATK%': 40.0,
    'DEF%': 40.0,
    'ACC': 40.0,
    'RES': 40.0,
    'CDmg': 35.0,
    'CRate': 30.0,
    'SPD': 30.0,
    'ATK flat': 14 * 8.0,
    'HP flat': 344 * 8.0,
    'DEF flat': 14 * 8.0,
}

essence_attribute = {
    1: 'Water',
    2: 'Fire',
    3: 'Wind',
    4: 'Light',
    5: 'Dark',
    6: 'Magic'
}

essence_grade = {
    1: 'Low',
    2: 'Mid',
    3: 'High'
}


def get_sub_score(sub):
    if sub[0] == 0:
        return 0

    rune_type = rune_effect_type(sub[0])
    max = sub_max_value_map[rune_type] if rune_type in sub_max_value_map else 0
    return sub[1] / max


def rune_efficiency(rune):
    slot = rune['slot_no']

    grade = rune['class']

    main_bonus = 1.5 if slot % 2 == 0 else 0.8

    base_score = main_bonus * grade_multiplier_map[grade]

    for se in [rune['prefix_eff']] + rune['sec_eff']:
        base_score += get_sub_score(se)

    score = base_score + 0.8
    max_score = main_bonus + 1.8

    final_score = score / max_score

    return final_score


def get_map_value(key, value_map, default='unknown'):
    if key not in value_map:
        if key > 10000:
            return "Hall of Heroes"
        return default
    return value_map[key]


class RunLogger(SWPlugin):
    def __init__(self):
        with open('swproxy.config') as f:
            self.config = json.load(f)

    @staticmethod
    def get_item_name(crate):
        if 'random_scroll' in crate and crate['random_scroll']['item_master_id'] == 1:
            return "Unknown Scroll x%s" % crate['random_scroll']['item_quantity']
        if 'random_scroll' in crate and crate['random_scroll']['item_master_id'] == 8:
            return "Summoning Stones x%s" % crate['random_scroll']['item_quantity']
        if 'random_scroll' in crate and crate['random_scroll']['item_master_id'] == 2:
            return "Mystical Scroll"
        if 'costume_point' in crate:
            return "Shapeshift Stone x%s" % crate['costume_point']
        if 'rune_upgrade_stone' in crate:
            return "Power Stone x%s" % crate['rune_upgrade_stone']['item_quantity']
        if 'unit_info' in crate:
            return '%s %s*' % (monster_name(crate['unit_info']['unit_master_id']), crate['unit_info']['class'])
        if 'material' in crate:
            id = str(crate['material']['item_master_id'])
            attribute = essence_attribute[int(id[-1])]
            grade = essence_grade[int(id[-4])]
            return "Essence of %s(%s) x%s" % (attribute,grade,crate['material']['item_quantity'])
        if 'summon_pieces' in crate:
            return "Summoning Pieces %s x%s" % (monster_name(crate['summon_pieces']['item_master_id']),crate['summon_pieces']['item_quantity'])
        return 'Unknown drop %s' % json.dumps(crate)

    def process_request(self, req_json, resp_json):
        config = self.config
        if 'log_runs' not in config or not config['log_runs']:
            return

        command = req_json['command']
        if command == 'BattleScenarioStart':
            stage = '%s %s - %s' % (get_map_value(req_json['region_id'], scenario_map),
                                              get_map_value(req_json['difficulty'], difficulty_map),
                                              req_json['stage_no'])
            if 'run-logger-data' not in config:
                config['run-logger-data'] = {}

            plugin_data = config['run-logger-data']
            wizard_id = str(req_json['wizard_id'])
            plugin_data[wizard_id] = {'stage' : stage}

        if command == 'BattleScenarioResult' or command == 'BattleDungeonResult':
            return self.log_end_battle(req_json,resp_json, config)

    def build_unit_dictionary(self, wizard_id):
        if os.path.exists('%s-optimizer.json' % wizard_id):
            with open('%s-optimizer.json' % wizard_id) as f:
                user_data = json.load(f)
                mon_dict = {}
                for mon in user_data["mons"]:
                    mon_dict[mon['unit_id']] = mon['name']
                return mon_dict

    def log_end_battle(self, req_json, resp_json, config):
        if not config["log_runs"]:
            return

        command = req_json['command']

        if command == 'BattleDungeonResult':
            stage = '%s B%s' % (get_map_value(req_json['dungeon_id'], dungeon_map, req_json['dungeon_id']),
                                          req_json['stage_id'])

        if command == 'BattleScenarioResult':
            wizard_id = str(resp_json['wizard_info']['wizard_id'])
            if 'run-logger-data' in config and wizard_id in config['run-logger-data'] \
                    and 'stage' in config['run-logger-data'][wizard_id]:
                stage = config['run-logger-data'][wizard_id]['stage']
            else:
                stage = 'unknown'

        wizard_id = str(resp_json['wizard_info']['wizard_id'])
        if not os.path.exists('%s-optimizer.json' % wizard_id):
            logger.warn("Optimizer file is needed for RunLogger plugin")
            return
        user_mons = self.build_unit_dictionary(wizard_id)
        win_lost = 'Win' if resp_json["win_lose"] == 1 else 'Lost'

        # Are we recording losses?
        if 'log_wipes' in config and not config["log_wipes"] and win_lost == 'Lost':
            return

        reward = resp_json['reward'] if 'reward' in resp_json else {}
        mana = reward['mana'] if 'mana' in reward else 0
        crystal = reward['crystal'] if 'crystal' in reward else 0
        energy = reward['energy'] if 'energy' in reward else 0
        timer = req_json['clear_time']

        m = divmod(timer / 1000, 60)
        elapsed_time = '%s:%02d' % (m[0], m[1])

        filename = "%s-runs.csv" % wizard_id
        is_new_file = not os.path.exists(filename)

        with open(filename, "ab") as log_file:
            field_names = ['date', 'dungeon', 'result', 'time', 'mana', 'crystal', 'energy', 'drop', 'grade', 'value',
                            'set', 'eff', 'slot', 'rarity', 'main_stat', 'prefix_stat','sub1','sub2','sub3','sub4','team1','team2','team3','team4','team5']

            header = {'date': 'Date','dungeon': 'Dungeon', 'result': 'Result', 'time':'Clear time', 'mana':'Mana',
                      'crystal': 'Crystal', 'energy': 'Energy', 'drop': 'Drop', 'grade': 'Rune Grade','value': 'Sell value',
                      'set': 'Rune Set', 'eff': 'Max Efficiency', 'slot': 'Slot', 'rarity': 'Rune Rarity',
                      'main_stat': 'Main stat', 'prefix_stat': 'Prefix stat', 'sub1': 'Secondary stat 1',
                      'sub2': 'Secondary stat 2,', 'sub3': 'Secondary stat 3', 'sub4': 'Secondary stat 4',
                      'team1': 'Team1', 'team2': 'Team2', 'team3': 'Team3', 'team4': 'Team4', 'team5': 'Team5'}

            SWPlugin.call_plugins('process_csv_row', ('run_logger', 'header', (field_names, header)))

            log_writer = DictUnicodeWriter(log_file, fieldnames=field_names)
            if is_new_file:
                log_writer.writerow(header)

            if 'crate' in reward:
                if 'mana' in reward['crate']:
                    reward['mana'] += reward['crate']['mana']
                if 'energy' in reward['crate']:
                    reward['energy'] += reward['crate']['energy']
                if 'crystal' in reward['crate']:
                    reward['crystal'] += reward['crate']['crystal']

            log_entry = {'date': time.strftime("%Y-%m-%d %H:%M"), 'dungeon': stage, 'result': win_lost,
                         'time': elapsed_time, 'mana': mana, 'crystal': crystal, 'energy': energy}

            if 'crate' in reward:
                if 'rune' in reward['crate']:
                    rune = reward['crate']['rune']
                    eff = rune_efficiency(rune) * 100
                    rune_set = rune_set_id(rune['set_id'])
                    slot = rune['slot_no']
                    grade = rune['class']
                    rank = get_map_value(len(rune['sec_eff']), rune_class_map)

                    log_entry['drop'] = 'Rune'
                    log_entry['grade'] = '%s*' % grade
                    log_entry['value'] = rune['sell_value']
                    log_entry['set'] = rune_set
                    log_entry['eff'] = '%0.2f%%' % eff
                    log_entry['slot'] = slot
                    log_entry['rarity'] = rank
                    log_entry['main_stat'] = rune_effect(rune['pri_eff'])
                    log_entry['prefix_stat'] = rune_effect(rune['prefix_eff'])

                    i = 1
                    for se in rune['sec_eff']:
                        log_entry['sub%s' %i] = rune_effect(se)
                        i += 1
                else:
                    other_item = self.get_item_name(reward['crate'])
                    log_entry['drop'] = other_item

            if 'unit_list' in resp_json and len(resp_json['unit_list']) > 0:
                for i in range(1, len(resp_json['unit_list']) + 1):
                    log_entry['team%s' % i] = monster_name(resp_json['unit_list'][i-1]['unit_master_id'])
            else:
                for i in range(1, len(req_json['unit_id_list']) + 1):
                    id = req_json['unit_id_list'][i-1]['unit_id']
                    log_entry['team%s' % i] = user_mons[id]

            if 'instance_info' in resp_json:
                log_entry['drop'] = 'Secret Dungeon'

            SWPlugin.call_plugins('process_csv_row', ('run_logger', 'entry', (field_names, log_entry)))
            log_writer.writerow(log_entry)
            return
