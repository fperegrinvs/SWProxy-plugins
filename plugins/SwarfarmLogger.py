import SWPlugin
import logging
import json
import httplib, urllib

logger = logging.getLogger("SWProxy")


class SwarfarmLogger(SWPlugin.SWPlugin):
    def __init__(self):
        with open('swproxy.config') as f:
            self.config = json.load(f)

    def process_request(self, req_json, resp_json):
        if 'enable_swarfarm_logger' not in self.config or not self.config['enable_swarfarm_logger']:
            return

        command = req_json.get('command')

        if command not in ['BattleDungeonResult', 'BattleScenarioResult', 'SummonUnit']:
            return

        result_data = None

        # Generate a trimmed dict with the necessary items from request and response
        if command in ['BattleDungeonResult', 'BattleScenarioResult']:
            result_data = {
                'command': command,
                'wizard_id': req_json.get('wizard_id'),
                'tzone': resp_json.get('tzone'),
                'tvalue': resp_json.get('tvalue'),
                'dungeon_id': req_json.get('dungeon_id'),
                'stage_id': req_json.get('stage_id'),
                'scenario_info': resp_json.get('scenario_info'),
                'clear_time': req_json['clear_time'],
                'win_lose': resp_json['win_lose'],
                'reward': resp_json.get('reward'),
            }
        elif command == 'SummonUnit':
            result_data = {
                'wizard_id': req_json.get('wizard_id'),
                'command': command,
                'tzone': resp_json.get('tzone'),
                'tvalue': resp_json.get('tvalue'),
                'mode': req_json.get('mode'),
                'item_info': resp_json.get('item_info'),
                'unit_list': resp_json.get('unit_list'),
            }
        elif command == 'BattleRiftOfWorldsRaidResult':
            pass

        if result_data:
            with open(str(resp_json['ts_val']) + '-logger-output.json', 'ab') as f:
                json.dump(result_data, f)
                f.write('\n\n')

            data = json.dumps(result_data)
            url = 'https://swarfarm.com/data/log/upload/'
            resp = urllib.urlopen(url, data=urllib.urlencode({'data': data}))
            content = resp.readlines()
            resp.close()
            if resp.getcode() != 200:
                logger.warn('SwarfarmLogger - Error: ' + content)
