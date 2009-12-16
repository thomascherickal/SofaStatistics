#! /usr/bin/env python
# -*- coding: utf-8 -*-
import wx

import my_globals
import getdata
import projects


class FiltSelectDlg(wx.Dialog):
    def __init__(self, parent, flds, var_labels, var_notes, var_types, val_dics,
                 fil_var_dets, bolnew=True):
        debug = False
        self.flds = flds
        self.var_labels = var_labels
        self.var_notes = var_notes
        self.var_types = var_types
        self.val_dics = val_dics
        self.fil_var_dets = fil_var_dets
        if bolnew:
            title = _("Apply filter")
        else:
            title = _("Current filter")
        wx.Dialog.__init__(self, parent=parent, title=title, 
                           style=wx.CAPTION|wx.CLOSE_BOX|
                           wx.SYSTEM_MENU, pos=(300, 100))
        self.parent = parent
        self.panel = wx.Panel(self)
        lblfont = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD)
        szrMain = wx.BoxSizer(wx.VERTICAL)
        szrQuick = wx.BoxSizer(wx.HORIZONTAL)
        szrFlexible = wx.BoxSizer(wx.HORIZONTAL)
        radQuick = wx.RadioButton(self.panel, -1, _("Quick"))
        radFlexible = wx.RadioButton(self.panel, -1, _("Flexible"))
        radQuick.Bind(wx.EVT_RADIOBUTTON, self.OnRadQuickSel)
        radFlexible.Bind(wx.EVT_RADIOBUTTON, self.OnRadFlexSel)
        self.dropVars = wx.Choice(self.panel, -1, size=(300, -1))
        self.dropVars.Bind(wx.EVT_RIGHT_DOWN, self.OnRightClickVars)
        self.setup_vars()
        gte_choices = ["=", "!=", ">", "<", ">=", "<="]
        self.dropGTE = wx.Choice(self.panel, -1, choices=gte_choices)
        self.txtVal = wx.TextCtrl(self.panel, -1, "")
        szrQuick.Add(radQuick, 0)
        szrQuick.Add(self.dropVars, 1, wx.LEFT|wx.RIGHT, 5)
        szrQuick.Add(self.dropGTE, 0)
        szrQuick.Add(self.txtVal, 0)
        szrFlexible.Add(radFlexible, 0)
        szrMain.Add(szrQuick, 0, wx.ALL, 5)
        szrMain.Add(szrFlexible, 0, wx.ALL, 5)
        self.panel.SetSizer(szrMain)
        szrMain.SetSizeHints(self)
        self.Layout()

    def setup_vars(self, var=None):
        var_names = projects.get_approp_var_names(self.flds)
        var_choices, self.sorted_var_names = \
            getdata.get_sorted_choice_items(dic_labels=self.var_labels, 
                                            vals=var_names)
        self.dropVars.SetItems(var_choices)
        if var:
            idx = self.sorted_var_names.index(var)
        else:
            idx = 0
        self.dropVars.SetSelection(idx)

    def OnRadQuickSel(self, event):
        ""
        self.enable_quick_dets(True)
        
    def OnRadFlexSel(self, event):
        ""
        self.enable_quick_dets(False)
        
    def enable_quick_dets(self, enable):
        self.dropVars.Enable(enable)
        self.dropGTE.Enable(enable)
        self.txtVal.Enable(enable)

    def get_var(self):
        idx = self.dropVars.GetSelection()
        var = self.sorted_var_names[idx]
        var_item = self.dropVars.GetStringSelection()
        return var, var_item
    
    def OnRightClickVars(self, event):
        var, choice_item = self.get_var()
        var_name, var_label = getdata.extractChoiceDets(choice_item)
        updated = projects.SetVarProps(choice_item, var_name, var_label, 
                            self.flds, self.var_labels, self.var_notes, 
                            self.var_types, self.val_dics, self.fil_var_dets)
        if updated:
            self.setup_vars(var)
        