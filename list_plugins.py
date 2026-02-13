
from architecture_modular import REGISTRY
from plugins_core import *
from plugins_advanced import *
from plugins_correlation import *
from plugins_volume import *
from plugins_fundamentals import *
from plugins_attribution import *
from plugins_forensic import *
from plugins_whale import *
from plugins_dashboard import *
from plugins_watch import *
from plugins_screener import *
from plugins_honest import *
from plugins_state import *
from plugins_portfolio import *

print("Registered Plugins:")
for name in REGISTRY.plugins.keys():
    print(f"- '{name}'")
