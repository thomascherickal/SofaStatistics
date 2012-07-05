#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import wx

import my_globals as mg
import lib
import my_exceptions
import config_output
import full_html
import indep2var
import projects

OUTPUT_MODULES = ["my_globals as mg", "core_stats", "charting_output", "output", 
                  "getdata"]
LIMITS_MSG = (u"This chart type is not currently available in this release. "
              u"More chart types coming soon!")
CUR_SORT_OPT = mg.SORT_NONE
CUR_DATA_OPT = mg.SHOW_FREQ
SHOW_AVG = False
ROTATE = False

"""
If sorting of x-axis not explicit, will be sort_opt=mg.SORT_NONE and will thus 
    be sorted by values not labels and order of values determined by GROUP BY
    in database engine used. See specifics in, for example, 
    get_line_chart_script().
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
                   style=wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX|
                   wx.RESIZE_BORDER|wx.CLOSE_BOX|wx.SYSTEM_MENU|
                   wx.CAPTION|wx.CLIP_CHILDREN)
        config_output.ConfigUI.__init__(self, autoupdate=True)
        cc = config_output.get_cc()
        global SHOW_AVG
        SHOW_AVG = False
        global CUR_DATA_OPT
        CUR_DATA_OPT = mg.SHOW_FREQ
        self.min_data_type = None # not used here - need fine-grained control of 
        # up to 3 drop downs
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.url_load = True # btn_expand
        (self.var_labels, self.var_notes, 
         self.var_types, 
         self.val_dics) = lib.get_var_dets(cc[mg.CURRENT_VDTS_PATH])
        variables_rc_msg = _("Right click variables to view/edit details")
        config_output.add_icon(frame=self)
        self.szr_main = wx.BoxSizer(wx.VERTICAL)
        # top panel
        self.panel_top = wx.Panel(self)        
        bx_vars = wx.StaticBox(self.panel_top, -1, _("Variables"))
        self.szr_top = wx.BoxSizer(wx.VERTICAL)
        szr_help_data = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_data = self.get_szr_data(self.panel_top) # mixin
        if mg.PLATFORM == mg.LINUX: # http://trac.wxwidgets.org/ticket/9859
            bx_vars.SetToolTipString(variables_rc_msg)
        self.btn_help = wx.Button(self.panel_top, wx.ID_HELP)
        self.btn_help.Bind(wx.EVT_BUTTON, self.on_btn_help)
        self.szr_vars = wx.StaticBoxSizer(bx_vars, wx.HORIZONTAL)
        self.szr_vars_top_left = wx.BoxSizer(wx.VERTICAL)
        szr_chart_btns = wx.BoxSizer(wx.HORIZONTAL)
        self.chart_type = mg.SIMPLE_BARCHART
        init_chart_config = mg.CHART_CONFIG[self.chart_type][mg.NON_AVG_KEY]
        dropdown_width = self.get_dropdown_width(init_chart_config)
        # var 1
        lbl1 = init_chart_config[0][mg.LBL_KEY]
        min_data_type1 = init_chart_config[0][mg.MIN_DATA_TYPE_KEY]
        self.lbl_var1 = wx.StaticText(self.panel_top, -1, u"%s:" % lbl1)
        self.lbl_var1.SetFont(self.LABEL_FONT)
        self.drop_var1 = wx.Choice(self.panel_top, -1, choices=[], 
                                   size=(dropdown_width,-1))
        self.drop_var1.Bind(wx.EVT_CHOICE, self.on_var1_sel)
        self.drop_var1.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_var1)
        self.drop_var1.SetToolTipString(variables_rc_msg)
        self.sorted_var_names1 = []
        self.setup_var_dropdown(self.drop_var1, mg.VAR_1_DEFAULT, 
                                self.sorted_var_names1, var_name=None,
                                override_min_data_type=min_data_type1)
        # var 2
        lbl2 = init_chart_config[1][mg.LBL_KEY]
        min_data_type2 = init_chart_config[1][mg.MIN_DATA_TYPE_KEY]
        self.lbl_var2 = wx.StaticText(self.panel_top, -1, u"%s:" % lbl2)
        self.lbl_var2.SetFont(self.LABEL_FONT)
        self.drop_var2 = wx.Choice(self.panel_top, -1, choices=[], 
                                   size=(dropdown_width,-1))
        self.drop_var2.Bind(wx.EVT_CHOICE, self.on_var2_sel)
        self.drop_var2.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_var2)
        self.drop_var2.SetToolTipString(variables_rc_msg)
        self.sorted_var_names2 = []
        self.setup_var_dropdown(self.drop_var2, mg.VAR_2_DEFAULT, 
                                self.sorted_var_names2, var_name=None, 
                                inc_drop_select=True,
                                override_min_data_type=min_data_type2)
        # var 3
        lbl3 = mg.CHARTS_CHART_BY
        min_data_type3 = mg.VAR_TYPE_CAT
        try:
            lbl3 = init_chart_config[2][mg.LBL_KEY]
            min_data_type3 = init_chart_config[2][mg.MIN_DATA_TYPE_KEY]
        except Exception:
            # OK if not a third drop down for chart
            my_exceptions.DoNothingException()
        self.lbl_var3 = wx.StaticText(self.panel_top, -1, u"%s:" % lbl3)
        self.lbl_var3.SetFont(self.LABEL_FONT)
        self.drop_var3 = wx.Choice(self.panel_top, -1, choices=[], 
                                   size=(dropdown_width,-1))
        self.drop_var3.Bind(wx.EVT_CHOICE, self.on_var3_sel)
        self.drop_var3.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_var3)
        self.drop_var3.SetToolTipString(variables_rc_msg)
        self.sorted_var_names3 = []
        self.setup_var_dropdown(self.drop_var3, mg.VAR_3_DEFAULT, 
                                self.sorted_var_names3, var_name=None, 
                                inc_drop_select=True, 
                                override_min_data_type=min_data_type3)
        # var 3 visibility
        try:
            init_chart_config[2]
        except Exception:
            self.lbl_var3.Hide()
            self.drop_var3.Hide()
        # var 4
        lbl4 = mg.CHARTS_CHART_BY
        min_data_type4 = mg.VAR_TYPE_CAT
        try:
            lbl4 = init_chart_config[3][mg.LBL_KEY]
            min_data_type4 = init_chart_config[3][mg.MIN_DATA_TYPE_KEY]
        except Exception:
            # OK if not a third drop down for chart
            my_exceptions.DoNothingException()
        self.lbl_var4 = wx.StaticText(self.panel_top, -1, u"%s:" % lbl4)
        self.lbl_var4.SetFont(self.LABEL_FONT)
        self.drop_var4 = wx.Choice(self.panel_top, -1, choices=[], 
                                   size=(dropdown_width,-1))
        self.drop_var4.Bind(wx.EVT_CHOICE, self.on_var4_sel)
        self.drop_var4.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_var4)
        self.drop_var4.SetToolTipString(variables_rc_msg)
        self.sorted_var_names4 = []
        self.setup_var_dropdown(self.drop_var4, mg.VAR_4_DEFAULT, 
                                self.sorted_var_names4, var_name=None, 
                                inc_drop_select=True, 
                                override_min_data_type=min_data_type4)
        # var 4 visibility
        try:
            init_chart_config[3]
        except Exception:
            self.lbl_var4.Hide()
            self.drop_var4.Hide()
        # layout
        help_down_by = 27 if mg.PLATFORM == mg.MAC else 17
        szr_help_data.Add(self.btn_help, 0, wx.TOP, help_down_by)
        szr_help_data.Add(self.szr_data, 1, wx.LEFT, 5)
        self.szr_vars.Add(self.lbl_var1, 0, wx.TOP|wx.RIGHT, 5)
        self.szr_vars.Add(self.drop_var1, 0, wx.RIGHT|wx.TOP, 5)
        self.szr_vars.Add(self.lbl_var2, 0, wx.TOP|wx.RIGHT, 5)
        self.szr_vars.Add(self.drop_var2, 0, wx.RIGHT|wx.TOP, 5)
        self.szr_vars.Add(self.lbl_var3, 0, wx.TOP|wx.RIGHT, 5)
        self.szr_vars.Add(self.drop_var3, 0, wx.RIGHT|wx.TOP, 5)
        self.szr_vars.Add(self.lbl_var4, 0, wx.TOP|wx.RIGHT, 5)
        self.szr_vars.Add(self.drop_var4, 0, wx.RIGHT|wx.TOP, 5)
        # assemble sizer for top panel
        static_box_gap = 0 if mg.PLATFORM == mg.MAC else 5
        if static_box_gap:
            self.szr_top.Add(wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, 
                             static_box_gap)
        self.szr_top.Add(szr_help_data, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        if static_box_gap:
            self.szr_top.Add(wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, 
                             static_box_gap)
        self.szr_top.Add(self.szr_vars, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        self.panel_top.SetSizer(self.szr_top)
        self.szr_top.SetSizeHints(self.panel_top)
        # Charts
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
        self.rad_bar_sort_opts = self.get_rad_sort(self.panel_bar_chart)
        self.rad_simple_bar_perc = self.get_rad_perc(self.panel_bar_chart)
        self.chk_simple_bar_avg = self.get_chk_avg(self.panel_bar_chart, 
                                                   self.on_chk_simple_bar_avg)
        self.chk_simple_bar_rotate = self.get_chk_rotate(self.panel_bar_chart)
        if mg.PLATFORM == mg.WINDOWS:
            tickbox_down_by = 27 # to line up with a combo
        elif mg.PLATFORM == mg.LINUX:
            tickbox_down_by = 22
        else:
            tickbox_down_by = 27
        self.szr_bar_chart.Add(self.rad_bar_sort_opts, 0, wx.TOP|wx.RIGHT, 5)
        self.szr_bar_chart.Add(self.rad_simple_bar_perc, 0, wx.TOP, 5)
        self.szr_bar_chart.AddSpacer(10)
        self.szr_bar_chart.Add(self.chk_simple_bar_avg, 0, wx.TOP, 
                               tickbox_down_by)
        self.szr_bar_chart.AddSpacer(10)
        self.szr_bar_chart.Add(self.chk_simple_bar_rotate, 0, wx.TOP, 
                               tickbox_down_by)
        self.panel_bar_chart.SetSizer(self.szr_bar_chart)
        self.szr_bar_chart.SetSizeHints(self.panel_bar_chart)
        # clustered bar chart
        self.szr_clust_bar_chart = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_clust_bar_chart = wx.Panel(self.panel_mid)
        self.rad_clust_bar_perc = self.get_rad_perc(self.panel_clust_bar_chart)
        self.chk_clust_bar_rotate = self.get_chk_rotate(self.panel_clust_bar_chart)
        self.chk_clust_bar_avg = self.get_chk_avg(self.panel_clust_bar_chart, 
                                                  self.on_chk_clust_bar_avg)
        self.szr_clust_bar_chart.Add(self.rad_clust_bar_perc, 0, wx.TOP, 5)
        self.szr_clust_bar_chart.AddSpacer(10)
        self.szr_clust_bar_chart.Add(self.chk_clust_bar_avg, 0, wx.TOP, 
                                         tickbox_down_by)
        self.szr_clust_bar_chart.AddSpacer(10)
        self.szr_clust_bar_chart.Add(self.chk_clust_bar_rotate, 0, wx.TOP, 
                                         tickbox_down_by)
        self.panel_clust_bar_chart.SetSizer(self.szr_clust_bar_chart)
        self.szr_clust_bar_chart.SetSizeHints(self.panel_clust_bar_chart)
        # pie chart
        self.szr_pie_chart = wx.BoxSizer(wx.VERTICAL)
        self.panel_pie_chart = wx.Panel(self.panel_mid)
        self.rad_pie_sort_opts = self.get_rad_sort(self.panel_pie_chart, 
                                                   u"slices")
        self.szr_pie_chart.Add(self.rad_pie_sort_opts, 0, wx.TOP, 5)
        self.panel_pie_chart.SetSizer(self.szr_pie_chart)
        self.szr_pie_chart.SetSizeHints(self.panel_pie_chart)
        # line chart
        self.szr_line_chart = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_line_chart = wx.Panel(self.panel_mid)
        self.rad_line_perc = self.get_rad_perc(self.panel_line_chart)
        self.szr_line_chart.Add(self.rad_line_perc, 0, wx.TOP, 5)
        self.chk_line_rotate = self.get_chk_rotate(self.panel_line_chart)
        self.chk_line_trend = wx.CheckBox(self.panel_line_chart, -1, 
                                         _("Show trend line?"))
        self.chk_line_trend.SetValue(False)
        self.chk_line_trend.SetToolTipString(_(u"Show trend line?"))
        self.chk_line_smooth = wx.CheckBox(self.panel_line_chart, -1, 
                                         _("Show smoothed data line?"))
        self.chk_line_smooth.SetValue(False)
        self.chk_line_smooth.SetToolTipString(_(u"Show smoothed data line?"))
        self.chk_line_avg = self.get_chk_avg(self.panel_line_chart, 
                                             self.on_chk_line_avg)
        self.szr_line_chart.AddSpacer(10)
        self.szr_line_chart.Add(self.chk_line_avg, 0, wx.TOP, 
                                tickbox_down_by)
        self.szr_line_chart.AddSpacer(10)
        self.szr_line_chart.Add(self.chk_line_trend, 0, wx.TOP, 
                                tickbox_down_by)
        self.szr_line_chart.AddSpacer(10)
        self.szr_line_chart.Add(self.chk_line_smooth, 0, wx.TOP, 
                                tickbox_down_by)
        self.szr_line_chart.AddSpacer(10)
        self.szr_line_chart.Add(self.chk_line_rotate, 0, wx.TOP, 
                                tickbox_down_by)
        self.panel_line_chart.SetSizer(self.szr_line_chart)
        self.szr_line_chart.SetSizeHints(self.panel_line_chart)
        # area chart
        self.szr_area_chart = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_area_chart = wx.Panel(self.panel_mid)
        self.rad_area_perc = self.get_rad_perc(self.panel_area_chart)
        self.chk_area_rotate = self.get_chk_rotate(self.panel_area_chart)
        self.chk_area_avg = self.get_chk_avg(self.panel_area_chart, 
                                             self.on_chk_area_avg)
        self.szr_area_chart.Add(self.rad_area_perc, 0, wx.TOP, 5)
        self.szr_area_chart.AddSpacer(10)
        self.szr_area_chart.Add(self.chk_area_avg, 0, wx.TOP, 
                                tickbox_down_by)
        self.szr_area_chart.AddSpacer(10)
        self.szr_area_chart.Add(self.chk_area_rotate, 0, wx.TOP, 
                                tickbox_down_by)
        self.panel_area_chart.SetSizer(self.szr_area_chart)
        self.szr_area_chart.SetSizeHints(self.panel_area_chart)
        # histogram
        self.szr_histogram = wx.BoxSizer(wx.VERTICAL)
        self.panel_histogram = wx.Panel(self.panel_mid)
        self.chk_show_normal = wx.CheckBox(self.panel_histogram, -1, 
                                           _("Show normal curve?"))
        self.chk_show_normal.SetValue(False)
        self.chk_show_normal.SetToolTipString(_(u"Show normal curve?"))
        self.szr_histogram.Add(self.chk_show_normal, 0, 
                               wx.TOP|wx.BOTTOM|wx.LEFT, 10)
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
        # boxplot
        self.szr_boxplot = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_boxplot = wx.Panel(self.panel_mid)
        self.chk_boxplot_rotate = self.get_chk_rotate(self.panel_boxplot)
        self.szr_boxplot.Add(self.chk_boxplot_rotate, 0, 
                             wx.TOP|wx.BOTTOM|wx.LEFT, 10)
        self.panel_boxplot.SetSizer(self.szr_boxplot)
        self.szr_boxplot.SetSizeHints(self.panel_boxplot)
        # Hide all panels except default. Display and layout then hide.
        # Prevents flicker on change later.
        panels2hide = [self.panel_clust_bar_chart, self.panel_pie_chart,
                       self.panel_line_chart, self.panel_area_chart,
                       self.panel_histogram, self.panel_scatterplot, 
                       self.panel_boxplot]
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
        self.szr_main.Add(self.panel_top, 0, wx.GROW)
        if static_box_gap:
            self.szr_main.Add(wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, 
                              static_box_gap)
        self.szr_main.Add(self.panel_mid, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        self.szr_main.Add(self.panel_bottom, 1, wx.GROW)
        self.SetAutoLayout(True)
        self.SetSizer(self.szr_main)
        szr_lst = [self.panel_top, self.panel_mid, self.panel_bottom]
        lib.set_size(window=self, szr_lst=szr_lst, width_init=1024, 
                     height_init=myheight)
    
    def get_dropdown_width(self, chart_config):
        dropdown_width = 210 if len(chart_config) < 4 else 175 # 4, 175
        return dropdown_width
    
    def get_rad_perc(self, panel):
        rad = wx.RadioBox(panel, -1, _(u"Data reported"), 
                          choices=mg.DATA_SHOW_OPTS, size=(-1,50))
        idx_data_opt = mg.DATA_SHOW_OPTS.index(CUR_DATA_OPT)
        rad.SetSelection(idx_data_opt)
        rad.SetToolTipString(_(u"Report frequency or percentage?"))
        rad.Bind(wx.EVT_RADIOBOX, self.on_rad_perc)
        return rad
    
    def get_chk_rotate(self, panel):
        chk = wx.CheckBox(panel, -1, _("Rotate labels?"))
        chk.SetValue(ROTATE)
        chk.SetToolTipString(_(u"Rotate x-axis labels?"))
        chk.Bind(wx.EVT_CHECKBOX, self.on_chk_rotate)
        return chk
    
    def get_rad_sort(self, panel, sort_item=u"bars"):
        rad = wx.RadioBox(panel, -1, _(u"Sort order of %s" % sort_item), 
                          choices=mg.SORT_OPTS, size=(-1,50))
        idx_current_sort_opt = mg.SORT_OPTS.index(CUR_SORT_OPT)
        rad.SetSelection(idx_current_sort_opt)
        rad.Bind(wx.EVT_RADIOBOX, self.on_rad_sort_opt)
        return rad
    
    def get_chk_avg(self, panel, on_event):
        chk = wx.CheckBox(panel, -1, _("Show averages?"))
        chk.SetValue(SHOW_AVG)
        chk.SetToolTipString(_(u"Show averages not frequencies?"))
        chk.Bind(wx.EVT_CHECKBOX, on_event)
        return chk
    
    def on_show(self, event):
        try:
            self.html.pizza_magic() # must happen after Show
        except Exception:
            my_exceptions.DoNothingException() # need on Mac or exception survives
        finally:
            # any initial content
            html2show = _("<p>Waiting for a report to be run.</p>")
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
            self.btn_clust_bar_chart.SetCursor(hand)
            self.btn_pie_chart.SetCursor(hand)
            self.btn_line_chart.SetCursor(hand)
            self.btn_area_chart.SetCursor(hand)
            self.btn_histogram.SetCursor(hand)
            self.btn_scatterplot.SetCursor(hand)
            self.btn_boxplot.SetCursor(hand)
        self.btn_to_rollback = self.btn_bar_chart
        self.bmp_to_rollback_to = self.bmp_btn_bar_chart

    def get_chart_subtype_key(self):
        chart_subtype_key = (mg.AVG_KEY 
                             if (mg.AVG_KEY in mg.CHART_CONFIG[self.chart_type]) 
                                 and SHOW_AVG
                             else mg.NON_AVG_KEY)
        return chart_subtype_key

    def refresh_vars(self):
        self.setup_var_dropdowns()
        self.update_defaults()

    def setup_var_dropdowns(self):
        debug = False
        if debug: print(u"Chart type is: %s" % self.chart_type)
        varname1, varname2, varname3, varname4 = self.get_vars()
        chart_subtype_key = self.get_chart_subtype_key()
        chart_config = mg.CHART_CONFIG[self.chart_type][chart_subtype_key]
        dropdown_width = self.get_dropdown_width(chart_config)
        if debug: print(u"Dropdown width: %s" % dropdown_width)
        # var 1
        lbl1 = chart_config[0][mg.LBL_KEY]
        min_data_type1 = chart_config[0][mg.MIN_DATA_TYPE_KEY]
        inc_drop_select1 = chart_config[0][mg.INC_SELECT_KEY]
        self.setup_var_dropdown(self.drop_var1, mg.VAR_1_DEFAULT, 
                                self.sorted_var_names1, var_name=varname1,
                                inc_drop_select=inc_drop_select1, 
                                override_min_data_type=min_data_type1)
        self.lbl_var1.SetLabel(u"%s:" % lbl1)
        self.drop_var1.SetMaxSize(wx.Size(dropdown_width,-1))
        self.drop_var1.SetMinSize(wx.Size(dropdown_width,-1))
        # var 2
        lbl2 = chart_config[1][mg.LBL_KEY]
        min_data_type2 = chart_config[1][mg.MIN_DATA_TYPE_KEY]
        inc_drop_select2 = chart_config[1][mg.INC_SELECT_KEY]
        self.setup_var_dropdown(self.drop_var2, mg.VAR_2_DEFAULT, 
                                self.sorted_var_names2, var_name=varname2, 
                                inc_drop_select=inc_drop_select2, 
                                override_min_data_type=min_data_type2)
        self.drop_var2.Enable(True)
        self.lbl_var2.Enable(True)
        self.lbl_var2.SetLabel(u"%s:" % lbl2)
        self.drop_var2.SetMaxSize(wx.Size(dropdown_width,-1))
        self.drop_var2.SetMinSize(wx.Size(dropdown_width,-1))
        # var 3
        show3 = True
        try:
            chart_config[2]
            lbl3 = chart_config[2][mg.LBL_KEY]
            min_data_type3 = chart_config[2][mg.MIN_DATA_TYPE_KEY]
            inc_drop_select3 = chart_config[2][mg.INC_SELECT_KEY]
            self.setup_var_dropdown(self.drop_var3, mg.VAR_3_DEFAULT, 
                                    self.sorted_var_names3, var_name=varname3, 
                                    inc_drop_select=inc_drop_select3, 
                                    override_min_data_type=min_data_type3)
            self.lbl_var3.SetLabel(u"%s:" % lbl3)
            self.drop_var3.SetMaxSize(wx.Size(dropdown_width,-1))
            self.drop_var3.SetMinSize(wx.Size(dropdown_width,-1))
        except Exception:
            show3 = False
        # var 4
        show4 = True
        try:
            chart_config[3]
            lbl4 = chart_config[3][mg.LBL_KEY]
            min_data_type4 = chart_config[3][mg.MIN_DATA_TYPE_KEY]
            inc_drop_select4 = chart_config[3][mg.INC_SELECT_KEY]
            self.setup_var_dropdown(self.drop_var4, mg.VAR_4_DEFAULT, 
                                    self.sorted_var_names4, var_name=varname4, 
                                    inc_drop_select=inc_drop_select4, 
                                    override_min_data_type=min_data_type4)
            self.lbl_var4.SetLabel(u"%s:" % lbl4)
            self.drop_var4.SetMaxSize(wx.Size(dropdown_width,-1))
            self.drop_var4.SetMinSize(wx.Size(dropdown_width,-1))
        except Exception:
            show4 = False
        self.panel_top.Layout()
        """
        Make fresh layout (don't want to end up with the drop downs narrower but 
            still as far apart as when wide).
        """
        self.szr_vars.Clear()
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
        self.lbl_var3.Show(show3)
        self.drop_var3.Show(show3)
        self.lbl_var4.Show(show4)
        self.drop_var4.Show(show4)
        self.panel_top.Layout()
        
    def on_rad_perc(self, event):
        debug = False
        global CUR_DATA_OPT
        # http://www.blog.pythonlibrary.org/2011/09/20/...
        # ... wxpython-binding-multiple-widgets-to-the-same-handler/
        rad = event.GetEventObject()
        idx_sel = rad.GetSelection()
        try:
            CUR_DATA_OPT = mg.DATA_SHOW_OPTS[idx_sel]
        except IndexError:
            my_exceptions.DoNothingException()
        if debug: print(u"Current data option: %s" % CUR_DATA_OPT)
    
    def on_chk_rotate(self, event):
        global ROTATE
        chk = event.GetEventObject()
        ROTATE = chk.IsChecked()

    def on_chk_avg(self, chk, rad):
        global SHOW_AVG
        SHOW_AVG = chk.IsChecked()
        self.setup_var_dropdowns()
        rad.Enable(not SHOW_AVG)
            
    def on_chk_simple_bar_avg(self, event):
        self.on_chk_avg(self.chk_simple_bar_avg, self.rad_simple_bar_perc)

    def on_chk_clust_bar_avg(self, event):
        self.on_chk_avg(self.chk_clust_bar_avg, self.rad_clust_bar_perc)
                    
    def on_chk_line_avg(self, event):
        self.on_chk_avg(self.chk_line_avg, self.rad_line_perc)
                        
    def on_chk_area_avg(self, event):
        self.on_chk_avg(self.chk_area_avg, self.rad_area_perc)
    
    def on_rad_sort_opt(self, event):
        debug = False
        global CUR_SORT_OPT
        rad = event.GetEventObject()
        idx_sel = rad.GetSelection()
        try:
            CUR_SORT_OPT = mg.SORT_OPTS[idx_sel]
        except IndexError:
            my_exceptions.DoNothingException()
        if debug: print(u"Current sort option: %s" % CUR_SORT_OPT)
        
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
        self.setup_var_dropdowns()
        self.panel_displayed.Show(False)
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
        self.rad_simple_bar_perc.SetSelection(mg.DATA_SHOW_OPTS.index(CUR_DATA_OPT))
        self.chk_simple_bar_rotate.SetValue(ROTATE)
        self.chk_simple_bar_avg.SetValue(SHOW_AVG)
        self.rad_simple_bar_perc.Enable(not SHOW_AVG)
        self.btn_chart(event, btn, btn_bmp, btn_bmp_sel, panel)

    def on_btn_clustered_bar_chart(self, event):
        self.chart_type = mg.CLUSTERED_BARCHART
        btn = self.btn_clust_bar_chart
        btn_bmp = self.bmp_btn_clust_bar_chart
        btn_bmp_sel = self.bmp_btn_clust_bar_chart_sel
        panel = self.panel_clust_bar_chart
        self.rad_clust_bar_perc.SetSelection(mg.DATA_SHOW_OPTS.index(CUR_DATA_OPT))
        self.chk_clust_bar_rotate.SetValue(ROTATE)
        self.chk_clust_bar_avg.SetValue(SHOW_AVG)
        self.rad_clust_bar_perc.Enable(not SHOW_AVG)
        self.btn_chart(event, btn, btn_bmp, btn_bmp_sel, panel)

    def on_btn_pie_chart(self, event):
        self.chart_type = mg.PIE_CHART
        btn = self.btn_pie_chart
        btn_bmp = self.bmp_btn_pie_chart
        btn_bmp_sel = self.bmp_btn_pie_chart_sel
        panel = self.panel_pie_chart
        self.rad_pie_sort_opts.SetSelection(mg.SORT_OPTS.index(CUR_SORT_OPT))
        self.btn_chart(event, btn, btn_bmp, btn_bmp_sel, panel)
        
    def on_btn_line_chart(self, event):
        self.chart_type = mg.LINE_CHART
        btn = self.btn_line_chart
        btn_bmp = self.bmp_btn_line_chart
        btn_bmp_sel = self.bmp_btn_line_chart_sel
        panel = self.panel_line_chart
        self.rad_line_perc.SetSelection(mg.DATA_SHOW_OPTS.index(CUR_DATA_OPT))
        self.chk_line_rotate.SetValue(ROTATE)
        self.chk_line_avg.SetValue(SHOW_AVG)
        self.rad_line_perc.Enable(not SHOW_AVG)
        self.btn_chart(event, btn, btn_bmp, btn_bmp_sel, panel)
        self.setup_line_extras()

    def on_btn_area_chart(self, event):
        self.chart_type = mg.AREA_CHART
        btn = self.btn_area_chart
        btn_bmp = self.bmp_btn_area_chart
        btn_bmp_sel = self.bmp_btn_area_chart_sel
        panel = self.panel_area_chart
        self.rad_area_perc.SetSelection(mg.DATA_SHOW_OPTS.index(CUR_DATA_OPT))
        self.chk_area_rotate.SetValue(ROTATE)
        self.chk_area_avg.SetValue(SHOW_AVG)
        self.rad_area_perc.Enable(not SHOW_AVG)
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
        self.chart_type = mg.BOXPLOT
        btn = self.btn_boxplot
        btn_bmp = self.bmp_btn_boxplot
        btn_bmp_sel = self.bmp_btn_boxplot_sel
        panel = self.panel_boxplot
        self.chk_boxplot_rotate.SetValue(ROTATE)
        self.btn_chart(event, btn, btn_bmp, btn_bmp_sel, panel)
        
    def on_btn_chart(self, event):
        wx.MessageBox(LIMITS_MSG)

    def on_btn_run(self, event):
        # get settings
        cc = config_output.get_cc()
        if self.chart_type not in []:
            run_ok = self.test_config_ok()
            add_to_report = self.chk_add_to_report.IsChecked()
            if run_ok:
                get_script_args=[cc[mg.CURRENT_CSS_PATH], add_to_report,
                                 cc[mg.CURRENT_REPORT_PATH]]
                config_output.ConfigUI.on_btn_run(self, event, OUTPUT_MODULES, 
                                                  get_script_args, 
                                                  new_has_dojo=True)
        else:
            wx.MessageBox(LIMITS_MSG)

    def on_btn_script(self, event):
        # TODO NB will have new_has_dojo=True
        wx.MessageBox(u"This version does not support exporting chart code yet")
    
    def on_var1_sel(self, event):
        pass
    
    def setup_line_extras(self):
        """
        Only enable trendlines and smooth line if chart type is line and a 
            single line chart.
        """
        show_line_extras = (self.chart_type == mg.LINE_CHART and (
                (not SHOW_AVG # normal and dropdown2 is nothing
                     and self.drop_var2.GetStringSelection() == mg.DROP_SELECT)
                 or (SHOW_AVG # AVG and dropdown3 is nothing
                     and self.drop_var3.GetStringSelection() == mg.DROP_SELECT)
            ))
        self.chk_line_trend.Enable(show_line_extras)
        self.chk_line_smooth.Enable(show_line_extras)
        
    def on_var2_sel(self, event):
        self.setup_line_extras()
    
    def on_var3_sel(self, event):
        self.setup_line_extras()
    
    def on_var4_sel(self, event):
        self.setup_line_extras()
    
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
        updated = projects.set_var_props(choice_item, var_name, var_label, 
                                         self.var_labels, self.var_notes, 
                                         self.var_types,  self.val_dics)
        if updated:
            self.setup_var_dropdowns()
            self.update_defaults()

    def on_database_sel(self, event):
        """
        Reset dbe, database, cursor, tables, table, tables dropdown, 
            fields, has_unique, and idxs after a database selection.
        """
        config_output.ConfigUI.on_database_sel(self, event)
        # now update var dropdowns
        config_output.update_var_dets(dlg=self)
        self.setup_var_dropdowns()
                
    def on_table_sel(self, event):
        "Reset key data details after table selection."       
        config_output.ConfigUI.on_table_sel(self, event)
        # now update var dropdowns
        config_output.update_var_dets(dlg=self)
        self.setup_var_dropdowns()
       
    def on_btn_config(self, event):
        """
        Want to retain already selected item - even though label and even 
            position may have changed.
        """
        config_output.ConfigUI.on_btn_config(self, event)
        self.setup_var_dropdowns()
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
        varname4, unused = self.get_var_dets(self.drop_var4, 
                                             self.sorted_var_names4)
        return varname1, varname2, varname3, varname4
    
    def update_defaults(self):
        """
        The values for a variable we try to keep unless it is not in the list.
        """
        debug = False
        mg.VAR_1_DEFAULT = self.drop_var1.GetStringSelection()
        mg.VAR_2_DEFAULT = self.drop_var2.GetStringSelection()
        try: # might not be visible
            mg.VAR_3_DEFAULT = self.drop_var3.GetStringSelection()
        except Exception:
            my_exceptions.DoNothingException()
        try: # might not be visible
            mg.VAR_4_DEFAULT = self.drop_var4.GetStringSelection()
        except Exception:
            my_exceptions.DoNothingException()
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
        # 1) Variable selected but an earlier one has not (No Selection instead)
        """
        Line charts have one exception - can select chart by without series by
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
                    # OK only if a line chart and we are in the chart by var 
                    if self.chart_type == mg.LINE_CHART:
                        chart_subtype_key = self.get_chart_subtype_key()
                        chart_config = mg.CHART_CONFIG[self.chart_type]\
                                                            [chart_subtype_key]
                        var_role = chart_config[var_idx][mg.VAR_ROLE_KEY]                         
                        if var_role == mg.VAR_ROLE_CHARTS:
                            continue
                    varlbl = lblctrl.GetLabel().rstrip(u":")
                    wx.MessageBox(_(u"\"%s\" has a variable selected but the "
                                    u"previous drop down list \"%s\" does not.") 
                                  % (varlbl, lbl_with_no_select))
                    return False
        # 2) Excluding No Selections, we have duplicate selections
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

    def get_script(self, css_idx, css_fil, add_to_report, report_name):
        """
        Build script from inputs.
        For each dropdown identify the variable role (according to CHART_CONFIG, 
            chart type, and whether data is averaged or not). Not all dropdowns 
            will have a variable selected (i.e. 'Not Selected' is the selection) 
            but for those that do identify the field name, field label, and the 
            value labels ready to pass to the appropriate data collection 
            function.
        """
        debug = False
        dd = mg.DATADETS_OBJ
        is_avg = (mg.AVG_KEY in mg.CHART_CONFIG[self.chart_type] and SHOW_AVG)
        is_perc = (CUR_DATA_OPT == mg.SHOW_PERC) and not is_avg
        rotate = u"True" if ROTATE else u"False"
        script_lst = []
        titles, subtitles = self.get_titles()
        script_lst.append(u"titles=%s" % unicode(titles))
        script_lst.append(u"subtitles=%s" % unicode(subtitles))
        script_lst.append(lib.get_tbl_filt_clause(dd.dbe, dd.db, dd.tbl))
        myvars = self.get_vars()
        if debug: print(myvars)
        # other variables to set up
        script_lst.append(u"add_to_report = %s" % ("True" if add_to_report
                                                    else "False"))
        rptname = lib.escape_pre_write(report_name)
        script_lst.append(u"report_name = u\"%s\"" % rptname)
        avg_fldlbl = None
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
                script_lst.append(u"%s = u\"%s\"" % (var_role, var_val)) # e.g. var_role_avg = "age"
                var_name = lib.get_item_label(self.var_labels, var_val)
                script_lst.append(u"%s_name=u\"%s\"" % (var_role, var_name)) # e.g. var_role_avg_name = "Age"
                val_lbls = self.val_dics.get(var_val, {})
                script_lst.append(u"%s_lbls = %s" % (var_role, val_lbls)) # e.g. var_role_avg_lbls = {}
            if var_role == mg.VAR_ROLE_AVG:
                avg_fldlbl = var_name
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
            if is_avg:
                if avg_fldlbl is None:
                    raise Exception(u"Label for variable being averaged not "
                                    u"supplied.")
                ytitle2use = u'u"Mean %s"' % avg_fldlbl
            else:
                ytitle2use = (u"mg.Y_AXIS_PERC_LBL" if is_perc 
                              else u"mg.Y_AXIS_FREQ_LBL")
        if self.chart_type == mg.SIMPLE_BARCHART:
            script_lst.append(get_simple_barchart_script(is_perc, ytitle2use, 
                                                    rotate, css_fil, css_idx))
        elif self.chart_type == mg.CLUSTERED_BARCHART:
            script_lst.append(get_clustered_barchart_script(is_perc, ytitle2use, 
                                                    rotate, css_fil, css_idx))
        elif self.chart_type == mg.PIE_CHART:
            script_lst.append(get_pie_chart_script(css_fil, css_idx))
        elif self.chart_type == mg.LINE_CHART:
            inc_trend = (u"True" if self.chk_line_trend.IsChecked()
                            and self.chk_line_trend.Enabled
                        else u"False")
            inc_smooth = (u"True" if self.chk_line_smooth.IsChecked()
                            and self.chk_line_smooth.Enabled
                        else u"False")
            script_lst.append(get_line_chart_script(is_perc, ytitle2use, rotate, 
                                                    inc_trend, inc_smooth, 
                                                    css_fil, css_idx))
        elif self.chart_type == mg.AREA_CHART:
            script_lst.append(get_area_chart_script(is_perc, ytitle2use, rotate, 
                                                    css_fil, css_idx))
        elif self.chart_type == mg.HISTOGRAM:
            inc_normal = (u"True" if self.chk_show_normal.IsChecked()
                          else u"False")
            script_lst.append(get_histogram_script(inc_normal, css_fil, 
                                                   css_idx))
        elif self.chart_type == mg.SCATTERPLOT:
            script_lst.append(get_scatterplot_script(css_fil, css_idx, 
                                       dot_border=self.chk_borders.IsChecked()))
        elif self.chart_type == mg.BOXPLOT:
            script_lst.append(get_boxplot_script(rotate, css_fil, css_idx))
        script_lst.append(u"fil.write(chart_output)")
        return u"\n".join(script_lst)

