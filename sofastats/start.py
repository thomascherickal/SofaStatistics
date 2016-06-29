#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
SOFA Statistics is released under the open source AGPL3 licence and the
copyright is held by Paton-Simpson & Associates Ltd.

SOFA can be run in 3 main ways:

1) As a stand-alone GUI application (launched with start.py)
2) Headless (no GUI) via scripting
3) As a GUI but launched from another GUI program.

In 3) the code won't rely on SofaApp to set the Top Level Window, show it, and
start the main loop. That will need to happen in the calling code which replaces
start.py.
"""

from __future__ import absolute_import
import traceback

from sofastats import home
from sofastats import setup_sofastats


show_early_steps = True # same in setup and start

def main():
    try:
        if show_early_steps:
            print(u"About to load app")
        app = home.SofaApp()
        #inspect = True
        #if inspect:
        #    import wx.lib.inspection
        #    wx.lib.inspection.InspectionTool().Show()
        app.MainLoop()
    except Exception, e:
        print(traceback.format_exc())
        app = setup_sofastats.ErrMsgApp(e)
        app.MainLoop()
        del app


if __name__ == '__main__':
    main()
