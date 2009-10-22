from __future__ import print_function

import pgdb
import wx
import pprint

import my_globals
import getdata
import util

# http://www.postgresql.org/docs/8.4/static/datatype.html
BIGINT = "bigint" # "signed eight-byte integer"
#BIGSERIAL = "autoincrementing eight-byte integer" # not a real type, only a
#  notational convenience 
# (see http://www.postgresql.org/docs/8.4/static/datatype-numeric.html)
BIT = "bit" # "fixed-length bit string"
BITVARYING = "bit varying" # "variable-length bit string"
BOOLEAN = "boolean" # "logical Boolean (true/false)"
BOX = "box" # "rectangular box on a plane"
BYTEA = "bytea" # "binary data ('byte array')"
CHARVARYING = "character varying" # "variable-length character string"
CHAR = "character" # "fixed-length character string"
CIDR = "cidr" # "IPv4 or IPv6 network address"
CIRCLE = "circle" # "circle on a plane"
DATE = "date" # "calendar date (year, month, day)"
DECIMAL = "decimal" # The types decimal and numeric are equivalent. 
  # Both types are part of the SQL standard. 
DOUBLE = "double precision" # "double precision floating-point number (8 bytes)"
INET = "inet" # "IPv4 or IPv6 host address"
INTEGER = "integer" # "signed four-byte integer"
INTERVAL = "interval" # "time span"
LINE = "line" # "infinite line on a plane"
LSEG = "lseg" # "line segment on a plane"
MACADDR = "macaddr" # "MAC (Media Access Control) address"
MONEY = "money" # "currency amount"
NUMERIC = "numeric" # "exact numeric of selectable precision"
PATH = "path" # "geometric path on a plane"
POINT = "point" # "geometric point on a plane"
POLYGON = "polygon" # "closed geometric path on a plane"
REAL = "real" # "single precision floating-point number (4 bytes)"
SMALLINT = "smallint" # "signed two-byte integer"
#SERIAL = "autoincrementing four-byte integer"
TEXT = "text" # "variable-length character string"
TIME = "time" # "time of day"
TIMESTAMP = "timestamp" # "date and time"
TSQUERY = "tsquery" # "text search query"
TSVECTOR = "tsvector" # "text search document"
TXID_SNAPSHOT = "txid_snapshot" # "user-level transaction ID snapshot"
UUID = "uuid" # "universally unique identifier"
XML = "xml" # "XML data"

def quote_obj(raw_val):
    return '"%s"' % raw_val

def quote_val(raw_val):
    return "'%s'" % raw_val

def get_placeholder():
    return "%s"

def get_summable(clause):
    return "CASE WHEN %s THEN 1 ELSE 0 END" % clause

def DbeSyntaxElements():
    if_clause = "CASE WHEN %s THEN %s ELSE %s END"
    return (if_clause, quote_obj, quote_val, get_placeholder, get_summable)


