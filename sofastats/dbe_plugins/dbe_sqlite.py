import sqlite3 as sqlite
import pprint
import re
import wx #@UnusedImport
import wx.grid

from .. import basic_lib as b
from .. import my_globals as mg
from .. import lib
from .. import my_exceptions
from .. import settings_grid

Row = sqlite.Row  ## @UndefinedVariable - needed for making cursor return dicts

DEFAULT_DB = 'sqlite_default_db'
DEFAULT_TBL = 'sqlite_default_tbl'
## http://www.sqlite.org/datatype3.html
NUMERIC_TYPES = ['int', 'integer', 'tinyint', 'smallint', 'mediumint', 'bigint',
    'unsigned big int', 'int2', 'int8', 'float', 'numeric', 'real', 'double',
    'double precision', 'float real', 'numeric']
DATE_TYPES = ['date', 'datetime', 'time', 'timestamp']
DATABASE_KEY = 'database'
DATABASE_FLD_LABEL = _('Database(s)')

if_clause = 'CASE WHEN %s THEN %s ELSE %s END'
placeholder = '?'
left_obj_quote = '`'
right_obj_quote = '`'
gte_not_equals = '!='
cartesian_joiner = ' JOIN '

## http://www.sqlite.org/lang_keywords.html
## The following is non-standard but will work
def quote_obj(raw_val):
    return f'{left_obj_quote}{raw_val}{right_obj_quote}'

def quote_val(raw_val):
    """
    Single quote is the literal delimiter and internal single quotes need
    escaping by repeating them.
    """
    return lib.DbLib.quote_val(raw_val,
        sql_str_literal_quote="'", sql_esc_str_literal_quote="''")

def get_summable(clause):
    return clause

def get_syntax_elements():
    return (if_clause, left_obj_quote, right_obj_quote, quote_obj, quote_val,
        placeholder, get_summable, gte_not_equals, cartesian_joiner)

def get_first_sql(quoted_tblname, top_n, order_val=None):
    orderby = "ORDER BY %s" % quote_obj(order_val) if order_val else ''
    return f"SELECT * FROM {quoted_tblname} {orderby} LIMIT {top_n}"

def add_funcs_to_con(con):
    con.create_function("is_numeric", 1, lib.TypeLib.is_numeric)
    con.create_function("is_std_datetime_str", 1,
        lib.DateLib.is_std_datetime_str)

def get_con(con_dets, db, *, add_checks=False):
    """
    Use this connection rather than hand-making one. Risk of malformed database
    schema. E.g. DatabaseError: malformed database schema (sofa_tmp_tbl) - 
    no such function: is_numeric

    add_checks -- adds user-defined functions so can be used in check 
    constraints to ensure data type integrity.
    """
    ## any sqlite connection details at all?
    try:
        con_dets_sqlite = con_dets[mg.DBE_SQLITE]
    except Exception as e:
        raise my_exceptions.MissingConDets(mg.DBE_SQLITE)
    ## able to extract con dets in a form usable for scripts?
    try:
        sqlite_con_dets_str = pprint.pformat(con_dets_sqlite)
    except Exception as e:
        raise Exception("Unable to extract connection details from "
            f"{con_dets_sqlite}.\nCaused by error: {b.ue(e)}")
    ## any connection details for this database?
    try:
        con_dets_sqlite_db = con_dets_sqlite[db]
    except Exception as e:
        raise Exception(f'No connections for SQLite database "{db}"')
    ## able to actually connect to database?
    try:
        con = sqlite.connect(**con_dets_sqlite_db) #@UndefinedVariable
    except Exception as e:
        ## failure because still pointing to dev path?
        if "/home/g/Documents/sofastats" in sqlite_con_dets_str:
            raise Exception("Problem with default project file. "
                f"Delete {mg.INT_PATH / mg.PROJ_CUSTOMISED_FILE} "
                f"and restart SOFA.\nCaused by error {b.ue(e)}.")
        else:
            raise Exception(f"Unable to make connection with db '{db}' "
                f"using: {lib.escape_pre_write(sqlite_con_dets_str)}"
                f"\nCaused by error: {b.ue(e)}")
    if mg.USE_SQLITE_UDFS:
        print('*'*60)
        print("Overriding so can open sofa_db in SOFA")
        print('*'*60)
        add_checks = True  ## if having trouble opening e.g. if tmp_tbl left
            ## there will have constraints relying on absent UDFs
    if add_checks:
        ## some UDFs needed for strict type checking constraints
        add_funcs_to_con(con)
    return con

