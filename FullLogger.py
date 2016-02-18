import SWPlugin
import json

class FullLogger(SWPlugin.SWPlugin):
    def __init__(self):
        with open('swproxy.config') as f:
            self.config = json.load(f)

    def process_request(self, req_json, resp_json, plugins):
        config = self.config
        if 'full_log' not in config or config['full_log'] == False:
            return


        with open(config['full_log_filename'], "a") as fr:
            import time
            fr.write('%s\n' % time.ctime())
            fr.write('Request (%s):\n' % resp_json['command'])
            fr.write('%s\n' % json.dumps(req_json))
            fr.write('Response (%s):\n' % resp_json['command'])
            fr.write('%s\n\n' % json.dumps(resp_json))
