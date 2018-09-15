import wx

from . import basic_lib as b
from . import my_globals as mg
from . import lib
from . import config_output
from . import getdata
from . import projects

def get_val(raw_val, flds, fldname):
    """
    Value is validated first. Raw value will always be a string.

    If numeric, must be a number, an empty string (turned to Null), or any
    variant of Null.

    If a date, must be a usable date, an empty string, or Null. Empty strings
    are turned to Null. Usable dates are returned as std datetimes.

    If a string, can be anything. Variants of Null are treated specially.

    Null values (or any variant of Null) are turned to None which will be
    processed correctly as a Null when clauses are made.
    """
    debug = False
    bolnumeric = flds[fldname][mg.FLD_BOLNUMERIC]
    boldatetime = flds[fldname][mg.FLD_BOLDATETIME]
    if bolnumeric:
        if lib.TypeLib.is_numeric(raw_val):
            return float(raw_val)
        else:  ## not a num - a valid string?
            if isinstance(raw_val, str):
                if raw_val == '' or raw_val.lower() == 'null':
                    return None
        raise Exception('Only a number, an empty string, or Null can be '
            'entered for filtering a numeric field')
    elif boldatetime:
        usable_datetime = lib.DateLib.is_usable_datetime_str(raw_val)
        if usable_datetime:
            if debug: print(f"A valid datetime: '{raw_val}'")
            return lib.DateLib.get_std_datetime_str(raw_val)
        else:  ## not a datetime - a valid string?
            if isinstance(raw_val, str):
                if raw_val == '' or raw_val.lower() == 'null':
                    return None
        raise Exception('Only a datetime, an empty string, or Null can be '
            'entered for filtering a datetime field')
    else:
        if raw_val.lower() == 'null':
            return None
        else:
            return raw_val