def get_simple_barchart_script(is_perc, ytitle2use, rotate, 
                               css_fil, css_idx):
    esc_css_fil = lib.escape_pre_write(css_fil)
    script = u"""
chart_output_dets = charting_output.get_gen_chart_output_dets(
                    mg.SIMPLE_BARCHART, 
                    dbe, cur, tbl, tbl_filt, 
                    var_role_avg, var_role_avg_name, var_role_avg_lbls, 
                    var_role_cat, var_role_cat_name, var_role_cat_lbls,
                    var_role_series, var_role_series_name, var_role_series_lbls,
                    var_role_charts, var_role_charts_name, var_role_charts_lbls, 
                    sort_opt="%(sort_opt)s", rotate=%(rotate)s, 
                    is_perc=%(is_perc)s)
x_title = var_role_cat_name
y_title = %(ytitle2use)s
chart_output = charting_output.simple_barchart_output(titles, subtitles,
    x_title, y_title, chart_output_dets, rotate=%(rotate)s, 
    css_fil=u"%(css_fil)s", css_idx=%(css_idx)s, 
    page_break_after=False)
    """ % {u"sort_opt": CUR_SORT_OPT, u"is_perc": str(is_perc), 
           u"ytitle2use": ytitle2use, u"rotate": rotate,
           u"css_fil": esc_css_fil, u"css_idx": css_idx}
    return script

