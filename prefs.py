#! /usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import os
import pprint
import wx

import my_globals
import config_dlg
import config_globals


class PrefsDlg(wx.Dialog):
    def __init__(self, parent, prefs_dic):
        wx.Dialog.__init__(self, parent=parent, title=_("Preferences"), 
                           style=wx.CAPTION|wx.CLOSE_BOX|
                           wx.SYSTEM_MENU, pos=(300,100))
        if not prefs_dic:
            prefs_dic[my_globals.PREFS_KEY] = {my_globals.DEFAULT_LEVEL_KEY: \
                                               my_globals.LEVEL_BRIEF}
        self.prefs_dic = prefs_dic
        self.parent = parent
        self.panel = wx.Panel(self)
        lblfont = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD)
        self.szrMain = wx.BoxSizer(wx.VERTICAL)
        szrLevel = config_dlg.get_szrLevel(self, self.panel)
        self.szrMain.Add(self.szrLevel, 0, wx.ALL, 10)
        self.setup_btns()
        self.szrMain.Add(self.szrStdBtns, 0, wx.GROW|wx.ALL, 10)
        self.panel.SetSizer(self.szrMain)
        self.szrMain.SetSizeHints(self)
        self.Layout()
        
    def setup_btns(self):
        """
        Set up standard buttons.
        """
        btnCancel = wx.Button(self.panel, wx.ID_CANCEL)
        btnCancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        btnOK = wx.Button(self.panel, wx.ID_OK, _("Apply"))
        btnOK.Bind(wx.EVT_BUTTON, self.on_ok)
        btnOK.SetDefault()
        self.szrStdBtns = wx.StdDialogButtonSizer()
        self.szrStdBtns.AddButton(btnCancel)
        self.szrStdBtns.AddButton(btnOK)
        self.szrStdBtns.Realize()

    def on_cancel(self, event):
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL) # only for dialogs 
        # (MUST come after Destroy)
    
    def on_ok(self, event):
        self.prefs_dic[my_globals.PREFS_KEY][my_globals.DEFAULT_LEVEL_KEY] = \
            self.radLevel.GetStringSelection()
        prefs_path = os.path.join(my_globals.INT_PATH, 
                                  my_globals.INT_PREFS_FILE)
        f = codecs.open(prefs_path, "w", "utf-8")
        f.write(u"%s = " % my_globals.PREFS_KEY + \
                pprint.pformat(self.prefs_dic[my_globals.PREFS_KEY]))
        f.close()
        config_globals.set_DEFAULT_LEVEL() # run after prefs file updated.
        self.Destroy()
        self.SetReturnCode(wx.ID_OK) # or nothing happens!  
        # Prebuilt dialogs must do this internally.
        