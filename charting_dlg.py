#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import wx

import my_globals as mg
import lib
import config_dlg
import full_html
import getdata
import indep2var
import projects

OUTPUT_MODULES = ["my_globals as mg", "charting_output", "output", 
                  "getdata"]
cc = config_dlg.get_cc()
dd = getdata.get_dd()

LIMITS_MSG = (u"Only simple and clustered bar charts available in this release."
              u" More coming soon!")

class DlgCharting(indep2var.DlgIndep2VarConfig):

    inc_gp_by_select = True
    
    def __init__(self, title, takes_range=False):
        # see http://old.nabble.com/wx.StaticBoxSizer-td21662703.html
        if mg.MAX_HEIGHT <= 620:
            myheight = 600
        elif mg.MAX_HEIGHT <= 870:
            myheight = mg.MAX_HEIGHT - 70
        else:
            myheight = 800
        wx.Dialog.__init__(self, parent=None, id=-1, title=title, 
                           pos=(mg.HORIZ_OFFSET, 0), size=(1024, myheight),
                           style=wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX|\
                           wx.RESIZE_BORDER|wx.SYSTEM_MENU|wx.CAPTION|\
                           wx.CLIP_CHILDREN)
        self.takes_range = takes_range
        self.url_load = True # btn_expand
        self.var_labels, self.var_notes, self.var_types, self.val_dics = \
                                    lib.get_var_dets(cc[mg.CURRENT_VDTS_PATH])
        variables_rc_msg = _("Right click variables to view/edit details")
        config_dlg.add_icon(frame=self)
        szr_main = wx.BoxSizer(wx.VERTICAL)
        # top panel
        self.panel_top = wx.Panel(self)
        bx_vars = wx.StaticBox(self.panel_top, -1, _("Variables"))
        szr_top = wx.BoxSizer(wx.VERTICAL)
        self.szr_data = self.get_szr_data(self.panel_top) # mixin
        if mg.PLATFORM == mg.LINUX: # http://trac.wxwidgets.org/ticket/9859
            bx_vars.SetToolTipString(variables_rc_msg)
        szr_vars = wx.StaticBoxSizer(bx_vars, wx.VERTICAL)
        szr_vars_top = wx.BoxSizer(wx.HORIZONTAL)
        szr_vars_bottom = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_vars_top_left = wx.BoxSizer(wx.VERTICAL)
        szr_vars_top_right = wx.BoxSizer(wx.VERTICAL)
        szr_vars_top_left_top = wx.BoxSizer(wx.HORIZONTAL)
        szr_vars_top_left_mid = wx.BoxSizer(wx.HORIZONTAL)
        szr_vars_top_right_top = wx.BoxSizer(wx.HORIZONTAL)
        szr_vars_top_right_bottom = wx.BoxSizer(wx.HORIZONTAL)
        szr_chart_btns = wx.BoxSizer(wx.HORIZONTAL)
        # var 1
        self.min_data_type = mg.VAR_TYPE_CAT # needed to set up var 1
        self.lbl_var1 = wx.StaticText(self.panel_top, -1, mg.CHART_VALUES)
        self.lbl_var1.SetFont(self.LABEL_FONT)
        # TODO only want the fields which are numeric? Depends
        self.drop_var1 = wx.Choice(self.panel_top, -1, choices=[], 
                                   size=(300,-1))
        self.drop_var1.Bind(wx.EVT_CHOICE, self.on_var1_sel)
        self.drop_var1.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_var1)
        self.drop_var1.SetToolTipString(variables_rc_msg)
        self.sorted_var_names1 = []
        self.setup_var(self.drop_var1, mg.VAR_1_DEFAULT, self.sorted_var_names1)
        # var 2
        self.lbl_var2 = wx.StaticText(self.panel_top, -1, mg.CHART_BY)
        self.lbl_var2.SetFont(self.LABEL_FONT)
        self.lbl_var2.Enable(False)
        # TODO - only want the fields which are numeric? Depends
        self.drop_var2 = wx.Choice(self.panel_top, -1, choices=[], 
                                   size=(300,-1))
        self.drop_var2.Bind(wx.EVT_CHOICE, self.on_var2_sel)
        self.drop_var2.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_var2)
        self.drop_var2.SetToolTipString(variables_rc_msg)
        self.sorted_var_names2 = []
        self.drop_var2.SetItems([])
        self.drop_var2.Enable(False)
        self.sorted_var_names2 = []
        self.setup_var(self.drop_var2, mg.VAR_2_DEFAULT, self.sorted_var_names2)
        # layout
        szr_vars_top_left_top.Add(self.lbl_var1, 0, wx.TOP|wx.RIGHT, 5)
        szr_vars_top_left_top.Add(self.drop_var1, 0, wx.RIGHT|wx.TOP, 5)
        szr_vars_top_left_mid.Add(self.lbl_var2, 0, wx.TOP|wx.RIGHT, 5)
        szr_vars_top_left_mid.Add(self.drop_var2, 0, wx.RIGHT|wx.TOP, 5)
        self.szr_vars_top_left.Add(szr_vars_top_left_top, 0)
        self.szr_vars_top_left.Add(szr_vars_top_left_mid, 0)
        # group by
        self.lbl_group_by = wx.StaticText(self.panel_top, -1, _("Group By:"))
        self.lbl_group_by.SetFont(self.LABEL_FONT)
        self.drop_group_by = wx.Choice(self.panel_top, -1, choices=[], 
                                     size=(300,-1))
        self.drop_group_by.Bind(wx.EVT_CHOICE, self.on_group_by_sel)
        self.drop_group_by.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_group_by)
        self.drop_group_by.SetToolTipString(variables_rc_msg)
        self.gp_vals_sorted = [] # same order in dropdowns
        self.gp_choice_items_sorted = [] # refreshed as required and in 
            # order of labels, not raw values
        self.sorted_var_names_by = [] # var names sorted by labels i.e. same as 
            # dropdown.  Refreshed as needed so always usable.
        self.setup_group_by()     
        
        self.lbl_chop_warning = wx.StaticText(self.panel_top, -1, "")
        szr_vars_top_right_top.Add(self.lbl_group_by, 0, wx.RIGHT|wx.TOP, 5)
        szr_vars_top_right_top.Add(self.drop_group_by, 0, wx.GROW)
        szr_vars_top_right_top.Add(self.lbl_chop_warning, 1, wx.TOP|wx.RIGHT, 5)
        # group by A
        self.lbl_group_a = wx.StaticText(self.panel_top, -1, _("Group A:"))
        self.drop_group_a = wx.Choice(self.panel_top, -1, choices=[], 
                                    size=(200,-1))
        self.drop_group_a.Bind(wx.EVT_CHOICE, self.on_group_by_a_sel)
        # group by B
        self.lbl_group_b = wx.StaticText(self.panel_top, -1, _("Group B:"))
        self.drop_group_b = wx.Choice(self.panel_top, -1, choices=[], 
                                    size=(200,-1))
        self.drop_group_b.Bind(wx.EVT_CHOICE, self.on_group_by_b_sel)
        self.setup_group_by_dropdowns()
        szr_vars_top_right_bottom.Add(self.lbl_group_a, 0, wx.RIGHT|wx.TOP, 5)
        szr_vars_top_right_bottom.Add(self.drop_group_a, 0, wx.RIGHT, 5)
        szr_vars_top_right_bottom.Add(self.lbl_group_b, 0, wx.RIGHT|wx.TOP, 5)
        szr_vars_top_right_bottom.Add(self.drop_group_b, 0)
        szr_vars_top_right.Add(szr_vars_top_right_top, 1, wx.GROW)
        szr_vars_top_right.Add(szr_vars_top_right_bottom, 0, wx.GROW|wx.TOP, 5)
        szr_vars_top.Add(self.szr_vars_top_left, 0)
        ln_vert = wx.StaticLine(self.panel_top, style=wx.LI_VERTICAL) 
        szr_vars_top.Add(ln_vert, 0, wx.GROW|wx.LEFT|wx.RIGHT, 5)
        szr_vars_top.Add(szr_vars_top_right, 0)
        szr_vars.Add(szr_vars_top, 0)      
        szr_vars.Add(szr_vars_bottom, 0, wx.GROW)
        # assemble sizer for top panel
        static_box_gap = 0 if mg.PLATFORM == mg.MAC else 10
        if static_box_gap:
            szr_top.Add(wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, static_box_gap)
        szr_top.Add(self.szr_data, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        if static_box_gap:
            szr_top.Add(wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, static_box_gap)
        szr_top.Add(szr_vars, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        self.panel_top.SetSizer(szr_top)
        szr_top.SetSizeHints(self.panel_top)
        # Charts
        self.chart_type = mg.SIMPLE_BARCHART
        # chart buttons
        self.panel_mid = wx.Panel(self)
        bx_charts = wx.StaticBox(self.panel_mid, -1, _("Chart Types"))
        self.szr_mid = wx.StaticBoxSizer(bx_charts, wx.VERTICAL)
        self.setup_chart_btns(szr_chart_btns)
        self.szr_mid.Add(szr_chart_btns, 0, wx.GROW)
        if mg.PLATFORM == mg.LINUX: # http://trac.wxwidgets.org/ticket/9859
            bx_charts.SetToolTipString(_("Make chart"))
        # Chart Settings
        # bar chart
        self.szr_bar_chart = wx.BoxSizer(wx.VERTICAL)
        self.panel_bar_chart = wx.Panel(self.panel_mid)
        lbl_bar_chart = wx.StaticText(self.panel_bar_chart, -1, 
                            u"Bar chart configuration still under construction")
        self.szr_bar_chart.Add(lbl_bar_chart, 1, wx.TOP|wx.BOTTOM, 10)
        self.panel_bar_chart.SetSizer(self.szr_bar_chart)
        self.szr_bar_chart.SetSizeHints(self.panel_bar_chart)
        # clustered bar chart
        self.szr_clustered_bar_chart = wx.BoxSizer(wx.VERTICAL)
        self.panel_clustered_bar_chart = wx.Panel(self.panel_mid)
        lbl_clustered_bar_chart = wx.StaticText(self.panel_clustered_bar_chart, 
                                    -1, u"Clustered bar chart "
                                    u"configuration still under construction")
        self.szr_clustered_bar_chart.Add(lbl_clustered_bar_chart, 1, 
                                         wx.TOP|wx.BOTTOM, 10)
        self.panel_clustered_bar_chart.SetSizer(self.szr_clustered_bar_chart)
        self.szr_clustered_bar_chart.SetSizeHints(\
                                        self.panel_clustered_bar_chart)
        self.panel_clustered_bar_chart.Show(False)
        # pie chart
        self.szr_pie_chart = wx.BoxSizer(wx.VERTICAL)
        self.panel_pie_chart = wx.Panel(self.panel_mid)
        lbl_pie_chart = wx.StaticText(self.panel_pie_chart, -1, 
                            u"Pie chart configuration still under construction")
        self.szr_pie_chart.Add(lbl_pie_chart, 1, wx.TOP|wx.BOTTOM, 10)
        self.panel_pie_chart.SetSizer(self.szr_pie_chart)
        self.szr_pie_chart.SetSizeHints(self.panel_pie_chart)
        self.panel_pie_chart.Show(False)
        # default chart type (bar chart)
        self.panel_displayed = self.panel_bar_chart
        self.szr_mid.Add(self.panel_bar_chart, 0, wx.GROW)
        self.panel_mid.SetSizer(self.szr_mid)
        self.szr_mid.SetSizeHints(self.panel_mid)
        # Bottom panel
        self.panel_bottom = wx.Panel(self)
        szr_titles = wx.BoxSizer(wx.HORIZONTAL)
        szr_lower = wx.BoxSizer(wx.HORIZONTAL)
        szr_bottom_left = wx.BoxSizer(wx.VERTICAL)
        # titles, subtitles
        szr_bottom = wx.BoxSizer(wx.VERTICAL)
        lbl_titles = wx.StaticText(self.panel_bottom, -1, _("Title:"))
        lbl_titles.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.txt_titles = wx.TextCtrl(self.panel_bottom, -1, size=(250,40), 
                                      style=wx.TE_MULTILINE)
        lbl_subtitles = wx.StaticText(self.panel_bottom, -1, _("Subtitle:"))
        lbl_subtitles.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, 
                                          wx.BOLD))
        self.txt_subtitles = wx.TextCtrl(self.panel_bottom, -1, size=(250,40), 
                                         style=wx.TE_MULTILINE)
        szr_titles.Add(lbl_titles, 0, wx.RIGHT, 5)
        szr_titles.Add(self.txt_titles, 1, wx.RIGHT, 10)
        szr_titles.Add(lbl_subtitles, 0, wx.RIGHT, 5)
        szr_titles.Add(self.txt_subtitles, 1)
        self.szr_config_bottom, self.szr_config_top = \
            self.get_misc_config_szrs(self.panel_bottom) # mixin                         
        self.szr_output_btns = self.get_szr_output_btns(self.panel_bottom, 
                                                        inc_clear=False) # mixin
        self.html = full_html.FullHTML(panel=self.panel_bottom, parent=self, 
                                       size=(200, 150))
        if mg.PLATFORM == mg.MAC:
            self.html.Bind(wx.EVT_WINDOW_CREATE, self.on_show)
        else:
            self.Bind(wx.EVT_SHOW, self.on_show)
        szr_bottom_left.Add(self.html, 1, wx.GROW|wx.BOTTOM, 5)
        szr_bottom_left.Add(self.szr_config_top, 0, wx.GROW)
        szr_bottom_left.Add(self.szr_config_bottom, 0, wx.GROW)
        szr_lower.Add(szr_bottom_left, 1, wx.GROW)
        szr_lower.Add(self.szr_output_btns, 0, wx.GROW|wx.LEFT, 10)
        szr_bottom.Add(szr_titles, 0, wx.GROW|wx.ALL, 10)
        szr_bottom.Add(szr_lower, 2, wx.GROW|wx.ALL, 10)
        self.add_other_var_opts()
        self.panel_bottom.SetSizer(szr_bottom)
        szr_bottom.SetSizeHints(self.panel_bottom)
        # assemble entire frame
        szr_main.Add(self.panel_top, 0, wx.GROW)
        static_box_gap = 0 if mg.PLATFORM == mg.MAC else 10
        if static_box_gap:
            szr_main.Add(wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, static_box_gap)
        szr_main.Add(self.panel_mid, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szr_main.Add(self.panel_bottom, 1, wx.GROW)
        self.SetAutoLayout(True)
        self.SetSizer(szr_main)
        szr_lst = [self.panel_top, self.panel_mid, self.panel_bottom]
        lib.set_size(window=self, szr_lst=szr_lst, width_init=1024, 
                     height_init=myheight)
        
        self.drop_group_by.Enable(False)

    def on_show(self, event):
        try:
            self.html.pizza_magic() # must happen after Show
        except Exception, e:
            pass # needed on Mac else exception survives
        finally:
            # any initial content
            html2show = _("<p>Waiting for a report to be run.</p>")
            self.html.show_html(html2show)
    
    def setup_chart_btns(self, szr_chart_btns):
        # bar charts
        bmp_btn_bar_chart = wx.Image(os.path.join(mg.SCRIPT_PATH, u"images", 
                                                  u"bar_chart.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_bar_chart = wx.BitmapButton(self.panel_mid, -1, 
                                             bmp_btn_bar_chart)
        self.btn_bar_chart.Bind(wx.EVT_BUTTON, self.on_btn_bar_chart)
        self.btn_bar_chart.SetToolTipString(_("Make Bar Chart"))
        self.btn_bar_chart.SetDefault()
        self.btn_bar_chart.SetFocus()
        szr_chart_btns.Add(self.btn_bar_chart)
        # clustered bar charts
        bmp_btn_clust_bar_chart = wx.Image(os.path.join(mg.SCRIPT_PATH, 
                                        u"images", u"clustered_bar_chart.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_clust_bar_chart = wx.BitmapButton(self.panel_mid, -1, 
                                                       bmp_btn_clust_bar_chart)
        self.btn_clust_bar_chart.Bind(wx.EVT_BUTTON, 
                                      self.on_btn_clustered_bar_chart)
        self.btn_clust_bar_chart.SetToolTipString(_("Make Clustered Bar Chart"))
        szr_chart_btns.Add(self.btn_clust_bar_chart)
        # pie charts
        bmp_btn_pie_chart = wx.Image(os.path.join(mg.SCRIPT_PATH, u"images", 
                                                  u"pie_chart.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_pie_chart = wx.BitmapButton(self.panel_mid, -1, 
                                             bmp_btn_pie_chart)
        self.btn_pie_chart.Bind(wx.EVT_BUTTON, self.on_btn_pie_chart)
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
        if mg.PLATFORM == mg.LINUX:
            hand = wx.StockCursor(wx.CURSOR_HAND)
            self.btn_bar_chart.SetCursor(hand)
            self.btn_clust_bar_chart.SetCursor(hand)
            self.btn_pie_chart.SetCursor(hand)
            self.btn_line_chart.SetCursor(hand)
            self.btn_area_chart.SetCursor(hand)
            self.btn_scatterplot.SetCursor(hand)
            self.btn_histogram.SetCursor(hand)
    
    def setup_var1(self):
        self.min_data_type = mg.CHART_TYPE_TO_MIN_DATA_TYPE.get(self.chart_type, 
                                                                mg.VAR_TYPE_CAT)
        var_gp, var_name1, var_name2 = self.get_vars()
        self.setup_var(self.drop_var1, mg.VAR_1_DEFAULT, self.sorted_var_names1, 
                       var_name1)
    
    def display_var2(self):
        show = (self.chart_type in mg.TWO_VAR_CHART_TYPES)
        self.drop_var2.Enable(show)
        self.lbl_var2.Enable(show)
    
    def on_btn_bar_chart(self, event):
        self.chart_type = mg.SIMPLE_BARCHART
        self.btn_bar_chart.SetFocus()
        self.btn_bar_chart.SetDefault()
        event.Skip()
        self.lbl_var1.SetLabel(mg.CHART_VALUES)
        self.lbl_var2.SetLabel(mg.CHART_BY)
        if self.panel_displayed == self.panel_bar_chart:
            return
        else:
            self.panel_displayed.Show(False)
            self.setup_var1()
        self.display_var2()
        self.szr_mid.Remove(self.panel_displayed)
        self.szr_mid.Add(self.panel_bar_chart, 0, wx.GROW)
        self.panel_displayed = self.panel_bar_chart
        self.panel_bar_chart.Show(True)
        self.panel_mid.Layout() # self.Layout() doesn't work in Windows

    def on_btn_clustered_bar_chart(self, event):
        self.chart_type = mg.CLUSTERED_BARCHART
        self.btn_clust_bar_chart.SetFocus()
        self.btn_clust_bar_chart.SetDefault()
        event.Skip()
        self.lbl_var1.SetLabel(mg.CHART_VALUES)
        self.lbl_var2.SetLabel(mg.CHART_BY)
        self.btn_clust_bar_chart.SetDefault()
        self.btn_clust_bar_chart.SetFocus()
        if self.panel_displayed == self.panel_clustered_bar_chart:
            event.Skip()
            return
        else:
            self.panel_displayed.Show(False)
            self.setup_var1()
        self.display_var2()
        self.szr_mid.Remove(self.panel_displayed)
        self.szr_mid.Add(self.panel_clustered_bar_chart, 0, wx.GROW)
        self.panel_displayed = self.panel_clustered_bar_chart
        self.panel_clustered_bar_chart.Show(True)
        self.panel_mid.Layout()

    def on_btn_pie_chart(self, event):
        self.chart_type = mg.PIE_CHART
        self.btn_pie_chart.SetFocus()
        self.btn_pie_chart.SetDefault()
        event.Skip()
        self.lbl_var1.SetLabel(mg.CHART_VALUES)
        self.lbl_var2.SetLabel(mg.CHART_BY)
        if self.panel_displayed == self.panel_pie_chart:
            return
        else:
            self.panel_displayed.Show(False)
            self.setup_var1()
        self.display_var2()
        self.szr_mid.Remove(self.panel_displayed)
        self.szr_mid.Add(self.panel_pie_chart, 0, wx.GROW)
        self.panel_displayed = self.panel_pie_chart
        self.panel_pie_chart.Show(True)
        self.panel_mid.Layout()
        
    def on_btn_chart(self, event):
        wx.MessageBox(LIMITS_MSG)

    def get_script(self, css_idx, css_fil):
        "Build script from inputs"
        debug = False
        script_lst = []
        titles, subtitles = self.get_titles()
        script_lst.append(u"titles=%s" % unicode(titles))
        script_lst.append(u"subtitles=%s" % unicode(subtitles))
        unused, tbl_filt = lib.get_tbl_filt(dd.dbe, dd.db, dd.tbl)
        var_gp, var_name1, var_name2 = self.get_vars()
        script_lst.append(u"tbl_filt = u\"%s\"" % tbl_filt)
        script_lst.append(u"fld_measure = u\"%s\"" % var_name1)
        if self.chart_type in mg.TWO_VAR_CHART_TYPES:
            script_lst.append(u"fld_gp = u\"%s\"" % var_name2)
            script_lst.append(u"var_label2=u\"%s\"" % \
                              lib.get_item_label(self.var_labels, var_name2))
            script_lst.append(u"group_by_val_labels = %s" % 
                              self.val_dics.get(var_name2, {}))
        script_lst.append(u"var_label1=u\"%s\"" % \
                          lib.get_item_label(self.var_labels, var_name1))
        script_lst.append(u"measure_val_labels = %s" % 
                          self.val_dics.get(var_name1, {}))
        if self.chart_type == mg.SIMPLE_BARCHART:
            script_lst.append(u"xaxis_dets, y_vals = "
                  u"charting_output.get_simple_barchart_dets(dbe=\"%(dbe)s\", "
                  u"cur=cur,"
                  u"\n    tbl=tbl, tbl_filt=tbl_filt, fld_measure=fld_measure, "
                  u"xaxis_val_labels=measure_val_labels)" % {u"dbe": dd.dbe})
            script_lst.append(u"series_dets = [{u\"label\": var_label1, "
                              u"u\"y_vals\": y_vals},]")
            script_lst.append(u"chart_output = "
                  u"charting_output.barchart_output(titles, subtitles,"
                  u"\n    xaxis_dets, series_dets, css_idx=%s, css_fil=\"%s\", "
                  u"page_break_after=False)" % (css_idx, css_fil))
        elif self.chart_type == mg.CLUSTERED_BARCHART:
            script_lst.append(u"xaxis_dets, series_dets = "
                  u"charting_output.get_clustered_barchart_dets(dbe=\"%(dbe)s\"" 
                        u", cur=cur,"
                  u"\n    tbl=tbl, tbl_filt=tbl_filt, fld_measure=fld_measure, "
                  u"fld_gp=fld_gp, "
                  u"\n    xaxis_val_labels=measure_val_labels, "
                  u"group_by_val_labels=group_by_val_labels)" % 
                    {u"dbe": dd.dbe})
            script_lst.append(u"chart_output = "
                  u"charting_output.barchart_output(titles, "
                        u"subtitles,"
                  u"\n    xaxis_dets, series_dets, "
                  u" css_idx=%s, css_fil=\"%s\", page_break_after=False)" %
                      (css_idx, css_fil))
        elif self.chart_type == mg.PIE_CHART:
            script_lst.append(u"slice_dets = "
                  u"charting_output.get_pie_chart_dets(dbe=\"%(dbe)s\"" 
                        u", cur=cur,"
                  u"\n    tbl=tbl, tbl_filt=tbl_filt, fld_measure=fld_measure, "
                  u"\n    slice_val_labels=measure_val_labels)" % 
                    {u"dbe": dd.dbe})
            script_lst.append(u"chart_output = "
                  u"charting_output.piechart_output(titles, "
                        u"subtitles,"
                  u"\n    slice_dets, css_idx=%s, css_fil=\"%s\", "
                  u"page_break_after=False)" % (css_idx, css_fil))
        script_lst.append(u"fil.write(chart_output)")
        return u"\n".join(script_lst)
    
    def on_btn_run(self, event):
        # get settings
        if self.chart_type in (mg.SIMPLE_BARCHART, mg.CLUSTERED_BARCHART, 
                               mg.PIE_CHART):
            run_ok = self.test_config_ok()
            add_to_report = self.chk_add_to_report.IsChecked()
            if run_ok:
                css_fil = cc[mg.CURRENT_CSS_PATH]
                config_dlg.ConfigDlg.on_btn_run(self, event, OUTPUT_MODULES, 
                                                get_script_args=[css_fil], 
                                                new_has_dojo=True)
        else:
            wx.MessageBox(LIMITS_MSG)
        
    def on_btn_export(self, event):
        
        
        # TODO NB will have new_has_dojo=True
        
        wx.MessageBox(u"This version does not support exporting chart code yet")
    
    def on_var1_sel(self, event):
        pass
        
    def on_var2_sel(self, event):
        pass
    
    def add_other_var_opts(self, szr=None):
        pass

    def on_rclick_var1(self, event):
        self.on_rclick_var(self.drop_var1, self.sorted_var_names1)
        
    def on_rclick_var2(self, event):
        self.on_rclick_var(self.drop_var2, self.sorted_var_names2)
        
    def on_rclick_var(self, drop_var, sorted_var_names):
        var_name, choice_item = self.get_var_dets(drop_var, sorted_var_names)
        var_label = lib.get_item_label(self.var_labels, var_name)
        updated = projects.set_var_props(choice_item, var_name, var_label, 
                                         self.var_labels, self.var_notes, 
                                         self.var_types,  self.val_dics)
        if updated:
            self.refresh_vars()
    
    def refresh_vars(self):
        var_gp, var_name1, var_name2 = self.get_vars()
        self.setup_group_by(var_gp)
        self.setup_var(self.drop_var1, mg.VAR_1_DEFAULT, self.sorted_var_names1, 
                       var_name1)
        self.setup_var(self.drop_var2, mg.VAR_2_DEFAULT, self.sorted_var_names2,
                       var_name2)
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
        self.setup_group_by_dropdowns()
                
    def on_table_sel(self, event):
        "Reset key data details after table selection."       
        config_dlg.ConfigDlg.on_table_sel(self, event)
        # now update var dropdowns
        self.update_var_dets()
        self.setup_group_by()
        self.setup_var(self.drop_var1, mg.VAR_1_DEFAULT, self.sorted_var_names1)
        self.setup_var(self.drop_var2, mg.VAR_2_DEFAULT, self.sorted_var_names2)
        self.setup_group_by_dropdowns()
    
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
        self.setup_var(self.drop_var2, mg.VAR_2_DEFAULT, self.sorted_var_names2, 
                       var_name2)
        self.setup_group_by_dropdowns(val_a, val_b)
        self.update_defaults()
        
    def on_btn_var_dets_path(self, event):
        """
        Want to retain already selected item - even though label and even 
            position may have changed.
        """
        val_a, val_b = self.get_vals()
        var_gp, var_name1, var_name2 = self.get_vars()
        config_dlg.ConfigDlg.on_btn_var_dets_path(self, event)
        
        
        return # will sort out when wiring up for real
        
        
        self.setup_group_by(var_gp)
        self.setup_var(self.drop_var1, mg.VAR_1_DEFAULT, self.sorted_var_names1, 
                       var_name1)
        self.setup_var(self.drop_var2, mg.VAR_2_DEFAULT, self.sorted_var_names2, 
                       var_name2)
        self.setup_group_by_dropdowns(val_a, val_b)
        self.update_defaults()

    def get_vars(self):
        """
        self.sorted_var_names_by and self.sorted_var_names1 and 2 are set when 
            dropdowns are set (and only changed when reset).
        """
        var_name1, unused = self.get_var_dets(self.drop_var1, 
                                              self.sorted_var_names1)
        if self.chart_type in mg.TWO_VAR_CHART_TYPES:
            var_name2, unused = self.get_var_dets(self.drop_var2, 
                                                  self.sorted_var_names2)
        else:
            var_name2 = None
        var_gp, unused = self.get_group_by()
        return var_gp, var_name1, var_name2
    
    def update_defaults(self):
        mg.GROUP_BY_DEFAULT = self.drop_group_by.GetStringSelection()
        mg.VAR_1_DEFAULT = self.drop_var1.GetStringSelection()
        mg.VAR_2_DEFAULT = self.drop_var2.GetStringSelection()
        mg.VAL_A_DEFAULT = self.drop_group_a.GetStringSelection()
        mg.VAL_B_DEFAULT = self.drop_group_b.GetStringSelection()
   
    def get_drop_vals(self):
        """
        Get values from main drop downs.
        Returns var_gp_numeric, var_gp, label_gp, val_a, label_a, val_b, 
            label_b, var_1, label_1, var_1, label_1.
        """
        selection_idx_gp = self.drop_group_by.GetSelection()
        var_gp = self.sorted_var_names_by[selection_idx_gp]
        label_gp = lib.get_item_label(item_labels=self.var_labels, 
                                      item_val=var_gp)
        var_gp_numeric = dd.flds[var_gp][mg.FLD_BOLNUMERIC]
        # Now the a and b choices under the group
        val_dic = self.val_dics.get(var_gp, {})
        selection_idx_a = self.drop_group_a.GetSelection()
        val_a_raw = self.gp_vals_sorted[selection_idx_a]
        val_a = lib.any2unicode(val_a_raw)
        label_a = lib.get_item_label(item_labels=val_dic, 
                                     item_val=val_a_raw)
        selection_idx_b = self.drop_group_b.GetSelection()
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
        if self.drop_group_by.GetStringSelection() == \
                self.drop_var1.GetStringSelection():
            wx.MessageBox(_("Variable 1 and the Grouped By Variable cannot be "
                            "the same"))
            return False
        if self.drop_group_by.GetStringSelection() == \
                self.drop_var2.GetStringSelection():
            wx.MessageBox(_("Variable 2 and the Grouped By Variable cannot be "
                            "the same"))
            return False
        if (self.chart_type in mg.TWO_VAR_CHART_TYPES and
                self.drop_var1.GetStringSelection() ==
                self.drop_var2.GetStringSelection()):
            wx.MessageBox(_("Variable 1 and 2 cannot be the same"))
            return False
        
        
        
        
        # group A and B cannot be the same
        # TODO reactivate when group by re-enabled
        #if self.drop_group_a.GetStringSelection() == \
        #        self.drop_group_b.GetStringSelection():
        #    wx.MessageBox(_("Group A and Group B must be different"))
        #    return False
        
        
        
        
        
        if self.takes_range:
            var_gp_numeric, var_gp, unused, unused, unused, unused, unused, \
                unused, unused, unused, unused = self.get_drop_vals()
            # group a must be lower than group b
            val_dic = self.val_dics.get(var_gp, {})
            selection_idx_a = self.drop_group_a.GetSelection()
            val_a = self.vals_with_labels[selection_idx_a]
            selection_idx_b = self.drop_group_b.GetSelection()
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
