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
import settings_grid

Row = sqlite.Row # needed for making cursor return dicts

DEFAULT_DB = u"sqlite_default_db"
DEFAULT_TBL = u"sqlite_default_tbl"
NUMERIC_TYPES = [u"integer", u"float", u"numeric", u"real"]
DATE_TYPES = [u"date", u"datetime", u"time", u"timestamp"]

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
    return u"\"%s\"" % raw_val

def get_summable(clause):
    return clause

def get_syntax_elements():
    return (if_clause, left_obj_quote, right_obj_quote, quote_obj, quote_val, 
            placeholder, get_summable, gte_not_equals)

def add_funcs_to_con(con):
    con.create_function("is_numeric", 1, lib.is_numeric)
    con.create_function("is_std_datetime_str", 1, lib.is_std_datetime_str)

def get_con(con_dets, db):
    """
    Use this connection rather than hand-making one.  Risk of malformed database
        schema.  E.g. DatabaseError: malformed database schema (sofa_tmp_tbl) - 
        no such function: is_numeric
    """
    con_dets_sqlite = con_dets.get(mg.DBE_SQLITE)
    if not con_dets_sqlite:
        raise my_exceptions.MissingConDets(mg.DBE_SQLITE)
    if not con_dets_sqlite.get(db):
        raise Exception, u"No connections for SQLite database %s" % db
    try:
        con = sqlite.connect(**con_dets_sqlite[db])
    except Exception, e:
        raise Exception, u"Unable to connect to SQLite database " + \
            u"using supplied database: %s. " % db + \
            u"Orig error: %s" % e
    # some user-defined functions needed for strict type checking constraints
    add_funcs_to_con(con)
    return con

def get_con_resources(con_dets, default_dbs, db=None):
    """
    When opening from scratch, e.g. clicking on Report Tables from Start,
        no db, so must identify one, but when selecting dbe-db in dropdowns, 
        there will be a db.
    Returns dict with con, cur, dbs, db.
    """
    if not db:
        # use default, or failing that, try the file_name
        default_db = default_dbs.get(mg.DBE_SQLITE) # might be None
        if default_db:
            db = default_db
        else:
            db = con_dets[mg.DBE_SQLITE].keys()[0]
    con = get_con(con_dets, db)
    cur = con.cursor() # must return tuples not dics
    con_resources = {mg.DBE_CON: con, mg.DBE_CUR: cur, mg.DBE_DBS: [db,],
                     mg.DBE_DB: db}
    return con_resources

def get_tbls(cur, db):
    "Get table names given database and cursor"
    SQL_get_tbls = u"""SELECT name 
        FROM sqlite_master 
        WHERE type = 'table'
        ORDER BY name"""
    cur.execute(SQL_get_tbls)
    tbls = [x[0] for x in cur.fetchall()]
    tbls.sort(key=lambda s: s.upper())
    return tbls

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
                                                  _("Default Table:"))
    parent.lbl_sqlite_default_tbl.SetFont(lblfont)
    DEFAULT_TBL = parent.sqlite_default_tbl if parent.sqlite_default_tbl \
        else u""
    parent.txt_sqlite_default_tbl = wx.TextCtrl(scroll, -1, DEFAULT_TBL, 
                                             size=(250,-1))
    parent.txt_sqlite_default_tbl.Enable(not readonly)
    parent.txt_sqlite_default_tbl.SetToolTipString(_("Default table"
                                                     " (optional)"))
    bx_sqlite = wx.StaticBox(scroll, -1, "SQLite")
    parent.szr_sqlite = wx.StaticBoxSizer(bx_sqlite, wx.VERTICAL)
    #3 SQLITE INNER
    szr_sqlite_inner = wx.BoxSizer(wx.HORIZONTAL)
    szr_sqlite_inner.Add(parent.lbl_sqlite_default_db, 0, wx.LEFT|wx.RIGHT, 5)
    szr_sqlite_inner.Add(parent.txt_sqlite_default_db, 0, wx.RIGHT, 10)
    szr_sqlite_inner.Add(parent.lbl_sqlite_default_tbl, 0, wx.LEFT|wx.RIGHT, 5)
    szr_sqlite_inner.Add(parent.txt_sqlite_default_tbl, 0, wx.RIGHT, 10)
    parent.szr_sqlite.Add(szr_sqlite_inner, 0, wx.GROW)
    sqlite_col_dets = [{"col_label": _("Database(s)"), 
                        "col_type": settings_grid.COL_TEXT_BROWSE, 
                        "col_width": 400, 
                        "file_phrase": _("Choose an SQLite database file")}]
    parent.sqlite_config_data = []
    data = parent.sqlite_data[:]
    data.sort(key=lambda s: s[0])
    parent.sqlite_grid = settings_grid.SettingsEntry(frame=parent, 
        panel=scroll, szr=parent.szr_sqlite, dim_share=1, readonly=readonly, 
        grid_size=(550, 100), col_dets=sqlite_col_dets, 
        data=parent.sqlite_data, config_data=parent.sqlite_config_data, 
        force_focus=True)
    szr.Add(parent.szr_sqlite, 0, wx.GROW|wx.ALL, 10)

def get_proj_settings(parent, proj_dic):
    parent.sqlite_default_db = \
        proj_dic["default_dbs"].get(mg.DBE_SQLITE)
    parent.sqlite_default_tbl = \
        proj_dic["default_tbls"].get(mg.DBE_SQLITE)
    if proj_dic["con_dets"].get(mg.DBE_SQLITE):
        parent.sqlite_data = [(x["database"],) \
             for x in proj_dic["con_dets"][mg.DBE_SQLITE].values()]
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
    """
    parent.sqlite_grid.update_config_data()
    #pprint.pprint(parent.sqlite_config_data) # debug
    sqlite_settings = parent.sqlite_config_data
    if sqlite_settings:
        con_dets_sqlite = {}
        for sqlite_setting in sqlite_settings:
            # e.g. ("C:\.....\my_sqlite_db",)
            db_path = sqlite_setting[0]
            db_name = lib.get_file_name(db_path)
            new_sqlite_dic = {}
            new_sqlite_dic["database"] = db_path
            con_dets_sqlite[db_name] = new_sqlite_dic
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
    default_dbs[mg.DBE_SQLITE] = DEFAULT_DB if DEFAULT_DB else None
    default_tbls[mg.DBE_SQLITE] = DEFAULT_TBL if DEFAULT_TBL else None
    return incomplete_sqlite, has_sqlite_con

# unique to SQLite (because used to store tables for user-entered data plus 
# imported data)
def valid_name(name):
    """
    Bad name for SQLite?  The best way is to find out for real (not too costly
        and 100% valid by definition).  Strangely, SQLite accepts u"" as a table
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
        cur.execute("""CREATE TABLE "%s" (`%s` TEXT)""" % (name, name))
        cur.execute("""DROP TABLE "%s" """ % name)
        valid = True
    except Exception, e:
        if debug: print(unicode(e))
    finally:
        cur.close()
        con.close()
        return valid
