import json
import os
import time
import SWPlugin

from SWParser import rune_set_id, rune_effect, monster_name, rune_effect_type

runecraft_grade_map = {
    1: 'Common',
    2: 'Magic',
    3: 'Rare',
    4: 'Hero',
    5: 'Legendary'
}

raid_map = {
    1001: 'Khi\'zar',
}

def identify_raid(id):
    return raid_map[id]

def identify_rune_grade(id):
    return runecraft_grade_map[id]

class RaidLogger(SWPlugin.SWPlugin):
    def __init__(self):
        with open('swproxy.config') as f:
            self.config = json.load(f)

    def process_request(self, req_json, resp_json):
        config = self.config
        if 'log_raids' not in config or not config['log_raids']:
            return

        command = req_json['command']
        if command == 'BattleRiftOfWorldsRaidResult':
            return self.log_end_battle(req_json, resp_json, config)

        if command == 'BattleRiftOfWorldsRaidStart':
            if 'raid-logger-data' not in config:
                config['raid-logger-data'] = {}

            plugin_data = config['raid-logger-data']
            wizard_id = str(resp_json['wizard_info']['wizard_id'])
            start = int(time.time())
            stage = '%s R%s' % (identify_raid(resp_json['battle_info']['room_info']['raid_id']), resp_json['battle_info']['stage_id'])
            team = []
            for i in resp_json['battle_info']['user_list']:
                if i['wizard_id'] != resp_json['wizard_info']['wizard_id']:
                    team.append(i['wizard_name'])

            plugin_data[wizard_id] = {'stage' : stage, 'start': start, 'team': team}

    def log_end_battle(self, req_json, resp_json, config):
        if not config["log_raids"]:
            return

        wizard_id = str(resp_json['wizard_info']['wizard_id'])
        if 'raid-logger-data' in config and wizard_id in config['raid-logger-data'] \
                and 'start' in config['raid-logger-data'][wizard_id]:

            start_data = config['raid-logger-data'][wizard_id]

            delta = int(time.time()) - start_data['start']
            m = divmod(delta, 60)
            s = m[1]  # seconds
            elapsed_time = '%s:%02d' % (m[0], s)
        else:
            elapsed_time = 'N/A'

        win_lost = 'Win' if resp_json["win_lose"] == 1 else 'Lost'
        log_entry = "%s,%s,%s,%s,%s,%s," % (time.strftime("%Y-%m-%d %H:%M"), start_data['stage'] if 'stage' in start_data else 'unknown',
                                            win_lost, elapsed_time, start_data['team'][0], start_data['team'][1])

        if win_lost == 'Win':
            order = 0
            for i in resp_json['battle_reward_list']:
                if wizard_id != str(i['wizard_id']):
                    order += 1
                else:
                    break

            reward = resp_json['battle_reward_list'][order]['reward_list'][0]
            if reward['item_master_type'] == 1:
                log_entry += "%s" % 'Rainbowmon 3*'
            elif reward['item_master_type'] == 6:
                log_entry += "%s,%s" % ('Mana Stones', reward['item_quantity'])
            elif reward['item_master_type'] == 27:
                if reward['runecraft_type'] == 2:
                    item = 'Grindstone'
                elif reward['runecraft_type'] == 1:
                    item = 'Enchanted Gem'
                value = resp_json['reward']['crate']['runecraft_info']['sell_value']
                rune_set = rune_set_id(reward['runecraft_set_id'])
                rarity = identify_rune_grade(reward['runecraft_rank'])
                stat = rune_effect_type(reward['runecraft_effect_id'])
                log_entry += "%s,%s,%s,%s,%s" % (item, value, rune_set, rarity, stat)
            elif reward['item_master_type'] == 9:
                if reward['item_master_id'] == 2:
                    log_entry += "Mystical Scroll"
                elif reward['item_master_id'] == 8:
                    log_entry += "Summoning Stones x%s" % reward['item_quantity']
            elif reward['item_master_type'] == 10: #placeholder waiting for info
                log_entry += "Shapeshifting Stone x%s" % reward['item_quantity']
            else:
                log_entry += "Unknown drop %s" % json.dumps(reward)

        filename = "%s-raids.csv" % wizard_id
        if not os.path.exists(filename):
            log_entry = 'Date,Raid,Result,Clear time,Teammate #1,Teammate #2,Drop,Sell Value,Rune Set,Rarity,Stat\n' + log_entry

        with open(filename, "a") as fr:
            fr.write(log_entry)
            fr.write('\n')
        return