## SWProxy Plugins
plugins for the SW Proxy

Each plugin have 2 files, a .py file with the actual plugin code and a .yapsy-plugin file with the plugin description. 
To install the plugins just drop the desired plugins  in the /plugins folder, copy and edit the .config file to the parent foolder and restart sw proxy.

### Full Logger
Dumps the contents of the requests and responses from/to com2us servers on a text file ("full_log_filename" from swproxy.config)

### Recruit Evaluator
This plugin will generate extra data when visiting friend. The extra data is intended to help with guild recruit evaluation.

### Run Logger
Will log runs and drops from Necro, Dragon and Giants. The outut filename is defined in the "full_log_filename" parameter of swproxy.config  
