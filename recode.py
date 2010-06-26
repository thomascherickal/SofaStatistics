#! /usr/bin/env python
# -*- coding: utf-8 -*-

import pprint
import wx

import my_globals as mg
import config_globals
import lib
import config_dlg
import dbe_plugins.dbe_sqlite as dbe_sqlite
import getdata
import projects
import settings_grid

dd = getdata.get_dd()
cc = config_dlg.get_cc()

TO = u"TO"
MIN = u"MIN"
MAX = u"MAX"
REMAINING = u"REMAINING"
MISSING = u"MISSING"

obj_quoter = dbe_sqlite.quote_obj
val_quoter = dbe_sqlite.quote_val

def make_when_clause(orig_clause, new, new_fld_type):
    if new_fld_type in (mg.FLD_TYPE_STRING, mg.FLD_TYPE_DATE):
        new = val_quoter(new)
    when_clause = u"            WHEN %s THEN %s" % (orig_clause, new)
    return when_clause

def process_orig(orig, fldname, fld_type):
    """
    Turn an orig value into a clause ready for use in an SQL CASE WHEN snippet.
    orig -- a string
    fldname -- field being used in the expression
    fld_type -- e.g. string
    Settings must be one per line.  In simplest case, just enter a single 
        value.
    Use "TO" for ranges rather than the ambiguous "-".
    Keywords are TO, MIN, MAX, REMAINING, MISSING.  If the user has values 
        like that they wish to recode, e.g. "MISSING" -> 99, they will need 
        to use SQLite to manipulate the data themselves.
    Virtue of keeping it very simple for easy cases, and adequate interface 
        for more flexible recoding.
    If you want 1-6, 10+ to become "Inappropriate" you would have two lines:
    1 TO 6  -> Inappropriate
    10 TO MAX -> Inappropriate
    Using commas etc as separators meant problems when recoding text which 
        contained commas.  Would require escape characters etc.  Rapidly 
        becomes too complex for target users. The approach taken in 
        sometimes slightly inefficient but it is easy to learn and apply and 
        check for mistakes.
    Look for keywords. Patterns:
    1) Look for special keywords first:
    Special:
    REMAINING
    MISSING
    2) Then look for TO.  OK to use for strings. 
    If found, split and identify if either side is MIN or 
    MAX. NB MIN must be on left and MAX on right. OK to have both. 
    NB MIN TO MAX != REMAINING.  The latter includes NULLS.
    Examples: a TO b, a TO MAX, MIN TO MAX, MIN TO B  
    3) Assume we are dealing with a single value e.g. 1 or Did Not Reply
    """
    debug = False
    fld = obj_quoter(fldname)
    if not isinstance(orig, basestring):
        raise Exception, u"process_orig() expects strings"
    orig_clause = None
    # 1 Special
    if orig.strip() == REMAINING:
        orig_clause = u"%s = TRUE" % fld # i.e. when TRUE
    elif orig.strip() == MISSING:
        orig_clause = u"%s IS NULL" % fld
    # 2 Range
    elif TO in orig:
        parts = orig.split(TO)
        if debug: print(parts)
        if len(parts) != 2:
            raise Exception, _("Unable to process \"%s\"") % orig
        l_part = parts[0].strip()
        r_part = parts[1].strip()
        if r_part == MIN:
            raise Exception, (_("%(min)s can only be on the left side "
                               "e.g.%(min)s TO 12")) % {"min": MIN}
        if l_part == MAX:
            raise Exception, (_("%(max)s can only be on the right side "
                               "e.g. %(max)s TO 12")) % {"max": MAX}
        has_min = False
        has_max = False
        num_mismatch = False
        date_mismatch = False
        if l_part == MIN:
            has_min = True
        else:
            if (fld_type == mg.FLD_TYPE_NUMERIC and not lib.is_numeric(l_part)):
                num_mismatch = True
            elif (fld_type == mg.FLD_TYPE_DATE 
                    and not lib.is_std_datetime_str(l_part)):
                date_mismatch = True
        if r_part == MAX:
            has_max = True
        else:
            if (fld_type == mg.FLD_TYPE_NUMERIC and not lib.is_numeric(r_part)):
                num_mismatch = True
            elif (fld_type == mg.FLD_TYPE_DATE
                    and not lib.is_std_datetime_str(r_part)):
                date_mismatch = True
        if num_mismatch:
            if debug: print(l_part, r_part)
            raise Exception, _("Only numeric values can be recoded for this "
                               "variable")
        if date_mismatch:
            if debug: print(l_part, r_part)
            raise Exception, _("Only date values can be recoded for this "
                               "variable")
        if fld_type in (mg.FLD_TYPE_STRING, mg.FLD_TYPE_DATE):
            l_prep = val_quoter(l_part)
            r_prep = val_quoter(r_part)
        else:
            l_prep = l_part
            r_prep = r_part
        if has_min: # MIN TO MAX
            if has_max:
                orig_clause = u"%s IS NOT NULL" % fld
            else: # MIN TO b
                orig_clause = u"%s <= %s" % (fld, r_prep) 
        else:
            if has_max: # a TO MAX
                orig_clause = u"%s >= %s" % (fld, l_prep)
            else: # a TO b
                orig_clause = u"%s BETWEEN %s AND %s" % (fld, l_prep, r_prep)
    # 3 Single value
    else:
        if fld_type in (mg.FLD_TYPE_STRING, mg.FLD_TYPE_DATE):
            orig_clause = u"%s = %s" % (fld, val_quoter(orig))
        else:
            orig_clause = u"%s = %s" % (fld, orig)
    if orig_clause is None:
        raise Exception, "Unable to process original value in recode config"
    return orig_clause

