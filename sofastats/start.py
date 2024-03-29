"""
SOFA Statistics is released under the open source AGPL3 licence and the
copyright is held by Paton-Simpson & Associates Ltd.

SOFA can be run in 3 main ways:

1) As a stand-alone GUI application (launched with start.py) e.g. (depending on
where start.py is located)
  cd ~/projects/sofastats_proj/sofastatistics && python3 -m sofastats.start
2) Headless (no GUI) via scripting
3) As a GUI but launched from another GUI program.

In 3) the code won't rely on SofaApp to set the Top Level Window, show it, and
start the main loop. That will need to happen in the calling code which replaces
start.py.
"""

## modify sys.path to avoid using dist-package version if installed as well
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd().parent))
from sofastats import setup_sofastats
from sofastats import home  #@UnresolvedImport

show_early_steps = True  ## same in setup and start

def main():
    try:
        if show_early_steps:
            print('About to load Sofastats app')
        app = home.SofaApp()
        app.MainLoop()
    except Exception as e:
        print(e)
        app = setup_sofastats.ErrMsgApp(e)
        app.MainLoop()
        del app

if __name__ == '__main__':
    main()
