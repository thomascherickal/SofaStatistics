
from __future__ import division # so 5/2 = 2.5 not 2 !

import MySQLdb
import wx
import pprint

import my_globals
import getdata
import util

BIGINT = "bigint"
DECIMAL = "decimal"
DOUBLE = "double"
FLOAT = "float"
INT = "int"
MEDIUMINT = "mediumint"
SMALLINT = "smallint"
TINYINT = "tinyint"


def quote_obj(raw_val):
    return "`%s`" % raw_val

def quote_val(raw_val):
    return "\"%s\"" % raw_val

def DbeSyntaxElements():
    if_clause = "IF(%s, %s, %s)"
    abs_wrapper_l = ""
    abs_wrapper_r = ""
    return if_clause, abs_wrapper_l, abs_wrapper_r


class DbDets(getdata.DbDets):
    
    """
    __init__ supplies default_dbs, default_tbls, conn_dets and 
        db and tbl (may be None).
    """
            
    def getDbDets(self):
        """
        Return connection, cursor, and get lists of 
            databases, tables, fields, and index info,
            based on the MySQL database connection details provided.
        Sets db and tbl if not supplied.
        The database used will be the default or the first if none provided.
        The table used will be the default or the first if none provided.
        The field dets will be taken from the table used.
        Returns conn, cur, dbs, tbls, flds, has_unique, idxs.
        """
        conn_dets_mysql = self.conn_dets.get(my_globals.DBE_MYSQL)
        if not conn_dets_mysql:
            raise Exception, "No connection details available for MySQL"
        try:
            conn = MySQLdb.connect(**conn_dets_mysql)
        except Exception, e:
            raise Exception, "Unable to connect to MySQL db.  " + \
                "Orig error: %s" % e
        cur = conn.cursor() # must return tuples not dics
        # get database name
        SQL_get_db_names = """SELECT SCHEMA_NAME 
            FROM information_schema.SCHEMATA
            WHERE SCHEMA_NAME <> 'information_schema'"""
        cur.execute(SQL_get_db_names)
        dbs = [x[0] for x in cur.fetchall()]
        dbs_lc = [x.lower() for x in dbs]
        # get db (default if possible otherwise first)
        # NB db must be accessible from connection
        if not self.db:
            # use default if possible, or fall back to first
            default_db_mysql = self.default_dbs.get(my_globals.DBE_MYSQL)
            if default_db_mysql.lower() in dbs_lc:
                self.db = default_db_mysql
            else:
                self.db = dbs[0]
        else:
            if self.db.lower() not in dbs_lc:
                raise Exception, "Database \"%s\" not available " % self.db + \
                    "from supplied connection"
        # get table names
        tbls = self.getDbTbls(cur, self.db)
        tbls_lc = [x.lower() for x in tbls]        
        # get table (default if possible otherwise first)
        # NB table must be in the database
        if not self.tbl:
            # use default if possible
            default_tbl_mysql = self.default_tbls.get(my_globals.DBE_MYSQL)
            if default_tbl_mysql and default_tbl_mysql.lower() in tbls_lc:
                self.tbl = default_tbl_mysql
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
            print self.db
            print self.tbl
            pprint.pprint(tbls)
            pprint.pprint(flds)
            pprint.pprint(idxs)
        return conn, cur, dbs, tbls, flds, has_unique, idxs
    
    def getDbTbls(self, cur, db):
        "Get table names given database and cursor"
        SQL_get_tbl_names = """SELECT TABLE_NAME 
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = '%s'
            UNION SELECT TABLE_NAME
            FROM information_schema.VIEWS
            WHERE TABLE_SCHEMA = '%s'""" % (db, db)
        cur.execute(SQL_get_tbl_names)
        tbls = [x[0] for x in cur.fetchall()] 
        tbls.sort(key=lambda s: s.upper())
        return tbls
    
    def _GetMinMax(self, col_type, num_prec, dec_pts):
        """
        Use col_type not fld_type.  The former is inconsistent - float 
            and double have unsigned at end but not rest!
        Returns minimum and maximum allowable numeric values.
        NB even though a floating point type will not store values closer 
            to zero than a certain level, such values will be accepted here.
            The database will store these as zero.
        """
        if col_type.lower().startswith(TINYINT) \
                and not col_type.lower().endswith("unsigned"):
            min = -(2**7)
            max = (2**7)-1
        elif col_type.lower().startswith(TINYINT) \
                and col_type.lower().endswith("unsigned"):
            min = 0
            max = (2**8)-1
        elif col_type.lower().startswith(SMALLINT) \
                and not col_type.lower().endswith("unsigned"):
            min = -(2**15)
            max = (2**15)-1
        elif col_type.lower().startswith(SMALLINT) \
                and col_type.lower().endswith("unsigned"):
            min = 0
            max = (2**16)-1
        elif col_type.lower().startswith(MEDIUMINT) \
                and not col_type.lower().endswith("unsigned"):
            min = -(2**23)
            max = (2**23)-1
        elif col_type.lower().startswith(MEDIUMINT) \
                and col_type.lower().endswith("unsigned"):
            min = 0
            max = (2**24)-1
        elif col_type.lower().startswith(INT) \
                and not col_type.lower().endswith("unsigned"):
            min = -(2**31)
            max = (2**31)-1
        elif col_type.lower().startswith(INT) \
                and col_type.lower().endswith("unsigned"):
            min = 0
            max = (2**32)-1
        elif col_type.lower().startswith(BIGINT) \
                and not col_type.lower().endswith("unsigned"):
            min = -(2**63)
            max = (2**63)-1
        elif col_type.lower().startswith(BIGINT) \
                and col_type.lower().endswith("unsigned"):
            min = 0
            max = (2**64)-1
        elif col_type.lower().startswith(FLOAT) \
                and not col_type.lower().endswith("unsigned"):
            min = -3.402823466E+38
            max = 3.402823466E+38
        elif col_type.lower().startswith(FLOAT) \
                and col_type.lower().endswith("unsigned"):
            min = 0
            max = 3.402823466E+38
        elif col_type.lower().startswith(DOUBLE) \
                and not col_type.lower().endswith("unsigned"):
            min = -1.7976931348623157E+308
            max = 1.7976931348623157E+308
        elif col_type.lower().startswith(DOUBLE) \
                and col_type.lower().endswith("unsigned"):
            min = 0
            max = 1.7976931348623157E+308
        elif col_type.lower().startswith(DECIMAL) \
                and not col_type.lower().endswith("unsigned"):
            # e.g. 6,2 -> 9999.99
            abs_max = ((10**(num_prec + 1))-1)/(10**dec_pts)
            min = -abs_max
            max = abs_max
        elif col_type.lower().startswith(DECIMAL) \
                and col_type.lower().endswith("unsigned"):
            abs_max = ((10**(num_prec + 1))-1)/(10**dec_pts)
            min = 0
            max = abs_max
        else:
            min = None
            max = None
        return min, max
    
    def getTblFlds(self, cur, db, tbl):
        """
        Returns details for set of fields given database, table, and cursor.
        NUMERIC_SCALE - number of significant digits to right of decimal point.
            Null if not numeric.
        NUMERIC_SCALE will be Null if not numeric.
        """
        numeric_lst = [BIGINT, DECIMAL, DOUBLE, FLOAT, INT, MEDIUMINT, 
                       SMALLINT, TINYINT]
        numeric_full_lst = []
        for num_type in numeric_lst:
            numeric_full_lst.append(num_type)
            numeric_full_lst.append("%s unsigned" % num_type)
        numeric_IN_clause = "('" + "', '".join(numeric_full_lst) + "')"
        """SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME="" 
            AND TABLE_SCHEMA = "" """
        SQL_get_fld_dets = """SELECT 
            COLUMN_NAME,
                ORDINAL_POSITION - 1
            AS ord_pos,
            IS_NULLABLE,
            COLUMN_DEFAULT,
            DATA_TYPE,
            CHARACTER_MAXIMUM_LENGTH,
            CHARACTER_SET_NAME,
                LOWER(DATA_TYPE) IN %s """ % numeric_IN_clause + """
            AS bolnumeric,
                EXTRA = 'auto_increment'
            AS autonumber,
                NUMERIC_SCALE
            AS dec_pts,
            NUMERIC_PRECISION,
            COLUMN_TYPE,
                LOWER(DATA_TYPE) IN 
                ('date', 'time', 'datetime', 'timestamp', 'year')
            AS boldatetime,
                LOWER(DATA_TYPE) IN 
                ('timestamp')
            AS timestamp
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME=\"%s\"
            AND TABLE_SCHEMA = \"%s\" """ % (tbl, db) 
        cur.execute(SQL_get_fld_dets)
        fld_dets = cur.fetchall()
        # build dic of fields, each with dic of characteristics
        flds = {}
        for (fld_name, ord_pos, nullable, fld_default, fld_type, max_len, 
                 charset, numeric, autonum, dec_pts, num_prec, col_type, 
                 boldatetime, timestamp) in fld_dets:
            bolnullable = True if nullable == "YES" else False
            boldata_entry_ok = False if (autonum or timestamp) else True
            bolnumeric = True if numeric else False
            fld_txt = not bolnumeric and not boldatetime
            bolsigned = (col_type.find("unsigned") == -1)
            min_val, max_val = self._GetMinMax(col_type, num_prec, dec_pts)
            dets_dic = {
                        my_globals.FLD_SEQ: ord_pos,
                        my_globals.FLD_BOLNULLABLE: bolnullable,
                        my_globals.FLD_DATA_ENTRY_OK: boldata_entry_ok,
                        my_globals.FLD_COLUMN_DEFAULT: fld_default,
                        my_globals.FLD_BOLTEXT: fld_txt,
                        my_globals.FLD_TEXT_LENGTH: max_len,
                        my_globals.FLD_CHARSET: charset,
                        my_globals.FLD_BOLNUMERIC: bolnumeric,
                        my_globals.FLD_BOLAUTONUMBER: autonum,
                        my_globals.FLD_DECPTS: dec_pts,
                        my_globals.FLD_NUM_WIDTH: num_prec,
                        my_globals.FLD_BOL_NUM_SIGNED: bolsigned,
                        my_globals.FLD_NUM_MIN_VAL: min_val,
                        my_globals.FLD_NUM_MAX_VAL: max_val,
                        my_globals.FLD_BOLDATETIME: boldatetime,
                        }
            flds[fld_name] = dets_dic
        return flds

    def getIndexDets(self, cur, db, tbl):
        """
        has_unique - boolean
        idxs = [idx0, idx1, ...]
        each idx is a dict name, is_unique, flds
        """
        SQL_get_index_dets = """SELECT 
            INDEX_NAME, 
                GROUP_CONCAT(COLUMN_NAME) 
            AS fld_names,
                NOT NON_UNIQUE 
            AS unique_index
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE table_name = "%s"
            AND table_schema = "%s"
            GROUP BY INDEX_NAME""" % (tbl, db)
        cur.execute(SQL_get_index_dets)
        index_dets = cur.fetchall()
        # [(INDEX_NAME, fld_names, unique_index), ...]
        # initialise
        has_unique = False
        idxs = []
        for idx_name, raw_fld_names, unique_index in index_dets:
            fld_names = [x.strip() for x in raw_fld_names.split(",")]
            if unique_index:
                has_unique = True
            idx_dic = {my_globals.IDX_NAME: idx_name, 
                       my_globals.IDX_IS_UNIQUE: unique_index, 
                       my_globals.IDX_FLDS: fld_names}
            idxs.append(idx_dic)
        debug = False
        if debug:
            pprint.pprint(idxs)
            print has_unique
        return has_unique, idxs

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
    # pprint.pprint(data)
    fld_dics = [x[2] for x in data]
    fld_names = [x[1] for x in data]
    fld_names_clause = " (`" + "`, `".join(fld_names) + "`) "
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
        val2use = getdata.PrepValue(my_globals.DBE_MYSQL, val, fld_dic)
        if debug: print str(val2use) 
        data_lst.append(val2use)
    data_tup = tuple(data_lst)
    if debug: pprint.pprint(data_tup)
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
    parent.lblMysqlDefaultDb = wx.StaticText(scroll, -1, 
                                             "Default Database (name only):")
    parent.lblMysqlDefaultDb.SetFont(lblfont)
    mysql_default_db = parent.mysql_default_db if parent.mysql_default_db \
        else ""
    parent.txtMysqlDefaultDb = wx.TextCtrl(scroll, -1, 
                                           mysql_default_db, 
                                           size=(250,-1))
    parent.txtMysqlDefaultDb.Enable(not read_only)
    # default table
    parent.lblMysqlDefaultTbl = wx.StaticText(scroll, -1, 
                                       "Default Table:")
    parent.lblMysqlDefaultTbl.SetFont(lblfont)
    mysql_default_tbl = parent.mysql_default_tbl if parent.mysql_default_tbl \
        else ""
    parent.txtMysqlDefaultTbl = wx.TextCtrl(scroll, -1, 
                                            mysql_default_tbl, 
                                            size=(250,-1))
    parent.txtMysqlDefaultTbl.Enable(not read_only)
    # host
    parent.lblMysqlHost = wx.StaticText(scroll, -1, "Host:")
    parent.lblMysqlHost.SetFont(lblfont)
    mysql_host = parent.mysql_host if parent.mysql_host else ""
    parent.txtMysqlHost = wx.TextCtrl(scroll, -1, mysql_host, 
                                      size=(100,-1))
    parent.txtMysqlHost.Enable(not read_only)
    # user
    parent.lblMysqlUser = wx.StaticText(scroll, -1, "User:")
    parent.lblMysqlUser.SetFont(lblfont)
    mysql_user = parent.mysql_user if parent.mysql_user else ""
    parent.txtMysqlUser = wx.TextCtrl(scroll, -1, mysql_user, 
                                      size=(100,-1))
    parent.txtMysqlUser.Enable(not read_only)
    # password
    parent.lblMysqlPwd = wx.StaticText(scroll, -1, "Password:")
    parent.lblMysqlPwd.SetFont(lblfont)
    mysql_pwd = parent.mysql_pwd if parent.mysql_pwd else ""
    parent.txtMysqlPwd = wx.TextCtrl(scroll, -1, mysql_pwd, 
                                     size=(300,-1))
    parent.txtMysqlPwd.Enable(not read_only)
    #2 MYSQL
    bxMysql= wx.StaticBox(scroll, -1, "MySQL")
    parent.szrMysql = wx.StaticBoxSizer(bxMysql, wx.VERTICAL)
    #3 MYSQL INNER
    #4 MYSQL INNER TOP
    szrMysqlInnerTop = wx.BoxSizer(wx.HORIZONTAL)
    # default database
    szrMysqlInnerTop.Add(parent.lblMysqlDefaultDb, 0, wx.LEFT|wx.RIGHT, 5)
    szrMysqlInnerTop.Add(parent.txtMysqlDefaultDb, 1, wx.GROW|wx.RIGHT, 10)
    # default table
    szrMysqlInnerTop.Add(parent.lblMysqlDefaultTbl, 0, wx.LEFT|wx.RIGHT, 5)
    szrMysqlInnerTop.Add(parent.txtMysqlDefaultTbl, 1, wx.GROW|wx.RIGHT, 10)
    #4 MYSQL INNER BOTTOM
    szrMysqlInnerBtm = wx.BoxSizer(wx.HORIZONTAL)
    # host 
    szrMysqlInnerBtm.Add(parent.lblMysqlHost, 0, wx.LEFT|wx.RIGHT, 5)
    szrMysqlInnerBtm.Add(parent.txtMysqlHost, 0, wx.RIGHT, 10)
    # user
    szrMysqlInnerBtm.Add(parent.lblMysqlUser, 0, wx.LEFT|wx.RIGHT, 5)
    szrMysqlInnerBtm.Add(parent.txtMysqlUser, 0, wx.RIGHT, 10)
    # password
    szrMysqlInnerBtm.Add(parent.lblMysqlPwd, 0, wx.LEFT|wx.RIGHT, 5)
    szrMysqlInnerBtm.Add(parent.txtMysqlPwd, 1, wx.GROW|wx.RIGHT, 10)
    #2 combine
    parent.szrMysql.Add(szrMysqlInnerTop, 0, wx.GROW|wx.ALL, 5)
    parent.szrMysql.Add(szrMysqlInnerBtm, 0, wx.ALL, 5)
    szr.Add(parent.szrMysql, 0, wx.GROW|wx.ALL, 10)
    
