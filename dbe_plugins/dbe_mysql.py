from __future__ import print_function
from __future__ import division # so 5/2 = 2.5 not 2 !

import MySQLdb
import wx
import pprint

import my_globals as mg
import getdata

BIGINT = "bigint"
DECIMAL = "decimal"
DOUBLE = "double"
FLOAT = "float"
INT = "int"
MEDIUMINT = "mediumint"
SMALLINT = "smallint"
TINYINT = "tinyint"

if_clause = u"IF(%s, %s, %s)"
placeholder = u"?"
left_obj_quote = u"`"
right_obj_quote = u"`"
gte_not_equals = u"!="

def quote_obj(raw_val):
    return u"%s%s%s" % (left_obj_quote, raw_val, right_obj_quote)

def quote_val(raw_val):
    return u"\"%s\"" % raw_val

def get_summable(clause):
    return clause

def get_syntax_elements():
    return (if_clause, left_obj_quote, right_obj_quote, quote_obj, quote_val, 
            placeholder, get_summable, gte_not_equals)

def get_con_resources(con_dets, default_dbs, db=None):
    """
    When opening from scratch, e.g. clicking on Report Tables from Start,
        no db, so must identify one, but when selecting dbe-db in dropdowns, 
        there will be a db.
    Returns dict with con, cur, dbs, db.
    Connection keywords must be plain strings not unicode strings
    """
    con_dets_mysql = con_dets.get(mg.DBE_MYSQL)
    if not con_dets_mysql:
        raise Exception, u"No connection details available for MySQL"
    try:
        con_dets_mysql["use_unicode"] = True
        if db:
            con_dets_mysql["db"] = db
        con = MySQLdb.connect(**con_dets_mysql)
    except Exception, e:
        raise Exception, u"Unable to connect to MySQL db.  " + \
            u"Orig error: %s" % e
    cur = con.cursor() # must return tuples not dics    
    SQL_get_db_names = u"""SELECT SCHEMA_NAME 
            FROM information_schema.SCHEMATA
            WHERE SCHEMA_NAME <> 'information_schema'"""
    cur.execute(SQL_get_db_names)
    dbs = [x[0] for x in cur.fetchall()]
    dbs_lc = [x.lower() for x in dbs]
    if not db:
        # use default if possible, or fall back to first
        default_db_mysql = default_dbs.get(mg.DBE_MYSQL)
        if default_db_mysql.lower() in dbs_lc:
            db = default_db_mysql
        else:
            db = dbs[0]
        # need to reset con and cur
        cur.close()
        con.close()
        con_dets_mysql["db"] = db
        con = MySQLdb.connect(**con_dets_mysql)
        cur = con.cursor()
    else:
        if db.lower() not in dbs_lc:
            raise Exception, u"Database \"%s\" not available " % db + \
                u"from supplied connection"
    con_resources = {mg.DBE_CON: con, mg.DBE_CUR: cur, mg.DBE_DBS: [db,],
                     mg.DBE_DB: db}
    return con_resources

def get_tbls(cur, db):
    "Get table names given database and cursor"
    SQL_get_tbl_names = u"""SELECT TABLE_NAME 
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = %s
        UNION SELECT TABLE_NAME
        FROM information_schema.VIEWS
        WHERE TABLE_SCHEMA = %s """ % (quote_val(db), quote_val(db))
    cur.execute(SQL_get_tbl_names)
    tbls = [x[0] for x in cur.fetchall()] 
    tbls.sort(key=lambda s: s.upper())
    return tbls

def get_min_max(col_type, num_prec, dec_pts):
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

