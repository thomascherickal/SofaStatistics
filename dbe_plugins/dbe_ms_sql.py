# Must run makepy once - 
# see http://www.thescripts.com/forum/thread482449.html e.g. the following 
# way - run PYTHON\Lib\site-packages\pythonwin\pythonwin.exe (replace PYTHON 
# with folder python is in).  Tools>COM Makepy utility - select appropriate 
# library - e.g. for ADO it would be Microsoft ActiveX Data Objects 2.8 Library 
# (2.8) - and select OK. NB DAO must be done separately from ADO etc.

from __future__ import print_function
import adodbapi
import win32com.client

import wx
import pprint

import my_globals as mg
import dbe_plugins.dbe_globals as dbe_globals
import my_exceptions
import lib

AD_OPEN_KEYSET = 1
AD_LOCK_OPTIMISTIC = 3
AD_SCHEMA_COLUMNS = 4

if_clause = u"CASE WHEN %s THEN %s ELSE %s END"
placeholder = u"?"
left_obj_quote = u"["
right_obj_quote = u"]"
gte_not_equals = u"!="

def quote_obj(raw_val):
    return u"%s%s%s" % (left_obj_quote, raw_val, right_obj_quote)

def quote_val(raw_val):
    return lib.quote_val(raw_val, unsafe_internal_quote=u"'", 
                         safe_internal_quote=u"''")

def get_summable(clause):
    return u"CASE WHEN %s THEN 1 ELSE 0 END" % clause

def get_first_sql(tblname, top_n, order_val=None):
    orderby = u"ORDER BY %s" % quote_obj(order_val) if order_val else u""
    return u"SELECT TOP %(top_n)s * FROM %(tblname)s %(orderby)s" % \
        {"top_n": top_n, "tblname": quote_obj(tblname), "orderby": orderby}
        
def get_syntax_elements():
    return (if_clause, left_obj_quote, right_obj_quote, quote_obj, quote_val, 
            placeholder, get_summable, gte_not_equals)

def get_DSN(provider, host, user, pwd, db):
    """
    http://www.connectionstrings.com/sql-server-2005
    """
    DSN = u"""PROVIDER=%s;
        Data Source='%s';
        User ID='%s';
        Password='%s';
        Initial Catalog='%s';
        Integrated Security=SSPI""" % (provider, host, user, pwd, db)
    return DSN

def get_dbs(host, user, pwd, default_dbs, db=None):
    """
    Get dbs and the db to use.  Exclude master.
    NB need to use a separate connection here with db Initial Catalog
        undefined.        
    """
    DSN = get_DSN(provider=u"SQLOLEDB", host=host, user=user, pwd=pwd, db=u"")
    try:
        con = adodbapi.connect(DSN)
    except Exception:
        raise Exception(u"Unable to connect to MS SQL Server with host: "
                        u"%s; user: %s; and pwd: %s" % (host, user, pwd))
    cur = con.cursor() # must return tuples not dics
    cur.adoconn = con.adoConn # (need to access from just the cursor)
    try: # MS SQL Server 2000
        cur.execute(u"SELECT name FROM master.dbo.sysdatabases ORDER BY name")
    except Exception: # SQL Server 2005
        cur.execute(u"SELECT name FROM sys.databases ORDER BY name")
    # only want dbs with at least one table.
    all_dbs = [x[0] for x in cur.fetchall() if x[0] != u"master"]
    dbs = []
    for db4list in all_dbs:
        try:
            con, cur = get_con_cur_for_db(host, user, pwd, db4list)
        except Exception:
            continue
        if has_tbls(cur, db4list):
            dbs.append(db4list)
    if not dbs:
        raise Exception(_("Unable to find any databases that have tables "
                          "and you have permission to access."))
    dbs_lc = [x.lower() for x in dbs]
    # get db (default if possible otherwise first)
    # NB db must be accessible from connection
    if not db:
        # use default if possible, or fall back to first. NB may have no tables.
        default_db_mssql = default_dbs.get(mg.DBE_MS_SQL) # might be None
        try:
            db = dbs[0] # init
        except IndexError:
            raise Exception(_("No databases to choose from"))
        if default_db_mssql:
            if default_db_mssql.lower() in dbs_lc:
                db = default_db_mssql
    else:
        if db.lower() not in dbs_lc:
            raise Exception(u"Database \"%s\" not available " % db +
                            u"from supplied connection")
    cur.close()
    con.close()
    return dbs, db

