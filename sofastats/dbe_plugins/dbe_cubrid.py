from __future__ import print_function
from __future__ import division # so 5/2 = 2.5 not 2 !

"""
http://www.cubrid.org/wiki_apis/entry/cubrid-odbc-driver-installation-instructions
sudo service cubrid start demodb

sudo su -s $SHELL cubrid 
cubrid broker start

sudo service cubrid stop
csql demodb
"""

import os
import wx
import pprint

from sofastats import basic_lib as b
from sofastats import my_globals as mg
from sofastats import my_exceptions
from sofastats import lib
import CUBRIDdb as cubrid

# http://www.cubrid.org/manual/841/en/Data%20Types
# numeric data types
INT = u"int"
INTEGER = u"integer"
SHORT = u"short"
SMALLINT = u"smallint"
BIGINT = u"bigint"
DECIMAL = u"decimal"
NUMERIC = u"numeric"
DOUBLE = u"double"
DOUBLE_PRECISION = u"double precision"
FLOAT = u"float"
REAL = u"real"
DOUBLE = u"double"
MONETARY = u"monetary"

DEFAULT_PORT = 33000

if_clause = u"IF(%s, %s, %s)"
placeholder = u"?"
left_obj_quote = u"`"
right_obj_quote = u"`"
gte_not_equals = u"!="
cartesian_joiner = u","

def quote_obj(raw_val):
    return u"%s%s%s" % (left_obj_quote, raw_val, right_obj_quote)

def quote_val(raw_val, charset2try="iso-8859-1"):
    return lib.DbLib.quote_val(raw_val, sql_str_literal_quote=u"'", 
                         sql_esc_str_literal_quote=u"''", 
                         pystr_use_double_quotes=True, charset2try=charset2try)

def get_summable(clause):
    return u"CASE WHEN %s THEN 1 ELSE 0 END" % clause

def get_first_sql(quoted_tblname, top_n, order_val=None):
    orderby = u"ORDER BY %s" % quote_obj(order_val) if order_val else u""
    return (u"SELECT * FROM %(tblname)s %(orderby)s LIMIT %(top_n)s" %
            {"top_n": top_n, "tblname": quoted_tblname, "orderby": orderby})
        
def get_syntax_elements():
    return (if_clause, left_obj_quote, right_obj_quote, quote_obj, quote_val, 
            placeholder, get_summable, gte_not_equals, cartesian_joiner)

def get_con_cur_for_db(con_dets_cubrid, db):
    """
    Could use charset="utf8") http://mysql-python.sourceforge.net/CUBRIDdb.html
    """
    try:
        cubrid_db = "demodb"
        if db:
            cubrid_db = db
        con_url = u"CUBRID:%s:%s:%s:%s:%s" % (con_dets_cubrid["host"], 
                                              con_dets_cubrid["port"], 
                                              cubrid_db, 
                                              con_dets_cubrid["user"],
                                              con_dets_cubrid["passwd"])
        con = cubrid.connect(con_url)
    except Exception, e:
        raise Exception(u"Unable to connect to CUBRID db using %s. "
            u"\nCaused by error: %s" % (con_url, b.ue(e)))
    cur = con.cursor() # must return tuples not dics
    return con, cur

def get_dbs_list(con_dets, default_dbs):
    con_resources = get_con_resources(con_dets, default_dbs)
    con_resources[mg.DBE_CUR].close()
    con_resources[mg.DBE_CON].close()
    return con_resources[mg.DBE_DBS]

