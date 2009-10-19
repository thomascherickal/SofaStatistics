#Must run makepy once - 
#see http://www.thescripts.com/forum/thread482449.html e.g. the following 
#way - run PYTHON\Lib\site-packages\pythonwin\pythonwin.exe (replace 
#PYTHON with folder python is in).  Tools>COM Makepy utility - select 
#appropriate library - e.g. for ADO it would be 
# Microsoft ActiveX Data Objects 2.8 Library (2.8) - and 
#select OK.  NB DAO has to be done separately from ADO etc.

from __future__ import print_function
import adodbapi
import os
import pprint
import win32com.client
import wx

import my_globals
import dbe_plugins.dbe_globals as dbe_globals
import getdata
import settings_grid


AD_OPEN_KEYSET = 1
AD_LOCK_OPTIMISTIC = 3
AD_SCHEMA_COLUMNS = 4

MSACCESS_DEFAULT_DB = "msaccess_default_db"
MSACCESS_DEFAULT_TBL = "msaccess_default_tbl"

def quote_obj(raw_val):
    return "[%s]" % raw_val

def quote_val(raw_val):
    return "'%s'" % raw_val.replace("'", "''") # escape internal single quotes

def get_placeholder():
    return "?"

def get_summable(clause):
    return "ABS(%s)" % clause # true is -1 so we need to get sum of +1s

def DbeSyntaxElements():
    if_clause = "IIF(%s, %s, %s)"
    return (if_clause, quote_obj, quote_val, get_placeholder, get_summable)

    
