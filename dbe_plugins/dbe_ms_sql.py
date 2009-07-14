#Must run makepy once - 
#see http://www.thescripts.com/forum/thread482449.html e.g. the following 
#way - run PYTHON\Lib\site-packages\pythonwin\pythonwin.exe (replace 
#PYTHON with folder python is in).  Tools>COM Makepy utility - select 
#appropriate library - e.g. for ADO it would be 
# Microsoft ActiveX Data Objects 2.8 Library (2.8) - and 
#select OK.  NB DAO has to be done separately from ADO etc.

import adodbapi
import win32com.client

import wx
import pprint

import my_globals
import getdata
import table_entry


# numeric
BYTE = 'Byte - 1-byte unsigned integer'
INTEGER = 'Integer - 2-byte signed integer'
LONGINT = 'Long Integer - 4-byte signed integer'
DECIMAL = 'Decimal'
SINGLE = 'Single'
DOUBLE = 'Double'
CURRENCY = 'Currency'
# other
DATE = 'date'
BOOLEAN = 'boolean'
TIMESTAMP = 'timestamp'
VARCHAR = 'varchar'
LONGVARCHAR = 'longvarchar'

AD_OPEN_KEYSET = 1
AD_LOCK_OPTIMISTIC = 3
AD_SCHEMA_COLUMNS = 4


def quote_obj(raw_val):
    return "[%s]" % raw_val

def quote_val(raw_val):
    return "'%s'" % raw_val.replace("'", "''")

def DbeSyntaxElements():
    if_clause = "CASE WHEN %s THEN %s ELSE %s END"
    abs_wrapper_l = ""
    abs_wrapper_r = ""
    return if_clause, abs_wrapper_l, abs_wrapper_r

    
