import pprint
import random
import sqlite3 as sqlite
import string
import wx

import my_globals as mg
import lib
import config_dlg
import getdata # must be anything referring to plugin modules
import dbe_plugins.dbe_sqlite as dbe_sqlite
import full_html
import projects
import recode
import settings_grid

dd = getdata.get_dd()
cc = config_dlg.get_cc()
obj_quoter = dbe_sqlite.quote_obj

WAITING_MSG = _("<p>Waiting for at least one field to be configured.</p>")

"""
New tables do not have user-defined functions added as part of data type 
    constraints.  Data integrity is protected via the data entry grid and its 
    validation.  Otherwise, only SOFA (or theoretically, any application 
    providing the same user-defined function names) would be able to open it.
Modifying an existing table involves making a tmp table with all the data type 
    constraints added as per new design's field types.  Then data is inserted 
    into table looking for errors.  If no errors, drop orig table, make new 
    table without strict typing, and mass insert all the records from the temp
    table into it.  Then drop the temp table to clean up.
"""


class FldMismatchException(Exception):
    def __init__(self):
        debug = False
        if debug: print("A FldMismatchException")


def has_data_changed(orig_data, final_data):
    """
    The original data is in the form of a list of tuples - the tuples are 
        field name and type.
    The final data is a list of dicts, with keys for:
        mg.TBL_FLD_NAME, 
        mg.TBL_FLD_NAME_ORIG,
        mg.TBL_FLD_TYPE,
        mg.TBL_FLD_TYPE_ORIG.
    Different if TBL_FLD_NAME != TBL_FLD_NAME_ORIG
    Different if TBL_FLD_TYPE != TBL_FLD_TYPE_ORIG
    Different if set of TBL_FLD_NAMEs not same as set of field names. 
    NB Need first two checks in case names swapped.  Sets wouldn't change 
        but data would have changed.
    """
    debug = False
    if debug:
        print("\n%s\n%s" % (pprint.pformat(orig_data), 
                            pprint.pformat(final_data)))
    data_changed = False
    final_fld_names = set()
    for final_dict in final_data:
        final_fld_names.add(final_dict[mg.TBL_FLD_NAME])
        if (final_dict[mg.TBL_FLD_NAME] != final_dict[mg.TBL_FLD_NAME_ORIG] 
            or final_dict[mg.TBL_FLD_TYPE] != final_dict[mg.TBL_FLD_TYPE_ORIG]):
            if debug: print("name or type changed")
            data_changed = True
            break
    # get fld names from orig_data for comparison
    orig_fld_names = set([x[0] for x in orig_data])
    if orig_fld_names != final_fld_names:
        if debug: print("set of field names changed")
        data_changed = True
    return data_changed

def copy_orig_tbl(orig_tbl_name):
    dd.con.commit()
    getdata.force_tbls_refresh()
    SQL_drop_tmp2 = u"DROP TABLE IF EXISTS %s" % obj_quoter(mg.TMP_TBL_NAME2)
    dd.cur.execute(SQL_drop_tmp2)
    dd.con.commit()
    # In SQLite, CREATE TABLE AS drops all constraints, indexes etc.
    SQL_make_copy = u"CREATE TABLE %s AS SELECT * FROM %s" % \
                    (obj_quoter(mg.TMP_TBL_NAME2), obj_quoter(orig_tbl_name))
    dd.cur.execute(SQL_make_copy)
    SQL_restore_index = u"CREATE UNIQUE INDEX sofa_id_idx on %s (%s)" % \
                        (obj_quoter(mg.TMP_TBL_NAME2), obj_quoter(mg.SOFA_ID))
    dd.cur.execute(SQL_restore_index)
    getdata.force_tbls_refresh()

def restore_copy_tbl(orig_tbl_name):
    """
    Will only work if orig tbl already wiped
    """
    dd.con.commit()
    getdata.force_tbls_refresh()
    SQL_rename_tbl = (u"ALTER TABLE %s RENAME TO %s" % 
                      (obj_quoter(mg.TMP_TBL_NAME2), obj_quoter(orig_tbl_name)))
    dd.cur.execute(SQL_rename_tbl)

def wipe_tbl(tblname):
    dd.con.commit()
    getdata.force_tbls_refresh()
    SQL_drop_orig = u"DROP TABLE IF EXISTS %s" % obj_quoter(tblname)
    dd.cur.execute(SQL_drop_orig)
    dd.con.commit()
 
