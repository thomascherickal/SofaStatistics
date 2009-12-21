#! /usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import os
import pprint
import wx

import my_globals


class PrefsDlg(wx.Dialog):
    def __init__(self, parent, prefs_dic):
        wx.Dialog.__init__(self, parent=parent, title=_("Preferences"), 
                           style=wx.CAPTION|wx.CLOSE_BOX|
                           wx.SYSTEM_MENU, pos=(300, 100))
        if not prefs_dic:
            prefs_dic[my_globals.PREFS_KEY] = {my_globals.DATE_ENTRY_FORMAT: \
                                               my_globals.INT_DATE_ENTRY_FORMAT}
        self.prefs_dic = prefs_dic
        self.parent = parent
        self.panel = wx.Panel(self)
        lblfont = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD)
        self.szrMain = wx.BoxSizer(wx.VERTICAL)
        self.szrDateFormat = wx.BoxSizer(wx.VERTICAL)
        df_choices = [_("day/month/year (e.g. 31/01/2010)"),
                      _("month/day/year (e.g. 01/31/2010)")]
        self.radDateFormat = wx.RadioBox(self.panel, -1, "Date Entry Format", 
                                    choices=df_choices, 
                                    style=wx.RA_SPECIFY_ROWS)
        date_format = self.prefs_dic[my_globals.PREFS_KEY]\
            [my_globals.DATE_ENTRY_FORMAT]
        self.radDateFormat.SetSelection(date_format)
        self.szrDateFormat.Add(self.radDateFormat, 0)
        self.szrMain.Add(self.szrDateFormat, 0, wx.ALL, 10)
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
        btnCancel.Bind(wx.EVT_BUTTON, self.OnCancel)
        btnOK = wx.Button(self.panel, wx.ID_OK, _("Apply"))
        btnOK.Bind(wx.EVT_BUTTON, self.OnOK)
        btnOK.SetDefault()
        self.szrStdBtns = wx.StdDialogButtonSizer()
        self.szrStdBtns.AddButton(btnCancel)
        self.szrStdBtns.AddButton(btnOK)
        self.szrStdBtns.Realize()

    def OnCancel(self, event):
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL) # only for dialogs 
        # (MUST come after Destroy)
    
    def OnOK(self, event):
        my_globals.DATE_FORMATS_IN_USE = self.radDateFormat.GetSelection()
        self.prefs_dic[my_globals.PREFS_KEY][my_globals.DATE_ENTRY_FORMAT] = \
            self.radDateFormat.GetSelection()
        prefs_path = os.path.join(my_globals.LOCAL_PATH, 
                                  my_globals.INTERNAL_FOLDER,
                                  my_globals.INT_PREFS_FILE)
        f = codecs.open(prefs_path, "w", "utf-8")
        f.write(u"%s = " % my_globals.PREFS_KEY + \
                pprint.pformat(self.prefs_dic[my_globals.PREFS_KEY]))
        f.close()
        self.Destroy()
        self.SetReturnCode(wx.ID_OK) # or nothing happens!  
        # Prebuilt dialogs must do this internally.
        