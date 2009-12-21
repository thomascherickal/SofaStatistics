#! /usr/bin/env python
# -*- coding: utf-8 -*-

import wx

class PrefsDlg(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent=parent, title=_("Preferences"), 
                           style=wx.CAPTION|wx.CLOSE_BOX|
                           wx.SYSTEM_MENU, pos=(300, 100))
        self.parent = parent
        self.panel = wx.Panel(self)
        lblfont = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD)
        self.szrMain = wx.BoxSizer(wx.VERTICAL)
        
        self.panel.SetSizer(self.szrMain)
        self.szrMain.SetSizeHints(self)
        self.Layout()