import json
import os
import time
from SWParser import *
from SWPlugin import SWPlugin
import threading

sources = {
	1: 'Unknown Scroll',
	2: 'Mystical Scroll',
	3: 'Light & Dark Scroll',
	4: 'Water Scroll',
	5: 'Fire Scroll',
	6: 'Wind Scroll',
	7: 'Legendary Scroll',
	8: 'Exclusive Summons',
	9: "Legendary Pieces",
	10: "Light & Dark Pieces"
}

def identify_scroll(id):
    return sources[id]

class MonsterLogger(SWPlugin):
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

        wizard_id = str(resp_json['wizard_info']['wizard_id'])
        if 'unit_list' in resp_json:
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

        filename = "%s-summons.csv" % wizard_id
        is_new_file = not os.path.exists(filename)

        with open(filename, "ab") as log_file:
            field_names = ['date', 'scroll', 'unit_name', 'attribute', 'grade', 'awake']

            header = {'date': 'Date', 'scroll': 'Scroll', 'unit_name': 'Unit', 'attribute': 'Attribute', 'grade': 'Grade',
                      'awake': 'Awakened'}

            SWPlugin.call_plugins('process_csv_row', ('summon_logger', 'header', (field_names, header)))

            log_writer = DictUnicodeWriter(log_file, fieldnames=field_names)
            if is_new_file:
                log_writer.writerow(header)

            log_entry = {'date': time.strftime("%Y-%m-%d %H:%M"), 'scroll': scroll, 'unit_name': unit_name,
                         'attribute': attribute, 'grade': grade, 'awake': awake}

            SWPlugin.call_plugins('process_csv_row', ('summon_logger', 'entry', (field_names, log_entry)))
            log_writer.writerow(log_entry)
            return
