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

def process_orig(orig, fld_type):
    """
    Turn an orig value into a clause ready for use in an SQL CASE WHEN snippet.
    orig -- a string
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
    if not isinstance(orig, basestring):
        raise Exception, u"process_orig() expects strings"
    orig_clause = None
    # 1 Special
    if orig.strip() == REMAINING:
        orig_clause = u"= TRUE" # i.e. when TRUE
    elif orig.strip() == MISSING:
        orig_clause = u"IS NULL"
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
                orig_clause = u"IS NOT NULL"
            else: # MIN TO b
                orig_clause = u"<= %s" % r_prep
        else:
            if has_max: # a TO MAX
                orig_clause = u">= %s" % l_prep
            else: # a TO b
                orig_clause = u"BETWEEN %s AND %s" % (l_prep, r_prep)
    # 3 Single value
    else:
        if fld_type in (mg.FLD_TYPE_STRING, mg.FLD_TYPE_DATE):
            orig_clause = u"%s" % val_quoter(orig)
        else:
            orig_clause = u"%s" % orig
    if orig_clause is None:
        raise Exception, "Unable to process original value in recode config"
    return orig_clause

def process_label(dict_labels, fld_type, new, label):
    """
    Add label to dictionary of labels for variable
    """
    if fld_type in (mg.FLD_TYPE_STRING, mg.FLD_TYPE_DATE):
        new = val_quoter(new)
    dict_labels[new] = val_quoter(label)


class RecodeDlg(settings_grid.SettingsEntryDlg):
    
    def __init__(self, tblname, config_data):
        """
        tblname -- table containing the variable we are recoding
        config_data -- a list of dicts with the following keys: mg.TBL_FLD_NAME,
            mg.TBL_FLD_NAME_ORIG, mg.TBL_FLD_TYPE, mg.TBL_FLD_TYPE_ORIG.
        """
        self.tblname = tblname
        col_dets = [
                    {"col_label": _("From"), "col_type": settings_grid.COL_STR, 
                     "col_width": 200},
                    {"col_label": _("To"), "col_type": settings_grid.COL_STR, 
                     "col_width": 200},
                    {"col_label": _("Label"), "col_type": settings_grid.COL_STR, 
                     "col_width": 200, "empty_ok": True},
                     ]
        grid_size = (650, 250)
        wx.Dialog.__init__(self, None, title=_("Recode Variable"),
                          size=(700,350), pos=(mg.HORIZ_OFFSET+150,100),
                          style=wx.RESIZE_BORDER|wx.CAPTION|wx.SYSTEM_MENU)
        self.var_labels, self.var_notes, self.var_types, self.val_dics = \
                                    lib.get_var_dets(cc[mg.CURRENT_VDTS_PATH])
        self.panel = wx.Panel(self)
        # New controls
        lbl_from = wx.StaticText(self.panel, -1, _("Recode:"))
        lbl_from.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.config_data = config_data
        # [('string', 'fname', 'fname (string)'), ...]
        # field type is used for validation and constructing recode SQL string
        fld_dets = [(x[mg.TBL_FLD_TYPE], x[mg.TBL_FLD_NAME],
                     u"%s (%s)" % (x[mg.TBL_FLD_NAME], x[mg.TBL_FLD_TYPE])) 
                    for x in self.config_data]
        fld_dets.sort(key=lambda s: s[2].upper()) # needed consistent sorting
        self.fld_types = [x[0] for x in fld_dets]
        self.fld_names = [x[1] for x in fld_dets]
        self.fld_choices = [x[2] for x in fld_dets]
        self.drop_from = wx.Choice(self.panel, -1, choices=self.fld_choices, 
                                   size=(250,-1))
        self.drop_from.Bind(wx.EVT_CONTEXT_MENU, self.on_var_rclick)
        self.drop_from.SetToolTipString(_("Right click to view variable "
                                          "details"))
        lbl_to = wx.StaticText(self.panel, -1, u"To:")
        lbl_to.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.txt_to = wx.TextCtrl(self.panel, -1, size=(250, -1))
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
        dim_share = 2
        data = []
        self.recode_config_data = []
        self.tabentry = settings_grid.SettingsEntry(self, self.panel, 
                                                self.szr_main, dim_share, False, 
                                                grid_size, col_dets, data, 
                                                self.recode_config_data)
        self.szr_main.Add(self.szr_btns, 0, wx.GROW|wx.ALL, 10)
        self.panel.SetSizer(self.szr_main)
        self.szr_main.SetSizeHints(self)
        self.Layout()
        self.drop_from.SetFocus()

    def on_var_rclick(self, event):
        var_idx = self.drop_from.GetSelection()
        var_name = self.fld_names[var_idx]
        var_label = lib.get_item_label(self.var_labels, var_name)
        choice_item = lib.get_choice_item(self.var_labels, var_name)
        updated = projects.set_var_props(choice_item, var_name, var_label, 
                                         self.var_labels, self.var_notes, 
                                         self.var_types, self.val_dics)

    def on_cancel(self, event):
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL)

    def on_help(self, event):
        pass

    def recode_tbl(self, case_when, oth_name_types, idx_orig_fld):
        """
        Build SQL, rename existing to tmp table, mass insert old and new rows 
            into table with orig name, delete tmp table.
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
        if debug: print(SQL_make_recoded_tbl)
        dd.cur.execute(SQL_make_recoded_tbl)
        # want fields before new field, then case when, then any remaining flds
        fld_clauses_lst = []
        fld_clauses_lst.append(u"NULL AS %s" % obj_quoter(mg.SOFA_ID))
        # fldnames from start of other (non sofa_id) fields to before new field 
        # (may be none)
        name_types_pre_new = oth_name_types[: idx_orig_fld+1]
        for name, unused in name_types_pre_new:
            fld_clauses_lst.append(obj_quoter(name))
        fld_clauses_lst.append(case_when)
        # want fields after new field (if any).  Skip 2 (orig fld, recoded fld)
        name_types_post_new = oth_name_types[idx_orig_fld+2:]
        for name, unused in name_types_post_new:
            fld_clauses_lst.append(name)
        fld_clauses = u",\n    ".join(fld_clauses_lst)
        SQL_insert_content = ("INSERT INTO %(tblname)s "
            "\n    SELECT %(fld_clauses)s "
            "\n    FROM %(tmp_tbl)s" % {"tblname": obj_quoter(self.tblname), 
                                  "fld_clauses": fld_clauses,
                                  "tmp_tbl": obj_quoter(mg.TMP_TBL_NAME)})
        if debug: print(SQL_insert_content)
        dd.cur.execute(SQL_insert_content)
        dd.con.commit()
        getdata.force_tbls_refresh()
        SQL_drop_tmp = u"DROP TABLE IF EXISTS %s" % obj_quoter(mg.TMP_TBL_NAME)
        dd.cur.execute(SQL_drop_tmp)
        dd.con.commit()

    def update_labels(self):
        print("*"*60)
        print("update_labels() not implemented yet")
        print("*"*60)

    def on_recode(self, event):
        """
        Get settings, validate when Recode button clicked, make recoded table, 
            give message that a once-off recode - won't be automatic if new rows 
            added or cells edited.
        """
        debug = False
        fld_idx = self.drop_from.GetSelection()
        fldname = self.fld_names[fld_idx]
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
        fld_type = self.fld_types[fld_idx]
        self.tabentry.update_config_data()
        if debug: 
            print(pprint.pformat(self.recode_config_data))
            print(fldname)
            print(fld_type)
        # get settings (and build labels)
        if not self.recode_config_data:
            wx.MessageBox(_("Please add some recode details"))
            return
        when_clauses = []
        dict_labels = {}
        type_set = set()
        new_vals = [x[1] for x in self.recode_config_data]
        for new_val in new_vals:
            lib.update_type_set(type_set, val=new_val)
        new_fld_type = lib.get_overall_fld_type(type_set)
        for orig, new, label in self.recode_config_data:
            print(orig, new, label)
            try:
                orig_clause = process_orig(orig, fld_type)
            except Exception, e:
                wx.MessageBox(_("Problem with your recode configuration. Orig "
                                "error: %s" % e))
                return
            process_label(dict_labels, fld_type, new, label)
            when_clauses.append(make_when_clause(orig_clause, new, 
                                                 new_fld_type))
        case_when_lst = []
        case_when_lst.append(u"    CASE %s " % obj_quoter(fldname))
        case_when_lst.extend(when_clauses)
        case_when_lst.append(u"        END\n    AS %s" % 
                             obj_quoter(new_fldname))
        case_when = u"\n".join(case_when_lst)
        if debug: 
            pprint.pprint(dict_labels)
            pprint.pprint(case_when)
        oth_name_types = getdata.get_oth_name_types(self.config_data)
        # insert new field just after the source field
        if fldname == mg.SOFA_ID:
            idx_orig_fld = 0
        else:
            idx_orig_fld = [x[0] for x in oth_name_types].index(fldname)
        oth_name_types.insert(idx_orig_fld+1,(new_fldname, new_fld_type))
        try:
            self.recode_tbl(case_when, oth_name_types, idx_orig_fld)
            wx.MessageBox(_("Please Note - this was a once-off recode - it "
                            "won't be automatic if new rows are added or cells "
                            "are edited"))
        except Exception, e:
            raise Exception, _("Problem recoding table. Orig error: %s") % e
        self.update_labels()
        self.Destroy()
        self.SetReturnCode(wx.ID_OK)