def make_strict_typing_tbl(orig_tbl_name, oth_name_types, fld_settings):
    """
    Make table for purpose of forcing all data into strict type fields.  Not
        necessary to check sofa_id field (autoincremented integer) so not 
        included.
    Will be dropped when making redesigned table.  If not, will
    Make table with all the fields apart from the sofa_id.  The fields
        should be set with strict check constraints so that, even though the
        table is SQLite, it cannot accept inappropriate data.
    Try to insert into strict table all fields in original table (apart from 
        the sofa_id which will be autoincremented from scratch).
    oth_name_types - name, type tuples excluding sofa_id.
    fld_settings -- dict with TBL_FLD_NAME, TBL_FLD_NAME_ORIG, TBL_FLD_TYPE,
        TBL_FLD_TYPE_ORIG. Includes row with sofa_id.
    """
    debug = False
    tmp_name = obj_quoter(mg.TMP_TBL_NAME)
    getdata.reset_con(add_checks=True) # can't deactivate the user-defined 
        # functions until the tmp table has been deleted.
    getdata.force_tbls_refresh()
    SQL_drop_tmp_tbl = u"DROP TABLE IF EXISTS %s" % tmp_name
    dd.cur.execute(SQL_drop_tmp_tbl)
    dd.con.commit()
    # create table with strictly-typed fields
    create_fld_clause = getdata.get_create_flds_txt(oth_name_types, 
                                                    strict_typing=True,
                                                    inc_sofa_id=False)
    SQL_make_tmp_tbl = u"CREATE TABLE %s (%s) " % (tmp_name, 
                                                   create_fld_clause)
    if debug: print(SQL_make_tmp_tbl)
    dd.cur.execute(SQL_make_tmp_tbl)
    # unable to use CREATE ... AS SELECT at same time as defining table.
    # attempt to insert data into strictly-typed fields.
    select_fld_clause = getdata.make_flds_clause(fld_settings)
    SQL_insert_all = u"INSERT INTO %s SELECT %s FROM %s""" % (tmp_name, 
                                                      select_fld_clause, 
                                                      obj_quoter(orig_tbl_name))
    if debug: print(SQL_insert_all)
    dd.cur.execute(SQL_insert_all)
    dd.con.commit()

def make_redesigned_tbl(final_name, oth_name_types):
    """
    Make new table with all the fields from the tmp table (which doesn't 
        have the sofa_id field) plus the sofa_id field.
    Don't want new table to have any constraints which rely on user-defined 
        functions.
    """
    debug = False
    tmp_name = obj_quoter(mg.TMP_TBL_NAME)
    final_name = obj_quoter(final_name)
    create_fld_clause = getdata.get_create_flds_txt(oth_name_types, 
                                                    strict_typing=False,
                                                    inc_sofa_id=True)
    if debug: print(create_fld_clause)
    dd.con.commit()
    if debug:
        print(u"About to drop %s" % final_name)
        SQL_get_tbls = u"""SELECT name 
            FROM sqlite_master 
            WHERE type = 'table'
            ORDER BY name"""
        dd.cur.execute(SQL_get_tbls)
        tbls = [x[0] for x in dd.cur.fetchall()]
        tbls.sort(key=lambda s: s.upper())
        print(tbls)
    getdata.force_tbls_refresh()
    SQL_drop_orig = u"DROP TABLE IF EXISTS %s" % final_name
    dd.cur.execute(SQL_drop_orig)
    dd.con.commit()
    if debug:
        print(u"Supposedly just dropped %s" % final_name)
        SQL_get_tbls = u"""SELECT name 
            FROM sqlite_master 
            WHERE type = 'table'
            ORDER BY name"""
        dd.cur.execute(SQL_get_tbls)
        tbls = [x[0] for x in dd.cur.fetchall()]
        tbls.sort(key=lambda s: s.upper())
        print(tbls)
    SQL_make_redesigned_tbl = u"CREATE TABLE %s (%s)" % (final_name, 
                                                         create_fld_clause)
    dd.cur.execute(SQL_make_redesigned_tbl)
    dd.con.commit()
    oth_names = [obj_quoter(x[0]) for x in oth_name_types]
    null_plus_oth_flds = u" NULL, " + u", ".join(oth_names)
    SQL_insert_all = u"INSERT INTO %s SELECT %s FROM %s""" % (final_name, 
                                                null_plus_oth_flds, tmp_name)
    if debug: print(SQL_insert_all)
    dd.con.commit()
    dd.cur.execute(SQL_insert_all)
    dd.con.commit()
    if debug:
        print(u"About to drop %s" % tmp_name)
        SQL_get_tbls = u"""SELECT name 
            FROM sqlite_master 
            WHERE type = 'table'
            ORDER BY name"""
        dd.cur.execute(SQL_get_tbls)
        tbls = [x[0] for x in dd.cur.fetchall()]
        tbls.sort(key=lambda s: s.upper())
        print(tbls)
    getdata.force_tbls_refresh()
    SQL_drop_tmp = u"DROP TABLE %s" % tmp_name # crucial this happens
    dd.cur.execute(SQL_drop_tmp)
    dd.con.commit()
    if debug:
        print(u"Supposedly just dropped %s" % tmp_name)
        SQL_get_tbls = u"""SELECT name 
            FROM sqlite_master 
            WHERE type = 'table'
            ORDER BY name"""
        dd.cur.execute(SQL_get_tbls)
        tbls = [x[0] for x in dd.cur.fetchall()]
        tbls.sort(key=lambda s: s.upper())
        print(tbls)
    getdata.reset_con(add_checks=False) # should be OK now tmp table gone

def insert_data(row_idx, grid_data):
    """
    Return list of values to display in inserted row.
    Needs to know row index plus already used variable labels (to prevent 
        collisions).
    """
    existing_var_names = [x[0] for x in grid_data]
    next_fld_name = lib.get_next_fld_name(existing_var_names)
    row_data = [next_fld_name, mg.FLD_TYPE_NUMERIC]
    return row_data

def cell_invalidation(val, row, col, grid, col_dets):
    """
    The first column text must be either empty, or 
        alphanumeric (and underscores), and unique (field name) 
        and the second must be empty or from mg.CONF_... e.g. "numeric"
    """
    if col == 0:
        return _invalid_fld_name(row, grid)
    elif col == 1:
        return _invalid_fld_type(row, grid)
    else:
        raise Exception(u"Two many columns for default cell invalidation test")

