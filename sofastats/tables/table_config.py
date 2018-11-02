"""
When saving a table, a check is made that the table name is not a duplicate. But
when saving an existing table, it is OK to save the table using that table name.
So a table's existing name is stored in the validator object so we can check
against it. The complication occurs if the user starts with a new table (in
which case existing_name is None) and chooses to recode. The table is saved with
the name entered. It is important that the existing name property of the
validator is changed from None to this new name. After all, saving that table
again at the end of the recode is legitimately overriding an existing table of
that name.  
"""

import pprint
import random
import sqlite3 as sqlite
import string
import wx #@UnusedImport
import wx.grid
import wx.html2

from .. import basic_lib as b
from .. import my_globals as mg
from .. import lib
from .. import config_output
from .. import getdata  ## must be anything referring to plugin modules
from ..dbe_plugins import dbe_sqlite
from .. import output
from .. import recode
from .. import settings_grid

objqtr = dbe_sqlite.quote_obj

def reset_default_dd(tbl=None, add_checks=False):
    """
    Completely reset connection etc with option of changing add_checks setting.
    """
    debug = False
    dd = mg.DATADETS_OBJ
    if debug:
        print(f'Resetting connection to default db. Add_checks: {add_checks}')
    try:
        dd.cur.close()
        dd.con.close()
        dd.set_dbe(dbe=mg.DBE_SQLITE, db=mg.SOFA_DB, tbl=tbl, 
                add_checks=add_checks)  ## Must reset entire dbe to change checks
        if debug:  ## check the connection is still working
            obj_qtr = getdata.get_obj_quoter_func(mg.DBE_SQLITE)
            dd.cur.execute(f'SELECT * FROM {obj_qtr(dd.tbls[0])}')
            print(dd.cur.fetchone())
    except Exception as e:
        raise Exception(f'Problem resetting dd with tbl {tbl}.'
            f'\nCaused by error: {b.ue(e)}')

WAITING_MSG = _('<p>Waiting for at least one field to be configured.</p>')

"""
New tables do not have user-defined functions added as part of data type
constraints. Data integrity is protected via the data entry grid and its
validation. Otherwise, only SOFA (or theoretically, any application providing
the same user-defined function names) would be able to open it.

Modifying an existing table involves making a tmp table with all the data type
constraints added as per new design's field types. Then data is inserted into
table looking for errors. If no errors, drop orig table, make new table without
strict typing, and mass insert all the records from the temp table into it. Then
drop the temp table to clean up.
"""


class FldMismatchException(Exception):
    def __init__(self):
        debug = False
        if debug: print('A FldMismatchException')


def has_data_changed(orig_data, final_data):
    """
    The original data is in the form of a list of tuples - the tuples are field
    name and type.

    The final data is a list of dicts, with keys for:
        mg.TBL_FLDNAME,
        mg.TBL_FLDNAME_ORIG,
        mg.TBL_FLDTYPE,
        mg.TBL_FLDTYPE_ORIG.
    Different if TBL_FLDNAME != TBL_FLDNAME_ORIG
    Different if TBL_FLDTYPE != TBL_FLDTYPE_ORIG
    Different if set of TBL_FLDNAMEs not same as set of field names.
    NB Need first two checks in case names swapped.  Sets wouldn't change but
    data would have changed.
    """
    debug = False
    if debug:
        print(f"\n{pprint.pformat(orig_data)}\n{pprint.pformat(final_data)}")
    data_changed = False
    final_fldnames = set()
    for final_dict in final_data:
        final_fldnames.add(final_dict[mg.TBL_FLDNAME])
        if (final_dict[mg.TBL_FLDNAME] != final_dict[mg.TBL_FLDNAME_ORIG] 
            or final_dict[mg.TBL_FLDTYPE] != final_dict[mg.TBL_FLDTYPE_ORIG]):
            if debug: print('name or type changed')
            data_changed = True
            break
    ## get fld names from orig_data for comparison
    orig_fldnames = set([x[0] for x in orig_data])
    if orig_fldnames != final_fldnames:
        if debug: print('set of field names changed')
        data_changed = True
    return data_changed

def copy_orig_tbl(orig_tblname):
    dd = mg.DATADETS_OBJ
    dd.con.commit()
    getdata.force_sofa_tbls_refresh(sofa_default_db_cur=dd.cur)
    SQL_drop_tmp2 = ('DROP TABLE IF EXISTS '
        f'{getdata.tblname_qtr(mg.DBE_SQLITE, mg.TMP_TBLNAME2)}')
    dd.cur.execute(SQL_drop_tmp2)
    dd.con.commit()
    ## In SQLite, CREATE TABLE AS drops all constraints, indexes etc.
    SQL_make_copy = ('CREATE TABLE '
        f'{getdata.tblname_qtr(mg.DBE_SQLITE, mg.TMP_TBLNAME2)} '
        f'AS SELECT * FROM {getdata.tblname_qtr(mg.DBE_SQLITE, orig_tblname)}')
    dd.cur.execute(SQL_make_copy)
    SQL_restore_index = ('CREATE UNIQUE INDEX sofa_id_idx on '
        f'{getdata.tblname_qtr(mg.DBE_SQLITE, mg.TMP_TBLNAME2)} '
        f'({getdata.tblname_qtr(mg.DBE_SQLITE, mg.SOFA_ID)})')
    try:
        dd.cur.execute(SQL_restore_index)
    except Exception:
        pass  ## Sofa index is already present so OK if not able to remake it
    getdata.force_sofa_tbls_refresh(sofa_default_db_cur=dd.cur)

def restore_copy_tbl(orig_tblname):
    """
    Will only work if orig tbl already wiped
    """
    dd = mg.DATADETS_OBJ
    dd.con.commit()
    getdata.force_sofa_tbls_refresh(sofa_default_db_cur=dd.cur)
    SQL_rename_tbl = ('ALTER TABLE '
        f'{getdata.tblname_qtr(mg.DBE_SQLITE, mg.TMP_TBLNAME2)} RENAME TO '
        f'{getdata.tblname_qtr(mg.DBE_SQLITE, orig_tblname)}')
    dd.cur.execute(SQL_rename_tbl)