def process_label(dict_labels, fld_type, new, label):
    """
    Add non-empty label to dictionary of labels for variable
    """
    if label == u"":
        return
    if fld_type in (mg.FLD_TYPE_STRING, mg.FLD_TYPE_DATE):
        new = val_quoter(new)
    dict_labels[new] = val_quoter(label)
    
def warn_about_existing_labels(recode_dlg, val, row, col, grid, col_dets):
    """
    If a non-empty value, check to see if this variable has value labels 
        already.  If it does, let the user know.
    """
    debug = False
    if recode_dlg.new_fldname in recode_dlg.warned: # once is enough
        return
    if col == 2 and val != u"" and recode_dlg.new_fldname != u"":
        recode_dlg.warned.append(recode_dlg.new_fldname)
        if debug: print(recode_dlg.new_fldname)
        if recode_dlg.val_dics.get(recode_dlg.new_fldname):
            if debug: print(recode_dlg.val_dics[recode_dlg.new_fldname])
            max_width = 0
            fld_val_dic = recode_dlg.val_dics[recode_dlg.new_fldname]
            for key, label in fld_val_dic.items():
                max_width = len(unicode(key)) if len(unicode(key)) > max_width \
                    else max_width
            existing_labels_lst = []
            for key, label in fld_val_dic.items():
                display = u"%s:   %s" % (unicode(key).ljust(max_width), label)
                existing_labels_lst.append(display)
            existing_labels = u"\n".join(existing_labels_lst)
            wx.MessageBox(_("\"%(new_fldname)s\" already has value labels set. "
                            "Only add labels here if you wish to add to or "
                            "override existing value labels\n\n"
                            "Existing labels:\n\n%(existing_labels)s") % 
                            {"new_fldname": recode_dlg.new_fldname, 
                             "existing_labels": existing_labels})