def get_clustered_barchart_script(is_perc, ytitle2use, rotate, css_fil, 
                                  css_idx):
    esc_css_fil = lib.escape_pre_write(css_fil)
    script = u"""
chart_output_dets = charting_output.get_gen_chart_output_dets(
                    mg.CLUSTERED_BARCHART, 
                    dbe, cur, tbl, tbl_filt, 
                    var_role_avg, var_role_avg_name, var_role_avg_lbls, 
                    var_role_cat, var_role_cat_name, var_role_cat_lbls,
                    var_role_series, var_role_series_name, var_role_series_lbls,
                    var_role_charts, var_role_charts_name, var_role_charts_lbls, 
                    sort_opt="%(sort_opt)s", rotate=%(rotate)s, 
                    is_perc=%(is_perc)s)
x_title = var_role_cat_name
y_title = %(ytitle2use)s
chart_output = charting_output.clustered_barchart_output(titles, subtitles,
    x_title, y_title, chart_output_dets, rotate=%(rotate)s, 
    css_fil=u"%(css_fil)s", 
    css_idx=%(css_idx)s, page_break_after=False)    
    """ % {u"sort_opt": mg.SORT_NONE, u"is_perc": str(is_perc), 
           u"ytitle2use": ytitle2use, u"rotate": rotate, 
           u"css_fil": esc_css_fil, u"css_idx": css_idx}
    return script

