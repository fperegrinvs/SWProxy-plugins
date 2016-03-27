import SWPlugin
import json
import os
import time

from SWParser import monster_name, monster_attribute

sources = {
	1: 'Unknown', #Confirmed
	2: 'Mystical', #Confirmed
	3: '3', #Legendary?
	4: 'Water', #Confirmed
	5: 'Fire??', #Presumed
	6: 'Wind??', #Presumed
	7: '7', #L&D?
	8: 'Exclusive', #Confirmed
	9: '9'
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
                scroll = 'Social'
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
