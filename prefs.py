#! /usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import os
import pprint
import wx

import my_globals as mg
import config_dlg
import config_globals


class PrefsDlg(wx.Dialog):
    def __init__(self, parent, prefs_dic):
        wx.Dialog.__init__(self, parent=parent, title=_("Preferences"), 
                           style=wx.CAPTION|wx.CLOSE_BOX|
                           wx.SYSTEM_MENU, pos=(300,300))
        if not prefs_dic:
            prefs_dic[mg.PREFS_KEY] = {mg.DEFAULT_LEVEL_KEY: mg.LEVEL_BRIEF}
        self.prefs_dic = prefs_dic
        self.parent = parent
        self.panel = wx.Panel(self)
        self.szr_main = wx.BoxSizer(wx.VERTICAL)
        szr_level = config_dlg.get_szr_level(self, self.panel)
        self.szr_main.Add(self.szr_level, 0, wx.ALL, 10)
        self.setup_btns()
        self.szr_main.Add(self.szr_std_btns, 0, wx.GROW|wx.ALL, 10)
        self.panel.SetSizer(self.szr_main)
        self.szr_main.SetSizeHints(self)
        self.Layout()
        
    def setup_btns(self):
        """
        Set up standard buttons.
        """
        btn_cancel = wx.Button(self.panel, wx.ID_CANCEL)
        btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        btn_ok = wx.Button(self.panel, wx.ID_OK, _("Apply"))
        btn_ok.Bind(wx.EVT_BUTTON, self.on_ok)
        btn_ok.SetDefault()
        self.szr_std_btns = wx.StdDialogButtonSizer()
        self.szr_std_btns.AddButton(btn_cancel)
        self.szr_std_btns.AddButton(btn_ok)
        self.szr_std_btns.Realize()

    def on_cancel(self, event):
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL) # only for dialogs 
        # (MUST come after Destroy)
    
    def on_ok(self, event):
        self.prefs_dic[mg.PREFS_KEY][mg.DEFAULT_LEVEL_KEY] = \
            self.rad_level.GetStringSelection()
        prefs_path = os.path.join(mg.INT_PATH, mg.INT_PREFS_FILE)
        f = codecs.open(prefs_path, "w", "utf-8")
        f.write(u"%s = " % mg.PREFS_KEY +
                pprint.pformat(self.prefs_dic[mg.PREFS_KEY]))
        f.close()
        config_globals.set_DEFAULT_LEVEL() # run after prefs file updated.
        self.Destroy()
        self.SetReturnCode(wx.ID_OK) # or nothing happens!  
        # Prebuilt dialogs must do this internally.
        