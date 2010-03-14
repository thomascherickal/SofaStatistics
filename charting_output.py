#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import wx

import my_globals as mg
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
    
    min_data_type = mg.VAR_TYPE_ORD # TODO - wire up for each chart type
    inc_gp_by_select = True
    
    def __init__(self, title, dbe, con_dets, default_dbs=None,
                 default_tbls=None, fil_var_dets="", fil_css="", fil_report="", 
                 fil_script="", takes_range=False):
        if mg.MAX_HEIGHT <= 620:
            myheight = 600
        elif mg.MAX_HEIGHT <= 870:
            myheight = mg.MAX_HEIGHT - 70
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
        self.url_load = True # btn_expand
        self.var_labels, self.var_notes, self.var_types, self.val_dics = \
            projects.get_var_dets(fil_var_dets)
        variables_rc_msg = _("Right click variables to view/edit details")
        config_dlg.add_icon(frame=self)
        szrmain = wx.BoxSizer(wx.VERTICAL)
        # top panel
        self.panel_top = wx.Panel(self)
        szrtop = wx.BoxSizer(wx.VERTICAL)
        self.szr_data = self.get_szr_data(self.panel_top) # mixin
        bxVars = wx.StaticBox(self.panel_top, -1, _("Variables"))
        if not mg.IN_WINDOWS: # http://trac.wxwidgets.org/ticket/9859
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
        szr_chart_btns = wx.BoxSizer(wx.HORIZONTAL)
        # var 1
        lbl_var1 = wx.StaticText(self.panel_top, -1, u"Var 1:")
        lbl_var1.SetFont(self.LABEL_FONT)
        # TODO only want the fields which are numeric? Depends
        self.drop_var1 = wx.Choice(self.panel_top, -1, choices=[], 
                                   size=(300,-1))
        self.drop_var1.Bind(wx.EVT_CHOICE, self.on_var1_sel)
        self.drop_var1.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_var1)
        self.drop_var1.SetToolTipString(variables_rc_msg)
        
        
        
        
        self.sorted_var_names1 = []
        
        self.sorted_var_names2 = []
        
        self.setup_var(self.drop_var1, mg.VAR_1_DEFAULT, self.sorted_var_names1)
        # var 2
        lbl_var2 = wx.StaticText(self.panel_top, -1, u"Var 2:")
        lbl_var2.SetFont(self.LABEL_FONT)
        lbl_var2.Enable(False)
        # TODO - only want the fields which are numeric? Depends
        self.drop_var2 = wx.Choice(self.panel_top, -1, choices=[], 
                                   size=(300,-1))
        self.drop_var2.Bind(wx.EVT_CHOICE, self.on_var2_sel)
        self.drop_var2.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_var2)
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
        self.dropGroupBy = wx.Choice(self.panel_top, -1, choices=[], 
                                     size=(300,-1))
        self.dropGroupBy.Bind(wx.EVT_CHOICE, self.on_group_by_sel)
        self.dropGroupBy.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_group_by)
        self.dropGroupBy.SetToolTipString(variables_rc_msg)
        self.setup_group_by()
        self.lblchop_warning = wx.StaticText(self.panel_top, -1, "")
        szrVarsTopRightTop.Add(self.lblGroupBy, 0, wx.RIGHT|wx.TOP, 5)
        szrVarsTopRightTop.Add(self.dropGroupBy, 0, wx.GROW)
        szrVarsTopRightTop.Add(self.lblchop_warning, 1, wx.TOP|wx.RIGHT, 5)
        # group by A
        self.lblGroupA = wx.StaticText(self.panel_top, -1, _("Group A:"))
        self.dropGroupA = wx.Choice(self.panel_top, -1, choices=[], 
                                    size=(200,-1))
        self.dropGroupA.Bind(wx.EVT_CHOICE, self.on_group_by_a_sel)
        # group by B
        self.lblGroupB = wx.StaticText(self.panel_top, -1, _("Group B:"))
        self.dropGroupB = wx.Choice(self.panel_top, -1, choices=[], 
                                    size=(200,-1))
        self.dropGroupB.Bind(wx.EVT_CHOICE, self.on_group_by_b_sel)
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
        szrtop.Add(self.szr_data, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szrtop.Add(szrVars, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        self.panel_top.SetSizer(szrtop)
        szrtop.SetSizeHints(self.panel_top)
        
        
        
        # Charts
        # chart buttons
        self.panel_mid = wx.Panel(self)
        bxcharts = wx.StaticBox(self.panel_mid, -1, _("Chart Types"))
        self.szrmid = wx.StaticBoxSizer(bxcharts, wx.VERTICAL)
        self.setup_chart_btns(szr_chart_btns)
        self.szrmid.Add(szr_chart_btns, 0, wx.GROW)
        if not mg.IN_WINDOWS: # http://trac.wxwidgets.org/ticket/9859
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
        szr_lower = wx.BoxSizer(wx.HORIZONTAL)
        szr_bottom_left = wx.BoxSizer(wx.VERTICAL)
        # titles, subtitles
        szr_bottom = wx.BoxSizer(wx.VERTICAL)
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
        self.szr_config_bottom, self.szr_config_top = \
            self.get_misc_config_szrs(self.panel_bottom) # mixin                         
        self.szrOutputButtons = self.get_szrOutputBtns(self.panel_bottom, 
                                                       inc_clear=False) # mixin
        self.html = full_html.FullHTML(self.panel_bottom, size=(200, 150))
        html2show = _("<p>Waiting for a report to be run.</p>")
        self.html.show_html(html2show)
        szr_bottom_left.Add(self.html, 1, wx.GROW|wx.BOTTOM, 5)
        szr_bottom_left.Add(self.szr_config_top, 0, wx.GROW)
        szr_bottom_left.Add(self.szr_config_bottom, 0, wx.GROW)
        szr_lower.Add(szr_bottom_left, 1, wx.GROW)
        szr_lower.Add(self.szrOutputButtons, 0, wx.GROW|wx.LEFT, 10)
        szr_bottom.Add(szrTitles, 0, wx.GROW|wx.ALL, 10)
        szr_bottom.Add(szr_lower, 2, wx.GROW|wx.ALL, 10)
        self.add_other_var_opts()
        self.panel_bottom.SetSizer(szr_bottom)
        szr_bottom.SetSizeHints(self.panel_bottom)
        # assemble entire frame
        szrmain.Add(self.panel_top, 0, wx.GROW)
        szrmain.Add(self.panel_mid, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szrmain.Add(self.panel_bottom, 1, wx.GROW)
        self.SetAutoLayout(True)
        self.SetSizer(szrmain)
        self.SetMinSize((930,600))
        self.Layout()
    
    def setup_chart_btns(self, szr_chart_btns):
        # bar charts
        bmp_btn_bar_chart = wx.Image(os.path.join(mg.SCRIPT_PATH, u"images", 
                                                  u"bar_chart.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_bar_chart = wx.BitmapButton(self.panel_mid, -1, 
                                             bmp_btn_bar_chart)
        self.btn_bar_chart.Bind(wx.EVT_BUTTON, self.on_btn_bar_chart)
        self.btn_bar_chart.SetToolTipString(_("Make Bar Chart"))
        szr_chart_btns.Add(self.btn_bar_chart)
        # clustered bar charts
        bmp_btn_clustered_bar_chart = \
                            wx.Image(os.path.join(mg.SCRIPT_PATH, u"images", 
                                                  u"clustered_bar_chart.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_clustered_bar_chart = wx.BitmapButton(self.panel_mid, -1, 
                                             bmp_btn_clustered_bar_chart)
        self.btn_clustered_bar_chart.Bind(wx.EVT_BUTTON, 
                                          self.on_btn_clustered_bar_chart)
        self.btn_clustered_bar_chart.SetToolTipString(_("Make Clustered Bar "
                                                        "Chart"))
        szr_chart_btns.Add(self.btn_clustered_bar_chart)
        # pie charts
        bmp_btn_pie_chart = wx.Image(os.path.join(mg.SCRIPT_PATH, u"images", 
                                                  u"pie_chart.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_pie_chart = wx.BitmapButton(self.panel_mid, -1, 
                                             bmp_btn_pie_chart)
        self.btn_pie_chart.Bind(wx.EVT_BUTTON, self.on_btn_chart)
        self.btn_pie_chart.SetToolTipString(_("Make Pie Chart"))
        szr_chart_btns.Add(self.btn_pie_chart)
        # line charts
        bmp_btn_line_chart = wx.Image(os.path.join(mg.SCRIPT_PATH, u"images", 
                                                   u"line_chart.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_line_chart = wx.BitmapButton(self.panel_mid, -1, 
                                              bmp_btn_line_chart)
        self.btn_line_chart.Bind(wx.EVT_BUTTON, self.on_btn_chart)
        self.btn_line_chart.SetToolTipString(_("Make Line Chart"))
        szr_chart_btns.Add(self.btn_line_chart)
        # area charts
        bmp_btn_area_chart = wx.Image(os.path.join(mg.SCRIPT_PATH, u"images", 
                                                   u"area_chart.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_area_chart = wx.BitmapButton(self.panel_mid, -1, 
                                              bmp_btn_area_chart)
        self.btn_area_chart.Bind(wx.EVT_BUTTON, self.on_btn_chart)
        self.btn_area_chart.SetToolTipString(_("Make Area Chart"))
        szr_chart_btns.Add(self.btn_area_chart)
        # scatterplots
        bmp_btn_scatterplot = wx.Image(os.path.join(mg.SCRIPT_PATH, u"images", 
                                                    u"scatterplot.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_scatterplot = wx.BitmapButton(self.panel_mid, -1, 
                                               bmp_btn_scatterplot)
        self.btn_scatterplot.Bind(wx.EVT_BUTTON, self.on_btn_chart)
        self.btn_scatterplot.SetToolTipString(_("Make Scatterplot"))
        szr_chart_btns.Add(self.btn_scatterplot)
        # histograms
        bmp_btn_histogram = wx.Image(os.path.join(mg.SCRIPT_PATH, u"images", 
                                                  u"histogram.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_histogram = wx.BitmapButton(self.panel_mid, -1, 
                                             bmp_btn_histogram)
        self.btn_histogram.Bind(wx.EVT_BUTTON, self.on_btn_chart)
        self.btn_histogram.SetToolTipString(_("Make Histogram"))
        szr_chart_btns.Add(self.btn_histogram)
        if not mg.IN_WINDOWS:
            hand = wx.StockCursor(wx.CURSOR_HAND)
            self.btn_bar_chart.SetCursor(hand)
            self.btn_clustered_bar_chart.SetCursor(hand)
            self.btn_pie_chart.SetCursor(hand)
            self.btn_line_chart.SetCursor(hand)
            self.btn_area_chart.SetCursor(hand)
            self.btn_scatterplot.SetCursor(hand)
            self.btn_histogram.SetCursor(hand)
    
    def on_btn_bar_chart(self, event):
        if self.panel_displayed == self.panel_bar_chart:
            return
        else:
            self.panel_displayed.Show(False)
        self.szrmid.Remove(self.panel_displayed)
        self.szrmid.Add(self.panel_bar_chart, 0, wx.GROW)
        self.panel_displayed = self.panel_bar_chart
        self.panel_bar_chart.Show(True)
        self.panel_mid.Layout() # self.Layout() doesn't work in Windows

    def on_btn_clustered_bar_chart(self, event):
        if self.panel_displayed == self.panel_clustered_bar_chart:
            return
        else:
            self.panel_displayed.Show(False)
        self.szrmid.Remove(self.panel_displayed)
        self.szrmid.Add(self.panel_clustered_bar_chart, 0, wx.GROW)
        self.panel_displayed = self.panel_clustered_bar_chart
        self.panel_clustered_bar_chart.Show(True)
        self.panel_mid.Layout()

    def on_btn_chart(self, event):
        wx.MessageBox(u"Charting is under construction")
    
    def on_btn_run(self, event):
        wx.MessageBox(u"Charting is under construction")
        
    def on_btn_export(self, event):
        wx.MessageBox(u"Charting is under construction")
    
    def on_var1_sel(self, event):
        pass
        
    def on_var2_sel(self, event):
        pass
    
    def add_other_var_opts(self):
        pass

    def on_rclick_var1(self, event):
        self.on_rclick_var(self.drop_var1, self.sorted_var_names1)
        
    def on_rclick_var2(self, event):
        self.on_rclick_var(self.drop_var2, self.sorted_var_names2)
        
    def on_rclick_var(self, drop_var, sorted_var_names):
        var_name, choice_item = self.get_var_dets(drop_var, sorted_var_names)
        var_label = lib.get_item_label(self.var_labels, var_name)
        updated = projects.set_var_props(choice_item, var_name, var_label, 
                            self.flds, self.var_labels, self.var_notes, 
                            self.var_types, self.val_dics, self.fil_var_dets)
        if updated:
            self.refresh_vars()
    
    def refresh_vars(self):
        var_gp, var_name1 = self.get_vars() # , var_name2
        self.setup_group_by(var_gp)
        self.setup_var(self.drop_var1, mg.VAR_1_DEFAULT, self.sorted_var_names1, 
                       var_name1)
        #self.setup_var(self.drop_var2, mg.VAR_2_DEFAULT, self.sorted_var_names2,
        #       var_name2)
        self.update_defaults()

    def on_database_sel(self, event):
        """
        Reset dbe, database, cursor, tables, table, tables dropdown, 
            fields, has_unique, and idxs after a database selection.
        """
        config_dlg.ConfigDlg.on_database_sel(self, event)
        # now update var dropdowns
        self.update_var_dets()
        self.setup_group_by()
        self.setup_var(self.drop_var1, mg.VAR_1_DEFAULT, self.sorted_var_names1)
        #self.setup_var(self.drop_var2, mg.VAR_2_DEFAULT, self.sorted_var_names2)
        self.setup_group_dropdowns()
                
    def on_table_sel(self, event):
        "Reset key data details after table selection."       
        config_dlg.ConfigDlg.on_table_sel(self, event)
        # now update var dropdowns
        self.update_var_dets()
        self.setup_group_by()
        self.setup_var(self.drop_var1, mg.VAR_1_DEFAULT, self.sorted_var_names1)
        #self.setup_var(self.drop_var2, mg.VAR_2_DEFAULT, self.sorted_var_names2)
        self.setup_group_dropdowns()
    
    def on_var_dets_file_lost_focus(self, event):
        """
        Want to retain already selected item - even though label and even 
            position may have changed.
        """
        val_a, val_b = self.get_vals()
        var_gp, var_name1, var_name2 = self.get_vars()
        config_dlg.ConfigDlg.on_var_dets_file_lost_focus(self, event)
        self.setup_group_by(var_gp)
        self.setup_var(self.drop_var1, mg.VAR_1_DEFAULT, self.sorted_var_names1, 
                       var_name1)
        #self.setup_var(self.drop_var2, mg.VAR_2_DEFAULT, self.sorted_var_names2, 
        #               var_name2)
        self.setup_group_dropdowns(val_a, val_b)
        self.update_defaults()
        
    def on_btn_var_dets_path(self, event):
        """
        Want to retain already selected item - even though label and even 
            position may have changed.
        """
        val_a, val_b = self.get_vals()
        var_gp, var_nam1, var_name2 = self.get_vars()
        config_dlg.ConfigDlg.on_btn_var_dets_path(self, event)
        self.setup_group_by(var_gp)
        self.setup_var(self.drop_var1, mg.VAR_1_DEFAULT, self.sorted_var_names1, 
                       var_name1)
        #self.setup_var(self.drop_var2, mg.VAR_2_DEFAULT, self.sorted_var_names2, 
        #               var_name2)
        self.setup_group_dropdowns(val_a, val_b)
        self.update_defaults()
    
    def get_vars(self):
        """
        self.sorted_var_names_by and self.sorted_var_names1 and 2 are set when 
            dropdowns are set (and only changed when reset).
        """
        var_name1, unused = self.get_var_dets(self.drop_var1, 
                                              self.sorted_var_names1)
        #var_name2, unused = self.get_var_dets(self.drop_var2, 
        #                                      self.sorted_var_names2)
        var_gp, unused = self.get_group_by()
        return var_gp, var_name1 #, var_name2
    
    def update_defaults(self):
        mg.GROUP_BY_DEFAULT = self.dropGroupBy.GetStringSelection()
        mg.VAR_1_DEFAULT = self.drop_var1.GetStringSelection()
        mg.VAR_2_DEFAULT = self.drop_var2.GetStringSelection()
        mg.VAL_A_DEFAULT = self.dropGroupA.GetStringSelection()
        mg.VAL_B_DEFAULT = self.dropGroupB.GetStringSelection()
   
    def get_drop_vals(self):
        """
        Get values from main drop downs.
        Returns var_gp_numeric, var_gp, label_gp, val_a, label_a, val_b, 
            label_b, var_1, label_1, var_1, label_1.
        """
        selection_idx_gp = self.dropGroupBy.GetSelection()
        var_gp = self.sorted_var_names_by[selection_idx_gp]
        label_gp = lib.get_item_label(item_labels=self.var_labels, 
                                      item_val=var_gp)
        var_gp_numeric = self.flds[var_gp][mg.FLD_BOLNUMERIC]
        # Now the a and b choices under the group
        val_dic = self.val_dics.get(var_gp, {})
        selection_idx_a = self.dropGroupA.GetSelection()
        val_a_raw = self.gp_vals_sorted[selection_idx_a]
        val_a = lib.any2unicode(val_a_raw)
        label_a = lib.get_item_label(item_labels=val_dic, 
                                     item_val=val_a_raw)
        selection_idx_b = self.dropGroupB.GetSelection()
        val_b_raw = self.gp_vals_sorted[selection_idx_b]
        val_b = lib.any2unicode(val_b_raw)
        label_b = lib.get_item_label(item_labels=val_dic, 
                                     item_val=val_b_raw)
        # the other variable(s)
        selection_idx_1 = self.drop_var1.GetSelection()
        var_1 = self.sorted_var_names1[selection_idx_1]
        label_1 = lib.get_item_label(item_labels=self.var_labels, 
                                     item_val=var_1)
        selection_idx_2 = self.drop_var2.GetSelection()
        var_2 = self.sorted_var_names2[selection_idx_2]
        label_2 = lib.get_item_label(item_labels=self.var_labels, 
                                     item_val=var_2)
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
            val_dic = self.val_dics.get(var_gp, {})
            selection_idx_a = self.dropGroupA.GetSelection()
            val_a = self.vals_with_labels[selection_idx_a]
            selection_idx_b = self.dropGroupB.GetSelection()
            val_b = self.vals_with_labels[selection_idx_b]
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
