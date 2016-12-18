import SWPlugin
import logging
import json
import os
import threading
import urllib
import urllib2

logger = logging.getLogger("SWProxy")


class SwagLogger(SWPlugin.SWPlugin):
    log_url = 'https://gw.swop.one/data/upload/'

    def __init__(self):
        super(SwagLogger, self).__init__()
        self.plugin_enabled = True

        config_name = 'swproxy.config'
        if not os.path.exists(config_name):
            self.config = {}
        else:
            with open(config_name) as f:
                self.config = json.load(f)

        self.plugin_enabled = not self.config.get('disable_swag_logger', False)

    def process_request(self, req_json, resp_json):
        if self.plugin_enabled:
            t = threading.Thread(target=self.process_data, args=(req_json, resp_json))
            t.start()

    def process_data(self, req_json, resp_json):
        command = req_json.get('command')

        if command == 'GetGuildWarBattleLogByGuildId':
            if resp_json:
                try:
                    request = urllib2.Request(self.log_url)
                    request.add_header('Content-Type','application/json')
                    resp = urllib2.urlopen(request, json.dumps(resp_json))
                except urllib2.HTTPError as e:
                    logger.warn('SwagLogger - Error: {}'.format(e.readline()))
                else:
                    resp.close()
                    logger.info('SwagLogger - {} logged successfully'.format(command))
