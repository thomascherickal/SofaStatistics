from functools import partial
import os
import wx  #@UnusedImport
import wx.html2

from sofastats import my_globals as mg
from sofastats import lib
from sofastats import config_output
from sofastats import config_ui
from sofastats import getdata
from sofastats import output
from sofastats import projects
from sofastats.stats import indep2var

CUR_SORT_OPT_LBL = mg.SORT_VALUE_LBL
CUR_DATA_OPT_LBL = mg.SHOW_FREQ_LBL
ROTATE = False
SHOW_N = False
MAJOR_TICKS = False
HIDE_MARKERS = False
BARS_SORTED_LBL = 'bars'
CLUSTERS_SORTED_LBL = 'clusters'
SLICES_SORTED_LBL = 'slices'
GROUPS_SORTED_LBL = 'groups'

DROPDOWN_LABEL_WHEN_INACTIVE = ' '

"""
If sorting of x-axis not explicit, will be sort_opt=mg.SORT_VALUE_LBL and will
thus be sorted by values not labels and order of values determined by GROUP BY
in database engine used. See specifics in, for example, get_line_chart_script().

Value dropdowns have to be built fresh each time the data source changes because
in Linux the process of changing the values list dynamically is far too slow
when a non-system font is chosen. Much, much quicker to build a fresh one each
time with the new list as the initial value.
"""


