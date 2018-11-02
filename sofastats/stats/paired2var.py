import wx  #@UnusedImport
import wx.html2

from sofastats import my_globals as mg
from sofastats import lib
from sofastats import config_output
from sofastats import config_ui
from sofastats import getdata
from sofastats import output
from sofastats import projects


class DlgPaired2VarConfig(wx.Dialog, config_ui.ConfigUI):
    """
    ConfigUI -- provides reusable interface for data selection, setting labels,
    exporting scripts buttons etc.  Sets values for db, default_tbl etc and
    responds to selections etc.
    """

    def __init__(self, title):
        cc = output.get_cc()
        wx.Dialog.__init__(self, parent=None, id=-1, title=title,
            pos=(mg.HORIZ_OFFSET,0),
            style=wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX|wx.RESIZE_BORDER|wx.CLOSE_BOX
            |wx.SYSTEM_MENU|wx.CAPTION|wx.CLIP_CHILDREN)
        config_ui.ConfigUI.__init__(self, autoupdate=True)
        self.title = title
        self.exiting = False
        self.SetFont(mg.GEN_FONT)
        self.output_modules = [
            (None, 'my_globals as mg'),
            ('stats', 'core_stats'),
            (None, 'getdata'),
            (None, 'output'),
            (None, 'stats_output'),
        ]
        self.Bind(wx.EVT_CLOSE, self.on_btn_close)
        self.url_load = True  ## btn_expand
        (self.var_labels, self.var_notes, 
         self.var_types, 
         self.val_dics) = lib.get_var_dets(cc[mg.CURRENT_VDTS_PATH])
        self.variables_rc_msg = _('Right click variables to view/edit details')
        ## set up panel for frame
        self.panel = wx.Panel(self)
        bx_desc = wx.StaticBox(self.panel, -1, _('Purpose'))
        bx_vars = wx.StaticBox(self.panel, -1, _('Variables'))
        config_output.add_icon(frame=self)
        ## key settings
        self.drop_tbls_panel = self.panel
        self.drop_tbls_system_font_size = False
        hide_db = projects.get_hide_db()
        self.drop_tbls_idx_in_szr = 3 if not hide_db else 1  ## the 2 database items are missing)
        self.drop_tbls_sel_evt = self.on_table_sel
        self.drop_tbls_rmargin = 10
        self.drop_tbls_can_grow = False
        (self.szr_data,
         self.szr_output_config) = self.get_gen_config_szrs(self.panel,
                                                hide_db=hide_db)  ## mixin
        self.drop_tbls_szr = self.szr_data
        getdata.data_dropdown_settings_correct(parent=self)
        self.szr_output_display = self.get_szr_output_display(
            self.panel, inc_clear=False, idx_style=1)
        szr_main = wx.BoxSizer(wx.VERTICAL)
        szr_top = wx.BoxSizer(wx.HORIZONTAL)
        szr_desc = wx.StaticBoxSizer(bx_desc, wx.VERTICAL)
        eg1, eg2, eg3 = self.get_examples()
        lbl_desc1 = wx.StaticText(self.panel, -1, eg1)
        lbl_desc1.SetFont(mg.GEN_FONT)
        lbl_desc2 = wx.StaticText(self.panel, -1, eg2)
        lbl_desc2.SetFont(mg.GEN_FONT)
        lbl_desc3 = wx.StaticText(self.panel, -1, eg3)
        lbl_desc3.SetFont(mg.GEN_FONT)
        szr_desc.Add(lbl_desc1, 1, wx.GROW|wx.LEFT, 5)
        szr_desc.Add(lbl_desc2, 1, wx.GROW|wx.LEFT, 5)
        szr_desc.Add(lbl_desc3, 1, wx.GROW|wx.LEFT, 5)
        self.btn_help = wx.Button(self.panel, wx.ID_HELP)
        self.btn_help.SetFont(mg.BTN_FONT)
        self.btn_help.Bind(wx.EVT_BUTTON, self.on_btn_help)
        if mg.PLATFORM == mg.LINUX:  ## http://trac.wxwidgets.org/ticket/9859
            bx_vars.SetToolTip(self.variables_rc_msg)
        szr_vars = wx.StaticBoxSizer(bx_vars, wx.VERTICAL)
        self.szr_vars_top = wx.BoxSizer(wx.HORIZONTAL)
        szr_vars_bottom = wx.BoxSizer(wx.HORIZONTAL)
        szr_vars.Add(self.szr_vars_top, 1, wx.LEFT, 5)
        szr_vars.Add(szr_vars_bottom, 0, wx.LEFT, 5)
        ## groups
        self.lbl_group_a = wx.StaticText(self.panel, -1, _('Group A:'))
        self.lbl_group_a.SetFont(mg.LABEL_FONT)
        self.lbl_group_b = wx.StaticText(self.panel, -1, _('Group B:'))
        self.lbl_group_b.SetFont(mg.LABEL_FONT)
        self.setup_var_dropdowns()
        ## phrase
        self.lbl_phrase = wx.StaticText(
            self.panel, -1, _('Start making your selections'))
        szr_vars_bottom.Add(self.lbl_phrase, 0, wx.GROW|wx.TOP|wx.BOTTOM, 10)
        szr_bottom = wx.BoxSizer(wx.HORIZONTAL)
        if mg.MAX_HEIGHT <= 620:
            myheight = 130
        elif mg.MAX_HEIGHT <= 820:
            myheight = ((350 * mg.MAX_HEIGHT) / 1024.0) - 20
        else:
            myheight = 350
        if mg.PLATFORM == mg.MAC:
            myheight = myheight*0.3
        self.html = wx.html2.WebView.New(
            self.panel, -1, size=wx.Size(200, myheight))
        if mg.PLATFORM == mg.MAC:
            self.html.Bind(wx.EVT_WINDOW_CREATE, self.on_show)
        else:
            self.Bind(wx.EVT_SHOW, self.on_show)
        szr_bottom.Add(self.html, 1, wx.GROW)
        szr_bottom.Add(self.szr_output_display, 0, wx.GROW|wx.LEFT, 10)
        static_box_gap = 0 if mg.PLATFORM == mg.MAC else 10
        if static_box_gap:
            szr_main.Add(wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, static_box_gap)
        help_down_by = 27 if mg.PLATFORM == mg.MAC else 17
        szr_top.Add(self.btn_help, 0, wx.TOP, help_down_by)
        szr_top.Add(szr_desc, 1, wx.LEFT, 5)
        szr_main.Add(szr_top, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        if static_box_gap:
            szr_main.Add(wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, static_box_gap)
        szr_main.Add(self.szr_data, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        if static_box_gap:
            szr_main.Add(wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, static_box_gap)
        szr_main.Add(szr_vars, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        if static_box_gap:
            szr_main.Add(wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, static_box_gap)
        szr_main.Add(self.szr_output_config, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szr_main.Add(szr_bottom, 2, wx.GROW|wx.ALL, 10)
        self.panel.SetSizer(szr_main)
        szr_lst = [szr_top, self.szr_data, szr_vars, self.szr_output_config,
            szr_bottom]
        lib.GuiLib.set_size(window=self, szr_lst=szr_lst, width_init=1024)

    def get_fresh_drop_a(self, items, idx_a):
        """
        Must make fresh to get performant display even with lots of items in a
        non-system font on Linux.
        """
        try:
            self.drop_group_a.Destroy()  ## don't want more than one
        except Exception:
            pass
        drop_group_a = wx.Choice(self.panel, -1, choices=items, size=(300, -1))
        drop_group_a.SetFont(mg.GEN_FONT)
        drop_group_a.SetSelection(idx_a)
        drop_group_a.Bind(wx.EVT_CHOICE, self.on_group_by_sel)
        drop_group_a.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_group_a)
        drop_group_a.SetToolTip(self.variables_rc_msg)
        return drop_group_a

    def get_fresh_drop_b(self, items, idx_b):
        try:
            self.drop_group_b.Destroy()  ## don't want more than one
        except Exception:
            pass
        drop_group_b = wx.Choice(self.panel, -1, choices=items, size=(300, -1))
        drop_group_b.SetFont(mg.GEN_FONT)
        drop_group_b.SetSelection(idx_b)
        drop_group_b.Bind(wx.EVT_CHOICE, self.on_group_by_sel)
        drop_group_b.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_group_b)
        drop_group_b.SetToolTip(self.variables_rc_msg)
        return drop_group_b

    def setup_var_dropdowns(self):
        """
        Makes fresh objects each time (and rebinds etc) because that is the only
        way (in Linux at least) to have a non-standard font-size for items in a
        performant way e.g. if more than 10-20 items in a list. Very slow if
        having to add items to dropdown if having to set font e.g. using
        SetItems().
        """
        var_a, var_b = self.get_vars()
        fld_choice_items = self.get_group_choices()
        idx_a = projects.get_idx_to_select(
            fld_choice_items, var_a, self.var_labels, mg.GROUP_A_DEFAULT)
        self.drop_group_a = self.get_fresh_drop_a(fld_choice_items, idx_a)
        idx_b = projects.get_idx_to_select(
            fld_choice_items, var_b, self.var_labels, mg.GROUP_B_DEFAULT)
        self.drop_group_b = self.get_fresh_drop_b(fld_choice_items, idx_b)
        self.panel.Layout()
        try:
            self.szr_vars_top.Clear()
        except Exception:
            pass
        self.szr_vars_top.Add(self.lbl_group_a, 0, wx.RIGHT, 5)
        self.szr_vars_top.Add(self.drop_group_a)
        self.szr_vars_top.Add(self.lbl_group_b, 0, wx.LEFT|wx.RIGHT, 5)
        self.szr_vars_top.Add(self.drop_group_b)
        self.panel.Layout()

    def on_show(self, _event):
        if self.exiting:
            return
        html2show = _('<p>Waiting for an analysis to be run.</p>')
        self.html.SetPage(html2show, mg.BASE_URL)

    def on_rclick_group_a(self, _event):
        var_a, choice_item = self.get_var_a()
        var_label_a = lib.GuiLib.get_item_label(
            item_labels=self.var_labels, item_val=var_a)
        updated = config_output.set_var_props(choice_item, var_a, var_label_a,
            self.var_labels, self.var_notes, self.var_types, self.val_dics)
        if updated:
            self.refresh_vars()

    def on_rclick_group_b(self, _event):
        var_b, choice_item = self.get_var_b()
        var_label_b = lib.GuiLib.get_item_label(
            item_labels=self.var_labels, item_val=var_b)
        updated = config_output.set_var_props(choice_item, var_b, var_label_b,
            self.var_labels, self.var_notes, self.var_types, self.val_dics)
        if updated:
            self.refresh_vars()

    def refresh_vars(self):
        self.setup_var_dropdowns()
        self.update_defaults()
        self.update_phrase()

    def get_group_choices(self):
        """
        Get group choice items.

        Also stores var names, and var names sorted by their labels (for later
        reference).
        """
        var_names = projects.get_approp_var_names(
            self.var_types, self.min_data_type)
        if len(var_names) < 2:
            msg = (_(
                '<p>There are not enough suitable variables available for this '
                'analysis. Only variables with a %s data type can be used in '
                'this analysis.</p>'
                '<p>This problem sometimes occurs when numeric data is '
                'accidentally imported from a spreadsheet as text. In such '
                'cases the solution is to format the data columns to a numeric '
                'format in the spreadsheet and re-import it.</p>')
                % mg.VAR_TYPE_KEY2_SHORT_LBL.get(
                    self.min_data_type, _('suitable')))
            try:
                self.html.SetPage(msg, mg.BASE_URL)
            except Exception:  ## no html ctrl yet so defer and display when ready
                pass
        (fld_choice_items,
         self.sorted_var_names) = lib.GuiLib.get_sorted_choice_items(
                                    dic_labels=self.var_labels, vals=var_names)
        return fld_choice_items

    def on_database_sel(self, event):
        """
        Reset dbe, database, cursor, tables, table, tables dropdown, fields,
        has_unique, and idxs after a database selection.
        """
        if config_ui.ConfigUI.on_database_sel(self, event):
            output.update_var_dets(dlg=self)
            self.setup_var_dropdowns()

    def on_table_sel(self, event):
        "Reset key data details after table selection."
        config_ui.ConfigUI.on_table_sel(self, event)
        output.update_var_dets(dlg=self)
        self.setup_var_dropdowns()

    def get_var_a(self):
        idx_a = self.drop_group_a.GetSelection()
        var_a = self.sorted_var_names[idx_a]
        var_a_item = self.drop_group_a.GetStringSelection()
        return var_a, var_a_item

    def get_var_b(self):
        idx_b = self.drop_group_b.GetSelection()
        var_b = self.sorted_var_names[idx_b]
        var_b_item = self.drop_group_b.GetStringSelection()
        return var_b, var_b_item

    def get_vars(self):
        """
        self.sorted_var_names is set when dropdowns are set (and only changed
        when reset).
        """
        try:
            var_a, unused = self.get_var_a()
        except Exception:
            var_a = None
        try:
            var_b, unused = self.get_var_b()
        except Exception:
            var_b = None
        return var_a, var_b

    def on_btn_var_config(self, event):
        config_ui.ConfigUI.on_btn_var_config(self, event)
        self.setup_var_dropdowns()        
        self.update_phrase()

    def on_group_by_sel(self, event):
        self.update_phrase()
        self.update_defaults()
        event.Skip()

    def get_drop_vals(self):
        """
        Get values from main drop downs.

        Returns var_a, label_a, var_b, label_b.
        """
        var_a, var_b = self.get_vars()
        label_a = lib.GuiLib.get_item_label(
            item_labels=self.var_labels, item_val=var_a)
        label_b = lib.GuiLib.get_item_label(
            item_labels=self.var_labels, item_val=var_b)
        return var_a, label_a, var_b, label_b

    def update_phrase(self):
        """
        Update phrase based on Group A and Group B.
        """
        try:
            unused, label_a, unused, label_b = self.get_drop_vals()
            self.lbl_phrase.SetLabel(_("Is \"%(a)s\" different from \"%(b)s\"?") 
                % {'a': label_a, 'b': label_b})
        except Exception:
            self.lbl_phrase.SetLabel('')

    def update_defaults(self):
        mg.GROUP_A_DEFAULT = self.drop_group_a.GetStringSelection()
        mg.GROUP_B_DEFAULT = self.drop_group_b.GetStringSelection()

    def on_btn_run(self, event):
        """
        Generate script to special location (INT_SCRIPT_PATH), run script
        putting output in special location (INT_REPORT_PATH) and into report
        file, and finally, display html output.
        """
        cc = output.get_cc()
        run_ok = self.test_config_ok()
        if run_ok:
            ## css_idx is supplied at the time
            get_script_args = {
                'css_fil': cc[mg.CURRENT_CSS_PATH],
                'report_name': cc[mg.CURRENT_REPORT_PATH],
                'details': mg.DEFAULT_DETAILS}
            config_ui.ConfigUI.on_btn_run(self, event, get_script_args)

    def test_config_ok(self):
        """
        Are the appropriate selections made to enable an analysis to be run?
        """
        ## group A and B cannot be the same
        if (self.drop_group_a.GetStringSelection()
                == self.drop_group_b.GetStringSelection()):
            wx.MessageBox(_('Group A and Group B must be different'))
            return False
        return True

    def on_btn_help(self, event):
        wx.MessageBox('Under construction')
        event.Skip()

    def on_btn_clear(self, event):
        wx.MessageBox('Under construction')
        event.Skip()