class RecodeHelpDlg(wx.Dialog):
    def __init__(self, parent):
        debug = False
        wx.Dialog.__init__(self, parent=parent, title=_("Recoding Help"), 
                           style=wx.CAPTION|wx.SYSTEM_MENU, 
                           pos=(mg.HORIZ_OFFSET+100,100))
        self.panel = wx.Panel(self)
        bx_rules = wx.StaticBox(self.panel, -1, _("Recoding Rules"))
        szr_rules = wx.StaticBoxSizer(bx_rules, wx.VERTICAL)
        lblfont = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD)
        szr_main = wx.BoxSizer(wx.VERTICAL)
        rules = _("1. Ranges use the keyword TO e.g. \"150 TO 250\". "
            "All keywords must be upper case, so \"TO\" will work but \"to\" "
            "will not.\n\n2. \"MIN\" and \"MAX\" can be used in ranges e.g. "
            "\"MIN TO 100\", or \"100 TO MAX\". You can even use \"MIN TO MAX\""
            " if you\n    want to leave out missing values.\n\n3. \"REMAINING\""
            " and \"MISSING\" are the two remaining keywords you can use\n"
            "    e.g. if you want all missing values to become 99 you would "
            "have a line with From as \"MISSING\", and To as 99\n\n4. Only one "
            "condition is allowed per line. So if you want to recode <=5 and "
            "10+ to 99 you would have one line with \n\n    \"MIN TO 5\" as "
            "From and 99 as To \n\n        and another line with\n\n"
            "    \"10 TO MAX\" as From and 99 as To.")
        lbl_rules = wx.StaticText(self.panel, -1, rules)
        szr_rules.Add(lbl_rules, 1, wx.GROW|wx.ALL, 10)
        btn_online_help = wx.Button(self.panel, -1, _("Online Help"))
        btn_online_help.Bind(wx.EVT_BUTTON, self.on_online_help)
        btn_online_help.SetToolTipString(_("Get more help with recoding "
                                           "online"))
        btn_close = wx.Button(self.panel, wx.ID_CLOSE)
        btn_close.Bind(wx.EVT_BUTTON, self.on_close)
        szr_btns = wx.FlexGridSizer(rows=1, cols=2, hgap=5, vgap=5)
        szr_btns.AddGrowableCol(1,2) # idx, propn
        szr_btns.Add(btn_online_help, 0)
        szr_btns.Add(btn_close, 0, wx.ALIGN_RIGHT)
        szr_main.Add(szr_rules, 0, wx.GROW|wx.ALL, 10)
        szr_main.Add(szr_btns, 0, wx.GROW|wx.ALL, 10)
        self.panel.SetSizer(szr_main)
        szr_main.SetSizeHints(self)
        self.Layout()
        
    def on_online_help(self, event):
        import webbrowser
        url = (u"http://www.sofastatistics.com/wiki/doku.php"
               u"?id=help:recoding_data")
        webbrowser.open_new_tab(url)
        event.Skip()
        
    def on_close(self, event):
        self.Destroy()
        