def get_dbs_list(con_dets, default_dbs):
    """
    Get list of all databases for this dbe (as per con dets in proj file).

    NB con_resources will only have one db listed (this dbe has one db per 
    connection).
    """
    con_dets_sqlite = con_dets.get(mg.DBE_SQLITE)
    if not con_dets_sqlite:
        raise my_exceptions.MissingConDets(mg.DBE_SQLITE)
    return con_dets_sqlite.keys()

def get_con_resources(con_dets, default_dbs, db=None, *, add_checks=False):
    """
    When opening from scratch, e.g. clicking on Report Tables from Start,
    no db, so must identify one, but when selecting dbe-db in dropdowns, there 
    will be a db.

    Returns dict with con, cur, dbs, db.
    """
    if not db:
        ## if no con specified, use default, or failing that, try a specific file
        default_db = default_dbs.get(mg.DBE_SQLITE)  ## might be None
        if default_db:
            db = default_db
        else:
            db = con_dets[mg.DBE_SQLITE].keys()[0]
    try:
        con = get_con(con_dets, db, add_checks=add_checks)
    except Exception as e:
        print(str(e))
        raise
    cur = con.cursor()  ## must return tuples not dics
    if cur is None:
        raise Exception(_("Unable to get valid cursor from database "
            "connection to \"%s\"" % db))
    if not has_tbls(cur, db):
        raise Exception(_("\n\nDatabase \"%s\" didn't have any tables. "
            "You can only connect to SQLite databases which have data in them."
            "\n\nIf you just wanted an empty SQLite database to put fresh data" 
            " into from within SOFA, use the supplied sofa_db database "
            "instead.") % db)
    con_resources = {mg.DBE_CON: con, mg.DBE_CUR: cur, mg.DBE_DBS: [db,],
        mg.DBE_DB: db}
    return con_resources

def get_unsorted_tblnames(cur, db):
    "Get table names given database and cursor"
    SQL_get_tbls = """SELECT name 
        FROM sqlite_master 
        WHERE type = 'table'
        ORDER BY name"""
    try:
        cur.execute(SQL_get_tbls)
    except Exception as e:
        if b.ue(e).startswith("malformed database schema"):
            raise my_exceptions.MalformedDb()
        else:
            print(b.ue(e))
            raise
    tbls = [x[0] for x in cur.fetchall()]
    return tbls

def get_tbls(cur, db):
    "Get table names given database and cursor"
    tbls = get_unsorted_tblnames(cur, db)
    tbls.sort(key=lambda s: s.upper())
    return tbls

def has_tbls(cur, db):
    "Any non-system tables?"
    tbls = get_unsorted_tblnames(cur, db)
    if tbls:
        return True
    return False

def get_char_len(type_text):
    """
    NB SQLite never truncates whatever you specify.
    http://www.sqlite.org/faq.html#q9

    Look for numbers in brackets (if any) to work out length.

    If just, for example, TEXT, will return None.
    """
    reobj = re.compile(r"\w*()")
    match = reobj.search(type_text)    
    try:
        return int(match.group(1))
    except ValueError:
        return None

def get_flds(cur, db, tbl):
    "http://www.sqlite.org/pragma.html"
    ## get encoding
    cur.execute(u'PRAGMA encoding')
    encoding = cur.fetchone()[0]
    ## get field details
    cur.execute(f"PRAGMA table_info({quote_obj(tbl)})")
    fld_dets = cur.fetchall() 
    flds = {}
    for cid, fldname, fldtype, notnull, dflt_value, pk in fld_dets:
        bolnullable = (notnull == 0)
        bolnumeric = fldtype.lower() in NUMERIC_TYPES
        bolautonum = (pk == 1 and fldtype.lower() == 'integer')            
        boldata_entry_ok = not bolautonum
        boldatetime = fldtype.lower() in DATE_TYPES
        fld_txt = not (bolnumeric or boldatetime)
        bolsigned = True if bolnumeric else None
        dets_dic = {
            mg.FLD_SEQ: cid,
            mg.FLD_BOLNULLABLE: bolnullable,
            mg.FLD_DATA_ENTRY_OK: boldata_entry_ok,
            mg.FLD_COLUMN_DEFAULT: dflt_value,
            mg.FLD_BOLTEXT: fld_txt,
            mg.FLD_TEXT_LENGTH: get_char_len(fldtype),
            mg.FLD_CHARSET: encoding,
            mg.FLD_BOLNUMERIC: bolnumeric,
            mg.FLD_BOLAUTONUMBER: bolautonum,
            mg.FLD_DECPTS: None,  ## not really applicable - no limit
            mg.FLD_NUM_WIDTH: None,  ## no limit (TODO unless check constraint)
            mg.FLD_BOL_NUM_SIGNED: bolsigned,
            mg.FLD_NUM_MIN_VAL: None,  ## not really applicable - no limit
            mg.FLD_NUM_MAX_VAL: None,  ## not really applicable - no limit
            mg.FLD_BOLDATETIME: boldatetime, 
        }
        flds[fldname] = dets_dic
    return flds