def cell_response(self, val, row, col, grid, col_dets):
    pass

def _invalid_fld_name(row, grid):
    "Return boolean and string message"
    other_fld_names = []
    for i in range(grid.GetNumberRows()):
        if i == row:
            continue
        other_fld_names.append(grid.GetCellValue(row=i, col=0))
    field_name = grid.GetCellValue(row=row, col=0)
    if field_name.strip() == u"":
        return False, ""
    if not dbe_sqlite.valid_name(field_name):
        msg = _("Field names can only contain letters, numbers, and "
              "underscores")
        return True, msg
    if field_name in other_fld_names:
        msg = _("%s has already been used as a field name") % field_name
        return True, msg
    return False, u""

def _invalid_fld_type(row, grid):
    "Return boolean and string message"
    field_type = grid.GetCellValue(row=row, col=1)
    if field_type.strip() == u"":
        return False, ""
    if field_type not in [mg.FLD_TYPE_NUMERIC, 
                          mg.FLD_TYPE_STRING, 
                          mg.FLD_TYPE_DATE]:
        msg = _("%s is not a valid field type") % field_type
        return True, msg
    return False, u""

def validate_tbl_name(tbl_name, name_ok_to_reuse):
    "Returns boolean plus string message"
    valid_name = dbe_sqlite.valid_name(tbl_name)
    if not valid_name:
        msg = _("You can only use letters, numbers and underscores "
            "in a SOFA name.  Use another name?")
        return False, msg
    if tbl_name == name_ok_to_reuse: # we're just editing an existing table
        duplicate = False
    else:
        duplicate = getdata.dup_tbl_name(tbl_name)
    if duplicate:
        msg = _("Cannot use this name.  A table named \"%s\" already exists in"
                " the default SOFA database") % tbl_name
        return False, msg
    return True, u""


class SafeTblNameValidator(wx.PyValidator):
    def __init__(self, name_ok_to_reuse):
        """
        Not ok to duplicate an existing name unless it is the same table i.e.
            a name ok to reuse.  None if a new table.
        """
        wx.PyValidator.__init__(self)
        self.name_ok_to_reuse = name_ok_to_reuse
        self.Bind(wx.EVT_CHAR, self.on_char)
    
    def Clone(self):
        # wxPython
        return SafeTblNameValidator(self.name_ok_to_reuse)
        
    def Validate(self, win):
        # wxPython
        text_ctrl = self.GetWindow()
        text = text_ctrl.GetValue()
        valid, msg = validate_tbl_name(text, self.name_ok_to_reuse)
        if not valid:
            wx.MessageBox(msg)
            text_ctrl.SetFocus()
            text_ctrl.Refresh()
            return False
        else:
            text_ctrl.Refresh()
            return True
    
    def on_char(self, event):
        # allow backspace and delete (both) etc
        if event.GetKeyCode() in [wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE, 
                                  wx.WXK_BACK, wx.WXK_LEFT, wx.WXK_RIGHT]:
            event.Skip()
            return
        try:
            keycode = chr(event.GetKeyCode())
        except Exception:
            return
        # allow alphanumeric and underscore
        if keycode not in string.letters and keycode not in string.digits \
                and keycode != "_":
            return
        event.Skip()
    
    def TransferToWindow(self):
        # wxPython
        return True
    
    def TransferFromWindow(self):
        # wxPython
        return True

    