def set_db_in_con_dets(con_dets, db):
    "Set database in connection details (if appropriate)"
    con_dets[u"db"] = db
    
def get_con_cur_for_db(host, user, pwd, db):
    DSN = get_DSN(provider=u"SQLOLEDB", host=host, user=user, pwd=pwd, db=db)
    try:
        con = adodbapi.connect(DSN)
    except Exception, e:
        raise Exception(u"Unable to connect to MS SQL Server with "
                        u"database %s; and supplied connection: " % db +
                        u"host: %s; user: %s; pwd: %s." % (host, user, pwd) +
                        u"\nCaused by error: %s" % lib.ue(e))
    cur = con.cursor()
    cur.adoconn = con.adoConn # (need to access from just the cursor) 
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
    If no db defined, use default if possible, or first with tables.
    Returns dict with con, cur, dbs, db.
    """
    con_dets_mssql = con_dets.get(mg.DBE_MS_SQL)
    if not con_dets_mssql:
        raise my_exceptions.MissingConDets(mg.DBE_MS_SQL)
    host = con_dets_mssql["host"] # plain string keywords only
    user = con_dets_mssql["user"]
    pwd = con_dets_mssql["passwd"]
    dbs, db = get_dbs(host, user, pwd, default_dbs, db)
    set_db_in_con_dets(con_dets_mssql, db)
    con, cur = get_con_cur_for_db(host, user, pwd, db)     
    con_resources = {mg.DBE_CON: con, mg.DBE_CUR: cur, mg.DBE_DBS: dbs,
                     mg.DBE_DB: db}
    return con_resources

def get_tbls(cur, db):
    """
    Get table names given database and cursor. NB not system tables.
    Cursor must be suitable for db.
    """
    cat = win32com.client.Dispatch(r'ADOX.Catalog')
    cat.ActiveConnection = cur.adoconn
    alltables = cat.Tables
    tbls = []
    for tab in alltables:
        if tab.Type == "TABLE":
            tbls.append(tab.Name)
    cat = None
    return tbls

def has_tbls(cur, db):
    "Any non-system tables?"
    cat = win32com.client.Dispatch(r'ADOX.Catalog')
    cat.ActiveConnection = cur.adoconn
    alltables = cat.Tables
    for tab in alltables:
        if tab.Type == "TABLE":
            return True
    return False
            
def get_flds(cur, db, tbl):
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
        fldname = rs.Fields(u"COLUMN_NAME").Value
        ord_pos = rs.Fields(u"ORDINAL_POSITION").Value
        char_set = rs.Fields(u"CHARACTER_SET_NAME").Value
        extras[fldname] = (ord_pos, char_set)
        rs.MoveNext()
    flds = {}
    for col in cat.Tables(tbl).Columns:
        # build dic of fields, each with dic of characteristics
        fldname = col.Name
        if debug: print(col.Type)
        fldtype = dbe_globals.get_ado_dict().get(col.Type)
        if not fldtype:
            raise Exception(u"Not an MS SQL Server ADO field type %d"
                            % col.Type)
        bolnumeric = fldtype in dbe_globals.NUMERIC_TYPES
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
        boldatetime = fldtype in dbe_globals.DATETIME_TYPES
        fld_txt = not bolnumeric and not boldatetime
        num_prec = col.Precision
        bolsigned = True if bolnumeric else None
        min_val, max_val = dbe_globals.get_min_max(fldtype, num_prec, 
                                                   dec_pts)
        dets_dic = {
                    mg.FLD_SEQ: extras[fldname][0],
                    mg.FLD_BOLNULLABLE: bolnullable,
                    mg.FLD_DATA_ENTRY_OK: boldata_entry_ok,
                    mg.FLD_COLUMN_DEFAULT: default,
                    mg.FLD_BOLTEXT: fld_txt,
                    mg.FLD_TEXT_LENGTH: col.DefinedSize,
                    mg.FLD_CHARSET: extras[fldname][1],
                    mg.FLD_BOLNUMERIC: bolnumeric,
                    mg.FLD_BOLAUTONUMBER: bolautonum,
                    mg.FLD_DECPTS: dec_pts,
                    mg.FLD_NUM_WIDTH: num_prec,
                    mg.FLD_BOL_NUM_SIGNED: bolsigned,
                    mg.FLD_NUM_MIN_VAL: min_val,
                    mg.FLD_NUM_MAX_VAL: max_val,
                    mg.FLD_BOLDATETIME: boldatetime, 
                    }
        flds[fldname] = dets_dic
    debug = False 
    if debug:
        pprint.pprint(flds)
    cat = None
    return flds

def get_index_dets(cur, db, tbl):
    """
    db -- needed by some dbes sharing interface.
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
        fldnames = [x.Name for x in index.Columns]
        idx_dic = {mg.IDX_NAME: index.Name, mg.IDX_IS_UNIQUE: index.Unique, 
                   mg.IDX_FLDS: fldnames}
        idxs.append(idx_dic)
    cat = None
    debug = False
    if debug:
        pprint.pprint(idxs)
        print(has_unique)
    return idxs, has_unique