class Btns:

    @staticmethod
    def _setup_bar_chart_btns(self, szr_chart_btns, btn_gap):
        self.bmp_btn_bar_chart = wx.Image(os.path.join(mg.SCRIPT_PATH, 
            'images', 'bar_chart.xpm'), wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.bmp_btn_bar_chart_sel = wx.Image(os.path.join(mg.SCRIPT_PATH,
            'images', 'bar_chart_sel.xpm'),
            wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_bar_chart = wx.BitmapButton(self.panel_mid, -1,
            self.bmp_btn_bar_chart_sel, style=wx.NO_BORDER)
        self.btn_bar_chart.Bind(
            wx.EVT_BUTTON, partial(Btns.on_btn_bar_chart, self))
        self.btn_bar_chart.SetToolTip(_('Make Bar Chart'))
        self.btn_bar_chart.SetDefault()
        self.btn_bar_chart.SetFocus()
        szr_chart_btns.Add(self.btn_bar_chart, 0, wx.RIGHT, btn_gap)

    @staticmethod
    def _setup_clust_bar_chart_btns(self, szr_chart_btns, btn_gap):
        self.bmp_btn_clust_bar = wx.Image(
            os.path.join(mg.SCRIPT_PATH, 'images', 'clustered_bar_chart.xpm'),
            wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.bmp_btn_clust_bar_sel = wx.Image(os.path.join(
            mg.SCRIPT_PATH, 'images', 'clustered_bar_chart_sel.xpm'),
            wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_clust_bar = wx.BitmapButton(
            self.panel_mid, -1, self.bmp_btn_clust_bar, style=wx.NO_BORDER)
        self.btn_clust_bar.Bind(wx.EVT_BUTTON,
            partial(Btns.on_btn_clustered_bar_chart, self))
        self.btn_clust_bar.SetToolTip(_('Make Clustered Bar Chart'))
        szr_chart_btns.Add(self.btn_clust_bar, 0, wx.RIGHT, btn_gap)

    @staticmethod
    def _setup_pie_chart_btns(self, szr_chart_btns, btn_gap):
        self.bmp_btn_pie_chart = wx.Image(os.path.join(mg.SCRIPT_PATH,
            'images', 'pie_chart.xpm'), wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.bmp_btn_pie_chart_sel = wx.Image(
            os.path.join(mg.SCRIPT_PATH, 'images', 'pie_chart_sel.xpm'),
            wx.BITMAP_TYPE_XPM).ConvertToBitmap() 
        self.btn_pie_chart = wx.BitmapButton(
            self.panel_mid, -1, self.bmp_btn_pie_chart, style=wx.NO_BORDER)
        self.btn_pie_chart.Bind(
            wx.EVT_BUTTON, partial(Btns.on_btn_pie_chart, self))
        self.btn_pie_chart.SetToolTip(_('Make Pie Chart'))
        szr_chart_btns.Add(self.btn_pie_chart, 0, wx.RIGHT, btn_gap)

    @staticmethod
    def _setup_line_chart_btns(self, szr_chart_btns, btn_gap):
        self.bmp_btn_line_chart = wx.Image(os.path.join(mg.SCRIPT_PATH,
            'images', 'line_chart.xpm'), wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.bmp_btn_line_chart_sel = wx.Image(
            os.path.join(mg.SCRIPT_PATH, 'images', 'line_chart_sel.xpm'),
            wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_line_chart = wx.BitmapButton(
            self.panel_mid, -1, self.bmp_btn_line_chart, style=wx.NO_BORDER)
        self.btn_line_chart.Bind(
            wx.EVT_BUTTON, partial(Btns.on_btn_line_chart, self))
        self.btn_line_chart.SetToolTip(_('Make Line Chart'))
        szr_chart_btns.Add(self.btn_line_chart, 0, wx.RIGHT, btn_gap)

    @staticmethod
    def _setup_area_chart_btns(self, szr_chart_btns, btn_gap):
        self.bmp_btn_area_chart = wx.Image(os.path.join(mg.SCRIPT_PATH,
            'images', 'area_chart.xpm'), wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.bmp_btn_area_chart_sel = wx.Image(os.path.join(
            mg.SCRIPT_PATH, 'images', 'area_chart_sel.xpm'),
            wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_area_chart = wx.BitmapButton(
            self.panel_mid, -1, self.bmp_btn_area_chart, style=wx.NO_BORDER)
        self.btn_area_chart.Bind(
            wx.EVT_BUTTON, partial(Btns.on_btn_area_chart, self))
        self.btn_area_chart.SetToolTip(_('Make Area Chart'))
        szr_chart_btns.Add(self.btn_area_chart, 0, wx.RIGHT, btn_gap)

    @staticmethod
    def _setup_histo_chart_btns(self, szr_chart_btns, btn_gap):
        self.bmp_btn_histogram = wx.Image(os.path.join(mg.SCRIPT_PATH, 
            'images', 'histogram.xpm'), wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.bmp_btn_histogram_sel = wx.Image(
            os.path.join(mg.SCRIPT_PATH, 'images', 'histogram_sel.xpm'),
            wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_histogram = wx.BitmapButton(
            self.panel_mid, -1, self.bmp_btn_histogram, style=wx.NO_BORDER)
        self.btn_histogram.Bind(
            wx.EVT_BUTTON, partial(Btns.on_btn_histogram, self))
        self.btn_histogram.SetToolTip(_('Make Histogram'))
        szr_chart_btns.Add(self.btn_histogram, 0, wx.RIGHT, btn_gap)

    @staticmethod
    def _setup_scatter_chart_btns(self, szr_chart_btns, btn_gap):
        self.bmp_btn_scatterplot = wx.Image(os.path.join(mg.SCRIPT_PATH, 
            'images', 'scatterplot.xpm'),
            wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.bmp_btn_scatterplot_sel = wx.Image(os.path.join(mg.SCRIPT_PATH, 
            'images', 'scatterplot_sel.xpm'),
            wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_scatterplot = wx.BitmapButton(self.panel_mid, -1,
            self.bmp_btn_scatterplot, style=wx.NO_BORDER)
        self.btn_scatterplot.Bind(
            wx.EVT_BUTTON, partial(Btns.on_btn_scatterplot, self))
        self.btn_scatterplot.SetToolTip(_('Make Scatterplot'))
        szr_chart_btns.Add(self.btn_scatterplot, 0, wx.RIGHT, btn_gap)

    @staticmethod
    def _setup_box_chart_btns(self, szr_chart_btns):
        self.bmp_btn_boxplot = wx.Image(os.path.join(mg.SCRIPT_PATH,
            'images', 'boxplot.xpm'), wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.bmp_btn_boxplot_sel = wx.Image(os.path.join(mg.SCRIPT_PATH,
            'images', 'boxplot_sel.xpm'),
            wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.btn_boxplot = wx.BitmapButton(self.panel_mid, -1,
            self.bmp_btn_boxplot, style=wx.NO_BORDER)
        self.btn_boxplot.Bind(
            wx.EVT_BUTTON, partial(Btns.on_btn_boxplot, self))
        self.btn_boxplot.SetToolTip(_('Make Box and Whisker Plot'))
        szr_chart_btns.Add(self.btn_boxplot)

    @staticmethod
    def setup_chart_btns(self, szr_chart_btns):
        btn_gap = 10 if mg.PLATFORM == mg.WINDOWS else 2
        Btns._setup_bar_chart_btns(self, szr_chart_btns, btn_gap)
        Btns._setup_clust_bar_chart_btns(self, szr_chart_btns, btn_gap)
        Btns._setup_pie_chart_btns(self, szr_chart_btns, btn_gap)
        Btns._setup_line_chart_btns(self, szr_chart_btns, btn_gap)
        Btns._setup_area_chart_btns(self, szr_chart_btns, btn_gap)
        Btns._setup_histo_chart_btns(self, szr_chart_btns, btn_gap)
        Btns._setup_scatter_chart_btns(self, szr_chart_btns, btn_gap)
        Btns._setup_box_chart_btns(self, szr_chart_btns)
        if mg.PLATFORM == mg.LINUX:
            hand = wx.Cursor(wx.CURSOR_HAND)
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

    @staticmethod
    def btn_chart(self, event, btn, btn_bmp, btn_sel_bmp, panel):
        btn.SetFocus()
        btn.SetDefault()
        self.btn_to_rollback.SetBitmapLabel(self.bmp_to_rollback_to)
        self.btn_to_rollback = btn
        self.bmp_to_rollback_to = btn_bmp
        btn.SetBitmapLabel(btn_sel_bmp)
        event.Skip()
        if self.panel_displayed == panel:
            return  ## just reclicking on same one
        self.panel_displayed.Show(False)
        self.panel_displayed = panel
        panel.Show(True)
        self.panel_mid.Layout()  ## self.Layout() doesn't work in Windows
        Dropdowns.setup_var_dropdowns(self)

    @staticmethod
    def on_btn_bar_chart(self, event):
        self.chart_type = mg.SIMPLE_BARCHART
        btn = self.btn_bar_chart
        btn_bmp = self.bmp_btn_bar_chart
        btn_bmp_sel = self.bmp_btn_bar_chart_sel
        panel = self.panel_bar_chart
        self.drop_bar_val.SetSelection(
            mg.DATA_SHOW_OPT_LBLS.index(CUR_DATA_OPT_LBL))
        self.drop_bar_sort.SetSelection(
            mg.STD_SORT_OPT_LBLS.index(CUR_SORT_OPT_LBL))
        self.chk_simple_bar_rotate.SetValue(ROTATE)
        Btns.btn_chart(self, event, btn, btn_bmp, btn_bmp_sel, panel)

    @staticmethod
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
        except ValueError:  ## doesn't have increasing, or decreasing
            CUR_SORT_OPT_LBL = mg.SORT_VALUE_LBL
            idx_sort = mg.STD_SORT_OPT_LBLS.index(CUR_SORT_OPT_LBL)
        self.drop_clust_val.SetSelection(idx_val)
        self.drop_clust_sort.SetSelection(idx_sort)
        self.chk_clust_bar_rotate.SetValue(ROTATE)
        Btns.btn_chart(self, event, btn, btn_bmp, btn_bmp_sel, panel)

    @staticmethod
    def on_btn_pie_chart(self, event):
        self.chart_type = mg.PIE_CHART
        btn = self.btn_pie_chart
        btn_bmp = self.bmp_btn_pie_chart
        btn_bmp_sel = self.bmp_btn_pie_chart_sel
        panel = self.panel_pie_chart
        self.drop_pie_sort.SetSelection(mg.STD_SORT_OPT_LBLS.index(
            CUR_SORT_OPT_LBL))
        Btns.btn_chart(self, event, btn, btn_bmp, btn_bmp_sel, panel)

    @staticmethod
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
        except ValueError:  ## doesn't have increasing, or decreasing
            CUR_SORT_OPT_LBL = mg.SORT_VALUE_LBL
            idx_sort = mg.STD_SORT_OPT_LBLS.index(CUR_SORT_OPT_LBL)
        self.drop_line_val.SetSelection(idx_val)
        self.drop_line_sort.SetSelection(idx_sort)
        self.chk_line_rotate.SetValue(ROTATE)
        self.chk_line_hide_markers.SetValue(HIDE_MARKERS)
        self.chk_line_major_ticks.SetValue(MAJOR_TICKS)
        Btns.btn_chart(self, event, btn, btn_bmp, btn_bmp_sel, panel)
        self.setup_line_extras()

    @staticmethod
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
        self.chk_area_major_ticks.SetValue(MAJOR_TICKS)
        Btns.btn_chart(self, event, btn, btn_bmp, btn_bmp_sel, panel)

    @staticmethod
    def on_btn_histogram(self, event):
        self.chart_type = mg.HISTOGRAM
        btn = self.btn_histogram
        btn_bmp = self.bmp_btn_histogram
        btn_bmp_sel = self.bmp_btn_histogram_sel
        panel = self.panel_histogram
        Btns.btn_chart(self, event, btn, btn_bmp, btn_bmp_sel, panel)

    @staticmethod
    def on_btn_scatterplot(self, event):
        self.chart_type = mg.SCATTERPLOT
        btn = self.btn_scatterplot
        btn_bmp = self.bmp_btn_scatterplot
        btn_bmp_sel = self.bmp_btn_scatterplot_sel
        panel = self.panel_scatterplot
        Btns.btn_chart(self, event, btn, btn_bmp, btn_bmp_sel, panel)

    @staticmethod
    def on_btn_boxplot(self, event):
        global CUR_SORT_OPT_LBL
        self.chart_type = mg.BOXPLOT
        btn = self.btn_boxplot
        btn_bmp = self.bmp_btn_boxplot
        btn_bmp_sel = self.bmp_btn_boxplot_sel
        panel = self.panel_boxplot
        try:
            idx_sort = mg.SORT_VAL_AND_LABEL_OPT_LBLS.index(CUR_SORT_OPT_LBL)
        except ValueError:  ## doesn't have increasing, or decreasing
            CUR_SORT_OPT_LBL = mg.SORT_VALUE_LBL
            idx_sort = mg.STD_SORT_OPT_LBLS.index(CUR_SORT_OPT_LBL)
        self.drop_box_sort.SetSelection(idx_sort)
        self.chk_boxplot_rotate.SetValue(ROTATE)
        Btns.btn_chart(self, event, btn, btn_bmp, btn_bmp_sel, panel)


class Checkboxes:

    @staticmethod
    def get_chk_rotate(self, panel):
        if mg.PLATFORM == mg.WINDOWS:
            rotate2use = _('Rotate labels?')
        else:
            rotate2use = _('Rotate\nlabels?')
        chk = self.checkbox2use(panel, -1, rotate2use)
        chk.SetFont(mg.GEN_FONT)
        chk.SetValue(ROTATE)
        chk.SetToolTip(_('Rotate x-axis labels?'))
        chk.Bind(wx.EVT_CHECKBOX, partial(Checkboxes.on_chk_rotate, self))
        return chk

    @staticmethod
    def get_chk_major_ticks(self, panel):
        if mg.PLATFORM == mg.WINDOWS:
            major2use = _('Major labels only?')
        else:
            major2use = _('Major\nlabels only?')
        chk = self.checkbox2use(panel, -1, major2use, wrap=15)
        chk.SetFont(mg.GEN_FONT)
        chk.SetValue(MAJOR_TICKS)
        chk.SetToolTip(_('Show major labels only?'))
        chk.Bind(
            wx.EVT_CHECKBOX, partial(Checkboxes.on_chk_major_ticks, self))
        return chk

    @staticmethod
    def get_chk_hide_markers(self, panel):
        if mg.PLATFORM == mg.WINDOWS:
            hide2use = _('Hide markers?')
        else:
            hide2use = _('Hide\nmarkers?')
        chk = self.checkbox2use(panel, -1, hide2use, wrap=15)
        chk.SetFont(mg.GEN_FONT)
        chk.SetValue(HIDE_MARKERS)
        chk.SetToolTip(_('Hide markers?'))
        chk.Bind(wx.EVT_CHECKBOX,
            partial(Checkboxes.on_chk_hide_markers, self))
        return chk

    @staticmethod
    def get_chk_time_series(self, panel, line=True):
        if mg.PLATFORM == mg.WINDOWS:
            dates2use = _('Time series?')
        else:
            dates2use = _('Time\nseries?')
        chk = self.checkbox2use(panel, -1, dates2use)
        chk.SetFont(mg.GEN_FONT)
        chk.SetValue(MAJOR_TICKS)
        chk.SetToolTip(_('Time series i.e. spread over x-axis by date?'))
        event_func = (
            partial(Checkboxes.on_chk_line_time_series, self) if line
            else partial(Checkboxes.on_chk_area_time_series, self))
        chk.Bind(wx.EVT_CHECKBOX, event_func)
        return chk

    @staticmethod
    def get_chk_show_n(self, panel):
        if mg.PLATFORM == mg.WINDOWS:
            show_n2use = _('Show chart N?')
        else:
            show_n2use = _('Show\nchart N?')
        chk_show_n = wx.CheckBox(panel, -1, show_n2use)
        chk_show_n.Bind(
            wx.EVT_CHECKBOX, partial(Checkboxes.on_chk_show_n, self))
        chk_show_n.SetToolTip(_('Show chart N'))
        chk_show_n.SetValue(SHOW_N)
        chk_show_n.SetFont(mg.GEN_FONT)
        return chk_show_n

    @staticmethod
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

    @staticmethod
    def on_chk_major_ticks(self, event):
        global MAJOR_TICKS
        chk = event.GetEventObject()
        MAJOR_TICKS = chk.IsChecked()

    @staticmethod
    def on_chk_hide_markers(self, event):
        global HIDE_MARKERS
        chk = event.GetEventObject()
        HIDE_MARKERS = chk.IsChecked()

    @staticmethod
    def on_chk_show_n(self, event):
        global SHOW_N
        chk = event.GetEventObject()
        SHOW_N = chk.IsChecked()
        self.chk_simple_bar_show_n.SetValue(SHOW_N)
        self.chk_clust_bar_show_n.SetValue(SHOW_N)
        self.chk_pie_show_n.SetValue(SHOW_N)
        self.chk_line_show_n.SetValue(SHOW_N)
        self.chk_area_show_n.SetValue(SHOW_N)
        self.chk_histogram_show_n.SetValue(SHOW_N)
        self.chk_scatterplot_show_n.SetValue(SHOW_N)
        self.chk_boxplot_show_n.SetValue(SHOW_N)

    @staticmethod
    def on_chk_line_time_series(self, event):
        debug = False
        chk = event.GetEventObject()
        self.drop_line_sort.Enable(not chk.IsChecked())
        time_series = chk.IsChecked()
        rotate = self.chk_line_rotate.IsChecked()
        show_major = self._get_show_major(time_series, rotate)
        if debug:
            print(f"time_series: {chk.IsChecked()}; "
                f"rotate: {self.chk_line_rotate.IsChecked()}; "
                f"show_major: {show_major}")
        self.chk_line_major_ticks.Enable(show_major)
        Dropdowns.setup_var_dropdowns(self)
        self.panel_line_chart.Refresh()

    @staticmethod
    def on_chk_area_time_series(self, event):
        debug = False
        chk = event.GetEventObject()
        self.drop_area_sort.Enable(not chk.IsChecked())
        time_series = chk.IsChecked()
        rotate = self.chk_area_rotate.IsChecked()
        show_major = self._get_show_major(time_series, rotate)
        if debug:
            print(f"time_series: {chk.IsChecked()}; "
                f"rotate: {self.chk_line_rotate.IsChecked()}; "
                f"show_major: {show_major}")
        self.chk_area_major_ticks.Enable(show_major)
        Dropdowns.setup_var_dropdowns(self)
        self.panel_area_chart.Refresh()


class Dropdowns:

    @staticmethod
    def get_drop_val_opts(self, panel):
        drop_opts = wx.Choice(
            panel, -1, choices=mg.DATA_SHOW_OPT_LBLS, size=(90, -1))
        drop_opts.SetFont(mg.GEN_FONT)
        idx_data_opt = mg.DATA_SHOW_OPT_LBLS.index(CUR_DATA_OPT_LBL)
        drop_opts.SetSelection(idx_data_opt)
        drop_opts.Bind(wx.EVT_CHOICE, self.on_drop_val)
        drop_opts.SetToolTip(
            'Report count(frequency), percentage, average, or sum?')
        return drop_opts

    @staticmethod
    def get_drop_sort_opts(self, panel, choices=mg.STD_SORT_OPT_LBLS):
        drop_opts = wx.Choice(panel, -1, choices=choices, size=(100, -1))
        drop_opts.SetFont(mg.GEN_FONT)
        idx_current_sort_opt = mg.STD_SORT_OPT_LBLS.index(CUR_SORT_OPT_LBL)
        drop_opts.SetSelection(idx_current_sort_opt)
        drop_opts.Bind(wx.EVT_CHOICE, partial(Dropdowns.on_drop_sort, self))
        drop_opts.SetToolTip(_('Sort order for categories'))
        return drop_opts

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
            CUR_SORT_OPT_LBL = drop.GetLabel()  ## label is what we want to store e.g. mg.SORT_VALUE_LBL
        if debug: print(f"Current sort option: {CUR_SORT_OPT_LBL}")

    @staticmethod
    def get_fresh_drop_var1(self, items, idx_sel):
        """
        Must make fresh to get performant display when lots of items in a
        non-system font on Linux.
        """
        try:
            self.drop_var1.Destroy()  ## don't want more than one
        except Exception:
            pass
        drop_var1 = wx.Choice(
            self.panel_vars, -1, choices=items, size=wx.DefaultSize)
        drop_var1.SetFont(mg.GEN_FONT)
        drop_var1.SetSelection(idx_sel)
        drop_var1.Bind(wx.EVT_CHOICE, partial(Dropdowns.on_var1_sel, self))
        drop_var1.Bind(
            wx.EVT_CONTEXT_MENU, partial(Dropdowns.on_rclick_var1, self))
        drop_var1.SetToolTip(self.variables_rc_msg)
        return drop_var1

    @staticmethod
    def get_fresh_drop_var2(self, items, idx_sel):
        """
        Must make fresh to get performant display even with lots of items in a
        non-system font on Linux.
        """
        try:
            self.drop_var2.Destroy()  ## don't want more than one
        except Exception:
            pass
        drop_var2 = wx.Choice(
            self.panel_vars, -1, choices=items, size=wx.DefaultSize)
        drop_var2.SetFont(mg.GEN_FONT)
        drop_var2.SetSelection(idx_sel)
        drop_var2.Bind(wx.EVT_CHOICE, partial(Dropdowns.on_var2_sel, self))
        drop_var2.Bind(
            wx.EVT_CONTEXT_MENU, partial(Dropdowns.on_rclick_var2, self))
        drop_var2.SetToolTip(self.variables_rc_msg)
        return drop_var2

    @staticmethod
    def get_fresh_drop_var3(self, items, idx_sel):
        """
        Must make fresh to get performant display even with lots of items in a
        non-system font on Linux.
        """
        try:
            self.drop_var3.Destroy()  ## don't want more than one
        except Exception:
            pass
        drop_var3 = wx.Choice(
            self.panel_vars, -1, choices=items, size=wx.DefaultSize)
        drop_var3.SetFont(mg.GEN_FONT)
        drop_var3.SetSelection(idx_sel)
        drop_var3.Bind(wx.EVT_CHOICE, partial(Dropdowns.on_var3_sel, self))
        drop_var3.Bind(
            wx.EVT_CONTEXT_MENU, partial(Dropdowns.on_rclick_var3, self))
        drop_var3.SetToolTip(self.variables_rc_msg)
        return drop_var3

    @staticmethod
    def get_fresh_drop_var4(self, items, idx_sel):
        """
        Must make fresh to get performant display even with lots of items in a
        non-system font on Linux.
        """
        try:
            self.drop_var4.Destroy()  ## don't want more than one
        except Exception:
            pass
        drop_var4 = wx.Choice(
            self.panel_vars, -1, choices=items, size=wx.DefaultSize)
        drop_var4.SetFont(mg.GEN_FONT)
        drop_var4.SetSelection(idx_sel)
        drop_var4.Bind(wx.EVT_CHOICE, partial(Dropdowns.on_var4_sel, self))
        drop_var4.Bind(
            wx.EVT_CONTEXT_MENU, partial(Dropdowns.on_rclick_var4, self))
        drop_var4.SetToolTip(self.variables_rc_msg)
        return drop_var4

    @staticmethod
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
        lbl1 = f"{rawlbl1}:"
        try:
            self.lbl_var1.SetLabel(lbl1)  ## if not already made, make it (this also means we only make it if not already made)
        except Exception:
            self.lbl_var1 = wx.StaticText(self.panel_vars, -1, lbl1)
            self.lbl_var1.SetFont(mg.LABEL_FONT)

    @staticmethod
    def get_items_and_sel_idx(self, default,
            sorted_var_names, var_name=None, *,
            inc_drop_select=False, override_min_data_type=None):
        debug = False
        min_data_type = (override_min_data_type if override_min_data_type
            else self.min_data_type)
        if debug: print(var_name, self.min_data_type, override_min_data_type)
        var_names = projects.get_approp_var_names(
            self.var_types, min_data_type)
        (var_choice_items, 
         sorted_vals) = lib.GuiLib.get_sorted_choice_items(
             dic_labels=self.var_labels, vals=var_names,
             inc_drop_select=inc_drop_select)
        while True:
            try:
                del sorted_var_names[0]
            except IndexError:
                break
        sorted_var_names.extend(sorted_vals)
        ## set selection
        idx_var = projects.get_idx_to_select(
            var_choice_items, var_name, self.var_labels, default)
        return var_choice_items, idx_var

    @staticmethod
    def _setup_var_dropdown_1(self, varname1, chart_config, *,
            time_series=False, show_agg=False):
        chart_config1 = chart_config[0]
        min_data_type1 = chart_config1[mg.MIN_DATA_TYPE_KEY]
        inc_drop_select1 = chart_config1[mg.EMPTY_VAL_OK]
        kwargs = {'chart_config1': chart_config1}
        if time_series:
            if not show_agg:
                kwargs['lbl1_override'] = mg.CHART_DATETIMES_LBL
        Dropdowns._update_lbl_var1(self, **kwargs)
        self.sorted_var_names1 = []
        items1, idx_sel1 = Dropdowns.get_items_and_sel_idx(
            self, mg.VAR_1_DEFAULT,
            sorted_var_names=self.sorted_var_names1, var_name=varname1,
            inc_drop_select=inc_drop_select1,
            override_min_data_type=min_data_type1)
        self.drop_var1 = Dropdowns.get_fresh_drop_var1(self, items1, idx_sel1)

    @staticmethod
    def _setup_var_dropdown_2(self, varname2, chart_config, *,
            time_series=False, show_agg=False):
        chart_config2 = chart_config[1]
        min_data_type2 = chart_config2[mg.MIN_DATA_TYPE_KEY]
        inc_drop_select2 = chart_config2[mg.EMPTY_VAL_OK]
        rawlbl = chart_config2[mg.LBL_KEY]
        if time_series and show_agg:
            rawlbl = mg.CHART_DATETIMES_LBL
        lbl2 = f'{rawlbl}:'
        try:
            self.lbl_var2.SetLabel(lbl2)  ## if not already made, make it (this also means we only make it if not already made)
        except Exception:
            self.lbl_var2 = wx.StaticText(self.panel_vars, -1, lbl2)
            self.lbl_var2.SetFont(mg.LABEL_FONT)
        self.sorted_var_names2 = []
        items2, idx_sel2 = Dropdowns.get_items_and_sel_idx(
            self, mg.VAR_2_DEFAULT,
            sorted_var_names=self.sorted_var_names2, var_name=varname2,
            inc_drop_select=inc_drop_select2,
            override_min_data_type=min_data_type2)
        self.drop_var2 = Dropdowns.get_fresh_drop_var2(self, items2, idx_sel2)

    @staticmethod
    def _setup_var_dropdown_3(self, varname3, chart_config):
        try:
            chart_config3 = chart_config[2]
            lbl3 = f'{chart_config3[mg.LBL_KEY]}:'
            min_data_type3 = chart_config3[mg.MIN_DATA_TYPE_KEY]
            inc_drop_select3 = chart_config3[mg.EMPTY_VAL_OK]
        except IndexError:
            ## OK if not a third drop down for chart
            lbl3 = f'{mg.CHARTS_CHART_BY_LBL}:'
            min_data_type3 = mg.VAR_TYPE_CAT_KEY
            inc_drop_select3 = True
        try:
            self.lbl_var3.SetLabel(lbl3)  ## if not already made, make it (this also means we only make it if not already made)
        except Exception:
            self.lbl_var3 = wx.StaticText(self.panel_vars, -1, lbl3)
            self.lbl_var3.SetFont(mg.LABEL_FONT)
        self.sorted_var_names3 = []
        items3, idx_sel3 = Dropdowns.get_items_and_sel_idx(
            self, mg.VAR_3_DEFAULT,
            sorted_var_names=self.sorted_var_names3, var_name=varname3,
            inc_drop_select=inc_drop_select3,
            override_min_data_type=min_data_type3)
        self.drop_var3 = Dropdowns.get_fresh_drop_var3(self, items3, idx_sel3)
        ## var 3 visibility
        try:
            chart_config[2]
        except Exception:
            show = False
            self.lbl_var3.Show()  ## temp
            self.drop_var3.Show()  ## temp
        else:
            show = True
        return show

    @staticmethod
    def _setup_dropdown_4(self, varname4, chart_config):
        try:
            chart_config4 = chart_config[3]
            lbl4 = f"{chart_config4[mg.LBL_KEY]}:"
            min_data_type4 = chart_config4[mg.MIN_DATA_TYPE_KEY]
            inc_drop_select4 = chart_config4[mg.EMPTY_VAL_OK]
        except IndexError:
            ## OK if not a third drop down for chart
            lbl4 = f"{mg.CHARTS_CHART_BY_LBL}:"
            min_data_type4 = mg.VAR_TYPE_CAT_KEY
            inc_drop_select4 = True
        try:
            self.lbl_var4.SetLabel(lbl4)  ## if not already made, make it (this also means we only make it if not already made)
        except Exception:
            self.lbl_var4 = wx.StaticText(self.panel_vars, -1, lbl4)
            self.lbl_var4.SetFont(mg.LABEL_FONT)
        self.sorted_var_names4 = []
        items4, idx_sel4 = Dropdowns.get_items_and_sel_idx(
            self, mg.VAR_4_DEFAULT,
            sorted_var_names=self.sorted_var_names4, var_name=varname4,
            inc_drop_select=inc_drop_select4,
            override_min_data_type=min_data_type4)
        self.drop_var4 = Dropdowns.get_fresh_drop_var4(self, items4, idx_sel4)
        ## var 4 visibility
        try:
            chart_config[3]
        except Exception:
            self.lbl_var4.Show()  ## temp
            self.drop_var4.Show()  ## temp
            show = False
        else:
            show = True
        return show

    @staticmethod
    def setup_var_dropdowns(self):
        """
        Makes fresh objects each time (and rebinds etc) because that is the only
        way (in Linux at least) to have a non-standard font-size for items in a
        performant way e.g. if more than 10-20 items in a list. Very slow if
        having to add items to dropdown if having to set font e.g. using
        SetItems().

        Set up the third and fourth set of labels even though not needed unless
        doing e.g. scatterplots to ensure they become visible when needed.
        """
        varname1, varname2, varname3, varname4 = self.get_vars()
        chart_subtype_key = self.get_chart_subtype_key()
        chart_config = mg.CHART_CONFIG[self.chart_type][chart_subtype_key]
        ## time series special case - not easy to handle by simple config settings
        show_agg, unused = self.get_agg_dets()
        time_series = (
            (self.chart_type == mg.LINE_CHART
                and self.chk_line_time_series.IsChecked())
            or
            (self.chart_type == mg.AREA_CHART
                and self.chk_area_time_series.IsChecked()))
        Dropdowns._setup_var_dropdown_1(self, varname1, chart_config,
            time_series=time_series, show_agg=show_agg)
        Dropdowns._setup_var_dropdown_2(self, varname2, chart_config,
            time_series=time_series, show_agg=show_agg)
        show_3 = Dropdowns._setup_var_dropdown_3(self, varname3, chart_config)
        show_4 = Dropdowns._setup_dropdown_4(self, varname4, chart_config)
        self.panel_vars.Layout()
        self.drop_var1.Show(True)
        self.drop_var2.Show(True)
        try:
            self.szr_vars.Clear()
        except Exception:
            pass
        top_right = wx.TOP|wx.RIGHT
        self.szr_vars.Add(self.lbl_var1, 0, top_right, 5)
        self.szr_vars.Add(self.drop_var1, 0, wx.FIXED_MINSIZE|top_right, 5)
        self.szr_vars.Add(self.lbl_var2, 0, top_right, 5)
        self.szr_vars.Add(self.drop_var2, 0, wx.FIXED_MINSIZE|top_right, 5)
        self.szr_vars.Add(self.lbl_var3, 0, top_right, 5)
        self.szr_vars.Add(self.drop_var3, 0, wx.FIXED_MINSIZE|top_right, 5)
        self.szr_vars.Add(self.lbl_var4, 0, top_right, 5)
        self.szr_vars.Add(self.drop_var4, 0, wx.FIXED_MINSIZE|top_right, 5)
        self.panel_vars.Layout()
        if not show_3:
            self.lbl_var3.SetLabel(DROPDOWN_LABEL_WHEN_INACTIVE)  ## If you hide it, you can't see it later when you change the label and show it - Grrrrrr
            self.drop_var3.Hide()
        if not show_4:
            self.lbl_var4.SetLabel(DROPDOWN_LABEL_WHEN_INACTIVE)
            self.drop_var4.Hide()

    @staticmethod
    def on_var1_sel(self, unused_event):
        self.update_defaults()

    @staticmethod
    def on_var2_sel(self, _event):
        self.setup_line_extras()
        self.update_defaults()

    @staticmethod
    def on_var3_sel(self, _event):
        self.setup_line_extras()
        self.update_defaults()

    @staticmethod
    def on_var4_sel(self, _event):
        self.setup_line_extras()
        self.update_defaults()

    @staticmethod
    def on_rclick_var1(self, unused_event):
        self.on_rclick_var(self.drop_var1, self.sorted_var_names1)

    @staticmethod
    def on_rclick_var2(self, unused_event):
        self.on_rclick_var(self.drop_var2, self.sorted_var_names2)

    @staticmethod
    def on_rclick_var3(self, unused_event):
        self.on_rclick_var(self.drop_var3, self.sorted_var_names3)

    @staticmethod
    def on_rclick_var4(self, unused_event):
        self.on_rclick_var(self.drop_var4, self.sorted_var_names4)

    @staticmethod
    def on_rclick_var(self, drop_var, sorted_var_names):
        var_name, choice_item = self.get_var_dets(drop_var, sorted_var_names)
        if var_name == mg.DROP_SELECT:
            return
        var_label = lib.GuiLib.get_item_label(self.var_labels, var_name)
        updated = config_output.set_var_props(choice_item, var_name, var_label,
            self.var_labels, self.var_notes, self.var_types, self.val_dics)
        if updated:
            Dropdowns.setup_var_dropdowns(self)
            self.update_defaults()


class Setup:

    flags_prop_zero = wx.SizerFlags(proportion=0)
    ## Always aligned to the left and top
    ## standard top and right border is 5
    flags_aligned = flags_prop_zero.Align(wx.ALIGN_LEFT|wx.ALIGN_TOP).Expand()
    flags_std = flags_aligned.Border(wx.TOP|wx.RIGHT, 5)
    
    @staticmethod
    def setup_simple_bar(self):
        self.szr_bar_chart = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_bar_chart = wx.Panel(self.panel_mid)
        lbl_val = wx.StaticText(self.panel_bar_chart, -1, _('Data\nreported:'))
        self.drop_bar_val = Dropdowns.get_drop_val_opts(
            self, self.panel_bar_chart)
        lbl_sort_str = _('Sort order\nof %s:') % BARS_SORTED_LBL
        lbl_sort = wx.StaticText(self.panel_bar_chart, -1, lbl_sort_str)
        self.drop_bar_sort = Dropdowns.get_drop_sort_opts(
            self, self.panel_bar_chart)
        self.chk_simple_bar_rotate = Checkboxes.get_chk_rotate(
            self, self.panel_bar_chart)
        self.chk_bar_borders = wx.CheckBox(
            self.panel_bar_chart, -1, _('Bar borders?'))
        self.chk_bar_borders.SetFont(mg.GEN_FONT)
        self.chk_bar_borders.SetValue(False)
        self.chk_bar_borders.SetToolTip(_('Show borders around bars?'))
        self.szr_bar_chart.Add(lbl_val, Setup.flags_std)
        self.szr_bar_chart.AddSpacer(5)
        self.szr_bar_chart.Add(self.drop_bar_val, Setup.flags_std)
        self.szr_bar_chart.AddSpacer(10)
        self.szr_bar_chart.Add(lbl_sort, Setup.flags_std)
        self.szr_bar_chart.AddSpacer(5)
        self.szr_bar_chart.Add(self.drop_bar_sort, Setup.flags_std)
        self.szr_bar_chart.AddSpacer(10)
        self.szr_bar_chart.Add(self.chk_simple_bar_rotate,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_splitline_down_by))
        self.szr_bar_chart.AddSpacer(10)
        self.szr_bar_chart.Add(self.chk_bar_borders,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_down_by))
        self.szr_bar_chart.AddSpacer(10)
        self.chk_simple_bar_show_n = Checkboxes.get_chk_show_n(
            self, self.panel_bar_chart)
        self.szr_bar_chart.AddSpacer(5)
        self.szr_bar_chart.Add(self.chk_simple_bar_show_n,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_splitline_down_by))
        self.panel_bar_chart.SetSizer(self.szr_bar_chart)
        self.szr_bar_chart.SetSizeHints(self.panel_bar_chart)

    def setup_clust_bar(self):
        self.szr_clust_bar_chart = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_clust_bar = wx.Panel(self.panel_mid)
        lbl_val = wx.StaticText(self.panel_clust_bar, -1, _('Data\nreported:'))
        self.drop_clust_val = Dropdowns.get_drop_val_opts(
            self, self.panel_clust_bar)
        lbl_sort_str = _('Sort order\nof %s:') % CLUSTERS_SORTED_LBL
        lbl_sort = wx.StaticText(self.panel_clust_bar, -1, lbl_sort_str)
        self.drop_clust_sort = Dropdowns.get_drop_sort_opts(
            self, self.panel_clust_bar,
            choices=mg.SORT_VAL_AND_LABEL_OPT_LBLS)
        self.chk_clust_bar_rotate = Checkboxes.get_chk_rotate(
            self, self.panel_clust_bar)
        self.chk_clust_borders = wx.CheckBox(
            self.panel_clust_bar, -1, _('Bar borders?'))
        self.chk_clust_borders.SetFont(mg.GEN_FONT)
        self.chk_clust_borders.SetValue(False)
        self.chk_clust_borders.SetToolTip(_('Show borders around bars?'))
        self.szr_clust_bar_chart.Add(lbl_val, Setup.flags_std)
        self.szr_clust_bar_chart.AddSpacer(5)
        self.szr_clust_bar_chart.Add(self.drop_clust_val, Setup.flags_std)
        self.szr_clust_bar_chart.AddSpacer(10)
        self.szr_clust_bar_chart.Add(lbl_sort, Setup.flags_std)
        self.szr_clust_bar_chart.AddSpacer(5)
        self.szr_clust_bar_chart.Add(self.drop_clust_sort, Setup.flags_std)
        self.szr_clust_bar_chart.AddSpacer(10)
        self.szr_clust_bar_chart.Add(self.chk_clust_bar_rotate,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_splitline_down_by))
        self.szr_clust_bar_chart.AddSpacer(10)
        self.szr_clust_bar_chart.Add(self.chk_clust_borders,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_down_by))
        self.szr_clust_bar_chart.AddSpacer(10)
        self.chk_clust_bar_show_n = Checkboxes.get_chk_show_n(
            self, self.panel_clust_bar)
        self.szr_clust_bar_chart.AddSpacer(5)
        self.szr_clust_bar_chart.Add(self.chk_clust_bar_show_n,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_splitline_down_by))
        self.panel_clust_bar.SetSizer(self.szr_clust_bar_chart)
        self.szr_clust_bar_chart.SetSizeHints(self.panel_clust_bar)

    def setup_pie(self):
        self.szr_pie_chart = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_pie_chart = wx.Panel(self.panel_mid)
        lbl_sort = wx.StaticText(self.panel_pie_chart, -1,
            _('Sort order\nof %s:') % SLICES_SORTED_LBL)
        self.drop_pie_sort = Dropdowns.get_drop_sort_opts(
            self, self.panel_pie_chart)
        ## count
        self.chk_show_count = wx.CheckBox(
            self.panel_pie_chart, -1, _('Show Count?'))
        self.chk_show_count.SetFont(mg.GEN_FONT)
        self.chk_show_count.SetValue(False)
        self.chk_show_count.SetToolTip(_('Show Count?'))
        ## percentage
        self.chk_show_pct = wx.CheckBox(self.panel_pie_chart, -1, _('Show %?'))
        self.chk_show_pct.SetFont(mg.GEN_FONT)
        self.chk_show_pct.SetValue(False)
        self.chk_show_pct.SetToolTip(_('Show %?'))
        self.szr_pie_chart.Add(lbl_sort, Setup.flags_std)
        self.szr_pie_chart.AddSpacer(5)
        self.szr_pie_chart.Add(self.drop_pie_sort, Setup.flags_std)
        self.szr_pie_chart.AddSpacer(10)
        self.szr_pie_chart.Add(self.chk_show_count,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_down_by))
        self.szr_pie_chart.Add(self.chk_show_pct,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_down_by))
        self.szr_pie_chart.AddSpacer(10)
        self.chk_pie_show_n = Checkboxes.get_chk_show_n(
            self, self.panel_pie_chart)
        self.szr_pie_chart.Add(self.chk_pie_show_n,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_splitline_down_by))
        self.panel_pie_chart.SetSizer(self.szr_pie_chart)
        self.szr_pie_chart.SetSizeHints(self.panel_pie_chart)

    def setup_line(self):
        self.szr_line_chart = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_line_chart = wx.Panel(self.panel_mid)
        lbl_val = wx.StaticText(self.panel_line_chart, -1, _('Data\nreported:'))
        self.drop_line_val = Dropdowns.get_drop_val_opts(
            self, self.panel_line_chart)
        lbl_sort = wx.StaticText(self.panel_line_chart, -1,
            _('Sort order\nof %s:') % GROUPS_SORTED_LBL)
        self.drop_line_sort = Dropdowns.get_drop_sort_opts(
            self, self.panel_line_chart, choices=mg.SORT_VAL_AND_LABEL_OPT_LBLS)
        self.chk_line_time_series = Checkboxes.get_chk_time_series(
            self, self.panel_line_chart, line=True)
        if mg.PLATFORM == mg.WINDOWS:
            smooth2use = _('Smooth line?')
            trend2use = _('Trend line?')
        else:
            smooth2use = _('Smooth\nline?')
            trend2use = _('Trend\nline?')
        self.chk_line_rotate = Checkboxes.get_chk_rotate(
            self, self.panel_line_chart)
        self.chk_line_hide_markers = Checkboxes.get_chk_hide_markers(
            self, self.panel_line_chart)
        self.chk_line_trend = self.checkbox2use(
            self.panel_line_chart, -1, trend2use)
        self.chk_line_trend.SetFont(mg.GEN_FONT)
        self.chk_line_trend.SetToolTip(_('Show trend line?'))
        self.chk_line_smooth = self.checkbox2use(
            self.panel_line_chart, -1, smooth2use)
        self.chk_line_smooth.SetFont(mg.GEN_FONT)
        self.chk_line_smooth.SetToolTip(_('Show smoothed data line?'))
        self.chk_line_major_ticks = Checkboxes.get_chk_major_ticks(
            self, self.panel_line_chart)
        self.szr_line_chart.Add(lbl_val, Setup.flags_std)
        self.szr_line_chart.AddSpacer(5)
        self.szr_line_chart.Add(self.drop_line_val, Setup.flags_std)
        self.szr_line_chart.AddSpacer(10)
        self.szr_line_chart.Add(lbl_sort, Setup.flags_std)
        self.szr_line_chart.AddSpacer(5)
        self.szr_line_chart.Add(self.drop_line_sort, Setup.flags_std)
        self.szr_line_chart.AddSpacer(10)
        self.szr_line_chart.Add(self.chk_line_time_series,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_splitline_down_by))
        self.szr_line_chart.AddSpacer(10)
        self.szr_line_chart.Add(self.chk_line_trend,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_splitline_down_by))
        self.szr_line_chart.AddSpacer(10)
        self.szr_line_chart.Add(self.chk_line_smooth,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_splitline_down_by))
        self.setup_line_extras()
        self.szr_line_chart.AddSpacer(10)
        self.szr_line_chart.Add(self.chk_line_rotate,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_splitline_down_by))
        self.szr_line_chart.AddSpacer(10)
        self.szr_line_chart.Add(self.chk_line_hide_markers,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_splitline_down_by))
        self.szr_line_chart.AddSpacer(10)
        self.szr_line_chart.Add(self.chk_line_major_ticks, 0, wx.TOP,
            self.tickbox_splitline_down_by)
        self.szr_line_chart.AddSpacer(10)
        self.chk_line_show_n = Checkboxes.get_chk_show_n(
            self, self.panel_line_chart)
        self.szr_line_chart.Add(self.chk_line_show_n,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_splitline_down_by))
        self.panel_line_chart.SetSizer(self.szr_line_chart)
        self.szr_line_chart.SetSizeHints(self.panel_line_chart)

    def setup_area(self):
        self.szr_area_chart = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_area_chart = wx.Panel(self.panel_mid)
        lbl_val = wx.StaticText(self.panel_area_chart, -1, _('Data\nreported:'))
        self.drop_area_val = Dropdowns.get_drop_val_opts(
            self, self.panel_area_chart)
        lbl_sort = wx.StaticText(self.panel_area_chart, -1,
            _('Sort order\nof %s:') % GROUPS_SORTED_LBL)
        self.drop_area_sort = Dropdowns.get_drop_sort_opts(
            self, self.panel_area_chart)
        self.chk_area_time_series = Checkboxes.get_chk_time_series(
            self, self.panel_area_chart, line=False)
        self.chk_area_rotate = Checkboxes.get_chk_rotate(
            self, self.panel_area_chart)
        self.chk_area_hide_markers = Checkboxes.get_chk_hide_markers(
            self, self.panel_area_chart)
        self.chk_area_major_ticks = Checkboxes.get_chk_major_ticks(
            self, self.panel_area_chart)
        self.szr_area_chart.Add(lbl_val, Setup.flags_std)
        self.szr_area_chart.AddSpacer(5)
        self.szr_area_chart.Add(self.drop_area_val, Setup.flags_std)
        self.szr_area_chart.AddSpacer(10)
        self.szr_area_chart.Add(lbl_sort, Setup.flags_std)
        self.szr_line_chart.AddSpacer(5)
        self.szr_area_chart.Add(self.drop_area_sort, Setup.flags_std)
        self.szr_area_chart.AddSpacer(10)
        self.szr_area_chart.Add(self.chk_area_time_series,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_splitline_down_by))
        self.szr_area_chart.AddSpacer(10)
        self.szr_area_chart.Add(self.chk_area_rotate,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_splitline_down_by))
        self.szr_area_chart.AddSpacer(10)
        self.szr_area_chart.Add(self.chk_area_hide_markers,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_splitline_down_by))
        self.szr_area_chart.AddSpacer(10)
        self.szr_area_chart.Add(self.chk_area_major_ticks,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_splitline_down_by))
        self.szr_area_chart.AddSpacer(10)
        self.chk_area_show_n = Checkboxes.get_chk_show_n(
            self, self.panel_area_chart)
        self.szr_area_chart.Add(self.chk_area_show_n,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_splitline_down_by))
        self.panel_area_chart.SetSizer(self.szr_area_chart)
        self.szr_area_chart.SetSizeHints(self.panel_area_chart)

    def setup_histogram(self):
        self.szr_histogram = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_histogram = wx.Panel(self.panel_mid)
        self.chk_show_normal = wx.CheckBox(
            self.panel_histogram, -1, _('Show normal curve?'))
        self.chk_show_normal.SetFont(mg.GEN_FONT)
        self.chk_show_normal.SetValue(False)
        self.chk_show_normal.SetToolTip(_('Show normal curve?'))
        self.chk_hist_borders = wx.CheckBox(
            self.panel_histogram, -1, _('Bar borders?'))
        self.chk_hist_borders.SetFont(mg.GEN_FONT)
        self.chk_hist_borders.SetValue(True)
        self.chk_hist_borders.SetToolTip(_('Show borders around bars?'))
        self.szr_histogram.Add(self.chk_show_normal,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_down_by))
        self.szr_histogram.AddSpacer(10)
        self.szr_histogram.Add(self.chk_hist_borders,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_down_by))
        self.szr_histogram.AddSpacer(10)
        self.chk_histogram_show_n = Checkboxes.get_chk_show_n(
            self, self.panel_histogram)
        self.szr_histogram.Add(self.chk_histogram_show_n,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_splitline_down_by))
        self.panel_histogram.SetSizer(self.szr_histogram)
        self.szr_histogram.SetSizeHints(self.panel_histogram)

    def setup_scatterplot(self):
        self.szr_scatterplot = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_scatterplot = wx.Panel(self.panel_mid)
        self.chk_dot_borders = wx.CheckBox(
            self.panel_scatterplot, -1, _('Dot borders?'))
        self.chk_dot_borders.SetFont(mg.GEN_FONT)
        self.chk_dot_borders.SetValue(True)
        self.chk_dot_borders.SetToolTip(
            _('Show borders around scatterplot dots?'))
        self.chk_regression = wx.CheckBox(
            self.panel_scatterplot, -1, _('Show regression line?'))
        self.chk_regression.SetFont(mg.GEN_FONT)
        self.chk_regression.SetValue(False)
        self.chk_regression.SetToolTip(_('Show regression line?'))
        self.szr_scatterplot.Add(self.chk_dot_borders,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_down_by))
        self.szr_scatterplot.Add(self.chk_regression,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_down_by))
        self.szr_scatterplot.AddSpacer(10)
        self.chk_scatterplot_show_n = Checkboxes.get_chk_show_n(
            self, self.panel_scatterplot)
        self.szr_scatterplot.Add(self.chk_scatterplot_show_n,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_splitline_down_by))
        self.panel_scatterplot.SetSizer(self.szr_scatterplot)
        self.szr_scatterplot.SetSizeHints(self.panel_scatterplot)

    def setup_boxplot(self):
        self.szr_boxplot = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_boxplot = wx.Panel(self.panel_mid)
        ## sort order
        lbl_sort = wx.StaticText(
            self.panel_boxplot, -1, _('Sort order\nof %s:') % GROUPS_SORTED_LBL)
        self.drop_box_sort = Dropdowns.get_drop_sort_opts(
            self, self.panel_boxplot, choices=mg.SORT_VAL_AND_LABEL_OPT_LBLS)
        ## boxplot options
        lbl_box_opts = wx.StaticText(self.panel_boxplot, -1, _('Display:'))
        self.drop_box_opts = wx.Choice(self.panel_boxplot, -1,
            choices=mg.CHART_BOXPLOT_OPTIONS, size=(200,-1))
        self.drop_box_opts.SetFont(mg.GEN_FONT)
        self.drop_box_opts.SetToolTip(
            _('Display options for whiskers and outliers'))
        self.drop_box_opts.SetSelection(0)
        ## rotate
        self.chk_boxplot_rotate = Checkboxes.get_chk_rotate(
            self, self.panel_boxplot)
        ## assemble
        self.szr_boxplot.Add(lbl_sort, Setup.flags_std)
        self.szr_boxplot.AddSpacer(5)
        self.szr_boxplot.Add(self.drop_box_sort, Setup.flags_std)
        self.szr_boxplot.AddSpacer(10)
        self.szr_boxplot.Add(lbl_box_opts, Setup.flags_std)
        self.szr_boxplot.AddSpacer(5)
        self.szr_boxplot.Add(self.drop_box_opts, Setup.flags_std)
        self.szr_boxplot.AddSpacer(10)
        self.szr_boxplot.Add(self.chk_boxplot_rotate,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_splitline_down_by))
        self.szr_boxplot.AddSpacer(10)
        self.chk_boxplot_show_n = Checkboxes.get_chk_show_n(
            self, self.panel_boxplot)
        self.szr_boxplot.Add(self.chk_boxplot_show_n,
            Setup.flags_aligned.Border(wx.TOP, self.tickbox_splitline_down_by))
        self.panel_boxplot.SetSizer(self.szr_boxplot)
        self.szr_boxplot.SetSizeHints(self.panel_boxplot)


