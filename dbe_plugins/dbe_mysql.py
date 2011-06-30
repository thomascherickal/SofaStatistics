from __future__ import print_function
from __future__ import division # so 5/2 = 2.5 not 2 !

# 0.9.25 the first to use pymysql (for OS X). 

import wx
import pprint

import my_globals as mg
if mg.PLATFORM == mg.MAC:
    import pymysql as mysql # easier to get working on a Mac
else:
    import MySQLdb as mysql
import my_exceptions
import lib

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
    return lib.quote_val(raw_val, unsafe_internal_quote=u'"', 
                         safe_internal_quote=u'""')

def get_summable(clause):
    return clause

def get_first_sql(tblname, top_n, order_val=None):
    orderby = u"ORDER BY %s" % quote_obj(order_val) if order_val else u""
    return u"SELECT * FROM %(tblname)s %(orderby)s LIMIT %(top_n)s" % \
        {"top_n": top_n, "tblname": quote_obj(tblname), "orderby": orderby}
        
def get_syntax_elements():
    return (if_clause, left_obj_quote, right_obj_quote, quote_obj, quote_val, 
            placeholder, get_summable, gte_not_equals)

def get_con_cur_for_db(con_dets_mysql, db):
    """
    Could use charset="utf8") http://mysql-python.sourceforge.net/MySQLdb.html
    """
    try:
        con_dets_mysql["use_unicode"] = True
        if db:
            con_dets_mysql["db"] = db
        con = mysql.connect(**con_dets_mysql)
    except Exception, e:
        raise Exception(u"Unable to connect to MySQL db. "
                        u"\nCaused by error: %s" % lib.ue(e))
    cur = con.cursor() # must return tuples not dics
    return con, cur

def get_dbs_list(con_dets, default_dbs):
    con_resources = get_con_resources(con_dets, default_dbs)
    con_resources[mg.DBE_CUR].close()
    con_resources[mg.DBE_CON].close()
    return con_resources[mg.DBE_DBS]

def get_con_resources(con_dets, default_dbs, db=None):
    """
    When opening from scratch, e.g. clicking on Report Tables from Start,
        no db, so must identify one, but when selecting dbe-db in dropdowns, 
        there will be a db.
    Returns dict with con, cur, dbs, db.
    Connection keywords must be plain strings not unicode strings.
    Using SHOW DATABASES works on old as well as new versions of MySQL.
    """
    con_dets_mysql = con_dets.get(mg.DBE_MYSQL)
    if not con_dets_mysql:
        raise my_exceptions.MissingConDets(mg.DBE_MYSQL)
    con, cur = get_con_cur_for_db(con_dets_mysql, db)
    #SQL_get_db_names = u"""SELECT SCHEMA_NAME 
    #        FROM information_schema.SCHEMATA
    #        WHERE SCHEMA_NAME <> 'information_schema'"""
    SQL_get_db_names = "SHOW DATABASES"
    cur.execute(SQL_get_db_names)
    # only want dbs with at least one table.
    all_dbs = [x[0] for x in cur.fetchall() if x[0] != u"information_schema"]
    dbs = []
    for db4list in all_dbs:
        try:
            con, cur = get_con_cur_for_db(con_dets_mysql, db4list)
        except Exception, e:
            continue
        if has_tbls(cur, db4list):
            dbs.append(db4list)
        cur.close()
        con.close()
    if not dbs:
        raise Exception(_("Unable to find any databases that have tables "
                          "and you have permission to access."))
    dbs_lc = [x.lower() for x in dbs]
    con, cur = get_con_cur_for_db(con_dets_mysql, db)
    if not db:
        # use default if possible, or fall back to first
        default_db_mysql = default_dbs.get(mg.DBE_MYSQL) # might be None
        db = dbs[0] # init
        if default_db_mysql:
            if default_db_mysql.lower() in dbs_lc:
                db = default_db_mysql
        # need to reset con and cur
        cur.close()
        con.close()
        con_dets_mysql["db"] = db
        con = mysql.connect(**con_dets_mysql)
        cur = con.cursor()
    else:
        if db.lower() not in dbs_lc:
            raise Exception(u"Database \"%s\" not available " % db +
                            u"from supplied connection")
    con_resources = {mg.DBE_CON: con, mg.DBE_CUR: cur, mg.DBE_DBS: dbs,
                     mg.DBE_DB: db}
    return con_resources