def get_pie_chart_script(css_fil, css_idx):
    esc_css_fil = lib.escape_pre_write(css_fil)
    script = u"""
chart_output_dets = charting_output.get_gen_chart_output_dets(mg.PIE_CHART, 
                    dbe, cur, tbl, tbl_filt, 
                    var_role_avg, var_role_avg_name, var_role_avg_lbls, 
                    var_role_cat, var_role_cat_name, var_role_cat_lbls,
                    var_role_series, var_role_series_name, var_role_series_lbls,
                    var_role_charts, var_role_charts_name, var_role_charts_lbls, 
                    sort_opt="%(sort_opt)s")
chart_output = charting_output.piechart_output(titles, subtitles,
            chart_output_dets, css_fil=u"%(css_fil)s", css_idx=%(css_idx)s,
            page_break_after=False)
    """ % {u"sort_opt": CUR_SORT_OPT, u"css_fil": esc_css_fil, 
           u"css_idx": css_idx}
    return script

def get_line_chart_script(is_perc, ytitle2use, rotate, inc_trend, 
                          inc_smooth, css_fil, css_idx):
    esc_css_fil = lib.escape_pre_write(css_fil)
    xy_titles = (u"""
x_title = var_role_cat_name
y_title = %(ytitle2use)s""" % {u"ytitle2use": ytitle2use})
    script = (u"""
chart_output_dets = charting_output.get_gen_chart_output_dets(mg.LINE_CHART, 
                    dbe, cur, tbl, tbl_filt, 
                    var_role_avg, var_role_avg_name, var_role_avg_lbls, 
                    var_role_cat, var_role_cat_name, var_role_cat_lbls,
                    var_role_series, var_role_series_name, var_role_series_lbls,
                    var_role_charts, var_role_charts_name, var_role_charts_lbls, 
                    sort_opt=mg.SORT_NONE,
                    rotate=%(rotate)s, is_perc=%(is_perc)s)
%(xy_titles)s
chart_output = charting_output.linechart_output(titles, subtitles, 
    x_title, y_title, chart_output_dets, rotate=%(rotate)s, 
    inc_trend=%(inc_trend)s, inc_smooth=%(inc_smooth)s, 
    css_fil=u"%(css_fil)s", css_idx=%(css_idx)s, 
    page_break_after=False)""" %
        {u"is_perc": str(is_perc), u"rotate": rotate, u"xy_titles": xy_titles,
         u"inc_trend": inc_trend, u"inc_smooth": inc_smooth, 
         u"css_fil": esc_css_fil, u"css_idx": css_idx})
    return script

