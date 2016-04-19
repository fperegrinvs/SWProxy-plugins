import time
import json
import os
from SWPlugin import SWPlugin
from SWParser import *

class LiveOptimizer(SWPlugin):
    def __init__(self):
        with open('swproxy.config') as f:
            self.config = json.load(f)

    def process_request(self, req_json, resp_json):
        config = self.config
        if 'live_sync' not in config or not config['live_sync']:
            return
        command = req_json['command']
        if command == 'BattleRiftOfWorldsRaidResult':
            return self.log_end_raid(req_json, resp_json, config)
        if command == 'SellRuneCraftItem':
            return self.logSellCraft(req_json, resp_json, config)
        if command == 'BattleDungeonResult' or command == 'BattleScenarioResult':
            return self.log_dungeon_result(req_json, resp_json, config)
        if command == 'SellRune':
            return self.log_sell_rune(req_json, resp_json, config)
        if command == 'UpgradeRune':
            return self.log_upgrade_rune(req_json, resp_json, config)
        if command == 'EquipRune':
            return self.log_equip_rune(req_json, resp_json, config)
        if command == 'UnequipRune':
            return self.log_unequip_rune(req_json, resp_json, config)
        if command == 'AmplifyRune':
            return self.log_amplify_rune(req_json, resp_json, config)
        if command == 'BuyBlackMarketItem':
            return self.log_buy_rune(req_json, resp_json, config)

    def log_buy_rune(self, req_json, resp_json, config):
        if 'runes' in resp_json and len(resp_json['runes']) == 1:
            self.save_action(req_json['wizard_id'], req_json["ts_val"], 'new_rune',
                         {'rune':  map_rune(resp_json['runes'][0], '0') })

    def log_amplify_rune(self, req_json, resp_json, config):
        self.save_action(req_json['wizard_id'], req_json["ts_val"], 'amplify_rune',
                         {'rune_id': req_json['rune_id'], 'craft_id': req_json['craft_item_id'], 'rune':  map_rune(resp_json['rune'], '0') })

    def log_unequip_rune(self, req_json, resp_json, config):
        self.save_action(req_json['wizard_id'], req_json["ts_val"], 'unequip_rune', {'rune_id': req_json['rune_id']})

    def log_equip_rune(self, req_json, resp_json, config):
        self.save_action(req_json['wizard_id'], req_json["ts_val"], 'equip_rune', {'rune_id': req_json['rune_id'], 'mob_id': req_json['unit_id']})

    def log_upgrade_rune(self, req_json, resp_json, config):
        self.save_action(req_json['wizard_id'], req_json["ts_val"], 'upgrade_rune', {'rune': map_rune(resp_json['rune'], '0')})

    def log_sell_rune(self, req_json, resp_json, config):
        self.save_action(req_json['wizard_id'], req_json["ts_val"], 'sell_rune', {'rune_id_list': req_json['rune_id_list']})

    def log_dungeon_result(self, req_json, resp_json, config):
        win_lost = 'Win' if resp_json["win_lose"] == 1 else 'Lost'

        # do not log loses
        if win_lost == 'Lost':
            return
        reward = resp_json['reward'] if 'reward' in resp_json else {}
        if 'crate' in reward and 'rune' in reward['crate']:
            rune = reward['crate']['rune']
            optimizer_rune, _ = map_rune(rune, 1)
            self.save_action(req_json['wizard_id'], req_json["ts_val"], 'new_rune', {'rune': optimizer_rune})

    def logSellCraft(self, req_json, resp_json, config):
        self.save_action(req_json['wizard_id'], req_json["ts_val"], 'sell_craft', {'craft_id_list': req_json['craft_item_id_list']})
        pass

    def save_action(self, wizard_id, timestamp, action, content):
        result = {'wizard_id': wizard_id, 'timestamp': timestamp, 'action': action}
        result.update(content)
        filename = 'live/%s-live-%s.json' % (wizard_id, int(time.time() * 1000))
        if not os.path.exists('live'):
            os.makedirs('live')
        with open(filename, 'w') as f:
            json.dump(result, f)

    def log_end_raid(self, req_json, resp_json, config):
        wizard_id = str(resp_json['wizard_info']['wizard_id'])
        win_lost = 'Win' if resp_json["win_lose"] == 1 else 'Lost'

        if win_lost == 'Win':
            order = 0
            for i in resp_json['battle_reward_list']:
                if wizard_id != str(i['wizard_id']):
                    order += 1
                else:
                    break

            reward = resp_json['battle_reward_list'][order]['reward_list'][0]
            if reward['item_master_type'] == 27:
                craft_info = resp_json['reward']['crate']['runecraft_info']
                type_str = str(craft_info['craft_type_id'])
                craft = {
                 'item_id': craft_info['craft_item_id'],
                 'type': 'E' if craft_info['craft_type'] == 1 else 'G',
                 'set':  rune_set_id(int(type_str[:-4])),
                 'stat': rune_effect_type(int(type_str[-4:-2])),
                 'grade': int(type_str[-1:])
                }
                self.save_action(wizard_id, resp_json["ts_val"], 'new_craft', {'craft': craft})
