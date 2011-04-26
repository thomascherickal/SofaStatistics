from __future__ import print_function

#from pysqlite2 import dbapi2 as sqlite
import sqlite3 as sqlite
import os
import pprint
import re
import string
import wx

import my_globals as mg
import lib
import my_exceptions
import getdata
import settings_grid

Row = sqlite.Row # needed for making cursor return dicts

DEFAULT_DB = u"sqlite_default_db"
DEFAULT_TBL = u"sqlite_default_tbl"
NUMERIC_TYPES = [u"integer", u"float", u"numeric", u"real"]
DATE_TYPES = [u"date", u"datetime", u"time", u"timestamp"]
DATABASE_KEY = u"database"
DATABASE_FLD_LABEL = _("Database(s)")

if_clause = u"CASE WHEN %s THEN %s ELSE %s END"
placeholder = u"?"
left_obj_quote = u"`"
right_obj_quote = u"`"
gte_not_equals = u"!="

# http://www.sqlite.org/lang_keywords.html
# The following is non-standard but will work
def quote_obj(raw_val):
    return u"%s%s%s" % (left_obj_quote, raw_val, right_obj_quote)

def quote_val(raw_val):
    try:
        val = raw_val.replace('"', '""') # escape internal double quotes
    except AttributeError, e:
        raise Exception(u"Inappropriate attempt to quote non-string value."
                        u"\nCaused by error: %s" % lib.ue(e))
    return u"\"%s\"" % val

def get_summable(clause):
    return clause

def get_syntax_elements():
    return (if_clause, left_obj_quote, right_obj_quote, quote_obj, quote_val, 
            placeholder, get_summable, gte_not_equals)

def get_first_sql(tblname, top_n, order_val=None):
    orderby = u"ORDER BY %s" % quote_obj(order_val) if order_val else u""
    return u"SELECT * FROM %(tblname)s %(orderby)s LIMIT %(top_n)s" % \
        {"top_n": top_n, "tblname": quote_obj(tblname), "orderby": orderby}
        
def add_funcs_to_con(con):
    con.create_function("is_numeric", 1, lib.is_numeric)
    con.create_function("is_std_datetime_str", 1, lib.is_std_datetime_str)

def get_con(con_dets, db, add_checks=False):
    """
    Use this connection rather than hand-making one.  Risk of malformed database
        schema.  E.g. DatabaseError: malformed database schema (sofa_tmp_tbl) - 
        no such function: is_numeric
    add_checks -- adds user-defined functions so can be used in check 
        constraints to ensure data type integrity.
    """
    con_dets_sqlite = con_dets.get(mg.DBE_SQLITE)
    if not con_dets_sqlite:
        raise my_exceptions.MissingConDets(mg.DBE_SQLITE)
    if not con_dets_sqlite.get(db):
        raise Exception(u"No connections for SQLite database %s" % db)
    try:
        sofa_db_path = (u"Unable to get connection details for db '%s' "
                        u"using: %s") % (db, pprint.pformat(con_dets_sqlite))
        con = sqlite.connect(**con_dets_sqlite[db])
        try:
            sofa_db_path = con_dets_sqlite[db][DATABASE_KEY]
        except Exception:
            sofa_db_path = u"Unable to get SQLite database path"
    except Exception, e:
        if sofa_db_path == os.path.join(u"/home/g/sofastats/_internal", 
                                        mg.SOFA_DB):
            raise Exception(u"Problem with default project file. Delete "
                            u"%s and restart SOFA.\nCaused by error %s." %
                            (os.path.join(mg.INT_PATH, mg.PROJ_CUSTOMISED_FILE), 
                            lib.ue(e)))
        else:
            raise Exception(u"Unable to connect to SQLite database using "
                            u"supplied database: \"%s\" and supplied " % db +
                            u"connection details: %s." % sofa_db_path +
                            u"\nCaused by error: %s." % lib.ue(e))
    if mg.USE_SQLITE_UDFS:
        print("*"*60)
        print("Overriding so can open sofa_db in SOFA")
        print("*"*60)
        add_checks = True # if having trouble opening e.g. if tmp_tbl left there
            # will have constraints relying on absent user-defined functions.
    if add_checks:
        # some user-defined functions needed for strict type checking constraints
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