class RecodeDlg(settings_grid.SettingsEntryDlg):
    
    def __init__(self, tblname, fld_settings):
        """
        tblname -- table containing the variable we are recoding
        fld_settings -- a list of dicts with the following keys: 
            mg.TBL_FLD_NAME, mg.TBL_FLD_NAME_ORIG, mg.TBL_FLD_TYPE, 
            mg.TBL_FLD_TYPE_ORIG.
        """
        self.tblname = tblname
        self.warned = [] # For cell_response_func.  Lists vars warned about.
        col_dets = [
                    {"col_label": _("From"), "col_type": settings_grid.COL_STR, 
                     "col_width": 200},
                    {"col_label": _("To"), "col_type": settings_grid.COL_STR, 
                     "col_width": 200},
                    {"col_label": _("Label"), "col_type": settings_grid.COL_STR, 
                     "col_width": 200, "empty_ok": True},
                     ]
        grid_size = (640, 250)
        wx.Dialog.__init__(self, None, title=_("Recode Variable"),
                          size=(700,350), pos=(mg.HORIZ_OFFSET+150,100),
                          style=wx.RESIZE_BORDER|wx.CAPTION|wx.SYSTEM_MENU)
        self.var_labels, self.var_notes, self.var_types, self.val_dics = \
                                    lib.get_var_dets(cc[mg.CURRENT_VDTS_PATH])
        self.panel = wx.Panel(self)
        # New controls
        lbl_from = wx.StaticText(self.panel, -1, _("Recode:"))
        lbl_from.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.settings_data = fld_settings
        # [('string', 'fname', 'fname (string)'), ...]
        # field type is used for validation and constructing recode SQL string
        fld_dets = [(x[mg.TBL_FLD_TYPE], x[mg.TBL_FLD_NAME],
                     u"%s (%s)" % (x[mg.TBL_FLD_NAME], x[mg.TBL_FLD_TYPE])) 
                    for x in self.settings_data]
        fld_dets.sort(key=lambda s: s[2].upper()) # needed consistent sorting
        self.fld_types = [x[0] for x in fld_dets]
        self.fld_names = [x[1] for x in fld_dets]
        self.fld_choices = [x[2] for x in fld_dets]
        self.fldname = self.fld_names[0]
        self.new_fldname = u""
        self.drop_from = wx.Choice(self.panel, -1, choices=self.fld_choices, 
                                   size=(250,-1))
        self.drop_from.SetSelection(0)
        self.drop_from.Bind(wx.EVT_CHOICE, self.on_var_sel)
        self.drop_from.Bind(wx.EVT_CONTEXT_MENU, self.on_var_rclick)
        self.drop_from.SetToolTipString(_("Right click to view variable "
                                          "details"))
        lbl_to = wx.StaticText(self.panel, -1, u"To:")
        lbl_to.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.txt_to = wx.TextCtrl(self.panel, -1, size=(250, -1))
        self.txt_to.Bind(wx.EVT_CHAR, self.on_txt_to_char)
        init_recode_clauses_data = []
        self.recode_clauses_data = []
        self.tabentry = settings_grid.SettingsEntry(self, self.panel, False, 
                                grid_size, col_dets, init_recode_clauses_data, 
                                self.recode_clauses_data,
                                cell_response_func=warn_about_existing_labels)
        self.tabentry.grid.Enable(False)
        self.tabentry.grid.SetToolTipString(_("Disabled until there is a "
                                              "variable to recode to"))
        btn_cancel = wx.Button(self.panel, wx.ID_CANCEL)
        btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        btn_help = wx.Button(self.panel, wx.ID_HELP)
        btn_help.Bind(wx.EVT_BUTTON, self.on_help)
        btn_recode = wx.Button(self.panel, -1, _("Recode"))
        btn_recode.Bind(wx.EVT_BUTTON, self.on_recode)
        btn_recode.SetToolTipString(_("Recode an existing variable into a new "
                                      "variable"))
        # sizers
        self.szr_main = wx.BoxSizer(wx.VERTICAL)
        self.szr_vars = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_btns = wx.FlexGridSizer(rows=1, cols=3, hgap=5, vgap=0)
        self.szr_btns.AddGrowableCol(0,2) # idx, propn
        self.szr_vars.Add(lbl_from, 0, wx.RIGHT, 5)
        self.szr_vars.Add(self.drop_from, 1, wx.RIGHT, 10)
        self.szr_vars.Add(lbl_to, 0, wx.RIGHT, 5)
        self.szr_vars.Add(self.txt_to, 1)
        self.szr_main.Add(self.szr_vars, 0, wx.GROW|wx.ALL, 10)
        self.szr_btns.Add(btn_cancel)
        self.szr_btns.Add(btn_help)
        self.szr_btns.Add(btn_recode)
        self.szr_main.Add(self.tabentry.grid, 2, wx.GROW|wx.ALL, 5)
        self.szr_main.Add(self.szr_btns, 0, wx.GROW|wx.ALL, 10)
        self.panel.SetSizer(self.szr_main)
        self.szr_main.SetSizeHints(self)
        self.Layout()
        self.drop_from.SetFocus()

    def on_var_sel(self, event):
        var_idx = self.drop_from.GetSelection()
        self.fldname = self.fld_names[var_idx]

    def on_var_rclick(self, event):
        var_label = lib.get_item_label(self.var_labels, self.fldname)
        choice_item = lib.get_choice_item(self.var_labels, self.fldname)
        updated = projects.set_var_props(choice_item, self.fldname, var_label, 
                                         self.var_labels, self.var_notes, 
                                         self.var_types, self.val_dics)
    def on_txt_to_char(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_RETURN:
            self.tabentry.grid.SetFocus()
            return
        # NB callafter to allow data to updated in text ctrl
        wx.CallAfter(self.update_new_fldname)
        event.Skip()
    
    def update_new_fldname(self):
        debug = False
        self.new_fldname = self.txt_to.GetValue()
        if debug: print(self.new_fldname)
        enable = (self.new_fldname.strip() != u"")
        self.tabentry.grid.Enable(enable)

    def on_cancel(self, event):
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL)

    def on_help(self, event):
        dlg = RecodeHelpDlg(self)
        dlg.ShowModal()
        event.Skip()
    
    def recover_from_failed_recode(self):
        """
        If this goes wrong, delete freshly-created table with orig name, and 
            rename tmp table back to orig name. That way, we haven't wiped the 
            original table merely because of a recode problem
        """
        dd.con.commit()
        getdata.force_tbls_refresh()
        SQL_drop_orig = u"DROP TABLE IF EXISTS %s" % obj_quoter(self.tblname)
        dd.cur.execute(SQL_drop_orig)
        dd.con.commit()
        getdata.force_tbls_refresh()
        SQL_rename_tbl = (u"ALTER TABLE %s RENAME TO %s" % 
                          (obj_quoter(mg.TMP_TBL_NAME),
                           obj_quoter(self.tblname)))
        dd.cur.execute(SQL_rename_tbl)
        getdata.force_tbls_refresh()
        dd.set_db(dd.db, tbl=self.tblname) # refresh tbls downwards
    
    def recode_tbl(self, case_when, oth_name_types, 
                   idx_new_fld_in_oth_name_types):
        """
        Build SQL, rename existing to tmp table, create empty table with orig 
            name, and then mass into it.
        oth_name_types -- includes the new field
        idx_new_fld_in_oth_name_types -- needed an index which could be used in 
            oth_name_types. An idx for the orig field wouldn't work if the field 
            was the sofa_id.
        """
        debug = False
        # rename table to tmp
        getdata.force_tbls_refresh()
        SQL_drop_tmp = u"DROP TABLE IF EXISTS %s" % obj_quoter(mg.TMP_TBL_NAME)
        dd.cur.execute(SQL_drop_tmp)
        SQL_rename_tbl = (u"ALTER TABLE %s RENAME TO %s" % 
                          (obj_quoter(self.tblname), 
                           obj_quoter(mg.TMP_TBL_NAME)))
        dd.cur.execute(SQL_rename_tbl)
        # create new table with orig name and extra field
        create_fld_clause = getdata.get_create_flds_txt(oth_name_types, 
                                                        strict_typing=False,
                                                        inc_sofa_id=True)
        getdata.force_tbls_refresh()
        SQL_make_recoded_tbl = u"CREATE TABLE %s (%s) " % \
                                   (obj_quoter(self.tblname), create_fld_clause)
        if debug: print(u"SQL_make_recoded_tbl: %s" % SQL_make_recoded_tbl)
        dd.cur.execute(SQL_make_recoded_tbl)
        # want fields before new field, then case when, then any remaining flds
        fld_clauses_lst = []
        fld_clauses_lst.append(u"NULL AS %s" % obj_quoter(mg.SOFA_ID))
        # fldnames from start of other (non sofa_id) fields to before new field 
        # (may be none)
        if debug: 
            print(u"oth_name_types: %s" % oth_name_types)
            print(u"idx_new_fld_in_oth_name_types: %s" % 
                  idx_new_fld_in_oth_name_types)
        name_types_pre_new = oth_name_types[: idx_new_fld_in_oth_name_types]
        if debug: print(u"name_types_pre_new: %s" % name_types_pre_new)
        for name, unused in name_types_pre_new:
            fld_clauses_lst.append(obj_quoter(name))
        fld_clauses_lst.append(case_when)
        # want fields after new field (if any).  Skip new recoded fld.
        name_types_post_new = oth_name_types[idx_new_fld_in_oth_name_types+1:]
        if debug: print(u"name_types_post_new: %s" % name_types_post_new)
        for name, unused in name_types_post_new:
            fld_clauses_lst.append(obj_quoter(name))
        fld_clauses = u",\n    ".join(fld_clauses_lst)
        SQL_insert_content = ("INSERT INTO %(tblname)s "
            "\n    SELECT %(fld_clauses)s "
            "\n    FROM %(tmp_tbl)s" % {"tblname": obj_quoter(self.tblname), 
                                  "fld_clauses": fld_clauses,
                                  "tmp_tbl": obj_quoter(mg.TMP_TBL_NAME)})
        print("*"*60)
        print(SQL_insert_content) # worth keeping and not likely to be overdone
        print("*"*60)
        try:
            dd.cur.execute(SQL_insert_content)
        except Exception, e:
            print(SQL_insert_content)
            print(unicode(e))
            self.recover_from_failed_recode()
            raise
        dd.con.commit()
        getdata.force_tbls_refresh()
        SQL_drop_tmp = u"DROP TABLE IF EXISTS %s" % obj_quoter(mg.TMP_TBL_NAME)
        dd.cur.execute(SQL_drop_tmp)
        dd.con.commit()
        dd.set_db(dd.db, tbl=self.tblname) # refresh tbls downwards

    def update_labels(self, fldname, dict_labels):
        """
        Look in vdt file in current project
        """
        try:
            self.val_dics[fldname].update(dict_labels)
        except KeyError:
            self.val_dics[fldname] = dict_labels
        projects.update_vdt(self.var_labels, self.var_notes, self.var_types, 
                            self.val_dics)

    def get_case_when_clause(self, new_fldname, new_fldtype, fldtype, 
                             dict_labels):
        """
        Recoding into new variable with a CASE WHEN SQL syntax clause.
        """
        debug = False
        when_clauses = []
        for orig, new, label in self.recode_clauses_data:
            if debug: print(orig, new, label)
            try:
                orig_clause = process_orig(orig, self.fldname, fldtype)
            except Exception, e:
                wx.MessageBox(_("Problem with your recode configuration. Orig "
                                "error: %s" % e))
                return
            process_label(dict_labels, fldtype, new, label)
            when_clauses.append(make_when_clause(orig_clause, new, new_fldtype))
        case_when_lst = []
        case_when_lst.append(u"    CASE")
        case_when_lst.extend(when_clauses)
        case_when_lst.append(u"        END\n    AS %s" % 
                             obj_quoter(new_fldname))
        case_when = u"\n".join(case_when_lst)
        if debug: 
            pprint.pprint(dict_labels)
            pprint.pprint(case_when)
        return case_when

    def on_recode(self, event):
        """
        Get settings, validate when Recode button clicked, make recoded table, 
            give message that a once-off recode - won't be automatic if new rows 
            added or cells edited.
        """
        debug = False
        fld_idx = self.drop_from.GetSelection()
        new_fldname = self.txt_to.GetValue()
        if not new_fldname:
            wx.MessageBox(_("Please add a new field name"))
            self.txt_to.SetFocus()
            return
        if not dbe_sqlite.valid_name(new_fldname):
            wx.MessageBox(_("Field names can only contain letters, numbers, "
                               "and underscores"))
            return
        # can't already be in use
        if new_fldname in self.fld_names:
            wx.MessageBox(_("Unable to use an existing field name (%s)" % 
                            new_fldname))
            return
        fldtype = self.fld_types[fld_idx]
        self.tabentry.update_settings_data()
        if debug: 
            print(pprint.pformat(self.recode_clauses_data))
            print(self.fldname)
            print(fldtype)
        # get settings (and build labels)
        if not self.recode_clauses_data:
            wx.MessageBox(_("Please add some recode details"))
            return
        dict_labels = {}
        # get field type of recoded values (and thus, new field)
        type_set = set()
        new_vals = [x[1] for x in self.recode_clauses_data]
        for new_val in new_vals:
            lib.update_type_set(type_set, val=new_val)
        new_fldtype = lib.get_overall_fld_type(type_set)
        case_when = self.get_case_when_clause(new_fldname, new_fldtype, fldtype, 
                                              dict_labels)
        oth_name_types = getdata.get_oth_name_types(self.settings_data)
        # insert new field just after the source field
        if self.fldname == mg.SOFA_ID:
            idx_new_fld_in_oth_name_types = 0 # idx in oth_name_types
        else:
            idx_new_fld_in_oth_name_types = \
                        [x[0] for x in oth_name_types].index(self.fldname) + 1
        oth_name_types.insert(idx_new_fld_in_oth_name_types,
                              (new_fldname, new_fldtype))
        if debug: print(oth_name_types)
        try:
            self.recode_tbl(case_when, oth_name_types, 
                            idx_new_fld_in_oth_name_types)
            wx.MessageBox(_("Please Note - this was a once-off recode - it "
                            "won't be applied automatically when new rows are "
                            "added or cells are edited."))
        except Exception, e:
            raise Exception, _("Problem recoding table. Orig error: %s") % e
        self.update_labels(self.fldname, dict_labels)
        self.Destroy()
        self.SetReturnCode(wx.ID_OK)