def get_area_chart_script(is_perc, ytitle2use, rotate, css_fil, css_idx):
    esc_css_fil = lib.escape_pre_write(css_fil)
    dd = mg.DATADETS_OBJ
    script = (u"""
chart_output_dets = charting_output.get_gen_chart_output_dets(mg.AREA_CHART, 
                    dbe, cur, tbl, tbl_filt, 
                    var_role_avg, var_role_avg_name, var_role_avg_lbls, 
                    var_role_cat, var_role_cat_name, var_role_cat_lbls,
                    var_role_series, var_role_series_name, var_role_series_lbls,
                    var_role_charts, var_role_charts_name, var_role_charts_lbls, 
                    sort_opt=mg.SORT_NONE,
                    rotate=%(rotate)s, is_perc=%(is_perc)s)
x_title = var_role_cat_name
y_title = %(ytitle2use)s
chart_output = charting_output.areachart_output(titles, subtitles, 
    x_title, y_title, chart_output_dets, rotate=%(rotate)s, 
    css_fil=u"%(css_fil)s", 
    css_idx=%(css_idx)s, page_break_after=False)""" %
    {u"dbe": dd.dbe, u"is_perc": str(is_perc), u"rotate": rotate, 
     u"ytitle2use": ytitle2use, u"css_fil": esc_css_fil, u"css_idx": css_idx})
    return script

