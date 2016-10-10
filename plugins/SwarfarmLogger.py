import SWPlugin
import logging
import json
import os
import threading
import urllib
import urllib2

logger = logging.getLogger("SWProxy")


class SwarfarmLogger(SWPlugin.SWPlugin):
    commands_url = 'https://swarfarm.com/data/log/accepted_commands/'
    log_url = 'https://swarfarm.com/data/log/upload/'
    accepted_commands = None

    def __init__(self):
        super(SwarfarmLogger, self).__init__()
        self.plugin_enabled = True

        config_name = 'swproxy.config'
        if not os.path.exists(config_name):
            self.config = {}
        else:
            with open(config_name) as f:
                self.config = json.load(f)

        self.plugin_enabled = not self.config.get('disable_swarfarm_logger', False)

        if self.plugin_enabled:
            # Get the list of accepted commands from the server
            logger.info('SwarfarmLogger - Retrieving list of accepted log types from SWARFARM...')
            try:
                resp = urllib2.urlopen(self.commands_url)
                self.accepted_commands = json.loads(resp.readline())
                resp.close()
            except urllib2.HTTPError:
                logger.fatal('SwarfarmLogger - Unable to retrieve accepted log types. SWARFARM logging is disabled.')
                self.plugin_enabled = False


    def process_request(self, req_json, resp_json):
        if self.plugin_enabled:
            t = threading.Thread(target=self.process_data, args=(req_json, resp_json))
            t.start()

    def process_data(self, req_json, resp_json):
        command = req_json.get('command')

        if command in self.accepted_commands:
            accepted_data = self.accepted_commands[command]
            result_data = {}

            if 'request' in accepted_data:
                result_data['request'] = {item: req_json.get(item) for item in accepted_data['request']}

            if 'response' in accepted_data:
                result_data['response'] = {item: resp_json.get(item) for item in accepted_data['response']}

            if result_data:
                data = json.dumps(result_data)
                resp = urllib2.urlopen(self.log_url, data=urllib.urlencode({'data': data}))
                content = resp.readline()
                resp.close()
                if resp.getcode() == 200:
                    logger.info('SwarfarmLogger - {} logged successfully'.format(command))
                else:
                    logger.warn('SwarfarmLogger - Error: %s' % content)