class DbDets(getdata.DbDets):

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

    def getFldType(self, adotype):
        """
        http://www.devguru.com/Technologies/ado/quickref/field_type.html
        http://www.databasedev.co.uk/fields_datatypes.html
        """
        if adotype == win32com.client.constants.adUnsignedTinyInt:
            fld_type = BYTE # 1-byte unsigned integer
        elif adotype == win32com.client.constants.adSmallInt:
            fld_type = INTEGER # 2-byte signed integer
        elif adotype == win32com.client.constants.adInteger:
            fld_type = LONGINT # 4-byte signed integer
        elif adotype == win32com.client.constants.adSingle:
            fld_type = SINGLE # Single-precision floating-point value
        elif adotype == win32com.client.constants.adDouble:
            fld_type = DOUBLE # Double precision floating-point
        elif adotype == win32com.client.constants.adNumeric:
            fld_type = DECIMAL
        elif adotype == win32com.client.constants.adCurrency:
            fld_type = CURRENCY
        elif adotype == win32com.client.constants.adVarWChar:
            fld_type = VARCHAR
        elif adotype == win32com.client.constants.adBoolean:
            fld_type = BOOLEAN
        elif adotype == win32com.client.constants.adDBTimeStamp:
            fld_type = TIMESTAMP
        else:
            raise Exception, "Not an MS SQL Server ADO field type %d" % adotype
        return fld_type

    def GetMinMax(self, fld_type, num_prec, dec_pts):
        """
        Returns minimum and maximum allowable numeric values.  
        Nones if not numeric.
        NB even though a floating point type will not store values closer 
            to zero than a certain level, such values will be accepted here.
            The database will store these as zero.
        http://www.databasedev.co.uk/fields_datatypes.html38 
        """
        if fld_type == BYTE:
            min = 0
            max = (2**8)-1 # 255
        elif fld_type == INTEGER:
            min = -(2**15)
            max = (2**15)-1            
        elif fld_type == LONGINT:
            min = -(2**31)
            max = (2**31)-1            
        elif fld_type == DECIMAL:
            # (+- 38 if .adp as opposed to .mdb)
            min = -((10**38)-1)
            max = (10**38)-1
        elif fld_type == SINGLE: # signed by default
            min = -3.402823466E+38
            max = 3.402823466E+38
        elif fld_type == DOUBLE:
            min = -1.79769313486231E308
            max = 1.79769313486231E308
        elif fld_type == CURRENCY:
            """
            Accurate to 15 digits to the left of the decimal point and 
                4 digits to the right.
            e.g. 19,4 -> 999999999999999.9999
            """
            dec_pts = 4
            num_prec = 15 + dec_pts
            abs_max = ((10**(num_prec + 1))-1)/(10**dec_pts)
            min = -abs_max
            max = abs_max
        else:
            min = None
            max = None
        return min, max

    def getTblFlds(self, cur, db, tbl):
        """
        Returns details for set of fields given database, table, and cursor.
        NUMERIC_SCALE - number of significant digits to right of decimal point.
        NUMERIC_SCALE should be Null if not numeric (but is in fact 255 so 
            I must set to None!).
        """
        debug = True
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
            if debug: print col.Type
            fld_type = self.getFldType(col.Type)
            bolnumeric = fld_type in [BYTE, INTEGER, LONGINT, DECIMAL, 
                                      SINGLE, DOUBLE, CURRENCY]
            try:
                bolautonum = col.Properties("AutoIncrement").Value
            except Exception:
                bolautonum = False
            try:
                bolnullable = col.Properties("Nullable").Value
            except Exception:
                bolnullable = False
            try:
                default = col.Properties("Default").Value
            except Exception:
                default = ""
            boldata_entry_ok = False if bolautonum else True
            dec_pts = col.NumericScale if col.NumericScale < 18 else 0
            boldatetime = fld_type in [DATE, TIMESTAMP]
            fld_txt = not bolnumeric and not boldatetime
            num_prec = col.Precision
            min_val, max_val = self.GetMinMax(fld_type, num_prec, dec_pts)
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
            print has_unique
        return has_unique, idxs

    def _getDbs(self, user, pwd):
        """
        Get dbs and the db to use.
        NB need to use a separate connection with db undefined.        
        """
        DSN = """PROVIDER=SQLOLEDB;
            Data Source=(local);
            User ID='%s';
            Password='%s';
            Initial Catalog='';
            Integrated Security=SSPI""" % (user, pwd)
        conn = adodbapi.connect(connstr=DSN)
        cur = conn.cursor() # must return tuples not dics
        cur.execute("SELECT name FROM sysdatabases")
        dbs = [x[0] for x in cur.fetchall()]
        # get table names (from first db if none provided)
        db_to_use = self.db if self.db else dbs[0]
        cur.close()
        conn.close()
        return dbs, db_to_use

    def getDbDets(self):
        """
        Return connection, cursor, and get lists of 
            databases, tables, and fields 
            based on the MySQL database connection details provided.
        The database used will be the first if none provided.
        The table used will be the first if none provided.
        The field dets will be taken from the table used.
        Returns conn, cur, dbs, tbls, flds, has_unique, idxs.
        """
        conn_dets_mssql = self.conn_dets.get(my_globals.DBE_MS_SQL)
        if not conn_dets_mssql:
            raise Exception, "No connection details available for MS SQL Server"
        user = conn_dets_mssql["user"]
        pwd = conn_dets_mssql["passwd"]
        dbs, db_to_use = self._getDbs(user, pwd)
        DSN = """PROVIDER=SQLOLEDB;
            Data Source=(local);
            User ID='%s';
            Password='%s';
            Initial Catalog='%s';
            Integrated Security=SSPI""" % (user, pwd, db_to_use)
        conn = adodbapi.connect(connstr=DSN)
        cur = conn.cursor()
        cur.adoconn = conn.adoConn # (need to be able to access from just the cursor)
        tbls = self.getDbTbls(cur, db_to_use)
        # get field names (from first table if none provided)
        tbl_to_use = self.tbl if self.tbl else tbls[0]
        flds = self.getTblFlds(cur, db_to_use, tbl_to_use)
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
    conn_dets["db"] = db

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
    fld_names_clause = " ([" + "], [".join(fld_names) + "]) "
    # e.g. (`fname`, `lname`, `dob` ...)
    fld_placeholders_clause = " (" + \
        ", ".join(["%s" for x in range(len(data))]) + ") "
    # e.g. " (%s, %s, %s ...) "
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
    parent.lblMssqlDefaultDb = wx.StaticText(scroll, -1, "Default Database:")
    parent.lblMssqlDefaultDb.SetFont(lblfont)
    mssql_default_db = parent.mssql_default_db if parent.mssql_default_db \
        else ""
    parent.txtMssqlDefaultDb = wx.TextCtrl(scroll, -1, 
                                           mssql_default_db, 
                                           size=(250,-1))
    parent.txtMssqlDefaultDb.Enable(not read_only)
    # default table
    parent.lblMssqlDefaultTbl = wx.StaticText(scroll, -1, 
                                       "Default Table:")
    parent.lblMssqlDefaultTbl.SetFont(lblfont)
    mssql_default_tbl = parent.mssql_default_tbl if parent.mssql_default_tbl \
        else ""
    parent.txtMssqlDefaultTbl = wx.TextCtrl(scroll, -1, 
                                            mssql_default_tbl, 
                                            size=(250,-1))
    parent.txtMssqlDefaultTbl.Enable(not read_only)
    # host
    parent.lblMssqlHost = wx.StaticText(scroll, -1, "Host:")
    parent.lblMssqlHost.SetFont(lblfont)
    mssql_host = parent.mssql_host if parent.mssql_host else ""
    parent.txtMssqlHost = wx.TextCtrl(scroll, -1, mssql_host, 
                                      size=(100,-1))
    parent.txtMssqlHost.Enable(not read_only)
    # user
    parent.lblMssqlUser = wx.StaticText(scroll, -1, "User:")
    parent.lblMssqlUser.SetFont(lblfont)
    mssql_user = parent.mssql_user if parent.mssql_user else ""
    parent.txtMssqlUser = wx.TextCtrl(scroll, -1, mssql_user, 
                                      size=(100,-1))
    parent.txtMssqlUser.Enable(not read_only)
    # password
    parent.lblMssqlPwd = wx.StaticText(scroll, -1, "Password:")
    parent.lblMssqlPwd.SetFont(lblfont)
    mssql_pwd = parent.mssql_pwd if parent.mssql_pwd else ""
    parent.txtMssqlPwd = wx.TextCtrl(scroll, -1, mssql_pwd, 
                                     size=(300,-1))
    parent.txtMssqlPwd.Enable(not read_only)
    #2 MS SQL SERVER
    bxMssql= wx.StaticBox(scroll, -1, "Microsoft SQL Server")
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
    parent.mssql_default_db = proj_dic["default_dbs"][my_globals.DBE_MS_SQL]
    parent.mssql_default_tbl = proj_dic["default_tbls"][my_globals.DBE_MS_SQL]
    # optional (although if any mssql, for eg, must have all)
    if proj_dic["conn_dets"].get(my_globals.DBE_MS_SQL):
        parent.mssql_host = proj_dic["conn_dets"][my_globals.DBE_MS_SQL]["host"]
        parent.mssql_user = proj_dic["conn_dets"][my_globals.DBE_MS_SQL]["user"]
        parent.mssql_pwd = proj_dic["conn_dets"][my_globals.DBE_MS_SQL]["passwd"]
    else:
        parent.mssql_host, parent.mssql_user, parent.mssql_pwd = "", "", ""