def get_con_resources(con_dets, default_dbs, db=None, add_checks=False):
    """
    When opening from scratch, e.g. clicking on Report Tables from Start,
        no db, so must identify one, but when selecting dbe-db in dropdowns, 
        there will be a db.
    Returns dict with con, cur, dbs, db.
    """
    if not db:
        # if no con specified, use default, or failing that, try a specific file
        default_db = default_dbs.get(mg.DBE_SQLITE) # might be None
        if default_db:
            db = default_db
        else:
            db = con_dets[mg.DBE_SQLITE].keys()[0]
    try:
        con = get_con(con_dets, db, add_checks=add_checks)
    except Exception, e:
            print(unicode(e))
            raise
    cur = con.cursor() # must return tuples not dics
    if not has_tbls(cur, db):
        raise Exception(_(u"\n\nDatabase \"%s\" didn't have any tables. "
            u"You can only connect to SQLite databases which have data in them."
            u"\n\nIf you just wanted an empty SQLite database to put fresh data" 
            u" into from within SOFA, use the supplied sofa_db database "
            u"instead.") % db)
    con_resources = {mg.DBE_CON: con, mg.DBE_CUR: cur, mg.DBE_DBS: [db,],
                     mg.DBE_DB: db}
    return con_resources

def get_unsorted_tblnames(cur, db):
    "Get table names given database and cursor"
    SQL_get_tbls = u"""SELECT name 
        FROM sqlite_master 
        WHERE type = 'table'
        ORDER BY name"""
    try:
        cur.execute(SQL_get_tbls)
    except Exception, e:
        if lib.ue(e).startswith(u"malformed database schema"):
            raise my_exceptions.MalformedDbError()
        else:
            print(lib.ue(e))
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
    # get encoding
    cur.execute(u"PRAGMA encoding")
    encoding = cur.fetchone()[0]
    # get field details
    cur.execute(u"PRAGMA table_info(%s)" % quote_obj(tbl))
    fld_dets = cur.fetchall() 
    flds = {}
    for cid, fld_name, fld_type, notnull, dflt_value, pk in fld_dets:
        bolnullable = True if notnull == 0 else False
        bolnumeric = fld_type.lower() in NUMERIC_TYPES
        bolautonum = (pk == 1 and fld_type.lower() == "integer")            
        boldata_entry_ok = False if bolautonum else True
        boldatetime = fld_type.lower() in DATE_TYPES
        fld_txt = not bolnumeric and not boldatetime
        bolsigned = True if bolnumeric else None
        dets_dic = {
            mg.FLD_SEQ: cid,
            mg.FLD_BOLNULLABLE: bolnullable,
            mg.FLD_DATA_ENTRY_OK: boldata_entry_ok,
            mg.FLD_COLUMN_DEFAULT: dflt_value,
            mg.FLD_BOLTEXT: fld_txt,
            mg.FLD_TEXT_LENGTH: get_char_len(fld_type),
            mg.FLD_CHARSET: encoding,
            mg.FLD_BOLNUMERIC: bolnumeric,
            mg.FLD_BOLAUTONUMBER: bolautonum,
            mg.FLD_DECPTS: None, # not really applicable - no limit
            mg.FLD_NUM_WIDTH: None, # no limit (TODO unless check constraint)
            mg.FLD_BOL_NUM_SIGNED: bolsigned,
            mg.FLD_NUM_MIN_VAL: None, # not really applicable - no limit
            mg.FLD_NUM_MAX_VAL: None, # not really applicable - no limit
            mg.FLD_BOLDATETIME: boldatetime, 
            }
        flds[fld_name] = dets_dic
    return flds