class DlgFiltSelect(wx.Dialog):
    def __init__(self, parent, var_labels, var_notes, var_types, val_dics):
        dd = mg.DATADETS_OBJ
        self.var_dets = _('Variable Details')
        self.var_labels = var_labels
        self.var_notes = var_notes
        self.var_types = var_types
        self.val_dics = val_dics
        tbl_filt_label, self.tbl_filt = lib.FiltLib.get_tbl_filt(
            dd.dbe, dd.db, dd.tbl)
        title = _('Current filter') if self.tbl_filt else _('Apply filter')
        wx.Dialog.__init__(self, parent=parent, title=title, 
            style=wx.CAPTION|wx.SYSTEM_MENU, pos=(mg.HORIZ_OFFSET+100,100))
        self.parent = parent
        self.panel = wx.Panel(self)
        ## szrs
        szr_main = wx.BoxSizer(wx.VERTICAL)
        szr_label = wx.BoxSizer(wx.HORIZONTAL)
        szr_quick = wx.BoxSizer(wx.HORIZONTAL)
        szr_flex = wx.BoxSizer(wx.VERTICAL)
        szr_flex_across = wx.BoxSizer(wx.HORIZONTAL)
        ## assemble
        self.rad_quick = wx.RadioButton(
            self.panel, -1, _('Quick'), style=wx.RB_GROUP)
        rad_flex = wx.RadioButton(self.panel, -1, _('Flexible'))
        self.rad_quick.Bind(wx.EVT_RADIOBUTTON, self.on_rad_quick_sel)
        rad_flex.Bind(wx.EVT_RADIOBUTTON, self.on_rad_flex_sel)
        btn_help = wx.Button(self.panel, wx.ID_HELP)
        btn_help.Bind(wx.EVT_BUTTON, self.on_btn_help)
        ## label content
        lbl_label = wx.StaticText(self.panel, -1, _('Label (optional):'))
        self.txt_label = wx.TextCtrl(self.panel, -1, tbl_filt_label)
        szr_label.Add(lbl_label, 0, wx.RIGHT, 10)
        szr_label.Add(self.txt_label, 1)
        ## quick content
        self.drop_vars = wx.Choice(self.panel, -1, size=(300,-1))
        self.drop_vars.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_vars)
        self.drop_vars.SetToolTip(
            _('Right click variable to view/edit details'))
        self.sorted_var_names = []  ## refreshed as required and in order of labels, not raw values
        self.setup_vars()
        gte_choices = mg.GTES
        self.drop_gte = wx.Choice(self.panel, -1, choices=gte_choices)
        self.drop_gte.SetSelection(0)
        self.txt_val = wx.TextCtrl(self.panel, -1, '')
        self.lbl_quick_instructions = wx.StaticText(self.panel, -1,
            _("(don't quote strings e.g. John not \"John\". Null for missing)"))
        szr_quick.Add(self.rad_quick, 0)
        szr_quick.Add(self.drop_vars, 1, wx.LEFT|wx.RIGHT, 5)
        szr_quick.Add(self.drop_gte, 0)
        szr_quick.Add(self.txt_val, 0)
        ## split
        ln_split = wx.StaticLine(self.panel)
        ## flexible content
        self.txt_flex_filter = wx.TextCtrl(
            self.panel, -1, '', style=wx.TE_MULTILINE, size=(-1,75))
        self.lbl_flex_example = wx.StaticText(
            self.panel, -1, _('(enter a filter e.g. agegp > 5)'))
        szr_flex_across.Add(rad_flex, 0, wx.RIGHT, 10)
        szr_flex_across.Add(btn_help, 0)
        szr_flex.Add(szr_flex_across, 0, wx.TOP|wx.BOTTOM, 10)
        szr_flex.Add(self.lbl_flex_example, 0)
        szr_flex.Add(self.txt_flex_filter, 1, wx.GROW)
        if self.tbl_filt:
            rad_flex.SetValue(True)
            self.enable_quick_dets(False)
            self.enable_flex_dets(True)
            self.txt_flex_filter.SetValue(self.tbl_filt)
        else:
            self.rad_quick.SetValue(True)
            self.enable_quick_dets(True)
            self.enable_flex_dets(False)
        self.setup_btns()
        szr_main.Add(szr_label, 0, wx.GROW|wx.ALL, 10)
        szr_main.Add(szr_quick, 0, wx.ALL, 10)
        szr_main.Add(self.lbl_quick_instructions, 0,
            wx.ALIGN_RIGHT|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        szr_main.Add(ln_split, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szr_main.Add(szr_flex, 0, wx.GROW|wx.ALL, 10)
        szr_main.Add(self.szr_btns, 0, wx.ALL|wx.GROW, 10)
        self.panel.SetSizer(szr_main)
        szr_main.SetSizeHints(self)
        self.Layout()
        self.txt_label.SetFocus()

    def setup_vars(self, var=None):
        var_names = projects.get_approp_var_names()
        var_choices, self.sorted_var_names = lib.GuiLib.get_sorted_choice_items(
            dic_labels=self.var_labels, vals=var_names)
        self.drop_vars.SetItems(var_choices)
        idx = self.sorted_var_names.index(var) if var else 0
        self.drop_vars.SetSelection(idx)

    def setup_btns(self):
        """
        Must have ID of wx.ID_... to trigger validators (no event binding
        needed) and for std dialog button layout.

        NB can only add some buttons as part of standard sizer to be realised.

        Insert or Add others after the Realize() as required.

        See http://aspn.activestate.com/ASPN/Mail/Message/wxpython-users/3605904
        and http://aspn.activestate.com/ASPN/Mail/Message/wxpython-users/3605432
        """
        btn_var_dets = wx.Button(self.panel, -1, self.var_dets)
        btn_var_dets.Bind(wx.EVT_BUTTON, self.on_var_dets)
        btn_delete = wx.Button(self.panel, wx.ID_DELETE, _('Remove'))
        btn_delete.Bind(wx.EVT_BUTTON, self.on_delete)
        btn_cancel = wx.Button(self.panel, wx.ID_CANCEL)
        btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        if not self.tbl_filt:
            btn_delete.Disable()
        btn_ok = wx.Button(self.panel, wx.ID_OK, _('Apply'))
        btn_ok.Bind(wx.EVT_BUTTON, self.on_ok)
        ## szrs
        self.szr_btns = wx.BoxSizer(wx.HORIZONTAL)
        szr_extra_btns = wx.BoxSizer(wx.HORIZONTAL)
        szr_std_btns = wx.StdDialogButtonSizer()
        ## assemble
        szr_extra_btns.Add(btn_var_dets, 0, wx.ALIGN_LEFT)
        szr_std_btns.AddButton(btn_cancel)
        szr_std_btns.AddButton(btn_ok)
        szr_std_btns.Realize()
        szr_std_btns.Insert(0, btn_delete, 0)
        self.szr_btns.Add(szr_extra_btns, 1)
        self.szr_btns.Add(szr_std_btns, 0)
        btn_ok.SetDefault()

    def on_var_dets(self, event):
        """
        Open dialog with list of variables. On selection, opens standard get
        settings dialog.
        """
        updated = set()  ## will get populated with a True to indicate update
        dlg = config_output.DlgListVars(
            self.var_labels, self.var_notes,
            self.var_types, self.val_dics, updated)
        dlg.ShowModal()
        if updated:
            idx_var = self.drop_vars.GetSelection()
            fldname = self.sorted_var_names[idx_var]
            self.setup_vars(var=fldname)
        event.Skip()

    def on_delete(self, event):
        dd = mg.DATADETS_OBJ
        try:
            del mg.DBE_TBL_FILTS[dd.dbe][dd.db][dd.tbl]
        except KeyError:
            raise Exception(
                'Tried to delete filter but not in global dictionary')
        self.Destroy()
        self.SetReturnCode(wx.ID_DELETE)  ## only for dialogs 
        ## (MUST come after Destroy)
        event.Skip()

    def on_cancel(self, _event):
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL)  ## only for dialogs 
        ## (MUST come after Destroy)

    def on_btn_help(self, event):
        demo = self.get_demo()
        dlg = lib.DlgHelp(parent=self,
            title=_('Filtering Help'), guidance_lbl=_('Filtering Rules'), 
            activity_lbl='filtering', guidance=demo, help_pg='filtering_data')
        dlg.ShowModal()
        event.Skip()

    def get_quick_filter(self):
        "Get filter from quick setting"
        debug = False
        dd = mg.DATADETS_OBJ
        idx_var = self.drop_vars.GetSelection()
        fldname = self.sorted_var_names[idx_var]
        rawval = self.txt_val.GetValue()
        val = get_val(rawval, dd.flds, fldname)
        gte = self.drop_gte.GetStringSelection()
        filt = getdata.make_fld_val_clause(dd.dbe, dd.flds, fldname, val, gte)
        if idx_var == 0 and rawval == '':
            dlg = wx.MessageDialog(None,
                f'Are you sure you want to apply the filter "{filt}"?',
                'Confirm Filter', wx.YES_NO|wx.ICON_QUESTION)
            retval = dlg.ShowModal()
            dlg.Destroy()
            if retval != wx.ID_YES:
                return
        if debug: print(filt)
        return filt

    def get_demo(self):
        dd = mg.DATADETS_OBJ
        val_quoter = getdata.get_val_quoter_func(dd.dbe)
        objqtr = getdata.get_obj_quoter_func(dd.dbe)
        if dd.dbe == mg.DBE_SQLITE:
            sqlite_extra_comment = ' (such as the default SOFA database)'
        else:
            sqlite_extra_comment = ''
        demo = ((_('Filters for %(dbe)s data%(sqlite_extra_comment)s '
            'should look like this:') +
            '\n\ne.g. %(city)s = %(vancouver)s'
            '\ne.g. %(city)s != %(unknown_city)s'
            '\ne.g. %(age)s >= 20'
            '\ne.g. (%(city)s = %(vancouver)s AND %(age)s >= 20) '
            'OR %(gender)s = 2'
            '\ne.g. %(satisfaction)s not in (9, 99, 999)'
            '\n\nAny valid SQL should work.')
            % {'dbe': dd.dbe,
               'city': objqtr('city'), 
               'vancouver': val_quoter('Vancouver'),
               'unknown_city': val_quoter('Unknown City'),
               'age': objqtr('age'),
               'gender': objqtr('gender'),
               'satisfaction': objqtr('satisfaction'),
               'sqlite_extra_comment': sqlite_extra_comment})
        return demo

    def on_ok(self, event):
        debug = False
        dd = mg.DATADETS_OBJ
        wx.BeginBusyCursor()
        tbl_filt_label = self.txt_label.GetValue() 
        if self.rad_quick.GetValue():
            try:
                tbl_filt = self.get_quick_filter()
                if tbl_filt is None:
                    lib.GuiLib.safe_end_cursor()
                    wx.MessageBox(
                        'Please set a filter and try again. Or just Cancel')
                    self.txt_val.SetFocus()
                    return
            except Exception as e:
                lib.GuiLib.safe_end_cursor()
                wx.MessageBox(_('Problem with design of filter: %s') % b.ue(e))
                self.txt_val.SetFocus()
                return
        else:
            tbl_filt = self.txt_flex_filter.GetValue()
            if not tbl_filt:
                lib.GuiLib.safe_end_cursor()
                wx.MessageBox(_('Please enter a filter'))
                return
        ## Must work with a simple query to that database
        dbe_tblname = getdata.tblname_qtr(dd.dbe, dd.tbl)
        filt_test_SQL = f"SELECT * FROM {dbe_tblname} WHERE ({tbl_filt})"
        if debug: print(f'Filter: {filt_test_SQL}')
        try:
            dd.cur.execute(filt_test_SQL)
        except Exception:
            demo = self.get_demo()
            lib.GuiLib.safe_end_cursor()
            wx.MessageBox(
                _("Problem applying filter \"%(filt)s\" to \"%(tbl)s\"")
                % {'filt': tbl_filt, 'tbl': dd.tbl}
                + '\n\n' + demo
                + '\n\nCheck for mistakes in variable names and types '
                "by clicking on the \"%s\" button." % self.var_dets)
            return
        if dd.dbe not in mg.DBE_TBL_FILTS:
            mg.DBE_TBL_FILTS[dd.dbe] = {}
        if dd.db not in mg.DBE_TBL_FILTS[dd.dbe]:
            mg.DBE_TBL_FILTS[dd.dbe][dd.db] = {}
        mg.DBE_TBL_FILTS[dd.dbe][dd.db][dd.tbl] = (tbl_filt_label, tbl_filt)
        self.Destroy()
        self.SetReturnCode(wx.ID_OK)  ## or nothing happens!  
        ## Prebuilt dialogs must do this internally.
        event.Skip()

    def on_rad_quick_sel(self, _event):
        self.enable_quick_dets(True)
        self.enable_flex_dets(False)

    def on_rad_flex_sel(self, _event):
        self.enable_quick_dets(False)
        self.enable_flex_dets(True)
        self.txt_flex_filter.SetFocus()

    def enable_quick_dets(self, enable):
        self.drop_vars.Enable(enable)
        self.drop_gte.Enable(enable)
        self.txt_val.Enable(enable)
        self.lbl_quick_instructions.Enable(enable)

    def enable_flex_dets(self, enable):
        self.lbl_flex_example.Enable(enable)
        self.txt_flex_filter.Enable(enable)

    def get_var(self):
        idx = self.drop_vars.GetSelection()
        var = self.sorted_var_names[idx]
        var_item = self.drop_vars.GetStringSelection()
        return var, var_item

    def on_rclick_vars(self, _event):
        var_name, choice_item = self.get_var()
        var_label = lib.GuiLib.get_item_label(
            item_labels=self.var_labels, item_val=var_name)
        updated = config_output.set_var_props(choice_item, var_name, var_label,
            self.var_labels, self.var_notes, self.var_types, self.val_dics)
        if updated:
            self.setup_vars(var_name)