def get_con_resources(con_dets, default_dbs, db=None):
    con_dets_cubrid = con_dets.get(mg.DBE_CUBRID)
    if not con_dets_cubrid:
        raise my_exceptions.MissingConDets(mg.DBE_CUBRID)
    con, cur = get_con_cur_for_db(con_dets_cubrid, db)

    #get database list from databases.txt file
    all_dbs = []
    env = os.getenv("CUBRID_DATABASES")
    if env is not None:
        f = open(env+"/databases.txt","r")
        line = f.readline() #skip first line
        line = f.readline()
        while line:
            all_dbs.append(line.partition('\t')[0])
            line = f.readline()
        f.close()
    
    # only want dbs with at least one table.
    dbs = []
    for db4list in all_dbs:
        try:
            con, cur = get_con_cur_for_db(con_dets_cubrid, db4list)
        except Exception:
            continue
        if has_tbls(cur, db4list):
            dbs.append(db4list)
        cur.close()
        con.close()
    if not dbs:
        raise Exception(_("Unable to find any databases that have tables "
                          "and you have permission to access."))
    dbs_lc = [x.lower() for x in dbs]
    con, cur = get_con_cur_for_db(con_dets_cubrid, db)
    if not db:
        # use default if possible, or fall back to first
        default_db_cubrid = default_dbs.get(mg.DBE_CUBRID) # might be None
        db = dbs[0] # init
        if default_db_cubrid:
            if default_db_cubrid.lower() in dbs_lc:
                db = default_db_cubrid
        # need to reset con and cur
        cur.close()
        con.close()
        cubrid_db = "demodb"
        if db:
            cubrid_db = db
        con_url = u"CUBRID:%s:%s:%s:%s:%s" % (con_dets_cubrid["host"], 
                                              con_dets_cubrid["port"], 
                                              cubrid_db, 
                                              con_dets_cubrid["user"],
                                              con_dets_cubrid["passwd"])        
        con = cubrid.connect(con_url)
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
    """
    SQL_get_tblnames = u"SHOW TABLES"
    cur.execute(SQL_get_tblnames)
    tbls = [x[0] for x in cur.fetchall()]
    tbls.sort(key=lambda s: s.upper())
    return tbls

def has_tbls(cur, db):
    SQL_get_tblnames = u"SHOW TABLES"
    cur.execute(SQL_get_tblnames)
    tbls = [x[0] for x in cur.fetchall()]
    if tbls:
        return True
    return False 

def get_min_max(coltype, num_prec, dec_pts):
    """
    Use coltype not fldtype.  The former is inconsistent - float 
        and double have unsigned at end but not rest!
    Returns minimum and maximum allowable numeric values.
    NB even though a floating point type will not store values closer 
        to zero than a certain level, such values will be accepted here.
        The database will store these as zero.
    """
    if coltype.lower().startswith(SHORT):
        min_val = -(2**15)
        max_val = (2**15)-1
    elif coltype.lower().startswith(SMALLINT):
        min_val = -(2**15)
        max_val = (2**15)-1
    elif coltype.lower().startswith(INT):
        min_val = -(2**31)
        max_val = (2**31)-1
    elif coltype.lower().startswith(INTEGER):
        min_val = -(2**31)
        max_val = (2**31)-1
    elif coltype.lower().startswith(BIGINT):
        min_val = -(2**63)
        max_val = (2**63)-1
    elif coltype.lower().startswith(FLOAT):
        min_val = -3.402823466E+38
        max_val = 3.402823466E+38
    elif coltype.lower().startswith(REAL):
        min_val = -3.402823466E+38
        max_val = 3.402823466E+38
    elif coltype.lower().startswith(DOUBLE):
        min_val = -1.7976931348623157E+308
        max_val = 1.7976931348623157E+308
    elif coltype.lower().startswith(DOUBLE_PRECISION):
        min_val = -1.7976931348623157E+308
        max_val = 1.7976931348623157E+308
    elif coltype.lower().startswith(MONETARY):
        min_val = -3.402823466E+38
        max_val = 3.402823466E+38
    elif coltype.lower().startswith(DECIMAL):
        abs_max = ((10**(num_prec + 1))-1)/(10**dec_pts)
        min_val = -abs_max
        max_val = abs_max
    elif coltype.lower().startswith(NUMERIC):
        abs_max = ((10**(num_prec + 1))-1)/(10**dec_pts)
        min_val = -abs_max
        max_val = abs_max
    else:
        min_val = None
        max_val = None
    return min_val, max_val

def get_flds(cur, db, tbl):
    """
    Returns details for set of fields given database, table, and cursor.
    NUMERIC_SCALE - number of significant digits to right of decimal point.
        Null if not numeric or decimal.
    NUMERIC_SCALE will be Null if not numeric.
    SHOW COLUMNS FROM tbl
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
    # http://www.cubrid.org/manual/841/en/Numeric%20Types
    numeric_lst = [INT, INTEGER, SHORT, SMALLINT, BIGINT, DECIMAL, DOUBLE, 
                   FLOAT, REAL, DOUBLE, DOUBLE_PRECISION, MONETARY]
    # http://www.cubrid.org/manual/841/en/Date%7CTime%20Types
    datetime_lst = ('date', 'time', 'datetime', 'timestamp')
    """
    iso8859-1 is the default charset for CUBRID.
    CUBRID also supports UTF-8 and EUC-KR charsets. There is one restriction 
        though as even though you can store data in other character sets, string 
        functions or LIKE search are not supported.
    """
    tbl_charset = u"iso8859-1"
    SQL_get_fld_dets = "SHOW COLUMNS FROM %s" % (quote_obj(tbl))
    cur.execute(SQL_get_fld_dets)
    flds = {}
    for i, row in enumerate(cur.fetchall()):
        if debug: print(row)
        fldname, coltype, nullable, unused, fld_default, extra = row
        bolnullable = (nullable == u"YES")
        autonum = u"auto_increment" in extra
        timestamp = coltype.lower().startswith("timestamp")
        boldata_entry_ok = not (autonum or timestamp)
        bolnumeric = False
        for num_type in numeric_lst:
            if coltype.lower().startswith(num_type):
                bolnumeric = True
                break
        if fld_default and bolnumeric:
            fld_default = float(fld_default) # so 0.0 not '0.0'
        boldatetime = False
        for dt_type in datetime_lst:
            if coltype.lower().startswith(dt_type):
                boldatetime = True
                break
        fld_txt = not bolnumeric and not boldatetime
        bolsigned = True if bolnumeric else None
        # init
        num_prec = None
        dec_pts = None
        #decimal or numeric
        if (coltype.lower().startswith(DECIMAL) 
                or coltype.lower().startswith(NUMERIC)):
            try:
                (num_prec, 
                 dec_pts) = [int(x) for x in 
                        coltype[coltype.index(u"("):].strip()[1:-1].split(u",")]
            except Exception:
                num_prec = None
                dec_pts = None
        # int or integer
        elif coltype.lower().startswith(INT):
            num_prec = 10
            dec_pts = 0
        # short or smallint
        elif (coltype.lower().startswith(SMALLINT) 
              or coltype.lower().startswith(SHORT)):
            num_prec = 5
            dec_pts = 0
        # bigint
        elif coltype.lower().startswith(BIGINT):
            num_prec = 19
            dec_pts = 0
        # float, real or monetary
        elif (coltype.lower().startswith(FLOAT) 
              or coltype.lower().startswith(REAL) 
              or coltype.lower().startswith(MONETARY)):
            num_prec = 12
        # double or double precision
        elif coltype.lower().startswith(DOUBLE):
            num_prec = 20
        min_val, max_val = get_min_max(coltype, num_prec, dec_pts)
        max_len = None
        if fld_txt:
            try:
                txt_len = coltype[coltype.index(u"("):].strip()[1:-1]
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
        flds[fldname] = dets_dic
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
    SQL_get_idx_dets = "SHOW INDEX FROM %s" % (quote_obj(tbl))
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
        #seq_in_idx = row[3]
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
    bx_cubrid= wx.StaticBox(scroll, -1, "CUBRID")
    # default database
    parent.lbl_cubrid_default_db = wx.StaticText(scroll, -1, 
                                             _("Default Database (name only):"))
    parent.lbl_cubrid_default_db.SetFont(lblfont)
    cubrid_default_db = (parent.cubrid_default_db if parent.cubrid_default_db
                         else u"")
    parent.txt_cubrid_default_db = wx.TextCtrl(scroll, -1, cubrid_default_db, 
                                              size=(200,-1))
    parent.txt_cubrid_default_db.Enable(not readonly)
    parent.txt_cubrid_default_db.SetToolTipString(_("Default database"))
    # default table
    parent.lbl_cubrid_default_tbl = wx.StaticText(scroll, -1, 
                                       _("Default Table:"))
    parent.lbl_cubrid_default_tbl.SetFont(lblfont)
    cubrid_default_tbl = (parent.cubrid_default_tbl if parent.cubrid_default_tbl
                          else u"")
    parent.txt_cubrid_default_tbl = wx.TextCtrl(scroll, -1, cubrid_default_tbl, 
                                               size=(200,-1))
    parent.txt_cubrid_default_tbl.Enable(not readonly)
    parent.txt_cubrid_default_tbl.SetToolTipString(_("Default table "
                                                     "(optional)"))
    # host
    parent.lbl_cubrid_host = wx.StaticText(scroll, -1, _("Host:"))
    parent.lbl_cubrid_host.SetFont(lblfont)
    cubrid_host = parent.cubrid_host if parent.cubrid_host else ""
    parent.txt_cubrid_host = wx.TextCtrl(scroll, -1, cubrid_host, size=(100,-1))
    parent.txt_cubrid_host.Enable(not readonly)
    parent.txt_cubrid_host.SetToolTipString(_("Host e.g. localhost, or "
                                              "localhost:%s" % DEFAULT_PORT))
    # user
    parent.lbl_cubrid_user = wx.StaticText(scroll, -1, _("User:"))
    parent.lbl_cubrid_user.SetFont(lblfont)
    cubrid_user = parent.cubrid_user if parent.cubrid_user else ""
    parent.txt_cubrid_user = wx.TextCtrl(scroll, -1, cubrid_user, size=(100,-1))
    parent.txt_cubrid_user.Enable(not readonly)
    parent.txt_cubrid_user.SetToolTipString(_("User e.g. dba"))
    # password
    parent.lbl_cubrid_pwd = wx.StaticText(scroll, -1, _("Password:"))
    parent.lbl_cubrid_pwd.SetFont(lblfont)
    cubrid_pwd = parent.cubrid_pwd if parent.cubrid_pwd else u""
    parent.txt_cubrid_pwd = wx.TextCtrl(scroll, -1, cubrid_pwd, size=(300,-1),
                                       style=wx.TE_PASSWORD)
    parent.txt_cubrid_pwd.Enable(not readonly)
    parent.txt_cubrid_pwd.SetToolTipString(_("Password"))
    #2 CUBRID
    parent.szr_cubrid = wx.StaticBoxSizer(bx_cubrid, wx.VERTICAL)
    #3 CUBRID INNER
    #4 CUBRID INNER TOP
    szr_cubrid_inner_top = wx.BoxSizer(wx.HORIZONTAL)
    # default database
    szr_cubrid_inner_top.Add(parent.lbl_cubrid_default_db, 0, 
                            wx.LEFT|wx.RIGHT, 5)
    szr_cubrid_inner_top.Add(parent.txt_cubrid_default_db, 0, 
                            wx.GROW|wx.RIGHT, 10)
    # default table
    szr_cubrid_inner_top.Add(parent.lbl_cubrid_default_tbl, 0, 
                            wx.LEFT|wx.RIGHT, 5)
    szr_cubrid_inner_top.Add(parent.txt_cubrid_default_tbl, 0, 
                            wx.GROW|wx.RIGHT, 10)
    #4 CUBRID INNER BOTTOM
    szr_cubrid_inner_btm = wx.BoxSizer(wx.HORIZONTAL)
    # host 
    szr_cubrid_inner_btm.Add(parent.lbl_cubrid_host, 0, wx.LEFT|wx.RIGHT, 5)
    szr_cubrid_inner_btm.Add(parent.txt_cubrid_host, 0, wx.RIGHT, 10)
    # user
    szr_cubrid_inner_btm.Add(parent.lbl_cubrid_user, 0, wx.LEFT|wx.RIGHT, 5)
    szr_cubrid_inner_btm.Add(parent.txt_cubrid_user, 0, wx.RIGHT, 10)
    # password
    szr_cubrid_inner_btm.Add(parent.lbl_cubrid_pwd, 0, wx.LEFT|wx.RIGHT, 5)
    szr_cubrid_inner_btm.Add(parent.txt_cubrid_pwd, 1, wx.GROW|wx.RIGHT, 10)
    #2 combine
    parent.szr_cubrid.Add(szr_cubrid_inner_top, 0, wx.GROW|wx.ALL, 5)
    parent.szr_cubrid.Add(szr_cubrid_inner_btm, 0, wx.ALL, 5)
    szr.Add(parent.szr_cubrid, 0, wx.GROW|wx.ALL, 10)
    