def getProjSettings(parent, proj_dic):
    ""
    parent.mysql_default_db = proj_dic["default_dbs"][my_globals.DBE_MYSQL]
    parent.mysql_default_tbl = proj_dic["default_tbls"][my_globals.DBE_MYSQL]
    # optional (although if any mysql, for eg, must have all)
    if proj_dic["conn_dets"].get(my_globals.DBE_MYSQL):
        parent.mysql_host = proj_dic["conn_dets"][my_globals.DBE_MYSQL]["host"]
        parent.mysql_user = proj_dic["conn_dets"][my_globals.DBE_MYSQL]["user"]
        parent.mysql_pwd = proj_dic["conn_dets"][my_globals.DBE_MYSQL]["passwd"]
    else:
        parent.mysql_host, parent.mysql_user, parent.mysql_pwd = "", "", ""

def setConnDetDefaults(parent):
    try:
        parent.mysql_default_db
    except AttributeError:
        parent.mysql_default_db = ""
    try:
        parent.mysql_default_tbl
    except AttributeError: 
        parent.mysql_default_tbl = ""
    try:
        parent.mysql_host
    except AttributeError: 
        parent.mysql_host = ""
    try:
        parent.mysql_user
    except AttributeError: 
        parent.mysql_user = ""
    try:            
        parent.mysql_pwd
    except AttributeError: 
        parent.mysql_pwd = ""
    