def setConnDetDefaults(parent):
    try:
        parent.mssql_default_db
    except AttributeError:
        parent.mssql_default_db = ""
    try:
        parent.mssql_default_tbl
    except AttributeError: 
        parent.mssql_default_tbl = ""
    try:
        parent.mssql_host
    except AttributeError: 
        parent.mssql_host = ""
    try:
        parent.mssql_user
    except AttributeError: 
        parent.mssql_user = ""
    try:            
        parent.mssql_pwd
    except AttributeError: 
        parent.mssql_pwd = ""

def processConnDets(parent, default_dbs, default_tbls, conn_dets):
    mssql_default_db = parent.txtMssqlDefaultDb.GetValue()
    mssql_default_tbl = parent.txtMssqlDefaultTbl.GetValue()
    mssql_host = parent.txtMssqlHost.GetValue()
    mssql_user = parent.txtMssqlUser.GetValue()
    mssql_pwd = parent.txtMssqlPwd.GetValue()
    has_mssql_conn = mssql_host and mssql_user and mssql_pwd \
        and mssql_default_db and mssql_default_tbl
    incomplete_mssql = (mssql_host or mssql_user or mssql_pwd \
        or mssql_default_db or mssql_default_tbl) and not has_mssql_conn
    if incomplete_mssql:
        wx.MessageBox("The SQL Server details are incomplete")
        parent.txtMssqlDefaultDb.SetFocus()
    default_dbs[my_globals.DBE_MS_SQL] = mssql_default_db \
        if mssql_default_db else None    
    default_tbls[my_globals.DBE_MS_SQL] = mssql_default_tbl \
        if mssql_default_tbl else None
    if mssql_host and mssql_user and mssql_pwd:
        conn_dets_mssql = {"host": mssql_host, "user": mssql_user, 
                           "passwd": mssql_pwd}
        conn_dets[my_globals.DBE_MS_SQL] = conn_dets_mssql
    return incomplete_mssql, has_mssql_conn