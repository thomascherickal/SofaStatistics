#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import wx

import my_globals as mg
import lib
import config_output
import config_ui
import full_html
import getdata
import indep2var
import output
import projects

CUR_SORT_OPT_LBL = mg.SORT_VALUE_LBL
CUR_DATA_OPT_LBL = mg.SHOW_FREQ_LBL
ROTATE = False
MAJOR = False
HIDE_MARKERS = False
BARS_SORTED_LBL = u"bars"
CLUSTERS_SORTED_LBL = u"clusters"
SLICES_SORTED_LBL = u"slices"
GROUPS_SORTED_LBL = u"groups"

"""
If sorting of x-axis not explicit, will be sort_opt=mg.SORT_VALUE_LBL and will 
thus be sorted by values not labels and order of values determined by GROUP BY
in database engine used. See specifics in, for example, get_line_chart_script().

Value dropdowns have to be built fresh each time the data source changes because
in Linux the process of changing the values list dynamically is far too slow 
when a non-system font is chosen. Much, much quicker to build a fresh one each 
time with the new list as the initial value.
"""

class DlgCharting(indep2var.DlgIndep2VarConfig):

    inc_gp_by_select = True
    range_gps = False
    
    def __init__(self, title):
        # see http://old.nabble.com/wx.StaticBoxSizer-td21662703.html
        if mg.MAX_HEIGHT <= 620:
            myheight = 600
        elif mg.MAX_HEIGHT <= 870:
            myheight = mg.MAX_HEIGHT - 70
        else:
            myheight = 800
        # can't use indep2var.DlgIndep2VarConfig - too many differences
        # so must init everything manually here
        wx.Dialog.__init__(self, parent=None, id=-1, title=title, 
            pos=(mg.HORIZ_OFFSET, 0), size=(1024, myheight),
            style=wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX|wx.RESIZE_BORDER|wx.CLOSE_BOX
            |wx.SYSTEM_MENU|wx.CAPTION|wx.CLIP_CHILDREN)
        config_ui.ConfigUI.__init__(self, autoupdate=True)
        if mg.PLATFORM == mg.WINDOWS:
            self.checkbox2use = lib.MultilineCheckBox
        else:
            self.checkbox2use = lib.StdCheckBox
        self.exiting = False
        self.title = title
        self.SetFont(mg.GEN_FONT)
        cc = output.get_cc()
        self.output_modules = ["my_globals as mg", "core_stats", 
            "charting_output", "output", "getdata"]
        global CUR_DATA_OPT_LBL
        CUR_DATA_OPT_LBL = mg.SHOW_FREQ_LBL
        self.min_data_type = None # not used in charting_dlg unlike most other dlgs - need fine-grained control of 
        # up to 4 drop downs
        self.Bind(wx.EVT_CLOSE, self.on_btn_close)
        self.url_load = True # btn_expand
        (self.var_labels, self.var_notes, 
         self.var_types, 
         self.val_dics) = lib.get_var_dets(cc[mg.CURRENT_VDTS_PATH])
        self.variables_rc_msg = _("Right click variables to view/edit details")
        config_output.add_icon(frame=self)
        self.szr_main = wx.BoxSizer(wx.VERTICAL)
        # top panel
        self.panel_data = wx.Panel(self)
        self.szr_help_data = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_vars = wx.Panel(self)
        # key settings
        hide_db = projects.get_hide_db()
        self.drop_tbls_panel = self.panel_data
        self.drop_tbls_system_font_size = False
        self.drop_tbls_sel_evt = self.on_table_sel
        self.drop_tbls_idx_in_szr = 3 if not hide_db else 1 # 2 fewer items
        self.drop_tbls_rmargin = 10
        self.drop_tbls_can_grow = False
        self.szr_data = self.get_szr_data(self.panel_data, hide_db=hide_db) # mixin
        self.drop_tbls_szr = self.szr_data
        getdata.data_dropdown_settings_correct(parent=self)
        # variables
        bx_vars = wx.StaticBox(self.panel_vars, -1, _("Variables"))
        self.szr_vars = wx.StaticBoxSizer(bx_vars, wx.HORIZONTAL)
        if mg.PLATFORM == mg.LINUX: # http://trac.wxwidgets.org/ticket/9859
            bx_vars.SetToolTipString(self.variables_rc_msg)
        # misc
        self.btn_help = wx.Button(self.panel_data, wx.ID_HELP)
        self.btn_help.Bind(wx.EVT_BUTTON, self.on_btn_help)
        szr_chart_btns = wx.BoxSizer(wx.HORIZONTAL)
        self.chart_type = mg.SIMPLE_BARCHART
        self.setup_var_dropdowns()
        self.panel_vars.SetSizer(self.szr_vars)
        self.szr_vars.SetSizeHints(self.panel_vars)
        # layout
        help_down_by = 27 if mg.PLATFORM == mg.MAC else 17
        self.szr_help_data.Add(self.btn_help, 0, wx.TOP, help_down_by)
        self.szr_help_data.Add(self.szr_data, 1, wx.LEFT, 5)
        # assemble sizer for help_data panel
        self.panel_data.SetSizer(self.szr_help_data)
        self.szr_help_data.SetSizeHints(self.panel_data)
        # chart buttons
        self.panel_mid = wx.Panel(self)
        bx_charts = wx.StaticBox(self.panel_mid, -1, _("Chart Types"))
        self.szr_mid = wx.StaticBoxSizer(bx_charts, wx.VERTICAL)
        self.setup_chart_btns(szr_chart_btns)
        self.szr_mid.Add(szr_chart_btns, 0, wx.GROW)
        if mg.PLATFORM == mg.LINUX: # http://trac.wxwidgets.org/ticket/9859
            bx_charts.SetToolTipString(_("Make chart"))
        # Chart Settings
        if mg.PLATFORM == mg.WINDOWS:
            self.tickbox_down_by = 10 # to line up with a combo
        elif mg.PLATFORM == mg.LINUX:
            self.tickbox_down_by = 10
        else:
            self.tickbox_down_by = 10
        # setup charts
        self.setup_simple_bar()
        self.setup_clust_bar()
        self.setup_pie()
        self.setup_line()
        self.setup_area()
        self.setup_histogram()
        self.setup_scatterplot()
        self.setup_boxplot()
        # Hide all panels except default. Display and layout then hide.
        # Prevents flicker on change later.
        panels2hide = [self.panel_clust_bar, self.panel_pie_chart,
            self.panel_line_chart, self.panel_area_chart, self.panel_histogram, 
            self.panel_scatterplot, self.panel_boxplot]
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
        self.szr_bottom = wx.BoxSizer(wx.VERTICAL)
        szr_titles = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_output_config = self.get_szr_output_config(self.panel_bottom) # mixin
        szr_lower = wx.BoxSizer(wx.HORIZONTAL)
        # titles, subtitles
        lbl_titles = wx.StaticText(self.panel_bottom, -1, _("Title:"))
        lbl_titles.SetFont(mg.LABEL_FONT)
        title_height = 40 if mg.PLATFORM == mg.MAC else 20
        self.txt_titles = wx.TextCtrl(self.panel_bottom, -1, 
            size=(250,title_height), style=wx.TE_MULTILINE)
        lbl_subtitles = wx.StaticText(self.panel_bottom, -1, _("Subtitle:"))
        lbl_subtitles.SetFont(mg.LABEL_FONT)
        self.txt_subtitles = wx.TextCtrl(self.panel_bottom, -1, 
            size=(250,title_height), style=wx.TE_MULTILINE)
        szr_titles.Add(lbl_titles, 0, wx.RIGHT, 5)
        szr_titles.Add(self.txt_titles, 1, wx.RIGHT, 10)
        szr_titles.Add(lbl_subtitles, 0, wx.RIGHT, 5)
        szr_titles.Add(self.txt_subtitles, 1)
        self.szr_output_display = self.get_szr_output_display(self.panel_bottom, 
            inc_clear=False, idx_style=1) # mixin
        self.html = full_html.FullHTML(panel=self.panel_bottom, parent=self, 
            size=(200, 150))
        if mg.PLATFORM == mg.MAC:
            self.html.Bind(wx.EVT_WINDOW_CREATE, self.on_show)
        else:
            self.Bind(wx.EVT_SHOW, self.on_show)
        self.szr_bottom.Add(szr_titles, 0, wx.GROW|wx.LEFT|wx.TOP|wx.RIGHT|
            wx.BOTTOM, 10)
        self.szr_bottom.Add(self.szr_output_config, 0, 
            wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szr_lower.Add(self.html, 1, wx.GROW)
        szr_lower.Add(self.szr_output_display, 0, wx.GROW|wx.LEFT, 10)
        self.szr_bottom.Add(szr_lower, 2, wx.GROW|wx.LEFT|wx.RIGHT|
            wx.BOTTOM|wx.TOP, 10)
        self.add_other_var_opts()
        self.panel_bottom.SetSizer(self.szr_bottom)
        self.szr_bottom.SetSizeHints(self.panel_bottom)
        # assemble entire frame
        static_box_gap = 0 if mg.PLATFORM == mg.MAC else 5
        if static_box_gap:
            self.szr_main.Add(wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, 
                static_box_gap)
        self.szr_main.Add(self.panel_data, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        if static_box_gap:
            self.szr_main.Add(wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, 
                static_box_gap)
        self.szr_main.Add(self.panel_mid, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        if static_box_gap:
            self.szr_main.Add(wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, 
                static_box_gap)
        self.szr_main.Add(self.panel_vars, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        self.szr_main.Add(self.panel_bottom, 1, wx.GROW)
        self.SetAutoLayout(True)
        self.SetSizer(self.szr_main)
        szr_lst = [self.szr_help_data, self.szr_vars, self.szr_mid, 
            self.szr_bottom] # each has a panel of its own
        lib.set_size(window=self, szr_lst=szr_lst, width_init=1024, 
            height_init=myheight)
    
    def get_drop_val_opts(self, panel):
        drop_opts = wx.Choice(panel, -1, choices=mg.DATA_SHOW_OPT_LBLS, 
            size=(90,-1))
        drop_opts.SetFont(mg.GEN_FONT)
        idx_data_opt = mg.DATA_SHOW_OPT_LBLS.index(CUR_DATA_OPT_LBL)
        drop_opts.SetSelection(idx_data_opt)
        drop_opts.Bind(wx.EVT_CHOICE, self.on_drop_val)
        drop_opts.SetToolTipString(u"Report count(frequency), percentage, "
                                   u"average, or sum?")
        return drop_opts
    
    def get_drop_sort_opts(self, panel, choices=mg.STD_SORT_OPT_LBLS):
        drop_opts = wx.Choice(panel, -1, choices=choices, size=(100,-1))
        drop_opts.SetFont(mg.GEN_FONT)
        idx_current_sort_opt = mg.STD_SORT_OPT_LBLS.index(CUR_SORT_OPT_LBL)
        drop_opts.SetSelection(idx_current_sort_opt)
        drop_opts.Bind(wx.EVT_CHOICE, self.on_drop_sort)
        drop_opts.SetToolTipString(_(u"Sort order for categories"))
        return drop_opts
    
    def setup_simple_bar(self):
        self.szr_bar_chart = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_bar_chart = wx.Panel(self.panel_mid)
        lbl_val = wx.StaticText(self.panel_bar_chart, -1, 
                                  _(u"Data\nreported:"))
        lbl_val.SetFont(mg.LABEL_FONT)
        self.drop_bar_val = self.get_drop_val_opts(self.panel_bar_chart)
        lbl_sort = wx.StaticText(self.panel_bar_chart, -1, 
                                 _(u"Sort order\nof %s:") % BARS_SORTED_LBL)
        lbl_sort.SetFont(mg.LABEL_FONT)
        self.drop_bar_sort = self.get_drop_sort_opts(self.panel_bar_chart)
        self.chk_simple_bar_rotate = self.get_chk_rotate(self.panel_bar_chart)
        self.chk_bar_borders = wx.CheckBox(self.panel_bar_chart, -1, 
                                           _("Bar borders?"))
        self.chk_bar_borders.SetFont(mg.GEN_FONT)
        self.chk_bar_borders.SetValue(False)
        self.chk_bar_borders.SetToolTipString(_("Show borders around bars?"))
        self.szr_bar_chart.Add(lbl_val, 0, wx.TOP|wx.RIGHT, 5)
        self.szr_bar_chart.Add(self.drop_bar_val, 0, wx.TOP, 5)
        self.szr_bar_chart.AddSpacer(10)
        self.szr_bar_chart.Add(lbl_sort, 0, wx.TOP|wx.RIGHT, 5)
        self.szr_bar_chart.Add(self.drop_bar_sort, 0, wx.TOP, 5)
        self.szr_bar_chart.AddSpacer(10)
        self.szr_bar_chart.Add(self.chk_simple_bar_rotate, 0, wx.TOP, 
                               self.tickbox_down_by)
        self.szr_bar_chart.AddSpacer(10)
        self.szr_bar_chart.Add(self.chk_bar_borders, 0, wx.TOP, 
                               self.tickbox_down_by)
        self.panel_bar_chart.SetSizer(self.szr_bar_chart)
        self.szr_bar_chart.SetSizeHints(self.panel_bar_chart)
        
    def setup_clust_bar(self):
        self.szr_clust_bar_chart = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_clust_bar = wx.Panel(self.panel_mid)
        lbl_val = wx.StaticText(self.panel_clust_bar, -1, 
                                  _(u"Data\nreported:"))
        lbl_val.SetFont(mg.LABEL_FONT)
        self.drop_clust_val = self.get_drop_val_opts(self.panel_clust_bar)
        lbl_sort = wx.StaticText(self.panel_clust_bar, -1, 
                                 _(u"Sort order\nof %s:") % CLUSTERS_SORTED_LBL)
        lbl_sort.SetFont(mg.LABEL_FONT)
        self.drop_clust_sort = self.get_drop_sort_opts(self.panel_clust_bar,
            choices=mg.SORT_VAL_AND_LABEL_OPT_LBLS)
        self.chk_clust_bar_rotate = self.get_chk_rotate(self.panel_clust_bar)
        self.chk_clust_borders = wx.CheckBox(self.panel_clust_bar, -1, 
                                             _("Bar borders?"))
        self.chk_clust_borders.SetFont(mg.GEN_FONT)
        self.chk_clust_borders.SetValue(False)
        self.chk_clust_borders.SetToolTipString(_("Show borders around bars?"))
        self.szr_clust_bar_chart.Add(lbl_val, 0, wx.TOP|wx.RIGHT, 5)
        self.szr_clust_bar_chart.Add(self.drop_clust_val, 0, wx.TOP, 5)
        self.szr_clust_bar_chart.AddSpacer(10)
        self.szr_clust_bar_chart.Add(lbl_sort, 0, wx.TOP|wx.RIGHT, 5)
        self.szr_clust_bar_chart.Add(self.drop_clust_sort, 0, wx.TOP, 5)
        self.szr_clust_bar_chart.AddSpacer(10)
        self.szr_clust_bar_chart.Add(self.chk_clust_bar_rotate, 0, wx.TOP, 
                                     self.tickbox_down_by)
        self.szr_clust_bar_chart.AddSpacer(10)
        self.szr_clust_bar_chart.Add(self.chk_clust_borders, 0, wx.TOP, 
                                     self.tickbox_down_by)
        self.panel_clust_bar.SetSizer(self.szr_clust_bar_chart)
        self.szr_clust_bar_chart.SetSizeHints(self.panel_clust_bar)
    
    def setup_pie(self):
        self.szr_pie_chart = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_pie_chart = wx.Panel(self.panel_mid)
        lbl_sort = wx.StaticText(self.panel_pie_chart, -1, 
                                 _(u"Sort order\nof %s:") % SLICES_SORTED_LBL)
        lbl_sort.SetFont(mg.LABEL_FONT)
        self.drop_pie_sort = self.get_drop_sort_opts(self.panel_pie_chart)
        self.chk_val_dets = wx.CheckBox(self.panel_pie_chart, -1, 
                                       _("Show Count and %?"))
        self.chk_val_dets.SetFont(mg.GEN_FONT)
        self.chk_val_dets.SetValue(False)
        self.chk_val_dets.SetToolTipString(_("Show Count and %?"))
        self.szr_pie_chart.Add(lbl_sort, 0, wx.TOP|wx.RIGHT, 5)
        self.szr_pie_chart.Add(self.drop_pie_sort, 0, wx.TOP|wx.RIGHT, 5)
        self.szr_pie_chart.AddSpacer(10)
        self.szr_pie_chart.Add(self.chk_val_dets, 0, wx.TOP, 
                               self.tickbox_down_by)
        self.panel_pie_chart.SetSizer(self.szr_pie_chart)
        self.szr_pie_chart.SetSizeHints(self.panel_pie_chart)
    
    def setup_line(self):
        self.szr_line_chart = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_line_chart = wx.Panel(self.panel_mid)
        lbl_val = wx.StaticText(self.panel_line_chart, -1, 
            _(u"Data\nreported:"))
        lbl_val.SetFont(mg.LABEL_FONT)
        self.drop_line_val = self.get_drop_val_opts(self.panel_line_chart)
        lbl_sort = wx.StaticText(self.panel_line_chart, -1, 
            _(u"Sort order\nof %s:") % GROUPS_SORTED_LBL)
        lbl_sort.SetFont(mg.LABEL_FONT)
        self.drop_line_sort = self.get_drop_sort_opts(self.panel_line_chart,
            choices=mg.SORT_VAL_AND_LABEL_OPT_LBLS)
        self.chk_line_time_series = self.get_chk_time_series(
            self.panel_line_chart, line=True)
        if mg.PLATFORM == mg.WINDOWS:
            smooth2use = _("Smooth line?")
            trend2use = _("Trend line?")
        else:
            smooth2use = _("Smooth\nline?")
            trend2use = _("Trend\nline?")
        self.chk_line_rotate = self.get_chk_rotate(self.panel_line_chart)
        self.chk_line_hide_markers = self.get_chk_hide_markers(
            self.panel_line_chart)
        self.chk_line_trend = self.checkbox2use(self.panel_line_chart, -1, 
            trend2use)
        self.chk_line_trend.SetFont(mg.GEN_FONT)
        self.chk_line_trend.SetToolTipString(_(u"Show trend line?"))
        self.chk_line_smooth = self.checkbox2use(self.panel_line_chart, -1, 
            smooth2use)
        self.chk_line_smooth.SetFont(mg.GEN_FONT)
        self.chk_line_smooth.SetToolTipString(_(u"Show smoothed data line?"))
        self.chk_line_major_ticks = self.get_chk_major_ticks(
            self.panel_line_chart)
        self.szr_line_chart.Add(lbl_val, 0, wx.TOP|wx.RIGHT, 5)
        self.szr_line_chart.Add(self.drop_line_val, 0, wx.TOP, 5)
        self.szr_line_chart.AddSpacer(10)
        self.szr_line_chart.Add(lbl_sort, 0, wx.TOP|wx.RIGHT, 5)
        self.szr_line_chart.Add(self.drop_line_sort, 0, wx.TOP|wx.RIGHT, 5)
        self.szr_line_chart.AddSpacer(10)
        self.szr_line_chart.Add(self.chk_line_time_series, 0, wx.TOP)
        self.szr_line_chart.AddSpacer(10)
        self.szr_line_chart.Add(self.chk_line_trend, 0, wx.TOP)
        self.szr_line_chart.AddSpacer(10)
        self.szr_line_chart.Add(self.chk_line_smooth, 0, wx.TOP)
        self.setup_line_extras()
        self.szr_line_chart.AddSpacer(10)
        self.szr_line_chart.Add(self.chk_line_rotate, 0, wx.TOP)
        self.szr_line_chart.AddSpacer(10)
        self.szr_line_chart.Add(self.chk_line_hide_markers, 0, wx.TOP)
        self.szr_line_chart.AddSpacer(10)
        self.szr_line_chart.Add(self.chk_line_major_ticks, 0, wx.TOP)
        self.panel_line_chart.SetSizer(self.szr_line_chart)
        self.szr_line_chart.SetSizeHints(self.panel_line_chart)
    
    def setup_area(self):
        self.szr_area_chart = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_area_chart = wx.Panel(self.panel_mid)
        lbl_val = wx.StaticText(self.panel_area_chart, -1,
            _(u"Data\nreported:"))
        lbl_val.SetFont(mg.LABEL_FONT)
        self.drop_area_val = self.get_drop_val_opts(self.panel_area_chart)
        lbl_sort = wx.StaticText(self.panel_area_chart, -1, 
            _(u"Sort order\nof %s:") % GROUPS_SORTED_LBL)
        lbl_sort.SetFont(mg.LABEL_FONT)
        self.drop_area_sort = self.get_drop_sort_opts(self.panel_area_chart)
        self.chk_area_time_series = self.get_chk_time_series(
            self.panel_area_chart, line=False)
        self.chk_area_rotate = self.get_chk_rotate(self.panel_area_chart)
        self.chk_area_hide_markers = self.get_chk_hide_markers(
            self.panel_area_chart)
        self.chk_area_major_ticks = self.get_chk_major_ticks(
            self.panel_area_chart)
        self.szr_area_chart.Add(lbl_val, 0, wx.TOP|wx.RIGHT, 5)
        self.szr_area_chart.Add(self.drop_area_val, 0, wx.TOP, 5)
        self.szr_area_chart.AddSpacer(10)
        self.szr_area_chart.Add(lbl_sort, 0, wx.TOP|wx.RIGHT, 5)
        self.szr_area_chart.Add(self.drop_area_sort, 0, wx.TOP|wx.RIGHT, 5)
        self.szr_area_chart.AddSpacer(10)
        self.szr_area_chart.Add(self.chk_area_time_series, 0, wx.TOP)
        self.szr_area_chart.AddSpacer(10)
        self.szr_area_chart.Add(self.chk_area_rotate, 0, wx.TOP)
        self.szr_area_chart.AddSpacer(10)
        self.szr_area_chart.Add(self.chk_area_hide_markers, 0, wx.TOP)
        self.szr_area_chart.AddSpacer(10)
        self.szr_area_chart.Add(self.chk_area_major_ticks, 0, wx.TOP)
        self.panel_area_chart.SetSizer(self.szr_area_chart)
        self.szr_area_chart.SetSizeHints(self.panel_area_chart)
    
    def setup_histogram(self):
        self.szr_histogram = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_histogram = wx.Panel(self.panel_mid)
        self.chk_show_normal = wx.CheckBox(self.panel_histogram, -1, 
                                           _("Show normal curve?"))
        self.chk_show_normal.SetFont(mg.GEN_FONT)
        self.chk_show_normal.SetValue(False)
        self.chk_show_normal.SetToolTipString(_(u"Show normal curve?"))
        self.chk_hist_borders = wx.CheckBox(self.panel_histogram, -1, 
                                             _("Bar borders?"))
        self.chk_hist_borders.SetFont(mg.GEN_FONT)
        self.chk_hist_borders.SetValue(True)
        self.chk_hist_borders.SetToolTipString(_("Show borders around bars?"))
        self.szr_histogram.Add(self.chk_show_normal, 0, 
                               wx.TOP|wx.BOTTOM|wx.LEFT, 10)
        self.szr_histogram.AddSpacer(10)
        self.szr_histogram.Add(self.chk_hist_borders, 0, wx.TOP, 
                               self.tickbox_down_by)
        self.panel_histogram.SetSizer(self.szr_histogram)
        self.szr_histogram.SetSizeHints(self.panel_histogram)
    
    def setup_scatterplot(self):
        self.szr_scatterplot = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_scatterplot = wx.Panel(self.panel_mid)
        self.chk_dot_borders = wx.CheckBox(self.panel_scatterplot, -1, 
            _("Dot borders?"))
        self.chk_dot_borders.SetFont(mg.GEN_FONT)
        self.chk_dot_borders.SetValue(True)
        self.chk_dot_borders.SetToolTipString(_("Show borders around "
            "scatterplot dots?"))
        self.chk_regression = wx.CheckBox(self.panel_scatterplot, -1, 
            _("Show regression line?"))
        self.chk_regression.SetFont(mg.GEN_FONT)
        self.chk_regression.SetValue(False)
        self.chk_regression.SetToolTipString(_("Show regression line?"))
        self.szr_scatterplot.Add(self.chk_dot_borders, 0, wx.TOP|wx.BOTTOM, 10)
        self.szr_scatterplot.Add(self.chk_regression, 0, wx.LEFT|wx.TOP|
            wx.BOTTOM, 10)
        self.panel_scatterplot.SetSizer(self.szr_scatterplot)
        self.szr_scatterplot.SetSizeHints(self.panel_scatterplot)
    
    def setup_boxplot(self):
        self.szr_boxplot = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_boxplot = wx.Panel(self.panel_mid)
        ## sort order
        lbl_sort = wx.StaticText(self.panel_boxplot, -1, 
                                 _(u"Sort order\nof %s:") % GROUPS_SORTED_LBL)
        lbl_sort.SetFont(mg.LABEL_FONT)
        self.drop_box_sort = self.get_drop_sort_opts(self.panel_boxplot, 
            choices=mg.SORT_VAL_AND_LABEL_OPT_LBLS)
        ## boxplot options
        lbl_box_opts = wx.StaticText(self.panel_boxplot, -1, _(u"Display:"))
        lbl_box_opts.SetFont(mg.LABEL_FONT)
        self.drop_box_opts = wx.Choice(self.panel_boxplot, -1,
            choices=mg.CHART_BOXPLOT_OPTIONS, size=(200,-1))
        self.drop_box_opts.SetFont(mg.GEN_FONT)
        self.drop_box_opts.SetToolTipString(_(u"Display options for whiskers "
            u"and outliers"))
        self.drop_box_opts.SetSelection(0)
        ## rotate
        self.chk_boxplot_rotate = self.get_chk_rotate(self.panel_boxplot)
        ## assemble
        self.szr_boxplot.Add(lbl_sort, 0, wx.TOP|wx.RIGHT, 5)
        self.szr_boxplot.Add(self.drop_box_sort, 0, wx.TOP, 5)
        self.szr_boxplot.AddSpacer(10)
        self.szr_boxplot.Add(lbl_box_opts, 0, wx.TOP|wx.RIGHT, 5)
        self.szr_boxplot.Add(self.drop_box_opts, 0, wx.TOP, 5)
        self.szr_boxplot.AddSpacer(10)
        self.szr_boxplot.Add(self.chk_boxplot_rotate, 0, wx.TOP|wx.BOTTOM, 10)
        self.panel_boxplot.SetSizer(self.szr_boxplot)
        self.szr_boxplot.SetSizeHints(self.panel_boxplot)
    
    def get_fresh_drop_var1(self, items, idx_sel):
        """
        Must make fresh to get performant display when lots of items in a 
            non-system font on Linux.
        """
        try:
            self.drop_var1.Destroy() # don't want more than one
        except Exception:
            pass
        drop_var1 = wx.Choice(self.panel_vars, -1, choices=items, 
                              size=(self.dropdown_width,-1))
        drop_var1.SetFont(mg.GEN_FONT)
        drop_var1.SetSelection(idx_sel)
        drop_var1.Bind(wx.EVT_CHOICE, self.on_var1_sel)
        drop_var1.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_var1)
        drop_var1.SetToolTipString(self.variables_rc_msg)
        return drop_var1
    
    def get_fresh_drop_var2(self, items, idx_sel):
        """
        Must make fresh to get performant display even with lots of items in a 
            non-system font on Linux.
        """
        try:
            self.drop_var2.Destroy() # don't want more than one
        except Exception:
            pass
        drop_var2 = wx.Choice(self.panel_vars, -1, choices=items, 
                              size=(self.dropdown_width,-1))
        drop_var2.SetFont(mg.GEN_FONT)
        drop_var2.SetSelection(idx_sel)
        drop_var2.Bind(wx.EVT_CHOICE, self.on_var2_sel)
        drop_var2.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_var2)
        drop_var2.SetToolTipString(self.variables_rc_msg)
        return drop_var2
    
    def get_fresh_drop_var3(self, items, idx_sel):
        """
        Must make fresh to get performant display even with lots of items in a 
            non-system font on Linux.
        """
        try:
            self.drop_var3.Destroy() # don't want more than one
        except Exception:
            pass
        drop_var3 = wx.Choice(self.panel_vars, -1, choices=items, 
                              size=(self.dropdown_width,-1))
        drop_var3.SetFont(mg.GEN_FONT)
        drop_var3.SetSelection(idx_sel)
        drop_var3.Bind(wx.EVT_CHOICE, self.on_var3_sel)
        drop_var3.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_var3)
        drop_var3.SetToolTipString(self.variables_rc_msg)
        return drop_var3
    
    def get_fresh_drop_var4(self, items, idx_sel):
        """
        Must make fresh to get performant display even with lots of items in a 
            non-system font on Linux.
        """
        try:
            self.drop_var4.Destroy() # don't want more than one
        except Exception:
            pass
        drop_var4 = wx.Choice(self.panel_vars, -1, choices=items, 
                              size=(self.dropdown_width,-1))
        drop_var4.SetFont(mg.GEN_FONT)
        drop_var4.SetSelection(idx_sel)
        drop_var4.Bind(wx.EVT_CHOICE, self.on_var4_sel)
        drop_var4.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_var4)
        drop_var4.SetToolTipString(self.variables_rc_msg)
        return drop_var4

    def _update_lbl_var1(self, chart_config1, lbl1_override=None):
        """
        Used by all chart types, not just those with an aggregate option. So 
        CUR_DATA_OPT may have been set by another chart type. Need to check this
        chart type has an aggregate option as well to know how to get var lbl.
        """
        if lbl1_override:
            rawlbl1 = lbl1_override
        else:
            show_agg, has_agg_config = self.get_agg_dets()
            if show_agg and has_agg_config:
                rawlbl1 = chart_config1[mg.LBL_KEY][CUR_DATA_OPT_LBL]
            else:
                rawlbl1 = chart_config1[mg.LBL_KEY]
        lbl1 = u"%s:" % rawlbl1
        try:
            self.lbl_var1.SetLabel(lbl1) # if not already made, make it (this also means we only make it if not already made)
        except Exception:
            self.lbl_var1 = wx.StaticText(self.panel_vars, -1, lbl1)
            self.lbl_var1.SetFont(mg.LABEL_FONT)

    def setup_var_dropdowns(self):
        """
        Makes fresh objects each time (and rebinds etc) because that is the only
        way (in Linux at least) to have a non-standard font-size for items in a
        performant way e.g. if more than 10-20 items in a list. Very slow if
        having to add items to dropdown if having to set font e.g. using
        SetItems().
        """
        varname1, varname2, varname3, varname4 = self.get_vars()
        chart_subtype_key = self.get_chart_subtype_key()
        chart_config = mg.CHART_CONFIG[self.chart_type][chart_subtype_key]
        self.dropdown_width = self.get_dropdown_width(chart_config)
        ## time series special case - not easy to handle by simple config settings
        show_agg, unused = self.get_agg_dets()
        time_series = (
            (self.chart_type == mg.LINE_CHART
                and self.chk_line_time_series.IsChecked())
            or
            (self.chart_type == mg.AREA_CHART
                and self.chk_area_time_series.IsChecked()))
        # var 1
        chart_config1 = chart_config[0]
        min_data_type1 = chart_config1[mg.MIN_DATA_TYPE_KEY]
        inc_drop_select1 = chart_config1[mg.EMPTY_VAL_OK]
        kwargs = {u"chart_config1": chart_config1}
        if time_series:
            if not show_agg:
                kwargs[u"lbl1_override"] = mg.CHART_DATETIMES_LBL
        self._update_lbl_var1(**kwargs)
        self.sorted_var_names1 = []
        (items1, 
         idx_sel1) = self.get_items_and_sel_idx(mg.VAR_1_DEFAULT, 
                            sorted_var_names=self.sorted_var_names1, 
                            var_name=varname1, inc_drop_select=inc_drop_select1, 
                            override_min_data_type=min_data_type1)
        self.drop_var1 = self.get_fresh_drop_var1(items1, idx_sel1)
        # var 2
        chart_config2 = chart_config[1]
        min_data_type2 = chart_config2[mg.MIN_DATA_TYPE_KEY]
        inc_drop_select2 = chart_config2[mg.EMPTY_VAL_OK]
        rawlbl = chart_config2[mg.LBL_KEY]
        if time_series and show_agg:
            rawlbl = mg.CHART_DATETIMES_LBL
        lbl2 = u"%s:" % rawlbl
        try:
            self.lbl_var2.SetLabel(lbl2)
        except Exception:
            self.lbl_var2 = wx.StaticText(self.panel_vars, -1, lbl2)
            self.lbl_var2.SetFont(mg.LABEL_FONT)
        self.sorted_var_names2 = []
        (items2, 
         idx_sel2) = self.get_items_and_sel_idx(mg.VAR_2_DEFAULT, 
                           sorted_var_names=self.sorted_var_names2, 
                           var_name=varname2, inc_drop_select=inc_drop_select2, 
                           override_min_data_type=min_data_type2)
        self.drop_var2 = self.get_fresh_drop_var2(items2, idx_sel2)
        # var 3
        try:
            chart_config3 = chart_config[2]
            lbl3 = u"%s:" % chart_config3[mg.LBL_KEY]
            min_data_type3 = chart_config3[mg.MIN_DATA_TYPE_KEY]
            inc_drop_select3 = chart_config3[mg.EMPTY_VAL_OK]
        except Exception:
            # OK if not a third drop down for chart
            lbl3 = u"%s:" % mg.CHARTS_CHART_BY_LBL
            min_data_type3 = mg.VAR_TYPE_CAT_KEY
            inc_drop_select3 = True
        try:
            self.lbl_var3.SetLabel(lbl3)
        except Exception:
            self.lbl_var3 = wx.StaticText(self.panel_vars, -1, lbl3)
            self.lbl_var3.SetFont(mg.LABEL_FONT)
        self.sorted_var_names3 = []
        (items3, 
         idx_sel3) = self.get_items_and_sel_idx(mg.VAR_3_DEFAULT, 
                           sorted_var_names=self.sorted_var_names3, 
                           var_name=varname3, inc_drop_select=inc_drop_select3, 
                           override_min_data_type=min_data_type3)
        self.drop_var3 = self.get_fresh_drop_var3(items3, idx_sel3)
        # var 3 visibility
        try:
            chart_config[2]
            show3 = True
        except Exception:
            self.lbl_var3.Hide()
            self.drop_var3.Hide()
            show3 = False
        # var 4
        try:
            chart_config4 = chart_config[3]
            lbl4 = u"%s:" % chart_config4[mg.LBL_KEY]
            min_data_type4 = chart_config4[mg.MIN_DATA_TYPE_KEY]
            inc_drop_select4 = chart_config4[mg.EMPTY_VAL_OK]
        except Exception:
            # OK if not a third drop down for chart
            lbl4 = u"%s:" % mg.CHARTS_CHART_BY_LBL
            min_data_type4 = mg.VAR_TYPE_CAT_KEY
            inc_drop_select4 = True
        try:
            self.lbl_var4.SetLabel(lbl4)
        except Exception:
            self.lbl_var4 = wx.StaticText(self.panel_vars, -1, lbl4)
            self.lbl_var4.SetFont(mg.LABEL_FONT)
        self.sorted_var_names4 = []
        (items4, 
         idx_sel4) = self.get_items_and_sel_idx(mg.VAR_4_DEFAULT, 
                           sorted_var_names=self.sorted_var_names4, 
                           var_name=varname4, inc_drop_select=inc_drop_select4, 
                           override_min_data_type=min_data_type4)
        self.drop_var4 = self.get_fresh_drop_var4(items4, idx_sel4)
        # var 4 visibility
        try:
            chart_config[3]
            show4 = True
        except Exception:
            self.lbl_var4.Hide()
            self.drop_var4.Hide()
            show4 = False
        self.panel_vars.Layout()
        self.drop_var1.Show(True)
        self.drop_var2.Show(True)
        self.lbl_var3.Show(show3)
        self.drop_var3.Show(show3)
        self.lbl_var4.Show(show4)
        self.drop_var4.Show(show4)
        try:
            self.szr_vars.Clear()
        except Exception:
            pass
        self.szr_vars.Add(self.lbl_var1, 0,wx.TOP|wx.RIGHT, 5)
        self.szr_vars.Add(self.drop_var1, 0, 
                          wx.FIXED_MINSIZE|wx.RIGHT|wx.TOP, 5)
        self.szr_vars.Add(self.lbl_var2, 0, wx.TOP|wx.RIGHT, 5)
        self.szr_vars.Add(self.drop_var2, 0, 
                          wx.FIXED_MINSIZE|wx.RIGHT|wx.TOP, 5)
        self.szr_vars.Add(self.lbl_var3, 0, wx.TOP|wx.RIGHT, 5)
        self.szr_vars.Add(self.drop_var3, 0, 
                          wx.FIXED_MINSIZE|wx.RIGHT|wx.TOP, 5)
        self.szr_vars.Add(self.lbl_var4, 0, wx.TOP|wx.RIGHT, 5)
        self.szr_vars.Add(self.drop_var4, 0, 
                          wx.FIXED_MINSIZE|wx.RIGHT|wx.TOP, 5)
        self.panel_vars.Layout()

    def get_items_and_sel_idx(self, default, sorted_var_names, var_name=None, 
                              inc_drop_select=False, 
                              override_min_data_type=None):
        debug = False
        min_data_type = (override_min_data_type if override_min_data_type
                         else self.min_data_type)
        if debug: print(var_name, self.min_data_type, override_min_data_type)
        var_names = projects.get_approp_var_names(self.var_types,
                                                  min_data_type)
        (var_choice_items, 
         sorted_vals) = lib.get_sorted_choice_items(dic_labels=self.var_labels,
                                                vals=var_names,
                                                inc_drop_select=inc_drop_select)
        while True:
            try:
                del sorted_var_names[0]
            except IndexError:
                break
        sorted_var_names.extend(sorted_vals)
        # set selection
        idx_var = projects.get_idx_to_select(var_choice_items, var_name, 
                                             self.var_labels, default)
        return var_choice_items, idx_var
    
    def get_dropdown_width(self, chart_config):
        dropdown_width = mg.STD_DROP_WIDTH if len(chart_config) < 4 else 160
        return dropdown_width
    
    def get_chk_rotate(self, panel):
        if mg.PLATFORM == mg.WINDOWS:
            rotate2use = _("Rotate labels?")
        else:
            rotate2use = _("Rotate\nlabels?")
        chk = self.checkbox2use(panel, -1, rotate2use)
        chk.SetFont(mg.GEN_FONT)
        chk.SetValue(ROTATE)
        chk.SetToolTipString(_(u"Rotate x-axis labels?"))
        chk.Bind(wx.EVT_CHECKBOX, self.on_chk_rotate)
        return chk
        # var 1

    def get_chk_major_ticks(self, panel):
        if mg.PLATFORM == mg.WINDOWS:
            major2use = _("Major labels only?")
        else:
            major2use = _("Major\nlabels only?")
        chk = self.checkbox2use(panel, -1, major2use, wrap=15)
        chk.SetFont(mg.GEN_FONT)
        chk.SetValue(MAJOR)
        chk.SetToolTipString(_(u"Show major labels only?"))
        chk.Bind(wx.EVT_CHECKBOX, self.on_chk_major_ticks)
        return chk

    def get_chk_hide_markers(self, panel):
        if mg.PLATFORM == mg.WINDOWS:
            hide2use = _("Hide markers?")
        else:
            hide2use = _("Hide\nmarkers?")
        chk = self.checkbox2use(panel, -1, hide2use, wrap=15)
        chk.SetFont(mg.GEN_FONT)
        chk.SetValue(HIDE_MARKERS)
        chk.SetToolTipString(_(u"Hide markers?"))
        chk.Bind(wx.EVT_CHECKBOX, self.on_chk_hide_markers)
        return chk

    def get_chk_time_series(self, panel, line=True):
        if mg.PLATFORM == mg.WINDOWS:
            dates2use = _("Time series?")
        else:
            dates2use = _("Time\nseries?")
        chk = self.checkbox2use(panel, -1, dates2use)
        chk.SetFont(mg.GEN_FONT)
        chk.SetValue(MAJOR)
        chk.SetToolTipString(_(u"Time series i.e. spread over x-axis by date?"))
        event_func = (self.on_chk_line_time_series if line
            else self.on_chk_area_time_series)
        chk.Bind(wx.EVT_CHECKBOX, event_func)
        return chk

    def on_drop_sort(self, event):
        debug = False
        global CUR_SORT_OPT_LBL
        drop = event.GetEventObject()
        try:
            idx_sel = drop.GetSelection()
            CUR_SORT_OPT_LBL = mg.STD_SORT_OPT_LBLS[idx_sel]
        except IndexError:
            pass
        except AttributeError:
            CUR_SORT_OPT_LBL = drop.GetLabel() # label is what we want to store e.g. mg.SORT_VALUE_LBL
        if debug: print(u"Current sort option: %s" % CUR_SORT_OPT_LBL)

    def on_drop_val(self, event):
        debug = False
        global CUR_DATA_OPT_LBL
        # http://www.blog.pythonlibrary.org/2011/09/20/...
        # ... wxpython-binding-multiple-widgets-to-the-same-handler/
        drop = event.GetEventObject()
        try:
            idx_sel = drop.GetSelection()
            CUR_DATA_OPT_LBL = mg.DATA_SHOW_OPT_LBLS[idx_sel]
        except IndexError:
            pass
        except AttributeError:
            CUR_DATA_OPT = drop.GetLabel() # label is what we want to store e.g. mg.SHOW_FREQ_LBL
        if debug: print(u"Current data option: %s" % CUR_DATA_OPT)
        self.setup_var_dropdowns() # e.g. if we select mean we now need an extra var and the 1st has to be numeric
        self.setup_line_extras()

    def on_show(self, event):
        if self.exiting:
            return
        try:
            self.html.pizza_magic() # must happen after Show
        except Exception:
            pass # need on Mac or exception survives
        finally:
            # any initial content
            html2show = _(u"<p>Waiting for a chart to be run.</p>")
            self.html.show_html(html2show)

    def on_btn_help(self, event):
        import webbrowser
        url = (u"http://www.sofastatistics.com/wiki/doku.php"
               u"?id=help:charts")
        webbrowser.open_new_tab(url)
        event.Skip()

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
        self.bmp_btn_clust_bar = wx.Image(os.path.join(mg.SCRIPT_PATH, 
                                        u"images", u"clustered_bar_chart.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.bmp_btn_clust_bar_sel = wx.Image(os.path.join(mg.SCRIPT_PATH, 
                                    u"images", u"clustered_bar_chart_sel.xpm"), 
                                    wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_clust_bar = wx.BitmapButton(self.panel_mid, -1, 
                                                   self.bmp_btn_clust_bar, 
                                                   style=wx.NO_BORDER)
        self.btn_clust_bar.Bind(wx.EVT_BUTTON, 
                                      self.on_btn_clustered_bar_chart)
        self.btn_clust_bar.SetToolTipString(_("Make Clustered Bar Chart"))
        szr_chart_btns.Add(self.btn_clust_bar, 0, wx.RIGHT, btn_gap)
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
        self.bmp_btn_histogram_sel = wx.Image(os.path.join(mg.SCRIPT_PATH, 
                                        u"images", u"histogram_sel.xpm"), 
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
        szr_chart_btns.Add(self.btn_scatterplot, 0, wx.RIGHT, btn_gap)
        # boxplots
        self.bmp_btn_boxplot = wx.Image(os.path.join(mg.SCRIPT_PATH, 
                                            u"images", u"boxplot.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.bmp_btn_boxplot_sel = wx.Image(os.path.join(mg.SCRIPT_PATH, 
                                            u"images", u"boxplot_sel.xpm"), 
                                        wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_boxplot = wx.BitmapButton(self.panel_mid, -1, 
                                               self.bmp_btn_boxplot, 
                                               style=wx.NO_BORDER)
        self.btn_boxplot.Bind(wx.EVT_BUTTON, self.on_btn_boxplot)
        self.btn_boxplot.SetToolTipString(_("Make Box and Whisker Plot"))
        szr_chart_btns.Add(self.btn_boxplot)
        if mg.PLATFORM == mg.LINUX:
            hand = wx.StockCursor(wx.CURSOR_HAND)
            self.btn_bar_chart.SetCursor(hand)
            self.btn_clust_bar.SetCursor(hand)
            self.btn_pie_chart.SetCursor(hand)
            self.btn_line_chart.SetCursor(hand)
            self.btn_area_chart.SetCursor(hand)
            self.btn_histogram.SetCursor(hand)
            self.btn_scatterplot.SetCursor(hand)
            self.btn_boxplot.SetCursor(hand)
        self.btn_to_rollback = self.btn_bar_chart
        self.bmp_to_rollback_to = self.bmp_btn_bar_chart

    def get_agg_dets(self):
        show_agg = CUR_DATA_OPT_LBL in mg.AGGREGATE_DATA_SHOW_OPT_LBLS
        has_agg_config = mg.AGGREGATE_KEY in mg.CHART_CONFIG[self.chart_type]
        return show_agg, has_agg_config

    def get_chart_subtype_key(self):
        show_agg, has_agg_config = self.get_agg_dets()
        chart_subtype_key = (mg.AGGREGATE_KEY if show_agg and has_agg_config
                             else mg.INDIV_VAL_KEY)
        return chart_subtype_key

    def refresh_vars(self):
        self.setup_var_dropdowns()
        self.update_defaults()
        
    def on_chk_rotate(self, event):
        global ROTATE
        chk = event.GetEventObject()
        ROTATE = chk.IsChecked()
        time_series_line = self.chk_line_time_series.IsChecked()
        show_major_line = self._get_show_major(time_series_line, ROTATE)
        self.chk_line_major_ticks.Enable(show_major_line)
        time_series_area = self.chk_area_time_series.IsChecked()
        show_major_area = self._get_show_major(time_series_area, ROTATE)
        self.chk_area_major_ticks.Enable(show_major_area)
        self.panel_line_chart.Refresh()
        self.panel_area_chart.Refresh()
        
    def on_chk_major_ticks(self, event):
        global MAJOR
        chk = event.GetEventObject()
        MAJOR = chk.IsChecked()
        
    def on_chk_hide_markers(self, event):
        global HIDE_MARKERS
        chk = event.GetEventObject()
        HIDE_MARKERS = chk.IsChecked()
    
    @staticmethod
    def _get_show_major(time_series, rotate):
        if not time_series:
            show_major = True
        else:
            if rotate:
                show_major = True
            else:
                show_major = False
        return show_major         
    
    def on_chk_line_time_series(self, event):
        debug = False
        chk = event.GetEventObject()
        self.drop_line_sort.Enable(not chk.IsChecked())
        time_series = chk.IsChecked()
        rotate = self.chk_line_rotate.IsChecked()
        show_major = self._get_show_major(time_series, rotate)
        if debug:
            print("time_series: {}; rotate: {}; show_major: {}".format(
                chk.IsChecked(), self.chk_line_rotate.IsChecked(), show_major))
        self.chk_line_major_ticks.Enable(show_major)
        self.setup_var_dropdowns()
        self.panel_line_chart.Refresh()
        
    def on_chk_area_time_series(self, event):
        debug = False
        chk = event.GetEventObject()
        self.drop_area_sort.Enable(not chk.IsChecked())
        time_series = chk.IsChecked()
        rotate = self.chk_area_rotate.IsChecked()
        show_major = self._get_show_major(time_series, rotate)
        if debug:
            print("time_series: {}; rotate: {}; show_major: {}".format(
                chk.IsChecked(), self.chk_line_rotate.IsChecked(), show_major))
        self.chk_area_major_ticks.Enable(show_major)
        self.setup_var_dropdowns()
        self.panel_area_chart.Refresh()

    def btn_chart(self, event, btn, btn_bmp, btn_sel_bmp, panel):
        btn.SetFocus()
        btn.SetDefault()
        self.btn_to_rollback.SetBitmapLabel(self.bmp_to_rollback_to)
        self.btn_to_rollback = btn
        self.bmp_to_rollback_to = btn_bmp
        btn.SetBitmapLabel(btn_sel_bmp)
        event.Skip()
        if self.panel_displayed == panel:
            return # just reclicking on same one
        self.panel_displayed.Show(False)
        self.szr_mid.Remove(self.panel_displayed)
        self.szr_mid.Add(panel, 0, wx.GROW)
        self.panel_displayed = panel
        panel.Show(True)
        self.panel_mid.Layout() # self.Layout() doesn't work in Windows
        self.setup_var_dropdowns()

    def on_btn_bar_chart(self, event):
        self.chart_type = mg.SIMPLE_BARCHART
        btn = self.btn_bar_chart
        btn_bmp = self.bmp_btn_bar_chart
        btn_bmp_sel = self.bmp_btn_bar_chart_sel
        panel = self.panel_bar_chart
        self.drop_bar_val.SetSelection(mg.DATA_SHOW_OPT_LBLS.index(CUR_DATA_OPT_LBL))
        self.drop_bar_sort.SetSelection(mg.STD_SORT_OPT_LBLS.index(CUR_SORT_OPT_LBL))
        self.chk_simple_bar_rotate.SetValue(ROTATE)
        self.btn_chart(event, btn, btn_bmp, btn_bmp_sel, panel)

    def on_btn_clustered_bar_chart(self, event):
        global CUR_SORT_OPT_LBL
        self.chart_type = mg.CLUSTERED_BARCHART
        btn = self.btn_clust_bar
        btn_bmp = self.bmp_btn_clust_bar
        btn_bmp_sel = self.bmp_btn_clust_bar_sel
        panel = self.panel_clust_bar
        idx_val = mg.DATA_SHOW_OPT_LBLS.index(CUR_DATA_OPT_LBL)
        try:
            idx_sort = mg.SORT_VAL_AND_LABEL_OPT_LBLS.index(CUR_SORT_OPT_LBL)
        except ValueError: # doesn't have increasing, or decreasing
            CUR_SORT_OPT_LBL = mg.SORT_VALUE_LBL
            idx_sort = mg.STD_SORT_OPT_LBLS.index(CUR_SORT_OPT_LBL)
        self.drop_clust_val.SetSelection(idx_val)
        self.drop_clust_sort.SetSelection(idx_sort)
        self.chk_clust_bar_rotate.SetValue(ROTATE)
        self.btn_chart(event, btn, btn_bmp, btn_bmp_sel, panel)

    def on_btn_pie_chart(self, event):
        self.chart_type = mg.PIE_CHART
        btn = self.btn_pie_chart
        btn_bmp = self.bmp_btn_pie_chart
        btn_bmp_sel = self.bmp_btn_pie_chart_sel
        panel = self.panel_pie_chart
        self.drop_pie_sort.SetSelection(mg.STD_SORT_OPT_LBLS.index(CUR_SORT_OPT_LBL))
        self.btn_chart(event, btn, btn_bmp, btn_bmp_sel, panel)

    def on_btn_line_chart(self, event):
        global CUR_SORT_OPT_LBL
        self.chart_type = mg.LINE_CHART
        btn = self.btn_line_chart
        btn_bmp = self.bmp_btn_line_chart
        btn_bmp_sel = self.bmp_btn_line_chart_sel
        panel = self.panel_line_chart
        idx_val = mg.DATA_SHOW_OPT_LBLS.index(CUR_DATA_OPT_LBL)
        try:
            idx_sort = mg.SORT_VAL_AND_LABEL_OPT_LBLS.index(CUR_SORT_OPT_LBL)
        except ValueError: # doesn't have increasing, or decreasing
            CUR_SORT_OPT_LBL = mg.SORT_VALUE_LBL
            idx_sort = mg.STD_SORT_OPT_LBLS.index(CUR_SORT_OPT_LBL)
        self.drop_line_val.SetSelection(idx_val)
        self.drop_line_sort.SetSelection(idx_sort)
        self.chk_line_rotate.SetValue(ROTATE)
        self.chk_line_hide_markers.SetValue(HIDE_MARKERS)
        self.chk_line_major_ticks.SetValue(MAJOR)
        self.btn_chart(event, btn, btn_bmp, btn_bmp_sel, panel)
        self.setup_line_extras()

    def on_btn_area_chart(self, event):
        self.chart_type = mg.AREA_CHART
        btn = self.btn_area_chart
        btn_bmp = self.bmp_btn_area_chart
        btn_bmp_sel = self.bmp_btn_area_chart_sel
        panel = self.panel_area_chart
        idx_val = mg.DATA_SHOW_OPT_LBLS.index(CUR_DATA_OPT_LBL)
        idx_sort = mg.SORT_VAL_AND_LABEL_OPT_LBLS.index(CUR_SORT_OPT_LBL)
        self.drop_area_val.SetSelection(idx_val)
        self.drop_area_sort.SetSelection(idx_sort)
        self.chk_area_rotate.SetValue(ROTATE)
        self.chk_area_hide_markers.SetValue(HIDE_MARKERS)
        self.chk_area_major_ticks.SetValue(MAJOR)
        self.btn_chart(event, btn, btn_bmp, btn_bmp_sel, panel)

    def on_btn_histogram(self, event):
        self.chart_type = mg.HISTOGRAM
        btn = self.btn_histogram
        btn_bmp = self.bmp_btn_histogram
        btn_bmp_sel = self.bmp_btn_histogram_sel
        panel = self.panel_histogram
        self.btn_chart(event, btn, btn_bmp, btn_bmp_sel, panel)

    def on_btn_scatterplot(self, event):
        self.chart_type = mg.SCATTERPLOT
        btn = self.btn_scatterplot
        btn_bmp = self.bmp_btn_scatterplot
        btn_bmp_sel = self.bmp_btn_scatterplot_sel
        panel = self.panel_scatterplot
        self.btn_chart(event, btn, btn_bmp, btn_bmp_sel, panel)

    def on_btn_boxplot(self, event):
        global CUR_SORT_OPT_LBL
        self.chart_type = mg.BOXPLOT
        btn = self.btn_boxplot
        btn_bmp = self.bmp_btn_boxplot
        btn_bmp_sel = self.bmp_btn_boxplot_sel
        panel = self.panel_boxplot
        try:
            idx_sort = mg.SORT_VAL_AND_LABEL_OPT_LBLS.index(CUR_SORT_OPT_LBL)
        except ValueError: # doesn't have increasing, or decreasing
            CUR_SORT_OPT_LBL = mg.SORT_VALUE_LBL
            idx_sort = mg.STD_SORT_OPT_LBLS.index(CUR_SORT_OPT_LBL)
        self.drop_box_sort.SetSelection(idx_sort)
        self.chk_boxplot_rotate.SetValue(ROTATE)
        self.btn_chart(event, btn, btn_bmp, btn_bmp_sel, panel)
        
    def on_btn_run(self, event):
        # get settings
        cc = output.get_cc()
        run_ok = self.test_config_ok()
        if run_ok:
            ## css_idx is supplied at the time
            get_script_args={u'css_fil': cc[mg.CURRENT_CSS_PATH], 
                u"report_name": cc[mg.CURRENT_REPORT_PATH], }
            config_ui.ConfigUI.on_btn_run(self, event, get_script_args, 
                new_has_dojo=True)

    def on_btn_script(self, event):
        # TODO NB will have new_has_dojo=True
        wx.MessageBox(u"This version does not support exporting chart code yet")
    
    def on_var1_sel(self, event):
        self.update_defaults()
    
    def setup_line_extras(self):
        """
        Only enable trendlines and smooth line if chart type is line and a 
            single line chart.
        """
        show_agg, unused = self.get_agg_dets()
        show_line_extras = (self.chart_type == mg.LINE_CHART and (
                (not show_agg # normal and dropdown2 is nothing
                     and self.drop_var2.GetStringSelection() == mg.DROP_SELECT)
                 or (show_agg # aggregate and dropdown3 is nothing
                     and self.drop_var3.GetStringSelection() == mg.DROP_SELECT)
            ))
        self.chk_line_trend.Enable(show_line_extras)
        self.chk_line_smooth.Enable(show_line_extras)
        self.panel_line_chart.Refresh()
        
    def on_var2_sel(self, event):
        self.setup_line_extras()
        self.update_defaults()
    
    def on_var3_sel(self, event):
        self.setup_line_extras()
        self.update_defaults()
    
    def on_var4_sel(self, event):
        self.setup_line_extras()
        self.update_defaults()
    
    def add_other_var_opts(self, szr=None):
        pass

    def on_rclick_var1(self, event):
        self.on_rclick_var(self.drop_var1, self.sorted_var_names1)
        
    def on_rclick_var2(self, event):
        self.on_rclick_var(self.drop_var2, self.sorted_var_names2)
        
    def on_rclick_var3(self, event):
        self.on_rclick_var(self.drop_var3, self.sorted_var_names3)
        
    def on_rclick_var4(self, event):
        self.on_rclick_var(self.drop_var4, self.sorted_var_names4)
        
    def on_rclick_var(self, drop_var, sorted_var_names):
        var_name, choice_item = self.get_var_dets(drop_var, sorted_var_names)
        if var_name == mg.DROP_SELECT:
            return
        var_label = lib.get_item_label(self.var_labels, var_name)
        updated = config_output.set_var_props(choice_item, var_name, var_label,
            self.var_labels, self.var_notes, self.var_types, self.val_dics)
        if updated:
            self.setup_var_dropdowns()
            self.update_defaults()

    def on_database_sel(self, event):
        """
        Reset dbe, database, cursor, tables, table, tables dropdown, 
            fields, has_unique, and idxs after a database selection.
        """
        if config_ui.ConfigUI.on_database_sel(self, event):
            output.update_var_dets(dlg=self)
            self.setup_var_dropdowns()
                
    def on_table_sel(self, event):
        "Reset key data details after table selection."       
        config_ui.ConfigUI.on_table_sel(self, event)
        # now update var dropdowns
        output.update_var_dets(dlg=self)
        self.setup_var_dropdowns()
       
    def on_btn_var_config(self, event):
        """
        Want to retain already selected item - even though label and even 
            position may have changed.
        """
        config_ui.ConfigUI.on_btn_var_config(self, event)
        self.setup_var_dropdowns()
        self.update_defaults()

    def get_vars(self):
        """
        self.sorted_var_names_by and self.sorted_var_names1, 2, and 3 are set 
            when dropdowns are set (and only changed when reset).
        May be called when var dropdowns not even created in which case it 
            should return Nones.
        """
        try:
            varname1, unused = self.get_var_dets(self.drop_var1, 
                                                 self.sorted_var_names1)
        except Exception:
            varname1 = None
        try:
            varname2, unused = self.get_var_dets(self.drop_var2, 
                                                 self.sorted_var_names2)
        except Exception:
            varname2 = None
        try:
            varname3, unused = self.get_var_dets(self.drop_var3, 
                                                 self.sorted_var_names3)
        except Exception:
            varname3 = None
        try:
            varname4, unused = self.get_var_dets(self.drop_var4, 
                                                 self.sorted_var_names4)
        except Exception:
            varname4 = None
        return varname1, varname2, varname3, varname4
    
    def update_defaults(self):
        """
        Should run this after any change or else might revert to the previous 
            value when drop vars are refreshed.
        The values for a variable we try to keep unless it is not in the list.
        """
        debug = False
        mg.VAR_1_DEFAULT = self.drop_var1.GetStringSelection()
        mg.VAR_2_DEFAULT = self.drop_var2.GetStringSelection()
        try:
            mg.VAR_3_DEFAULT = self.drop_var3.GetStringSelection()
        except Exception: # not visible
            mg.VAR_3_DEFAULT = None
        try:
            mg.VAR_4_DEFAULT = self.drop_var4.GetStringSelection()
        except Exception: # not visible
            mg.VAR_4_DEFAULT = None
        if debug: print(mg.VAR_1_DEFAULT, mg.VAR_2_DEFAULT, mg.VAR_3_DEFAULT, 
                        mg.VAR_4_DEFAULT)
   
    def update_phrase(self):
        pass

    def test_config_ok(self):
        """
        Are the appropriate selections made to enable an analysis to be run?
        No longer possible to have a Select showing where Select is not 
            acceptable. So the only issues are a No Selection followed by a 
            variable selection or duplicate variable selections.
        """
        debug = False
        lblctrls = [self.lbl_var1, self.lbl_var2, self.lbl_var3, self.lbl_var4]
        variables = self.get_vars()
        if debug: print(variables)
        if len(lblctrls) != len(variables):
            raise Exception(u"Mismatch in number of lbls and variables in "
                            u"charting dlg.")
        lblctrl_vars = zip(lblctrls, variables)
        idx_lblctrl_in_lblctrl_vars = 0
        idx_variable_in_lblctrl_vars = 1
        shown_lblctrl_vars = [x for x in lblctrl_vars 
                             if x[idx_lblctrl_in_lblctrl_vars].IsShown()]
        # 1) Required field empty
        for var_idx, shown_lblctrl_var in enumerate(shown_lblctrl_vars):
            chart_subtype_key = self.get_chart_subtype_key()
            chart_config = mg.CHART_CONFIG[self.chart_type][chart_subtype_key]
            allows_missing = chart_config[var_idx][mg.EMPTY_VAL_OK]
            lblctrl, variable = shown_lblctrl_var
            varlbl = lblctrl.GetLabel().rstrip(u":")
            role_missing = variable is None
            if role_missing and not allows_missing:
                wx.MessageBox(u"The required field %s is missing for the %s "
                    u"chart type." % (varlbl, self.chart_type))
                return False
        # 2) Variable selected but an earlier one has not (No Selection instead)
        """
        Line charts and Scatterplots have one exception - can select chart by
        without series by
        """
        has_no_select_selected = False
        lbl_with_no_select = u""
        for var_idx, shown_lblctrl_var in enumerate(shown_lblctrl_vars):
            lblctrl, variable = shown_lblctrl_var
            if variable == mg.DROP_SELECT:
                lbl_with_no_select = lblctrl.GetLabel().rstrip(u":")
                has_no_select_selected = True
            else:
                if has_no_select_selected: # already
                    # OK only if a line chart or scatterplot and we are in the chart by var 
                    if self.chart_type in (mg.LINE_CHART, mg.SCATTERPLOT):
                        chart_subtype_key = self.get_chart_subtype_key()
                        chart_config = mg.CHART_CONFIG[self.chart_type]\
                                                            [chart_subtype_key]
                        var_role = chart_config[var_idx][mg.VAR_ROLE_KEY]                         
                        if var_role == mg.VAR_ROLE_CHARTS:
                            continue
                    varlbl = lblctrl.GetLabel().rstrip(u":")
                    wx.MessageBox(_(u"\"%(varlbl)s\" has a variable selected "
                        u"but the previous drop down list "
                        u"\"%(lbl_with_no_select)s\" does not.") % 
                                  {u"varlbl": varlbl, 
                                   u"lbl_with_no_select": lbl_with_no_select})
                    return False
        # 3) Excluding No Selections, we have duplicate selections
        selected_lblctrl_vars = [x for x in shown_lblctrl_vars 
            if x[idx_variable_in_lblctrl_vars] != mg.DROP_SELECT]
        selected_lblctrls = [x[idx_lblctrl_in_lblctrl_vars] for x 
            in selected_lblctrl_vars]
        selected_lbls = [x.GetLabel().rstrip(u":") for x in selected_lblctrls]
        selected_vars = [x[idx_variable_in_lblctrl_vars] for x 
            in selected_lblctrl_vars]
        unique_selected_vars = set(selected_vars)
        if len(unique_selected_vars) < len(selected_vars):
                final_comma = u"" if len(selected_vars) < 3 else u","
                varlbls = (u'"' + u'", "'.join(selected_lbls[:-1]) + u'"' 
                    + final_comma + u" and \"%s\"" % selected_lbls[-1])
                wx.MessageBox(_(u"The variables selected for %s must be "
                    u"different.") % varlbls)
                return False
        return True

    def get_script(self, css_idx, css_fil, report_name):
        """
        Build script from inputs.
        
        For each dropdown identify the variable role (according to CHART_CONFIG, 
        chart type, and whether data is averaged or not). Not all dropdowns will 
        have a variable selected (i.e. 'Not Selected' is the selection) but for 
        those that do identify the field name, field label, and the value labels 
        ready to pass to the appropriate data collection function.
        """
        debug = False
        dd = mg.DATADETS_OBJ
        rotate = u"True" if ROTATE else u"False"
        major = u"True" if MAJOR else u"False"
        hide_markers = u"True" if HIDE_MARKERS else u"False"
        line_time_series = self.chk_line_time_series.IsChecked()
        area_time_series = self.chk_area_time_series.IsChecked()
        script_lst = []
        titles, subtitles = self.get_titles()
        script_lst.append(u"titles=%s" % unicode(titles))
        script_lst.append(u"subtitles=%s" % unicode(subtitles))
        script_lst.append(lib.get_tbl_filt_clause(dd.dbe, dd.db, dd.tbl))
        myvars = self.get_vars()
        if debug: print(myvars)
        # other variables to set up
        script_lst.append(u"add_to_report = %s" % ("True" if mg.ADD2RPT
            else "False"))
        rptname = lib.escape_pre_write(report_name)
        script_lst.append(u"report_name = u\"%s\"" % rptname)
        agg_fldlbl = None
        category_fldname = None
        chart_subtype_key = self.get_chart_subtype_key()
        chart_config = mg.CHART_CONFIG[self.chart_type][chart_subtype_key]
        var_roles_used = set()
        for var_val, var_dets in zip(myvars, chart_config):
            var_role = var_dets[mg.VAR_ROLE_KEY]
            role_not_sel = (var_val == mg.DROP_SELECT)
            var_roles_used.add(var_role)
            if role_not_sel:
                script_lst.append(u"%s = None" % var_role)
                script_lst.append(u"%s_name = None" % var_role)
                script_lst.append(u"%s_lbls = None" % var_role)
            else:
                script_lst.append(u"%s = u\"%s\"" % (var_role, var_val)) # e.g. var_role_agg = "age"
                var_name = lib.get_item_label(self.var_labels, var_val)
                script_lst.append(u"%s_name = u\"%s\"" % (var_role, var_name)) # e.g. var_role_agg_name = "Age"
                val_lbls = self.val_dics.get(var_val, {})
                script_lst.append(u"%s_lbls = %s" % (var_role, val_lbls)) # e.g. var_role_agg_lbls = {}
            if var_role == mg.VAR_ROLE_AGG:
                agg_fldlbl = var_name
            if var_role == mg.VAR_ROLE_CATEGORY:
                category_fldname = var_val
        for expected_var_role in mg.EXPECTED_VAR_ROLE_KEYS:
            if expected_var_role not in var_roles_used:
                # Needed even if not supplied by dropdown so we can have a
                # single api for get_gen_chart_dets()
                script_lst.append(u"%s = None" % expected_var_role)
                script_lst.append(u"%s_name = None" % expected_var_role)
                script_lst.append(u"%s_lbls = None" % expected_var_role)
        if self.chart_type in mg.GEN_CHARTS:
            if category_fldname is None:
                raise Exception(u"Cannot generate %s script if category field "
                    u"hasn't been set." % self.chart_type)
        if self.chart_type in mg.CHARTS_WITH_YTITLE_OPTIONS:
            if CUR_DATA_OPT_LBL == mg.SHOW_FREQ_LBL:
                ytitle2use = u"mg.Y_AXIS_FREQ_LBL"
            elif CUR_DATA_OPT_LBL == mg.SHOW_PERC_LBL:
                ytitle2use = u"mg.Y_AXIS_PERC_LBL"
            elif CUR_DATA_OPT_LBL in (mg.SHOW_AVG_LBL, mg.SHOW_SUM_LBL):
                if agg_fldlbl is None:
                    raise Exception(u"Aggregated variable label not supplied.")
                ytitle2use = (u'u"Mean %s"' % agg_fldlbl 
                    if CUR_DATA_OPT_LBL == mg.SHOW_AVG_LBL
                    else u'u"Sum of %s"' % agg_fldlbl)
        if self.chart_type == mg.SIMPLE_BARCHART:
            script_lst.append(get_simple_barchart_script(ytitle2use, rotate, 
                show_borders=self.chk_bar_borders.IsChecked(), css_fil=css_fil, 
                css_idx=css_idx))
        elif self.chart_type == mg.CLUSTERED_BARCHART:
            script_lst.append(get_clustered_barchart_script(ytitle2use, rotate, 
                show_borders=self.chk_clust_borders.IsChecked(), 
                css_fil=css_fil, css_idx=css_idx))
        elif self.chart_type == mg.PIE_CHART:
            inc_val_dets = (u"True" if self.chk_val_dets.IsChecked()
                else u"False")
            script_lst.append(get_pie_chart_script(css_fil, css_idx, 
                inc_val_dets))
        elif self.chart_type == mg.LINE_CHART:
            inc_trend = (u"True" if self.chk_line_trend.IsChecked()
                and self.chk_line_trend.Enabled else u"False")
            inc_smooth = (u"True" if self.chk_line_smooth.IsChecked()
                and self.chk_line_smooth.Enabled else u"False")
            script_lst.append(get_line_chart_script(ytitle2use,
                line_time_series, rotate, major, inc_trend, inc_smooth,
                hide_markers, css_fil, css_idx))
        elif self.chart_type == mg.AREA_CHART:
            script_lst.append(get_area_chart_script(ytitle2use,
                area_time_series, rotate, major, hide_markers, css_fil,
                css_idx))
        elif self.chart_type == mg.HISTOGRAM:
            inc_normal = (u"True" if self.chk_show_normal.IsChecked()
                else u"False")
            script_lst.append(get_histogram_script(inc_normal, 
                show_borders=self.chk_hist_borders.IsChecked(), css_fil=css_fil, 
                css_idx=css_idx))
        elif self.chart_type == mg.SCATTERPLOT:
            script_lst.append(get_scatterplot_script(css_fil, css_idx, 
                show_borders=self.chk_dot_borders.IsChecked(),
                inc_regression=self.chk_regression.IsChecked()))
        elif self.chart_type == mg.BOXPLOT:
            boxplot_opt = mg.CHART_BOXPLOT_OPTIONS[self.drop_box_opts.GetSelection()]
            script_lst.append(get_boxplot_script(rotate, boxplot_opt,
                css_fil, css_idx))
        script_lst.append(u"fil.write(chart_output)")
        return u"\n".join(script_lst)

def get_simple_barchart_script(ytitle2use, rotate, show_borders, css_fil, 
                               css_idx):
    esc_css_fil = lib.escape_pre_write(css_fil)
    script = (u"""
chart_output_dets = charting_output.get_gen_chart_output_dets(
    mg.SIMPLE_BARCHART, 
    dbe, cur, tbl, tbl_filt, 
    var_role_agg, var_role_agg_name, var_role_agg_lbls, 
    var_role_cat, var_role_cat_name, var_role_cat_lbls,
    var_role_series, var_role_series_name, var_role_series_lbls,
    var_role_charts, var_role_charts_name, var_role_charts_lbls, 
    sort_opt=mg.%(sort_opt)s, rotate=%(rotate)s, 
    data_show=mg.%(data_show)s)
x_title = var_role_cat_name
y_title = %(ytitle2use)s
chart_output = charting_output.simple_barchart_output(titles, subtitles,
    x_title, y_title, chart_output_dets, rotate=%(rotate)s, 
    show_borders=%(show_borders)s, css_fil=u"%(css_fil)s", 
    css_idx=%(css_idx)s, page_break_after=False)""" % 
    {u"sort_opt": mg.SORT_LBL2KEY[CUR_SORT_OPT_LBL], 
    u"data_show": mg.DATA_SHOW_LBL2KEY[CUR_DATA_OPT_LBL], 
           u"ytitle2use": ytitle2use, u"rotate": rotate,
           u"show_borders": show_borders, u"css_fil": esc_css_fil, 
           u"css_idx": css_idx})
    return script

def get_clustered_barchart_script(ytitle2use, rotate, show_borders, css_fil, 
                                  css_idx):
    esc_css_fil = lib.escape_pre_write(css_fil)
    script = (u"""
chart_output_dets = charting_output.get_gen_chart_output_dets(
    mg.CLUSTERED_BARCHART, 
    dbe, cur, tbl, tbl_filt, 
    var_role_agg, var_role_agg_name, var_role_agg_lbls, 
    var_role_cat, var_role_cat_name, var_role_cat_lbls,
    var_role_series, var_role_series_name, var_role_series_lbls,
    var_role_charts, var_role_charts_name, var_role_charts_lbls, 
    sort_opt=mg.%(sort_opt)s, rotate=%(rotate)s, 
    data_show=mg.%(data_show)s)
x_title = var_role_cat_name
y_title = %(ytitle2use)s
chart_output = charting_output.clustered_barchart_output(titles, subtitles,
    x_title, y_title, chart_output_dets, rotate=%(rotate)s, 
    show_borders=%(show_borders)s, css_fil=u"%(css_fil)s", 
    css_idx=%(css_idx)s, page_break_after=False)""" % 
    {u"sort_opt": mg.SORT_LBL2KEY[CUR_SORT_OPT_LBL], 
    u"data_show": mg.DATA_SHOW_LBL2KEY[CUR_DATA_OPT_LBL], 
           u"ytitle2use": ytitle2use, u"rotate": rotate, 
           u"show_borders": show_borders, u"css_fil": esc_css_fil, 
           u"css_idx": css_idx})
    return script

def get_pie_chart_script(css_fil, css_idx, inc_val_dets):
    esc_css_fil = lib.escape_pre_write(css_fil)
    script = (u"""
chart_output_dets = charting_output.get_gen_chart_output_dets(mg.PIE_CHART, 
    dbe, cur, tbl, tbl_filt, 
    var_role_agg, var_role_agg_name, var_role_agg_lbls, 
    var_role_cat, var_role_cat_name, var_role_cat_lbls, 
    var_role_series, var_role_series_name, var_role_series_lbls, 
    var_role_charts, var_role_charts_name, var_role_charts_lbls, 
    sort_opt=mg.%(sort_opt)s)
chart_output = charting_output.piechart_output(titles, subtitles,
    chart_output_dets, inc_val_dets=%(inc_val_dets)s, 
    css_fil=u"%(css_fil)s", css_idx=%(css_idx)s, page_break_after=False)""" % 
    {u"sort_opt": mg.SORT_LBL2KEY[CUR_SORT_OPT_LBL], u"css_fil": esc_css_fil, 
    u"css_idx": css_idx, u"inc_val_dets": inc_val_dets})
    return script

def get_line_chart_script(ytitle2use, time_series, rotate, major_ticks,
        inc_trend, inc_smooth, hide_markers, css_fil, css_idx):
    esc_css_fil = lib.escape_pre_write(css_fil)
    xy_titles = (u"""
x_title = var_role_cat_name
y_title = %(ytitle2use)s""" % {u"ytitle2use": ytitle2use})
    script = (u"""
chart_output_dets = charting_output.get_gen_chart_output_dets(mg.LINE_CHART, 
    dbe, cur, tbl, tbl_filt, 
    var_role_agg, var_role_agg_name, var_role_agg_lbls, 
    var_role_cat, var_role_cat_name, var_role_cat_lbls,
    var_role_series, var_role_series_name, var_role_series_lbls,
    var_role_charts, var_role_charts_name, var_role_charts_lbls, 
    sort_opt=mg.%(sort_opt)s, rotate=%(rotate)s, 
    data_show=mg.%(data_show)s, major_ticks=%(major_ticks)s, 
    time_series=%(time_series)s)
%(xy_titles)s
chart_output = charting_output.linechart_output(titles, subtitles, 
    x_title, y_title, chart_output_dets, time_series=%(time_series)s, 
    rotate=%(rotate)s, major_ticks=%(major_ticks)s, inc_trend=%(inc_trend)s, 
    inc_smooth=%(inc_smooth)s, hide_markers=%(hide_markers)s,
    css_fil=u"%(css_fil)s", css_idx=%(css_idx)s, page_break_after=False)""" %
    {u"sort_opt": mg.SORT_LBL2KEY[CUR_SORT_OPT_LBL], 
    u"data_show": mg.DATA_SHOW_LBL2KEY[CUR_DATA_OPT_LBL],
    u"time_series": time_series,
    u"rotate": rotate, u"major_ticks": major_ticks, u"xy_titles": xy_titles, 
    u"inc_trend": inc_trend, u"inc_smooth": inc_smooth,
    u"hide_markers": hide_markers, u"css_fil": esc_css_fil,
    u"css_idx": css_idx})
    return script

def get_area_chart_script(ytitle2use, time_series, rotate, major_ticks,
        hide_markers, css_fil, css_idx):
    esc_css_fil = lib.escape_pre_write(css_fil)
    dd = mg.DATADETS_OBJ
    script = (u"""
chart_output_dets = charting_output.get_gen_chart_output_dets(mg.AREA_CHART, 
    dbe, cur, tbl, tbl_filt, 
    var_role_agg, var_role_agg_name, var_role_agg_lbls, 
    var_role_cat, var_role_cat_name, var_role_cat_lbls,
    var_role_series, var_role_series_name, var_role_series_lbls,
    var_role_charts, var_role_charts_name, var_role_charts_lbls, 
    sort_opt=mg.%(sort_opt)s, rotate=%(rotate)s, 
    data_show=mg.%(data_show)s, major_ticks=%(major_ticks)s,
    time_series=%(time_series)s)
x_title = var_role_cat_name
y_title = %(ytitle2use)s
chart_output = charting_output.areachart_output(titles, subtitles, 
    x_title, y_title, chart_output_dets, time_series=%(time_series)s,
    rotate=%(rotate)s, major_ticks=%(major_ticks)s,
    hide_markers=%(hide_markers)s, css_fil=u"%(css_fil)s", 
    css_idx=%(css_idx)s, page_break_after=False)""" % {u"dbe": dd.dbe, 
    u"sort_opt": mg.SORT_LBL2KEY[CUR_SORT_OPT_LBL], 
    u"data_show": mg.DATA_SHOW_LBL2KEY[CUR_DATA_OPT_LBL],
    u"time_series": time_series, u"rotate": rotate, u"major_ticks": major_ticks,
    u"hide_markers": hide_markers, u"ytitle2use": ytitle2use,
    u"css_fil": esc_css_fil, u"css_idx": css_idx})
    return script

def get_histogram_script(inc_normal, show_borders, css_fil, css_idx):
    esc_css_fil = lib.escape_pre_write(css_fil)
    dd = mg.DATADETS_OBJ
    script = (u"""
(overall_title, 
chart_dets) = charting_output.get_histo_dets(dbe, cur, tbl, tbl_filt, flds,
    var_role_bin, var_role_bin_name, var_role_charts, var_role_charts_name, 
    var_role_charts_lbls, inc_normal=%(inc_normal)s)
chart_output = charting_output.histogram_output(titles, subtitles, 
    var_role_bin_name, overall_title, chart_dets, inc_normal=%(inc_normal)s, 
    show_borders=%(show_borders)s, css_fil=u"%(css_fil)s", 
    css_idx=%(css_idx)s, page_break_after=False)""" % {u"dbe": dd.dbe, 
        u"inc_normal": inc_normal, u"show_borders": show_borders, 
        u"css_fil": esc_css_fil, u"css_idx": css_idx})
    return script

def get_scatterplot_script(css_fil, css_idx, show_borders, inc_regression):
    esc_css_fil = lib.escape_pre_write(css_fil)
    dd = mg.DATADETS_OBJ
    regression = "True" if inc_regression else "False"
    script = (u"""
(overall_title, 
 scatterplot_dets) = charting_output.get_scatterplot_dets(dbe, cur, tbl, 
    tbl_filt, flds, var_role_x_axis, var_role_x_axis_name, 
    var_role_y_axis, var_role_y_axis_name, 
    var_role_series, var_role_series_name, var_role_series_lbls,
    var_role_charts, var_role_charts_name, var_role_charts_lbls, 
    unique=True, inc_regression=%(regression)s)
chart_output = charting_output.scatterplot_output(titles, subtitles,
    overall_title, scatterplot_dets, var_role_x_axis_name, var_role_y_axis_name, 
    add_to_report, report_name, %(show_borders)s, css_fil=u"%(css_fil)s", 
    css_idx=%(css_idx)s, page_break_after=False)
    """ % {u"dbe": dd.dbe, u"css_fil": esc_css_fil, u"css_idx": css_idx, 
        u"show_borders": show_borders, u"regression": regression})
    return script

def get_boxplot_script(rotate, boxplot_opt, css_fil, css_idx):
    esc_css_fil = lib.escape_pre_write(css_fil)
    dd = mg.DATADETS_OBJ
    script = (u"""
(xaxis_dets, xmin, xmax, ymin, ymax, 
 max_label_len, max_lbl_lines, 
 overall_title, chart_dets, 
 any_missing_boxes) = charting_output.get_boxplot_dets(dbe, cur, tbl, tbl_filt, 
                    flds, var_role_desc, var_role_desc_name,
                    var_role_cat, var_role_cat_name, var_role_cat_lbls,
                    var_role_series, var_role_series_name, var_role_series_lbls,
                    sort_opt="%(sort_opt)s", rotate=%(rotate)s,
                    boxplot_opt="%(boxplot_opt)s")
x_title = var_role_cat_name if var_role_cat_name else u""
y_title = var_role_desc_name 
chart_output = charting_output.boxplot_output(titles, subtitles, 
            any_missing_boxes, x_title, y_title, var_role_series_name, 
            xaxis_dets, max_label_len, max_lbl_lines, overall_title, chart_dets, 
            xmin, xmax, ymin, ymax, rotate=%(rotate)s,
            boxplot_opt="%(boxplot_opt)s", css_fil=u"%(css_fil)s", 
            css_idx=%(css_idx)s, page_break_after=False)
    """ % {u"dbe": dd.dbe, u"css_fil": esc_css_fil, 
        u"sort_opt": mg.SORT_LBL2KEY[CUR_SORT_OPT_LBL], u"rotate": rotate,
        u"boxplot_opt": boxplot_opt, u"css_idx": css_idx})
    return script