class ConfigTableDlg(settings_grid.SettingsEntryDlg):
    
    debug = False
    styles = u"""
        table {
            border-collapse: collapse;
        }
        th {
            margin: 0;
            padding: 9px 6px;
            border-left: solid 1px #c0c0c0;
            border-right: solid 1px #c0c0c0;
            vertical-align: top;
            font-family: Arial, Helvetica, sans-serif;
            font-weight: bold;
            font-size: 14px;
            color: white;
            background-color: #333435;
        }
        td{
            margin: 0;
            padding: 2px 6px;
            border: solid 1px #c0c0c0;
            font-size: 11px;
            color: #5f5f5f; # more clearly just demo data
        }"""
    
    def __init__(self, var_labels, val_dics, tblname_lst, init_fld_settings, 
                 fld_settings, readonly=False, new=False, 
                 insert_data_func=None, cell_invalidation_func=None, 
                 cell_response_func=None):
        """
        tblname_lst -- passed in as a list so changes can be made without 
            having to return anything. 
        init_fld_settings -- list of tuples (tuples must have at least one 
            item, even if only a "rename me").  Empty list ok.
        fld_settings -- add details to it in form of a list of dicts.
        """
        self.new = new
        self.changes_made = False
        if self.new and readonly:
            raise Exception(u"If new, should never be read only")
        self.var_labels = var_labels
        self.val_dics = val_dics
        if tblname_lst:
            name_ok_to_reuse = tblname_lst[0]
        else:
            name_ok_to_reuse = None
        self.tblname_lst = tblname_lst
        # set up new grid data based on data
        self.settings_data = fld_settings # settings_data is more generic and is
            # needed in code which called this.  Don't rename ;-)
        if fld_settings:
            raise Exception(u"fld_settings should always start off empty ready "
                            u"to received values")
        self.init_settings_data = init_fld_settings[:] # can check if end 
            # result changed
        self.setup_settings_data(init_fld_settings)
        self.readonly = readonly
        if not insert_data_func:
            insert_data_func = insert_data
        if not cell_invalidation_func:
            cell_invalidation_func = cell_invalidation
        if not cell_response_func:
            cell_response_func = cell_response
        # col_dets - See under settings_grid.SettingsEntry
        col_dets = [{"col_label": _("Field Name"), 
                     "col_type": settings_grid.COL_STR, 
                     "col_width": 100}, 
                    {"col_label": _("Data Type"), 
                     "col_type": settings_grid.COL_DROPDOWN, 
                     "col_width": 100,
                     "dropdown_vals": [mg.FLD_TYPE_NUMERIC, 
                                       mg.FLD_TYPE_STRING, 
                                       mg.FLD_TYPE_DATE]},
                   ]
        grid_size = (300,250)
        title = _("Configure Data Table")
        if readonly:
            title += _(" (Read Only)")
        wx.Dialog.__init__(self, None, title=title, size=(500,400), 
                           style=wx.RESIZE_BORDER|wx.CAPTION|wx.SYSTEM_MENU)
        self.panel = wx.Panel(self)
        # New controls
        lbl_tbl_label = wx.StaticText(self.panel, -1, _("Table Name:"))
        lbl_tbl_label.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.tblname = tblname_lst[0] if tblname_lst else _("table") + u"001"
        self.txt_tblname = wx.TextCtrl(self.panel, -1, self.tblname, 
                                        size=(450,-1))
        self.txt_tblname.Enable(not self.readonly)
        self.txt_tblname.SetValidator(SafeTblNameValidator(name_ok_to_reuse))
        if not readonly:
            btn_recode = wx.Button(self.panel, -1, _("Recode"))
            btn_recode.Bind(wx.EVT_BUTTON, self.on_recode)
            btn_recode.SetToolTipString(_("Recode values from one field into a "
                                          "new field"))
        # sizers
        self.szr_main = wx.BoxSizer(wx.VERTICAL)
        self.szr_tbl_label = wx.BoxSizer(wx.HORIZONTAL)
        szr_design = wx.BoxSizer(wx.HORIZONTAL)
        szr_design_left = wx.BoxSizer(wx.VERTICAL)
        szr_design_right = wx.BoxSizer(wx.VERTICAL)
        self.szr_tbl_label.Add(lbl_tbl_label, 0, wx.RIGHT, 5)
        self.szr_tbl_label.Add(self.txt_tblname, 0)
        bold = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD)
        design_here_lbl = _("Design Here:") if not self.readonly \
            else _("Design:")
        lbl_design_here = wx.StaticText(self.panel, -1, design_here_lbl)
        lbl_design_here.SetFont(font=bold)
        see_result_lbl = _("See Demonstration Result Here:") \
                            if not self.readonly else _("Demonstration Result:")
        lbl_see_result = wx.StaticText(self.panel, -1, see_result_lbl)
        lbl_see_result.SetFont(font=bold)
        self.html = full_html.FullHTML(panel=self.panel, parent=self, 
                                       size=(500,200))
        szr_design_left.Add(lbl_design_here, 0)
        if not self.readonly:
            lbl_sofa_id = wx.StaticText(self.panel, -1, 
                            _("The sofa_id is required and cannot be edited"))
            szr_design_left.Add(lbl_sofa_id, 0)
        self.tabentry = ConfigTableEntry(self, self.panel, self.readonly, 
                                    grid_size, col_dets, init_fld_settings, 
                                    fld_settings, insert_data_func, 
                                    cell_invalidation_func, cell_response_func)
        szr_design_left.Add(self.tabentry.grid, 1, wx.GROW|wx.ALL, 5)
        szr_design_right.Add(lbl_see_result, 0)
        szr_design_right.Add(self.html, 1, wx.GROW|wx.ALL, 10)
        szr_design.Add(szr_design_left, 0, wx.GROW)
        szr_design.Add(szr_design_right, 1, wx.GROW)
        self.setup_btns(self.readonly)
        self.szr_main.Add(self.szr_tbl_label, 0, wx.GROW|wx.ALL, 10)
        self.szr_main.Add(szr_design, 1, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        self.szr_main.Add(self.szr_btns, 0, wx.GROW|wx.ALL, 10)
        if not readonly:
            self.szr_btns.Insert(2, btn_recode, 0, wx.LEFT, 10)
        self.update_demo()
        self.panel.SetSizer(self.szr_main)
        self.szr_main.SetSizeHints(self)
        self.Layout()
        self.txt_tblname.SetFocus()
    
    def get_demo_val(self, row_idx, col_label, type):
        """
        Get best possible demo value for display in absence of source data.
        """
        val = None
        if col_label.lower() == mg.SOFA_ID:
            val = row_idx + 1
        else:
            try:
                val = random.choice(self.val_dics[col_label])
            except Exception:
                pass
        if val is None:
            val = lib.get_rand_val_of_type(type)
        return val
    
    def get_demo_row_lst(self, row_idx, design_flds_col_labels, 
                         design_flds_types):
        debug = False
        row_lst = []
        label_types = zip(design_flds_col_labels, design_flds_types)
        if debug: print("Label types:\n%s" % label_types)
        for col_label, type in label_types:
            val2use = self.get_demo_val(row_idx, col_label, type)
            row_lst.append(val2use)
        return row_lst
    
    def get_real_demo_data(self, display_n, db_flds_orig_names, 
                           design_flds_orig_names, design_flds_new_names, 
                           design_flds_col_labels, design_flds_types):
        """
        Add as many rows from orig data as possible up to the row limit.
        Fill in rest with demo data.
        """
        debug = False
        obj_quoter = getdata.get_obj_quoter_func(mg.DBE_SQLITE)
        flds_clause = u", ".join([obj_quoter(x) for x in db_flds_orig_names
                                  if x is not None])
        SQL_get_data = u"""SELECT %s FROM %s """ % (flds_clause,
                                            obj_quoter(self.tblname_lst[0]))
        dd.cur.execute(SQL_get_data) # NB won't contain any new or inserted flds
        rows = []
        row_idx = 0
        while True:
            if row_idx >= display_n:
                break # got all we need
            row_obj = dd.cur.fetchone()
            if row_obj is None:
                break # run out of rows
            row_dict = dict(zip(db_flds_orig_names, row_obj))
            if debug:
                print(u"\nRow dicts is \n%s" % pprint.pformat(row_dict)) 
            row_lst = []
            row_dets = zip(design_flds_orig_names, design_flds_new_names, 
                           design_flds_col_labels, design_flds_types)
            if debug: print("Row dets:\n%s" % pprint.pformat(row_dets))
            for orig_fldname, new_fldname, col_label, type in row_dets:
                if orig_fldname is None: # i.e. an inserted or added field
                    rawval = self.get_demo_val(row_idx, col_label, type)
                else:
                    try:
                        rawval = row_dict[orig_fldname]
                    except KeyError:
                        raise Exception(u"orig_fldname %s not in row_dict %s"
                                        % (orig_fldname, row_dict))
                if rawval is None:
                    rawval = mg.MISSING_VAL_INDICATOR
                valdic = self.val_dics.get(new_fldname)
                if valdic:
                    val2use = valdic.get(rawval, rawval)
                else:
                    val2use = rawval
                row_lst.append(val2use)
            rows.append(row_lst)
            row_idx+=1
        while row_idx < display_n:
            row_lst = self.get_demo_row_lst(row_idx, design_flds_col_labels, 
                                            design_flds_types)
            rows.append(row_lst)
            row_idx+=1
        return rows
    
    def update_demo(self):
        """
        Get data from underlying table (if any) as a dict using orig fld names.
        Use this data (or labelled version) if possible, else random according 
            to type.
        """
        debug = False
        if not self.settings_data:
            self.html.show_html(WAITING_MSG)
            return
        if debug: print(self.settings_data)
        # 1) part before the table-specific items e.g. column names and data
        html = [mg.DEFAULT_HDR % (u"Demonstration table", self.styles)]
        html.append(u"<table cellspacing='0'>\n<thead>\n<tr>")
        # 2) the table-specific items (inc column labels)
        # list based on sequence of fields in underlying table
        db_flds_orig_names = [] # will be the key for any dicts taken from db
        # lists based on sequence of fields in (re)design
        design_flds_orig_names = [] # NB will be None for new or inserted flds.
            # Ordered as per list of variables in design.
        design_flds_new_names = []
        design_flds_col_labels = []
        design_flds_types = []
        for data_dict in self.settings_data:
            # all must have same num of elements (even if a None) in same order
            fldname = data_dict[mg.TBL_FLD_NAME]
            design_flds_new_names.append(fldname)
            design_flds_col_labels.append(self.var_labels.get(fldname, 
                                                              fldname.title()))
            design_flds_orig_names.append(data_dict.get(mg.TBL_FLD_NAME_ORIG))
            design_flds_types.append(data_dict[mg.TBL_FLD_TYPE]) 
            if data_dict.get(mg.TBL_FLD_NAME_ORIG) is not None:
                db_flds_orig_names.append(data_dict[mg.TBL_FLD_NAME_ORIG])         
        if debug:
            print(db_flds_orig_names)
            print(design_flds_orig_names)
            print(design_flds_new_names)
            print(design_flds_col_labels)
            print(design_flds_types)
        # column names
        for col_label in design_flds_col_labels:
            html.append(u"<th>%s</th>" % col_label)
        # get data rows (list of lists)
        display_n = 4 # demo rows to display
        if self.new:
            rows = []
            for i in range(display_n):
                row_lst = self.get_demo_row_lst(i, design_flds_col_labels, 
                                                design_flds_types)
                rows.append(row_lst)
        else:
            rows = self.get_real_demo_data(display_n, db_flds_orig_names, 
                                  design_flds_orig_names, design_flds_new_names, 
                                  design_flds_col_labels, design_flds_types)
        # data rows into html
        for row in rows:
            html.append(u"</tr>\n</thead>\n<tbody><tr>")
            for raw_val in row:
                html.append(u"<td>%s</td>" % raw_val)
            html.append(u"</tr>")
        html.append(u"\n</tbody>\n</table></body></html>")
        html2show = u"".join(html)
        self.html.show_html(html2show)
    
    def setup_settings_data(self, data):
        debug = False
        extra = []
        # need to stay pointed to same memory but empty it
        while True:
            try:
                del self.settings_data[0]
            except IndexError:
                break
        for row in data:
            new_row = {mg.TBL_FLD_NAME: row[0], 
                       mg.TBL_FLD_NAME_ORIG: row[0], 
                       mg.TBL_FLD_TYPE: row[1], 
                       mg.TBL_FLD_TYPE_ORIG: row[1]}
            extra.append(new_row)
        self.settings_data += extra
        if debug: print("Initialised settings data: %s" % self.settings_data)
    
    def insert_before(self):
        """
        Overrides SettingsEntryDlg (only part where different is if pos == 0.
        Returns bolinserted, row inserted before (or None if no insertion),
            and row data (or None if no content added). 
        """
        selected_rows = self.tabentry.grid.GetSelectedRows()
        if not selected_rows:
            wx.MessageBox(_("Please select a row first (click to the left of "
                            "the row)"))
            return False, None, None
        pos = selected_rows[0]
        if pos == 0: # for table config only
            wx.MessageBox(_("The %s must always come first") % mg.SOFA_ID)
            return False, None, None
        bolinserted, row_data = self.tabentry.insert_row_above(pos)
        return bolinserted, pos, row_data

    def on_insert(self, event):
        """
        Insert before.
        Overridden so we can update settings_data with details of new row.
        Also need overridden insert_before().
        """
        bolinserted, row_before, row_data = self.insert_before()
        if bolinserted:
            # should be only change
            self.add_new_to_settings(row_before, row_data)
            self.update_demo()
        self.tabentry.grid.SetFocus()
        event.Skip()
    
    def add_new_to_settings(self, row_before, row_data):
        if self.debug: print("Row we inserted before was %s" % row_before)
        # insert new row into settings_data - Nones for original values
        new_row = {mg.TBL_FLD_NAME: row_data[0], 
                   mg.TBL_FLD_NAME_ORIG: None, 
                   mg.TBL_FLD_TYPE: row_data[1], 
                   mg.TBL_FLD_TYPE_ORIG: None}
        self.settings_data.insert(row_before, new_row)
        if self.debug: pprint.pprint(self.settings_data)
            
    def on_delete(self, event):
        "Overridden so we can update settings_data."
        row_del = self.tabentry.try_to_delete_row()
        if row_del is not None:
            if self.debug: print("Row deleted was %s" % row_del)
            # remove row from settings_data.
            del self.settings_data[row_del]
            self.update_demo()
            if self.debug: pprint.pprint(self.settings_data)
        self.tabentry.grid.SetFocus()
        event.Skip()
    
    def make_new_tbl(self):
        """
        Make new table.  Include unique index on special field prepended as
            with data imported.
        Only interested in SQLite when making a fresh SOFA table
        Do not use check constraints (based on user-defined functions) or else 
            only SOFA will be able to open the SQLite database.
        """       
        oth_name_types = getdata.get_oth_name_types(self.settings_data)
        tbl_name = self.tblname_lst[0] 
        getdata.make_sofa_tbl(dd.con, dd.cur, tbl_name, oth_name_types)
        wx.MessageBox(_("Your new table has been added to the default SOFA "
                        "database"))
            
    def modify_tbl(self):
        """
        Make temp table, with strict type enforcement for all fields.  
        Copy across all fields which remain in the original table (possibly 
            with new names and data types) plus add in all the new fields.
        NB SOFA_ID must be autoincrement.
        If any conversion errors (e.g. trying to change a field which 
            currently contains "fred" to a numeric field) abort 
            reconfiguration (with encouragement to fix source data or change
            type to string).
        Assuming reconfiguration is OK, create final table with original 
            table's name, without strict typing, but with an auto-
            incrementing and indexed SOFA_ID.
        Don't apply check constraints based on user-defined functions to
            final table as SQLite Database Browser can't open the database
            anymore.
        """
        debug = False
        orig_tbl_name = dd.tbl
        # other (i.e. not the sofa_id) field details
        oth_name_types = getdata.get_oth_name_types(self.settings_data)
        if debug: print("oth_name_types to feed into make_strict_typing_tbl %s" 
                        % oth_name_types)
        try:
            make_strict_typing_tbl(orig_tbl_name, oth_name_types, 
                                   self.settings_data)
        except sqlite.IntegrityError, e:
            if debug: print(unicode(e))
            dd.con.commit()
            getdata.force_tbls_refresh()
            SQL_drop_tmp_tbl = u"DROP TABLE IF EXISTS %s" % \
                                                obj_quoter(mg.TMP_TBL_NAME)
            dd.cur.execute(SQL_drop_tmp_tbl)
            dd.con.commit()
            raise FldMismatchException
        copy_orig_tbl(orig_tbl_name)
        wipe_tbl(orig_tbl_name)
        final_name = self.tblname_lst[0] # may have been renamed
        try:
            make_redesigned_tbl(final_name, oth_name_types)
        except Exception:
            restore_copy_tbl(orig_tbl_name)
        wipe_tbl(mg.TMP_TBL_NAME2)
        dd.set_db(dd.db, tbl=final_name) # refresh tbls downwards
    
    def make_changes(self):
        debug = False
        if not self.readonly:
            # NB must run Validate on the panel because the objects are 
            # contained by that and not the dialog itself. 
            # http://www.nabble.com/validator-not-in-a-dialog-td23112169.html
            if not self.panel.Validate(): # runs validators on all assoc ctrls
                return True
        if self.tblname_lst: # empty ready to repopulate
            del self.tblname_lst[0]
        tblname = self.txt_tblname.GetValue()
        self.tblname_lst.append(tblname)
        if self.new:
            self.make_new_tbl()
        else:
            if not self.readonly:
                self.modify_tbl()
        dd.set_db(dd.db, tbl=tblname) # refresh tbls downwards
        self.changes_made = True

    def refresh_dlg(self):
        """
        NB never doing this to a read-only table.  So always sofa_id, any other 
            rows, then a new row.
        Need to wipe all rows in the middle then insert fresh ones.
        Also need to update any state information the grid relies on.
        NB typically working on the tabentry object or its grid, not on self.
        """
        self.tabentry.any_editor_shown = False
        self.tabentry.new_editor_shown = False
        # Delete all rows after the first one (sofa_id) and before the new one
        rows2del = self.tabentry.rows_n-2 # less 1st and last
        self.tabentry.grid.DeleteRows(pos=1, numRows=rows2del)
        self.tabentry.grid.HideCellEditControl()
        self.tabentry.grid.ForceRefresh()
        self.tabentry.safe_layout_adjustment()
        # get list of name/type tuples (including sofa_id)
        init_settings_data = getdata.get_init_settings_data(self.tblname)
        self.setup_settings_data(init_settings_data)
        self.tabentry.rows_n = len(init_settings_data) + 1 # + new row
        self.tabentry.rows_to_fill = self.tabentry.rows_n
        # using default renderer and editor fine (text)
        for row_idx, nametype in enumerate(init_settings_data):
            if row_idx == 0:
                continue # sofa_id already there (and blue, read-only etc)
            fldname, fldtype = nametype
            self.tabentry.grid.InsertRows(row_idx, 1)
            self.tabentry.grid.SetCellValue(row_idx, 0, fldname)
            self.tabentry.grid.SetCellValue(row_idx, 1, fldtype)
            self.tabentry.grid.SetRowLabelValue(row_idx, unicode(row_idx+1))
            self.tabentry.grid.ForceRefresh() # deleteme
        # extra config
        self.tabentry.grid.SetRowLabelValue(self.tabentry.rows_n-1, u"*")
        # set cell and record position
        self.tabentry.respond_to_select_cell = False
        row2sel = 0 if self.tabentry.rows_n == 1 else 1
        self.tabentry.current_row_idx = row2sel
        self.tabentry.current_col_idx = 0
        self.tabentry.grid.SetGridCursor(self.tabentry.current_row_idx, 
                                         self.tabentry.current_col_idx)
        # misc
        self.tabentry.grid.ForceRefresh()
        self.update_demo()

    def on_recode(self, event):
        debug = False
        if self.readonly:
            raise Exception(_("Can't recode a read only table"))
        self.tabentry.update_settings_data()
        if debug:
            print(u"init_settings_data: %s" % self.init_settings_data)
            print(self.settings_data)
        # save any changes in table_config dlg first
        tblname_changed = False
        new_tbl = True
        if self.tblname_lst:
            tblname_changed = (self.tblname_lst[0] !=
                               self.txt_tblname.GetValue())
            new_tbl = False
        data_changed = has_data_changed(orig_data=self.init_settings_data, 
                                        final_data=self.settings_data)
        if new_tbl or tblname_changed or data_changed:
            ret = wx.MessageBox(_("You will need to save the changes you made "
                                  "first. Save changes and continue?"),
                                  caption=_("SAVE CHANGES?"), style=wx.YES_NO)
            if ret == wx.YES:
                try:
                    self.tabentry.update_settings_data()
                    self.make_changes() # pre-recode
                    self.init_settings_data = [(x[mg.TBL_FLD_NAME], 
                                                x[mg.TBL_FLD_TYPE]) 
                                                for x in self.settings_data]
                    if debug:
                        print("settings_data coming back after update:") 
                        pprint.pprint(self.settings_data)
                        pprint.pprint(u"init_settings_data after update: %s" % 
                                                        self.init_settings_data)
                except FldMismatchException:
                     wx.MessageBox(_("Unable to modify table. Some data does "
                                     "not match the column type. Please edit "
                                     "and try again."))
                     return
            else:
                return
        tblname = self.tblname_lst[0]
        # open recode dialog
        dlg = recode.RecodeDlg(tblname, self.settings_data)
        ret = dlg.ShowModal()
        if ret == wx.ID_OK: # run recode
            self.refresh_dlg()
            # now that the grid has been updated, we can update settings data 
            # (which does it from the grid)
            self.tabentry.update_settings_data()
            self.init_settings_data = [(x[mg.TBL_FLD_NAME], x[mg.TBL_FLD_TYPE]) 
                                                    for x in self.settings_data]
            if debug:
                print(u"Returned settings_data after recode: %s" % 
                                                            self.settings_data)
                pprint.pprint(u"init_settings_data after recode: %s" % 
                                                        self.init_settings_data)
            
    def on_cancel(self, event):
        """
        Override so can change return value.
        """
        self.Destroy()
        if self.changes_made:
            self.SetReturnCode(mg.RET_CHANGED_DESIGN)
        else:
            self.SetReturnCode(wx.ID_CANCEL)
    
    def on_ok(self, event):
        """
        Override so we can extend to include table name.
        """
        try:
            self.make_changes()
        except FldMismatchException:
             wx.MessageBox(_("Unable to modify table. Some data does not match "
                             "the column type. Please edit and try again."))
             return
        self.Destroy()
        self.SetReturnCode(mg.RET_CHANGED_DESIGN)

    
class ConfigTableEntry(settings_grid.SettingsEntry):
    """
    settings_data should be returned as a list of dicts with the keys:
        mg.TBL_FLD_NAME, etc
    """
    
    def __init__(self, frame, panel, readonly, grid_size, col_dets, 
                 init_settings_data, settings_data, insert_data_func=None, 
                 cell_invalidation_func=None, cell_response_func=None):
        self.frame = frame
        self.readonly = readonly
        force_focus = False
        settings_grid.SettingsEntry.__init__(self, frame, panel, readonly, 
                                   grid_size, col_dets, init_settings_data, 
                                   settings_data, force_focus, insert_data_func, 
                                   cell_invalidation_func, cell_response_func)
        self.debug = False # otherwise set in the parent class ;-)
        self.var_labels, self.var_notes, self.var_types, self.val_dics = \
                                    lib.get_var_dets(cc[mg.CURRENT_VDTS_PATH])
        # disable first row (id in demo tbl; SOFA_ID otherwise)
        attr = wx.grid.GridCellAttr()
        attr.SetReadOnly(True)
        attr.SetBackgroundColour(mg.READONLY_COLOUR)
        self.grid.SetRowAttr(0, attr)
        # allow right click on variable names
        self.grid.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.on_rclick_cell)
    
    def on_rclick_cell(self, event):
        col = event.GetCol()
        if col == 0:
            row = event.GetRow()
            cell_val = self.get_val(row, col)
            choice_item = lib.get_choice_item(self.var_labels, cell_val)
            var_label = lib.get_item_label(self.var_labels, cell_val)
            projects.set_var_props(choice_item, cell_val, var_label, 
                                   self.var_labels, self.var_notes, 
                                   self.var_types, self.val_dics)
    
    def process_cell_move(self, src_ctrl, src_row, src_col, dest_row, dest_col, 
                          direction):
        """
        dest row and col still unknown if from a return or TAB keystroke.
        So is the direction (could be down or down_left if end of line).
        """
        debug = False
        stayed_still, saved_new_row = \
            settings_grid.SettingsEntry.process_cell_move(self, src_ctrl, 
                                src_row, src_col, dest_row, dest_col, direction)
        if self.readonly or stayed_still:
            return
        fld_name = self.grid.GetCellValue(src_row, 0)
        fld_type = self.grid.GetCellValue(src_row, 1)
        if saved_new_row:
            if self.debug or debug: print("Row moved from was %s" % src_row)
            # For row we're leaving, fill in new details.
            # If an existing row, leave original values alone.
            try:
                self.settings_data[src_row][mg.TBL_FLD_NAME] = fld_name
                self.settings_data[src_row][mg.TBL_FLD_TYPE] = fld_type
            except IndexError: # leaving what was the new row
                new_row = {mg.TBL_FLD_NAME: fld_name, 
                           mg.TBL_FLD_NAME_ORIG: None, 
                           mg.TBL_FLD_TYPE: fld_type, 
                           mg.TBL_FLD_TYPE_ORIG: None}
                self.settings_data.append(new_row)
            if self.debug or debug: pprint.pprint(self.settings_data)
            self.frame.update_demo()
        else:
            if src_row == len(self.settings_data):
                # arriving at final row on init
                changed = False
            else:
                try:
                    settings_fldname = \
                                    self.settings_data[src_row][mg.TBL_FLD_NAME]
                    settings_fldtype = \
                                    self.settings_data[src_row][mg.TBL_FLD_TYPE]
                    changed = ((fld_name != settings_fldname) \
                                    or (fld_type != settings_fldtype))
                except IndexError:
                    changed = True
            if changed:
                self.update_settings_data()
                self.frame.update_demo()
            
    def update_settings_data(self):
        """
        Update settings_data.  Overridden so we can include original field 
            details (needed when making new version of the original table).
        Fill in details of fld_names and fld_types (leaving original versions
            untouched). 
        NB do not clear it - only modify.
        """
        debug = False
        grid_data = self.get_grid_data() # only saved data
        if debug: 
            print("grid data: %s" % grid_data)
            print("Original settings data:")
            pprint.pprint(self.settings_data)
        for i, row in enumerate(grid_data):
            if debug: print(row)
            self.settings_data[i][mg.TBL_FLD_NAME] = row[0]
            self.settings_data[i][mg.TBL_FLD_TYPE] = row[1]
        if self.debug or debug:
            print("Final settings data:")
            pprint.pprint(self.settings_data)
    
    def ok_to_delete_row(self, row):
        """
        Overridden settings_grid.SettingsEntry to handle row == 0.
        Should be the same otherwise.
        Can delete any row except the new row or the SOFA_ID row
        Returns boolean and msg.
        """
        if self.is_new_row(row):
            return False, _("Unable to delete new row")
        elif row == 0:
            return False, _("Unable to delete sofa id row")
        elif self.new_is_dirty:
            return False, _("Cannot delete a row while in the middle of making "
                            "a new one")
        else:
            return True, None
        