def get_histogram_script(inc_normal, css_fil, css_idx):
    esc_css_fil = lib.escape_pre_write(css_fil)
    dd = mg.DATADETS_OBJ
    script = u"""
histo_dets = charting_output.get_histo_dets(dbe, cur, tbl, tbl_filt, flds,
                                    var_role_bin, var_role_charts, 
                                    var_role_charts_name, var_role_charts_lbls)
chart_output = charting_output.histogram_output(titles, subtitles, 
            var_role_bin_name, histo_dets, inc_normal=%(inc_normal)s, 
            css_fil=u"%(css_fil)s", css_idx=%(css_idx)s, page_break_after=False)
    """ % {u"dbe": dd.dbe, u"inc_normal": inc_normal, u"css_fil": esc_css_fil, 
           u"css_idx": css_idx}
    return script

def get_scatterplot_script(css_fil, css_idx, dot_border):
    esc_css_fil = lib.escape_pre_write(css_fil)
    dd = mg.DATADETS_OBJ
    script = u"""
scatterplot_dets = charting_output.get_scatterplot_dets(dbe, cur, tbl, tbl_filt, 
            flds, var_role_x_axis, var_role_y_axis, 
            var_role_charts, var_role_charts_name, var_role_charts_lbls, 
            unique=True)
chart_output = charting_output.scatterplot_output(titles, subtitles,
            scatterplot_dets, var_role_x_axis, var_role_y_axis, add_to_report, 
            report_name, %(dot_border)s, css_fil=u"%(css_fil)s", 
            css_idx=%(css_idx)s, page_break_after=False)
    """ % {u"dbe": dd.dbe, u"css_fil": esc_css_fil, u"css_idx": css_idx, 
           u"dot_border": dot_border}
    return script