def wipe_tbl(tblname):
    dd = mg.DATADETS_OBJ
    dd.con.commit()
    getdata.force_sofa_tbls_refresh(sofa_default_db_cur=dd.cur)
    SQL_drop_orig = ('DROP TABLE IF EXISTS '
        f'{getdata.tblname_qtr(mg.DBE_SQLITE, tblname)}')
    dd.cur.execute(SQL_drop_orig)
    dd.con.commit()

def make_strict_typing_tbl(orig_tblname, oth_name_types, fld_settings):
    """
    Make table for purpose of forcing all data into strict type fields. Not
    necessary to check sofa_id field (autoincremented integer) so not included.

    Will be dropped when making redesigned table. If not, will not be possible
    to interact with database using tools like SQLite Database Browser.

    Make table with all the fields apart from the sofa_id. The fields should be
    set with strict check constraints so that, even though the table is SQLite,
    it cannot accept inappropriate data.

    Try to insert into strict table all fields in original table (apart from the
    sofa_id which will be autoincremented from scratch).

    :param list oth_name_types: name, type tuples excluding sofa_id
    :param dict fld_settings: dict with keys TBL_FLDNAME, TBL_FLDNAME_ORIG,
     TBL_FLDTYPE, TBL_FLDTYPE_ORIG. Includes row with sofa_id.
    """
    debug = False
    dd = mg.DATADETS_OBJ
    if debug: print(f'DBE in make_strict_typing_tbl is: {dd.dbe}')
    reset_default_dd(tbl=orig_tblname, add_checks=True)  ## Can't deactivate the
    ## user-defined functions until the tmp table has been deleted.
    wipe_tbl(mg.STRICT_TMP_TBL)
    ## create table with strictly-typed fields
    create_fld_clause = getdata.get_create_flds_txt(oth_name_types, 
        strict_typing=True, inc_sofa_id=False)
    qtd_tmp_name = getdata.tblname_qtr(mg.DBE_SQLITE, mg.STRICT_TMP_TBL)
    SQL_make_tmp_tbl = f'CREATE TABLE {qtd_tmp_name} ({create_fld_clause}) '
    if debug: print(SQL_make_tmp_tbl)
    dd.cur.execute(SQL_make_tmp_tbl)
    ## unable to use CREATE ... AS SELECT at same time as defining table.
    ## attempt to insert data into strictly-typed fields.
    select_fld_clause = getdata.make_flds_clause(fld_settings)
    SQL_insert_all = (f'INSERT INTO {qtd_tmp_name} SELECT {select_fld_clause} '
        f'FROM {getdata.tblname_qtr(mg.DBE_SQLITE, orig_tblname)}')
    if debug: print(SQL_insert_all)
    dd.cur.execute(SQL_insert_all)
    dd.con.commit()

def strict_cleanup(restore_tblname):
    """
    Must happen one way or another - whether an error or not
    """
    debug = False
    dd = mg.DATADETS_OBJ
    if debug:
        print(f'About to drop {mg.STRICT_TMP_TBL}')
        SQL_get_tbls = """SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name"""
        dd.cur.execute(SQL_get_tbls)
        tbls = [x[0] for x in dd.cur.fetchall()]
        tbls.sort(key=lambda s: s.upper())
        print(tbls)
    wipe_tbl(mg.STRICT_TMP_TBL)
    if debug:
        print(f'Supposedly just dropped {mg.STRICT_TMP_TBL}')
        SQL_get_tbls = """SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name"""
        dd.cur.execute(SQL_get_tbls)
        tbls = [x[0] for x in dd.cur.fetchall()]
        tbls.sort(key=lambda s: s.upper())
        print(tbls)
    reset_default_dd(tbl=restore_tblname, add_checks=False)  ## Should be OK now strict tmp table gone.
    getdata.force_sofa_tbls_refresh(sofa_default_db_cur=dd.cur)

def make_redesigned_tbl(final_name, oth_name_types):
    """
    Make new table with all the fields from the tmp table (which doesn't have
    the sofa_id field) plus the sofa_id field.

    Don't want new table to have any constraints which rely on user-defined
    functions.
    """
    debug = False
    dd = mg.DATADETS_OBJ
    if debug: print(f'DBE in make_redesigned_tbl is: {dd.dbe}')
    tmp_name = getdata.tblname_qtr(mg.DBE_SQLITE, mg.STRICT_TMP_TBL)
    unquoted_final_name = final_name
    final_name = getdata.tblname_qtr(mg.DBE_SQLITE, final_name)
    create_fld_clause = getdata.get_create_flds_txt(oth_name_types, 
        strict_typing=False, inc_sofa_id=True)
    if debug: print(create_fld_clause)
    dd.con.commit()
    if debug:
        print(f'About to drop {final_name}')
        SQL_get_tbls = """SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name"""
        dd.cur.execute(SQL_get_tbls)
        tbls = [x[0] for x in dd.cur.fetchall()]
        tbls.sort(key=lambda s: s.upper())
        print(tbls)
    wipe_tbl(unquoted_final_name)
    if debug:
        print(f'Supposedly just dropped {final_name}')
        SQL_get_tbls = """SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name"""
        dd.cur.execute(SQL_get_tbls)
        tbls = [x[0] for x in dd.cur.fetchall()]
        tbls.sort(key=lambda s: s.upper())
        print(tbls)
    SQL_make_redesigned_tbl = f'CREATE TABLE {final_name} ({create_fld_clause})'
    dd.cur.execute(SQL_make_redesigned_tbl)
    dd.con.commit()
    oth_names = [objqtr(x[0]) for x in oth_name_types]
    null_plus_oth_flds = ' NULL, ' + ', '.join(oth_names)
    SQL_insert_all = (f'INSERT INTO {final_name} SELECT {null_plus_oth_flds} '
        f'FROM {tmp_name}')
    if debug: print(SQL_insert_all)
    dd.con.commit()
    dd.cur.execute(SQL_insert_all)
    dd.con.commit()

