#! /usr/bin/env python
# -*- coding: utf-8 -*-

import wx

import gen_config


class NormalDlg(wx.Dialog, gen_config.GenConfig):
    def __init__(self, parent, dbe, con_dets, default_dbs, default_tbls,
                 var_labels, var_notes, var_types, val_dics, fil_var_dets):
        wx.Dialog.__init__(self, parent=parent, title=_("Normal Data?"),
                           size=(1024, 600),
                           style=wx.CAPTION|wx.CLOSE_BOX|wx.SYSTEM_MENU)
        self.dbe = dbe
        self.con_dets = con_dets
        self.default_dbs = default_dbs
        self.default_tbls = default_tbls
        self.var_labels = var_labels
        self.var_notes = var_notes
        self.var_types = var_types
        self.val_dics = val_dics
        self.fil_var_dets = fil_var_dets
        self.panel = wx.Panel(self)

        # szrs
        szrMain = wx.BoxSizer(wx.VERTICAL)
        
        
        self.setup_szrData(self.panel) # mixin
        self.setup_level_widgets(self.panel) # mixin
        self.setup_szrLevel(self.panel) # mixin
        
        btnOK = wx.Button(self.panel, wx.ID_OK)
        btnOK.Bind(wx.EVT_BUTTON, self.OnOK)
        szrStdBtns = wx.StdDialogButtonSizer()
        szrStdBtns.AddButton(btnOK)
        szrStdBtns.Realize()
        szrMain.Add(self.szrData, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szrMain.Add(self.szrLevel, 0, wx.ALL, 10)
        szrMain.Add(szrStdBtns, 0, wx.ALIGN_RIGHT|wx.ALL, 10)
        self.panel.SetSizer(szrMain)
        szrMain.SetSizeHints(self)
        self.Layout()

    def OnOK(self, event):
        self.Destroy()
        event.Skip()
        
    def refresh_vars(self):
        gen_config.GenConfig.update_var_dets(self)