class DbDets(getdata.DbDets):
    
    """
    __init__ supplies default_dbs, default_tbls, conn_dets and 
        db and tbl (may be None).
    """
        
    def getDbDets(self):
        """
        Return connection, cursor, and get lists of 
            databases, tables, fields, and index info, 
            based on the MS Access database connection details provided.
        Sets db and tbl if not supplied.
        Connection string as per the ADO documentation.
        The database used will be the default or the first if none provided.
        The table used will be the default or the first if none provided.
        The field dets will be taken from the table used.
        Returns conn, cur, dbs, tbls, flds, has_unique, idxs.
        """
        # get connection details for appropriate database
        conn_dets_access = self.conn_dets.get(my_globals.DBE_MS_ACCESS)
        if not conn_dets_access:
            raise Exception, "No connection details available for MS Access"
        # get the (only) database and use it to get the connection details
        if not self.db:
            # use default if possible, or fall back to random
            default_db_access = self.default_dbs.get(my_globals.DBE_MS_ACCESS)
            if default_db_access:
                self.db = default_db_access
            else:
                # conn_dets_access[0]["database"] e.g. u'C:\\mydata\\data.mdb'
                full_db_path = conn_dets_access[0]["database"]
                self.db = os.path.split(full_db_path)[1]
        if not conn_dets_access.get(self.db):
            raise Exception, "No connections for MS Access database %s" % \
                self.db
        conn_dets_access_db = conn_dets_access[self.db]
        """DSN syntax - http://support.microsoft.com/kb/193332 and 
        http://www.codeproject.com/database/connectionstrings.asp ...
        ... ?df=100&forumid=3917&exp=0&select=1598401"""
        database = conn_dets_access_db["database"]
        user = conn_dets_access_db["user"]
        pwd = conn_dets_access_db["pwd"]
        mdw = conn_dets_access_db["mdw"]
        DSN = """PROVIDER=Microsoft.Jet.OLEDB.4.0;DATA SOURCE=%s;
            USER ID=%s;PASSWORD=%s;Jet OLEDB:System Database=%s;""" % \
            (database, user, pwd, mdw)
        try:
            conn = adodbapi.connect(connstr=DSN)
        except Exception, e:
            raise Exception, "Unable to connect to MS Access database " + \
                "using supplied database: %s, user: %s, " % (database, user) + \
                "pwd: %s, or mdw: %s.  Orig error: %s" % (pwx, mdw, e)
        cur = conn.cursor() # must return tuples not dics
        cur.adoconn = conn.adoConn # (need to be able to access from just the cursor)
        # get database name
        dbs = [self.db]
        tbls = self.getDbTbls(cur, self.db)
        tbls_lc = [x.lower() for x in tbls]
        # get table (default if possible otherwise first)
        # NB table must be in the database
        if not self.tbl:
            # use default if possible
            default_tbl_access = self.default_tbls.get(my_globals.DBE_MS_ACCESS)
            if default_tbl_access and default_tbl_access.lower() in tbls_lc:
                self.tbl = default_tbl_access
            else:
                self.tbl = tbls[0]
        else:
            if self.tbl.lower() not in tbls_lc:
                raise Exception, "Table \"%s\" not found in database \"%s\"" % \
                    (self.tbl, self.db)
        # get field names (from first table if none provided)
        flds = self.getTblFlds(cur, self.db, self.tbl)
        has_unique, idxs = self.getIndexDets(cur, self.db, self.tbl)
        debug = False
        if debug:
            print(self.db)
            print(self.tbl)
            pprint.pprint(tbls)
            pprint.pprint(flds)
            pprint.pprint(idxs)
        return conn, cur, dbs, tbls, flds, has_unique, idxs

    def getDbTbls(self, cur, db):
        "Get table names given database and cursor. NB not system tables"
        tbls = []
        cat = win32com.client.Dispatch(r'ADOX.Catalog')
        cat.ActiveConnection = cur.adoconn
        alltables = cat.Tables
        tbls = []
        for tab in alltables:
            if tab.Type == 'TABLE':
                tbls.append(tab.Name)
        cat = None
        return tbls

    def getTblFlds(self, cur, db, tbl):
        """
        Returns details for set of fields given database, table, and cursor.
        NUMERIC_SCALE - number of significant digits to right of decimal point.
        NUMERIC_SCALE should be Null if not numeric (but is in fact 255 so 
            I must set to None!).
        """
        #http://msdn.microsoft.com/en-us/library/aa155430(office.10).aspx
        cat = win32com.client.Dispatch(r'ADOX.Catalog') # has everything I 
            # need but pos and charset
        cat.ActiveConnection = cur.adoconn
        # extra properties which can't be obtained from cat.Tables.Columns
        # viz ordinal position and charset
        # Do not add fourth constraint(None, None, "tbltest", None) will not work!
        # It should (see http://www.w3schools.com/ADO/met_conn_openschema.asp) but ...
        extras = {}
        rs = cur.adoconn.OpenSchema(AD_SCHEMA_COLUMNS, (None, None, tbl)) 
        while not rs.EOF:
            fld_name = rs.Fields("COLUMN_NAME").Value
            ord_pos = rs.Fields("ORDINAL_POSITION").Value
            char_set = rs.Fields("CHARACTER_SET_NAME").Value
            extras[fld_name] = (ord_pos, char_set)
            rs.MoveNext()
        flds = {}
        for col in cat.Tables(tbl).Columns:
            # build dic of fields, each with dic of characteristics
            fld_name = col.Name            
            fld_type = dbe_globals.getADODic().get(col.Type)
            if not fld_type:
                raise Exception, "Not an MS Access ADO field type %d" % col.Type
            bolautonum = col.Properties("AutoIncrement").Value
            boldata_entry_ok = False if bolautonum else True
            bolnumeric = fld_type in dbe_globals.NUMERIC_TYPES
            dec_pts = col.NumericScale if col.NumericScale < 18 else 0
            boldatetime = fld_type in dbe_globals.DATETIME_TYPES
            fld_txt = not bolnumeric and not boldatetime
            num_prec = col.Precision
            min_val, max_val = dbe_globals.GetMinMax(fld_type, num_prec, 
                                                     dec_pts)
            dets_dic = {
                my_globals.FLD_SEQ: extras[fld_name][0],
                my_globals.FLD_BOLNULLABLE: col.Properties("Nullable").Value,
                my_globals.FLD_DATA_ENTRY_OK: boldata_entry_ok,
                my_globals.FLD_COLUMN_DEFAULT: col.Properties("Default").Value,
                my_globals.FLD_BOLTEXT: fld_txt,
                my_globals.FLD_TEXT_LENGTH: col.DefinedSize,
                my_globals.FLD_CHARSET: extras[fld_name][1],
                my_globals.FLD_BOLNUMERIC: bolnumeric,
                my_globals.FLD_BOLAUTONUMBER: bolautonum,
                my_globals.FLD_DECPTS: dec_pts,
                my_globals.FLD_NUM_WIDTH: num_prec,
                my_globals.FLD_BOL_NUM_SIGNED: True,
                my_globals.FLD_NUM_MIN_VAL: min_val,
                my_globals.FLD_NUM_MAX_VAL: max_val,
                my_globals.FLD_BOLDATETIME: boldatetime, 
            }
            flds[fld_name] = dets_dic
        debug = False 
        if debug:
            pprint.pprint(flds)
        cat = None
        return flds  

    def getIndexDets(self, cur, db, tbl):
        """
        has_unique - boolean
        idxs = [idx0, idx1, ...]
        each idx is a dict name, is_unique, flds
        """
        cat = win32com.client.Dispatch(r'ADOX.Catalog')
        cat.ActiveConnection = cur.adoconn
        index_coll = cat.Tables(tbl).Indexes
        # initialise
        has_unique = False
        idxs = []
        for index in index_coll:
            if index.Unique:
                has_unique = True
            fld_names = [x.Name for x in index.Columns]
            idx_dic = {my_globals.IDX_NAME: index.Name, 
                       my_globals.IDX_IS_UNIQUE: index.Unique, 
                       my_globals.IDX_FLDS: fld_names}
            idxs.append(idx_dic)
        cat = None
        debug = False
        if debug:
            pprint.pprint(idxs)
            print(has_unique)
        return has_unique, idxs