def insert_data(grid_data):
    """
    Return list of values to display in inserted row.

    Needs to know row index plus already used variable labels (to prevent
    collisions).
    """
    existing_var_names = [x[0] for x in grid_data]
    next_fldname = lib.get_next_fldname(existing_var_names)
    row_data = [next_fldname, mg.FLDTYPE_NUMERIC_LBL]  ## display label for type
    return row_data

def cell_invalidation(_frame, _val, row, col, grid, _col_dets):
    """
    The first column text must be either empty, or alphanumeric (and
    underscores), and unique (field name) and the second must be empty or from
    mg.CONF_... e.g. "numeric"
    """
    if col == 0:
        return _invalid_fldname(row, grid)
    elif col == 1:
        return _invalid_fldtype(row, grid)
    else:
        raise Exception('Two many columns for default cell invalidation test')

def cell_response(self, val, row, col, grid, col_dets):
    pass

def _invalid_fldname(row, grid):
    "Return boolean and string message"
    other_fldnames = []
    for i in range(grid.GetNumberRows()):
        if i == row:
            continue
        other_fldnames.append(grid.GetCellValue(row=i, col=0))
    field_name = grid.GetCellValue(row=row, col=0)
    if field_name.strip() == '':
        return False, ''
    valid, err = dbe_sqlite.valid_fldname(field_name)
    if not valid:
        msg = _('Field names can only contain letters, numbers, and '
              'underscores.\nOrig error: %s') % err
        return True, msg
    if field_name in other_fldnames:
        msg = _('%s has already been used as a field name') % field_name
        return True, msg
    return False, ''

def _invalid_fldtype(row, grid):
    """
    Return boolean and string message

    References field type label and not key because label is what is in grid.
    """
    field_type = grid.GetCellValue(row=row, col=1)
    if field_type.strip() == '':
        return False, ''
    if field_type not in [mg.FLDTYPE_NUMERIC_LBL, 
            mg.FLDTYPE_STRING_LBL, mg.FLDTYPE_DATE_LBL]:
        msg = _('%s is not a valid field type') % field_type
        return True, msg
    return False, ''

def validate_tblname(tblname, existing_name):
    "Returns boolean plus string message"
    valid, unused = dbe_sqlite.valid_tblname(tblname)
    if ' ' in tblname:
        valid = False  ## to be consistent with importing and direct data entry rules. Now can't sidestep through pasting.
    if not valid:
        msg = _('You can only use letters, numbers and underscores '
            'in a SOFA name.  Use another name?')
        return False, msg
    if tblname == existing_name:  ## we're just editing an existing table
        duplicate = False
    else:
        duplicate = getdata.dup_tblname(tblname)
    if duplicate:
        msg = _("Cannot use this name. A table named \"%s\" already exists in"
            " the default SOFA database") % tblname
        return False, msg
    return True, ''


class SafeTblNameValidator(wx.PyValidator):
    def __init__(self):
        """
        Not ok to duplicate an existing name unless it is the same table i.e. a
        name ok to reuse. None if a new table.
        """
        wx.PyValidator.__init__(self)
        self.Bind(wx.EVT_CHAR, self.on_char)

    def Clone(self):
        ## wxPython
        new_SafeTblNameValidatory = SafeTblNameValidator()
        new_SafeTblNameValidatory.existing_name = self.existing_name
        return new_SafeTblNameValidatory

    def Validate(self, _win):
        ## wxPython
        ## Handle any messages here and here alone
        text_ctrl = self.GetWindow()
        text = text_ctrl.GetValue()
        valid, msg = validate_tblname(text, self.existing_name)  ## existing_name set externally, not passed into object, so we can change it again externally
        if not valid:
            wx.MessageBox(msg)
            text_ctrl.SetFocus()
            text_ctrl.Refresh()
            return False
        else:
            text_ctrl.Refresh()
            return True

    def on_char(self, event):
        ## allow backspace and delete (both) etc
        if event.GetKeyCode() in [wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE, 
                wx.WXK_BACK, wx.WXK_LEFT, wx.WXK_RIGHT]:
            event.Skip()
            return
        try:
            keycode = chr(event.GetKeyCode())
        except Exception:
            return
        ## allow alphanumeric and underscore
        if (keycode not in string.ascii_letters
                and keycode not in string.digits
                and keycode != '_'):
            return
        event.Skip()

    def TransferToWindow(self):
        ## wxPython
        return True

    def TransferFromWindow(self):
        ## wxPython
        return True


