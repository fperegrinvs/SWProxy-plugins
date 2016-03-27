import SWPlugin
import json
import os
import time

from SWParser import monster_name, monster_attribute

sources = {
	1: 'Unknown',
	2: 'Mystical',
	3: 'Light & Dark',
	4: 'Water',
	5: 'Fire',
	6: 'Wind',
	7: 'Legendary',
	8: 'Exclusive'
}

def identify_scroll(id):
    return sources[id]

class SummonLogger(SWPlugin.SWPlugin):
    def __init__(self):
        with open('swproxy.config') as f:
            self.config = json.load(f)

    def process_request(self, req_json, resp_json):
        config = self.config
        if 'log_summon' not in config or not config['log_summon']:
            return

        command = req_json['command']
        if command == 'SummonUnit':
            return self.log_summon(req_json, resp_json, config)

    def log_summon(self, req_json, resp_json, config):
        if not config["log_summon"]:
            return

        if 'unit_list' in resp_json:
            time = resp_json['unit_list'][0]['create_time']
            if 'item_info' in resp_json:
                scroll = identify_scroll(resp_json['item_info']['item_master_id'])
            else:
                mode = req_json['mode']
                if mode == 3:
                    scroll = 'Crystal'
                elif mode == 5:
                    scroll = 'Social'
                else:
                    scroll = 'Unidentified'
            unit_name = monster_name(resp_json['unit_list'][0]['unit_master_id'],'',False)
            attribute = monster_attribute(resp_json['unit_list'][0]['attribute'])
            grade = resp_json['unit_list'][0]['class']
            awakened = str(resp_json['unit_list'][0]['unit_master_id'])
            if int(awakened[-2]) == 0:
                awake = 'No'
            else:
                awake = 'Yes'

            log_entry = "%s,%s,%s,%s,%s*,%s" % (time,scroll,unit_name,attribute,grade,awake)

        filename = config['log_summon_filename']
        if not os.path.exists(filename):
            log_entry = 'Date,Summon Type,Unit,Attribute,Grade,Awakened\n' + log_entry

        with open(filename, "a") as fr:
            fr.write(log_entry)
            fr.write('\n')
        return
