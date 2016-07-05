from SWPlugin import SWPlugin
import logging

logger = logging.getLogger("SWProxy")


def generate_friend_swarfarm_data(data):
    lock_list = []                  # No data
    inventory = []                  # No data
    helper_list = []                # No data
    friend = data['friend']
    monsters = friend['unit_list']
    deco_list = friend['deco_list']
    
    storage_id = None
    wizard_id = 'unknown'
    for building in friend['building_list']:
        wizard_id = building['wizard_id']
        if building['building_master_id'] == 25:
            storage_id = building['building_id']
            break
    monsters.sort(key = lambda mon: (1 if mon['building_id'] == storage_id else 0,
                                     6 - mon['class'], 40 - mon['unit_level'], mon['attribute'],
                                     1 - ((mon['unit_master_id'] / 10) % 10), mon['unit_id']))

    for monster in monsters:
        runes = monster['runes']
        if isinstance(runes, dict):
            runes = runes.values()
        runes.sort(key = lambda r: (r['set_id'], r['slot_no']))

    with open("visit-" + str(wizard_id) + "-swarfarm.json", "w") as f:
        f.write(json.dumps({
            'inventory_info': inventory,
            'unit_list': monsters,
            'runes': runes,
            'building_list': friend['building_list'],
            'deco_list': deco_list,
            'wizard': friend,
            'unit_lock_list': lock_list,
            'helper_list': helper_list,
        }))

class GenerateFriendData(SWPlugin):
    def process_request(self, req_json, resp_json):
        if resp_json.get('command') == 'VisitFriend':
            generate_friend_swarfarm_data(resp_json)
            logger.info("Friend Swarfarm data generated")