class Scripts:

    @staticmethod
    def get_simple_barchart_script(ytitle2use, css_fil, css_idx, *,
            rotate, show_n, show_borders):
        esc_css_fil = lib.escape_pre_write(css_fil)
        sort_opt = mg.SORT_LBL2KEY[CUR_SORT_OPT_LBL]
        data_show = mg.DATA_SHOW_LBL2KEY[CUR_DATA_OPT_LBL]
        script = (f"""\
chart_output_dets = charting_output.get_gen_chart_output_dets(
    mg.SIMPLE_BARCHART, dbe, cur, tbl, tbl_filt, var_role_dic,
    sort_opt=mg.{sort_opt}, rotate={rotate}, data_show=mg.{data_show})
x_title = var_role_dic['cat_name']
y_title = {ytitle2use}
chart_output = charting_output.BarChart.simple_barchart_output(
    titles, subtitles,
    x_title, y_title,
    chart_output_dets, css_fil="{esc_css_fil}", css_idx={css_idx},
    rotate={rotate}, show_n={show_n},
    show_borders={show_borders}, page_break_after=False)""")
        return script

    @staticmethod
    def get_clustered_barchart_script(ytitle2use, css_fil, css_idx, *,
            rotate, show_n, show_borders):
        esc_css_fil = lib.escape_pre_write(css_fil)
        sort_opt = mg.SORT_LBL2KEY[CUR_SORT_OPT_LBL]
        data_show = mg.DATA_SHOW_LBL2KEY[CUR_DATA_OPT_LBL]
        script = (f"""\
chart_output_dets = charting_output.get_gen_chart_output_dets(
    mg.CLUSTERED_BARCHART, dbe, cur, tbl, tbl_filt, var_role_dic,
    sort_opt=mg.{sort_opt}, rotate={rotate}, data_show=mg.{data_show})
x_title = var_role_dic['cat_name']
y_title = {ytitle2use}
chart_output = charting_output.BarChart.clustered_barchart_output(
    titles, subtitles,
    x_title, y_title,
    chart_output_dets, css_fil="{esc_css_fil}", css_idx={css_idx},
    rotate={rotate}, show_n={show_n},
    show_borders={show_borders}, page_break_after=False)""")
        return script

    @staticmethod
    def get_pie_chart_script(css_fil, css_idx, *, inc_count, inc_pct, show_n):
        esc_css_fil = lib.escape_pre_write(css_fil)
        sort_opt = mg.SORT_LBL2KEY[CUR_SORT_OPT_LBL]
        script = (f"""\
chart_output_dets = charting_output.get_gen_chart_output_dets(mg.PIE_CHART,
    dbe, cur, tbl, tbl_filt, var_role_dic,
    sort_opt=mg.{sort_opt})
chart_output = charting_output.PieChart.piechart_output(titles, subtitles,
    chart_output_dets, css_fil="{esc_css_fil}", css_idx={css_idx},
    inc_count={inc_count}, inc_pct={inc_pct}, show_n={show_n},
    page_break_after=False)""")
        return script

    @staticmethod
    def get_line_chart_script(ytitle2use, css_fil, css_idx, *,
            time_series, rotate, show_n, major_ticks,
            inc_trend, inc_smooth, hide_markers):
        esc_css_fil = lib.escape_pre_write(css_fil)
        data_show = mg.DATA_SHOW_LBL2KEY[CUR_DATA_OPT_LBL]
        sort_opt = mg.SORT_LBL2KEY[CUR_SORT_OPT_LBL]
        xy_titles = (f"""\
x_title = var_role_dic['cat_name']
y_title = {ytitle2use}""")
        script = (f"""\
chart_output_dets = charting_output.get_gen_chart_output_dets(mg.LINE_CHART,
    dbe, cur, tbl, tbl_filt, var_role_dic,
    sort_opt=mg.{sort_opt}, rotate={rotate},
    data_show=mg.{data_show}, major_ticks={major_ticks},
    time_series={time_series})
{xy_titles}
chart_output = charting_output.LineAreaChart.linechart_output(titles, subtitles,
    x_title, y_title, chart_output_dets,
    css_fil="{esc_css_fil}", css_idx={css_idx},
    time_series={time_series}, rotate={rotate},
    show_n={show_n}, major_ticks={major_ticks},
    inc_trend={inc_trend}, inc_smooth={inc_smooth},
    hide_markers={hide_markers}, page_break_after=False)""")
        return script

    @staticmethod
    def get_area_chart_script(ytitle2use, css_fil, css_idx, *,
            time_series, rotate, show_n, major_ticks, hide_markers):
        esc_css_fil = lib.escape_pre_write(css_fil)
        sort_opt = mg.SORT_LBL2KEY[CUR_SORT_OPT_LBL]
        data_show = mg.DATA_SHOW_LBL2KEY[CUR_DATA_OPT_LBL]
        script = (f"""\
chart_output_dets = charting_output.get_gen_chart_output_dets(mg.AREA_CHART,
    dbe, cur, tbl, tbl_filt, var_role_dic,
    sort_opt=mg.{sort_opt}, rotate={rotate},
    data_show=mg.{data_show}, major_ticks={major_ticks},
    time_series={time_series})
x_title = var_role_dic['cat_name']
y_title = {ytitle2use}
chart_output = charting_output.LineAreaChart.areachart_output(titles, subtitles,
    x_title, y_title, chart_output_dets,
    css_fil="{esc_css_fil}", css_idx={css_idx},
    time_series={time_series}, rotate={rotate}, show_n={show_n},
    major_ticks={major_ticks}, hide_markers={hide_markers},
    page_break_after=False)""")
        return script

    @staticmethod
    def get_histogram_script(css_fil, css_idx, *,
            inc_normal, show_n, show_borders):
        esc_css_fil = lib.escape_pre_write(css_fil)
        script = (f"""\
(overall_title, 
chart_dets) = charting_output.Histo.get_histo_dets(dbe, cur, tbl, tbl_filt,
    flds, var_role_dic, inc_normal={inc_normal})
chart_output = charting_output.Histo.histogram_output(titles, subtitles,
    var_role_dic['bin_name'], overall_title, chart_dets,
    css_fil="{esc_css_fil}", css_idx={css_idx}, 
    inc_normal={inc_normal}, show_n={show_n},
    show_borders={show_borders}, page_break_after=False)""")
        return script

    @staticmethod
    def get_scatterplot_script(css_fil, css_idx, *,
            show_n, show_borders, inc_regression):
        esc_css_fil = lib.escape_pre_write(css_fil)
        regression = 'True' if inc_regression else 'False'
        script = (f"""\
(overall_title,
 scatterplot_dets) = charting_output.ScatterPlot.get_scatterplot_dets(
    dbe, cur, tbl, tbl_filt, var_role_dic, unique=True,
    inc_regression={regression})
chart_output = charting_output.ScatterPlot.scatterplot_output(titles, subtitles,
    overall_title, var_role_dic['x_axis_name'], var_role_dic['y_axis_name'],
    scatterplot_dets,
    css_fil="{esc_css_fil}", css_idx={css_idx},
    report_name=report_name, add_to_report=add_to_report,
    show_n={show_n}, show_borders={show_borders}, page_break_after=False)""")
        return script

    @staticmethod
    def get_boxplot_script(boxplot_opt, css_fil, css_idx, *, rotate, show_n):
        esc_css_fil = lib.escape_pre_write(css_fil)
        sort_opt = mg.SORT_LBL2KEY[CUR_SORT_OPT_LBL]
        script = (f"""\
(n_chart, xaxis_dets, xmin, xmax, ymin, ymax,
 max_label_len, max_lbl_lines,
 overall_title, chart_dets,
 any_missing_boxes) = charting_output.BoxPlot.get_boxplot_dets(dbe, cur, tbl,
    tbl_filt, flds, var_role_dic,
    sort_opt="{sort_opt}", rotate={rotate},
    boxplot_opt="{boxplot_opt}")
x_title = (var_role_dic['cat_name']
    if var_role_dic['cat_name'] else "")
y_title = var_role_dic['desc_name'] 
chart_output = charting_output.BoxPlot.boxplot_output(
    titles, subtitles, x_title, y_title, overall_title,
    var_role_dic['series_name'], n_chart,
    xaxis_dets, max_label_len, max_lbl_lines,
    chart_dets, boxplot_opt="{boxplot_opt}",
    css_fil="{esc_css_fil}", css_idx={css_idx},
    xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax,
    any_missing_boxes=any_missing_boxes, rotate={rotate}, show_n={show_n},
    page_break_after=False)""")
        return script

    @staticmethod
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
        rotate = 'True' if ROTATE else 'False'
        major_ticks = 'True' if MAJOR_TICKS else 'False'
        hide_markers = 'True' if HIDE_MARKERS else 'False'
        show_n = 'True' if SHOW_N else 'False'
        line_time_series = self.chk_line_time_series.IsChecked()
        area_time_series = self.chk_area_time_series.IsChecked()
        script_lst = []
        titles, subtitles = self.get_titles()
        script_lst.append(f'titles={titles}')
        script_lst.append(f"subtitles={subtitles}")
        script_lst.append(lib.FiltLib.get_tbl_filt_clause(
            dd.dbe, dd.db, dd.tbl))
        myvars = self.get_vars()
        if debug: print(myvars)
        ## other variables to set up
        add2report = "True" if mg.ADD2RPT else "False"
        script_lst.append(f"add_to_report = {add2report}")
        rptname = lib.escape_pre_write(report_name)
        script_lst.append(f'report_name = "{rptname}"')
        agg_fldlbl = None
        category_fldname = None
        chart_subtype_key = self.get_chart_subtype_key()
        chart_config = mg.CHART_CONFIG[self.chart_type][chart_subtype_key]
        var_roles_used = set()
        script_lst.append("var_role_dic = {}")
        for var_val, var_dets in zip(myvars, chart_config):
            var_role = var_dets[mg.VAR_ROLE_KEY]
            role_not_sel = (var_val == mg.DROP_SELECT)
            var_roles_used.add(var_role)
            if role_not_sel:
                script_lst.append(f"var_role_dic['{var_role}'] = None")
                script_lst.append(f"var_role_dic['{var_role}_name'] = None")
                script_lst.append(f"var_role_dic['{var_role}_lbls'] = None")
            else:
                script_lst.append(f'var_role_dic["{var_role}"] = "{var_val}"')  ## e.g. var_role_agg = "age"
                var_name = lib.GuiLib.get_item_label(self.var_labels, var_val)
                script_lst.append(
                    f'var_role_dic["{var_role}_name"] = "{var_name}"')  ## e.g. var_role_agg_name = "Age"
                val_lbls = self.val_dics.get(var_val, {})
                script_lst.append(
                    f"var_role_dic['{var_role}_lbls'] = {val_lbls}")  ## e.g. var_role_agg_lbls = {}
            if var_role == mg.VAR_ROLE_AGG:
                agg_fldlbl = var_name
            if var_role == mg.VAR_ROLE_CATEGORY:
                category_fldname = var_val
        for expected_var_role in mg.EXPECTED_VAR_ROLE_KEYS:
            if expected_var_role not in var_roles_used:
                ## Needed even if not supplied by dropdown so we can have a
                ## single api for get_gen_chart_dets()
                script_lst.append(f"var_role_dic['{expected_var_role}'] = None")
                script_lst.append(
                    f"var_role_dic['{expected_var_role}_name'] = None")
                script_lst.append(
                    f"var_role_dic['{expected_var_role}_lbls'] = None")
        if self.chart_type in mg.GEN_CHARTS:
            if category_fldname is None:
                raise Exception(
                    f"Cannot generate {self.chart_type} script if category "
                    "field hasn't been set.")
        if self.chart_type in mg.CHARTS_WITH_YTITLE_OPTIONS:
            if CUR_DATA_OPT_LBL == mg.SHOW_FREQ_LBL:
                ytitle2use = 'mg.Y_AXIS_FREQ_LBL'
            elif CUR_DATA_OPT_LBL == mg.SHOW_PERC_LBL:
                ytitle2use = 'mg.Y_AXIS_PERC_LBL'
            elif CUR_DATA_OPT_LBL in (mg.SHOW_AVG_LBL, mg.SHOW_SUM_LBL):
                if agg_fldlbl is None:
                    raise Exception('Aggregated variable label not supplied.')
                show_avg = (CUR_DATA_OPT_LBL == mg.SHOW_AVG_LBL)
                ytitle2use = (f'"Mean {agg_fldlbl}"' if show_avg
                    else f'"Sum of {agg_fldlbl}"')
        if self.chart_type == mg.SIMPLE_BARCHART:
            script_lst.append(Scripts.get_simple_barchart_script(
                ytitle2use, css_fil=css_fil, css_idx=css_idx, rotate=rotate,
                show_n=show_n, show_borders=self.chk_bar_borders.IsChecked()))
        elif self.chart_type == mg.CLUSTERED_BARCHART:
            script_lst.append(Scripts.get_clustered_barchart_script(
                ytitle2use, css_fil=css_fil, css_idx=css_idx, rotate=rotate,
                show_n=show_n, show_borders=self.chk_clust_borders.IsChecked()))
        elif self.chart_type == mg.PIE_CHART:
            inc_count = ('True' if self.chk_show_count.IsChecked() else 'False')
            inc_pct = ('True' if self.chk_show_pct.IsChecked() else 'False')
            script_lst.append(Scripts.get_pie_chart_script(
                css_fil, css_idx,
                inc_count=inc_count, inc_pct=inc_pct, show_n=show_n))
        elif self.chart_type == mg.LINE_CHART:
            inc_trend = ('True' if self.chk_line_trend.IsChecked()
                and self.chk_line_trend.Enabled else 'False')
            inc_smooth = ('True' if self.chk_line_smooth.IsChecked()
                and self.chk_line_smooth.Enabled else 'False')
            script_lst.append(Scripts.get_line_chart_script(
                ytitle2use, css_fil, css_idx,
                time_series=line_time_series, rotate=rotate, show_n=show_n,
                major_ticks=major_ticks, inc_trend=inc_trend, inc_smooth=inc_smooth,
                hide_markers=hide_markers))
        elif self.chart_type == mg.AREA_CHART:
            script_lst.append(Scripts.get_area_chart_script(
                ytitle2use, css_fil, css_idx,
                time_series=area_time_series, rotate=rotate, show_n=show_n,
                major_ticks=major_ticks, hide_markers=hide_markers))
        elif self.chart_type == mg.HISTOGRAM:
            inc_normal = (
                'True' if self.chk_show_normal.IsChecked() else 'False')
            script_lst.append(Scripts.get_histogram_script(css_fil=css_fil,
                css_idx=css_idx, inc_normal=inc_normal, show_n=show_n,
                show_borders=self.chk_hist_borders.IsChecked()))
        elif self.chart_type == mg.SCATTERPLOT:
            script_lst.append(Scripts.get_scatterplot_script(
                css_fil, css_idx,
                show_n=show_n, show_borders=self.chk_dot_borders.IsChecked(),
                inc_regression=self.chk_regression.IsChecked()))
        elif self.chart_type == mg.BOXPLOT:
            boxplot_opt = mg.CHART_BOXPLOT_OPTIONS[self.drop_box_opts.GetSelection()]
            script_lst.append(Scripts.get_boxplot_script(boxplot_opt,
                css_fil, css_idx, rotate=rotate, show_n=show_n))
        script_lst.append('fil.write(chart_output)')
        script = '\n'.join(script_lst)
        if debug: print(script)
        return script


