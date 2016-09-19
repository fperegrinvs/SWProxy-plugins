import SWPlugin
import logging
import json
import os
import threading
import urllib

logger = logging.getLogger("SWProxy")

accepted_commands = [
    'BattleDungeonResult',
    'BattleScenarioStart',
    'BattleScenarioResult',
    'SummonUnit',
]


class SwarfarmLogger(SWPlugin.SWPlugin):
    scenario_info = None

    def __init__(self):
        super(SwarfarmLogger, self).__init__()

        config_name = 'swproxy.config'
        if not os.path.exists(config_name):
            self.config = {}
            return

        with open(config_name) as f:
            self.config = json.load(f)

    def process_request(self, req_json, resp_json):
        if 'disable_swarfarm_logger' in self.config and self.config['disable_swarfarm_logger']:
            return

        t = threading.Thread(target=self.process_data, args=(req_json, resp_json))
        t.start()
        return

    def process_data(self, req_json, resp_json):
        command = req_json.get('command')

        if command not in accepted_commands:
            return

        # Store some data about scenarios in case the player fails. Scenario failure req/resp does not contain dungeon data
        if command == 'BattleScenarioStart':
            self.scenario_info = {
                'region_id': req_json.get('region_id'),
                'difficulty': req_json.get('difficulty'),
                'stage_no': req_json.get('stage_no'),
            }
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
                'scenario_info': self.scenario_info,
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
            data = json.dumps(result_data)
            url = 'https://swarfarm.com/data/log/upload/'
            resp = urllib.urlopen(url, data=urllib.urlencode({'data': data}))
            content = resp.readlines()
            resp.close()
            if resp.getcode() != 200:
                logger.warn('SwarfarmLogger - Error: %s' % content)

            self.scenario_info = None