def get_index_dets(cur, db, tbl):
    """
    :param str db: needed by some dbes sharing interface.
    :return: idxs = [idx0, idx1, ...] each idx is a dict name with keys
     is_unique, flds, has_unique (boolean)
    :rtype: list
    """
    debug = False
    cur.execute(f'PRAGMA index_list("{tbl}")')
    idx_lst = cur.fetchall()  ## [(seq, name, unique), ...]
    if debug: pprint.pprint(idx_lst)
    names_idx_name = 1
    names_idx_unique = 2
    ## initialise
    has_unique = False
    idxs = []
    if idx_lst:
        idx_names = [x[names_idx_name] for x in idx_lst]
        for i, idx_name in enumerate(idx_names):
            cur.execute(f'PRAGMA index_info("{idx_name}")')
            ## [(seqno, cid, name), ...]
            flds_idxnames = 2
            index_info = cur.fetchall()
            if debug: pprint.pprint(index_info)
            fldnames = [x[flds_idxnames] for x in index_info]
            unique = (idx_lst[i][names_idx_unique] == 1)
            if unique:
                has_unique = True
            idx_dic = {mg.IDX_NAME: idx_name, mg.IDX_IS_UNIQUE: unique, 
                mg.IDX_FLDS: fldnames}
            idxs.append(idx_dic)
    if debug:
        pprint.pprint(idxs)
        print(has_unique)
    return idxs, has_unique

def set_data_con_gui(parent, scroll, szr, lblfont, *, read_only=False):
    bx_sqlite = wx.StaticBox(scroll, -1, "SQLite")
    ## default database
    parent.lbl_sqlite_default_db = wx.StaticText(scroll, -1, 
        _('Default Database (name only):'))
    parent.lbl_sqlite_default_db.SetFont(lblfont)
    DEFAULT_DB = parent.sqlite_default_db if parent.sqlite_default_db else ''
    parent.txt_sqlite_default_db = wx.TextCtrl(
        scroll, -1, DEFAULT_DB, size=(250, -1))
    parent.txt_sqlite_default_db.Enable(not read_only)
    parent.txt_sqlite_default_db.SetToolTip(_('Default database (optional)'))
    ## default table
    parent.lbl_sqlite_default_tbl = wx.StaticText(scroll, -1, 
        _('Default Table (optional):'))
    parent.lbl_sqlite_default_tbl.SetFont(lblfont)
    DEFAULT_TBL = parent.sqlite_default_tbl if parent.sqlite_default_tbl else ''
    parent.txt_sqlite_default_tbl = wx.TextCtrl(
        scroll, -1, DEFAULT_TBL, size=(250, -1))
    parent.txt_sqlite_default_tbl.Enable(not read_only)
    parent.txt_sqlite_default_tbl.SetToolTip(_('Default table (optional)'))
    parent.szr_sqlite = wx.StaticBoxSizer(bx_sqlite, wx.VERTICAL)
    ## 3 SQLITE INNER
    szr_sqlite_inner = wx.BoxSizer(wx.HORIZONTAL)
    szr_sqlite_inner.Add(parent.lbl_sqlite_default_db, 0, wx.LEFT|wx.RIGHT, 5)
    szr_sqlite_inner.Add(parent.txt_sqlite_default_db, 0, wx.RIGHT, 10)
    szr_sqlite_inner.Add(parent.lbl_sqlite_default_tbl, 0, wx.LEFT|wx.RIGHT, 5)
    szr_sqlite_inner.Add(parent.txt_sqlite_default_tbl, 0, wx.RIGHT, 10)
    parent.szr_sqlite.Add(szr_sqlite_inner, 0, wx.GROW)
    sqlite_col_dets = [{'col_label': DATABASE_FLD_LABEL, 
        'coltype': settings_grid.COL_TEXT_BROWSE, 'colwidth': 400, 
        'file_phrase': _('Choose an SQLite database file')}]
    parent.sqlite_settings_data = []
    init_settings_data = parent.sqlite_data[:]
    init_settings_data.sort(key=lambda s: s[0])
    parent.sqlite_grid = settings_grid.SettingsEntry(frame=parent,
        panel=scroll, grid_size=(550,100),
        col_dets=sqlite_col_dets, init_settings_data=init_settings_data,
        settings_data=parent.sqlite_settings_data,
        read_only=read_only, force_focus=True)
    """
    Make sofa_db stand out as special but allow users to edit it (it may have 
    changed location since the project was created).

    Responsibility for making sure there is a database called sofa_db is up to 
    the validation code for saving the project.
    """
    attr = wx.grid.GridCellAttr()
    #attr.SetReadOnly(True)
    attr.SetBackgroundColour(mg.READ_ONLY_COLOUR)
    for row_idx, db_path in enumerate([x[0] for x in init_settings_data]):
        db_name = lib.get_file_name(db_path)  ## might not be unique
        if db_is_default_sofa_db(db_name):
            parent.sqlite_grid.grid.SetRowAttr(row_idx, attr)
    parent.szr_sqlite.Add(parent.sqlite_grid.grid, 1, wx.GROW|wx.ALL, 5)
    szr.Add(parent.szr_sqlite, 0, wx.GROW|wx.ALL, 10)