def get_boxplot_script(rotate, css_fil, css_idx):
    esc_css_fil = lib.escape_pre_write(css_fil)
    dd = mg.DATADETS_OBJ
    script = u"""
(xaxis_dets, xmin, xmax, 
 ymin, ymax, max_label_len, 
 max_lbl_lines, chart_dets, 
 any_missing_boxes) = charting_output.get_boxplot_dets(dbe, cur, tbl, tbl_filt, 
                    var_role_desc, var_role_desc_name,
                    var_role_cat, var_role_cat_name, var_role_cat_lbls,
                    var_role_series, var_role_series_name, var_role_series_lbls,
                    rotate=%(rotate)s)
x_title = var_role_cat_name
y_title = var_role_desc_name 
chart_output = charting_output.boxplot_output(titles, subtitles, 
                    any_missing_boxes, x_title, y_title, var_role_series_name, 
                    xaxis_dets, max_label_len, max_lbl_lines, chart_dets, xmin, 
                    xmax, ymin, ymax, rotate=%(rotate)s, css_fil=u"%(css_fil)s", 
                    css_idx=%(css_idx)s, page_break_after=False)
    """ % {u"dbe": dd.dbe, u"css_fil": esc_css_fil, u"rotate": rotate, 
           u"css_idx": css_idx}
    return script