def get_index_dets(cur, db, tbl):
    """
    db -- needed by some dbes sharing interface.
    idxs = [idx0, idx1, ...]
    each idx is a dict name, is_unique, flds
    has_unique - boolean
    """
    debug = False
    cur.execute(u"PRAGMA index_list(\"%s\")" % tbl)
    idx_lst = cur.fetchall() # [(seq, name, unique), ...]
    if debug: pprint.pprint(idx_lst)
    names_idx_name = 1
    names_idx_unique = 2
    # initialise
    has_unique = False
    idxs = []
    if idx_lst:
        idx_names = [x[names_idx_name] for x in idx_lst]
        for i, idx_name in enumerate(idx_names):
            cur.execute(u"PRAGMA index_info(\"%s\")" % idx_name)
            # [(seqno, cid, name), ...]
            flds_idx_names = 2
            index_info = cur.fetchall()
            if debug: pprint.pprint(index_info)
            fld_names = [x[flds_idx_names] for x in index_info]
            unique = (idx_lst[i][names_idx_unique] == 1)
            if unique:
                has_unique = True
            idx_dic = {mg.IDX_NAME: idx_name, mg.IDX_IS_UNIQUE: unique, 
                       mg.IDX_FLDS: fld_names}
            idxs.append(idx_dic)
    if debug:
        pprint.pprint(idxs)
        print(has_unique)
    return idxs, has_unique

def set_data_con_gui(parent, readonly, scroll, szr, lblfont):
    bx_sqlite = wx.StaticBox(scroll, -1, "SQLite")
    # default database
    parent.lbl_sqlite_default_db = wx.StaticText(scroll, -1, 
                                            _("Default Database (name only):"))
    parent.lbl_sqlite_default_db.SetFont(lblfont)
    DEFAULT_DB = parent.sqlite_default_db if parent.sqlite_default_db else ""
    parent.txt_sqlite_default_db = wx.TextCtrl(scroll, -1, DEFAULT_DB, 
                                               size=(250,-1))
    parent.txt_sqlite_default_db.Enable(not readonly)
    parent.txt_sqlite_default_db.SetToolTipString(_("Default database"
                                                 " (optional)"))
    # default table
    parent.lbl_sqlite_default_tbl = wx.StaticText(scroll, -1, 
                                               _("Default Table (optional):"))
    parent.lbl_sqlite_default_tbl.SetFont(lblfont)
    DEFAULT_TBL = parent.sqlite_default_tbl if parent.sqlite_default_tbl \
        else u""
    parent.txt_sqlite_default_tbl = wx.TextCtrl(scroll, -1, DEFAULT_TBL, 
                                             size=(250,-1))
    parent.txt_sqlite_default_tbl.Enable(not readonly)
    parent.txt_sqlite_default_tbl.SetToolTipString(_("Default table"
                                                     " (optional)"))
    parent.szr_sqlite = wx.StaticBoxSizer(bx_sqlite, wx.VERTICAL)
    #3 SQLITE INNER
    szr_sqlite_inner = wx.BoxSizer(wx.HORIZONTAL)
    szr_sqlite_inner.Add(parent.lbl_sqlite_default_db, 0, wx.LEFT|wx.RIGHT, 5)
    szr_sqlite_inner.Add(parent.txt_sqlite_default_db, 0, wx.RIGHT, 10)
    szr_sqlite_inner.Add(parent.lbl_sqlite_default_tbl, 0, wx.LEFT|wx.RIGHT, 5)
    szr_sqlite_inner.Add(parent.txt_sqlite_default_tbl, 0, wx.RIGHT, 10)
    parent.szr_sqlite.Add(szr_sqlite_inner, 0, wx.GROW)
    sqlite_col_dets = [{"col_label": DATABASE_FLD_LABEL, 
                        "col_type": settings_grid.COL_TEXT_BROWSE, 
                        "col_width": 400, 
                        "file_phrase": _("Choose an SQLite database file")}]
    parent.sqlite_settings_data = []
    init_settings_data = parent.sqlite_data[:]
    init_settings_data.sort(key=lambda s: s[0])
    parent.sqlite_grid = settings_grid.SettingsEntry(frame=parent, 
                           panel=scroll, readonly=readonly, grid_size=(550,100), 
                           col_dets=sqlite_col_dets, 
                           init_settings_data=init_settings_data, 
                           settings_data=parent.sqlite_settings_data, 
                           force_focus=True)
    # disable first row (default sofa db)
    attr = wx.grid.GridCellAttr()
    attr.SetReadOnly(True)
    attr.SetBackgroundColour(mg.READONLY_COLOUR)
    parent.sqlite_grid.grid.SetRowAttr(0, attr)
    parent.szr_sqlite.Add(parent.sqlite_grid.grid, 1, wx.GROW|wx.ALL, 5)
    szr.Add(parent.szr_sqlite, 0, wx.GROW|wx.ALL, 10)