def get_tbls(cur, db):
    """
    Get table names given database and cursor.
    SHOW TABLES works with older versions of MySQL than information_schema
    """
    #SQL_get_tbl_names = u"""SELECT TABLE_NAME 
    #    FROM information_schema.TABLES
    #    WHERE TABLE_SCHEMA = %s
    #    UNION SELECT TABLE_NAME
    #    FROM information_schema.VIEWS
    #    WHERE TABLE_SCHEMA = %s """ % (quote_val(db), quote_val(db))
    SQL_get_tbl_names = u"""SHOW TABLES FROM %s """ % quote_obj(db)
    cur.execute(SQL_get_tbl_names)
    tbls = [x[0] for x in cur.fetchall()]
    tbls.sort(key=lambda s: s.upper())
    return tbls

def has_tbls(cur, db):
    "Any non-system tables?  Cursor should match db"
    SQL_get_tbl_names = u"""SHOW TABLES FROM %s """ % quote_obj(db)
    cur.execute(SQL_get_tbl_names)
    tbls = [x[0] for x in cur.fetchall()]
    if tbls:
        return True
    return False 

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
    SHOW COLUMNS FROM tbl FROM db
    returns content like the following:
    Field      Type              Null    Key    Default    Extra
    id         int(11)           NO      PRI               auto_increment
    fname      varchar(20)       YES     MUL
    lname      varchar(20)       YES
    age        int(11)           YES     MUL
    isdec      decimal(10,0)     YES
    unsigned   int(10) unsigned  YES 
    """
    debug = False
    numeric_lst = [BIGINT, DECIMAL, DOUBLE, FLOAT, INT, MEDIUMINT, SMALLINT, 
                   TINYINT]
    datetime_lst = ('date', 'time', 'datetime', 'timestamp', 'year')
    
    SQL_get_create_tbl_dets = "SHOW CREATE TABLE %s" % quote_obj(tbl)
    cur.execute(SQL_get_create_tbl_dets)
    create_tbl_dets = cur.fetchone()[1]
    if debug: print(create_tbl_dets)
    try:
        start_idx = create_tbl_dets.index(u"DEFAULT CHARSET=") + \
            len(u"DEFAULT CHARSET=")
        tbl_charset = create_tbl_dets[start_idx:].strip()
    except ValueError: # e.g. if a view
        tbl_charset = u"latin1" # but could be anything - need to use 
            # information_schema approach to determine but that doesn't work in
            # older versions of MySQL
    SQL_get_fld_dets = "SHOW COLUMNS FROM %s FROM %s" % (quote_obj(tbl), 
                                                         quote_obj(db))
    cur.execute(SQL_get_fld_dets)
    flds = {}
    for i, row in enumerate(cur.fetchall()):
        if debug: print(row)
        fld_name, col_type, nullable, unused, fld_default, extra = row
        bolnullable = True if nullable == u"YES" else False
        autonum = u"auto_increment" in extra
        timestamp = col_type.lower().startswith("timestamp")
        boldata_entry_ok = not (autonum or timestamp)
        bolnumeric = False
        for num_type in numeric_lst:
            if col_type.lower().startswith(num_type):
                bolnumeric = True
                break
        if fld_default and bolnumeric:
            fld_default = float(fld_default) # so 0.0 not '0.0'
        boldatetime = False
        for dt_type in datetime_lst:
            if col_type.lower().startswith(dt_type):
                boldatetime = True
                break
        fld_txt = not bolnumeric and not boldatetime
        bolsigned = (col_type.find("unsigned") == -1) if bolnumeric else None
        # init
        num_prec = None
        dec_pts = None
        if col_type.lower().startswith(DECIMAL) or \
                col_type.lower().startswith(FLOAT):
            # e.g. get 10 and 0 from "(10,0)"
            try:
                num_prec, dec_pts = [int(x) for x in 
                    col_type[col_type.index(u"("):].strip()[1:-1].split(u",")]
            except Exception:
                if col_type.lower().startswith(FLOAT):
                    num_prec = 12
        elif col_type.lower().startswith(INT):
            num_prec = 10
            dec_pts = 0
        min_val, max_val = get_min_max(col_type, num_prec, dec_pts)
        max_len = None
        if fld_txt:
            try:
                txt_len = col_type[col_type.index(u"("):].strip()[1:-1]
                max_len = int(txt_len)
            except Exception:
                pass
        charset = tbl_charset if fld_txt else None
        dets_dic = {
                    mg.FLD_SEQ: i,
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

def get_index_dets(cur, db, tbl):
    """
    db -- needed by some dbes sharing interface.
    has_unique -- boolean
    idxs = [idx0, idx1, ...]
    Each idx is a dict with name, is_unique, flds
    SHOW INDEX FROM tbl FROM db
    returns content like the following:
    Table  Non_unique  Key_name    Seq_in_index  Column_name ...
    tbltest    0       PRIMARY     1             id
    tbltest    1       names_idx   1             fname
    tbltest    1       names_idx   2             lname
    tbltest    1       age_idx     1             age 
    """
    debug = False
    SQL_get_idx_dets = "SHOW INDEX FROM %s FROM %s" % (quote_obj(tbl), 
                                                       quote_obj(db))
    cur.execute(SQL_get_idx_dets)
    idx_dets = {} # key_name is the key
    idx_seq = {} # e.g. {0: "fname", 1: "lname"}
    next_seq = 0
    has_unique = False
    for row in cur.fetchall():
        # each key needs name, fld names, has_unique
        non_unique = row[1]
        if not non_unique:
            has_unique = True
        key_name = row[2]
        seq_in_idx = row[3]
        col_name = row[4]   
        if key_name not in idx_dets:
            # set up dict and seed with initial values
            # only change possible is adding additional flds if in idx
            idx_dets[key_name] = {mg.IDX_NAME: key_name, 
                                  mg.IDX_IS_UNIQUE: not non_unique,
                                  mg.IDX_FLDS: [col_name,]}
            # need to keep sort order of idx_dets 
            idx_seq[next_seq] = key_name
            next_seq += 1
        else:
            # only need to add any additional flds
            idx_dets[key_name][mg.IDX_FLDS].append(col_name)
    # get list of key_names sorted by idx sequence
    # idx_seq e.g. {0: "fname", 1: "lname"}
    lst_key_names = [idx_seq[x] for x in sorted(idx_seq)]
    # use sorted key_names to get sorted list of idx dicts
    idxs = []
    for key_name in lst_key_names:
        idxs.append(idx_dets[key_name])
    if debug:
        pprint.pprint(idxs)
        print(has_unique)
    return idxs, has_unique

def set_data_con_gui(parent, readonly, scroll, szr, lblfont):
    bx_mysql= wx.StaticBox(scroll, -1, "MySQL")
    # default database
    parent.lbl_mysql_default_db = wx.StaticText(scroll, -1, 
                                             _("Default Database (name only):"))
    parent.lbl_mysql_default_db.SetFont(lblfont)
    mysql_default_db = parent.mysql_default_db if parent.mysql_default_db \
        else u""
    parent.txt_mysql_default_db = wx.TextCtrl(scroll, -1, mysql_default_db, 
                                              size=(200,-1))
    parent.txt_mysql_default_db.Enable(not readonly)
    parent.txt_mysql_default_db.SetToolTipString(_("Default database"
                                                   " (optional)"))
    # default table
    parent.lbl_mysql_default_tbl = wx.StaticText(scroll, -1, 
                                       _("Default Table:"))
    parent.lbl_mysql_default_tbl.SetFont(lblfont)
    mysql_default_tbl = parent.mysql_default_tbl if parent.mysql_default_tbl \
        else u""
    parent.txt_mysql_default_tbl = wx.TextCtrl(scroll, -1, mysql_default_tbl, 
                                               size=(200,-1))
    parent.txt_mysql_default_tbl.Enable(not readonly)
    parent.txt_mysql_default_tbl.SetToolTipString(_("Default table (optional)"))
    # host
    parent.lbl_mysql_host = wx.StaticText(scroll, -1, _("Host:"))
    parent.lbl_mysql_host.SetFont(lblfont)
    mysql_host = parent.mysql_host if parent.mysql_host else ""
    parent.txt_mysql_host = wx.TextCtrl(scroll, -1, mysql_host, size=(100,-1))
    parent.txt_mysql_host.Enable(not readonly)
    parent.txt_mysql_host.SetToolTipString(_("Host e.g. localhost, or "
                                             "remote:3307"))
    # user
    parent.lbl_mysql_user = wx.StaticText(scroll, -1, _("User:"))
    parent.lbl_mysql_user.SetFont(lblfont)
    mysql_user = parent.mysql_user if parent.mysql_user else ""
    parent.txt_mysql_user = wx.TextCtrl(scroll, -1, mysql_user, size=(100,-1))
    parent.txt_mysql_user.Enable(not readonly)
    parent.txt_mysql_user.SetToolTipString(_("User e.g. root"))
    # password
    parent.lbl_mysql_pwd = wx.StaticText(scroll, -1, _("Password:"))
    parent.lbl_mysql_pwd.SetFont(lblfont)
    mysql_pwd = parent.mysql_pwd if parent.mysql_pwd else u""
    parent.txt_mysql_pwd = wx.TextCtrl(scroll, -1, mysql_pwd, size=(300,-1),
                                       style=wx.TE_PASSWORD)
    parent.txt_mysql_pwd.Enable(not readonly)
    parent.txt_mysql_pwd.SetToolTipString(_("Password"))
    #2 MYSQL
    parent.szr_mysql = wx.StaticBoxSizer(bx_mysql, wx.VERTICAL)
    #3 MYSQL INNER
    #4 MYSQL INNER TOP
    szr_mysql_inner_top = wx.BoxSizer(wx.HORIZONTAL)
    # default database
    szr_mysql_inner_top.Add(parent.lbl_mysql_default_db, 0, 
                            wx.LEFT|wx.RIGHT, 5)
    szr_mysql_inner_top.Add(parent.txt_mysql_default_db, 0, 
                            wx.GROW|wx.RIGHT, 10)
    # default table
    szr_mysql_inner_top.Add(parent.lbl_mysql_default_tbl, 0, 
                            wx.LEFT|wx.RIGHT, 5)
    szr_mysql_inner_top.Add(parent.txt_mysql_default_tbl, 0, 
                            wx.GROW|wx.RIGHT, 10)
    #4 MYSQL INNER BOTTOM
    szr_mysql_inner_btm = wx.BoxSizer(wx.HORIZONTAL)
    # host 
    szr_mysql_inner_btm.Add(parent.lbl_mysql_host, 0, wx.LEFT|wx.RIGHT, 5)
    szr_mysql_inner_btm.Add(parent.txt_mysql_host, 0, wx.RIGHT, 10)
    # user
    szr_mysql_inner_btm.Add(parent.lbl_mysql_user, 0, wx.LEFT|wx.RIGHT, 5)
    szr_mysql_inner_btm.Add(parent.txt_mysql_user, 0, wx.RIGHT, 10)
    # password
    szr_mysql_inner_btm.Add(parent.lbl_mysql_pwd, 0, wx.LEFT|wx.RIGHT, 5)
    szr_mysql_inner_btm.Add(parent.txt_mysql_pwd, 1, wx.GROW|wx.RIGHT, 10)
    #2 combine
    parent.szr_mysql.Add(szr_mysql_inner_top, 0, wx.GROW|wx.ALL, 5)
    parent.szr_mysql.Add(szr_mysql_inner_btm, 0, wx.ALL, 5)
    szr.Add(parent.szr_mysql, 0, wx.GROW|wx.ALL, 10)
    
def get_proj_settings(parent, proj_dic):
    """
    Want to store port, but not complicate things for the user unnecessarily. So
        only show host:port if non-standard port.
    """
    parent.mysql_default_db = proj_dic[mg.PROJ_DEFAULT_DBS].get(mg.DBE_MYSQL)
    parent.mysql_default_tbl = proj_dic[mg.PROJ_DEFAULT_TBLS].get(mg.DBE_MYSQL)
    # optional (although if any mysql, for eg, must have host, user, and passwd)
    if proj_dic[mg.PROJ_CON_DETS].get(mg.DBE_MYSQL):
        raw_host = proj_dic[mg.PROJ_CON_DETS][mg.DBE_MYSQL]["host"]
        raw_port = proj_dic[mg.PROJ_CON_DETS][mg.DBE_MYSQL].get("port", 3306)
        if raw_port != 3306:
            parent.mysql_host = u"%s:%s" % (raw_host, raw_port)
        else:
            parent.mysql_host = raw_host
        parent.mysql_user = proj_dic[mg.PROJ_CON_DETS][mg.DBE_MYSQL]["user"]
        parent.mysql_pwd = proj_dic[mg.PROJ_CON_DETS][mg.DBE_MYSQL]["passwd"]
    else:
        parent.mysql_host, parent.mysql_user, parent.mysql_pwd = u"", u"", u""

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
    """
    Can pass in port at end of host (separated by a colon e.g. remote:3007).
    Copes with missing default database and table. Will get the first available.
    """
    default_db = parent.txt_mysql_default_db.GetValue()
    mysql_default_db = default_db if default_db else None
    default_tbl = parent.txt_mysql_default_tbl.GetValue()
    mysql_default_tbl = default_tbl if default_tbl else None
    # separate port out if present (separated by :)
    raw_host = parent.txt_mysql_host.GetValue()
    if u":" in raw_host:
        mysql_host, raw_port = raw_host.split(u":")
        try:
            mysql_port = int(raw_port)
        except ValueError:
            raise Exception(u"Host had a ':' but the port was not an integer "
                            u"e.g. 3307")
    else:
        mysql_host = raw_host
        mysql_port = 3306
    mysql_user = parent.txt_mysql_user.GetValue()
    mysql_pwd = parent.txt_mysql_pwd.GetValue()
    has_mysql_con = mysql_host and mysql_user # allow blank password
    dirty = (mysql_host or mysql_user or mysql_pwd or mysql_default_db 
             or mysql_default_tbl)
    incomplete_mysql = dirty and not has_mysql_con
    if incomplete_mysql:
        wx.MessageBox(_("The MySQL details are incomplete"))
        parent.txt_mysql_default_db.SetFocus()
    default_dbs[mg.DBE_MYSQL] = mysql_default_db
    default_tbls[mg.DBE_MYSQL] = mysql_default_tbl
    if mysql_host and mysql_user and mysql_pwd:
        # no unicode keys for 2.6 bug http://bugs.python.org/issue2646
        con_dets_mysql = {"host": mysql_host, "port": mysql_port, 
                          "user": mysql_user, "passwd": mysql_pwd}
        con_dets[mg.DBE_MYSQL] = con_dets_mysql
    return incomplete_mysql, has_mysql_con
    