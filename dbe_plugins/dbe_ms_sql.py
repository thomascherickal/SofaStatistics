#Must run makepy once - 
#see http://www.thescripts.com/forum/thread482449.html e.g. the following 
#way - run PYTHON\Lib\site-packages\pythonwin\pythonwin.exe (replace 
#PYTHON with folder python is in).  Tools>COM Makepy utility - select 
#appropriate library - e.g. for ADO it would be 
# Microsoft ActiveX Data Objects 2.8 Library (2.8) - and 
#select OK.  NB DAO has to be done separately from ADO etc.

from __future__ import print_function
import adodbapi
import win32com.client

import wx
import pprint

import my_globals
import dbe_plugins.dbe_globals as dbe_globals
import getdata

AD_OPEN_KEYSET = 1
AD_LOCK_OPTIMISTIC = 3
AD_SCHEMA_COLUMNS = 4


def quote_obj(raw_val):
    return u"[%s]" % raw_val

def quote_val(raw_val):
    try:
        val = raw_val.replace("'", "''")
    except AttributeError, e:
        raise Exception, ("Inappropriate attempt to quote non-string value. "
                          "Orig error: %s" % e)
    return u"'%s'" % val

def get_placeholder():
    return u"?"

def get_summable(clause):
    return u"CASE WHEN %s THEN 1 ELSE 0 END" % clause

def DbeSyntaxElements():
    if_clause = u"CASE WHEN %s THEN %s ELSE %s END"
    return (if_clause, quote_obj, quote_val, get_placeholder, get_summable)

    
