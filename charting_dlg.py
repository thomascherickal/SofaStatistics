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
        #szr_vars_top_right = wx.BoxSizer(wx.VERTICAL)
        #szr_vars_top_left_top = wx.BoxSizer(wx.HORIZONTAL)
        #szr_vars_top_left_mid = wx.BoxSizer(wx.HORIZONTAL)
        #szr_vars_top_right_top = wx.BoxSizer(wx.HORIZONTAL)
        #szr_vars_top_right_bottom = wx.BoxSizer(wx.HORIZONTAL)
        szr_chart_btns = wx.BoxSizer(wx.HORIZONTAL)
        (self.min_data_type1, 
         self.min_data_type2) = \
                        mg.CHART_TYPE_TO_MIN_DATA_TYPES.get(mg.SIMPLE_BARCHART, 
                                                           (mg.VAR_TYPE_CAT,
                                                            mg.VAR_TYPE_CAT))        
        # var 1
        self.lbl_var1 = wx.StaticText(self.panel_top, -1, 
                                      u"%s:" % mg.CHART_VALUES)
        self.lbl_var1.SetFont(self.LABEL_FONT)
        self.drop_var1 = wx.Choice(self.panel_top, -1, choices=[], 
                                   size=(210,-1))
        self.drop_var1.Bind(wx.EVT_CHOICE, self.on_var1_sel)
        self.drop_var1.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_var1)
        self.drop_var1.SetToolTipString(variables_rc_msg)
        self.sorted_var_names1 = []
        self.setup_var(self.drop_var1, mg.VAR_1_DEFAULT, self.sorted_var_names1,
                       override_min_data_type=self.min_data_type1)
        # var 2
        self.min_data_type2 = mg.VAR_TYPE_CAT
        self.lbl_var2 = wx.StaticText(self.panel_top, -1, u"%s:"
                                      % mg.CHART_CHART_BY)
        self.lbl_var2.SetFont(self.LABEL_FONT)
        self.drop_var2 = wx.Choice(self.panel_top, -1, choices=[], 
                                   size=(210,-1))
        self.drop_var2.Bind(wx.EVT_CHOICE, self.on_var2_sel)
        self.drop_var2.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_var2)
        self.drop_var2.SetToolTipString(variables_rc_msg)
        self.sorted_var_names2 = []
        self.setup_var(self.drop_var2, mg.VAR_2_DEFAULT, self.sorted_var_names2, 
                       var_name=None, inc_drop_select=True,
                       override_min_data_type=self.min_data_type2)
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
                       var_name=None, inc_drop_select=True, 
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
        self.rad_pie_sort_opts = self.get_rad_sort(self.panel_pie_chart)
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
    
    def get_rad_sort(self, panel):
        rad = wx.RadioBox(panel, -1, _("Sort order of bars"), 
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

    def set_avg_dropdowns(self, from_scratch=False):
        # set drop1 to numeric, change label for drop1 to Averaged and 
        #    drop2 to By, add drop3
        unused, varname2, varname3 = self.get_vars()
        self.min_data_type1 = mg.VAR_TYPE_QUANT
        self.setup_var(self.drop_var1, mg.VAR_1_DEFAULT, self.sorted_var_names1,
                       override_min_data_type=self.min_data_type1)
        if from_scratch:
            # var 2
            inc_drop_select = (self.chart_type in 
                               mg.OPTIONAL_ONE_VAR_CHART_TYPES)
            self.setup_var(self.drop_var2, mg.VAR_2_DEFAULT, 
                           self.sorted_var_names2, varname2, inc_drop_select, 
                           override_min_data_type=self.min_data_type2)
            self.drop_var2.Enable(True)
            self.lbl_var2.Enable(True)
        self.lbl_var1.SetLabel(u"%s:" % mg.CHART_AVERAGED)
        self.lbl_var2.SetLabel(u"%s:" % mg.CHART_BY)
        if self.chart_type in mg.NO_CHART_BY:
            self.lbl_var3.SetLabel(u"%s:" % mg.CHART_BY)
        else:
            self.lbl_var3.SetLabel(u"%s:" % mg.CHART_CHART_BY)
        self.setup_var(self.drop_var3, mg.VAR_3_DEFAULT, 
                       self.sorted_var_names3, varname3, 
                       inc_drop_select=True, 
                       override_min_data_type=mg.VAR_TYPE_CAT)
        self.drop_var3.Show()
        self.lbl_var3.Show()
        self.panel_top.Layout()

    def unset_avg_dropdowns(self):
        # set drop1 to normal for simple bar, change label for drop2, hide
        # drop3
        (self.min_data_type1, 
         self.min_data_type2) = \
                        mg.CHART_TYPE_TO_MIN_DATA_TYPES.get(self.chart_type, 
                                                            (mg.VAR_TYPE_CAT,
                                                             mg.VAR_TYPE_CAT))
        self.setup_var(self.drop_var1, mg.VAR_1_DEFAULT, self.sorted_var_names1,
                       override_min_data_type=self.min_data_type1)
        (lbl1, lbl2,
         unused) = mg.CHART_TYPE_TO_LBLS.get(self.chart_type, (mg.CHART_VALUES, 
                                                mg.CHART_BY, mg.CHART_CHART_BY))
        self.lbl_var1.SetLabel(u"%s:" % lbl1)
        self.lbl_var2.SetLabel(u"%s:" % lbl2)
        self.drop_var3.Hide()
        self.lbl_var3.Hide()
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
        if SHOW_AVG:
            self.set_avg_dropdowns()
            rad.Enable(False)
        else:
            self.unset_avg_dropdowns()
            rad.Enable(True)
            
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
        
    def btn_chart(self, event, btn, btn_bmp, btn_sel_bmp, panel,
                  override_min_data_type1=None):
        """
        min_data_type is an indep2var thing which we ignore. We need more 
            fine-grained control -- e.g. numerical only for some drop downs and 
            categorical upwards for others.
        override_min_data_type1 -- 1 must be overridden if doing averages 
            (must be numeric). No need to override 2 and 3 - always 
            categorical upwards.
        """
        btn.SetFocus()
        btn.SetDefault()
        self.btn_to_rollback.SetBitmapLabel(self.bmp_to_rollback_to)
        self.btn_to_rollback = btn
        self.bmp_to_rollback_to = btn_bmp
        btn.SetBitmapLabel(btn_sel_bmp)
        event.Skip()
        if self.panel_displayed == panel:
            return # just reclicking on same one
        if (self.chart_type in mg.HAS_AVG_OPTION) and SHOW_AVG:
            self.set_avg_dropdowns(from_scratch=True)
        else:
            (lbl1, lbl2,
             lbl3) = mg.CHART_TYPE_TO_LBLS.get(self.chart_type, 
                              (mg.CHART_VALUES, mg.CHART_BY, mg.CHART_CHART_BY))
            self.lbl_var1.SetLabel(u"%s:" % lbl1)
            self.lbl_var2.SetLabel(u"%s:" % lbl2)
            self.lbl_var3.SetLabel(u"%s:" % lbl3)
            self.panel_top.Layout()
            (self.min_data_type1, 
             self.min_data_type2) = \
                        mg.CHART_TYPE_TO_MIN_DATA_TYPES.get(self.chart_type, 
                                                           (mg.VAR_TYPE_CAT,
                                                            mg.VAR_TYPE_CAT))
            varname1, varname2, varname3 = self.get_vars()
            # var 1
            if override_min_data_type1:
                self.min_data_type1 = override_min_data_type1
            self.setup_var(self.drop_var1, mg.VAR_1_DEFAULT, 
                           self.sorted_var_names1, varname1,
                           override_min_data_type=self.min_data_type1)
            # var 2
            inc_drop_select = (self.chart_type in 
                               mg.OPTIONAL_ONE_VAR_CHART_TYPES)
            self.setup_var(self.drop_var2, mg.VAR_2_DEFAULT, 
                           self.sorted_var_names2, varname2, inc_drop_select, 
                           override_min_data_type=self.min_data_type2)
            self.drop_var2.Enable(True)
            self.lbl_var2.Enable(True)
            # var 3 - always categorical upwards
            if self.chart_type in mg.THREE_VAR_CHART_TYPES:
                self.setup_var(self.drop_var3, mg.VAR_3_DEFAULT, 
                               self.sorted_var_names3, varname3, 
                               inc_drop_select=True, 
                               override_min_data_type=mg.VAR_TYPE_CAT)
                self.drop_var3.Show()
                self.lbl_var3.Show()
                self.panel_top.Layout()
            else:
                self.drop_var3.Hide()
                self.lbl_var3.Hide()
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
                       varname1, override_min_data_type=self.min_data_type1)
        inc_drop_select = (self.chart_type in mg.OPTIONAL_ONE_VAR_CHART_TYPES)
        self.setup_var(self.drop_var2, mg.VAR_2_DEFAULT, self.sorted_var_names2,
                       varname2, inc_drop_select, 
                       override_min_data_type=self.min_data_type2)
        self.setup_var(self.drop_var3, mg.VAR_3_DEFAULT, 
                       self.sorted_var_names3, varname3, 
                       inc_drop_select=True, 
                       override_min_data_type=mg.VAR_TYPE_CAT)
        self.update_defaults()

    def on_database_sel(self, event):
        """
        Reset dbe, database, cursor, tables, table, tables dropdown, 
            fields, has_unique, and idxs after a database selection.
        """
        config_output.ConfigUI.on_database_sel(self, event)
        # now update var dropdowns
        config_output.update_var_dets(dlg=self)
        self.setup_var(self.drop_var1, mg.VAR_1_DEFAULT, self.sorted_var_names1,
                       override_min_data_type=self.min_data_type1)
        inc_drop_select = (self.chart_type in mg.OPTIONAL_ONE_VAR_CHART_TYPES)
        self.setup_var(self.drop_var2, mg.VAR_2_DEFAULT, self.sorted_var_names2, 
                       var_name=None, inc_drop_select=inc_drop_select,
                       override_min_data_type=self.min_data_type2)
        self.setup_var(self.drop_var3, mg.VAR_3_DEFAULT, 
                       self.sorted_var_names3, var_name=None, 
                       inc_drop_select=True, 
                       override_min_data_type=mg.VAR_TYPE_CAT)
                
    def on_table_sel(self, event):
        "Reset key data details after table selection."       
        config_output.ConfigUI.on_table_sel(self, event)
        # now update var dropdowns
        config_output.update_var_dets(dlg=self)
        self.setup_var(self.drop_var1, mg.VAR_1_DEFAULT, self.sorted_var_names1,
                       override_min_data_type=self.min_data_type1)
        inc_drop_select = (self.chart_type in mg.OPTIONAL_ONE_VAR_CHART_TYPES)
        self.setup_var(self.drop_var2, mg.VAR_2_DEFAULT, self.sorted_var_names2, 
                       var_name=None, inc_drop_select=inc_drop_select,
                       override_min_data_type=self.min_data_type2)
        self.setup_var(self.drop_var3, mg.VAR_3_DEFAULT, 
                       self.sorted_var_names3, var_name=None, 
                       inc_drop_select=True, 
                       override_min_data_type=mg.VAR_TYPE_CAT)
       
    def on_btn_config(self, event):
        """
        Want to retain already selected item - even though label and even 
            position may have changed.
        """
        varname1, varname2, varname3 = self.get_vars()
        config_output.ConfigUI.on_btn_config(self, event)
        self.setup_var(self.drop_var1, mg.VAR_1_DEFAULT, self.sorted_var_names1, 
                       varname1, override_min_data_type=self.min_data_type1)
        inc_drop_select = (self.chart_type in mg.OPTIONAL_ONE_VAR_CHART_TYPES)
        self.setup_var(self.drop_var2, mg.VAR_2_DEFAULT, self.sorted_var_names2, 
                       varname2, inc_drop_select=inc_drop_select,
                       override_min_data_type=self.min_data_type2)
        self.setup_var(self.drop_var3, mg.VAR_3_DEFAULT, 
                       self.sorted_var_names3, varname3, 
                       inc_drop_select=True, 
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
        except Exception:
            my_exceptions.DoNothingException()
   
    def update_phrase(self):
        pass

    def test_config_ok(self):
        """
        Are the appropriate selections made to enable an analysis to be run?
        """
        has3vars = (self.chart_type in mg.THREE_VAR_CHART_TYPES
                    or (self.chart_type in mg.HAS_AVG_OPTION and SHOW_AVG))
        if has3vars:        
            setof3 = set([self.drop_var1.GetStringSelection(),
                        self.drop_var2.GetStringSelection(),
                        self.drop_var3.GetStringSelection()])
            if len(setof3) < 3:
                wx.MessageBox(_(u"The variables for %(var1)s, %(var2)s and "
                                u"%(var3)s must all be different") % 
                              {u"var1": self.lbl_var1.GetLabel().rstrip(u":"), 
                               u"var2": self.lbl_var2.GetLabel().rstrip(u":"),
                               u"var3": self.lbl_var3.GetLabel().rstrip(u":")})
                return False
            if self.drop_var2.GetStringSelection() == mg.DROP_SELECT:
                wx.MessageBox("Please make a selection for the second variable")
                return False
            if (self.chart_type == mg.CLUSTERED_BARCHART 
                    and self.drop_var3.GetStringSelection() == mg.DROP_SELECT):
                wx.MessageBox("Please make a selection for the third variable")
                return False
        else:
            setof2 = set([self.drop_var1.GetStringSelection(),
                        self.drop_var2.GetStringSelection()])
            if len(setof2) < 2:
                wx.MessageBox(_(u"Variables %(var1)s and %(var2)s must be "
                                u"different") % 
                              {u"var1": self.lbl_var1.GetLabel().rstrip(u":"), 
                               u"var2": self.lbl_var2.GetLabel().rstrip(u":")})
                return False
            # 2 drop downs showing - second must be completed if SHOW_AVG
            if (self.chart_type in mg.HAS_AVG_OPTION and SHOW_AVG 
                    and self.drop_var2.GetStringSelection() == mg.DROP_SELECT):
                wx.MessageBox("Please make a selection for the second variable")
                return False
        return True

    def get_script(self, css_idx, css_fil, add_to_report, report_name):
        """
        Build script from inputs
        fld_measure -- the main thing being graphed
        mg.FLD_GROUP_BY -- for grouping by (e.g. separate lines or bar series)
        mg.FLD_CHART_BY -- for charting by (separate charts)
        Mission - to set up the variables needed by the specific script for the 
            chart type. This includes the inputs to get_chart_dets() i.e. 
            fld_measure, etc (usually measure. Scatterplot is fld_x_axis).
            fld_gp_by etc, (If var 2 is By, set to this and if ).
            fld_chart_by etc,
        """
        dd = mg.DATADETS_OBJ
        is_perc = not(CUR_DATA_OPT == mg.SHOW_FREQ
                      or (self.chart_type in mg.HAS_AVG_OPTION and SHOW_AVG))
        rotate = u"True" if ROTATE else u"False"
        script_lst = []
        titles, subtitles = self.get_titles()
        script_lst.append(u"titles=%s" % unicode(titles))
        script_lst.append(u"subtitles=%s" % unicode(subtitles))
        script_lst.append(lib.get_tbl_filt_clause(dd.dbe, dd.db, dd.tbl))
        varname1, varname2, varname3 = self.get_vars()
        # dropdown (var) 1 - always the measure field unless a scatterplot
        var1lbl = u"fld_x_axis" if self.chart_type == mg.SCATTERPLOT \
                                else mg.FLD_MEASURE
        script_lst.append(u"%s = u\"%s\"" % (var1lbl, varname1))
        script_lst.append(u"%s_name=u\"%s\"" % (var1lbl,
                          lib.get_item_label(self.var_labels, varname1)))
        script_lst.append(u"%s_lbls = %s" % (var1lbl,
                          self.val_dics.get(varname1, {})))
        # dropdown (var) 2 - depends on chart type and whether freq or average
        if self.chart_type == mg.SCATTERPLOT:
            var2lbl = u"fld_y_axis"
        elif (self.chart_type in mg.HAS_AVG_OPTION) and SHOW_AVG:
            var2lbl = mg.FLD_GROUP_BY # need something to group the measure by
        elif self.chart_type in mg.NO_CHART_BY: # e.g. clustered bar chart
            var2lbl = mg.FLD_GROUP_BY
            # Chart by will take care of itself when we look at var 3 so no 
            # need to set here.
        else:
            var2lbl = mg.FLD_CHART_BY
            # Set group by's to None because charts will never have a group by 
            # if the second var is chart by. Will not be handled later.
            script_lst.append("%s=None" % mg.FLD_GROUP_BY)
            script_lst.append("%s=None" % mg.FLD_GROUP_BY_NAME)
            script_lst.append("%s=None" % mg.FLD_GROUP_BY_LBLS)
        # OK, we know what the 2nd drop represents - what was entered?
        if varname2 == mg.DROP_SELECT:
            script_lst.append(u"%s = None" % var2lbl)
            script_lst.append(u"%s_name = None" % var2lbl)
            script_lst.append(u"%s_lbls = None" % var2lbl)
        else: # Labels not needed for scatterplot but no harm and keeps 
            # consistent.
            script_lst.append(u"%s = u\"%s\"" % (var2lbl, varname2))
            script_lst.append(u"%s_name=u\"%s\"" % (var2lbl,
                                 lib.get_item_label(self.var_labels, varname2)))
            script_lst.append(u"%s_lbls = %s" % (var2lbl, 
                                               self.val_dics.get(varname2, {})))
        # dropdown (var) 3 - always chart by or nothing
        has3vars = (self.chart_type in mg.THREE_VAR_CHART_TYPES
                    or (self.chart_type in mg.HAS_AVG_OPTION and SHOW_AVG))
        if has3vars and varname3 != mg.DROP_SELECT:
            script_lst.append(u"%s = u\"%s\"" % (mg.FLD_CHART_BY, varname3))
            script_lst.append(u"%s=u\"%s\"" % (mg.FLD_CHART_BY_NAME,
                                lib.get_item_label(self.var_labels, varname3)))
            script_lst.append(u"%s = %s" % (mg.FLD_CHART_BY_LBLS,
                                        self.val_dics.get(varname3, {})))
        elif var2lbl != mg.FLD_CHART_BY:
            script_lst.append("%s=None" % mg.FLD_CHART_BY)
            script_lst.append("%s=None" % mg.FLD_CHART_BY_NAME)
            script_lst.append("%s=None" % mg.FLD_CHART_BY_LBLS)
        # other variables to set up
        script_lst.append(u"add_to_report = %s" % ("True" if add_to_report
                                                          else "False"))
        script_lst.append(u"report_name = u\"%s\"" %
                          lib.escape_pre_write(report_name))
        if (self.chart_type in mg.HAS_AVG_OPTION):
            if SHOW_AVG:
                script_lst.append(u"measure = mg.CHART_AVGS")
            else:
                script_lst.append(u"measure = mg.CHART_FREQS")
        if self.chart_type == mg.SIMPLE_BARCHART:
            script_lst.append(get_simple_barchart_script(is_perc, rotate,
                                                         css_fil, css_idx))
        elif self.chart_type == mg.CLUSTERED_BARCHART:
            script_lst.append(get_clustered_barchart_script(is_perc, rotate,
                                                            css_fil, css_idx))
        elif self.chart_type == mg.PIE_CHART:
            script_lst.append(get_pie_chart_script(css_fil, css_idx))
        elif self.chart_type == mg.LINE_CHART:
            inc_trend = u"True" if self.chk_line_trend.IsChecked() \
                                    and self.chk_line_trend.Enabled \
                                else u"False"
            inc_smooth = u"True" if self.chk_line_smooth.IsChecked() \
                                    and self.chk_line_smooth.Enabled \
                                else u"False"
            script_lst.append(get_line_chart_script(is_perc, rotate, inc_trend, 
                                        inc_smooth, css_fil, css_idx, 
                                        self.chart_type, varname2, varname3))
        elif self.chart_type == mg.AREA_CHART:
            script_lst.append(get_area_chart_script(is_perc, rotate, css_fil, 
                                                    css_idx))
        elif self.chart_type == mg.HISTOGRAM:
            inc_normal = u"True" if self.chk_show_normal.IsChecked() \
                                 else u"False"
            script_lst.append(get_histogram_script(inc_normal, css_fil, 
                                                   css_idx))
        elif self.chart_type == mg.SCATTERPLOT:
            script_lst.append(get_scatterplot_script(css_fil, css_idx, 
                                       dot_border=self.chk_borders.IsChecked()))
        elif self.chart_type == mg.BOXPLOT:
            script_lst.append(get_boxplot_script(rotate, css_fil, css_idx))
        script_lst.append(u"fil.write(chart_output)")
        return u"\n".join(script_lst)

def get_simple_barchart_script(is_perc, rotate, css_fil, css_idx):
    ytitle2use = u"mg.Y_AXIS_PERC_LBL" if is_perc else u"mg.Y_AXIS_FREQ_LBL"
    script = u"""
chart_dets = charting_output.get_chart_dets(mg.SIMPLE_BARCHART, 
                            dbe, cur, tbl, tbl_filt, 
                            fld_measure, fld_measure_name, fld_measure_lbls, 
                            fld_gp_by, fld_gp_by_name, fld_gp_by_lbls,
                            fld_chart_by, fld_chart_by_name, fld_chart_by_lbls, 
                            sort_opt="%(sort_opt)s", measure=measure, 
                            rotate=%(rotate)s, is_perc=%(is_perc)s)
x_title = u"" # uses series label instead
y_title = (%(ytitle2use)s if measure == mg.CHART_FREQS
                              else u"Mean %%s" %% fld_measure_name) 
chart_output = charting_output.simple_barchart_output(titles, subtitles,
    x_title, y_title, chart_dets, rotate=%(rotate)s, 
    css_fil=u"%(css_fil)s", css_idx=%(css_idx)s, 
    page_break_after=False)
    """ % {u"sort_opt": CUR_SORT_OPT, u"is_perc": str(is_perc), 
           u"ytitle2use": ytitle2use, u"rotate": rotate,
           u"css_fil": lib.escape_pre_write(css_fil), u"css_idx": css_idx}
    return script

def get_clustered_barchart_script(is_perc, rotate, css_fil, css_idx):
    ytitle2use = u"mg.Y_AXIS_PERC_LBL" if is_perc else u"mg.Y_AXIS_FREQ_LBL"
    script = u"""
chart_dets = charting_output.get_chart_dets(mg.CLUSTERED_BARCHART, 
                            dbe, cur, tbl, tbl_filt, 
                            fld_measure, fld_measure_name, fld_measure_lbls, 
                            fld_gp_by, fld_gp_by_name, fld_gp_by_lbls,
                            fld_chart_by, fld_chart_by_name, fld_chart_by_lbls, 
                            sort_opt="%(sort_opt)s", measure=measure,
                            rotate=%(rotate)s, is_perc=%(is_perc)s)
x_title = fld_measure_name if measure == mg.CHART_FREQS else fld_gp_by_name
y_title = (%(ytitle2use)s if measure == mg.CHART_FREQS
                              else u"Mean %%s" %% fld_measure_name) 
chart_output = charting_output.clustered_barchart_output(titles, subtitles,
    x_title, y_title, chart_dets, rotate=%(rotate)s, 
    css_fil=u"%(css_fil)s", 
    css_idx=%(css_idx)s, page_break_after=False)    
    """ % {u"sort_opt": mg.SORT_NONE, u"is_perc": str(is_perc), 
           u"ytitle2use": ytitle2use, u"rotate": rotate, 
           u"css_fil": lib.escape_pre_write(css_fil), u"css_idx": css_idx}
    return script

def get_pie_chart_script(css_fil, css_idx):
    script = u"""
chart_dets = charting_output.get_chart_dets(mg.PIE_CHART, 
                            dbe, cur, tbl, tbl_filt, 
                            fld_measure, fld_measure_name, fld_measure_lbls, 
                            fld_gp_by, fld_gp_by_name, fld_gp_by_lbls,
                            fld_chart_by, fld_chart_by_name, fld_chart_by_lbls, 
                            sort_opt="%(sort_opt)s", measure=mg.CHART_FREQS)
chart_output = charting_output.piechart_output(titles, subtitles,
            chart_dets, css_fil=u"%(css_fil)s", css_idx=%(css_idx)s,
            page_break_after=False)
    """ % {u"sort_opt": CUR_SORT_OPT, u"css_fil": lib.escape_pre_write(css_fil), 
           u"css_idx": css_idx}
    return script

def get_line_chart_script(is_perc, rotate, inc_trend, inc_smooth, css_fil, 
                          css_idx, chart_type, varname2, varname3):
    ytitle2use = u"mg.Y_AXIS_PERC_LBL" if is_perc else u"mg.Y_AXIS_FREQ_LBL"
    single_line = ((SHOW_AVG and varname3 == mg.DROP_SELECT) 
                   or (not SHOW_AVG and varname2 == mg.DROP_SELECT))
    if single_line:
        xy_titles = (u"""
x_title = u"" # uses series label instead
y_title = (%(ytitle2use)s if measure == mg.CHART_FREQS
                              else u"Mean %%s" %% fld_measure_name)""" % 
                              {u"ytitle2use": ytitle2use})
    else:
        xy_titles = (u"""
x_title = fld_measure_name if measure == mg.CHART_FREQS else fld_gp_by_name
y_title = (%(ytitle2use)s if measure == mg.CHART_FREQS
                              else u"Mean %%s" %% fld_measure_name)""" % 
                              {u"ytitle2use": ytitle2use})
    script = (u"""
chart_dets = charting_output.get_chart_dets(mg.LINE_CHART, 
                            dbe, cur, tbl, tbl_filt, 
                            fld_measure, fld_measure_name, fld_measure_lbls, 
                            fld_gp_by, fld_gp_by_name, fld_gp_by_lbls,
                            fld_chart_by, fld_chart_by_name, fld_chart_by_lbls, 
                            sort_opt=mg.SORT_NONE, measure=measure,
                            rotate=%(rotate)s, is_perc=%(is_perc)s)
%(xy_titles)s
chart_output = charting_output.linechart_output(titles, subtitles, 
    x_title, y_title, chart_dets, rotate=%(rotate)s, inc_trend=%(inc_trend)s, 
    inc_smooth=%(inc_smooth)s, 
    css_fil=u"%(css_fil)s", css_idx=%(css_idx)s, 
    page_break_after=False)""" %
        {u"is_perc": str(is_perc), u"rotate": rotate, u"xy_titles": xy_titles,
         u"inc_trend": inc_trend, u"inc_smooth": inc_smooth, 
         u"css_fil": lib.escape_pre_write(css_fil), u"css_idx": css_idx})
    return script

def get_area_chart_script(is_perc, rotate, css_fil, css_idx):
    ytitle2use = u"mg.Y_AXIS_PERC_LBL" if is_perc else u"mg.Y_AXIS_FREQ_LBL"
    dd = mg.DATADETS_OBJ
    script = (u"""
chart_dets = charting_output.get_chart_dets(mg.AREA_CHART, 
                            dbe, cur, tbl, tbl_filt, 
                            fld_measure, fld_measure_name, fld_measure_lbls, 
                            fld_gp_by, fld_gp_by_name, fld_gp_by_lbls,
                            fld_chart_by, fld_chart_by_name, fld_chart_by_lbls, 
                            sort_opt=mg.SORT_NONE, measure=measure,
                            rotate=%(rotate)s, is_perc=%(is_perc)s)
x_title = u"" # uses series label instead
y_title = (%(ytitle2use)s if measure == mg.CHART_FREQS
                              else u"Mean %%s" %% fld_measure_name) 
chart_output = charting_output.areachart_output(titles, subtitles, 
    x_title, y_title, chart_dets, rotate=%(rotate)s, 
    css_fil=u"%(css_fil)s", 
    css_idx=%(css_idx)s, page_break_after=False)""" %
    {u"dbe": dd.dbe, u"is_perc": str(is_perc), 
     u"rotate": rotate, u"ytitle2use": ytitle2use, 
     u"css_fil": lib.escape_pre_write(css_fil), u"css_idx": css_idx})
    return script

def get_histogram_script(inc_normal, css_fil, css_idx):
    dd = mg.DATADETS_OBJ
    script = u"""
histo_dets = charting_output.get_histo_dets(dbe, cur, tbl, tbl_filt, flds,
                                           fld_measure, fld_chart_by, 
                                           fld_chart_by_name, fld_chart_by_lbls)
chart_output = charting_output.histogram_output(titles, subtitles, 
            fld_measure_name, histo_dets, inc_normal=%(inc_normal)s, 
            css_fil=u"%(css_fil)s", css_idx=%(css_idx)s, page_break_after=False)
    """ % {u"dbe": dd.dbe, u"inc_normal": inc_normal, 
           u"css_fil": lib.escape_pre_write(css_fil), u"css_idx": css_idx}
    return script

def get_scatterplot_script(css_fil, css_idx, dot_border):
    dd = mg.DATADETS_OBJ
    script = u"""
scatterplot_dets = charting_output.get_scatterplot_dets(dbe, cur, tbl, tbl_filt, 
            flds, fld_x_axis, fld_y_axis, 
            fld_chart_by, fld_chart_by_name, fld_chart_by_lbls, 
            unique=True)
chart_output = charting_output.scatterplot_output(titles, subtitles,
            scatterplot_dets, fld_x_axis_name, fld_y_axis_name, add_to_report, 
            report_name, %(dot_border)s, css_fil=u"%(css_fil)s", 
            css_idx=%(css_idx)s, page_break_after=False)
    """ % {u"dbe": dd.dbe, u"css_fil": lib.escape_pre_write(css_fil), 
           u"css_idx": css_idx, u"dot_border": dot_border}
    return script

def get_boxplot_script(rotate, css_fil, css_idx):
    dd = mg.DATADETS_OBJ
    script = u"""
(xaxis_dets, xmin, xmax, 
 ymin, ymax, max_label_len, 
 chart_dets, 
 any_missing_boxes) = charting_output.get_boxplot_dets(dbe, cur, tbl, tbl_filt, 
                          fld_measure, fld_measure_name,
                          fld_gp_by, fld_gp_by_name, fld_gp_by_lbls,
                          fld_chart_by, fld_chart_by_name, fld_chart_by_lbls, 
                          rotate=%(rotate)s)
x_title = fld_gp_by_name if fld_chart_by else u""
y_title = fld_measure_name 
chart_output = charting_output.boxplot_output(titles, subtitles, 
            any_missing_boxes, x_title, y_title, xaxis_dets, max_label_len, 
            chart_dets, xmin, xmax, ymin, ymax, rotate=%(rotate)s, 
            css_fil=u"%(css_fil)s", css_idx=%(css_idx)s, page_break_after=False)
    """ % {u"dbe": dd.dbe, u"css_fil": lib.escape_pre_write(css_fil), 
           u"rotate": rotate, u"css_idx": css_idx}
    return script