class DlgConfigTable(settings_grid.DlgSettingsEntry):

    debug = False
    styles = """
        table {
            border-collapse: collapse;
        }
        th {
            margin: 0;
            padding: 9px 6px;
            border-left: solid 1px #c0c0c0;
            border-right: solid 1px #c0c0c0;
            vertical-align: top;
            font-family: Ubuntu, Helvetica, Arial, sans-serif;
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
            fld_settings, *, read_only=False, new=False, insert_data_func=None,
            cell_invalidation_func=None, cell_response_func=None):
        """
        :param list tblname_lst: passed in as a list so changes can be made
         without having to return anything.
        :param list init_fld_settings: list of tuples (tuples must have at least
         one item, even if only a "rename me"). Empty list ok.
        :param list fld_settings: add details to it in form of a list of dicts
        """
        self.exiting = False
        self.new = new
        self.changes_made = False
        self.read_only = read_only
        self.exiting = False
        if self.new and self.read_only:
            raise Exception('If new, should never be read only')
        self.var_labels = var_labels
        self.val_dics = val_dics
        if tblname_lst:
            existing_name = tblname_lst[0]
        else:
            existing_name = None
        self.tblname_lst = tblname_lst
        ## set up new grid data based on data
        self.settings_data = fld_settings  ## settings_data is more generic and
            ## is needed in code which called this.  Don't rename ;-)
        if fld_settings:
            raise Exception('fld_settings should always start off empty ready '
                'to receive values')
        self.init_settings_data = init_fld_settings[:]  ## can check if end
            ## result changed
        self.setup_settings_data(init_fld_settings)
        if not insert_data_func:
            insert_data_func = insert_data
        if not cell_invalidation_func:
            cell_invalidation_func = cell_invalidation
        if not cell_response_func:
            cell_response_func = cell_response
        ## col_dets - See under settings_grid.SettingsEntry
        col_dets = [{'col_label': _('Field Name'),
             'coltype': settings_grid.COL_STR,
             'colwidth': 100},
            {'col_label': _('Data Type'),
             'coltype': settings_grid.COL_DROPDOWN,
             'colwidth': 100,
             'dropdown_vals': [mg.FLDTYPE_NUMERIC_LBL, mg.FLDTYPE_STRING_LBL,
                mg.FLDTYPE_DATE_LBL]},
        ]
        grid_size = (300, 250)
        title = _('Configure Data Table')
        if self.read_only:
            title += _(' (Read Only)')
        wx.Dialog.__init__(self, None, title=title, size=(500, 400),
            style=wx.RESIZE_BORDER|wx.CAPTION|wx.SYSTEM_MENU)
        self.panel = wx.Panel(self)
        ## New controls
        lbl_tbl_label = wx.StaticText(self.panel, -1, _('Table Name:'))
        lbl_tbl_label.SetFont(mg.LABEL_FONT)
        self.tblname = tblname_lst[0] if tblname_lst else _('table') + '001'
        self.txt_tblname = wx.TextCtrl(
            self.panel, -1, self.tblname, size=(450, -1))
        self.txt_tblname.Enable(not self.read_only)
        self.tblname_validator = SafeTblNameValidator()
        self.tblname_validator.existing_name = existing_name  ## need to be able to change this class property from outside e.g. if we save the table when we recode it.
        self.txt_tblname.SetValidator(self.tblname_validator)
        if not self.read_only:
            btn_recode = wx.Button(self.panel, -1, _('Recode'))
            btn_recode.Bind(wx.EVT_BUTTON, self.on_recode)
            btn_recode.SetToolTip(
                _('Recode values from one field into a new field'))
        ## sizers
        self.szr_main = wx.BoxSizer(wx.VERTICAL)
        self.szr_tbl_label = wx.BoxSizer(wx.HORIZONTAL)
        szr_design = wx.BoxSizer(wx.HORIZONTAL)
        szr_design_left = wx.BoxSizer(wx.VERTICAL)
        szr_design_right = wx.BoxSizer(wx.VERTICAL)
        self.szr_tbl_label.Add(lbl_tbl_label, 0, wx.RIGHT, 5)
        self.szr_tbl_label.Add(self.txt_tblname, 0)
        design_here_lbl = (_('Design Here:') if not self.read_only
            else _('Design:'))
        lbl_design_here = wx.StaticText(self.panel, -1, design_here_lbl)
        lbl_design_here.SetFont(mg.LABEL_FONT)
        see_result_lbl = (_('See Demonstration Result Here:')
            if not self.read_only else _('Demonstration Result:'))
        lbl_see_result = wx.StaticText(self.panel, -1, see_result_lbl)
        lbl_see_result.SetFont(mg.LABEL_FONT)
        self.html = wx.html2.WebView.New(self.panel, -1, size=wx.Size(500, 200))
        if mg.PLATFORM == mg.MAC:
            self.html.Bind(wx.EVT_WINDOW_CREATE, self.on_show)
        else:
            self.Bind(wx.EVT_SHOW, self.on_show)
        szr_design_left.Add(lbl_design_here, 0)
        if not self.read_only:
            lbl_guidance = wx.StaticText(self.panel, -1,
                _("If you're new to designing data structures,"
                '\nit may help to look at the data structure '
                '\npage of www.sofastatistics.com/userguide.php'
                '\n\nNote - the sofa_id is required and cannot be edited.'))
            szr_design_left.Add(lbl_guidance, 0)
        self.tabentry = ConfigTableEntry(self, self.panel,
            grid_size, col_dets, init_fld_settings, fld_settings,
            insert_data_func, cell_invalidation_func, cell_response_func,
            read_only=self.read_only)
        szr_design_left.Add(self.tabentry.grid, 1, wx.GROW|wx.ALL, 5)
        szr_design_right.Add(lbl_see_result, 0)
        szr_design_right.Add(self.html, 1, wx.GROW|wx.ALL, 10)
        szr_design.Add(szr_design_left, 0, wx.GROW)
        szr_design.Add(szr_design_right, 1, wx.GROW)
        self.setup_btns(read_only=self.read_only)
        self.szr_main.Add(self.szr_tbl_label, 0, wx.GROW|wx.ALL, 10)
        self.szr_main.Add(szr_design, 1, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        self.szr_main.Add(self.szr_btns, 0, wx.GROW|wx.ALL, 10)
        if not self.read_only:
            self.szr_btns.Insert(2, btn_recode, 0, wx.LEFT, 10)
        self.panel.SetSizer(self.szr_main)
        self.szr_main.SetSizeHints(self)
        self.Layout()
        self.txt_tblname.SetFocus()

    def on_show(self, _event):
        if self.exiting:
            return
        self.update_demo()

    def get_demo_val(self, row_idx, col_label, lbl_type_key):
        """
        Get best possible demo value for display in absence of source data.
        """
        if col_label.lower() == mg.SOFA_ID:
            val = row_idx + 1
        else:
            try:
                val = random.choice(self.val_dics[col_label])
            except Exception:
                val = lib.get_rand_val_of_type(lbl_type_key)
        return val

    def get_demo_row_lst(self,
            row_idx, design_flds_col_labels, design_flds_types):
        """
        Using label not key because displaying field type.
        """
        debug = False
        row_lst = []
        label_types = zip(design_flds_col_labels, design_flds_types)
        if debug: print(f'Label types:\n{label_types}')
        for col_label, lbl_type in label_types:
            lbl_type_key = mg.FLDTYPE_LBL2KEY[lbl_type]
            val2use = self.get_demo_val(row_idx, col_label, lbl_type_key)
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
        dd = mg.DATADETS_OBJ
        orig_tblname = self.tblname_lst[0]
        flds_clause = ', '.join([objqtr(x) for x in db_flds_orig_names
            if x is not None])
        if debug: print('flds_clause', flds_clause)
        tblname = getdata.tblname_qtr(mg.DBE_SQLITE, orig_tblname)
        SQL_get_data = f'SELECT {flds_clause} FROM {tblname} '
        if debug: print('SQL_get_data', SQL_get_data)
        dd.cur.execute(SQL_get_data)  ## NB won't contain any new or inserted flds
        rows = []
        row_idx = 0
        while True:
            if row_idx >= display_n:
                ## refreshing cursor prevents table lock for some reason
                dd.cur.close()
                dd.cur = dd.con.cursor()
                break  ## got all we need
            row_obj = dd.cur.fetchone()
            if row_obj is None:
                break  ## run out of rows
            row_dict = dict(zip(db_flds_orig_names, row_obj))
            if debug:
                row_dict_str = pprint.pformat(row_dict)
                print(f'\nRow dicts is \n{row_dict_str}') 
            row_lst = []
            row_dets = zip(design_flds_orig_names, design_flds_new_names,
                design_flds_col_labels, design_flds_types)
            if debug: print(f'Row dets:\n{pprint.pformat(row_dets)}')
            for orig_fldname, new_fldname, col_label, lbl_type in row_dets:
                if orig_fldname is None:  ## i.e. an inserted or added field
                    lbl_type_key = mg.FLDTYPE_LBL2KEY[lbl_type]
                    rawval = self.get_demo_val(row_idx, col_label, lbl_type_key)
                else:
                    try:
                        rawval = row_dict[orig_fldname]
                    except KeyError:
                        raise Exception(f'orig_fldname {orig_fldname} not in '
                            f'row_dict {row_dict}')
                if rawval is None:
                    rawval = mg.MISSING_VAL_INDICATOR
                valdic = self.val_dics.get(new_fldname)
                if valdic:
                    val2use = valdic.get(rawval, rawval)
                else:
                    val2use = rawval
                row_lst.append(val2use)
            rows.append(row_lst)
            row_idx += 1
        while row_idx < display_n:
            row_lst = self.get_demo_row_lst(
                row_idx, design_flds_col_labels, design_flds_types)
            rows.append(row_lst)
            row_idx += 1
        return rows

    def update_demo(self):
        """
        Get data from underlying table (if any) as a dict using orig fld names.

        Use this data (or labelled version) if possible, else random according
        to type.
        """
        debug = False
        if not self.settings_data:
            self.html.SetPage(WAITING_MSG, mg.BASE_URL)
            return
        if debug: print(self.settings_data)
        ## 1) part before the table-specific items e.g. column names and data
        html = [mg.DEFAULT_HDR % {'title': 'Demonstration table',
            'css': self.styles, 'dojo_insert': ''}]
        html.append("<table cellspacing='0'>\n<thead>\n<tr>")
        ## 2) the table-specific items (inc column labels)
        ## list based on sequence of fields in underlying table
        db_flds_orig_names = []  ## will be the key for any dicts taken from db
        ## lists based on sequence of fields in (re)design
        design_flds_orig_names = []  ## NB will be None for new or inserted flds.
            ## Ordered as per list of variables in design.
        design_flds_new_names = []
        design_flds_col_labels = []
        design_flds_types = []
        for data_dict in self.settings_data:
            ## all must have same num of elements (even if a None) in same order
            fldname = data_dict[mg.TBL_FLDNAME]
            design_flds_new_names.append(fldname)
            design_flds_col_labels.append(
                self.var_labels.get(fldname, fldname.title()))
            design_flds_orig_names.append(data_dict.get(mg.TBL_FLDNAME_ORIG))
            design_flds_types.append(data_dict[mg.TBL_FLDTYPE]) 
            if data_dict.get(mg.TBL_FLDNAME_ORIG) is not None:
                db_flds_orig_names.append(data_dict[mg.TBL_FLDNAME_ORIG])         
        if debug:
            print(db_flds_orig_names)
            print(design_flds_orig_names)
            print(design_flds_new_names)
            print(design_flds_col_labels)
            print(design_flds_types)
        ## column names
        for col_label in design_flds_col_labels:
            html.append(f'<th>{col_label}</th>')
        ## get data rows (list of lists)
        display_n = 4  ## demo rows to display
        if self.new:
            rows = []
            for i in range(display_n):
                row_lst = self.get_demo_row_lst(
                    i, design_flds_col_labels, design_flds_types)
                rows.append(row_lst)
        else:
            rows = self.get_real_demo_data(display_n, db_flds_orig_names,
                design_flds_orig_names, design_flds_new_names,
                design_flds_col_labels, design_flds_types)
        ## data rows into html
        for row in rows:
            html.append('</tr>\n</thead>\n<tbody><tr>')
            for raw_val in row:
                html.append(f'<td>{raw_val}</td>')
            html.append('</tr>')
        html.append('\n</tbody>\n</table></body></html>')
        html2show = ''.join(html)
        self.html.SetPage(html2show, mg.BASE_URL)

    def setup_settings_data(self, data):
        debug = False
        extra = []
        ## need to stay pointed to same memory but empty it
        while True:
            try:
                del self.settings_data[0]
            except IndexError:
                break
        for fldname, fldtype in data:
            new_row = {
                mg.TBL_FLDNAME: fldname, mg.TBL_FLDNAME_ORIG: fldname,
                mg.TBL_FLDTYPE: fldtype, mg.TBL_FLDTYPE_ORIG: fldtype}
            extra.append(new_row)
        self.settings_data += extra
        if debug: print(f'Initialised settings data: {self.settings_data}')

    def insert_before(self):
        """
        Overrides DlgSettingsEntry (only part where different is if pos == 0.

        Returns bolinserted, row inserted before (or None if no insertion),
        and row data (or None if no content added). 
        """
        selected_rows = self.tabentry.grid.GetSelectedRows()
        if not selected_rows:
            wx.MessageBox(
                _('Please select a row first (click to the left of the row)'))
            return False, None, None
        pos = selected_rows[0]
        if pos == 0:  ## for table config only
            wx.MessageBox(_('The %s must always come first') % mg.SOFA_ID)
            return False, None, None
        bolinserted, row_data = self.tabentry.insert_row_above(pos)
        return bolinserted, pos, row_data

    def on_insert(self, event):
        """
        Insert before.

        Overridden so we can update settings_data with details of new row.

        Also need overridden insert_before().
        """
        bolinserted, row_before, (fldname, fldtype) = self.insert_before()
        if bolinserted:
            ## should be only change
            self.add_new_to_settings(row_before, fldname, fldtype)
            self.update_demo()
        self.tabentry.grid.SetFocus()
        event.Skip()

    def add_new_to_settings(self, row_before, fldname, fldtype):
        if self.debug: print(f'Row we inserted before was {row_before}')
        ## insert new row into settings_data - Nones for original values
        new_row = {
            mg.TBL_FLDNAME: fldname, mg.TBL_FLDNAME_ORIG: None,
            mg.TBL_FLDTYPE: fldtype, mg.TBL_FLDTYPE_ORIG: None}
        self.settings_data.insert(row_before, new_row)
        if self.debug: pprint.pprint(self.settings_data)

    def make_new_tbl(self):
        """
        Make new table. Include unique index on special field prepended as with
        data imported.

        Only interested in SQLite when making a fresh SOFA table

        Do not use check constraints (based on user-defined functions) or else
        only SOFA will be able to open the SQLite database.
        """
        debug = False
        dd = mg.DATADETS_OBJ
        oth_name_types = getdata.get_oth_name_types(self.settings_data)
        tblname = self.tblname_lst[0]
        if debug: print(f'DBE in make_new_tbl is: {dd.dbe}')
        getdata.make_sofa_tbl(
            dd.con, dd.cur, tblname, oth_name_types, headless=False)
        wx.MessageBox(
            _('Your new table has been added to the default SOFA database'))

    def modify_tbl(self):
        """
        Make temp table, with strict type enforcement for all fields.

        Copy across all fields which remain in the original table (possibly with
        new names and data types) plus add in all the new fields.

        NB SOFA_ID must be autoincrement.

        If any conversion errors (e.g. trying to change a field which currently
        contains "fred" to a numeric field) abort reconfiguration (with
        encouragement to fix source data or change type to string). Wipe strict
        tmp table and refresh everything.

        Assuming reconfiguration is OK, create final table with original table's
        name, without strict typing, but with an auto-incrementing and indexed
        SOFA_ID.

        Don't apply check constraints based on user-defined functions to final
        table as SQLite Database Browser can't open the database anymore.
        """
        debug = False
        dd = mg.DATADETS_OBJ
        orig_tblname = dd.tbl
        ## other (i.e. not the sofa_id) field details
        oth_name_types = getdata.get_oth_name_types(self.settings_data)
        if debug:
            print('oth_name_types to feed into '
                f'make_strict_typing_tbl {oth_name_types}')
        try:  ## 1 way or other must do strict_cleanup()
            make_strict_typing_tbl(
                orig_tblname, oth_name_types, self.settings_data)
        except sqlite.IntegrityError as e: #@UndefinedVariable
            if debug: print(b.ue(e))
            strict_cleanup(restore_tblname=orig_tblname)
            raise FldMismatchException
        except Exception as e:
            strict_cleanup(restore_tblname=orig_tblname)
            raise Exception('Problem making strictly-typed table.'
                f'\nCaused by error: {b.ue(e)}')
        copy_orig_tbl(orig_tblname)
        wipe_tbl(orig_tblname)
        final_name = self.tblname_lst[0]  ## may have been renamed
        try:
            make_redesigned_tbl(final_name, oth_name_types)
            strict_cleanup(restore_tblname=final_name)
            dd.set_tbl(tbl=final_name)
        except Exception as e:
            strict_cleanup(restore_tblname=orig_tblname)
            restore_copy_tbl(orig_tblname)  ## effectively removes tmp_tbl 2
            dd.set_tbl(tbl=orig_tblname)
            raise Exception('Problem making redesigned table.'
                f'\nCaused by error: {b.ue(e)}')
        wipe_tbl(mg.TMP_TBLNAME2)

    def make_changes(self):
        """
        The table name with the details we want will either be the new table
        (only possible after made of course) or if an existing table, the
        original name.
        """
        dd = mg.DATADETS_OBJ
        if not self.read_only:
            ## NB must run Validate on the panel because the objects are
            ## contained by that and not the dialog itself.
            ## http://www.nabble.com/validator-not-in-a-dialog-td23112169.html
            if not self.panel.Validate():  ## runs validators on all assoc ctrls
                raise Exception(_('Invalid table design.'))
        gui_tblname = self.txt_tblname.GetValue()
        if self.new:
            try:
                del self.tblname_lst[0]  ## empty ready to repopulate
            except Exception:
                pass  ## OK to fail to delete item in list if already empty
            self.tblname_lst.append(gui_tblname)
            self.make_new_tbl()
            dd.set_tbl(tbl=gui_tblname)
        else:
            if not self.read_only:
                orig_tblname = self.tblname_lst[0]
                del self.tblname_lst[0]  ## empty ready to repopulate
                self.tblname_lst.append(gui_tblname)
                dd.set_tbl(tbl=orig_tblname)  ## The new one hasn't hit the database yet
                self.modify_tbl()
        self.changes_made = True

    def refresh_dlg(self):
        """
        NB never doing this to a read-only table. So always sofa_id, any other
        rows, then a new row.

        Called by recode because it is the only thing which changes the
        underlying data table prior to Update.

        Need to wipe all rows in the middle then insert fresh ones.

        Also need to update any state information the grid relies on.

        NB typically working on the tabentry object or its grid, not on self.
        """
        dd = mg.DATADETS_OBJ
        self.tabentry.any_editor_shown = False
        self.tabentry.new_editor_shown = False
        ## Delete all rows after the first one (sofa_id) and before the new one
        rows2del = self.tabentry.rows_n-2  ## less 1st and last
        self.tabentry.grid.DeleteRows(pos=1, numRows=rows2del)
        self.tabentry.grid.HideCellEditControl()
        self.tabentry.grid.ForceRefresh()
        self.tabentry.safe_layout_adjustment()
        ## get list of name/type tuples (including sofa_id)
        init_settings_data = getdata.get_init_settings_data(dd, self.tblname)
        self.setup_settings_data(init_settings_data)
        self.tabentry.rows_n = len(init_settings_data) + 1  ## + new row
        self.tabentry.rows_to_fill = self.tabentry.rows_n
        ## using default renderer and editor fine (text)
        for row_idx, nametype in enumerate(init_settings_data):
            if row_idx == 0:
                continue  ## sofa_id already there (and blue, read-only etc)
            fldname, fldtype = nametype
            self.tabentry.grid.InsertRows(row_idx, 1)
            self.tabentry.grid.SetCellValue(row_idx, 0, fldname)
            self.tabentry.grid.SetCellValue(row_idx, 1, fldtype)
            self.tabentry.grid.SetRowLabelValue(row_idx, str(row_idx+1))
            self.tabentry.grid.ForceRefresh()  ## deleteme
        ## extra config
        self.tabentry.grid.SetRowLabelValue(
            self.tabentry.rows_n-1, mg.NEW_IS_READY)
        ## set cell and record position
        self.tabentry.respond_to_select_cell = False
        row2sel = 0 if self.tabentry.rows_n == 1 else 1
        self.tabentry.current_row_idx = row2sel
        self.tabentry.current_col_idx = 0
        self.tabentry.grid.SetGridCursor(self.tabentry.current_row_idx, 
            self.tabentry.current_col_idx)
        ## misc
        self.tabentry.grid.ForceRefresh()
        self.update_demo()

    def get_change_status(self):
        tblname_changed = False
        new_tbl = True
        if self.tblname_lst:
            tblname_changed = (
                self.tblname_lst[0] != self.txt_tblname.GetValue())
            new_tbl = False
        data_changed = has_data_changed(orig_data=self.init_settings_data,
            final_data=self.settings_data)
        return new_tbl, tblname_changed, data_changed

    def on_recode(self, _event):
        debug = False
        if self.read_only:
            raise Exception(_("Can't recode a read only table"))
        self.tabentry.update_settings_data()
        if debug:
            print(f'init_settings_data: {self.init_settings_data}')
            print(self.settings_data)
        ## save any changes in table_config dlg first
        new_tbl, tblname_changed, data_changed = self.get_change_status()
        if new_tbl or tblname_changed or data_changed:
            ret = wx.MessageBox(_('You will need to save the changes you made '
                'first. Save changes and continue?'), 
                caption=_('SAVE CHANGES?'), style=wx.YES_NO)
            if ret == wx.YES:
                try:
                    self.tabentry.update_settings_data()
                    self.make_changes()  ## pre-recode
                    self.init_settings_data = [(x[mg.TBL_FLDNAME],
                        x[mg.TBL_FLDTYPE]) for x in self.settings_data]
                    if debug:
                        print('settings_data coming back after update:')
                        pprint.pprint(self.settings_data)
                        pprint.pprint('init_settings_data after '
                            f'update: {self.init_settings_data}')
                except FldMismatchException:
                    wx.MessageBox(
                        _('Unable to modify table. Some data does not match the'
                        ' column type. Please edit and try again.'))
                    return
                except Exception as e:
                    wx.MessageBox(
                        _('Unable to modify table.\nCaused by error: %s')
                        % b.ue(e))
                    return
            else:
                return
        tblname = self.tblname_lst[0]
        self.tblname_validator.existing_name = tblname  ## otherwise, won't let us use this name if we started a new table, gave it a tentative name, and then saved it as the prerequisite for recoding it
        dlg = recode.DlgRecode(tblname, self.settings_data)
        ret = dlg.ShowModal()
        if ret == wx.ID_OK:  ## run recode
            self.changes_made = True
            self.refresh_dlg()
            ## Now that the grid has been updated, we can update settings data
            ## (which does it from the grid).
            self.tabentry.update_settings_data()
            self.init_settings_data = [(x[mg.TBL_FLDNAME], x[mg.TBL_FLDTYPE]) 
                for x in self.settings_data]
            if debug:
                print('Returned settings_data after '
                    f'recode: {self.settings_data}')
                pprint.pprint('init_settings_data after '
                    f'recode: {self.init_settings_data}')

    def on_cancel(self, _event):
        """
        Override so can change return value.
        """
        self.Destroy()
        if self.changes_made:
            self.SetReturnCode(mg.RET_CHANGED_DESIGN)
        else:
            self.SetReturnCode(wx.ID_CANCEL)

    def on_ok(self, _event):
        """
        Override so we can extend to include table name.
        """
        dd = mg.DATADETS_OBJ
        if self.read_only:
            self.exiting = True
            self.Destroy()
        else:
            ## NB any changes defined in recode are already done
            new_tbl, tblname_changed, data_changed = self.get_change_status()
            if new_tbl or tblname_changed or data_changed:
                try:
                    if not new_tbl:
                        orig_tblname = self.tblname_lst[0]
                        dd.set_tbl(tbl=orig_tblname)
                    else:
                        dd.set_tbl(tbl=None)
                    self.make_changes()
                    self.exiting = True
                    self.Destroy()
                    self.SetReturnCode(mg.RET_CHANGED_DESIGN)
                except FldMismatchException:
                    wx.MessageBox(
                        _('Unable to modify table. Some data does not match the'
                        ' column type. Please edit and try again.'))
                    return
                except Exception as e:
                    wx.MessageBox(
                        _("Unable to modify table.\nCaused by error: %s")
                        % b.ue(e))
                    return
            elif self.changes_made:  ## not in tableconf. Must've been in recoding
                self.exiting = True
                self.Destroy()
                self.SetReturnCode(mg.RET_CHANGED_DESIGN)
                return
            else:
                wx.MessageBox(_('No changes to update.'))
                return


class ConfigTableEntry(settings_grid.SettingsEntry):
    """
    settings_data should be returned as a list of dicts with the keys:
    mg.TBL_FLDNAME, etc
    """

    def __init__(self, frame, panel, grid_size, col_dets,
            init_settings_data, settings_data, insert_data_func=None,
            cell_invalidation_func=None, cell_response_func=None, *,
            read_only=False):
        cc = output.get_cc()
        self.frame = frame
        self.read_only = read_only
        settings_grid.SettingsEntry.__init__(self, frame, panel,
            grid_size, col_dets, init_settings_data, settings_data,
            insert_data_func, cell_invalidation_func, cell_response_func,
            read_only=read_only, force_focus=False)
        self.debug = False  ## otherwise set in the parent class ;-)
        (self.var_labels, self.var_notes, self.var_types,
         self.val_dics) = lib.get_var_dets(cc[mg.CURRENT_VDTS_PATH])
        ## disable first row (id in demo tbl; SOFA_ID otherwise)
        attr = wx.grid.GridCellAttr()
        attr.SetReadOnly(True)
        attr.SetBackgroundColour(mg.READ_ONLY_COLOUR)
        self.grid.SetRowAttr(0, attr)
        ## allow right click on variable names
        self.grid.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.on_rclick_cell)

    def on_rclick_cell(self, event):
        col = event.GetCol()
        if col == 0:
            row = event.GetRow()
            cell_val = self.get_val(row, col)
            choice_item = lib.GuiLib.get_choice_item(self.var_labels, cell_val)
            var_label = lib.GuiLib.get_item_label(self.var_labels, cell_val)
            config_output.set_var_props(choice_item, cell_val, var_label,
                self.var_labels, self.var_notes, self.var_types, self.val_dics)

    def process_cell_move(self, src_ctrl,
            src_row, src_col,
            dest_row, dest_col,
            direction):
        """
        dest row and col still unknown if from a return or TAB keystroke.
        So is the direction (could be down or down_left if end of line).
        """
        debug = False
        (stayed_still,
         saved_new_row) = settings_grid.SettingsEntry.process_cell_move(self,
                    src_ctrl, src_row, src_col, dest_row, dest_col, direction)
        if self.read_only or stayed_still:
            return
        fldname = self.grid.GetCellValue(src_row, 0)
        fldtype = self.grid.GetCellValue(src_row, 1)
        if saved_new_row:
            if self.debug or debug: print(f'Row moved from was {src_row}')
            ## For row we're leaving, fill in new details.
            ## If an existing row, leave original values alone.
            try:
                self.settings_data[src_row][mg.TBL_FLDNAME] = fldname
                self.settings_data[src_row][mg.TBL_FLDTYPE] = fldtype
            except IndexError:  ## leaving what was the new row
                new_row = {
                    mg.TBL_FLDNAME: fldname, mg.TBL_FLDNAME_ORIG: None,
                    mg.TBL_FLDTYPE: fldtype, mg.TBL_FLDTYPE_ORIG: None}
                self.settings_data.append(new_row)
            if self.debug or debug: pprint.pprint(self.settings_data)
            self.frame.update_demo()
        else:
            if src_row == len(self.settings_data):
                ## arriving at final row on init
                changed = False
            else:
                try:
                    settings_fldname = \
                        self.settings_data[src_row][mg.TBL_FLDNAME]
                    settings_fldtype = \
                         self.settings_data[src_row][mg.TBL_FLDTYPE]
                    changed = ((fldname != settings_fldname)
                         or (fldtype != settings_fldtype))
                except IndexError:
                    changed = True
            if changed:
                self.update_settings_data()
                self.frame.update_demo()

    def update_settings_data(self):
        """
        Update settings_data. Overridden so we can include original field
        details (needed when making new version of the original table).

        Fill in details of fldnames and fldtypes (leaving original versions
        untouched).

        NB do not clear it - only modify.
        """
        debug = False
        grid_data = self.get_grid_data()  ## only saved data. eol-safe inc
        if debug: 
            print(f'grid data: {grid_data}')
            print('Original settings data:')
            pprint.pprint(self.settings_data)
        for i, row in enumerate(grid_data):
            if debug: print(row)
            self.settings_data[i][mg.TBL_FLDNAME] = row[0]
            self.settings_data[i][mg.TBL_FLDTYPE] = row[1]
        if self.debug or debug:
            print('Final settings data:')
            pprint.pprint(self.settings_data)

    def try_to_delete_row(self, *, assume_row_deletion_attempt=True):
        """
        Overridden so we can update settings data.

        Delete row if a row selected and not the data entry row and put focus on
        new line.

        Return row idx deleted (or None if deletion did not occur).

        If it is assumed there was a row deletion attempt (e.g. clicked a delete
        button), then warn if no selection. If no such assumption, silently cope
        with situation where no selection.
        """
        debug = False
        selected_rows = self.grid.GetSelectedRows()
        sel_rows_n = len(selected_rows)
        if sel_rows_n == 1:
            row = selected_rows[0]
            ok_to_delete, msg = self.ok_to_delete_row(row)
            if ok_to_delete:
                self.delete_row(row)
                if self.debug or debug: print(f'Row deleted was {row}')
                ## remove row from settings_data.
                del self.frame.settings_data[row]
                self.frame.update_demo()
                if self.debug or debug: pprint.pprint(self.settings_data)
                return row
            else:
                wx.MessageBox(msg)
        elif sel_rows_n == 0:
            if assume_row_deletion_attempt:
                wx.MessageBox(_(
                    'Please select a row first (click to the left of the row)'))
            else:
                pass
        else:
            wx.MessageBox(_('Can only delete one row at a time'))
        return None

    def ok_to_delete_row(self, row):
        """
        Overridden settings_grid.SettingsEntry to handle row == 0.

        Should be the same otherwise.

        Can delete any row except the new row or the SOFA_ID row

        Returns boolean and msg.
        """
        if self.is_new_row(row):
            return False, _('Unable to delete new row')
        elif row == 0:
            return False, _('Unable to delete sofa id row')
        elif self.new_is_dirty:
            return (False, _(
                'Cannot delete a row while in the middle of making a new one'))
        else:
            return True, None