def get_flds(cur, db, tbl):
    """
    Returns details for set of fields given database, table, and cursor.
    NUMERIC_SCALE - number of significant digits to right of decimal point.
        Null if not numeric.
    NUMERIC_SCALE will be Null if not numeric.
    """
    debug = False
    numeric_lst = [BIGINT, DECIMAL, DOUBLE, FLOAT, INT, MEDIUMINT, 
                   SMALLINT, TINYINT]
    numeric_full_lst = []
    for num_type in numeric_lst:
        numeric_full_lst.append(num_type)
        numeric_full_lst.append(u"%s unsigned" % num_type)
    numeric_IN_clause = u"('" + u"', '".join(numeric_full_lst) + u"')"
    """SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME="" 
        AND TABLE_SCHEMA = "" """
    SQL_get_fld_dets = u"""SELECT 
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
        WHERE TABLE_NAME = %s
        AND TABLE_SCHEMA = %s """ % (quote_val(tbl), quote_val(db))
    if debug: print(SQL_get_fld_dets) 
    cur.execute(SQL_get_fld_dets)
    fld_dets = cur.fetchall()
    # build dic of fields, each with dic of characteristics
    flds = {}
    for (fld_name, ord_pos, nullable, fld_default, fld_type, max_len, 
             charset, numeric, autonum, dec_pts, num_prec, col_type, 
             boldatetime, timestamp) in fld_dets:
        bolnullable = True if nullable == u"YES" else False
        boldata_entry_ok = False if (autonum or timestamp) else True
        bolnumeric = True if numeric else False
        fld_txt = not bolnumeric and not boldatetime
        bolsigned = (col_type.find("unsigned") == -1)
        min_val, max_val = get_min_max(col_type, num_prec, dec_pts)
        dets_dic = {
                    mg.FLD_SEQ: ord_pos,
                    mg.FLD_BOLNULLABLE: bolnullable,
                    mg.FLD_DATA_ENTRY_OK: boldata_entry_ok,
                    mg.FLD_COLUMN_DEFAULT: fld_default,
                    mg.FLD_BOLTEXT: fld_txt,
                    mg.FLD_TEXT_LENGTH: max_len,
                    mg.FLD_CHARSET: charset,
                    mg.FLD_BOLNUMERIC: bolnumeric,
                    mg.FLD_BOLAUTONUMBER: autonum,
                    mg.FLD_DECPTS: dec_pts,
                    mg.FLD_NUM_WIDTH: num_prec,
                    mg.FLD_BOL_NUM_SIGNED: bolsigned,
                    mg.FLD_NUM_MIN_VAL: min_val,
                    mg.FLD_NUM_MAX_VAL: max_val,
                    mg.FLD_BOLDATETIME: boldatetime,
                    }
        flds[fld_name] = dets_dic
    if debug: print("flds: %s" % flds)
    return flds

def get_index_dets(cur, tbl):
    """
    has_unique - boolean
    idxs = [idx0, idx1, ...]
    each idx is a dict name, is_unique, flds
    """
    SQL_get_index_dets = u"""SELECT 
        INDEX_NAME, 
            GROUP_CONCAT(COLUMN_NAME) 
        AS fld_names,
            NOT NON_UNIQUE 
        AS unique_index
        FROM INFORMATION_SCHEMA.STATISTICS
        WHERE table_name = %s
        AND table_schema = %s
        GROUP BY INDEX_NAME """ % (quote_val(tbl), quote_val(db))
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
        idx_dic = {mg.IDX_NAME: idx_name, mg.IDX_IS_UNIQUE: unique_index, 
                   mg.IDX_FLDS: fld_names}
        idxs.append(idx_dic)
    debug = False
    if debug:
        pprint.pprint(idxs)
        print(has_unique)
    return idxs, has_unique