def get_proj_settings(parent, proj_dic):
    """
    Want to store port, but not complicate things for the user unnecessarily. So
        only show host:port if non-standard port.
    """
    parent.cubrid_default_db = proj_dic[mg.PROJ_DEFAULT_DBS].get(mg.DBE_CUBRID)
    parent.cubrid_default_tbl = proj_dic[mg.PROJ_DEFAULT_TBLS].get(mg.DBE_CUBRID)
    # optional (although if any mysql, for eg, must have host, user, and passwd)
    if proj_dic[mg.PROJ_CON_DETS].get(mg.DBE_CUBRID):
        raw_host = proj_dic[mg.PROJ_CON_DETS][mg.DBE_CUBRID]["host"]
        raw_port = proj_dic[mg.PROJ_CON_DETS][mg.DBE_CUBRID].get("port",
            DEFAULT_PORT)
        if raw_port != DEFAULT_PORT:
            parent.cubrid_host = u"%s:%s" % (raw_host, raw_port)
        else:
            parent.cubrid_host = raw_host
        parent.cubrid_user = proj_dic[mg.PROJ_CON_DETS][mg.DBE_CUBRID]["user"]
        parent.cubrid_pwd = proj_dic[mg.PROJ_CON_DETS][mg.DBE_CUBRID]["passwd"]
    else:
        (parent.cubrid_host, parent.cubrid_user, 
         parent.cubrid_pwd) = u"", u"", u""

