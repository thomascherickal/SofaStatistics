from __future__ import print_function

from pysqlite2 import dbapi2 as sqlite
import os
import pprint
import re
import string
import wx

import my_globals
import lib
import getdata
import projects
import settings_grid

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

def get_con(con_dets, db):
    con_dets_sqlite = con_dets.get(my_globals.DBE_SQLITE)
    if not con_dets_sqlite:
        raise Exception, u"No connection details available for SQLite"
    if not con_dets_sqlite.get(db):
        raise Exception, u"No connections for SQLite database %s" % db
    try:
        con = sqlite.connect(**con_dets_sqlite[db])
    except Exception, e:
        raise Exception, u"Unable to connect to SQLite database " + \
            u"using supplied database: %s. " % db + \
            u"Orig error: %s" % e
    # some user-defined functions needed for strict type checking constraints
    con.create_function("is_numeric", 1, lib.is_numeric)
    con.create_function("is_std_datetime_str", 1, lib.is_std_datetime_str)
    return con


class DbDets(getdata.DbDets):
    
    """
    __init__ supplies default_dbs, default_tbls, con_dets and 
        db and tbl (may be None).
    """
    
    debug = False
    
    def get_con_cur(self):        
        if not self.db:
            # use default, or failing that, try the file_name
            default_db_sqlite = self.default_dbs.get(my_globals.DBE_SQLITE)
            if default_db_sqlite:
                self.db = default_db_sqlite
            else:
                self.db = self.con_dets[my_globals.DBE_SQLITE].keys()[0]
        con = get_con(self.con_dets, self.db)
        cur = con.cursor() # must return tuples not dics
        return con, cur
      
    def get_db_dets(self):
        """
        Return connection, cursor, and get lists of 
            databases (only 1 for SQLite), tables, fields, and index info, 
            based on the SQLite database connection details provided.
        Sets db and tbl if not supplied.
        The database used will be the default SOFA db if nothing provided.
        The table used will be the default or the first if none provided.
        The field dets will be taken from the table used.
        Returns con, cur, dbs, tbls, flds, has_unique, idxs.
        """
        debug = False
        con, cur = self.get_con_cur()
        dbs = [self.db]
        tbls = self.get_db_tbls(cur, self.db)
        tbls_lc = [x.lower() for x in tbls]
        # get table (default if possible otherwise first)
        # NB table must be in the database
        if not self.tbl:
            # use default if possible
            default_tbl_sqlite = self.default_tbls.get(my_globals.DBE_SQLITE)
            if default_tbl_sqlite and default_tbl_sqlite.lower() in tbls_lc:
                self.tbl = default_tbl_sqlite
            else:
                try:
                    self.tbl = tbls[0]
                except IndexError:
                    raise Exception, u"No tables found in database \"%s\"" % \
                        self.db
        else:
            if self.tbl.lower() not in tbls_lc:
                raise Exception, u"Table \"%s\" not found " % self.tbl + \
                    u"in database \"%s\"" % self.db
        # get field names (from first table if none provided)
        flds = self.get_tbl_flds(cur, self.db, self.tbl)
        has_unique, idxs = self.get_index_dets(cur, self.db, self.tbl)
        if debug:
            print(self.db)
            print(self.tbl)
            pprint.pprint(tbls)
            pprint.pprint(flds)
            pprint.pprint(idxs)
        return con, cur, dbs, tbls, flds, has_unique, idxs
    
    def get_db_tbls(self, cur, db):
        "Get table names given database and cursor"
        SQL_get_tbl_names = u"""SELECT name 
            FROM sqlite_master 
            WHERE type = 'table'
            ORDER BY name"""
        cur.execute(SQL_get_tbl_names)
        tbls = [x[0] for x in cur.fetchall()]
        tbls.sort(key=lambda s: s.upper())
        return tbls

    def _getCharLen(self, type_text):
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
    
    def get_tbl_flds(self, cur, db, tbl):
        "http://www.sqlite.org/pragma.html"
        # get encoding
        cur.execute(u"PRAGMA encoding")
        encoding = cur.fetchone()[0]
        # get field details
        cur.execute(u"PRAGMA table_info(%s)" % tbl)
        fld_dets = cur.fetchall() 
        flds = {}
        for cid, fld_name, fld_type, notnull, dflt_value, pk in fld_dets:
            bolnullable = True if notnull == 0 else False
            bolnumeric = fld_type.lower() in NUMERIC_TYPES
            bolautonum = (pk == 1 and fld_type.lower() == "integer")            
            boldata_entry_ok = False if bolautonum else True
            boldatetime = fld_type.lower() in DATE_TYPES
            fld_txt = not bolnumeric and not boldatetime
            dets_dic = {
                my_globals.FLD_SEQ: cid,
                my_globals.FLD_BOLNULLABLE: bolnullable,
                my_globals.FLD_DATA_ENTRY_OK: boldata_entry_ok,
                my_globals.FLD_COLUMN_DEFAULT: dflt_value,
                my_globals.FLD_BOLTEXT: fld_txt,
                my_globals.FLD_TEXT_LENGTH: self._getCharLen(fld_type),
                my_globals.FLD_CHARSET: encoding,
                my_globals.FLD_BOLNUMERIC: bolnumeric,
                my_globals.FLD_BOLAUTONUMBER: bolautonum,
                my_globals.FLD_DECPTS: None, # not really applicable - no limit
                my_globals.FLD_NUM_WIDTH: None, # no limit (TODO unless check constraint)
                my_globals.FLD_BOL_NUM_SIGNED: True,
                my_globals.FLD_NUM_MIN_VAL: None, # not really applicable - no limit
                my_globals.FLD_NUM_MAX_VAL: None, # not really applicable - no limit
                my_globals.FLD_BOLDATETIME: boldatetime, 
                }
            flds[fld_name] = dets_dic
        return flds
    
    def get_index_dets(self, cur, db, tbl):
        """
        has_unique - booleanself.dropDefault_Dbe
        idxs = [idx0, idx1, ...]
        each idx is a dict name, is_unique, flds
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
                idx_dic = {my_globals.IDX_NAME: idx_name, 
                           my_globals.IDX_IS_UNIQUE: unique, 
                           my_globals.IDX_FLDS: fld_names}
                idxs.append(idx_dic)
        if debug:
            pprint.pprint(idxs)
            print(has_unique)
        return has_unique, idxs

def set_data_con_gui(parent, readonly, scroll, szr, lblfont):
    # default database
    parent.lblSqliteDefaultDb = wx.StaticText(scroll, -1, 
                                      _("Default Database (name only):"))
    parent.lblSqliteDefaultDb.SetFont(lblfont)
    DEFAULT_DB = parent.sqlite_default_db if parent.sqlite_default_db else ""
    parent.txtSqliteDefaultDb = wx.TextCtrl(scroll, -1, DEFAULT_DB, 
                                            size=(250,-1))
    parent.txtSqliteDefaultDb.Enable(not readonly)
    # default table
    parent.lblSqliteDefaultTbl = wx.StaticText(scroll, -1, _("Default Table:"))
    parent.lblSqliteDefaultTbl.SetFont(lblfont)
    DEFAULT_TBL = parent.sqlite_default_tbl if parent.sqlite_default_tbl \
        else ""
    parent.txtSqliteDefaultTbl = wx.TextCtrl(scroll, -1, DEFAULT_TBL, 
                                             size=(250,-1))
    parent.txtSqliteDefaultTbl.Enable(not readonly)
    bxSqlite = wx.StaticBox(scroll, -1, "SQLite")
    parent.szrSqlite = wx.StaticBoxSizer(bxSqlite, wx.VERTICAL)
    #3 SQLITE INNER
    szrSqliteInner = wx.BoxSizer(wx.HORIZONTAL)
    szrSqliteInner.Add(parent.lblSqliteDefaultDb, 0, wx.LEFT|wx.RIGHT, 5)
    szrSqliteInner.Add(parent.txtSqliteDefaultDb, 0, wx.RIGHT, 10)
    szrSqliteInner.Add(parent.lblSqliteDefaultTbl, 0, wx.LEFT|wx.RIGHT, 5)
    szrSqliteInner.Add(parent.txtSqliteDefaultTbl, 0, wx.RIGHT, 10)
    parent.szrSqlite.Add(szrSqliteInner, 0, wx.GROW)
    sqlite_col_dets = [{"col_label": _("Database(s)"), 
                        "col_type": settings_grid.COL_TEXT_BROWSE, 
                        "col_width": 400, 
                        "file_phrase": _("Choose an SQLite database file")}]
    parent.sqlite_config_data = []
    data = parent.sqlite_data[:]
    data.sort(key=lambda s: s[0])
    parent.sqlite_grid = settings_grid.SettingsEntry(frame=parent, 
        panel=scroll, szr=parent.szrSqlite, vert_share=1, readonly=readonly, 
        grid_size=(550, 100), col_dets=sqlite_col_dets, 
        data=parent.sqlite_data, config_data=parent.sqlite_config_data, 
        force_focus=True)
    szr.Add(parent.szrSqlite, 0, wx.GROW|wx.ALL, 10)

def get_proj_settings(parent, proj_dic):
    parent.sqlite_default_db = \
        proj_dic["default_dbs"].get(my_globals.DBE_SQLITE)
    parent.sqlite_default_tbl = \
        proj_dic["default_tbls"].get(my_globals.DBE_SQLITE)
    if proj_dic["con_dets"].get(my_globals.DBE_SQLITE):
        parent.sqlite_data = [(x["database"],) \
             for x in proj_dic["con_dets"][my_globals.DBE_SQLITE].values()]
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
    parent.sqlite_grid.update_config_data()
    DEFAULT_DB = parent.txtSqliteDefaultDb.GetValue()
    DEFAULT_TBL = parent.txtSqliteDefaultTbl.GetValue()
    has_sqlite_con = DEFAULT_DB and DEFAULT_TBL
    incomplete_sqlite = (DEFAULT_DB or DEFAULT_TBL) and not has_sqlite_con
    if incomplete_sqlite:
        wx.MessageBox(_("The SQLite details are incomplete"))
        parent.txtSqliteDefaultDb.SetFocus()
    default_dbs[my_globals.DBE_SQLITE] = DEFAULT_DB if DEFAULT_DB else None
    default_tbls[my_globals.DBE_SQLITE] = DEFAULT_TBL if DEFAULT_TBL else None
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
        con_dets[my_globals.DBE_SQLITE] = con_dets_sqlite        
    return incomplete_sqlite, has_sqlite_con

# unique to SQLite (because used to store tables for user-entered data plus 
# imported data)
def valid_name(name):
    """
    Bad name for SQLite?  The best way is to find out for real (not too 
        expensive and 100% valid by definition).
    """
    debug = False
    default_db = os.path.join(my_globals.LOCAL_PATH, my_globals.INTERNAL_FOLDER, 
                              u"sofa_tmp")
    con = sqlite.connect(default_db)
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