class DbDets(getdata.DbDets):
    
    """
    __init__ supplies default_dbs, default_tbls, con_dets and 
        db and tbl (may be None).  Db needs to be set in con_dets once 
        identified.
    """
    
    debug = False
    
    def get_con_cur(self):
        con_dets_mssql = self.con_dets.get(my_globals.DBE_MS_SQL)
        if not con_dets_mssql:
            raise Exception, (u"No connection details available for "
                              "MS SQL Server")
        host = con_dets_mssql["host"]
        user = con_dets_mssql["user"]
        pwd = con_dets_mssql["passwd"]
        self.dbs, self.db = self._getDbs(host, user, pwd)
        setDbInConDets(con_dets_mssql, self.db)
        DSN = u"""PROVIDER=SQLOLEDB;
            Data Source='%s';
            User ID='%s';
            Password='%s';
            Initial Catalog='%s';
            Integrated Security=SSPI""" % (host, user, pwd, self.db)
        try:
            con = adodbapi.connect(connstr=DSN)
        except Exception, e:
            raise Exception, u"Unable to connect to MS SQL Server with " + \
                u"database %s; and supplied connection: " % self.db + \
                u"host: %s; user: %s; pwd: %s. " % (host, user, pwd) + \
                u"Orig error: %s" % e
        cur = con.cursor()
        cur.adoconn = con.adoConn # (need to access from just the cursor)        
        return con, cur
    
    def getDbDets(self):
        """
        Return connection, cursor, and get lists of 
            databases, tables, fields, and index info,
            based on the MS SQL Server database connection details provided.
        Sets db and tbl if not supplied.
        The database used will be the default or the first if none provided.
        The table used will be the default or the first if none provided.
        The field dets will be taken from the table used.
        Returns con, cur, dbs, tbls, flds, has_unique, idxs.
        """
        debug = False
        con, cur = self.get_con_cur()
        tbls = self.getDbTbls(cur, self.db)
        if debug: print(tbls)
        tbls_lc = [x.lower() for x in tbls]        
        # get table (default if possible otherwise first)
        # NB table must be in the database
        if not self.tbl:
            # use default if possible
            default_tbl_mssql = self.default_tbls.get(my_globals.DBE_MS_SQL)
            if default_tbl_mssql and default_tbl_mssql.lower() in tbls_lc:
                self.tbl = default_tbl_mssql
            else:
                try:
                    self.tbl = tbls[0]
                except IndexError:
                    raise Exception, u"No tables found in database \"%s\"" % \
                        self.db
        else:
            if self.tbl.lower() not in tbls_lc:
                raise Exception, u"Table \"%s\" not found " % self.tbl + \
                    "in database \"%s\"" % self.db
        # get field names (from first table if none provided)
        flds = self.getTblFlds(cur, self.db, self.tbl)
        has_unique, idxs = self.getIndexDets(cur, self.db, self.tbl)
        if debug:
            print(self.db)
            print(self.tbl)
            pprint.pprint(tbls)
            pprint.pprint(flds)
            pprint.pprint(idxs)
        return con, cur, self.dbs, tbls, flds, has_unique, idxs

    def _getDbs(self, host, user, pwd):
        """
        Get dbs and the db to use.
        NB need to use a separate connection here with db Initial Catalog) 
            undefined.        
        """
        DSN = u"""PROVIDER=SQLOLEDB;
            Data Source='%s';
            User ID='%s';
            Password='%s';
            Initial Catalog='';
            Integrated Security=SSPI""" % (host, user, pwd)
        try:
            con = adodbapi.connect(connstr=DSN)
        except Exception, e:
            raise Exception, u"Unable to connect to MS SQL Server " + \
                u"with host: %s; user: %s; and pwd: %s" % (host, user, pwd)
        cur = con.cursor() # must return tuples not dics
        cur.execute(u"SELECT name FROM sysdatabases")
        dbs = [x[0] for x in cur.fetchall()]
        dbs_lc = [x.lower() for x in dbs]
        # get db (default if possible otherwise first)
        # NB db must be accessible from connection
        if not self.db:
            # use default if possible, or fall back to first
            default_db_mssql = self.default_dbs.get(my_globals.DBE_MS_SQL)
            if default_db_mssql.lower() in dbs_lc:
                db = default_db_mssql
            else:
                db = dbs[0]
        else:
            if self.db.lower() not in dbs_lc:
                raise Exception, u"Database \"%s\" not available " % self.db + \
                    u"from supplied connection"
            else:
                db = self.db
        cur.close()
        con.close()
        return dbs, db

    def getDbTbls(self, cur, db):
        "Get table names given database and cursor. NB not system tables"
        tbls = []
        cat = win32com.client.Dispatch(r'ADOX.Catalog')
        cat.ActiveConnection = cur.adoconn
        alltables = cat.Tables
        tbls = []
        for tab in alltables:
            if tab.Type == "TABLE":
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
        debug = False
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
            fld_name = rs.Fields(u"COLUMN_NAME").Value
            ord_pos = rs.Fields(u"ORDINAL_POSITION").Value
            char_set = rs.Fields(u"CHARACTER_SET_NAME").Value
            extras[fld_name] = (ord_pos, char_set)
            rs.MoveNext()
        flds = {}
        for col in cat.Tables(tbl).Columns:
            # build dic of fields, each with dic of characteristics
            fld_name = col.Name
            if debug: print(col.Type)
            fld_type = dbe_globals.getADODic().get(col.Type)
            if not fld_type:
                raise Exception, u"Not an MS SQL Server ADO field type %d" % \
                    col.Type
            bolnumeric = fld_type in dbe_globals.NUMERIC_TYPES
            try:
                bolautonum = col.Properties(u"AutoIncrement").Value
            except Exception:
                bolautonum = False
            try:
                bolnullable = col.Properties(u"Nullable").Value
            except Exception:
                bolnullable = False
            try:
                default = col.Properties(u"Default").Value
            except Exception:
                default = ""
            boldata_entry_ok = False if bolautonum else True
            dec_pts = col.NumericScale if col.NumericScale < 18 else 0
            boldatetime = fld_type in dbe_globals.DATETIME_TYPES
            fld_txt = not bolnumeric and not boldatetime
            num_prec = col.Precision
            min_val, max_val = dbe_globals.GetMinMax(fld_type, num_prec, 
                                                     dec_pts)
            dets_dic = {
                my_globals.FLD_SEQ: extras[fld_name][0],
                my_globals.FLD_BOLNULLABLE: bolnullable,
                my_globals.FLD_DATA_ENTRY_OK: boldata_entry_ok,
                my_globals.FLD_COLUMN_DEFAULT: default,
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

def setDbInConDets(con_dets, db):
    "Set database in connection details (if appropriate)"
    con_dets[u"db"] = db

def InsertRow(con, cur, tbl_name, data):
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
    fld_names_clause = u" ([" + u"], [".join(fld_names) + u"]) "
    # e.g. (`fname`, `lname`, `dob` ...)
    fld_placeholders_clause = u" (" + \
        u", ".join([u"%s" for x in range(len(data))]) + u") "
    # e.g. " (%s, %s, %s ...) "
    SQL_insert = u"INSERT INTO `%s` " % tbl_name + fld_names_clause + \
        u"VALUES %s" % fld_placeholders_clause
    if debug: print(SQL_insert)
    data_lst = []
    for i, data_dets in enumerate(data):
        if debug: pprint.pprint(data_dets)
        val, fld_name, fld_dic = data_dets
        val2use = getdata.PrepValue(my_globals.DBE_MS_SQL, val, fld_dic)
        data_lst.append(val2use)
    data_tup = tuple(data_lst)
    try:
        cur.execute(SQL_insert, data_tup)
        con.commit()
        return True, None
    except Exception, e:
        if debug: print(u"Failed to insert row.  SQL: %s, Data: %s" %
            (SQL_insert, unicode(data_tup)) + u"\n\nOriginal error: %s" % e)
        return False, u"%s" % e

def setDataConGui(parent, read_only, scroll, szr, lblfont):
    ""
    # default database
    parent.lblMssqlDefaultDb = wx.StaticText(scroll, -1, 
                                             _("Default Database (name only):"))
    parent.lblMssqlDefaultDb.SetFont(lblfont)
    mssql_default_db = parent.mssql_default_db if parent.mssql_default_db \
        else ""
    parent.txtMssqlDefaultDb = wx.TextCtrl(scroll, -1, 
                                           mssql_default_db, 
                                           size=(250,-1))
    parent.txtMssqlDefaultDb.Enable(not read_only)
    # default table
    parent.lblMssqlDefaultTbl = wx.StaticText(scroll, -1, 
                                       _("Default Table:"))
    parent.lblMssqlDefaultTbl.SetFont(lblfont)
    mssql_default_tbl = parent.mssql_default_tbl if parent.mssql_default_tbl \
        else ""
    parent.txtMssqlDefaultTbl = wx.TextCtrl(scroll, -1, 
                                            mssql_default_tbl, 
                                            size=(250,-1))
    parent.txtMssqlDefaultTbl.Enable(not read_only)
    # host
    parent.lblMssqlHost = wx.StaticText(scroll, -1, 
                                        _("Host - (local) if own machine:"))
    parent.lblMssqlHost.SetFont(lblfont)
    mssql_host = parent.mssql_host
    parent.txtMssqlHost = wx.TextCtrl(scroll, -1, mssql_host, 
                                      size=(100,-1))
    parent.txtMssqlHost.Enable(not read_only)
    # user
    parent.lblMssqlUser = wx.StaticText(scroll, -1, _("User:"))
    parent.lblMssqlUser.SetFont(lblfont)
    mssql_user = parent.mssql_user if parent.mssql_user else ""
    parent.txtMssqlUser = wx.TextCtrl(scroll, -1, mssql_user, 
                                      size=(100,-1))
    parent.txtMssqlUser.Enable(not read_only)
    # password
    parent.lblMssqlPwd = wx.StaticText(scroll, -1, 
                                       _("Password - space if none:"))
    parent.lblMssqlPwd.SetFont(lblfont)
    mssql_pwd = parent.mssql_pwd if parent.mssql_pwd else ""
    parent.txtMssqlPwd = wx.TextCtrl(scroll, -1, mssql_pwd, 
                                     size=(300,-1))
    parent.txtMssqlPwd.Enable(not read_only)
    #2 MS SQL SERVER
    bxMssql= wx.StaticBox(scroll, -1, u"Microsoft SQL Server")
    parent.szrMssql = wx.StaticBoxSizer(bxMssql, wx.VERTICAL)
    #3 MSSQL INNER
    #4 MSSQL INNER TOP
    szrMssqlInnerTop = wx.BoxSizer(wx.HORIZONTAL)
    # default database
    szrMssqlInnerTop.Add(parent.lblMssqlDefaultDb, 0, wx.LEFT|wx.RIGHT, 5)
    szrMssqlInnerTop.Add(parent.txtMssqlDefaultDb, 1, wx.GROW|wx.RIGHT, 10)
    # default table
    szrMssqlInnerTop.Add(parent.lblMssqlDefaultTbl, 0, wx.LEFT|wx.RIGHT, 5)
    szrMssqlInnerTop.Add(parent.txtMssqlDefaultTbl, 1, wx.GROW|wx.RIGHT, 10)
    #4 MSSQL INNER BOTTOM
    szrMssqlInnerBtm = wx.BoxSizer(wx.HORIZONTAL)
    # host 
    szrMssqlInnerBtm.Add(parent.lblMssqlHost, 0, wx.LEFT|wx.RIGHT, 5)
    szrMssqlInnerBtm.Add(parent.txtMssqlHost, 0, wx.RIGHT, 10)
    # user
    szrMssqlInnerBtm.Add(parent.lblMssqlUser, 0, wx.LEFT|wx.RIGHT, 5)
    szrMssqlInnerBtm.Add(parent.txtMssqlUser, 0, wx.RIGHT, 10)
    # password
    szrMssqlInnerBtm.Add(parent.lblMssqlPwd, 0, wx.LEFT|wx.RIGHT, 5)
    szrMssqlInnerBtm.Add(parent.txtMssqlPwd, 1, wx.GROW|wx.RIGHT, 10)
    #2 combine
    parent.szrMssql.Add(szrMssqlInnerTop, 0, wx.GROW|wx.ALL, 5)
    parent.szrMssql.Add(szrMssqlInnerBtm, 0, wx.ALL, 5)
    szr.Add(parent.szrMssql, 0, wx.GROW|wx.ALL, 10)

def getProjSettings(parent, proj_dic):
    ""
    parent.mssql_default_db = \
        proj_dic[u"default_dbs"].get(my_globals.DBE_MS_SQL)
    parent.mssql_default_tbl = \
        proj_dic[u"default_tbls"].get(my_globals.DBE_MS_SQL)
    # optional (although if any mssql, for eg, must have all)
    if proj_dic[u"con_dets"].get(my_globals.DBE_MS_SQL):
        parent.mssql_host = proj_dic["con_dets"][my_globals.DBE_MS_SQL]["host"]
        parent.mssql_user = proj_dic["con_dets"][my_globals.DBE_MS_SQL]["user"]
        parent.mssql_pwd = proj_dic["con_dets"][my_globals.DBE_MS_SQL]["passwd"]
    else:
        parent.mssql_host, parent.mssql_user, parent.mssql_pwd = "", "", ""

def setConDetDefaults(parent):
    try:
        parent.mssql_default_db
    except AttributeError:
        parent.mssql_default_db = u""
    try:
        parent.mssql_default_tbl
    except AttributeError: 
        parent.mssql_default_tbl = u""
    try:
        parent.mssql_host
    except AttributeError: 
        parent.mssql_host = u""
    try:
        parent.mssql_user
    except AttributeError: 
        parent.mssql_user = u""
    try:            
        parent.mssql_pwd
    except AttributeError: 
        parent.mssql_pwd = u""

def processConDets(parent, default_dbs, default_tbls, con_dets):
    mssql_default_db = parent.txtMssqlDefaultDb.GetValue()
    mssql_default_tbl = parent.txtMssqlDefaultTbl.GetValue()
    mssql_host = parent.txtMssqlHost.GetValue()
    mssql_user = parent.txtMssqlUser.GetValue()
    mssql_pwd = parent.txtMssqlPwd.GetValue()
    has_mssql_con = mssql_host and mssql_user and mssql_pwd \
        and mssql_default_db and mssql_default_tbl
    incomplete_mssql = (mssql_host or mssql_user or mssql_pwd \
        or mssql_default_db or mssql_default_tbl) and not has_mssql_con
    if incomplete_mssql:
        wx.MessageBox(_("The SQL Server details are incomplete"))
        parent.txtMssqlDefaultDb.SetFocus()
    default_dbs[my_globals.DBE_MS_SQL] = mssql_default_db \
        if mssql_default_db else None    
    default_tbls[my_globals.DBE_MS_SQL] = mssql_default_tbl \
        if mssql_default_tbl else None
    if mssql_host and mssql_user and mssql_pwd:
        con_dets_mssql = {"host": mssql_host, "user": mssql_user, 
                           "passwd": mssql_pwd}
        con_dets[my_globals.DBE_MS_SQL] = con_dets_mssql
    return incomplete_mssql, has_mssql_con