def set_data_con_gui(parent, readonly, scroll, szr, lblfont):
    bx_mssql= wx.StaticBox(scroll, -1, u"Microsoft SQL Server")
    # default database
    parent.lbl_mssql_default_db = wx.StaticText(scroll, -1, 
                                                _("Default Database:"))
    parent.lbl_mssql_default_db.SetFont(lblfont)
    mssql_default_db = parent.mssql_default_db if parent.mssql_default_db \
        else u""
    parent.txt_mssql_default_db = wx.TextCtrl(scroll, -1, mssql_default_db, 
                                           size=(250,-1))
    parent.txt_mssql_default_db.Enable(not readonly)
    parent.txt_mssql_default_db.SetToolTipString(_("Default database"
                                                   " (optional)"))
    # default table
    parent.lbl_mssql_default_tbl = wx.StaticText(scroll, -1, 
                                                 _("Default Table:"))
    parent.lbl_mssql_default_tbl.SetFont(lblfont)
    mssql_default_tbl = parent.mssql_default_tbl if parent.mssql_default_tbl \
        else u""
    parent.txt_mssql_default_tbl = wx.TextCtrl(scroll, -1, mssql_default_tbl, 
                                               size=(250,-1))
    parent.txt_mssql_default_tbl.Enable(not readonly)
    parent.txt_mssql_default_tbl.SetToolTipString(_("Default table (optional)"))
    # host
    parent.lbl_mssql_host = wx.StaticText(scroll, -1, 
                                          _("Host - (local) if your machine:"))
    parent.lbl_mssql_host.SetFont(lblfont)
    mssql_host = parent.mssql_host
    parent.txt_mssql_host = wx.TextCtrl(scroll, -1, mssql_host, size=(100,-1))
    parent.txt_mssql_host.Enable(not readonly)
    # 1433 is the default port for MS SQL Server
    parent.txt_mssql_host.SetToolTipString(_("Host e.g. (local), or "
                                             "190.190.200.100,1433, or "
                                             "my-svr-01,1433"))
    # user
    parent.lbl_mssql_user = wx.StaticText(scroll, -1, _("User - e.g. root:"))
    parent.lbl_mssql_user.SetFont(lblfont)
    mssql_user = parent.mssql_user if parent.mssql_user else ""
    parent.txt_mssql_user = wx.TextCtrl(scroll, -1, mssql_user, size=(100,-1))
    parent.txt_mssql_user.Enable(not readonly)
    parent.txt_mssql_user.SetToolTipString(_("User e.g. root"))
    # password
    parent.lbl_mssql_pwd = wx.StaticText(scroll, -1, 
                                         _("Password - space if none:"))
    parent.lbl_mssql_pwd.SetFont(lblfont)
    mssql_pwd = parent.mssql_pwd if parent.mssql_pwd else ""
    parent.txt_mssql_pwd = wx.TextCtrl(scroll, -1, mssql_pwd, size=(100,-1),
                                       style=wx.TE_PASSWORD)
    parent.txt_mssql_pwd.Enable(not readonly)
    parent.txt_mssql_pwd.SetToolTipString(_("Password"))
    #2 MS SQL SERVER
    parent.szr_mssql = wx.StaticBoxSizer(bx_mssql, wx.VERTICAL)
    #3 MSSQL INNER
    #4 MSSQL INNER TOP
    szr_mssql_inner_top = wx.BoxSizer(wx.HORIZONTAL)
    # default database
    szr_mssql_inner_top.Add(parent.lbl_mssql_default_db, 0, 
                            wx.LEFT|wx.RIGHT, 5)
    szr_mssql_inner_top.Add(parent.txt_mssql_default_db, 0, 
                            wx.GROW|wx.RIGHT, 10)
    # default table
    szr_mssql_inner_top.Add(parent.lbl_mssql_default_tbl, 0, 
                            wx.LEFT|wx.RIGHT, 5)
    szr_mssql_inner_top.Add(parent.txt_mssql_default_tbl, 0, 
                            wx.GROW|wx.RIGHT, 10)
    #4 MSSQL INNER BOTTOM
    szr_mssql_inner_btm = wx.BoxSizer(wx.HORIZONTAL)
    # host 
    szr_mssql_inner_btm.Add(parent.lbl_mssql_host, 0, wx.LEFT|wx.RIGHT, 5)
    szr_mssql_inner_btm.Add(parent.txt_mssql_host, 0, wx.RIGHT, 10)
    # user
    szr_mssql_inner_btm.Add(parent.lbl_mssql_user, 0, wx.LEFT|wx.RIGHT, 5)
    szr_mssql_inner_btm.Add(parent.txt_mssql_user, 0, wx.RIGHT, 10)
    # password
    szr_mssql_inner_btm.Add(parent.lbl_mssql_pwd, 0, wx.LEFT|wx.RIGHT, 5)
    szr_mssql_inner_btm.Add(parent.txt_mssql_pwd, 1, wx.GROW|wx.RIGHT, 10)
    #2 combine
    parent.szr_mssql.Add(szr_mssql_inner_top, 0, wx.GROW|wx.ALL, 5)
    parent.szr_mssql.Add(szr_mssql_inner_btm, 0, wx.ALL, 5)
    szr.Add(parent.szr_mssql, 0, wx.GROW|wx.ALL, 10)

