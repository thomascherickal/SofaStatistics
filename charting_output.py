#! /usr/bin/env python
# -*- coding: utf-8 -*-

import wx

import my_globals
import lib
import config_dlg
import full_html
import indep2var
import projects


class PageBarChart(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.SetBackgroundColour("red")
        t = wx.StaticText(self, -1, "This is a PageOne object", (20,20))

class DlgCharting(indep2var.DlgIndep2VarConfig):
    
    min_data_type = my_globals.VAR_TYPE_ORD # TODO - wire up for each chart type
    inc_gp_by_select = True
    
    def __init__(self, title, dbe, con_dets, default_dbs=None,
                 default_tbls=None, fil_var_dets="", fil_css="", fil_report="", 
                 fil_script="", takes_range=False):
        wx.Dialog.__init__(self, parent=None, id=-1, title=title, 
                           pos=(200, 0), 
                           style=wx.MINIMIZE_BOX | wx.MAXIMIZE_BOX | \
                           wx.RESIZE_BORDER | wx.SYSTEM_MENU | \
                           wx.CAPTION | wx.CLOSE_BOX | \
                           wx.CLIP_CHILDREN)
        self.dbe = dbe
        self.con_dets = con_dets
        self.default_dbs = default_dbs
        self.default_tbls = default_tbls
        self.fil_var_dets = fil_var_dets
        self.fil_css = fil_css
        self.fil_report = fil_report
        self.fil_script = fil_script
        self.takes_range = takes_range
        self.url_load = True # btnExpand
        self.var_labels, self.var_notes, self.var_types, self.val_dics = \
            projects.get_var_dets(fil_var_dets)
        variables_rc_msg = _("Right click variables to view/edit details")
        # set up panel for frame
        self.panel = wx.Panel(self)
        #self.panel.SetBackgroundColour(wx.Colour(205, 217, 215))
        config_dlg.add_icon(frame=self)
        self.szrData, self.szrConfigBottom, self.szrConfigTop = \
                                    self.get_gen_config_szrs(self.panel) # mixin
        self.szrOutputButtons = self.get_szrOutputBtns(self.panel, 
                                                       inc_clear=False) # mixin
        szrMain = wx.BoxSizer(wx.VERTICAL)
        bxVars = wx.StaticBox(self.panel, -1, _("Variables"))
        if not my_globals.IN_WINDOWS: # http://trac.wxwidgets.org/ticket/9859
            bxVars.SetToolTipString(variables_rc_msg)
        szrVars = wx.StaticBoxSizer(bxVars, wx.VERTICAL)
        szrVarsTop = wx.BoxSizer(wx.HORIZONTAL)
        szrVarsBottom = wx.BoxSizer(wx.HORIZONTAL)
        self.szrVarsTopLeft = wx.BoxSizer(wx.VERTICAL)
        szrVarsTopRight = wx.BoxSizer(wx.VERTICAL)
        szrVarsTopLeftTop = wx.BoxSizer(wx.HORIZONTAL)
        szrVarsTopLeftMid = wx.BoxSizer(wx.HORIZONTAL)
        szrVarsTopRightTop = wx.BoxSizer(wx.HORIZONTAL)
        szrVarsTopRightBottom = wx.BoxSizer(wx.HORIZONTAL)
        szrTitles = wx.BoxSizer(wx.HORIZONTAL)
        szrBottom = wx.BoxSizer(wx.HORIZONTAL)
        szrBottomLeft = wx.BoxSizer(wx.VERTICAL)
        szrCharts = wx.BoxSizer(wx.VERTICAL)
        # var 1
        lbl_var1 = wx.StaticText(self.panel, -1, u"Var 1:")
        lbl_var1.SetFont(self.LABEL_FONT)
        
        # only want the fields which are numeric? Depends
        
        self.drop_var1 = wx.Choice(self.panel, -1, choices=[], size=(300, -1))
        self.drop_var1.Bind(wx.EVT_CHOICE, self.OnVar1Sel)
        self.drop_var1.Bind(wx.EVT_CONTEXT_MENU, self.OnRightClickVar1)
        self.drop_var1.SetToolTipString(variables_rc_msg)
        self.sorted_var_names1 = []
        self.setup_var(self.drop_var1, my_globals.VAR_1_DEFAULT, 
                       self.sorted_var_names1)
        # var 2
        lbl_var2 = wx.StaticText(self.panel, -1, u"Var 2:")
        lbl_var2.SetFont(self.LABEL_FONT)
        lbl_var2.Enable(False)
        
        # only want the fields which are numeric? Depends
        
        self.drop_var2 = wx.Choice(self.panel, -1, choices=[], size=(300, -1))
        self.drop_var2.Bind(wx.EVT_CHOICE, self.OnVar2Sel)
        self.drop_var2.Bind(wx.EVT_CONTEXT_MENU, self.OnRightClickVar2)
        self.drop_var2.SetToolTipString(variables_rc_msg)
        self.sorted_var_names2 = []
        self.drop_var2.SetItems([])
        self.drop_var2.Enable(False)
        # layout
        szrVarsTopLeftTop.Add(lbl_var1, 0, wx.TOP|wx.RIGHT, 5)
        szrVarsTopLeftTop.Add(self.drop_var1, 0, wx.RIGHT|wx.TOP, 5)
        szrVarsTopLeftMid.Add(lbl_var2, 0, wx.TOP|wx.RIGHT, 5)
        szrVarsTopLeftMid.Add(self.drop_var2, 0, wx.RIGHT|wx.TOP, 5)
        self.szrVarsTopLeft.Add(szrVarsTopLeftTop, 0)
        self.szrVarsTopLeft.Add(szrVarsTopLeftMid, 0)
        # group by
        self.lblGroupBy = wx.StaticText(self.panel, -1, _("Group By:"))
        self.lblGroupBy.SetFont(self.LABEL_FONT)
        self.dropGroupBy = wx.Choice(self.panel, -1, choices=[], size=(300, -1))
        self.dropGroupBy.Bind(wx.EVT_CHOICE, self.OnGroupBySel)
        self.dropGroupBy.Bind(wx.EVT_CONTEXT_MENU, self.OnRightClickGroupBy)
        self.dropGroupBy.SetToolTipString(variables_rc_msg)
        self.setup_group_by()
        self.lblchop_warning = wx.StaticText(self.panel, -1, "")
        szrVarsTopRightTop.Add(self.lblGroupBy, 0, wx.RIGHT|wx.TOP, 5)
        szrVarsTopRightTop.Add(self.dropGroupBy, 0, wx.GROW)
        szrVarsTopRightTop.Add(self.lblchop_warning, 1, wx.TOP|wx.RIGHT, 5)
        # group by A
        self.lblGroupA = wx.StaticText(self.panel, -1, _("Group A:"))
        self.dropGroupA = wx.Choice(self.panel, -1, choices=[], size=(200, -1))
        self.dropGroupA.Bind(wx.EVT_CHOICE, self.OnGroupByASel)
        # group by B
        self.lblGroupB = wx.StaticText(self.panel, -1, _("Group B:"))
        self.dropGroupB = wx.Choice(self.panel, -1, choices=[], size=(200, -1))
        self.dropGroupB.Bind(wx.EVT_CHOICE, self.OnGroupByBSel)
        self.setup_group_dropdowns()
        szrVarsTopRightBottom.Add(self.lblGroupA, 0, wx.RIGHT|wx.TOP, 5)
        szrVarsTopRightBottom.Add(self.dropGroupA, 0, wx.RIGHT, 5)
        szrVarsTopRightBottom.Add(self.lblGroupB, 0, wx.RIGHT|wx.TOP, 5)
        szrVarsTopRightBottom.Add(self.dropGroupB, 0)
        szrVarsTopRight.Add(szrVarsTopRightTop, 1, wx.GROW)
        szrVarsTopRight.Add(szrVarsTopRightBottom, 0, wx.GROW|wx.TOP, 5)
        szrVarsTop.Add(self.szrVarsTopLeft, 0)
        lnVert = wx.StaticLine(self.panel, style=wx.LI_VERTICAL) 
        szrVarsTop.Add(lnVert, 0, wx.GROW|wx.LEFT|wx.RIGHT, 5)
        szrVarsTop.Add(szrVarsTopRight, 0)
        szrVars.Add(szrVarsTop, 0)      
        szrVars.Add(szrVarsBottom, 0, wx.GROW)
        
        # charts
        
        
        

        
        
        
        
        
        
        # titles, subtitles
        lblTitles = wx.StaticText(self.panel, -1, _("Title:"))
        lblTitles.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.txtTitles = wx.TextCtrl(self.panel, -1, size=(250,40), 
                                     style=wx.TE_MULTILINE)
        lblSubtitles = wx.StaticText(self.panel, -1, _("Subtitle:"))
        lblSubtitles.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, 
                                          wx.BOLD))
        self.txtSubtitles = wx.TextCtrl(self.panel, -1, size=(250,40), 
                                        style=wx.TE_MULTILINE)
        szrTitles.Add(lblTitles, 0, wx.RIGHT, 5)
        szrTitles.Add(self.txtTitles, 0, wx.RIGHT, 10)
        szrTitles.Add(lblSubtitles, 0, wx.RIGHT, 5)
        szrTitles.Add(self.txtSubtitles, 0)
        # bottom
        self.html = full_html.FullHTML(self.panel, size=(200, 150))
        html2show = _("<p>Waiting for a report to be run.</p>")
        self.html.show_html(html2show)
        szrBottomLeft.Add(self.html, 1, wx.GROW|wx.BOTTOM, 5)
        szrBottomLeft.Add(self.szrConfigTop, 0, wx.GROW)
        szrBottomLeft.Add(self.szrConfigBottom, 0, wx.GROW)
        szrBottom.Add(szrBottomLeft, 1, wx.GROW)
        szrBottom.Add(self.szrOutputButtons, 0, wx.GROW|wx.LEFT, 10)
        szrMain.Add(self.szrData, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szrMain.Add(szrVars, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szrMain.Add(szrCharts, 0, wx.GROW)
        szrMain.Add(szrTitles, 0, wx.ALL, 10)
        szrMain.Add(szrBottom, 2, wx.GROW|wx.ALL, 10)
        self.add_other_var_opts()
        self.panel.SetSizer(szrMain)
        szrMain.SetSizeHints(self)
        
    def OnVar1Sel(self, event):
        pass
        
    def OnVar2Sel(self, event):
        pass
    
    def add_other_var_opts(self):
        pass

    def OnRightClickVar1(self, event):
        self.OnRightClickVar(self.drop_var1, self.sorted_var_names1)
        
    def OnRightClickVar2(self, event):
        self.OnRightClickVar(self.drop_var2, self.sorted_var_names2)
        
    def OnRightClickVar(self, drop_var, sorted_var_names):
        var_name, choice_item = self.get_var_dets(drop_var, sorted_var_names)
        var_name, var_label = lib.extract_var_choice_dets(choice_item)
        updated = projects.set_var_props(choice_item, var_name, var_label, 
                            self.flds, self.var_labels, self.var_notes, 
                            self.var_types, self.val_dics, self.fil_var_dets)
        if updated:
            self.refresh_vars()
    
    def refresh_vars(self):
        var_gp, var_name1, var_name2 = self.get_vars()
        self.setup_group_by(var_gp)
        self.setup_var(self.drop_var1, my_globals.VAR_1_DEFAULT, 
                       self.sorted_var_names1, var_name1)
        self.setup_var(self.drop_var2, my_globals.VAR_2_DEFAULT, 
               self.sorted_var_names2, var_name2)
        self.update_defaults()

    def OnDatabaseSel(self, event):
        """
        Reset dbe, database, cursor, tables, table, tables dropdown, 
            fields, has_unique, and idxs after a database selection.
        """
        config_dlg.ConfigDlg.OnDatabaseSel(self, event)
        # now update var dropdowns
        self.update_var_dets()
        self.setup_group_by()
        self.setup_var(self.drop_var1, my_globals.VAR_1_DEFAULT, 
                       self.sorted_var_names1)
        self.setup_var(self.drop_var2, my_globals.VAR_2_DEFAULT, 
                       self.sorted_var_names2)
        self.setup_group_dropdowns()
                
    def OnTableSel(self, event):
        "Reset key data details after table selection."       
        config_dlg.ConfigDlg.OnTableSel(self, event)
        # now update var dropdowns
        self.update_var_dets()
        self.setup_group_by()
        self.setup_var(self.drop_var1, my_globals.VAR_1_DEFAULT, 
                       self.sorted_var_names1)
        self.setup_var(self.drop_var2, my_globals.VAR_2_DEFAULT, 
                       self.sorted_var_names2)
        self.setup_group_dropdowns()
    
    def OnVarDetsFileLostFocus(self, event):
        """
        Want to retain already selected item - even though label and even 
            position may have changed.
        """
        val_a, val_b = self.GetVals()
        var_gp, var_name1, var_name2 = self.get_vars()
        config_dlg.ConfigDlg.OnVarDetsFileLostFocus(self, event)
        self.setup_group_by(var_gp)
        self.setup_var(self.drop_var1, my_globals.VAR_1_DEFAULT, 
                       self.sorted_var_names1, var_name1)
        self.setup_var(self.drop_var2, my_globals.VAR_2_DEFAULT, 
                       self.sorted_var_names2, var_name2)
        self.setup_group_dropdowns(val_a, val_b)
        self.update_defaults()
        
    def OnButtonVarDetsPath(self, event):
        """
        Want to retain already selected item - even though label and even 
            position may have changed.
        """
        val_a, val_b = self.GetVals()
        var_gp, var_nam1, var_name2 = self.get_vars()
        config_dlg.ConfigDlg.OnButtonVarDetsPath(self, event)
        self.setup_group_by(var_gp)
        self.setup_var(self.drop_var1, my_globals.VAR_1_DEFAULT, 
                       self.sorted_var_names1, var_name1)
        self.setup_var(self.drop_var2, my_globals.VAR_2_DEFAULT, 
                       self.sorted_var_names2, var_name2)
        self.setup_group_dropdowns(val_a, val_b)
        self.update_defaults()
    
    def get_vars(self):
        """
        self.sorted_var_names_by and self.sorted_var_names1 and 2 are set when 
            dropdowns are set (and only changed when reset).
        """
        var_name1, unused = self.get_var_dets(self.drop_var1, 
                                              self.sorted_var_names1)
        var_name2, unused = self.get_var_dets(self.drop_var2, 
                                              self.sorted_var_names2)
        var_gp, unused = self.get_group_by()
        return var_gp, var_name1, var_name2
    
    def update_defaults(self):
        my_globals.GROUP_BY_DEFAULT = self.dropGroupBy.GetStringSelection()
        my_globals.VAR_1_DEFAULT = self.drop_var1.GetStringSelection()
        my_globals.VAR_2_DEFAULT = self.drop_var2.GetStringSelection()
        my_globals.VAL_A_DEFAULT = self.dropGroupA.GetStringSelection()
        my_globals.VAL_B_DEFAULT = self.dropGroupB.GetStringSelection()
   
    def get_drop_vals(self):
        """
        Get values from main drop downs.
        Returns var_gp_numeric, var_gp, label_gp, val_a, label_a, val_b, 
            label_b, var_1, label_1, var_1, label_1.
        """
        choice_gp_text = self.dropGroupBy.GetStringSelection()
        var_gp, label_gp = lib.extract_var_choice_dets(choice_gp_text)
        choice_a_text = self.dropGroupA.GetStringSelection()
        val_a, label_a = lib.extract_var_choice_dets(choice_a_text)
        choice_b_text = self.dropGroupB.GetStringSelection()
        val_b, label_b = lib.extract_var_choice_dets(choice_b_text)
        choice_1_text = self.drop_var1.GetStringSelection()
        var_1, label_1 = lib.extract_var_choice_dets(choice_1_text)
        choice_2_text = self.drop_var2.GetStringSelection()
        var_2, label_2 = lib.extract_var_choice_dets(choice_2_text)
        var_gp_numeric = self.flds[var_gp][my_globals.FLD_BOLNUMERIC]
        return var_gp_numeric, var_gp, label_gp, val_a, label_a, \
            val_b, label_b, var_1, label_1, var_2, label_2

    def update_phrase(self):
        pass

    def test_config_ok(self):
        """
        Are the appropriate selections made to enable an analysis to be run?
        """
        # main and group by averaged variables cannot be the same
        if self.dropGroupBy.GetStringSelection() == \
                self.drop_var1.GetStringSelection():
            wx.MessageBox(_("Variable 1 and the Grouped By Variable cannot be "
                            "the same"))
            return False
        if self.dropGroupBy.GetStringSelection() == \
                self.drop_var2.GetStringSelection():
            wx.MessageBox(_("Variable 2 and the Grouped By Variable cannot be "
                            "the same"))
            return False
        if self.drop_var1.GetStringSelection() == \
                self.drop_var2.GetStringSelection():
            wx.MessageBox(_("Variable 1 and 2 cannot be the same"))
            return False
        # group A and B cannot be the same
        if self.dropGroupA.GetStringSelection() == \
                self.dropGroupB.GetStringSelection():
            wx.MessageBox(_("Group A and Group B must be different"))
            return False
        if self.takes_range:
            var_gp_numeric, var_gp, unused, unused, unused, unused, unused, \
                unused, unused, unused, unused = self.get_drop_vals()
            # group a must be lower than group b
            val_a, unused = lib.extract_var_choice_dets(
                                        self.dropGroupA.GetStringSelection())
            val_b, unused = lib.extract_var_choice_dets(
                                        self.dropGroupB.GetStringSelection())
            if var_gp_numeric:
                # NB SQLite could have a string in a numeric field
                # could cause problems even if the string value is not one of 
                # the ones being tested as a range boundary here.
                try:
                    val_a = float(val_a)
                    val_b = float(val_b)
                except ValueError:
                    wx.MessageBox(u"Both values must be numeric.  "
                        u"Values selected were %s and %s" % (val_a, val_b))
                    return False
            if  val_a > val_b:
                wx.MessageBox(_("Group A must be lower than Group B"))
                return False
        return True