class DbDets(getdata.DbDets):
    
    """
    __init__ supplies default_dbs, default_tbls, conn_dets and 
        db and tbl (may be None).  Db needs to be set in conn_dets once 
        identified.
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
        self.debug = False
        if self.debug:
            print("Received db is: %s" % self.db)
            print("Received tbl is: %s" % self.tbl)
        conn_dets_pgsql = self.conn_dets.get(my_globals.DBE_PGSQL)
        if not conn_dets_pgsql:
            raise Exception, "No connection details available for PostgreSQL"
        try:
            if self.db:
                conn_dets_pgsql["database"] = self.db
            conn = pgdb.connect(**conn_dets_pgsql)
        except Exception, e:
            raise Exception, "Unable to connect to PostgreSQL db.  " + \
                "Orig error: %s" % e
        cur = conn.cursor() # must return tuples not dics
        # get database name
        SQL_get_db_names = """SELECT datname FROM pg_database"""
        cur.execute(SQL_get_db_names)
        dbs = [x[0] for x in cur.fetchall()]
        dbs_lc = [x.lower() for x in dbs]
        # get db (default if possible otherwise first)
        # NB db must be accessible from connection
        if not self.db:
            # use default if possible, or fall back to first
            default_db_pgsql = self.default_dbs.get(my_globals.DBE_PGSQL)
            if default_db_pgsql.lower() in dbs_lc:
                self.db = default_db_pgsql
            else:
                self.db = dbs[0]
            # need to reset conn and cur
            cur.close()
            conn.close()
            conn_dets_pgsql["database"] = self.db
            conn = pgdb.connect(**conn_dets_pgsql)
            cur = conn.cursor()
        else:
            if self.db.lower() not in dbs_lc:
                raise Exception, "Database \"%s\" not available " % self.db + \
                    "from supplied connection"
        if self.debug: pprint.pprint(self.conn_dets)
        # get table names
        tbls = self.getDbTbls(cur, self.db)
        tbls_lc = [x.lower() for x in tbls]        
        # get table (default if possible otherwise first)
        # NB table must be in the database
        if not self.tbl:
            # use default if possible
            default_tbl_pgsql = self.default_tbls.get(my_globals.DBE_PGSQL)
            if default_tbl_pgsql and default_tbl_pgsql.lower() in tbls_lc:
                self.tbl = default_tbl_pgsql
            else:
                self.tbl = tbls[0]
        else:
            if self.tbl.lower() not in tbls_lc:
                raise Exception, "Table \"%s\" not found in database \"%s\"" % \
                    (self.tbl, self.db)
        # get field names (from first table if none provided)
        flds = self.getTblFlds(cur, self.db, self.tbl)
        has_unique, idxs = self.getIndexDets(cur, self.db, self.tbl)
        if self.debug:
            print("Db is: %s" % self.db)
            print("Tbl is: %s" % self.tbl)
            pprint.pprint(tbls)
            pprint.pprint(flds)
            pprint.pprint(idxs)
        return conn, cur, dbs, tbls, flds, has_unique, idxs
    
    def getDbTbls(self, cur, db):
        """
        Get table names given database and cursor.
        http://www.alberton.info/postgresql_meta_info.html
        """
        SQL_get_tbl_names = """SELECT table_name
            FROM information_schema.tables
            WHERE table_type = 'BASE TABLE'
                AND table_schema NOT IN ('pg_catalog', 'information_schema')"""
        cur.execute(SQL_get_tbl_names)
        tbls = [x[0] for x in cur.fetchall()] 
        tbls.sort(key=lambda s: s.upper())
        return tbls
    
    def _GetMinMax(self, fld_type, num_prec, dec_pts, autonum):
        """
        Returns minimum and maximum allowable numeric values.
        num_prec - precision e.g. 6 for 23.5141
        dec_pts - scale e.g. 4 for 23.5141
        autonum - i.e. serial or bigserial
        http://www.postgresql.org/docs/8.4/static/datatype-numeric.html
        We use the following terms below: The scale of a numeric is the count of 
            decimal digits in the fractional part, to the right of the decimal 
            point. The precision of a numeric is the total count of significant 
            digits in the whole number, that is, the number of digits to both 
            sides of the decimal point. So the number 23.5141 has a precision of 
            6 and a scale of 4. Integers can be considered to have a scale of 
            zero.
        http://www.postgresql.org/docs/8.4/static/datatype-numeric.html
        NB even though a floating point type will not store values closer 
            to zero than a certain level, such values will be accepted here.
            The database will store these as zero. TODO - confirm with 
            PostgreSQL.
        """
        if fld_type == SMALLINT:
            min = -(2**15)
            max = (2**15)-1
        elif fld_type == INTEGER:
            min = 1 if autonum else -(2**31)
            max = (2**31)-1
        elif fld_type == BIGINT:
            min = 1 if autonum else -(2**63)
            max = (2**63)-1
        # http://www.postgresql.org/docs/8.4/static/datatype-money.html
        elif fld_type == MONEY:
            min = -92233720368547758.08
            max = 92233720368547758.07
        elif fld_type == REAL:
            # variable-precision, inexact. 6 decimal digits precision.
            min = -(2**128)
            max = (2**128)-1 # actually, rather a bit less, but this will do
        elif fld_type == DOUBLE:
            # variable-precision, inexact. 15 decimal digits precision.
            min = -(2**1024)
            max = (2**1024)-1
        elif fld_type == NUMERIC: #alias of decimal
            # variable-precision, inexact. 15 decimal digits precision.
            abs_max = 10**(num_prec - dec_pts)
            min = -abs_max
            max = abs_max
        else:
            min = None
            max = None
        return min, max    
    
    def getTblFlds(self, cur, db, tbl):
        """
        Returns details for set of fields given database, table, and cursor.
        http://archives.postgresql.org/pgsql-sql/2007-01/msg00082.php
        """
        debug = False
        SQL_get_fld_dets = """SELECT columns.column_name 
            AS col_name, 
                columns.ordinal_position 
            AS ord_pos,  
                columns.is_nullable 
            AS is_nullable, 
                columns.column_default 
            AS col_default,
                columns.data_type
            AS data_type, 
                columns.character_maximum_length 
            AS char_max_len, 
                columns.character_set_name 
            AS char_set_name,
                lower(columns.data_type) IN ('%s', '%s', '%s', '%s', '%s', '%s', 
                    '%s', '%s') """ % (SMALLINT, INTEGER, BIGINT, DECIMAL, 
                                       NUMERIC, REAL, DOUBLE, MONEY) + """
            AS bolnumeric,
                position('nextval' in columns.column_default) IS NOT NULL 
            AS autonumber,
                columns.numeric_scale 
            AS dec_pts,
                columns.numeric_precision 
            AS num_precision,
                lower(columns.data_type) IN ('%s', '%s', '%s', '%s') """ % \
                    (TIMESTAMP, DATE, TIME, INTERVAL) + """
            AS boldatetime,
                lower(columns.data_type) IN ('%s') """ % TIMESTAMP + """ 
            AS timestamp
            FROM information_schema.columns
            WHERE columns.table_schema::text = 'public'::text
            AND columns.table_name = '%s'
            ORDER BY columns.ordinal_position """ % tbl 
        cur.execute(SQL_get_fld_dets)
        fld_dets = cur.fetchall()
        if debug: pprint.pprint(fld_dets)
        # build dic of fields, each with dic of characteristics
        flds = {}
        for (fld_name, ord_pos, nullable, fld_default, fld_type, max_len, 
                 charset, numeric, autonum, dec_pts, num_prec, boldatetime, 
                 timestamp) in fld_dets:
            bolnullable = True if nullable == "YES" else False
            boldata_entry_ok = False if (autonum or timestamp) else True
            bolnumeric = True if numeric else False
            fld_txt = not bolnumeric and not boldatetime
            min_val, max_val = self._GetMinMax(fld_type, num_prec, dec_pts, 
                                               autonum)
            bolsigned = bolnumeric and autonum
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
        http://www.alberton.info/postgresql_meta_info.html
        """
        SQL_get_main_index_dets = """SELECT relname, indkey, indisunique
            FROM pg_class, pg_index
            WHERE pg_class.oid = pg_index.indexrelid
            AND pg_class.oid IN (
            SELECT indexrelid
            FROM pg_index INNER JOIN pg_class
            ON pg_class.oid=pg_index.indrelid
            WHERE pg_class.relname='%s')""" % tbl
        cur.execute(SQL_get_main_index_dets)
        main_index_dets = cur.fetchall()
        idxs = []
        has_unique = False
        for idx_name, indkey, unique_index in main_index_dets:
            fld_names = []
            if unique_index:
                has_unique = True
            # get field names
            fld_oids = indkey.replace(" ", ", ")
            SQL_get_idx_flds = """SELECT t.relname, a.attname
               FROM pg_index c
               LEFT JOIN pg_class t
               ON c.indrelid  = t.oid
               LEFT JOIN pg_attribute a
               ON a.attrelid = t.oid
               AND a.attnum = ANY(indkey)
               WHERE t.relname = '%s'
               AND a.attnum IN(%s)""" % (tbl, fld_oids)
            cur.execute(SQL_get_idx_flds)
            fld_names = [x[1] for x in cur.fetchall()]
            idx_dic = {my_globals.IDX_NAME: idx_name, 
                       my_globals.IDX_IS_UNIQUE: unique_index, 
                       my_globals.IDX_FLDS: fld_names}
            idxs.append(idx_dic)
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
    """
    debug = False
    if debug: pprint.pprint(data)
    fld_dics = [x[2] for x in data]
    fld_names = [x[1] for x in data]
    fld_names_clause = ' ("' + '", "'.join(fld_names) + '") '
    # e.g. ("fname", "lname", "dob" ...)
    fld_placeholders_clause = " (" + \
        ", ".join(["%s" for x in range(len(data))]) + ") "
    # e.g. " (%s, %s, %s ...) "
    SQL_insert = "INSERT INTO \"%s\" " % tbl_name + fld_names_clause + \
        "VALUES %s" % fld_placeholders_clause
    if debug: print(SQL_insert)
    data_lst = []
    for i, data_dets in enumerate(data):
        if debug: pprint.pprint(data_dets)
        val, fld_name, fld_dic = data_dets
        val2use = getdata.PrepValue(my_globals.DBE_PGSQL, val, fld_dic)
        if debug: print(str(val2use)) 
        data_lst.append(val2use)
    data_tup = tuple(data_lst)
    if debug: pprint.pprint(data_tup)
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
    parent.lblPgsqlDefaultDb = wx.StaticText(scroll, -1, 
                                             _("Default Database (name only):"))
    parent.lblPgsqlDefaultDb.SetFont(lblfont)
    pgsql_default_db = parent.pgsql_default_db if parent.pgsql_default_db \
        else ""
    parent.txtPgsqlDefaultDb = wx.TextCtrl(scroll, -1, 
                                           pgsql_default_db, 
                                           size=(250,-1))
    parent.txtPgsqlDefaultDb.Enable(not read_only)
    # default table
    parent.lblPgsqlDefaultTbl = wx.StaticText(scroll, -1, _("Default Table:"))
    parent.lblPgsqlDefaultTbl.SetFont(lblfont)
    pgsql_default_tbl = parent.pgsql_default_tbl if parent.pgsql_default_tbl \
        else ""
    parent.txtPgsqlDefaultTbl = wx.TextCtrl(scroll, -1, 
                                            pgsql_default_tbl, 
                                            size=(250,-1))
    parent.txtPgsqlDefaultTbl.Enable(not read_only)
    # host
    parent.lblPgsqlHost = wx.StaticText(scroll, -1, _("Host:"))
    parent.lblPgsqlHost.SetFont(lblfont)
    pgsql_host = parent.pgsql_host if parent.pgsql_host else ""
    parent.txtPgsqlHost = wx.TextCtrl(scroll, -1, pgsql_host, 
                                      size=(100,-1))
    parent.txtPgsqlHost.Enable(not read_only)
    # user
    parent.lblPgsqlUser = wx.StaticText(scroll, -1, _("User:"))
    parent.lblPgsqlUser.SetFont(lblfont)
    pgsql_user = parent.pgsql_user if parent.pgsql_user else ""
    parent.txtPgsqlUser = wx.TextCtrl(scroll, -1, pgsql_user, 
                                      size=(100,-1))
    parent.txtPgsqlUser.Enable(not read_only)
    # password
    parent.lblPgsqlPwd = wx.StaticText(scroll, -1, _("Password:"))
    parent.lblPgsqlPwd.SetFont(lblfont)
    pgsql_pwd = parent.pgsql_pwd if parent.pgsql_pwd else ""
    parent.txtPgsqlPwd = wx.TextCtrl(scroll, -1, pgsql_pwd, 
                                     size=(300,-1))
    parent.txtPgsqlPwd.Enable(not read_only)
    #2 pgsql
    bxpgsql= wx.StaticBox(scroll, -1, "pgsql")
    parent.szrpgsql = wx.StaticBoxSizer(bxpgsql, wx.VERTICAL)
    #3 pgsql INNER
    #4 pgsql INNER TOP
    szrpgsqlInnerTop = wx.BoxSizer(wx.HORIZONTAL)
    # default database
    szrpgsqlInnerTop.Add(parent.lblPgsqlDefaultDb, 0, wx.LEFT|wx.RIGHT, 5)
    szrpgsqlInnerTop.Add(parent.txtPgsqlDefaultDb, 1, wx.GROW|wx.RIGHT, 10)
    # default table
    szrpgsqlInnerTop.Add(parent.lblPgsqlDefaultTbl, 0, wx.LEFT|wx.RIGHT, 5)
    szrpgsqlInnerTop.Add(parent.txtPgsqlDefaultTbl, 1, wx.GROW|wx.RIGHT, 10)
    #4 pgsql INNER BOTTOM
    szrpgsqlInnerBtm = wx.BoxSizer(wx.HORIZONTAL)
    # host 
    szrpgsqlInnerBtm.Add(parent.lblPgsqlHost, 0, wx.LEFT|wx.RIGHT, 5)
    szrpgsqlInnerBtm.Add(parent.txtPgsqlHost, 0, wx.RIGHT, 10)
    # user
    szrpgsqlInnerBtm.Add(parent.lblPgsqlUser, 0, wx.LEFT|wx.RIGHT, 5)
    szrpgsqlInnerBtm.Add(parent.txtPgsqlUser, 0, wx.RIGHT, 10)
    # password
    szrpgsqlInnerBtm.Add(parent.lblPgsqlPwd, 0, wx.LEFT|wx.RIGHT, 5)
    szrpgsqlInnerBtm.Add(parent.txtPgsqlPwd, 1, wx.GROW|wx.RIGHT, 10)
    #2 combine
    parent.szrpgsql.Add(szrpgsqlInnerTop, 0, wx.GROW|wx.ALL, 5)
    parent.szrpgsql.Add(szrpgsqlInnerBtm, 0, wx.ALL, 5)
    szr.Add(parent.szrpgsql, 0, wx.GROW|wx.ALL, 10)
    
def getProjSettings(parent, proj_dic):
    ""
    parent.pgsql_default_db = proj_dic["default_dbs"].get(my_globals.DBE_PGSQL)
    parent.pgsql_default_tbl = \
        proj_dic["default_tbls"].get(my_globals.DBE_PGSQL)
    # optional (although if any pgsql, for eg, must have all)
    if proj_dic["conn_dets"].get(my_globals.DBE_PGSQL):
        parent.pgsql_host = proj_dic["conn_dets"][my_globals.DBE_PGSQL]["host"]
        parent.pgsql_user = proj_dic["conn_dets"][my_globals.DBE_PGSQL]["user"]
        parent.pgsql_pwd = \
            proj_dic["conn_dets"][my_globals.DBE_PGSQL]["password"]
    else:
        parent.pgsql_host, parent.pgsql_user, parent.pgsql_pwd = "", "", ""

def setConnDetDefaults(parent):
    try:
        parent.pgsql_default_db
    except AttributeError:
        parent.pgsql_default_db = ""
    try:
        parent.pgsql_default_tbl
    except AttributeError: 
        parent.pgsql_default_tbl = ""
    try:
        parent.pgsql_host
    except AttributeError: 
        parent.pgsql_host = ""
    try:
        parent.pgsql_user
    except AttributeError: 
        parent.pgsql_user = ""
    try:            
        parent.pgsql_pwd
    except AttributeError: 
        parent.pgsql_pwd = ""
    
def processConnDets(parent, default_dbs, default_tbls, conn_dets):
    pgsql_default_db = parent.txtPgsqlDefaultDb.GetValue()
    pgsql_default_tbl = parent.txtPgsqlDefaultTbl.GetValue()
    pgsql_host = parent.txtPgsqlHost.GetValue()
    pgsql_user = parent.txtPgsqlUser.GetValue()
    pgsql_pwd = parent.txtPgsqlPwd.GetValue()
    has_pgsql_conn = pgsql_host and pgsql_user and pgsql_pwd \
        and pgsql_default_db and pgsql_default_tbl
    incomplete_pgsql = (pgsql_host or pgsql_user or pgsql_pwd \
        or pgsql_default_db or pgsql_default_tbl) and not has_pgsql_conn
    if incomplete_pgsql:
        wx.MessageBox(_("The PostgreSQL details are incomplete"))
        parent.txtPgsqlDefaultDb.SetFocus()
    default_dbs[my_globals.DBE_PGSQL] = pgsql_default_db \
        if pgsql_default_db else None    
    default_tbls[my_globals.DBE_PGSQL] = pgsql_default_tbl \
        if pgsql_default_tbl else None
    if pgsql_host and pgsql_user and pgsql_pwd:
        conn_dets_pgsql = {"host": pgsql_host, "user": pgsql_user, 
                           "password": pgsql_pwd}
        conn_dets[my_globals.DBE_PGSQL] = conn_dets_pgsql
    return incomplete_pgsql, has_pgsql_conn
    