def db_is_default_sofa_db(db_name):
    """
    Be generous in what counts as a default sofa database. The following should
    all be OK: sofa_db (of course), original_sofa_db, sofa_db_testing etc.

    The user may have made copies, shifted it around etc. The only fixed one is
    that created during installation. The default project references that and it
    cannot be changed. But if they make copies etc and put them somewhere else,
    those versions can be used just like a standard default.

    Of course, a user can mess things up by giving other unsuitable files names
    which include sofa_db.
    """
    return mg.SOFA_DB in db_name

def get_proj_settings(parent, proj_dic):
    parent.sqlite_default_db = proj_dic[mg.PROJ_DEFAULT_DBS].get(mg.DBE_SQLITE)
    parent.sqlite_default_tbl = (
        proj_dic[mg.PROJ_DEFAULT_TBLS].get(mg.DBE_SQLITE))
    if proj_dic[mg.PROJ_CON_DETS].get(mg.DBE_SQLITE):
        parent.sqlite_data = [(x[DATABASE_KEY],) for x 
            in proj_dic[mg.PROJ_CON_DETS][mg.DBE_SQLITE].values()]
    else:
        parent.sqlite_data = []

def set_con_det_defaults(parent):
    try:            
        parent.sqlite_default_db
    except AttributeError: 
        parent.sqlite_default_db = ''
    try:
        parent.sqlite_default_tbl
    except AttributeError: 
        parent.sqlite_default_tbl = ''
    try:
        parent.sqlite_data
    except AttributeError: 
        parent.sqlite_data = []

def process_con_dets(parent, default_dbs, default_tbls, con_dets):
    """
    Copes with missing default database and table. Will get the first available.

    Namespace multiple databases with same name (presumably in different 
    folders).
    """
    if parent.sqlite_grid.new_is_dirty:
        incomplete_sqlite = True
        has_sqlite_con = False
        wx.MessageBox(_("The SQLite details on the new row have not been "
            "saved. Select the \"%s\" field in the new row and press Enter")
            % DATABASE_FLD_LABEL)
        parent.sqlite_grid.SetFocus()
        return incomplete_sqlite, has_sqlite_con
    parent.sqlite_grid.update_settings_data()
    #pprint.pprint(parent.sqlite_settings_data) # debug
    sqlite_settings = parent.sqlite_settings_data
    lacks_default_sofa_db = True
    if sqlite_settings:
        con_dets_sqlite = {}
        db_names = []
        for sqlite_setting in sqlite_settings:
            ## e.g. ("C:\.....\my_sqlite_db",)
            db_path = sqlite_setting[0]
            db_name = lib.get_file_name(db_path)  ## might not be unique
            if db_is_default_sofa_db(db_name):
                lacks_default_sofa_db = False
            ## need unique version to use as key
            db_name_key = lib.DbLib.get_unique_db_name_key(db_names, db_name)
            new_sqlite_dic = {}
            new_sqlite_dic[DATABASE_KEY] = db_path
            con_dets_sqlite[db_name_key] = new_sqlite_dic
        con_dets[mg.DBE_SQLITE] = con_dets_sqlite
    DEFAULT_DB = parent.txt_sqlite_default_db.GetValue()
    DEFAULT_TBL = parent.txt_sqlite_default_tbl.GetValue()
    try:
        has_sqlite_con = con_dets[mg.DBE_SQLITE]
    except KeyError:
        has_sqlite_con = False
    defaults_but_no_conns = (DEFAULT_DB or DEFAULT_TBL) and not has_sqlite_con
    conns_but_no_default_sofa_db = has_sqlite_con and lacks_default_sofa_db
    incomplete_sqlite = defaults_but_no_conns or conns_but_no_default_sofa_db
    if incomplete_sqlite:
        if defaults_but_no_conns:
            wx.MessageBox(_("The SQLite details are partially complete - "
                "either add a database or clear the SQLite default database "
                "and table"))
        elif conns_but_no_default_sofa_db:
            wx.MessageBox(_("The sofa default database \"%s\"must be included"
                " in the project.") % mg.SOFA_DB)
        parent.txt_sqlite_default_db.SetFocus()
    else:
        default_dbs[mg.DBE_SQLITE] = DEFAULT_DB if DEFAULT_DB else None
        default_tbls[mg.DBE_SQLITE] = DEFAULT_TBL if DEFAULT_TBL else None
    return incomplete_sqlite, has_sqlite_con

