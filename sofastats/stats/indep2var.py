import wx  #@UnusedImport
import wx.html2

from .. import basic_lib as b
from .. import my_globals as mg
from .. import lib
from .. import getdata
from .. import config_output
from .. import config_ui
from .. import output
from .. import projects

def get_range_idxs(vals, val_a, val_b):
    """
    Get range indexes for two values from list of values.

    NB the two values are strings as displayed in dropdowns even if the
    underlying data is not.

    E.g. '1' and '5' in [1, 2, 3, 4, 5]
    or 'Chrome' and 'Safari' in ['Chrome', 'Firefox', ...]
    or '1000000000000.2' etc in ['1000000000000.2', '1000000000000.3', ...].
    """
    debug = False
    if debug:
        print(vals)
        print(type(val_a).__name__, val_a)
        print(type(val_b).__name__, val_b)
    uvals = [lib.UniLib.any2unicode(x) for x in vals]
    idx_val_a = uvals.index(val_a.strip('"'))
    idx_val_b = uvals.index(val_b.strip('"'))
    return idx_val_a, idx_val_b


class DlgIndep2VarConfig(wx.Dialog, config_ui.ConfigUI):
    """
    ConfigUI - provides reusable interface for data selection, setting labels,
    exporting scripts buttons etc.  Sets values for db, default_tbl etc and
    responds to selections etc.
    """
    inc_gp_by_select = False

    def __init__(self, title, takes_range=False):
        cc = output.get_cc()
        if mg.MAX_HEIGHT <= 620:
            myheight = 600
        elif mg.MAX_HEIGHT <= 870:
            myheight = mg.MAX_HEIGHT - 70
        else:
            myheight = 800
        wx.Dialog.__init__(self, parent=None, id=-1, title=title,
            pos=(mg.HORIZ_OFFSET, 0), size=(1024, myheight),
            style=wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX|wx.RESIZE_BORDER|wx.CLOSE_BOX
            |wx.SYSTEM_MENU|wx.CAPTION|wx.CLIP_CHILDREN)
        config_ui.ConfigUI.__init__(self, autoupdate=True)
        self.SetFont(mg.GEN_FONT)
        self.output_modules = [
            (None, 'my_globals as mg'),
            ('stats', 'core_stats'),
            (None, 'getdata'),
            (None, 'output'),
            (None, 'stats_output'),
        ]
        self.Bind(wx.EVT_CLOSE, self.set_exiting)
        self.title = title
        self.takes_range = takes_range
        self.url_load = True  ## btn_expand
        (self.var_labels, self.var_notes, 
         self.var_types, 
         self.val_dics) = lib.get_var_dets(cc[mg.CURRENT_VDTS_PATH])
        self.variables_rc_msg = _('Right click variables to view/edit details')
        ## set up panels for frame
        self.panel_top = wx.Panel(self)
        self.panel_data = wx.Panel(self)
        self.panel_vars = wx.Panel(self)
        self.panel_bottom = wx.Panel(self)
        bx_desc = wx.StaticBox(self.panel_top, -1, _('Purpose'))
        bx_vars = wx.StaticBox(self.panel_vars, -1, _('Variables'))
        #self.panel.SetBackgroundColour(wx.Colour(205, 217, 215))
        config_output.add_icon(frame=self)
        szr_top = wx.BoxSizer(wx.HORIZONTAL)
        ## key settings
        self.drop_tbls_panel = self.panel_data
        self.drop_tbls_system_font_size = False
        hide_db = projects.get_hide_db()
        self.drop_tbls_idx_in_szr = 3 if not hide_db else 1  ## the 2 database items are missing)
        self.drop_tbls_sel_evt = self.on_table_sel
        self.drop_tbls_rmargin = 10
        self.drop_tbls_can_grow = False
        self.szr_data = self.get_szr_data(self.panel_data, hide_db=hide_db)  ## mixin
        self.panel_data.SetSizer(self.szr_data)
        self.szr_output_config = self.get_szr_output_config(self.panel_bottom) 
        self.drop_tbls_szr = self.szr_data
        getdata.data_dropdown_settings_correct(parent=self)
        self.szr_output_display = self.get_szr_output_display(
            self.panel_bottom, inc_clear=False, idx_style=1)
        szr_main = wx.BoxSizer(wx.VERTICAL)
        szr_desc = wx.StaticBoxSizer(bx_desc, wx.VERTICAL)
        self.btn_help = wx.Button(self.panel_top, wx.ID_HELP)
        self.btn_help.SetFont(mg.BTN_FONT)
        self.btn_help.Bind(wx.EVT_BUTTON, self.on_btn_help)
        eg1, eg2, eg3 = self.get_examples()
        lbl_desc1 = wx.StaticText(self.panel_top, -1, eg1)
        lbl_desc1.SetFont(mg.GEN_FONT)
        lbl_desc2 = wx.StaticText(self.panel_top, -1, eg2)
        lbl_desc2.SetFont(mg.GEN_FONT)
        lbl_desc3 = wx.StaticText(self.panel_top, -1, eg3)
        lbl_desc3.SetFont(mg.GEN_FONT)
        szr_desc.Add(lbl_desc1, 1, wx.GROW|wx.LEFT, 5)
        szr_desc.Add(lbl_desc2, 1, wx.GROW|wx.LEFT, 5)
        szr_desc.Add(lbl_desc3, 1, wx.GROW|wx.LEFT, 5)
        if mg.PLATFORM == mg.LINUX:  ## http://trac.wxwidgets.org/ticket/9859
            bx_vars.SetToolTip(self.variables_rc_msg)
        szr_vars = wx.StaticBoxSizer(bx_vars, wx.VERTICAL)
        szr_vars_top = wx.BoxSizer(wx.HORIZONTAL)
        szr_vars_bottom = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_vars_top_left = wx.BoxSizer(wx.VERTICAL)
        szr_vars_top_right = wx.BoxSizer(wx.VERTICAL)
        self.szr_avg_vars = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_group_by_vars = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_vars_a_and_b = wx.BoxSizer(wx.HORIZONTAL)
        ## var averaged
        self.lbl_avg = wx.StaticText(self.panel_vars, -1, f'{self.averaged}:')
        self.lbl_avg.SetFont(mg.LABEL_FONT)
        self.setup_avg_dropdown()
        self.szr_vars_top_left.Add(self.szr_avg_vars, 0)
        ## group by
        self.gp_vals_sorted = []  ## same order in dropdowns
        self.gp_choice_items_sorted = []  ## refreshed as required and in order of labels, not raw values
        self.sorted_var_names_by = [] ## var names sorted by labels i.e. same as dropdown. Refreshed as needed so always usable.
        self.lbl_group_by = wx.StaticText(self.panel_vars, -1, _('Group By:'))
        self.lbl_group_by.SetFont(mg.LABEL_FONT)
        self.lbl_chop_warning = wx.StaticText(self.panel_vars, -1, '')
        self.lbl_chop_warning.SetFont(mg.GEN_FONT)
        self.setup_group_dropdown()
        if self.range_gps:
            group_a_lbl = _('From Group')
            group_b_lbl = _('To')
        else:
            group_a_lbl = _('Group A:')
            group_b_lbl = _('Group B:')
        ## Gets unique values for selected variable. Sets choices for drop_group_a and B accordingly.
        self.lbl_group_a = wx.StaticText(self.panel_vars, -1, group_a_lbl)
        self.lbl_group_b = wx.StaticText(self.panel_vars, -1, group_b_lbl)
        msg = self.setup_a_and_b_dropdowns(suppress_immediate_msg=True)
        szr_vars_top_right.Add(self.szr_group_by_vars, 1, wx.GROW)
        szr_vars_top_right.Add(self.szr_vars_a_and_b, 0, wx.GROW|wx.TOP, 5)
        szr_vars_top.Add(self.szr_vars_top_left, 0)
        self.add_other_var_opts(szr=self.szr_vars_top_left)
        ln_vert = wx.StaticLine(self.panel_vars, style=wx.LI_VERTICAL) 
        szr_vars_top.Add(ln_vert, 0, wx.GROW|wx.LEFT|wx.RIGHT, 5)
        szr_vars_top.Add(szr_vars_top_right, 0)
        ## comment
        self.lbl_phrase = wx.StaticText(
            self.panel_vars, -1, _('Start making your selections'))
        style = wx.GROW|wx.BOTTOM
        if mg.PLATFORM != mg.MAC:
            style |= wx.TOP
        szr_vars_bottom.Add(self.lbl_phrase, 0, style, 5)
        szr_vars.Add(szr_vars_top, 0)      
        szr_vars.Add(szr_vars_bottom, 0, wx.GROW)
        self.panel_vars.SetSizer(szr_vars)
        szr_bottom = wx.BoxSizer(wx.VERTICAL)
        szr_lower = wx.BoxSizer(wx.HORIZONTAL)
        if mg.MAX_HEIGHT <= 620:
            myheight = 130
        elif mg.MAX_HEIGHT <= 820:
            myheight = ((mg.MAX_HEIGHT/1024.0)*350) - 20
        else:
            myheight = 350
        if mg.PLATFORM == mg.MAC:
            myheight = myheight*0.3
        self.html = wx.html2.WebView.New(
            self.panel_bottom, -1, size=wx.Size(200, myheight))
        if mg.PLATFORM == mg.MAC:
            self.html.Bind(wx.EVT_WINDOW_CREATE, self.on_show)
        else:
            self.Bind(wx.EVT_SHOW, self.on_show)
        szr_lower.Add(self.html, 1, wx.GROW)
        szr_lower.Add(self.szr_output_display, 0, wx.GROW|wx.LEFT, 10)
        szr_bottom.Add(self.szr_output_config, 0, wx.GROW)
        szr_bottom.Add(szr_lower, 1, wx.GROW|wx.TOP, 10)
        self.panel_bottom.SetSizer(szr_bottom)
        static_box_gap = 0 if mg.PLATFORM == mg.MAC else 10
        if static_box_gap:
            szr_main.Add(wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, static_box_gap)
        help_down_by = 27 if mg.PLATFORM == mg.MAC else 17
        szr_top.Add(self.btn_help, 0, wx.TOP, help_down_by)
        szr_top.Add(szr_desc, 1, wx.LEFT, 5)
        self.panel_top.SetSizer(szr_top)
        szr_main.Add(self.panel_top, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        if static_box_gap:
            szr_main.Add(wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, static_box_gap)
        szr_main.Add(self.panel_data, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        if static_box_gap:
            szr_main.Add(wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, static_box_gap)
        szr_main.Add(self.panel_vars, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        if static_box_gap:
            szr_main.Add(wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, static_box_gap)
        szr_main.Add(self.panel_bottom, 1, 
            wx.GROW|wx.LEFT|wx.BOTTOM|wx.RIGHT, 10)
        self.SetSizer(szr_main)
        szr_lst = [szr_top, self.szr_data, szr_vars, szr_bottom]
        lib.GuiLib.set_size(window=self, szr_lst=szr_lst)
        if msg:  ## otherwise appears before dialog even open and visible
            wx.CallAfter(lambda: wx.MessageBox(msg))

    def get_fresh_drop_avg(self, items, idx_avg):
        """
        Must make fresh to get performant display even with lots of items in a
        non-system font on Linux.
        """
        try:
            self.drop_avg.Destroy()  ## don't want more than one
        except Exception:
            pass
        drop_avg = wx.Choice(self.panel_vars, -1, choices=items, size=(220, -1))
        drop_avg.SetFont(mg.GEN_FONT)
        drop_avg.SetSelection(idx_avg)
        drop_avg.Bind(wx.EVT_CHOICE, self.on_averaged_sel)
        drop_avg.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_vars)
        drop_avg.SetToolTip(self.variables_rc_msg)
        return drop_avg

    def get_fresh_drop_group_by(self, items, idx_gp_by):
        try:
            self.drop_group_by.Destroy()  ## don't want more than one
        except Exception:
            pass
        drop_group_by = wx.Choice(
            self.panel_vars, -1, choices=items, size=(220, -1))
        drop_group_by.SetFont(mg.GEN_FONT)
        drop_group_by.SetSelection(idx_gp_by)
        drop_group_by.Bind(wx.EVT_CHOICE, self.on_group_by_sel)
        drop_group_by.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_group_by)
        drop_group_by.SetToolTip(self.variables_rc_msg)
        return drop_group_by

    def get_fresh_drop_a(self, items, idx_a):
        try:
            self.drop_group_a.Destroy()  ## don't want more than one
        except Exception:
            pass
        drop_group_a = wx.Choice(
            self.panel_vars, -1, choices=items, size=(200, -1))
        drop_group_a.SetFont(mg.GEN_FONT)
        drop_group_a.SetSelection(idx_a)
        drop_group_a.Bind(wx.EVT_CHOICE, self.on_group_by_a_sel)
        drop_group_a.SetToolTip(self.variables_rc_msg)
        return drop_group_a

    def get_fresh_drop_b(self, items, idx_b):
        try:
            self.drop_group_b.Destroy()  ## don't want more than one
        except Exception:
            pass
        drop_group_b = wx.Choice(
            self.panel_vars, -1, choices=items, size=(200, -1))
        drop_group_b.SetFont(mg.GEN_FONT)
        drop_group_b.SetSelection(idx_b)
        drop_group_b.Bind(wx.EVT_CHOICE, self.on_group_by_b_sel)
        drop_group_b.SetToolTip(self.variables_rc_msg)
        return drop_group_b

    def setup_avg_dropdown(self):
        unused, var_avg = self.get_vars()
        self.sorted_var_names_avg = []
        (var_avg_choice_items,
         idx_avg) = self.get_items_and_idx_for_avg(mg.VAR_AVG_DEFAULT,
                                            self.sorted_var_names_avg, var_avg)
        self.drop_avg = self.get_fresh_drop_avg(var_avg_choice_items, idx_avg)
        self.panel_vars.Layout()
        try:
            self.szr_avg_vars.Clear()
        except Exception:
            pass
        self.szr_avg_vars.Add(self.lbl_avg, 0, wx.TOP|wx.RIGHT, 5)
        self.szr_avg_vars.Add(self.drop_avg, 0, wx.RIGHT|wx.TOP, 5)
        self.panel_vars.Layout()

    def setup_group_dropdown(self):
        var_gp, unused = self.get_vars()
        var_names = projects.get_approp_var_names()
        (var_gp_by_items,
         self.sorted_var_names_by) = lib.GuiLib.get_sorted_choice_items(
                                     dic_labels=self.var_labels, vals=var_names,
                                     inc_drop_select=self.inc_gp_by_select)
        idx_gp_by = projects.get_idx_to_select(
            var_gp_by_items, var_gp, self.var_labels, mg.GROUP_BY_DEFAULT)
        self.drop_group_by = self.get_fresh_drop_group_by(
            var_gp_by_items, idx_gp_by)
        self.panel_vars.Layout()
        try:
            self.szr_group_by_vars.Clear()
        except Exception:
            pass
        self.szr_group_by_vars.Add(self.lbl_group_by, 0, wx.RIGHT|wx.TOP, 5)
        self.szr_group_by_vars.Add(self.drop_group_by, 0, wx.GROW|wx.RIGHT, 5)
        self.szr_group_by_vars.Add(self.lbl_chop_warning, 1, wx.RIGHT, 5)
        self.panel_vars.Layout()

    def setup_a_and_b_dropdowns(
            self, val_a=None, val_b=None, *, suppress_immediate_msg=False):
        """
        Makes fresh objects each time (and rebinds etc) because that is the only
        way (in Linux at least) to have a non-standard font-size for items in a
        performant way e.g. if more than 10-20 items in a list. Very slow if
        having to add items to dropdown if having to set font e.g. using
        SetItems().

        :param bool suppress_immediate_msg: so doesn't show message during init
         before screen even displayed.
        :return: msg (if we have suppress_immediate_msg we may want to do
         something manually later).
        """
        dd = mg.DATADETS_OBJ
        unused, tbl_filt = lib.FiltLib.get_tbl_filt(dd.dbe, dd.db, dd.tbl)
        where_filt, and_filt = lib.FiltLib.get_tbl_filts(tbl_filt)
        var_gp, choice_item = self.get_group_by()
        no_selection = (not choice_item or choice_item == mg.DROP_SELECT)
        if no_selection:
            (msg, items_a, idx_a, items_b, 
             idx_b, enable) = (None, [], 0, [], 0, False)
        else:  ## this is the potentially slow bit
            wx.BeginBusyCursor()
            (msg, items_a, idx_a,
             items_b, idx_b) = self.get_items_and_idxs_for_a_and_b(var_gp,
                                             val_a, val_b, where_filt, and_filt)
            lib.GuiLib.safe_end_cursor()
            enable = True
        self.drop_group_a = self.get_fresh_drop_a(items_a, idx_a)
        self.drop_group_b = self.get_fresh_drop_b(items_b, idx_b)
        self.lbl_group_a.Enable(enable)
        self.drop_group_a.Enable(enable)
        self.lbl_group_b.Enable(enable)
        self.drop_group_b.Enable(enable)
        self.panel_vars.Layout()
        try:
            self.szr_vars_a_and_b.Clear()
        except Exception:
            pass
        self.szr_vars_a_and_b.Add(self.lbl_group_a, 0, wx.RIGHT|wx.TOP, 5)
        self.szr_vars_a_and_b.Add(self.drop_group_a, 0, wx.RIGHT, 5)
        self.szr_vars_a_and_b.Add(self.lbl_group_b, 0, wx.RIGHT|wx.TOP, 5)
        self.szr_vars_a_and_b.Add(self.drop_group_b, 0)
        self.panel_vars.Layout()
        if msg and not suppress_immediate_msg:
            wx.MessageBox(msg)
        return msg

    def on_show(self, _event):
        if self.exiting:
            return
        str_content = _('<p>Waiting for an analysis to be run.</p>')
        lib.OutputLib.update_html_ctrl(self.html, str_content)

    def add_other_var_opts(self, szr=None):
        "Used by ANOVA at least"
        pass

    def on_rclick_tables(self, event):
        """
        Extend to pass on filter changes to group by val options a and b.
        """
        config_ui.ConfigUI.on_rclick_tables(self, event)
        self.refresh_vals()
        # event.Skip() - don't use or will appear twice in Windows!

    def on_rclick_group_by(self, _event):
        var_gp, choice_item = self.get_group_by()
        label_gp = lib.GuiLib.get_item_label(
            item_labels=self.var_labels, item_val=var_gp)
        updated = config_output.set_var_props(choice_item, var_gp, label_gp,
            self.var_labels, self.var_notes, self.var_types, self.val_dics)
        if updated:
            self.refresh_vars()

    def on_rclick_vars(self, _event):
        var_name, choice_item = self.get_var_dets(self.drop_avg,
                                                  self.sorted_var_names_avg)
        var_label = lib.GuiLib.get_item_label(item_labels=self.var_labels,
            item_val=var_name)
        updated = config_output.set_var_props(choice_item, var_name, var_label,
            self.var_labels, self.var_notes, self.var_types, self.val_dics)
        if updated:
            self.refresh_vars()

    def refresh_vars(self):
        self.setup_group_dropdown()
        self.setup_avg_dropdown()
        self.setup_a_and_b_dropdowns()
        self.update_defaults()
        self.update_phrase()

    def on_paint(self, event):
        if self.show_chop_warning:
            wx.CallAfter(self.show_chop_warning)
        event.Skip()

    def on_database_sel(self, event):
        """
        Reset dbe, database, cursor, tables, table, tables dropdown, fields,
        has_unique, and idxs after a database selection.
        """
        if config_ui.ConfigUI.on_database_sel(self, event):
            output.update_var_dets(dlg=self)
            self.setup_group_dropdown()
            self.setup_avg_dropdown()
            self.setup_a_and_b_dropdowns()

    def on_table_sel(self, event):
        "Reset key data details after table selection."       
        config_ui.ConfigUI.on_table_sel(self, event)
        ## now update var dropdowns
        output.update_var_dets(dlg=self)
        self.setup_group_dropdown()
        self.setup_avg_dropdown()
        self.setup_a_and_b_dropdowns()

    def on_btn_var_config(self, event):
        """
        Want to retain already selected item - even though label and even
        position may have changed.
        """
        val_a, val_b = self.get_vals()
        config_ui.ConfigUI.on_btn_var_config(self, event)
        self.setup_group_dropdown()
        self.setup_avg_dropdown()
        self.setup_a_and_b_dropdowns(val_a, val_b)
        self.update_defaults()
        self.update_phrase()

    def get_group_by(self):
        idx_by = self.drop_group_by.GetSelection()
        var_gp = self.sorted_var_names_by[idx_by]
        var_gp_item = self.drop_group_by.GetStringSelection()
        return var_gp, var_gp_item

    def get_var_dets(self, drop_var, sorted_var_names):
        idx_var = drop_var.GetSelection()
        var_name = sorted_var_names[idx_var]
        var_item = drop_var.GetStringSelection()
        return var_name, var_item

    def get_vars(self):
        """
        self.sorted_var_names_by and self.sorted_var_names_avg are set when
        dropdowns are set (and only changed when reset).
        """
        try:
            var_gp, unused = self.get_group_by()
        except Exception:
            var_gp = None
        try:
            var_avg, _var_item = self.get_var_dets(
                self.drop_avg, self.sorted_var_names_avg)
        except Exception:
            var_avg = None
        return var_gp, var_avg

    def get_vals(self):
        """
        self.gp_vals_sorted is set when dropdowns are set (and only changed when
        reset).
        """
        try:
            idx_a = self.drop_group_a.GetSelection()
            if idx_a == -1:
                val_a = None
            else:
                val_a = self.gp_vals_sorted[idx_a]
            idx_b = self.drop_group_b.GetSelection()
            if idx_b == -1:
                val_b = None
            else:
                val_b = self.gp_vals_sorted[idx_b]
        except AttributeError:
            val_a = None
            val_b = None
        return val_a, val_b

    def on_group_by_sel(self, event):
        self.refresh_vals()
        event.Skip()

    def refresh_vals(self):
        self.setup_a_and_b_dropdowns()
        self.update_phrase()
        self.update_defaults()

    def update_defaults(self):
        mg.GROUP_BY_DEFAULT = self.drop_group_by.GetStringSelection()
        mg.VAR_AVG_DEFAULT = self.drop_avg.GetStringSelection()
        mg.VAL_A_DEFAULT = self.drop_group_a.GetStringSelection()
        mg.VAL_B_DEFAULT = self.drop_group_b.GetStringSelection()

    def on_group_by_a_sel(self, event):        
        self.update_phrase()
        self.update_defaults()
        event.Skip()

    def on_group_by_b_sel(self, event):        
        self.update_phrase()
        self.update_defaults()
        event.Skip()

    def get_items_and_idx_for_avg(self, default, sorted_var_names,
            var_name=None, inc_drop_select=False, override_min_data_type=None):
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

    def _set_raw_group_val_items(self, var_gp, *, where_filt, and_filt, n_high):
        debug = False
        dd = mg.DATADETS_OBJ
        objqtr = getdata.get_obj_quoter_func(dd.dbe)
        quoted_tblname = getdata.tblname_qtr(dd.dbe, dd.tbl)
        SQL_get_count = f'SELECT COUNT(*) FROM {quoted_tblname} {where_filt}'
        if debug: print(SQL_get_count)
        dd.cur.execute(SQL_get_count)
        rows_n = dd.cur.fetchone()[0]
        if debug: print(f'{rows_n} records')
        high_n_recs = (rows_n >= n_high)
        if high_n_recs:
            first_sql = getdata.get_first_sql(
                dd.dbe, quoted_tblname, top_n=n_high)
            source = f'({first_sql}) AS qry'
            if debug: print(source)
        else:
            source = quoted_tblname
        var_gp_str = objqtr(var_gp)
        SQL_get_sorted_vals = f"""SELECT {var_gp_str}
            FROM {source}
            WHERE {var_gp_str} IS NOT NULL
                {and_filt}
            GROUP BY {var_gp_str}
            ORDER BY {var_gp_str}"""
        if debug: print(SQL_get_sorted_vals)
        dd.cur.execute(SQL_get_sorted_vals)
        ## cope if variable has massive spread of values
        self.gp_vals_sorted = []
        excess_length_cat = False
        while True:
            row = dd.cur.fetchone()
            if not row:
                break
            val2list = row[0]
            try:
                len_val2list = len(val2list)
                if len_val2list > mg.MAX_VAL_LEN_IN_SQL_CLAUSE:
                    excess_length_cat = True
                else:
                    self.gp_vals_sorted.append(val2list)
            except TypeError:
                self.gp_vals_sorted.append(val2list)
            n_vals = len(self.gp_vals_sorted)
            if n_vals == mg.MAX_GROUPS4DROPDOWN:
                break
        return excess_length_cat, high_n_recs

    def get_items_and_idxs_for_a_and_b(self,
            var_gp, val_a, val_b, where_filt, and_filt):
        """
        If under 250,000 records in source table (when filtered, if applicable),
        use entire table as source for group by query to get unique values. If
        250,000 upwards, use first 250,000 records as source. If more than 20
        unique values, only show first 20 and inform user.
        """
        msg = None
        n_high = 250_000
        val_dic = self.val_dics.get(var_gp, {})
        excess_length_cat, high_n_recs = self._set_raw_group_val_items(
            var_gp, where_filt=where_filt, and_filt=and_filt, n_high=n_high)
        n_vals = len(self.gp_vals_sorted)
        if n_vals == mg.MAX_GROUPS4DROPDOWN:
            if high_n_recs:
                chop_warning = (
                    f'Showing first {mg.MAX_GROUPS4DROPDOWN} groups'
                    f'\nin first {n_high:,} rows')
            else:
                chop_warning = (
                    f'Showing first {mg.MAX_GROUPS4DROPDOWN} unique groups')
        elif n_vals == 0:
            chop_warning = ''
        else:
            chop_warning = (f'Showing groups from\nfirst {n_high:,} rows'
                if high_n_recs else '')
        if excess_length_cat:
            msg = (f'Values longer than {mg.MAX_VAL_LEN_IN_SQL_CLAUSE} from '
                f'"{var_gp}" were not included')
            if not n_vals:
                msg = f'No suitable values to group by. {msg}'
        else:
            if not n_vals:
                wx.MessageBox(
                    f'No suitable values to group by in "{var_gp}"')
        self.lbl_chop_warning.SetLabel(chop_warning)
        dp2use = lib.OutputLib.get_best_dp(self.gp_vals_sorted)
        try:
            gp_vals2use = [round(x, dp2use) for x in self.gp_vals_sorted]
        except Exception:
            gp_vals2use = self.gp_vals_sorted
        self.gp_choice_items_sorted = [
            lib.GuiLib.get_choice_item(val_dic, x) for x in gp_vals2use]
        items_a = self.gp_choice_items_sorted
        items_b = self.gp_choice_items_sorted
        ## set selections
        if val_a:
            item_new_version_a = lib.GuiLib.get_choice_item(val_dic, val_a)
            idx_a = self.gp_choice_items_sorted.index(item_new_version_a)
        else:  ## use defaults if possible
            idx_a = 0
            if mg.VAL_A_DEFAULT:
                try:
                    idx_a = self.gp_choice_items_sorted.index(mg.VAL_A_DEFAULT)
                except ValueError:
                    pass  ## Using idx of 0 is OK
        if val_b:
            item_new_version_b = lib.GuiLib.get_choice_item(val_dic, val_b)
            idx_b = self.gp_choice_items_sorted.index(item_new_version_b)
        else:  ## use defaults if possible
            idx_b = 0
            if mg.VAL_B_DEFAULT:
                try:
                    idx_b = self.gp_choice_items_sorted.index(mg.VAL_B_DEFAULT)
                except ValueError:
                    pass  ## Using idx of 0 is OK
        return msg, items_a, idx_a, items_b, idx_b

    def get_drop_vals(self):
        """
        Get values (in unicode form) from main drop downs.

        Returns var_gp_numeric, var_gp, label_gp, val_a, label_a, val_b,
        label_b, var_avg, label_avg.
        """
        dd = mg.DATADETS_OBJ
        selection_idx_gp = self.drop_group_by.GetSelection()
        var_gp = self.sorted_var_names_by[selection_idx_gp]
        label_gp = lib.GuiLib.get_item_label(
            item_labels=self.var_labels, item_val=var_gp)
        var_gp_numeric = dd.flds[var_gp][mg.FLD_BOLNUMERIC]
        ## Now the a and b choices under the group
        val_dic = self.val_dics.get(var_gp, {})
        selection_idx_a = self.drop_group_a.GetSelection()
        if selection_idx_a == -1:
            raise Exception('Unable to set values for groups a and b. '
                'Check your data and any filtering applied.')
        val_a_raw = self.gp_vals_sorted[selection_idx_a]
        val_a = lib.UniLib.any2unicode(val_a_raw)
        label_a = lib.GuiLib.get_item_label(
            item_labels=val_dic, item_val=val_a_raw)
        selection_idx_b = self.drop_group_b.GetSelection()
        val_b_raw = self.gp_vals_sorted[selection_idx_b]
        val_b = lib.UniLib.any2unicode(val_b_raw)
        label_b = lib.GuiLib.get_item_label(
            item_labels=val_dic, item_val=val_b_raw)
        ## the avg variable(s)
        selection_idx_avg = self.drop_avg.GetSelection()
        var_avg = self.sorted_var_names_avg[selection_idx_avg]
        label_avg = lib.GuiLib.get_item_label(
            item_labels=self.var_labels, item_val=var_avg)
        return (var_gp_numeric, var_gp, label_gp,
            val_a, label_a,
            val_b, label_b,
            var_avg, label_avg)

    def on_averaged_sel(self, event):        
        self.update_phrase()
        self.update_defaults()
        event.Skip()

    def on_btn_run(self, event):
        """
        Generate script to special location (INT_SCRIPT_PATH), run script
        putting output in special location (INT_REPORT_PATH) and into report
        file, and finally, display html output.
        """
        cc = output.get_cc()
        run_ok = self.check_config_ok()
        if run_ok:
            ## css_idx is supplied at the time
            get_script_args = {
                'css_fpath': cc[mg.CURRENT_CSS_PATH],
                'report_fpath': cc[mg.CURRENT_REPORT_PATH],
                'details': mg.DEFAULT_DETAILS}
            config_ui.ConfigUI.on_btn_run(self, event, get_script_args)

    def check_config_ok(self):
        """
        Are the appropriate selections made to enable an analysis to be run?
        """
        ## group by and averaged variables cannot be the same
        if (self.drop_group_by.GetStringSelection()
                == self.drop_avg.GetStringSelection()):
            wx.MessageBox(_('The Grouped By Variable and the %s variable '
                'cannot be the same') % self.averaged)
            return False
        ## group A and B cannot be the same
        if (self.drop_group_a.GetStringSelection()
                == self.drop_group_b.GetStringSelection()):
            wx.MessageBox(_('Group A and Group B must be different'))
            return False
        if self.takes_range:
            try:
                (var_gp_numeric, unused, unused, unused,
                 unused, unused, unused, unused, unused) = self.get_drop_vals()
            except Exception as e:
                wx.MessageBox(
                    f'Unable to get script to make output. Orig error: {b.ue(e)}')
            ## group a must be lower than group b
            selection_idx_a = self.drop_group_a.GetSelection()
            val_a = self.gp_vals_sorted[selection_idx_a]
            selection_idx_b = self.drop_group_b.GetSelection()
            val_b = self.gp_vals_sorted[selection_idx_b]
            if var_gp_numeric:
                ## NB SQLite could have a string in a numeric field
                ## could cause problems even if the string value is not one of
                ## the ones being tested as a range boundary here.
                try:
                    val_a = float(val_a)
                    val_b = float(val_b)
                except (ValueError, TypeError):
                    wx.MessageBox('Both values must be numeric.  '
                        f'Values selected were {val_a} and {val_b}')
                    return False
            if  val_a > val_b:
                wx.MessageBox(_('Group A must be lower than Group B'))
                return False
        return True

    def on_btn_help(self, event):
        wx.MessageBox('Under construction')
        event.Skip()

    def on_btn_clear(self, event):
        wx.MessageBox('Under construction')
        event.Skip()
