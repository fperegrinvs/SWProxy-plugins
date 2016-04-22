## SWProxy Plugins
plugins for the SW Proxy

To get the latest versions of the plugins that are guaranteed to work with the latest SWProxy release, please visit the [Releases](https://github.com/lstern/SWProxy-plugins/releases) section. If you download the plugins directly from the repository they may not be fully compatible with the latest release of SWProxy and may have some reduced or no functionality.

Each plugin has 2 files, a .py file with the actual plugin code and a .yapsy-plugin file with the plugin description. 
To install the plugins just drop the desired plugins in the /plugins folder, copy and edit the .config file to the parent folder and restart sw proxy.

You can have multiple users connected and actively using the same proxy. It will separate users based on their user_id and create separate files for each account.

* [Video Tutorial](https://www.youtube.com/watch?v=T4zI6HViV9g)

### Arena Logger
Logs all attacks you make including rivals. In order to correctly record the opponent's name, the proxy must be connected when your phone recieves the arena log (on login, list refresh or when a new attack is recieved), otherwise it will just record the enemy team. The output filename is [user_id]_arena.csv

### Full Logger
Dumps the contents of the requests and responses from/to com2us servers on a text file ("full_log_filename" from swproxy.config)

### Generate Friend Swarfarm
Generates data for visited friends for use with Swarfarm. The generate data will not contain any inventory rune.

### Google Sheet Writer
Allows all reports to be written directly to Google Sheets. Requires an API key and extra dependencies. Once these dependencies are built into SWProxy a video tutorial will be made showing how to set it up.

### Raid Logger
Will log raid results including time, reward and raid members. The output filename is [user_id]_raids.csv

### Recruit Evaluator
This plugin will generate extra data when visiting friend. The extra data is intended to help with guild recruit evaluation.

### Run Logger
Will log runs and drops from Necro, Dragons, Giants, elemental halls and HoH. The outut filename is [user_id]_runs.csv  

### Summon Logger
Will log summons of any type of scroll, including social and crystal summon. Does not work with individual monster pieces (from SD).  The outut filename is [user_id]_summons.csv

### ToA Logger
Will log results from ToA attempts, it includes floor, difficulty, team used and monster faced in the last wave. The outut filename is [user_id]_toa.csv

### World Boss Logger
Will log each attack against the world boss, including the attack power, elemental bonus, total damage, grade and all the mobs selected for the fight. The outut filename is [user_id]_worldboss.csv

### SWarfarn Logger
Will send data about your runs and summons to [swarfarm](https://swarfarm.com/) where you will have access to full data and statistics about your runs. Site will also offer aggregate statistics using data from all users.