## unique to SQLite (because used to store tables for user-entered data plus 
## imported data)

def valid_tblname(tblname):
    return valid_name(tblname, is_tblname=True)

def valid_fldname(fldname):
    return valid_name(fldname, is_tblname=False)

def get_blocks(fldnames, block_sz=50):
    "Make blocks of at most block_sz"
    debug = False
    blocks = []
    i = 0
    while True:
        block = fldnames[i*block_sz:(i+1)*block_sz]
        if debug: print(f"Block is: {block}")
        if not block: break
        blocks.append(block)
        i += 1
    if debug: print(blocks)
    return blocks

def valid_fldnames(fldnames, block_sz=50):
    valid = True
    err = ''
    ## make blocks of at most block_sz
    blocks = get_blocks(fldnames, block_sz)
    for block in blocks:
        block_valid, block_err = valid_fldnames_block(block)
        if not block_valid:
            valid = False
            err = block_err
            break
    return valid, err

def valid_fldnames_block(block):
    debug = False
    default_db = mg.LOCAL_PATH / mg.INT_FOLDER / 'sofa_tmp'
    con = sqlite.connect(default_db) #@UndefinedVariable
    add_funcs_to_con(con)
    cur = con.cursor()
    valid = True
    err = ''
    try:
        flds_clause = ', '.join(['`%s` TEXT' % x for x in block])
        tblname = 'safetblname'
        ## in case it survives somehow esp safetblname
        ## OK if this fails here
        sql_drop = f'DROP TABLE IF EXISTS {tblname}'
        if debug: print(sql_drop)
        cur.execute(sql_drop)
        con.commit()
        ## usable names in practice?
        sql_make = f'CREATE TABLE {tblname} ({flds_clause})'
        if debug: print(sql_make)
        cur.execute(sql_make)
        con.commit()  ## otherwise when committing, no net change to commit and 
            ## no actual chance to succeed or fail
        ## clean up
        sql_drop = f'DROP TABLE IF EXISTS {tblname}'
        if debug: print(sql_drop)
        cur.execute(sql_drop)
        con.commit()
    except Exception as e:
        if debug: print(b.ue(e))
        valid = False
        err = b.ue(e)
    finally:
        cur.close()
        con.close()
        return valid, err

def valid_name(name, is_tblname=True):
    """
    tbl -- True for tblname being tested, False if a fldname being tested.

    Bad name for SQLite? The best way is to find out for real (not too costly
    and 100% valid by definition). Strangely, SQLite accepts '' as a table name
    but we won't ;-).
    """
    debug = False
    if name == '':
        return False
    default_db = mg.LOCAL_PATH / mg.INT_FOLDER / 'sofa_tmp'
    con = sqlite.connect(default_db) #@UndefinedVariable
    add_funcs_to_con(con)
    cur = con.cursor()
    valid = True
    err = ''
    try:
        if is_tblname:
            tblname = quote_obj(name)
            fldname = 'safefldname'
        else:
            tblname = 'safetblname'
            fldname = name
        ## in case it survives somehow esp safetblname
        ## OK if this fails here
        sql_drop = f'DROP TABLE IF EXISTS {tblname}'
        if debug: print(sql_drop)
        cur.execute(sql_drop)
        con.commit()
        ## usable names in practice?
        sql_make = f'CREATE TABLE {tblname} (`{fldname}` TEXT)'
        if debug: print(sql_make)
        cur.execute(sql_make)
        con.commit()  ## otherwise when committing, no net change to commit and 
            ## no actual chance to succeed or fail
        ## clean up
        sql_drop = f'DROP TABLE IF EXISTS {tblname}'
        if debug: print(sql_drop)
        cur.execute(sql_drop)
        con.commit()
    except Exception as e:
        valid = False
        if debug: print(b.ue(e))
        err = b.ue(e)
    finally:
        cur.close()
        con.close()
        return valid, err