def set_con_det_defaults(parent):
    try:
        parent.cubrid_default_db
    except AttributeError:
        parent.cubrid_default_db = u"demodb"
    try:
        parent.cubrid_default_tbl
    except AttributeError: 
        parent.cubrid_default_tbl = u""
    try:
        parent.cubrid_host
    except AttributeError: 
        parent.cubrid_host = u""
    try:
        parent.cubrid_user
    except AttributeError: 
        parent.cubrid_user = u"dba"
    try:            
        parent.cubrid_pwd
    except AttributeError: 
        parent.cubrid_pwd = u""
    
def process_con_dets(parent, default_dbs, default_tbls, con_dets):
    """
    Can pass in port at end of host (separated by a colon e.g. localhost:33000).
    Copes with missing default database and table. Will get the first available.
    """
    default_db = parent.txt_cubrid_default_db.GetValue()
    cubrid_default_db = default_db if default_db else None
    default_tbl = parent.txt_cubrid_default_tbl.GetValue()
    cubrid_default_tbl = default_tbl if default_tbl else None
    # separate port out if present (separated by :)
    raw_host = parent.txt_cubrid_host.GetValue()
    if u":" in raw_host:
        cubrid_host, raw_port = raw_host.split(u":")
        try:
            cubrid_port = int(raw_port)
        except ValueError:
            raise Exception(u"Host had a ':' but the port was not an integer "
                            u"e.g. localhost:%s" % DEFAULT_PORT)
    else:
        cubrid_host = raw_host
        cubrid_port = DEFAULT_PORT
    cubrid_user = parent.txt_cubrid_user.GetValue()
    cubrid_pwd = parent.txt_cubrid_pwd.GetValue()
    has_cubrid_con = cubrid_host and cubrid_user and cubrid_default_db # allow blank password
    dirty = (cubrid_host or cubrid_user or cubrid_pwd or cubrid_default_db 
             or cubrid_default_tbl)
    incomplete_cubrid = dirty and not has_cubrid_con
    if incomplete_cubrid:
        wx.MessageBox(_("The CUBRID details are incomplete"))
        parent.txt_cubrid_default_db.SetFocus()
    default_dbs[mg.DBE_CUBRID] = cubrid_default_db
    default_tbls[mg.DBE_CUBRID] = cubrid_default_tbl
    if has_cubrid_con:
        con_dets_cubrid = {"host": cubrid_host, "port": cubrid_port, 
                          "user": cubrid_user, "passwd": cubrid_pwd}
        con_dets[mg.DBE_CUBRID] = con_dets_cubrid
    return incomplete_cubrid, has_cubrid_con