class DlgCharting(indep2var.DlgIndep2VarConfig):

    """
    Handling fonts: unlike wxPython 2.8 on Ubuntu font sizing messes up spacing
    when you try to increase font size e.g. making a heading bold. Delaying the
    text of a text object until after it has been resized doesn't help. It seems
    the only answer is to make the parent object's default font the largest
    needed and then shrink from there.
    """

    inc_gp_by_select = True
    range_gps = False

    def __init__(self, title):
        ## see http://old.nabble.com/wx.StaticBoxSizer-td21662703.html
        if mg.MAX_HEIGHT <= 620:
            myheight = 600
        elif mg.MAX_HEIGHT <= 870:
            myheight = mg.MAX_HEIGHT - 70
        else:
            myheight = 800
        ## Can't use indep2var.DlgIndep2VarConfig - too many differences
        ## so must init everything manually here
        wx.Dialog.__init__(self, parent=None, id=-1, title=title,
            pos=(mg.HORIZ_OFFSET, 0), size=(1024, myheight),
            style=wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX|wx.RESIZE_BORDER|wx.CLOSE_BOX
            |wx.SYSTEM_MENU|wx.CAPTION|wx.CLIP_CHILDREN)
        config_ui.ConfigUI.__init__(self, autoupdate=True,
            multi_page_items=False)
        self.SetFont(mg.LABEL_FONT)  ## set to the largest font needed and reset smaller fonts to their smaller size. Seems to resize smaller successfully but not larger.
        if mg.PLATFORM == mg.WINDOWS:
            self.checkbox2use = lib.MultilineCheckBox
        else:
            self.checkbox2use = lib.StdCheckBox
        self.exiting = False
        self.title = title
        cc = output.get_cc()
        self.output_modules = [
            (None, 'my_globals as mg'),
            ('stats', 'core_stats'),
            ('charting', 'charting_output'),
            (None, 'output'),
            (None, 'getdata'),
        ]
        global CUR_DATA_OPT_LBL
        CUR_DATA_OPT_LBL = mg.SHOW_FREQ_LBL
        self.min_data_type = None  ## not used in charting_dlg unlike most other dlgs - need fine-grained control of up to 4 drop downs
        self.Bind(wx.EVT_CLOSE, self.on_btn_close)
        self.url_load = True  ## btn_expand
        (self.var_labels, self.var_notes,
         self.var_types,
         self.val_dics) = lib.get_var_dets(cc[mg.CURRENT_VDTS_PATH])
        self.variables_rc_msg = _('Right click variables to view/edit details')
        config_output.add_icon(frame=self)
        self.szr_main = wx.BoxSizer(wx.VERTICAL)
        ## top panel
        self.panel_data = wx.Panel(self)
        self.szr_help_data = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_vars = wx.Panel(self)
        ## key settings
        hide_db = projects.get_hide_db()
        self.drop_tbls_panel = self.panel_data
        self.drop_tbls_system_font_size = False
        self.drop_tbls_sel_evt = self.on_table_sel
        self.drop_tbls_idx_in_szr = 3 if not hide_db else 1  ## 2 fewer items
        self.drop_tbls_rmargin = 10
        self.drop_tbls_can_grow = False
        self.szr_data = self.get_szr_data(self.panel_data, hide_db=hide_db)  ## mixin
        self.drop_tbls_szr = self.szr_data
        getdata.data_dropdown_settings_correct(parent=self)
        ## variables
        bx_vars = wx.StaticBox(self.panel_vars, -1, _('Variables'))
        self.szr_vars = wx.StaticBoxSizer(bx_vars, wx.HORIZONTAL)
        if mg.PLATFORM == mg.LINUX:  ## http://trac.wxwidgets.org/ticket/9859
            bx_vars.SetToolTip(self.variables_rc_msg)
        ## misc
        self.btn_help = wx.Button(self.panel_data, wx.ID_HELP)
        self.btn_help.Bind(wx.EVT_BUTTON, self.on_btn_help)
        szr_chart_btns = wx.BoxSizer(wx.HORIZONTAL)
        self.chart_type = mg.SIMPLE_BARCHART
        Dropdowns.setup_var_dropdowns(self)
        self.panel_vars.SetSizer(self.szr_vars)
        self.szr_vars.SetSizeHints(self.panel_vars)
        ## layout
        help_down_by = 27 if mg.PLATFORM == mg.MAC else 17
        self.szr_help_data.Add(self.btn_help, 0, wx.TOP, help_down_by)
        self.szr_help_data.Add(self.szr_data, 1, wx.LEFT, 5)
        ## assemble sizer for help_data panel
        self.panel_data.SetSizer(self.szr_help_data)
        self.szr_help_data.SetSizeHints(self.panel_data)
        ## chart buttons
        self.panel_mid = wx.Panel(self)
        bx_charts = wx.StaticBox(self.panel_mid, -1, _('Chart Details'))
        self.szr_mid = wx.StaticBoxSizer(bx_charts, wx.VERTICAL)
        Btns.setup_chart_btns(self, szr_chart_btns)
        ## dp spinner
        szr_dp = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_dp_spinner = wx.StaticText(
            self.panel_mid, -1, _('Max dec\npoints'))
        self.dp_spinner = self.get_dp_spinner(
            self.panel_mid, dp_val=mg.DEFAULT_REPORT_DP)
        szr_dp.Add(self.lbl_dp_spinner, 0)
        szr_dp.Add(self.dp_spinner, 0, wx.LEFT, 10)
        szr_chart_btns.Add(szr_dp, 0, wx.TOP|wx.LEFT, 15)
        self.szr_mid.Add(szr_chart_btns, 0, wx.GROW)
        if mg.PLATFORM == mg.LINUX:  ## http://trac.wxwidgets.org/ticket/9859
            bx_charts.SetToolTip(_('Chart details'))
        ## Chart Settings
        if mg.PLATFORM == mg.WINDOWS:
            self.tickbox_down_by = 10  ## to line up with a combo
            self.tickbox_splitline_down_by = self.tickbox_down_by  ## Windows too dumb to split
        elif mg.PLATFORM == mg.LINUX:
            self.tickbox_down_by = 9
            self.tickbox_splitline_down_by = 5
        else:
            self.tickbox_down_by = 9
            self.tickbox_splitline_down_by = 5
        ## setup charts
        Setup.setup_simple_bar(self)
        Setup.setup_clust_bar(self)
        Setup.setup_pie(self)
        Setup.setup_line(self)
        Setup.setup_area(self)
        Setup.setup_histogram(self)
        Setup.setup_scatterplot(self)
        Setup.setup_boxplot(self)
        ## Hide all panels. Display and layout then hide.
        ## Prevents flicker on change later.
        panels = [
            self.panel_bar_chart,
            self.panel_clust_bar,
            self.panel_pie_chart,
            self.panel_line_chart,
            self.panel_area_chart,
            self.panel_histogram,
            self.panel_scatterplot,
            self.panel_boxplot,
        ]
        first_panel = panels[0]
        for i, panel in enumerate(panels):
            self.szr_mid.Add(panel, 0, wx.GROW)
            if i == 0:
                self.panel_mid.SetSizer(self.szr_mid)
                self.szr_mid.SetSizeHints(self.panel_mid)
            panel.Show(True)
            self.panel_mid.Layout()  ## self.Layout() doesn't work in Windows
            panel.Show(False)
            self.szr_mid.Detach(panel)
        ## Unhide default chart type (bar chart)
        self.panel_displayed = first_panel
        first_panel.Show(True)
        ## bottom panel
        self.panel_bottom = wx.Panel(self)
        self.szr_bottom = wx.BoxSizer(wx.VERTICAL)
        szr_titles = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_output_config = self.get_szr_output_config(self.panel_bottom)  ## mixin
        szr_lower = wx.BoxSizer(wx.HORIZONTAL)
        ## titles, subtitles
        lbl_titles = wx.StaticText(self.panel_bottom, -1, _('Title:'))
        lbl_titles.SetFont(mg.LABEL_FONT)
        title_height = 40 if mg.PLATFORM == mg.MAC else 20
        self.txt_titles = wx.TextCtrl(self.panel_bottom, -1,
            size=(250,title_height), style=wx.TE_MULTILINE)
        lbl_subtitles = wx.StaticText(self.panel_bottom, -1, _('Subtitle:'))
        lbl_subtitles.SetFont(mg.LABEL_FONT)
        self.txt_subtitles = wx.TextCtrl(self.panel_bottom, -1,
            size=(250,title_height), style=wx.TE_MULTILINE)
        szr_titles.Add(lbl_titles, 0, wx.RIGHT, 5)
        szr_titles.Add(self.txt_titles, 1, wx.RIGHT, 10)
        szr_titles.Add(lbl_subtitles, 0, wx.RIGHT, 5)
        szr_titles.Add(self.txt_subtitles, 1)
        self.szr_output_display = self.get_szr_output_display(
            self.panel_bottom, inc_clear=False, idx_style=1)  ## mixin
        self.html = wx.html2.WebView.New(self.panel_bottom, -1,
            size=wx.Size(200, 150))
        if mg.PLATFORM == mg.MAC:
            self.html.Bind(wx.EVT_WINDOW_CREATE, self.on_show)
        else:
            self.Bind(wx.EVT_SHOW, self.on_show)
        self.szr_bottom.Add(szr_titles, 0,
            wx.GROW|wx.LEFT|wx.TOP|wx.RIGHT|wx.BOTTOM, 10)
        self.szr_bottom.Add(
            self.szr_output_config, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szr_lower.Add(self.html, 1, wx.GROW)
        szr_lower.Add(self.szr_output_display, 0, wx.GROW|wx.LEFT, 10)
        self.szr_bottom.Add(szr_lower, 2,
            wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.TOP, 10)
        self.add_other_var_opts()
        self.panel_bottom.SetSizer(self.szr_bottom)
        self.szr_bottom.SetSizeHints(self.panel_bottom)
        ## assemble entire frame
        static_box_gap = 0 if mg.PLATFORM == mg.MAC else 5
        if static_box_gap:
            self.szr_main.Add(
                wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, static_box_gap)
        self.szr_main.Add(self.panel_data, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        if static_box_gap:
            self.szr_main.Add(
                wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, static_box_gap)
        self.szr_main.Add(self.panel_mid, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        if static_box_gap:
            self.szr_main.Add(
                wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, static_box_gap)
        self.szr_main.Add(self.panel_vars, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        self.szr_main.Add(self.panel_bottom, 1, wx.GROW)
        self.SetAutoLayout(True)
        self.SetSizer(self.szr_main)
        szr_lst = [
            self.szr_help_data, self.szr_vars, self.szr_mid, self.szr_bottom]  ## each has a panel of its own
        lib.GuiLib.set_size(window=self, szr_lst=szr_lst, width_init=1024,
            height_init=myheight)

    def on_drop_val(self, evt):
        debug = False
        global CUR_DATA_OPT_LBL
        ## http://www.blog.pythonlibrary.org/2011/09/20/wxpython-binding-multiple-widgets-to-the-same-handler/
        drop = evt.GetEventObject()
        try:
            idx_sel = drop.GetSelection()
            CUR_DATA_OPT_LBL = mg.DATA_SHOW_OPT_LBLS[idx_sel]
        except IndexError:
            pass
        except AttributeError:
            CUR_DATA_OPT = drop.GetLabel()  ## label is what we want to store e.g. mg.SHOW_FREQ_LBL
        if debug: print(f"Current data option: {CUR_DATA_OPT}")
        Dropdowns.setup_var_dropdowns(self)  ## e.g. if we select mean we now need an extra var and the 1st has to be numeric
        self.setup_line_extras()

    def on_show(self, _evt):
        if self.exiting:
            return
        html2show = _("<p>Waiting for a chart to be run.</p>")
        self.html.SetPage(html2show, mg.BASE_URL)

    def on_btn_help(self, evt):
        import webbrowser
        url = ('http://www.sofastatistics.com/wiki/doku.php?id=help:charts')
        webbrowser.open_new_tab(url)
        evt.Skip()

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
        Dropdowns.setup_var_dropdowns(self)
        self.update_defaults()

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

    def on_btn_run(self, event):
        ## get settings
        cc = output.get_cc()
        run_ok = self.test_config_ok()
        if run_ok:
            ## css_idx is supplied at the time
            get_script_args={
                'css_fil': cc[mg.CURRENT_CSS_PATH],
                'report_name': cc[mg.CURRENT_REPORT_PATH]}
            config_ui.ConfigUI.on_btn_run(
                self, event, get_script_args, new_has_dojo=True)

    def setup_line_extras(self):
        """
        Only enable trendlines and smooth line if chart type is line and a
        single line chart.
        """
        show_agg, unused = self.get_agg_dets()
        show_line_extras = (self.chart_type == mg.LINE_CHART and (
                (not show_agg  ## normal and dropdown2 is nothing
                     and self.drop_var2.GetStringSelection() == mg.DROP_SELECT)
                 or (show_agg  ## aggregate and dropdown3 is nothing
                     and self.drop_var3.GetStringSelection() == mg.DROP_SELECT)
            ))
        self.chk_line_trend.Enable(show_line_extras)
        self.chk_line_smooth.Enable(show_line_extras)
        self.panel_line_chart.Refresh()

    def add_other_var_opts(self, szr=None):
        pass

    def on_database_sel(self, evt):
        """
        Reset dbe, database, cursor, tables, table, tables dropdown,
        fields, has_unique, and idxs after a database selection.
        """
        if config_ui.ConfigUI.on_database_sel(self, evt):
            output.update_var_dets(dlg=self)
            Dropdowns.setup_var_dropdowns(self)

    def on_table_sel(self, evt):
        "Reset key data details after table selection."       
        config_ui.ConfigUI.on_table_sel(self, evt)
        ## now update var dropdowns
        output.update_var_dets(dlg=self)
        Dropdowns.setup_var_dropdowns(self)

    def on_btn_var_config(self, evt):
        """
        Want to retain already selected item - even though label and even
        position may have changed.
        """
        config_ui.ConfigUI.on_btn_var_config(self, evt)
        Dropdowns.setup_var_dropdowns(self)
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
        except Exception:  ## not visible
            mg.VAR_3_DEFAULT = None
        try:
            mg.VAR_4_DEFAULT = self.drop_var4.GetStringSelection()
        except Exception:  ## not visible
            mg.VAR_4_DEFAULT = None
        if debug:
            print(mg.VAR_1_DEFAULT, mg.VAR_2_DEFAULT, mg.VAR_3_DEFAULT,
                mg.VAR_4_DEFAULT)
   
    def update_phrase(self):
        pass

    def test_config_ok(self):
        """
        Are the appropriate selections made to enable an analysis to be run?

        There are up to four possible pairs of labels/dropdowns. We can check if
        a pair is present just by looking at the lbl (which is a static text
        ctrl). Used to see if it was visible (IsShown()) but I need them visible
        always because of layout issues. Instead, it is not active if I set
        label to ' ' so that's what we should test for.

        No longer possible to have a Select showing where Select is not
        acceptable. So the only issues are a No Selection followed by a variable
        selection or duplicate variable selections.
        """
        debug = False
        lblctrls = [self.lbl_var1, self.lbl_var2, self.lbl_var3, self.lbl_var4]
        variables = self.get_vars()
        if debug: print(variables)
        if len(lblctrls) != len(variables):
            raise Exception(
                'Mismatch in number of lbls and variables in charting dlg.')
        lblctrl_vars = zip(lblctrls, variables)
        shown_lblctrl_vars = [
            (ctrl, var_lbl) for ctrl, var_lbl in lblctrl_vars
            if ctrl.Label != DROPDOWN_LABEL_WHEN_INACTIVE]
        ## 1) Required field empty
        for var_idx, shown_lblctrl_var in enumerate(shown_lblctrl_vars):
            chart_subtype_key = self.get_chart_subtype_key()
            chart_config = mg.CHART_CONFIG[self.chart_type][chart_subtype_key]
            allows_missing = chart_config[var_idx][mg.EMPTY_VAL_OK]
            lblctrl, variable = shown_lblctrl_var
            varlbl = lblctrl.GetLabel().rstrip(':')
            role_missing = variable is None
            if role_missing and not allows_missing:
                wx.MessageBox(
                    f"The required field {varlbl} is missing for "
                    f"the {self.chart_type} chart type.")
                return False
        ## 2) Variable selected but an earlier one has not (No Selection instead)
        """
        Line charts and Scatterplots have one exception - can select chart by
        without series by
        """
        has_no_select_selected = False
        lbl_with_no_select = ''
        for var_idx, shown_lblctrl_var in enumerate(shown_lblctrl_vars):
            lblctrl, variable = shown_lblctrl_var
            if variable == mg.DROP_SELECT:
                lbl_with_no_select = lblctrl.GetLabel().rstrip(':')
                has_no_select_selected = True
            else:
                if has_no_select_selected:  ## already
                    ## OK only if a line chart or scatterplot and we are in the chart by var
                    if self.chart_type in (mg.LINE_CHART, mg.SCATTERPLOT):
                        chart_subtype_key = self.get_chart_subtype_key()
                        chart_config = mg.CHART_CONFIG\
                            [self.chart_type][chart_subtype_key]
                        var_role = chart_config[var_idx][mg.VAR_ROLE_KEY]                         
                        if var_role == mg.VAR_ROLE_CHARTS:
                            continue
                    varlbl = lblctrl.GetLabel().rstrip(':')
                    wx.MessageBox(
                        _('"%(varlbl)s" has a variable selected but '
                        'the previous drop down list "%(lbl_with_no_select)s" '
                        'does not.') % {'varlbl': varlbl,
                        'lbl_with_no_select': lbl_with_no_select})
                    return False
        ## 3) Excluding No Selections, we have duplicate selections
        selected_lblctrl_vars = [(ctrl, var) for ctrl, var in shown_lblctrl_vars
            if var != mg.DROP_SELECT]
        selected_lblctrls = [
            (ctrl, var_lbl) for ctrl, var_lbl in selected_lblctrl_vars]
        selected_lbls = [ctrl.GetLabel().rstrip(':')
            for ctrl, _var_lbl in selected_lblctrls]
        selected_vars = [var_lbl for _ctrl, var_lbl in selected_lblctrl_vars]
        unique_selected_vars = set(selected_vars)
        if len(unique_selected_vars) < len(selected_vars):
                final_comma = '' if len(selected_vars) < 3 else ','
                varlbls = ('"' + '", "'.join(selected_lbls[:-1]) + '"'
                    + final_comma + ' and "%s"' % selected_lbls[-1])
                wx.MessageBox(
                    _('The variables selected for %s must be different.')
                    % varlbls)
                return False
        return True

    def get_script(self, css_idx, css_fil, report_name):
        return Scripts.get_script(self, css_idx, css_fil, report_name)
