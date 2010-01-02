#! /usr/bin/env python
# -*- coding: utf-8 -*-

import wx
import wxmpl
from pylab import normpdf, randn

import my_globals
import lib
import getdata
import config_dlg
import core_stats
import projects


class HistoDlg(wxmpl.PlotDlg):
    def __init__(self, parent, var_label, vals):
        wxmpl.PlotDlg.__init__(self, parent, 
		    title="Similar to normal distribution curve?", size=(10.0, 6.0), 
		    dpi=96)
        btnOK = wx.Button(self, wx.ID_OK)
        btnOK.Bind(wx.EVT_BUTTON, self.OnOK)
        self.sizer.Add(btnOK, 0, wx.ALIGN_RIGHT|wx.ALL, 10)
        fig = self.get_figure()
        axes = fig.gca()
        n, bins, patches = axes.hist(vals, 100, normed=1, 
            facecolor="#f87526", edgecolor="#8f8f8f")
        mu = core_stats.mean(vals)
        sigma = core_stats.stdev(vals)
        y = normpdf( bins, mu, sigma)
        l = axes.plot(bins, y,  color="#5a4a3d", linewidth=4)
        axes.set_xlabel(var_label)
        axes.set_ylabel('P')
        axes.set_title("Histogram for %s" % var_label)
        self.draw()
        self.SetSizer(self.sizer)
        self.Fit()

    def OnOK(self, event):
        self.Destroy()


class NormalDlg(wx.Dialog, config_dlg.ConfigDlg):
    def __init__(self, parent, dbe, con_dets, default_dbs, default_tbls,
                 var_labels, var_notes, var_types, val_dics, fil_var_dets):
        wx.Dialog.__init__(self, parent=parent, title=_("Normal Data?"),
                           size=(1024, 600),
                           style=wx.CAPTION|wx.CLOSE_BOX|wx.SYSTEM_MENU)
        # the following properties all required to utilise get_szrData
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
        bxDesc = wx.StaticBox(self.panel, -1, _("Purpose"))
        szrDesc = wx.StaticBoxSizer(bxDesc, wx.VERTICAL)
        self.szrData = self.get_szrData(self.panel) # mixin
        bxVars = wx.StaticBox(self.panel, -1, _("Variable to Check"))
        szrVars = wx.StaticBoxSizer(bxVars, wx.VERTICAL)
        szrVarsTop = wx.BoxSizer(wx.HORIZONTAL)
        self.szrLevel = self.get_szrLevel(self.panel) # mixin
        self.szrExamine = wx.BoxSizer(wx.VERTICAL)
        # assembly
        lblDesc1 = wx.StaticText(self.panel, -1, 
                _("Is the frequency curve for the variable close enough to the "
                  "normal distribution curve for use with tests requiring that?"
                  ))
        lblDesc2 = wx.StaticText(self.panel, -1, 
                _("Select a variable to check."))
        szrDesc.Add(lblDesc1, 0, wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szrDesc.Add(lblDesc2, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        lblVars = wx.StaticText(self.panel, -1, _("Variable:"))
        lblVars.SetFont(self.LABEL_FONT)
        self.dropVars = wx.Choice(self.panel, -1, size=(300, -1))
        self.dropVars.Bind(wx.EVT_CHOICE, self.OnVarsSel)
        self.dropVars.Bind(wx.EVT_RIGHT_DOWN, self.OnRightClickVars)
        self.dropVars.SetToolTipString(_("Right click variable to view/edit "
                                         "details"))
        self.setup_vars()
        lblexplanation = wx.StaticText(self.panel, -1, 
                   _("Only quantity (number) variables are listed here. "
                     "Anything else is automatically not normal."))
        szrVarsTop.Add(lblVars, 0, wx.LEFT|wx.RIGHT, 5)
        szrVarsTop.Add(self.dropVars, 0)
        szrVars.Add(szrVarsTop, 0)
        szrVars.Add(lblexplanation, 0, wx.ALL, 5)


        #imgHisto = 


        btnOK = wx.Button(self.panel, wx.ID_OK)
        btnOK.Bind(wx.EVT_BUTTON, self.OnOK)
        szrStdBtns = wx.StdDialogButtonSizer()
        szrStdBtns.AddButton(btnOK)
        szrStdBtns.Realize()
        szrMain.Add(szrDesc, 0, wx.ALL, 10)
        szrMain.Add(self.szrData, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szrMain.Add(szrVars, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szrMain.Add(self.szrLevel, 0, wx.ALL, 10)
        szrMain.Add(self.szrExamine, 1)
        szrMain.Add(szrStdBtns, 0, wx.ALIGN_RIGHT|wx.ALL, 10)
        self.panel.SetSizer(szrMain)
        szrMain.SetSizeHints(self)
        self.Layout()

    def OnOK(self, event):
        self.Destroy()
        event.Skip()

    def setup_vars(self, var=None):
        var_names = projects.get_approp_var_names(self.flds, self.var_types,
                                        min_data_type=my_globals.VAR_TYPE_QUANT)
        var_choices, self.sorted_var_names = lib.get_sorted_choice_items(
                                    dic_labels=self.var_labels, vals=var_names)
        self.dropVars.SetItems(var_choices)
        idx = self.sorted_var_names.index(var) if var else 0
        self.dropVars.SetSelection(idx)

    def refresh_vars(self):
        config_dlg.ConfigDlg.update_var_dets(self)
        
    def get_var(self):
        idx = self.dropVars.GetSelection()
        var = self.sorted_var_names[idx]
        var_item = self.dropVars.GetStringSelection()
        return var, var_item
    
    def OnVarsSel(self, event):
        var, choice_item = self.get_var()
        var_name, var_label = lib.extract_var_choice_dets(choice_item)
        unused, tbl_filt = lib.get_tbl_filt(self.dbe, self.db, self.tbl)
        where_filt, unused = lib.get_tbl_filts(tbl_filt)
        obj_quoter = getdata.get_obj_quoter_func(self.dbe)
        s = """SELECT %(var)s
            FROM %(tbl)s 
            %(where_filt)s
            ORDER BY %(var)s""" % {"var": obj_quoter(var), 
                                   "tbl": obj_quoter(self.tbl),
                                   "where_filt": where_filt}
        self.cur.execute(s)
        vals = [x[0] for x in self.cur.fetchall()]
        dlg = HistoDlg(parent=self, var_label=var_label, vals=vals)
        dlg.ShowModal()
        event.Skip()
    
    def OnRightClickVars(self, event):
        var, choice_item = self.get_var()
        var_name, var_label = lib.extract_var_choice_dets(choice_item)
        updated = projects.set_var_props(choice_item, var_name, var_label, 
                            self.flds, self.var_labels, self.var_notes, 
                            self.var_types, self.val_dics, self.fil_var_dets)
        if updated:
            self.setup_vars(var)