def InsertRow(conn, cur, tbl_name, data):
    """
    data = [(value as string (or None), fld_name, fld_dets), ...]
    Modify any values (according to field details) to be ready for insertion.
    Use placeholders in execute statement.
    Commit insert statement.
    TODO - test this in Windows.
    """
    debug = False
    if debug: pprint.pprint(data)
    fld_dics = [x[2] for x in data]
    fld_names = [x[1] for x in data]
    fld_names_clause = " ([" + "], [".join(fld_names) + "]) "
    # e.g. (`fname`, `lname`, `dob` ...)
    fld_placeholders_clause = " (" + \
        ", ".join(["%s" for x in range(len(data))]) + ") "
    # e.g. " (%s, %s, %s ...) "
    SQL_insert = "INSERT INTO `%s` " % tbl_name + fld_names_clause + \
        "VALUES %s" % fld_placeholders_clause
    if debug: print(SQL_insert)
    data_lst = []
    for i, data_dets in enumerate(data):
        if debug: pprint.pprint(data_dets)
        val, fld_name, fld_dic = data_dets
        val2use = getdata.PrepValue(my_globals.DBE_MS_ACCESS, val, fld_dic)
        data_lst.append(val2use)
    data_tup = tuple(data_lst)
    try:
        cur.execute(SQL_insert, data_tup)
        conn.commit()
        return True
    except Exception, e:
        if debug: print("Failed to insert row.  SQL: %s, Data: %s" %
            (SQL_insert, str(data_tup)) + "\n\nOriginal error: %s" % e)
        return False

def setDataConnGui(parent, read_only, scroll, szr, lblfont):
    ""
    # default database
    parent.lblMsaccessDefaultDb = wx.StaticText(scroll, -1, 
                                                "Default Database (name only):")
    parent.lblMsaccessDefaultDb.SetFont(lblfont)
    MSACCESS_DEFAULT_DB = parent.msaccess_default_db \
        if parent.msaccess_default_db else ""
    parent.txtMsaccessDefaultDb = wx.TextCtrl(scroll, -1, MSACCESS_DEFAULT_DB, 
                                              size=(250,-1))
    parent.txtMsaccessDefaultDb.Enable(not read_only)
    # default table
    parent.lblMsaccessDefaultTbl = wx.StaticText(scroll, -1, 
                                                 "Default Table:")
    parent.lblMsaccessDefaultTbl.SetFont(lblfont)
    MSACCESS_DEFAULT_TBL = parent.msaccess_default_tbl \
        if parent.msaccess_default_tbl else ""
    parent.txtMsaccessDefaultTbl = wx.TextCtrl(scroll, -1, MSACCESS_DEFAULT_TBL, 
                                               size=(250,-1))
    parent.txtMsaccessDefaultTbl.Enable(not read_only)
    bxMsaccess= wx.StaticBox(scroll, -1, "MS Access")
    parent.szrMsaccess = wx.StaticBoxSizer(bxMsaccess, wx.VERTICAL)
    #3 MS ACCESS INNER
    szrMsaccessInner = wx.BoxSizer(wx.HORIZONTAL)
    szrMsaccessInner.Add(parent.lblMsaccessDefaultDb, 0, 
                         wx.LEFT|wx.RIGHT, 5)
    szrMsaccessInner.Add(parent.txtMsaccessDefaultDb, 1, 
                         wx.GROW|wx.RIGHT, 10)
    szrMsaccessInner.Add(parent.lblMsaccessDefaultTbl, 0, 
                         wx.LEFT|wx.RIGHT, 5)
    szrMsaccessInner.Add(parent.txtMsaccessDefaultTbl, 1, 
                         wx.GROW|wx.RIGHT, 10)
    parent.szrMsaccess.Add(szrMsaccessInner, 0)
    col_det_db = {"col_label": "Database(s)", 
                  "col_type": settings_grid.COL_TEXT_BROWSE, 
                  "col_width": 300, 
                  "file_phrase": "Choose an MS Access database file", 
                  "file_wildcard": "MS Access databases (*.mdb)|*.mdb",
                  "empty_ok": False}
    col_det_sec = {"col_label": "Security File (*.mdw) (opt)", 
                  "col_type": settings_grid.COL_TEXT_BROWSE, 
                  "col_width": 300, 
                  "file_phrase": "Choose an MS Access security file", 
                  "file_wildcard": "MS Access security files (*.mdw)|*.mdw",
                  "empty_ok": True}
    col_det_usr = {"col_label": "User Name (opt)", 
                  "col_type": settings_grid.COL_STR, 
                  "col_width": 140, 
                  "file_phrase": None, 
                  "file_wildcard": None,
                  "empty_ok": True}
    col_det_pwd = {"col_label": "Password (opt)", 
                  "col_type": settings_grid.COL_STR, 
                  "col_width": 140, 
                  "file_phrase": None, 
                  "file_wildcard": None,
                  "empty_ok": True}
    msaccess_col_dets = [col_det_db, col_det_sec, col_det_usr, col_det_pwd]
    parent.msaccess_new_grid_data = []
    parent.msaccess_grid = settings_grid.TableEntry(frame=parent, 
        panel=scroll, szr=parent.szrMsaccess, vert_share=1, read_only=read_only, 
        grid_size=(1000, 100), col_dets=msaccess_col_dets, 
        data=parent.msaccess_data, 
        new_grid_data=parent.msaccess_new_grid_data)
    szr.Add(parent.szrMsaccess, 0, wx.GROW|wx.ALL, 10)