def set_data_con_gui(parent, readonly, scroll, szr, lblfont):
    # default database
    parent.lblMysqlDefaultDb = wx.StaticText(scroll, -1, 
                                             _("Default Database (name only):"))
    parent.lblMysqlDefaultDb.SetFont(lblfont)
    mysql_default_db = parent.mysql_default_db if parent.mysql_default_db \
        else ""
    parent.txtMysqlDefaultDb = wx.TextCtrl(scroll, -1, mysql_default_db, 
                                           size=(200,-1))
    parent.txtMysqlDefaultDb.Enable(not readonly)
    # default table
    parent.lblMysqlDefaultTbl = wx.StaticText(scroll, -1, 
                                       _("Default Table:"))
    parent.lblMysqlDefaultTbl.SetFont(lblfont)
    mysql_default_tbl = parent.mysql_default_tbl if parent.mysql_default_tbl \
        else ""
    parent.txtMysqlDefaultTbl = wx.TextCtrl(scroll, -1, mysql_default_tbl, 
                                            size=(200,-1))
    parent.txtMysqlDefaultTbl.Enable(not readonly)
    # host
    parent.lblMysqlHost = wx.StaticText(scroll, -1, _("Host:"))
    parent.lblMysqlHost.SetFont(lblfont)
    mysql_host = parent.mysql_host if parent.mysql_host else ""
    parent.txtMysqlHost = wx.TextCtrl(scroll, -1, mysql_host, size=(100,-1))
    parent.txtMysqlHost.Enable(not readonly)
    # user
    parent.lblMysqlUser = wx.StaticText(scroll, -1, _("User:"))
    parent.lblMysqlUser.SetFont(lblfont)
    mysql_user = parent.mysql_user if parent.mysql_user else ""
    parent.txtMysqlUser = wx.TextCtrl(scroll, -1, mysql_user, size=(100,-1))
    parent.txtMysqlUser.Enable(not readonly)
    # password
    parent.lblMysqlPwd = wx.StaticText(scroll, -1, _("Password:"))
    parent.lblMysqlPwd.SetFont(lblfont)
    mysql_pwd = parent.mysql_pwd if parent.mysql_pwd else ""
    parent.txtMysqlPwd = wx.TextCtrl(scroll, -1, mysql_pwd, size=(300,-1))
    parent.txtMysqlPwd.Enable(not readonly)
    #2 MYSQL
    bxMysql= wx.StaticBox(scroll, -1, "MySQL")
    parent.szrMysql = wx.StaticBoxSizer(bxMysql, wx.VERTICAL)
    #3 MYSQL INNER
    #4 MYSQL INNER TOP
    szrMysqlInnerTop = wx.BoxSizer(wx.HORIZONTAL)
    # default database
    szrMysqlInnerTop.Add(parent.lblMysqlDefaultDb, 0, wx.LEFT|wx.RIGHT, 5)
    szrMysqlInnerTop.Add(parent.txtMysqlDefaultDb, 0, wx.GROW|wx.RIGHT, 10)
    # default table
    szrMysqlInnerTop.Add(parent.lblMysqlDefaultTbl, 0, wx.LEFT|wx.RIGHT, 5)
    szrMysqlInnerTop.Add(parent.txtMysqlDefaultTbl, 0, wx.GROW|wx.RIGHT, 10)
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
    
def get_proj_settings(parent, proj_dic):
    parent.mysql_default_db = proj_dic["default_dbs"].get(mg.DBE_MYSQL)
    parent.mysql_default_tbl = \
        proj_dic["default_tbls"].get(mg.DBE_MYSQL)
    # optional (although if any mysql, for eg, must have all)
    if proj_dic["con_dets"].get(mg.DBE_MYSQL):
        parent.mysql_host = proj_dic["con_dets"][mg.DBE_MYSQL]["host"]
        parent.mysql_user = proj_dic["con_dets"][mg.DBE_MYSQL]["user"]
        parent.mysql_pwd = proj_dic["con_dets"][mg.DBE_MYSQL]["passwd"]
    else:
        parent.mysql_host, parent.mysql_user, parent.mysql_pwd = "", "", ""

def set_con_det_defaults(parent):
    try:
        parent.mysql_default_db
    except AttributeError:
        parent.mysql_default_db = u""
    try:
        parent.mysql_default_tbl
    except AttributeError: 
        parent.mysql_default_tbl = u""
    try:
        parent.mysql_host
    except AttributeError: 
        parent.mysql_host = u""
    try:
        parent.mysql_user
    except AttributeError: 
        parent.mysql_user = u""
    try:            
        parent.mysql_pwd
    except AttributeError: 
        parent.mysql_pwd = u""
    
def process_con_dets(parent, default_dbs, default_tbls, con_dets):
    mysql_default_db = parent.txtMysqlDefaultDb.GetValue()
    mysql_default_tbl = parent.txtMysqlDefaultTbl.GetValue()
    mysql_host = parent.txtMysqlHost.GetValue()
    mysql_user = parent.txtMysqlUser.GetValue()
    mysql_pwd = parent.txtMysqlPwd.GetValue()
    has_mysql_con = mysql_host and mysql_user and mysql_pwd \
        and mysql_default_db and mysql_default_tbl
    incomplete_mysql = (mysql_host or mysql_user or mysql_pwd \
        or mysql_default_db or mysql_default_tbl) and not has_mysql_con
    if incomplete_mysql:
        wx.MessageBox(_("The MySQL details are incomplete"))
        parent.txtMysqlDefaultDb.SetFocus()
    default_dbs[mg.DBE_MYSQL] = mysql_default_db \
        if mysql_default_db else None    
    default_tbls[mg.DBE_MYSQL] = mysql_default_tbl \
        if mysql_default_tbl else None
    if mysql_host and mysql_user and mysql_pwd:
        con_dets_mysql = {"host": mysql_host, "user": mysql_user, 
                           "passwd": mysql_pwd}
        con_dets[mg.DBE_MYSQL] = con_dets_mysql
    return incomplete_mysql, has_mysql_con
    