#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
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
        if my_globals.MAX_HEIGHT <= 620:
            myheight = 600
        elif my_globals.MAX_HEIGHT <= 870:
            myheight = my_globals.MAX_HEIGHT - 70
        else:
            myheight = 800
        wx.Dialog.__init__(self, parent=None, id=-1, title=title, 
                           pos=(200, 0), size=(1000,myheight),
                           style=wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX| \
                           wx.RESIZE_BORDER|wx.SYSTEM_MENU| \
                           wx.CAPTION|wx.CLOSE_BOX|wx.CLIP_CHILDREN)
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
        config_dlg.add_icon(frame=self)
        szrmain = wx.BoxSizer(wx.VERTICAL)
        # top panel
        self.panel_top = wx.Panel(self)
        szrtop = wx.BoxSizer(wx.VERTICAL)
        self.szrData = self.get_szrData(self.panel_top) # mixin
        bxVars = wx.StaticBox(self.panel_top, -1, _("Variables"))
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
        szrchart_btns = wx.BoxSizer(wx.HORIZONTAL)
        # var 1
        lbl_var1 = wx.StaticText(self.panel_top, -1, u"Var 1:")
        lbl_var1.SetFont(self.LABEL_FONT)
        # TODO only want the fields which are numeric? Depends
        self.drop_var1 = wx.Choice(self.panel_top, -1, choices=[], 
                                   size=(300,-1))
        self.drop_var1.Bind(wx.EVT_CHOICE, self.OnVar1Sel)
        self.drop_var1.Bind(wx.EVT_CONTEXT_MENU, self.OnRightClickVar1)
        self.drop_var1.SetToolTipString(variables_rc_msg)
        self.sorted_var_names1 = []
        self.setup_var(self.drop_var1, my_globals.VAR_1_DEFAULT, 
                       self.sorted_var_names1)
        # var 2
        lbl_var2 = wx.StaticText(self.panel_top, -1, u"Var 2:")
        lbl_var2.SetFont(self.LABEL_FONT)
        lbl_var2.Enable(False)
        # TODO - only want the fields which are numeric? Depends
        self.drop_var2 = wx.Choice(self.panel_top, -1, choices=[], size=(300, -1))
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
        self.lblGroupBy = wx.StaticText(self.panel_top, -1, _("Group By:"))
        self.lblGroupBy.SetFont(self.LABEL_FONT)
        self.dropGroupBy = wx.Choice(self.panel_top, -1, choices=[], size=(300, -1))
        self.dropGroupBy.Bind(wx.EVT_CHOICE, self.OnGroupBySel)
        self.dropGroupBy.Bind(wx.EVT_CONTEXT_MENU, self.OnRightClickGroupBy)
        self.dropGroupBy.SetToolTipString(variables_rc_msg)
        self.setup_group_by()
        self.lblchop_warning = wx.StaticText(self.panel_top, -1, "")
        szrVarsTopRightTop.Add(self.lblGroupBy, 0, wx.RIGHT|wx.TOP, 5)
        szrVarsTopRightTop.Add(self.dropGroupBy, 0, wx.GROW)
        szrVarsTopRightTop.Add(self.lblchop_warning, 1, wx.TOP|wx.RIGHT, 5)
        # group by A
        self.lblGroupA = wx.StaticText(self.panel_top, -1, _("Group A:"))
        self.dropGroupA = wx.Choice(self.panel_top, -1, choices=[], size=(200, -1))
        self.dropGroupA.Bind(wx.EVT_CHOICE, self.OnGroupByASel)
        # group by B
        self.lblGroupB = wx.StaticText(self.panel_top, -1, _("Group B:"))
        self.dropGroupB = wx.Choice(self.panel_top, -1, choices=[], size=(200, -1))
        self.dropGroupB.Bind(wx.EVT_CHOICE, self.OnGroupByBSel)
        self.setup_group_dropdowns()
        szrVarsTopRightBottom.Add(self.lblGroupA, 0, wx.RIGHT|wx.TOP, 5)
        szrVarsTopRightBottom.Add(self.dropGroupA, 0, wx.RIGHT, 5)
        szrVarsTopRightBottom.Add(self.lblGroupB, 0, wx.RIGHT|wx.TOP, 5)
        szrVarsTopRightBottom.Add(self.dropGroupB, 0)
        szrVarsTopRight.Add(szrVarsTopRightTop, 1, wx.GROW)
        szrVarsTopRight.Add(szrVarsTopRightBottom, 0, wx.GROW|wx.TOP, 5)
        szrVarsTop.Add(self.szrVarsTopLeft, 0)
        lnVert = wx.StaticLine(self.panel_top, style=wx.LI_VERTICAL) 
        szrVarsTop.Add(lnVert, 0, wx.GROW|wx.LEFT|wx.RIGHT, 5)
        szrVarsTop.Add(szrVarsTopRight, 0)
        szrVars.Add(szrVarsTop, 0)      
        szrVars.Add(szrVarsBottom, 0, wx.GROW)
        # assemble sizer for top panel
        szrtop.Add(self.szrData, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szrtop.Add(szrVars, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        self.panel_top.SetSizer(szrtop)
        szrtop.SetSizeHints(self.panel_top)
        
        
        
        # Charts
        # chart buttons
        self.panel_mid = wx.Panel(self)
        bxcharts = wx.StaticBox(self.panel_mid, -1, _("Chart Types"))
        self.szrmid = wx.StaticBoxSizer(bxcharts, wx.VERTICAL)
        self.setup_chart_btns(szrchart_btns)
        self.szrmid.Add(szrchart_btns, 0, wx.GROW)
        if not my_globals.IN_WINDOWS: # http://trac.wxwidgets.org/ticket/9859
            bxcharts.SetToolTipString(_("Make chart"))
        # Chart Settings
        # bar chart
        self.szr_bar_chart = wx.BoxSizer(wx.VERTICAL)
        self.panel_bar_chart = wx.Panel(self.panel_mid)
        lbl_bar_chart = wx.StaticText(self.panel_bar_chart, -1, 
                            "Bar chart configuration still under construction")
        self.szr_bar_chart.Add(lbl_bar_chart, 1, wx.TOP|wx.BOTTOM, 10)
        self.panel_bar_chart.SetSizer(self.szr_bar_chart)
        self.szr_bar_chart.SetSizeHints(self.panel_bar_chart)
        # clustered bar chart
        self.szr_clustered_bar_chart = wx.BoxSizer(wx.VERTICAL)
        self.panel_clustered_bar_chart = wx.Panel(self.panel_mid)
        lbl_clustered_bar_chart = wx.StaticText(self.panel_clustered_bar_chart, 
                                    -1, "Clustered bar chart "
                                    "configuration still under construction")
        self.szr_clustered_bar_chart.Add(lbl_clustered_bar_chart, 1, 
                                         wx.TOP|wx.BOTTOM, 10)
        self.panel_clustered_bar_chart.SetSizer(self.szr_clustered_bar_chart)
        self.szr_clustered_bar_chart.SetSizeHints(\
                                        self.panel_clustered_bar_chart)
        self.panel_clustered_bar_chart.Show(False)
        # default chart type (bar chart)
        self.panel_displayed = self.panel_bar_chart
        self.szrmid.Add(self.panel_bar_chart, 0, wx.GROW)
        
        self.panel_mid.SetSizer(self.szrmid)
        self.szrmid.SetSizeHints(self.panel_mid)
        # Bottom panel
        self.panel_bottom = wx.Panel(self)
        szrTitles = wx.BoxSizer(wx.HORIZONTAL)
        szrBottom = wx.BoxSizer(wx.HORIZONTAL)
        szrBottomLeft = wx.BoxSizer(wx.VERTICAL)
        # titles, subtitles
        szrbottom = wx.BoxSizer(wx.VERTICAL)
        lblTitles = wx.StaticText(self.panel_bottom, -1, _("Title:"))
        lblTitles.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.txtTitles = wx.TextCtrl(self.panel_bottom, -1, size=(350,40), 
                                     style=wx.TE_MULTILINE)
        lblSubtitles = wx.StaticText(self.panel_bottom, -1, _("Subtitle:"))
        lblSubtitles.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, 
                                          wx.BOLD))
        self.txtSubtitles = wx.TextCtrl(self.panel_bottom, -1, size=(350,40), 
                                        style=wx.TE_MULTILINE)
        szrTitles.Add(lblTitles, 0, wx.RIGHT, 5)
        szrTitles.Add(self.txtTitles, 1, wx.RIGHT, 10)
        szrTitles.Add(lblSubtitles, 0, wx.RIGHT, 5)
        szrTitles.Add(self.txtSubtitles, 1)
        self.szrConfigBottom, self.szrConfigTop = \
            self.get_misc_config_szrs(self.panel_bottom) # mixin                         
        self.szrOutputButtons = self.get_szrOutputBtns(self.panel_bottom, 
                                                       inc_clear=False) # mixin
        self.html = full_html.FullHTML(self.panel_bottom, size=(200, 150))
        html2show = _("<p>Waiting for a report to be run.</p>")
        self.html.show_html(html2show)
        szrBottomLeft.Add(self.html, 1, wx.GROW|wx.BOTTOM, 5)
        szrBottomLeft.Add(self.szrConfigTop, 0, wx.GROW)
        szrBottomLeft.Add(self.szrConfigBottom, 0, wx.GROW)
        szrBottom.Add(szrBottomLeft, 1, wx.GROW)
        szrBottom.Add(self.szrOutputButtons, 0, wx.GROW|wx.LEFT, 10)
        szrbottom.Add(szrTitles, 0, wx.GROW|wx.ALL, 10)
        szrbottom.Add(szrBottom, 2, wx.GROW|wx.ALL, 10)
        self.add_other_var_opts()
        self.panel_bottom.SetSizer(szrbottom)
        szrbottom.SetSizeHints(self.panel_bottom)
        # assemble entire frame
        szrmain.Add(self.panel_top, 0, wx.GROW)
        szrmain.Add(self.panel_mid, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szrmain.Add(self.panel_bottom, 1, wx.GROW)
        self.SetAutoLayout(True)
        self.SetSizer(szrmain)
        self.SetMinSize((930,600))
        self.Layout()
    
    def setup_chart_btns(self, szrchart_btns):
        # bar charts
        bmp_btn_bar_chart = wx.Image(os.path.join(my_globals.SCRIPT_PATH, 
                                                  u"images", u"bar_chart.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_bar_chart = wx.BitmapButton(self.panel_mid, -1, 
                                             bmp_btn_bar_chart)
        self.btn_bar_chart.Bind(wx.EVT_BUTTON, self.OnBtnBarChart)
        self.btn_bar_chart.SetToolTipString(_("Make Bar Chart"))
        szrchart_btns.Add(self.btn_bar_chart)
        # clustered bar charts
        bmp_btn_clustered_bar_chart = \
                            wx.Image(os.path.join(my_globals.SCRIPT_PATH, 
                                      u"images", u"clustered_bar_chart.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_clustered_bar_chart = wx.BitmapButton(self.panel_mid, -1, 
                                             bmp_btn_clustered_bar_chart)
        self.btn_clustered_bar_chart.Bind(wx.EVT_BUTTON, 
                                          self.OnBtnClusteredBarChart)
        self.btn_clustered_bar_chart.SetToolTipString(_("Make Clustered Bar "
                                                        "Chart"))
        szrchart_btns.Add(self.btn_clustered_bar_chart)
        # pie charts
        bmp_btn_pie_chart = wx.Image(os.path.join(my_globals.SCRIPT_PATH, 
                                                  u"images", u"pie_chart.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_pie_chart = wx.BitmapButton(self.panel_mid, -1, 
                                             bmp_btn_pie_chart)
        self.btn_pie_chart.Bind(wx.EVT_BUTTON, self.OnBtnChart)
        self.btn_pie_chart.SetToolTipString(_("Make Pie Chart"))
        szrchart_btns.Add(self.btn_pie_chart)
        # line charts
        bmp_btn_line_chart = wx.Image(os.path.join(my_globals.SCRIPT_PATH, 
                                                  u"images", u"line_chart.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_line_chart = wx.BitmapButton(self.panel_mid, -1, 
                                              bmp_btn_line_chart)
        self.btn_line_chart.Bind(wx.EVT_BUTTON, self.OnBtnChart)
        self.btn_line_chart.SetToolTipString(_("Make Line Chart"))
        szrchart_btns.Add(self.btn_line_chart)
        # area charts
        bmp_btn_area_chart = wx.Image(os.path.join(my_globals.SCRIPT_PATH, 
                                                  u"images", u"area_chart.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_area_chart = wx.BitmapButton(self.panel_mid, -1, 
                                              bmp_btn_area_chart)
        self.btn_area_chart.Bind(wx.EVT_BUTTON, self.OnBtnChart)
        self.btn_area_chart.SetToolTipString(_("Make Area Chart"))
        szrchart_btns.Add(self.btn_area_chart)
        # scatterplots
        bmp_btn_scatterplot = wx.Image(os.path.join(my_globals.SCRIPT_PATH, 
                                              u"images", u"scatterplot.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_scatterplot = wx.BitmapButton(self.panel_mid, -1, 
                                               bmp_btn_scatterplot)
        self.btn_scatterplot.Bind(wx.EVT_BUTTON, self.OnBtnChart)
        self.btn_scatterplot.SetToolTipString(_("Make Scatterplot"))
        szrchart_btns.Add(self.btn_scatterplot)
        # histograms
        bmp_btn_histogram = wx.Image(os.path.join(my_globals.SCRIPT_PATH, 
                                                  u"images", u"histogram.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_histogram = wx.BitmapButton(self.panel_mid, -1, 
                                             bmp_btn_histogram)
        self.btn_histogram.Bind(wx.EVT_BUTTON, self.OnBtnChart)
        self.btn_histogram.SetToolTipString(_("Make Histogram"))
        szrchart_btns.Add(self.btn_histogram)
        if not my_globals.IN_WINDOWS:
            hand = wx.StockCursor(wx.CURSOR_HAND)
            self.btn_bar_chart.SetCursor(hand)
            self.btn_clustered_bar_chart.SetCursor(hand)
            self.btn_pie_chart.SetCursor(hand)
            self.btn_line_chart.SetCursor(hand)
            self.btn_area_chart.SetCursor(hand)
            self.btn_scatterplot.SetCursor(hand)
            self.btn_histogram.SetCursor(hand)
    
    def OnBtnBarChart(self, event):
        if self.panel_displayed == self.panel_bar_chart:
            return
        else:
            self.panel_displayed.Show(False)
        self.szrmid.Remove(self.panel_displayed)
        self.szrmid.Add(self.panel_bar_chart, 0, wx.GROW)
        self.panel_displayed = self.panel_bar_chart
        self.panel_bar_chart.Show(True)
        self.panel_mid.Layout() # self.Layout() doesn't work in Windows

    def OnBtnClusteredBarChart(self, event):
        if self.panel_displayed == self.panel_clustered_bar_chart:
            return
        else:
            self.panel_displayed.Show(False)
        self.szrmid.Remove(self.panel_displayed)
        self.szrmid.Add(self.panel_clustered_bar_chart, 0, wx.GROW)
        self.panel_displayed = self.panel_clustered_bar_chart
        self.panel_clustered_bar_chart.Show(True)
        self.panel_mid.Layout()

    def OnBtnChart(self, event):
        wx.MessageBox(u"Charting is under construction")
    
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
