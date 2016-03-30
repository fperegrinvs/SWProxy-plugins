import json
import os
import time
import SWPlugin

from SWParser import rune_set_id, rune_effect, monster_name, rune_effect_type

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
    9001: "Dragon's Lair",
    10025: "Hall of Heroes",
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
        return default
    return value_map[key]


class RunLogger(SWPlugin.SWPlugin):
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
        if command == 'BattleScenarioResult' or command == 'BattleDungeonResult':
            return self.log_end_battle(req_json, resp_json, config)

        if command == 'BattleDungeonStart':
            stage = '%s B%s' % (get_map_value(req_json['dungeon_id'], dungeon_map, req_json['dungeon_id']),
                                          req_json['stage_id'])

        if command == 'BattleScenarioStart':
            stage = '%s %s - %s' % (get_map_value(req_json['region_id'], scenario_map),
                                              get_map_value(req_json['difficulty'], difficulty_map),
                                              req_json['stage_no'])

        if command == 'BattleDungeonStart' or command == 'BattleScenarioStart':
            if 'run-logger-data' not in config:
                config['run-logger-data'] = {}

            plugin_data = config['run-logger-data']
            wizard_id = str(req_json['wizard_id'])
            start = int(time.time())
            plugin_data[wizard_id] = {'stage' : stage, 'start': start}

    def log_end_battle(self, req_json, resp_json, config):
        if not config["log_runs"]:
            return

        wizard_id = str(resp_json['wizard_info']['wizard_id'])
        if 'run-logger-data' in config and wizard_id in config['run-logger-data'] \
                and 'start' in config['run-logger-data'][wizard_id]:

            delta = int(time.time()) - config['run-logger-data'][wizard_id]['start']
            m = divmod(delta, 60)
            s = m[1]  # seconds
            elapsed_time = '%s:%02d' % (m[0], s)
        else:
            elapsed_time = 'N/A'

        win_lost = 'Win' if resp_json["win_lose"] == 1 else 'Lost'
        reward = resp_json['reward'] if 'reward' in resp_json else {}
        crystal = reward['crystal'] if 'crystal' in reward else 0
        energy = reward['energy'] if 'energy' in reward else 0

        if 'run-logger-data' in config and wizard_id in config['run-logger-data'] \
                and 'stage' in config['run-logger-data'][wizard_id]:
            resp_stage = config['run-logger-data'][wizard_id]['stage']
        else:
            resp_stage = 'unknown'

        log_entry = "%s,%s,%s,%s,%s,%s,%s," % (time.strftime("%Y-%m-%d %H:%M"), resp_stage, win_lost,
                                               elapsed_time, reward['mana'], crystal, energy)

        if 'crate' in reward:
            if 'rune' in reward['crate']:
                rune = reward['crate']['rune']
                eff = rune_efficiency(rune) * 100
                rune_set = rune_set_id(rune['set_id'])
                slot = rune['slot_no']
                grade = rune['class']
                rank = get_map_value(len(rune['sec_eff']), rune_class_map)

                log_entry += "Rune,%s*,%s,%s,%0.2f%%,%s,%s,%s,%s" % (
                    grade, rune['sell_value'], rune_set, eff, slot, rank, rune_effect(rune['pri_eff']),
                    rune_effect(rune['prefix_eff']))

                for se in rune['sec_eff']:
                    log_entry += ",%s" % rune_effect(se)
            else:
                other_item = self.get_item_name(reward['crate'])
                log_entry += other_item

        filename = "%s-runs.csv" % wizard_id
        if not os.path.exists(filename):
            log_entry = 'Date,Dungeon,Result,Clear time,Mana,Crystal,Energy,Drop,Rune Grade,Sell value,' \
                        + 'Rune Set,Max Efficiency,Slot,Rune Rarity,Main stat,Prefix stat,Secondary stat 1,Secondary stat 2,' \
                        + 'Secondary stat 3,Secondary stat 4\n' + log_entry

        with open(filename, "a") as fr:
            fr.write(log_entry)
            fr.write('\n')
        return