def getProjSettings(parent, proj_dic):
    ""
    parent.msaccess_default_db = \
        proj_dic["default_dbs"].get(my_globals.DBE_MS_ACCESS)
    parent.msaccess_default_tbl = \
        proj_dic["default_tbls"].get(my_globals.DBE_MS_ACCESS)
    if proj_dic["conn_dets"].get(my_globals.DBE_MS_ACCESS):
        parent.msaccess_data = [(x["database"], x["mdw"], x["user"], 
                                 x["pwd"]) \
            for x in proj_dic["conn_dets"][my_globals.DBE_MS_ACCESS].values()]
    else:
        parent.msaccess_data = []

def setConnDetDefaults(parent):
    try:
        parent.msaccess_default_db
    except AttributeError:
        parent.msaccess_default_db = ""
    try:
        parent.msaccess_default_tbl
    except AttributeError:
        parent.msaccess_default_tbl = ""
    try:
        parent.msaccess_data
    except AttributeError:
        parent.msaccess_data = []

def processConnDets(parent, default_dbs, default_tbls, conn_dets):
    parent.msaccess_grid.UpdateNewGridData()
    MSACCESS_DEFAULT_DB = parent.txtMsaccessDefaultDb.GetValue()
    MSACCESS_DEFAULT_TBL = parent.txtMsaccessDefaultTbl.GetValue()
    has_msaccess_conn = MSACCESS_DEFAULT_DB and MSACCESS_DEFAULT_TBL
    incomplete_msaccess = (MSACCESS_DEFAULT_DB or MSACCESS_DEFAULT_TBL) \
        and not has_msaccess_conn
    if incomplete_msaccess:
        wx.MessageBox("The MS Access details are incomplete")
        parent.txtMsaccessDefaultDb.SetFocus()
    default_dbs[my_globals.DBE_MS_ACCESS] = MSACCESS_DEFAULT_DB \
        if MSACCESS_DEFAULT_DB else None            
    default_tbls[my_globals.DBE_MS_ACCESS] = MSACCESS_DEFAULT_TBL \
        if MSACCESS_DEFAULT_TBL else None
    #pprint.pprint(parent.msaccess_new_grid_data) # debug
    msaccess_settings = parent.msaccess_new_grid_data
    if msaccess_settings:
        conn_dets_msaccess = {}
        for msaccess_setting in msaccess_settings:
            db_path = msaccess_setting[0]
            db_name = parent.getFileName(db_path)
            new_msaccess_dic = {}
            new_msaccess_dic["database"] = db_path
            new_msaccess_dic["mdw"] = msaccess_setting[1]
            new_msaccess_dic["user"] = msaccess_setting[2]
            new_msaccess_dic["pwd"] = msaccess_setting[3]
            conn_dets_msaccess[db_name] = new_msaccess_dic
        conn_dets[my_globals.DBE_MS_ACCESS] = conn_dets_msaccess
    return incomplete_msaccess, has_msaccess_conn