def processConnDets(parent, default_dbs, default_tbls, conn_dets):
    mysql_default_db = parent.txtMysqlDefaultDb.GetValue()
    mysql_default_tbl = parent.txtMysqlDefaultTbl.GetValue()
    mysql_host = parent.txtMysqlHost.GetValue()
    mysql_user = parent.txtMysqlUser.GetValue()
    mysql_pwd = parent.txtMysqlPwd.GetValue()
    has_mysql_conn = mysql_host and mysql_user and mysql_pwd \
        and mysql_default_db and mysql_default_tbl
    incomplete_mysql = (mysql_host or mysql_user or mysql_pwd \
        or mysql_default_db or mysql_default_tbl) and not has_mysql_conn
    if incomplete_mysql:
        wx.MessageBox("The MySQL details are incomplete")
        parent.txtMysqlDefaultDb.SetFocus()
    default_dbs[my_globals.DBE_MYSQL] = mysql_default_db \
        if mysql_default_db else None    
    default_tbls[my_globals.DBE_MYSQL] = mysql_default_tbl \
        if mysql_default_tbl else None
    if mysql_host and mysql_user and mysql_pwd:
        conn_dets_mysql = {"host": mysql_host, "user": mysql_user, 
                           "passwd": mysql_pwd}
        conn_dets[my_globals.DBE_MYSQL] = conn_dets_mysql
    return incomplete_mysql, has_mysql_conn
    