def get_proj_settings(parent, proj_dic):
    parent.sqlite_default_db = proj_dic[mg.PROJ_DEFAULT_DBS].get(mg.DBE_SQLITE)
    parent.sqlite_default_tbl = \
                              proj_dic[mg.PROJ_DEFAULT_TBLS].get(mg.DBE_SQLITE)
    if proj_dic[mg.PROJ_CON_DETS].get(mg.DBE_SQLITE):
        parent.sqlite_data = [(x[DATABASE_KEY],) \
             for x in proj_dic[mg.PROJ_CON_DETS][mg.DBE_SQLITE].values()]
    else:
        parent.sqlite_data = []

def set_con_det_defaults(parent):
    try:            
        parent.sqlite_default_db
    except AttributeError: 
        parent.sqlite_default_db = u""
    try:
        parent.sqlite_default_tbl
    except AttributeError: 
        parent.sqlite_default_tbl = u""
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
        wx.MessageBox(_(u"The SQLite details on the new row "
                        u"have not been saved. "
                        u"Select the \"%s\" field in the new row "
                        u"and press Enter")
                        % DATABASE_FLD_LABEL)
        parent.sqlite_grid.SetFocus()
        return incomplete_sqlite, has_sqlite_con
    parent.sqlite_grid.update_settings_data()
    #pprint.pprint(parent.sqlite_settings_data) # debug
    sqlite_settings = parent.sqlite_settings_data
    if sqlite_settings:
        con_dets_sqlite = {}
        db_names = []
        for sqlite_setting in sqlite_settings:
            # e.g. ("C:\.....\my_sqlite_db",)
            db_path = sqlite_setting[0]
            db_name = lib.get_file_name(db_path) # might not be unique
            db_name_key = lib.get_unique_db_name_key(db_names, db_name)
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
    incomplete_sqlite = (DEFAULT_DB or DEFAULT_TBL) and not has_sqlite_con
    if incomplete_sqlite:
        wx.MessageBox(_("The SQLite details are incomplete"))
        parent.txt_sqlite_default_db.SetFocus()
    else:
        default_dbs[mg.DBE_SQLITE] = DEFAULT_DB if DEFAULT_DB else None
        default_tbls[mg.DBE_SQLITE] = DEFAULT_TBL if DEFAULT_TBL else None
    return incomplete_sqlite, has_sqlite_con

# unique to SQLite (because used to store tables for user-entered data plus 
# imported data)
    
def valid_tblname(tblname):
    return valid_name(tblname, is_tblname=True)

def valid_fldname(fldname):
    return valid_name(fldname, is_tblname=False)

def valid_name(name, is_tblname=True):
    """
    tbl -- True for tblname being tested, False if a fldname being tested.
    Bad name for SQLite?  The best way is to find out for real (not too costly
        and 100% valid by definition). Strangely, SQLite accepts u"" as a table
        name but we won't ;-).
    """
    debug = False
    if name == u"":
        return False
    default_db = os.path.join(mg.LOCAL_PATH, mg.INT_FOLDER, u"sofa_tmp")
    con = sqlite.connect(default_db)
    add_funcs_to_con(con)
    cur = con.cursor()
    valid = False
    try:
        if is_tblname:
            tblname = getdata.tblname_qtr(mg.DBE_SQLITE, name)
            fldname = u"safefldname"
        else:
            tblname = u"safetblname"
            fldname = name
        # in case it survives somehow esp safetblname
        # OK if this fails here
        sql_drop = "DROP TABLE IF EXISTS %s" % tblname
        if debug: print(sql_drop)
        cur.execute(sql_drop)
        con.commit()
        # usable names in practice?
        sql_make = "CREATE TABLE %s (`%s` TEXT)" % (tblname, fldname)
        if debug: print(sql_make)
        cur.execute(sql_make)
        con.commit() # otherwise when committing, no net change to commit and 
            # no actual chance to succeed or fail
        # clean up
        sql_drop = "DROP TABLE IF EXISTS %s" % tblname
        if debug: print(sql_drop)
        cur.execute(sql_drop)
        con.commit()
        valid = True
    except Exception, e:
        if debug: print(lib.ue(e))
    finally:
        cur.close()
        con.close()
        return valid