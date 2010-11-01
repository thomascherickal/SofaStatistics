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

OUTPUT_MODULES = ["my_globals as mg", "core_stats", "charting_output", "output", 
                  "getdata"]
cc = config_dlg.get_cc()
dd = getdata.get_dd()

LIMITS_MSG = (u"This chart type is not currently available in this release. "
              u"More chart types coming soon!")
CUR_SORT_OPT = mg.SORT_NONE
INC_PERC = True


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
        szr_help_data = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_data = self.get_szr_data(self.panel_top) # mixin
        if mg.PLATFORM == mg.LINUX: # http://trac.wxwidgets.org/ticket/9859
            bx_vars.SetToolTipString(variables_rc_msg)
        self.btn_help = wx.Button(self.panel_top, wx.ID_HELP)
        self.btn_help.Bind(wx.EVT_BUTTON, self.on_btn_help)
        szr_vars = wx.StaticBoxSizer(bx_vars, wx.HORIZONTAL)
        self.szr_vars_top_left = wx.BoxSizer(wx.VERTICAL)
        szr_vars_top_right = wx.BoxSizer(wx.VERTICAL)
        szr_vars_top_left_top = wx.BoxSizer(wx.HORIZONTAL)
        szr_vars_top_left_mid = wx.BoxSizer(wx.HORIZONTAL)
        szr_vars_top_right_top = wx.BoxSizer(wx.HORIZONTAL)
        szr_vars_top_right_bottom = wx.BoxSizer(wx.HORIZONTAL)
        szr_chart_btns = wx.BoxSizer(wx.HORIZONTAL)
        # var 1
        self.min_data_type = mg.VAR_TYPE_CAT # needed to set up var 1
        self.lbl_var1 = wx.StaticText(self.panel_top, -1, 
                                      u"%s:" % mg.CHART_VALUES)
        self.lbl_var1.SetFont(self.LABEL_FONT)
        self.drop_var1 = wx.Choice(self.panel_top, -1, choices=[], 
                                   size=(210,-1))
        self.drop_var1.Bind(wx.EVT_CHOICE, self.on_var1_sel)
        self.drop_var1.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_var1)
        self.drop_var1.SetToolTipString(variables_rc_msg)
        self.sorted_var_names1 = []
        self.setup_var(self.drop_var1, mg.VAR_1_DEFAULT, self.sorted_var_names1)
        # var 2
        self.min_data_type2 = self.min_data_type
        self.lbl_var2 = wx.StaticText(self.panel_top, -1, u"%s:" % mg.CHART_BY)
        self.lbl_var2.SetFont(self.LABEL_FONT)
        self.drop_var2 = wx.Choice(self.panel_top, -1, choices=[], 
                                   size=(210,-1))
        self.drop_var2.Bind(wx.EVT_CHOICE, self.on_var2_sel)
        self.drop_var2.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_var2)
        self.drop_var2.SetToolTipString(variables_rc_msg)
        self.sorted_var_names2 = []
        self.setup_var(self.drop_var2, mg.VAR_2_DEFAULT, self.sorted_var_names2, 
                       var_name=None, inc_drop_select=True)
        # var 3
        self.lbl_var3 = wx.StaticText(self.panel_top, -1, u"%s:" % 
                                      mg.CHART_CHART_BY)
        self.lbl_var3.SetFont(self.LABEL_FONT)
        self.drop_var3 = wx.Choice(self.panel_top, -1, choices=[], 
                                   size=(210,-1))
        self.drop_var3.Bind(wx.EVT_CHOICE, self.on_var3_sel)
        self.drop_var3.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_var3)
        self.drop_var3.SetToolTipString(variables_rc_msg)
        self.sorted_var_names3 = []
        self.setup_var(self.drop_var3, mg.VAR_3_DEFAULT, self.sorted_var_names3, 
                       var_name=None, inc_drop_select=False, 
                       override_min_data_type=mg.VAR_TYPE_CAT) # inc all
        # layout
        help_down_by = 27 if mg.PLATFORM == mg.MAC else 17
        szr_help_data.Add(self.btn_help, 0, wx.TOP, help_down_by)
        szr_help_data.Add(self.szr_data, 1, wx.LEFT, 5)
        szr_vars.Add(self.lbl_var1, 0, wx.TOP|wx.RIGHT, 5)
        szr_vars.Add(self.drop_var1, 0, wx.RIGHT|wx.TOP, 5)
        szr_vars.Add(self.lbl_var2, 0, wx.TOP|wx.RIGHT, 5)
        szr_vars.Add(self.drop_var2, 0, wx.RIGHT|wx.TOP, 5)
        szr_vars.Add(self.lbl_var3, 0, wx.TOP|wx.RIGHT, 5)
        szr_vars.Add(self.drop_var3, 0, wx.RIGHT|wx.TOP, 5)
        # var 3 invisible
        self.lbl_var3.Hide()
        self.drop_var3.Hide()
        # assemble sizer for top panel
        static_box_gap = 0 if mg.PLATFORM == mg.MAC else 5
        if static_box_gap:
            szr_top.Add(wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, static_box_gap)
        szr_top.Add(szr_help_data, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
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
        self.szr_bar_chart = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_bar_chart = wx.Panel(self.panel_mid)
        self.rad_bar_sort_opts = wx.RadioBox(self.panel_bar_chart, -1, 
                                             _("Sort order of bars"), 
                                             choices=mg.SORT_OPTS, 
                                             size=(-1,50))
        idx_current_sort_opt = mg.SORT_OPTS.index(CUR_SORT_OPT)
        self.rad_bar_sort_opts.SetSelection(idx_current_sort_opt)
        self.rad_bar_sort_opts.Bind(wx.wx.EVT_RADIOBOX, 
                                    self.on_rad_bar_sort_opt)
        self.chk_simple_bar_perc = wx.CheckBox(self.panel_bar_chart, -1, 
                                               _("Show percent?"))
        self.chk_simple_bar_perc.SetValue(INC_PERC)
        self.chk_simple_bar_perc.SetToolTipString(_(u"Show percent in tool "
                                                    u"tip?"))
        self.chk_simple_bar_perc.Bind(wx.EVT_CHECKBOX, 
                                      self.on_chk_simple_bar_perc)
        self.szr_bar_chart.Add(self.rad_bar_sort_opts, 0, wx.TOP|wx.RIGHT, 5)
        if mg.PLATFORM == mg.WINDOWS:
            bar_perc_down_by = 27
        elif mg.PLATFORM == mg.LINUX:
            bar_perc_down_by = 22
        else:
            bar_perc_down_by = 27
        self.szr_bar_chart.Add(self.chk_simple_bar_perc, 0, wx.TOP, 
                               bar_perc_down_by)
        self.panel_bar_chart.SetSizer(self.szr_bar_chart)
        self.szr_bar_chart.SetSizeHints(self.panel_bar_chart)
        # clustered bar chart
        self.szr_clustered_bar_chart = wx.BoxSizer(wx.VERTICAL)
        self.panel_clustered_bar_chart = wx.Panel(self.panel_mid)
        self.chk_clust_bar_perc = wx.CheckBox(self.panel_clustered_bar_chart, 
                                              -1, _("Show percent?"))
        self.chk_clust_bar_perc.SetValue(INC_PERC)
        self.chk_clust_bar_perc.SetToolTipString(_(u"Show percent in tool "
                                                   u"tip?"))
        self.chk_clust_bar_perc.Bind(wx.EVT_CHECKBOX, 
                                     self.on_chk_clust_bar_perc)
        self.szr_clustered_bar_chart.Add(self.chk_clust_bar_perc, 1, 
                                         wx.TOP|wx.BOTTOM, 10)
        self.panel_clustered_bar_chart.SetSizer(self.szr_clustered_bar_chart)
        self.szr_clustered_bar_chart.SetSizeHints(\
                                        self.panel_clustered_bar_chart)
        # pie chart
        self.szr_pie_chart = wx.BoxSizer(wx.VERTICAL)
        self.panel_pie_chart = wx.Panel(self.panel_mid)
        self.rad_pie_sort_opts = wx.RadioBox(self.panel_pie_chart, -1, 
                                             _("Sort order of pie slices"), 
                                             choices=mg.SORT_OPTS, 
                                             size=(-1,50))
        self.rad_pie_sort_opts.SetSelection(idx_current_sort_opt)
        self.rad_pie_sort_opts.Bind(wx.wx.EVT_RADIOBOX, 
                                    self.on_rad_pie_sort_opt)
        self.szr_pie_chart.Add(self.rad_pie_sort_opts, 0, wx.TOP, 5)
        self.panel_pie_chart.SetSizer(self.szr_pie_chart)
        self.szr_pie_chart.SetSizeHints(self.panel_pie_chart)
        # line chart
        self.szr_line_chart = wx.BoxSizer(wx.VERTICAL)
        self.panel_line_chart = wx.Panel(self.panel_mid)
        self.chk_line_perc = wx.CheckBox(self.panel_line_chart, -1, 
                                         _("Show percent?"))
        self.chk_line_perc.SetValue(INC_PERC)
        self.chk_line_perc.SetToolTipString(_(u"Show percent in tool tip?"))
        self.chk_line_perc.Bind(wx.EVT_CHECKBOX, self.on_chk_line_perc)
        self.szr_line_chart.Add(self.chk_line_perc, 1, wx.TOP|wx.BOTTOM, 10)
        self.panel_line_chart.SetSizer(self.szr_line_chart)
        self.szr_line_chart.SetSizeHints(self.panel_line_chart)
        # area chart
        self.szr_area_chart = wx.BoxSizer(wx.VERTICAL)
        self.panel_area_chart = wx.Panel(self.panel_mid)
        self.chk_area_perc = wx.CheckBox(self.panel_area_chart, -1, 
                                         _("Show percent?"))
        self.chk_area_perc.SetValue(INC_PERC)
        self.chk_area_perc.SetToolTipString(_(u"Show percent in tool tip?"))
        self.chk_area_perc.Bind(wx.EVT_CHECKBOX, self.on_chk_area_perc)
        self.szr_area_chart.Add(self.chk_area_perc, 1, wx.TOP|wx.BOTTOM, 10)
        self.panel_area_chart.SetSizer(self.szr_area_chart)
        self.szr_area_chart.SetSizeHints(self.panel_area_chart)
        # histogram
        self.szr_histogram = wx.BoxSizer(wx.VERTICAL)
        self.panel_histogram = wx.Panel(self.panel_mid)
        self.panel_histogram.SetSizer(self.szr_histogram)
        self.szr_histogram.SetSizeHints(self.panel_histogram)
        # scatterplot
        self.szr_scatterplot = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_scatterplot = wx.Panel(self.panel_mid)
        self.chk_borders = wx.CheckBox(self.panel_scatterplot, -1, 
                                       _("Dot borders?"))
        self.chk_borders.SetValue(True)
        self.szr_scatterplot.Add(self.chk_borders, 0, wx.TOP|wx.BOTTOM, 10)
        self.chk_borders.SetToolTipString(_("Show borders around scatterplot "
                                            "dots?"))
        self.panel_scatterplot.SetSizer(self.szr_scatterplot)
        self.szr_scatterplot.SetSizeHints(self.panel_scatterplot)
        # Hide all panels except default.  Display and layout then hide.
        # Prevents flicker on change later.
        panels2hide = [self.panel_clustered_bar_chart, self.panel_pie_chart,
                       self.panel_line_chart, self.panel_area_chart,
                       self.panel_histogram, self.panel_scatterplot]
        check = True
        for panel2hide in panels2hide:
            self.szr_mid.Add(panel2hide, 0, wx.GROW)
            if check:
                self.panel_mid.SetSizer(self.szr_mid)
                self.szr_mid.SetSizeHints(self.panel_mid)
                check = False
            panel2hide.Show(True)
            self.panel_mid.Layout() # self.Layout() doesn't work in Windows
            panel2hide.Show(False)
            self.szr_mid.Remove(panel2hide)
        # default chart type (bar chart)
        self.panel_displayed = self.panel_bar_chart
        self.szr_mid.Add(self.panel_bar_chart, 0, wx.GROW)
        self.panel_bar_chart.Show(True)
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
        title_height = 40 if mg.PLATFORM == mg.MAC else 20
        self.txt_titles = wx.TextCtrl(self.panel_bottom, -1, 
                                      size=(250,title_height), 
                                      style=wx.TE_MULTILINE)
        lbl_subtitles = wx.StaticText(self.panel_bottom, -1, _("Subtitle:"))
        lbl_subtitles.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, 
                                          wx.BOLD))
        self.txt_subtitles = wx.TextCtrl(self.panel_bottom, -1, 
                                         size=(250,title_height), 
                                         style=wx.TE_MULTILINE)
        szr_titles.Add(lbl_titles, 0, wx.RIGHT, 5)
        szr_titles.Add(self.txt_titles, 1, wx.RIGHT, 10)
        szr_titles.Add(lbl_subtitles, 0, wx.RIGHT, 5)
        szr_titles.Add(self.txt_subtitles, 1)
        self.szr_config = self.get_config_szr(self.panel_bottom) # mixin                         
        self.szr_output_btns = self.get_szr_output_btns(self.panel_bottom, 
                                                        inc_clear=False) # mixin
        self.html = full_html.FullHTML(panel=self.panel_bottom, parent=self, 
                                       size=(200, 150))
        if mg.PLATFORM == mg.MAC:
            self.html.Bind(wx.EVT_WINDOW_CREATE, self.on_show)
        else:
            self.Bind(wx.EVT_SHOW, self.on_show)
        szr_bottom_left.Add(self.html, 1, wx.GROW|wx.BOTTOM, 5)
        szr_bottom_left.Add(self.szr_config, 0, wx.GROW)
        szr_lower.Add(szr_bottom_left, 1, wx.GROW)
        szr_lower.Add(self.szr_output_btns, 0, wx.GROW|wx.LEFT, 10)
        szr_bottom.Add(szr_titles, 0, wx.GROW|wx.LEFT|wx.TOP|wx.RIGHT, 10)
        szr_bottom.Add(szr_lower, 2, wx.GROW|wx.ALL, 10)
        self.add_other_var_opts()
        self.panel_bottom.SetSizer(szr_bottom)
        szr_bottom.SetSizeHints(self.panel_bottom)
        # assemble entire frame
        szr_main.Add(self.panel_top, 0, wx.GROW)
        if static_box_gap:
            szr_main.Add(wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, static_box_gap)
        szr_main.Add(self.panel_mid, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szr_main.Add(self.panel_bottom, 1, wx.GROW)
        self.SetAutoLayout(True)
        self.SetSizer(szr_main)
        szr_lst = [self.panel_top, self.panel_mid, self.panel_bottom]
        lib.set_size(window=self, szr_lst=szr_lst, width_init=1024, 
                     height_init=myheight)            
        
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
        btn_gap = 10 if mg.PLATFORM == mg.WINDOWS else 2
        # bar charts
        self.bmp_btn_bar_chart = wx.Image(os.path.join(mg.SCRIPT_PATH, 
                                                u"images", u"bar_chart.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.bmp_btn_bar_chart_sel = wx.Image(os.path.join(mg.SCRIPT_PATH, 
                                            u"images", u"bar_chart_sel.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_bar_chart = wx.BitmapButton(self.panel_mid, -1, 
                                             self.bmp_btn_bar_chart_sel, 
                                             style=wx.NO_BORDER)
        self.btn_bar_chart.Bind(wx.EVT_BUTTON, self.on_btn_bar_chart)
        self.btn_bar_chart.SetToolTipString(_("Make Bar Chart"))
        self.btn_bar_chart.SetDefault()
        self.btn_bar_chart.SetFocus()
        szr_chart_btns.Add(self.btn_bar_chart, 0, wx.RIGHT, btn_gap)
        # clustered bar charts
        self.bmp_btn_clust_bar_chart = wx.Image(os.path.join(mg.SCRIPT_PATH, 
                                        u"images", u"clustered_bar_chart.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.bmp_btn_clust_bar_chart_sel = wx.Image(os.path.join(mg.SCRIPT_PATH, 
                                    u"images", u"clustered_bar_chart_sel.xpm"), 
                                    wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_clust_bar_chart = wx.BitmapButton(self.panel_mid, -1, 
                                                   self.bmp_btn_clust_bar_chart, 
                                                   style=wx.NO_BORDER)
        self.btn_clust_bar_chart.Bind(wx.EVT_BUTTON, 
                                      self.on_btn_clustered_bar_chart)
        self.btn_clust_bar_chart.SetToolTipString(_("Make Clustered Bar Chart"))
        szr_chart_btns.Add(self.btn_clust_bar_chart, 0, wx.RIGHT, btn_gap)
        # pie charts
        self.bmp_btn_pie_chart = wx.Image(os.path.join(mg.SCRIPT_PATH, 
                                                u"images", u"pie_chart.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.bmp_btn_pie_chart_sel = wx.Image(os.path.join(mg.SCRIPT_PATH, 
                                            u"images", u"pie_chart_sel.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap() 
        self.btn_pie_chart = wx.BitmapButton(self.panel_mid, -1, 
                                             self.bmp_btn_pie_chart, 
                                             style=wx.NO_BORDER)                  
        self.btn_pie_chart.Bind(wx.EVT_BUTTON, self.on_btn_pie_chart)
        self.btn_pie_chart.SetToolTipString(_("Make Pie Chart"))
        szr_chart_btns.Add(self.btn_pie_chart, 0, wx.RIGHT, btn_gap)
        # line charts
        self.bmp_btn_line_chart = wx.Image(os.path.join(mg.SCRIPT_PATH, 
                                            u"images", u"line_chart.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.bmp_btn_line_chart_sel = wx.Image(os.path.join(mg.SCRIPT_PATH, 
                                            u"images", u"line_chart_sel.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_line_chart = wx.BitmapButton(self.panel_mid, -1, 
                                              self.bmp_btn_line_chart, 
                                              style=wx.NO_BORDER)
        self.btn_line_chart.Bind(wx.EVT_BUTTON, self.on_btn_line_chart)
        self.btn_line_chart.SetToolTipString(_("Make Line Chart"))
        szr_chart_btns.Add(self.btn_line_chart, 0, wx.RIGHT, btn_gap)
        # area charts
        self.bmp_btn_area_chart = wx.Image(os.path.join(mg.SCRIPT_PATH, 
                                        u"images", u"area_chart.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.bmp_btn_area_chart_sel = wx.Image(os.path.join(mg.SCRIPT_PATH, 
                                        u"images", u"area_chart_sel.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_area_chart = wx.BitmapButton(self.panel_mid, -1, 
                                              self.bmp_btn_area_chart, 
                                              style=wx.NO_BORDER)
        self.btn_area_chart.Bind(wx.EVT_BUTTON, self.on_btn_area_chart)
        self.btn_area_chart.SetToolTipString(_("Make Area Chart"))
        szr_chart_btns.Add(self.btn_area_chart, 0, wx.RIGHT, btn_gap)
        # histograms
        self.bmp_btn_histogram = wx.Image(os.path.join(mg.SCRIPT_PATH, 
                                            u"images", u"histogram.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.bmp_btn_histogram_sel = wx.Image(os.path.join(mg.SCRIPT_PATH, u"images", 
                                                  u"histogram_sel.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_histogram = wx.BitmapButton(self.panel_mid, -1, 
                                             self.bmp_btn_histogram, 
                                             style=wx.NO_BORDER)
        self.btn_histogram.Bind(wx.EVT_BUTTON, self.on_btn_histogram)
        self.btn_histogram.SetToolTipString(_("Make Histogram"))
        szr_chart_btns.Add(self.btn_histogram, 0, wx.RIGHT, btn_gap)
        # scatterplots
        self.bmp_btn_scatterplot = wx.Image(os.path.join(mg.SCRIPT_PATH, 
                                            u"images", u"scatterplot.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.bmp_btn_scatterplot_sel = wx.Image(os.path.join(mg.SCRIPT_PATH, 
                                            u"images", u"scatterplot_sel.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_scatterplot = wx.BitmapButton(self.panel_mid, -1, 
                                               self.bmp_btn_scatterplot, 
                                               style=wx.NO_BORDER)
        self.btn_scatterplot.Bind(wx.EVT_BUTTON, self.on_btn_scatterplot)
        self.btn_scatterplot.SetToolTipString(_("Make Scatterplot"))
        szr_chart_btns.Add(self.btn_scatterplot)
        if mg.PLATFORM == mg.LINUX:
            hand = wx.StockCursor(wx.CURSOR_HAND)
            self.btn_bar_chart.SetCursor(hand)
            self.btn_clust_bar_chart.SetCursor(hand)
            self.btn_pie_chart.SetCursor(hand)
            self.btn_line_chart.SetCursor(hand)
            self.btn_area_chart.SetCursor(hand)
            self.btn_scatterplot.SetCursor(hand)
            self.btn_histogram.SetCursor(hand)
        self.btn_to_rollback = self.btn_bar_chart
        self.bmp_to_rollback_to = self.bmp_btn_bar_chart

    def on_chk_simple_bar_perc(self, event):
        global INC_PERC
        INC_PERC = self.chk_simple_bar_perc.IsChecked()

    def on_chk_clust_bar_perc(self, event):
        global INC_PERC
        INC_PERC = self.chk_clust_bar_perc.IsChecked()

    def on_chk_line_perc(self, event):
        global INC_PERC
        INC_PERC = self.chk_line_perc.IsChecked()

    def on_chk_area_perc(self, event):
        global INC_PERC
        INC_PERC = self.chk_area_perc.IsChecked()
        
    def on_rad_sort_opt(self, idx_sel):
        debug = False
        global CUR_SORT_OPT
        try:
            CUR_SORT_OPT = mg.SORT_OPTS[idx_sel]
        except IndexError, e:
            pass
        if debug: print(u"Current sort option: %s" % CUR_SORT_OPT)
    
    def on_rad_bar_sort_opt(self, event):
        idx_sel = self.rad_bar_sort_opts.GetSelection()
        self.on_rad_sort_opt(idx_sel)
        
    def on_rad_pie_sort_opt(self, event):
        idx_sel = self.rad_pie_sort_opts.GetSelection()
        self.on_rad_sort_opt(idx_sel)
        
    def btn_chart(self, event, btn, btn_bmp, btn_sel_bmp, panel, lbla=None, 
                  lblb=None, override_min_data_type2=None):
        btn.SetFocus()
        btn.SetDefault()
        self.btn_to_rollback.SetBitmapLabel(self.bmp_to_rollback_to)
        self.btn_to_rollback = btn
        self.bmp_to_rollback_to = btn_bmp
        btn.SetBitmapLabel(btn_sel_bmp)
        event.Skip()
        if self.panel_displayed == panel:
            return # just reclicking on same one
        lbla = lbla if lbla else mg.CHART_VALUES
        lblb = lblb if lblb else mg.CHART_BY
        self.lbl_var1.SetLabel(u"%s:" % lbla)
        self.lbl_var2.SetLabel(u"%s:" % lblb)
        self.panel_top.Layout()
        self.min_data_type = mg.CHART_TYPE_TO_MIN_DATA_TYPE.get(self.chart_type, 
                                                                mg.VAR_TYPE_CAT)
        self.panel_displayed.Show(False)        
        varname1, varname2, varname3 = self.get_vars()
        # var 1
        self.setup_var(self.drop_var1, mg.VAR_1_DEFAULT, 
                       self.sorted_var_names1, varname1)
        # var 2
        if override_min_data_type2:
            self.min_data_type2 = override_min_data_type2
        else:
            self.min_data_type2 = self.min_data_type
        inc_drop_select = (self.chart_type in mg.OPTIONAL_ONE_VAR_CHART_TYPES)
        self.setup_var(self.drop_var2, mg.VAR_2_DEFAULT, self.sorted_var_names2, 
                       varname2, inc_drop_select, 
                       override_min_data_type=self.min_data_type2)
        self.drop_var2.Enable(True)
        self.lbl_var2.Enable(True)
        # var 3
        if self.chart_type in mg.THREE_VAR_CHART_TYPES:
            self.setup_var(self.drop_var3, mg.VAR_3_DEFAULT, 
                           self.sorted_var_names3, varname3, 
                           inc_drop_select=False, 
                           override_min_data_type=mg.VAR_TYPE_CAT)
            self.drop_var3.Show()
            self.lbl_var3.Show()
            self.panel_top.Layout()
        else:
            self.drop_var3.Hide()
            self.lbl_var3.Hide()
        self.szr_mid.Remove(self.panel_displayed)
        self.szr_mid.Add(panel, 0, wx.GROW)
        self.panel_displayed = panel
        panel.Show(True)
        self.panel_mid.Layout() # self.Layout() doesn't work in Windows
           
    def on_btn_bar_chart(self, event):
        self.chart_type = mg.SIMPLE_BARCHART
        btn = self.btn_bar_chart
        btn_bmp = self.bmp_btn_bar_chart
        btn_bmp_sel = self.bmp_btn_bar_chart_sel
        panel = self.panel_bar_chart
        self.rad_bar_sort_opts.SetSelection(mg.SORT_OPTS.index(CUR_SORT_OPT))
        self.chk_simple_bar_perc.SetValue(INC_PERC)
        self.btn_chart(event, btn, btn_bmp, btn_bmp_sel, panel,
                       lblb=mg.CHART_CHART_BY)

    def on_btn_clustered_bar_chart(self, event):
        self.chart_type = mg.CLUSTERED_BARCHART
        btn = self.btn_clust_bar_chart
        btn_bmp = self.bmp_btn_clust_bar_chart
        btn_bmp_sel = self.bmp_btn_clust_bar_chart_sel
        panel = self.panel_clustered_bar_chart
        self.chk_clust_bar_perc.SetValue(INC_PERC)
        self.btn_chart(event, btn, btn_bmp, btn_bmp_sel, panel)

    def on_btn_pie_chart(self, event):
        self.chart_type = mg.PIE_CHART
        btn = self.btn_pie_chart
        btn_bmp = self.bmp_btn_pie_chart
        btn_bmp_sel = self.bmp_btn_pie_chart_sel
        panel = self.panel_pie_chart
        self.rad_pie_sort_opts.SetSelection(mg.SORT_OPTS.index(CUR_SORT_OPT))
        self.btn_chart(event, btn, btn_bmp, btn_bmp_sel, panel, 
                       lblb=mg.CHART_CHART_BY)
        
    def on_btn_line_chart(self, event):
        self.chart_type = mg.LINE_CHART
        btn = self.btn_line_chart
        btn_bmp = self.bmp_btn_line_chart
        btn_bmp_sel = self.bmp_btn_line_chart_sel
        panel = self.panel_line_chart
        self.chk_line_perc.SetValue(INC_PERC)
        self.btn_chart(event, btn, btn_bmp, btn_bmp_sel, panel)

    def on_btn_area_chart(self, event):
        self.chart_type = mg.AREA_CHART
        btn = self.btn_area_chart
        btn_bmp = self.bmp_btn_area_chart
        btn_bmp_sel = self.bmp_btn_area_chart_sel
        panel = self.panel_area_chart
        self.chk_area_perc.SetValue(INC_PERC)
        self.btn_chart(event, btn, btn_bmp, btn_bmp_sel, panel,
                       lblb=mg.CHART_CHART_BY)

    def on_btn_histogram(self, event):
        self.chart_type = mg.HISTOGRAM
        btn = self.btn_histogram
        btn_bmp = self.bmp_btn_histogram
        btn_bmp_sel = self.bmp_btn_histogram_sel
        panel = self.panel_histogram
        self.btn_chart(event, btn, btn_bmp, btn_bmp_sel, panel,
                       lblb=mg.CHART_CHART_BY,
                       override_min_data_type2=mg.VAR_TYPE_CAT)

    def on_btn_scatterplot(self, event):
        self.chart_type = mg.SCATTERPLOT
        btn = self.btn_scatterplot
        btn_bmp = self.bmp_btn_scatterplot
        btn_bmp_sel = self.bmp_btn_scatterplot_sel
        panel = self.panel_scatterplot
        self.btn_chart(event, btn, btn_bmp, btn_bmp_sel, panel, 
                       lbla=_(u"X-axis"), lblb=_(u"Y-axis"))
        
    def on_btn_chart(self, event):
        wx.MessageBox(LIMITS_MSG)

    def on_btn_run(self, event):
        # get settings
        if self.chart_type not in []:
            run_ok = self.test_config_ok()
            add_to_report = self.chk_add_to_report.IsChecked()
            if run_ok:
                get_script_args=[cc[mg.CURRENT_CSS_PATH], add_to_report,
                                 cc[mg.CURRENT_REPORT_PATH]]
                config_dlg.ConfigDlg.on_btn_run(self, event, OUTPUT_MODULES, 
                                                get_script_args, 
                                                new_has_dojo=True)
        else:
            wx.MessageBox(LIMITS_MSG)

    def on_btn_script(self, event):
        # TODO NB will have new_has_dojo=True
        wx.MessageBox(u"This version does not support exporting chart code yet")
    
    def on_var1_sel(self, event):
        pass
        
    def on_var2_sel(self, event):
        pass
    
    def on_var3_sel(self, event):
        pass
    
    def add_other_var_opts(self, szr=None):
        pass

    def on_rclick_var1(self, event):
        self.on_rclick_var(self.drop_var1, self.sorted_var_names1)
        
    def on_rclick_var2(self, event):
        self.on_rclick_var(self.drop_var2, self.sorted_var_names2)
        
    def on_rclick_var3(self, event):
        self.on_rclick_var(self.drop_var3, self.sorted_var_names3)
        
    def on_rclick_var(self, drop_var, sorted_var_names):
        var_name, choice_item = self.get_var_dets(drop_var, sorted_var_names)
        if var_name == mg.DROP_SELECT:
            return
        var_label = lib.get_item_label(self.var_labels, var_name)
        updated = projects.set_var_props(choice_item, var_name, var_label, 
                                         self.var_labels, self.var_notes, 
                                         self.var_types,  self.val_dics)
        if updated:
            self.refresh_vars()
    
    def refresh_vars(self):
        varname1, varname2, varname3 = self.get_vars()
        self.setup_var(self.drop_var1, mg.VAR_1_DEFAULT, self.sorted_var_names1, 
                       varname1)
        inc_drop_select = (self.chart_type in mg.OPTIONAL_ONE_VAR_CHART_TYPES)
        self.setup_var(self.drop_var2, mg.VAR_2_DEFAULT, self.sorted_var_names2,
                       varname2, inc_drop_select, 
                       override_min_data_type=self.min_data_type2)
        self.setup_var(self.drop_var3, mg.VAR_3_DEFAULT, 
                       self.sorted_var_names3, varname3, 
                       inc_drop_select=False, 
                       override_min_data_type=mg.VAR_TYPE_CAT)
        self.update_defaults()

    def on_database_sel(self, event):
        """
        Reset dbe, database, cursor, tables, table, tables dropdown, 
            fields, has_unique, and idxs after a database selection.
        """
        config_dlg.ConfigDlg.on_database_sel(self, event)
        # now update var dropdowns
        self.update_var_dets()
        self.setup_var(self.drop_var1, mg.VAR_1_DEFAULT, self.sorted_var_names1)
        inc_drop_select = (self.chart_type in mg.OPTIONAL_ONE_VAR_CHART_TYPES)
        self.setup_var(self.drop_var2, mg.VAR_2_DEFAULT, self.sorted_var_names2, 
                       var_name=None, inc_drop_select=inc_drop_select,
                       override_min_data_type=self.min_data_type2)
        self.setup_var(self.drop_var3, mg.VAR_3_DEFAULT, 
                       self.sorted_var_names3, var_name=None, 
                       inc_drop_select=False, 
                       override_min_data_type=mg.VAR_TYPE_CAT)
                
    def on_table_sel(self, event):
        "Reset key data details after table selection."       
        config_dlg.ConfigDlg.on_table_sel(self, event)
        # now update var dropdowns
        self.update_var_dets()
        self.setup_var(self.drop_var1, mg.VAR_1_DEFAULT, self.sorted_var_names1)
        inc_drop_select = (self.chart_type in mg.OPTIONAL_ONE_VAR_CHART_TYPES)
        self.setup_var(self.drop_var2, mg.VAR_2_DEFAULT, self.sorted_var_names2, 
                       var_name=None, inc_drop_select=inc_drop_select,
                       override_min_data_type=self.min_data_type2)
        self.setup_var(self.drop_var3, mg.VAR_3_DEFAULT, 
                       self.sorted_var_names3, var_name=None, 
                       inc_drop_select=False, 
                       override_min_data_type=mg.VAR_TYPE_CAT)
       
    def on_btn_config(self, event):
        """
        Want to retain already selected item - even though label and even 
            position may have changed.
        """
        varname1, varname2, varname3 = self.get_vars()
        config_dlg.ConfigDlg.on_btn_config(self, event)
        self.setup_var(self.drop_var1, mg.VAR_1_DEFAULT, self.sorted_var_names1, 
                       varname1)
        inc_drop_select = (self.chart_type in mg.OPTIONAL_ONE_VAR_CHART_TYPES)
        self.setup_var(self.drop_var2, mg.VAR_2_DEFAULT, self.sorted_var_names2, 
                       varname2, inc_drop_select=inc_drop_select,
                       override_min_data_type=self.min_data_type2)
        self.setup_var(self.drop_var3, mg.VAR_3_DEFAULT, 
                       self.sorted_var_names3, varname3, 
                       inc_drop_select=False, 
                       override_min_data_type=mg.VAR_TYPE_CAT)
        self.update_defaults()

    def get_vars(self):
        """
        self.sorted_var_names_by and self.sorted_var_names1, 2, and 3 are set 
            when dropdowns are set (and only changed when reset).
        """
        varname1, unused = self.get_var_dets(self.drop_var1, 
                                             self.sorted_var_names1)
        varname2, unused = self.get_var_dets(self.drop_var2, 
                                             self.sorted_var_names2)
        varname3, unused = self.get_var_dets(self.drop_var3, 
                                             self.sorted_var_names3)
        return varname1, varname2, varname3
    
    def update_defaults(self):
        mg.VAR_1_DEFAULT = self.drop_var1.GetStringSelection()
        mg.VAR_2_DEFAULT = self.drop_var2.GetStringSelection()
        try: # might not be visible
            mg.VAR_3_DEFAULT = self.drop_var3.GetStringSelection()
        except Exception, e:
            pass
   
    def update_phrase(self):
        pass

    def test_config_ok(self):
        """
        Are the appropriate selections made to enable an analysis to be run?
        """
        # main and group by averaged variables cannot be the same
        if (self.chart_type == mg.CLUSTERED_BARCHART and
                self.drop_var2.GetStringSelection() == mg.DROP_SELECT):
            wx.MessageBox(_("A selection must be made for Variable 2"))
            return False
        if (self.drop_var1.GetStringSelection() ==
                self.drop_var2.GetStringSelection()):
            wx.MessageBox(_("Variable 1 and 2 cannot be the same"))
            return False
        return True

    def get_script(self, css_idx, css_fil, add_to_report, report_name):
        "Build script from inputs"
        debug = False
        inc_perc = u"True" if INC_PERC else u"False"
        script_lst = []
        titles, subtitles = self.get_titles()
        script_lst.append(u"titles=%s" % unicode(titles))
        script_lst.append(u"subtitles=%s" % unicode(subtitles))
        script_lst.append(lib.get_tbl_filt_clause(dd.dbe, dd.db, dd.tbl))
        varname1, varname2, varname3 = self.get_vars()
        # var 1
        var1lbl = u"fld_x_axis" if self.chart_type == mg.SCATTERPLOT \
                                                else u"fld_measure"
        script_lst.append(u"%s = u\"%s\"" % (var1lbl, varname1))
        script_lst.append(u"%s_name=u\"%s\"" % (var1lbl,
                          lib.get_item_label(self.var_labels, varname1)))
        script_lst.append(u"%s_lbls = %s" % (var1lbl,
                          self.val_dics.get(varname1, {})))
        # var 2
        var2lbl = u"fld_y_axis" if self.chart_type == mg.SCATTERPLOT \
                                                else u"fld_gp"
        if varname2 == mg.DROP_SELECT:
            script_lst.append(u"%s = None" % var2lbl)
        else:
            script_lst.append(u"%s = u\"%s\"" % (var2lbl, varname2))
        script_lst.append(u"%s_name=u\"%s\"" % (var2lbl,
                          lib.get_item_label(self.var_labels, varname2)))
        script_lst.append(u"%s_lbls = %s" % (var2lbl, 
                                             self.val_dics.get(varname2, {})))
        # var 3
        
        
        
        
        script_lst.append(u"add_to_report = %s" % ("True" if add_to_report
                          else "False"))
        script_lst.append(u"report_name = u\"%s\"" %
                          lib.escape_pre_write(report_name))
        if self.chart_type == mg.SIMPLE_BARCHART:
            script_lst.append(get_simple_barchart_script(inc_perc, css_fil, 
                                                         css_idx))
        elif self.chart_type == mg.CLUSTERED_BARCHART:
            script_lst.append(get_clustered_barchart_script(inc_perc, css_fil, 
                                                    css_idx, self.chart_type))
        elif self.chart_type == mg.PIE_CHART:
            script_lst.append(get_pie_chart_script(css_fil, css_idx))
        elif self.chart_type == mg.LINE_CHART:
            script_lst.append(get_line_chart_script(inc_perc, css_fil, css_idx, 
                                                    self.chart_type, varname2))
        elif self.chart_type == mg.AREA_CHART:
            script_lst.append(get_area_chart_script(inc_perc, css_fil, css_idx))
        elif self.chart_type == mg.HISTOGRAM:
            script_lst.append(get_histogram_script(css_fil, css_idx))
        elif self.chart_type == mg.SCATTERPLOT:
            script_lst.append(get_scatterplot_script(css_fil, css_idx, 
                                       dot_border=self.chk_borders.IsChecked()))
        script_lst.append(u"fil.write(chart_output)")
        return u"\n".join(script_lst)
    

def get_simple_barchart_script(inc_perc, css_fil, css_idx):
    script = u"""
simple_barchart_dets = charting_output.get_single_val_dets(
            dbe="%(dbe)s", cur=cur, tbl=tbl, tbl_filt=tbl_filt, 
            fld_gp=fld_gp, fld_gp_name=fld_gp_name, fld_gp_lbls=fld_gp_lbls, 
            fld_measure=fld_measure, fld_measure_lbls=fld_measure_lbls, 
            sort_opt="%(sort_opt)s")
barchart_dets = []
for simple_barchart_det in simple_barchart_dets:
    chart_by_label = simple_barchart_det[mg.CHART_CHART_BY_LABEL]
    xaxis_dets = simple_barchart_det[mg.CHART_MEASURE_DETS]
    y_vals = simple_barchart_det[mg.CHART_Y_VALS]
    series_dets = [{u"label": fld_measure_name, "y_vals": y_vals},]
    barchart_dets.append({mg.CHART_CHART_BY_LABEL: chart_by_label,
                          mg.CHART_XAXIS_DETS: xaxis_dets, 
                          mg.CHART_SERIES_DETS: series_dets})
x_title = u""
chart_output = charting_output.barchart_output(titles, subtitles,
            x_title, barchart_dets, inc_perc=%(inc_perc)s, 
            css_fil="%(css_fil)s", css_idx=%(css_idx)s, 
            page_break_after=False)
    """ % {u"dbe": dd.dbe, u"sort_opt": CUR_SORT_OPT, u"inc_perc": inc_perc, 
           u"css_fil": lib.escape_pre_write(css_fil), u"css_idx": css_idx}
    return script

def get_clustered_barchart_script(inc_perc, css_fil, css_idx, chart_type):
    script = u"""
xaxis_dets, max_label_len, series_dets = charting_output.get_grouped_val_dets(
            chart_type="%(chart_type)s", dbe="%(dbe)s", cur=cur, tbl=tbl, 
            tbl_filt=tbl_filt, fld_gp=fld_gp, fld_gp_lbls=fld_gp_lbls, 
            fld_measure=fld_measure, fld_measure_lbls=fld_measure_lbls)
chart_by_label = mg.CHART_CHART_BY_LABEL_ALL
barchart_dets = [{mg.CHART_CHART_BY_LABEL: chart_by_label,
                  mg.CHART_XAXIS_DETS: xaxis_dets, 
                  mg.CHART_SERIES_DETS: series_dets}]
chart_output = charting_output.barchart_output(titles, subtitles,
            fld_measure_name, barchart_dets, inc_perc=%(inc_perc)s, 
            css_fil="%(css_fil)s", css_idx=%(css_idx)s, page_break_after=False)    
    """ % {u"dbe": dd.dbe, u"chart_type": chart_type, u"inc_perc": inc_perc, 
           u"css_fil": lib.escape_pre_write(css_fil), u"css_idx": css_idx}
    return script

def get_pie_chart_script(css_fil, css_idx):
    script = u"""
pie_chart_dets = charting_output.get_pie_chart_dets(dbe="%(dbe)s", cur=cur, 
            tbl=tbl, tbl_filt=tbl_filt, 
            fld_gp=fld_gp, fld_gp_name=fld_gp_name, fld_gp_lbls=fld_gp_lbls, 
            fld_measure=fld_measure, fld_measure_lbls=fld_measure_lbls, 
            sort_opt="%(sort_opt)s")
chart_output = charting_output.piechart_output(titles, subtitles,
            pie_chart_dets, css_fil="%(css_fil)s", css_idx=%(css_idx)s,
            page_break_after=False)
    """ % {u"dbe": dd.dbe, u"sort_opt": CUR_SORT_OPT,  
           u"css_fil": lib.escape_pre_write(css_fil), u"css_idx": css_idx}
    return script

def get_line_chart_script(inc_perc, css_fil, css_idx, chart_type, varname2):
    single_line = (varname2 == mg.DROP_SELECT)
    if single_line:
        script = u"""
single_linechart_dets = charting_output.get_single_val_dets(
            dbe="%(dbe)s", cur=cur, tbl=tbl, tbl_filt=tbl_filt, 
            fld_gp=fld_gp, fld_gp_name=fld_gp_name, fld_gp_lbls=fld_gp_lbls, 
            fld_measure=fld_measure, fld_measure_lbls=fld_measure_lbls, 
            sort_opt=mg.SORT_NONE)
chart_by_label = single_linechart_dets[0][mg.CHART_CHART_BY_LABEL]
xaxis_dets = single_linechart_dets[0][mg.CHART_MEASURE_DETS]
y_vals = single_linechart_dets[0][mg.CHART_Y_VALS]
max_label_len = single_linechart_dets[0][mg.CHART_MAX_LABEL_LEN]
series_dets = [{u"label": fld_measure_name, "y_vals": y_vals},]
x_title = u""
        """ % {u"dbe": dd.dbe}
    else:
        script = u"""
xaxis_dets, max_label_len, series_dets = charting_output.get_grouped_val_dets(
            chart_type="%(chart_type)s", dbe="%(dbe)s", cur=cur, tbl=tbl, 
            tbl_filt=tbl_filt, fld_gp=fld_gp, fld_gp_lbls=fld_gp_lbls, 
            fld_measure=fld_measure, fld_measure_lbls=fld_measure_lbls)
x_title = fld_measure_name
        """ % {u"chart_type": chart_type, u"dbe": dd.dbe}
    script += u"""
chart_output = charting_output.linechart_output(titles, subtitles, x_title, 
            xaxis_dets, max_label_len, series_dets, inc_perc=%(inc_perc)s, 
            css_fil="%(css_fil)s", css_idx=%(css_idx)s, page_break_after=False)
    """ % {u"inc_perc": inc_perc, u"css_fil": lib.escape_pre_write(css_fil), 
           u"css_idx": css_idx}
    return script

def get_area_chart_script(inc_perc, css_fil, css_idx):
    script = u"""
areachart_dets = charting_output.get_single_val_dets(
            dbe="%(dbe)s", cur=cur, tbl=tbl, tbl_filt=tbl_filt, 
            fld_gp=fld_gp, fld_gp_name=fld_gp_name, fld_gp_lbls=fld_gp_lbls, 
            fld_measure=fld_measure, fld_measure_lbls=fld_measure_lbls, 
            sort_opt=mg.SORT_NONE)
chart_dets = []
for areachart_det in areachart_dets:
    chart_by_label = areachart_det[mg.CHART_CHART_BY_LABEL]
    xaxis_dets = areachart_det[mg.CHART_MEASURE_DETS]
    y_vals = areachart_det[mg.CHART_Y_VALS]
    series_dets = [{u"label": fld_measure_name, "y_vals": y_vals},]
    max_label_len = areachart_det[mg.CHART_MAX_LABEL_LEN]
    chart_dets.append({mg.CHART_CHART_BY_LABEL: chart_by_label,
                       mg.CHART_XAXIS_DETS: xaxis_dets, 
                       mg.CHART_SERIES_DETS: series_dets,
                       mg.CHART_MAX_LABEL_LEN: max_label_len})
chart_output = charting_output.areachart_output(titles, subtitles,
            chart_dets, inc_perc=%(inc_perc)s,
            css_fil="%(css_fil)s", css_idx=%(css_idx)s, page_break_after=False)
    """ % {u"dbe": dd.dbe, u"inc_perc": inc_perc, 
           u"css_fil": lib.escape_pre_write(css_fil), u"css_idx": css_idx}
    return script

def get_histogram_script(css_fil, css_idx):
    script = u"""
histo_dets = charting_output.get_histo_dets(dbe="%(dbe)s", cur=cur, tbl=tbl, 
            tbl_filt=tbl_filt, 
            fld_gp=fld_gp, fld_gp_name=fld_gp_name, fld_gp_lbls=fld_gp_lbls,
            fld_measure=fld_measure)
chart_output = charting_output.histogram_output(titles, subtitles, 
            fld_measure_name, histo_dets, css_fil="%(css_fil)s", 
            css_idx=%(css_idx)s, page_break_after=False)
    """ % {u"dbe": dd.dbe, u"css_fil": lib.escape_pre_write(css_fil), 
           u"css_idx": css_idx}
    return script

def get_scatterplot_script(css_fil, css_idx, dot_border):
    script = u"""
sample_a, sample_b, data_tups = core_stats.get_paired_data(dbe=u"%(dbe)s",
        cur=cur, tbl=tbl, tbl_filt=tbl_filt, fld_a=fld_x_axis, 
        fld_b=fld_y_axis, unique=True) # only need unique combos for plotting
if data_tups:
    scatter_data = [{mg.SAMPLE_A: sample_a, mg.SAMPLE_B: sample_b,
                     mg.DATA_TUPS: data_tups},]
else:
    scatter_data = []
chart_output = charting_output.scatterplot_output(titles, subtitles,
            scatter_data, fld_x_axis_name, fld_y_axis_name, add_to_report, 
            report_name, %(dot_border)s, css_fil="%(css_fil)s", 
            css_idx=%(css_idx)s, page_break_after=False)
    """ % {u"dbe": dd.dbe, u"css_fil": lib.escape_pre_write(css_fil), 
           u"css_idx": css_idx, u"dot_border": dot_border}
    return script