def get_proj_settings(parent, proj_dic):
    parent.mssql_default_db = proj_dic[mg.PROJ_DEFAULT_DBS].get(mg.DBE_MS_SQL)
    parent.mssql_default_tbl = proj_dic[mg.PROJ_DEFAULT_TBLS].get(mg.DBE_MS_SQL)
    # optional (although if any mssql, for eg, must have all)
    if proj_dic[mg.PROJ_CON_DETS].get(mg.DBE_MS_SQL):
        parent.mssql_host = proj_dic[mg.PROJ_CON_DETS][mg.DBE_MS_SQL]["host"]
        parent.mssql_user = proj_dic[mg.PROJ_CON_DETS][mg.DBE_MS_SQL]["user"]
        parent.mssql_pwd = proj_dic[mg.PROJ_CON_DETS][mg.DBE_MS_SQL]["passwd"]
    else:
        parent.mssql_host, parent.mssql_user, parent.mssql_pwd = "", "", ""

def set_con_det_defaults(parent):
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

def process_con_dets(parent, default_dbs, default_tbls, con_dets):
    """
    Copes with missing default database and table. Will get the first available.
    """
    mssql_default_db = parent.txt_mssql_default_db.GetValue()
    mssql_default_tbl = parent.txt_mssql_default_tbl.GetValue()
    mssql_host = parent.txt_mssql_host.GetValue()
    mssql_user = parent.txt_mssql_user.GetValue()
    mssql_pwd = parent.txt_mssql_pwd.GetValue()
    has_mssql_con = mssql_host and mssql_user and mssql_pwd
    dirty = (mssql_host or mssql_user or mssql_pwd or mssql_default_db 
             or mssql_default_tbl)
    incomplete_mssql = dirty and not has_mssql_con
    if incomplete_mssql:
        wx.MessageBox(_("The SQL Server details are incomplete"))
        parent.txt_mssql_default_db.SetFocus()
    default_dbs[mg.DBE_MS_SQL] = mssql_default_db \
        if mssql_default_db else None    
    default_tbls[mg.DBE_MS_SQL] = mssql_default_tbl \
        if mssql_default_tbl else None
    if mssql_host and mssql_user and mssql_pwd:
        con_dets_mssql = {"host": mssql_host, "user": mssql_user, 
                           "passwd": mssql_pwd}
        con_dets[mg.DBE_MS_SQL] = con_dets_mssql
    return incomplete_mssql, has_mssql_con
