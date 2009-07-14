
from pysqlite2 import dbapi2 as sqlite
import pprint
import re
import wx

import my_globals
import getdata
import projects
import table_entry
import util

# http://www.sqlite.org/lang_keywords.html
# The following is non-standard but will work
def quote_obj(raw_val):
    return "`%s`" % raw_val

def quote_val(raw_val):
    return "\"%s\"" % raw_val

def DbeSyntaxElements():
    if_clause = "CASE WHEN %s THEN %s ELSE %s END"
    abs_wrapper_l = ""
    abs_wrapper_r = ""
    return if_clause, abs_wrapper_l, abs_wrapper_r


class DbDets(getdata.DbDets):

    def getDbTbls(self, cur, db):
        "Get table names given database and cursor"
        SQL_get_tbl_names = """SELECT name 
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

    def getTblFlds(self, cur, db, tbl):
        "http://www.sqlite.org/pragma.html"
        # get encoding
        cur.execute("PRAGMA encoding")
        encoding = cur.fetchone()[0]
        # get field details
        cur.execute("PRAGMA table_info(%s)" % tbl)
        fld_dets = cur.fetchall() 
        flds = {}
        for cid, fld_name, fld_type, notnull, dflt_value, pk in fld_dets:
            bolnullable = True if notnull == 0 else False
            bolnumeric = fld_type.lower() in ["integer", "float", "numeric", 
                                              "real"]
            bolautonum = (pk == 1 and fld_type.lower() == "integer")            
            boldata_entry_ok = False if bolautonum else True
            boldatetime = fld_type.lower() in ["date", "datetime", "time", 
                                               "timestamp"]
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
    
    def getIndexDets(self, cur, db, tbl):
        """
        has_unique - booleanself.dropDefault_Dbe
        idxs = [idx0, idx1, ...]
        each idx is a dict name, is_unique, flds
        """
        debug = False
        cur.execute("PRAGMA index_list(\"%s\")" % tbl)
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
                cur.execute("PRAGMA index_info(\"%s\")" % idx_name)
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
            print has_unique
        return has_unique, idxs
        
    def getDbDets(self):
        """
        Return connection, cursor, and get lists of 
            databases (only one for SQLite), tables, and fields 
            based on the SQLite database connection details provided.
        The database used will be the default SOFA db if nothing provided.
        The table used will be the first if none provided.
        The field dets will be taken from the table used.
        Returns conn, cur, dbs, tbls, flds, has_unique, idxs.
        """
        conn_dets_sqlite = self.conn_dets.get(my_globals.DBE_SQLITE)
        if not conn_dets_sqlite:
            raise Exception, "No connection details available for SQLite"
        if not self.db:
            self.db = my_globals.SOFA_DEFAULT_DB
        if not conn_dets_sqlite.get(self.db):
            raise Exception, "No connections for SQLite database %s" % \
                self.db
        conn = sqlite.connect(**conn_dets_sqlite[self.db])
        cur = conn.cursor() # must return tuples not dics
        dbs = [self.db]
        db_to_use = self.db
        tbls = self.getDbTbls(cur, self.db)
        # get field names (from first table if none provided)
        tbl_to_use = self.tbl if self.tbl else tbls[0]
        flds = self.getTblFlds(cur, self.db, tbl_to_use)
        has_unique, idxs = self.getIndexDets(cur, db_to_use, tbl_to_use)
        debug = False
        if debug:
            print self.db
            print self.tbl
            pprint.pprint(tbls)
            pprint.pprint(flds)
            pprint.pprint(idxs)
        return conn, cur, dbs, tbls, flds, has_unique, idxs

def setDbInConnDets(conn_dets, db):
    "Set database in connection details (if appropriate)"
    pass # only ever one database

def InsertRow(conn, cur, tbl_name, data):
    """
    data = [(value as string (or None), fld_name, fld_dets), ...]
    Modify any values (according to field details) to be ready for insertion.
    Use placeholders in execute statement.
    Commit insert statement.
    """
    debug = False
    if debug: pprint.pprint(data)
    fld_dics = [x[2] for x in data]
    fld_names = [x[1] for x in data]
    # http://www.sqlite.org/lang_keywords.html
    # The following is non-standard but will work
    fld_names_clause = " (`" + "`, `".join(fld_names) + "`) "
    # e.g. (`fname`, `lname`, `dob` ...)
    # http://docs.python.org/library/sqlite3.html re placeholders
    fld_placeholders_clause = " (" + \
        ", ".join(["?" for x in range(len(data))]) + ") "
    # e.g. " (?, ?, ? ...) "
    SQL_insert = "INSERT INTO `%s` " % tbl_name + fld_names_clause + \
        "VALUES %s" % fld_placeholders_clause
    if debug: print SQL_insert
    data_lst = []
    for i, data_dets in enumerate(data):
        if debug: pprint.pprint(data_dets)
        val, fld_name, fld_dic = data_dets
        val2use = getdata.PrepValue(val, fld_dic)
        data_lst.append(val2use)
    data_tup = tuple(data_lst)
    try:
        cur.execute(SQL_insert, data_tup)
        conn.commit()
        return True
    except Exception, e:
        if debug: print "Failed to insert row.  SQL: %s, Data: %s" % \
            (SQL_insert, str(data_tup)) + "\n\nOriginal error: %s" % e
        return False

def setDataConnGui(parent, read_only, scroll, szr, lblfont):
    ""
    # default database
    parent.lblSqliteDefaultDb = wx.StaticText(scroll, -1, "Default Database:")
    parent.lblSqliteDefaultDb.SetFont(lblfont)
    sqlite_default_db = parent.sqlite_default_db if parent.sqlite_default_db \
        else ""
    parent.txtSqliteDefaultDb = wx.TextCtrl(scroll, -1, 
                                            sqlite_default_db, 
                                            size=(250,-1))
    parent.txtSqliteDefaultDb.Enable(not read_only)
    # default table
    parent.lblSqliteDefaultTbl = wx.StaticText(scroll, -1, "Default Table:")
    parent.lblSqliteDefaultTbl.SetFont(lblfont)
    sqlite_default_tbl = parent.sqlite_default_tbl if parent.sqlite_default_tbl \
        else ""
    parent.txtSqliteDefaultTbl = wx.TextCtrl(scroll, -1,
                                             sqlite_default_tbl, 
                                             size=(250,-1))
    parent.txtSqliteDefaultTbl.Enable(not read_only)
    bxSqlite = wx.StaticBox(scroll, -1, "SQLite")
    parent.szrSqlite = wx.StaticBoxSizer(bxSqlite, wx.VERTICAL)
    #3 SQLITE INNER
    szrSqliteInner = wx.BoxSizer(wx.HORIZONTAL)
    szrSqliteInner.Add(parent.lblSqliteDefaultDb, 0, wx.LEFT|wx.RIGHT, 5)
    szrSqliteInner.Add(parent.txtSqliteDefaultDb, 1, wx.GROW|wx.RIGHT, 10)
    szrSqliteInner.Add(parent.lblSqliteDefaultTbl, 0, wx.LEFT|wx.RIGHT, 5)
    szrSqliteInner.Add(parent.txtSqliteDefaultTbl, 1, wx.GROW|wx.RIGHT, 10)
    parent.szrSqlite.Add(szrSqliteInner, 0)
    sqlite_col_dets = [("Database(s)", table_entry.COL_TEXT_BROWSE, 400, 
                        "Choose an SQLite database file")]
    parent.sqlite_new_grid_data = []
    parent.sqlite_grid = table_entry.TableEntry(frame=parent, 
        panel=scroll, szr=parent.szrSqlite, read_only=read_only, 
        grid_size=(550, 100), col_dets=sqlite_col_dets, 
        data=parent.sqlite_data, new_grid_data=parent.sqlite_new_grid_data)
    szr.Add(parent.szrSqlite, 0, wx.GROW|wx.ALL, 10)

def getProjSettings(parent, proj_dic):
    ""
    parent.sqlite_default_db = proj_dic["default_dbs"][my_globals.DBE_SQLITE]
    parent.sqlite_default_tbl = proj_dic["default_tbls"][my_globals.DBE_SQLITE]
    if proj_dic["conn_dets"].get(my_globals.DBE_SQLITE):
        parent.sqlite_data = [(x["database"],) \
             for x in proj_dic["conn_dets"][my_globals.DBE_SQLITE].values()]
    else:
        parent.sqlite_data = []

def setConnDetDefaults(parent):
    try:            
        parent.sqlite_default_db
    except AttributeError: 
        parent.sqlite_default_db = ""
    try:
        parent.sqlite_default_tbl
    except AttributeError: 
        parent.sqlite_default_tbl = ""
    try:
        parent.sqlite_data
    except AttributeError: 
        parent.sqlite_data = []

def processConnDets(parent, default_dbs, default_tbls, conn_dets):
    parent.sqlite_grid.UpdateNewGridData()
    sqlite_default_db = parent.txtSqliteDefaultDb.GetValue()
    sqlite_default_tbl = parent.txtSqliteDefaultTbl.GetValue()
    has_sqlite_conn = sqlite_default_db and sqlite_default_tbl
    incomplete_sqlite = (sqlite_default_db or sqlite_default_tbl) \
        and not has_sqlite_conn
    if incomplete_sqlite:
        wx.MessageBox("The SQLite details are incomplete")
        parent.txtSqliteDefaultDb.SetFocus()
    default_dbs[my_globals.DBE_SQLITE] = sqlite_default_db \
        if sqlite_default_db else None
    default_tbls[my_globals.DBE_SQLITE] = sqlite_default_tbl \
        if sqlite_default_tbl else None
    #pprint.pprint(parent.sqlite_new_grid_data) # debug
    sqlite_settings = parent.sqlite_new_grid_data
    if sqlite_settings:
        conn_dets_sqlite = {}
        for sqlite_setting in sqlite_settings:
            # e.g. ("C:\.....\my_sqlite_db",)
            db_path = sqlite_setting[0]
            db_name = parent.getFileName(db_path)
            new_sqlite_dic = {}
            new_sqlite_dic["database"] = db_path
            conn_dets_sqlite[db_name] = new_sqlite_dic
        conn_dets[my_globals.DBE_SQLITE] = conn_dets_sqlite        
    return incomplete_sqlite, has_sqlite_conn

