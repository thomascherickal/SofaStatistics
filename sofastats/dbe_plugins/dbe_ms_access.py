# Must run makepy once - 
# see http://www.thescripts.com/forum/thread482449.html e.g. the following 
# way - run PYTHON\Lib\site-packages\pythonwin\pythonwin.exe (replace PYTHON 
# with folder python is in).  Tools>COM Makepy utility - select appropriate 
# library - e.g. for ADO it would be Microsoft ActiveX Data Objects 2.8 Library 
# (2.8) - and select OK. NB DAO must be done separately from ADO etc.

from __future__ import print_function
import adodbapi #@UnresolvedImport
import pprint
import win32com.client #@UnresolvedImport
import wx

from sofastats import basic_lib as b
from sofastats import my_globals as mg
from sofastats import lib
from sofastats import my_exceptions
from dbe_plugins import dbe_globals
from sofastats import settings_grid

AD_OPEN_KEYSET = 1
AD_LOCK_OPTIMISTIC = 3
AD_SCHEMA_COLUMNS = 4

MSACCESS_DEFAULT_DB = "msaccess_default_db"
MSACCESS_DEFAULT_TBL = "msaccess_default_tbl"

if_clause = u"IIF(%s, %s, %s)"
placeholder = u"?"
left_obj_quote = u"["
right_obj_quote = u"]"
cartesian_joiner = u", "

# http://ask.metafilter.com/38350/ ...
# ... How-does-not-equal-translate-into-Access-Language
gte_not_equals = u"<>" # all the others accept both

def quote_obj(raw_val):
    return u"%s%s%s" % (left_obj_quote, raw_val, right_obj_quote)

def quote_val(raw_val, charset2try="iso-8859-1"):
    return lib.DbLib.quote_val(raw_val, sql_str_literal_quote=u"'", 
        sql_esc_str_literal_quote=u"''", pystr_use_double_quotes=True,
        charset2try=charset2try)

def get_summable(clause):
    return u"ABS(%s)" % clause # true is -1 so we need to get sum of +1s

def get_first_sql(quoted_tblname, top_n, order_val=None):
    orderby = u"ORDER BY %s" % quote_obj(order_val) if order_val else u""
    return u"SELECT TOP %(top_n)s * FROM %(tblname)s %(orderby)s" % \
        {"top_n": top_n, "tblname": quoted_tblname, "orderby": orderby}

def get_syntax_elements():
    return (if_clause, left_obj_quote, right_obj_quote, quote_obj, quote_val, 
            placeholder, get_summable, gte_not_equals, cartesian_joiner)

def get_dbs_list(con_dets, default_dbs):
    """
    Get list of all databases for this dbe (as per con dets in proj file).
    NB con_resources will only have one db listed (this dbe has one db per 
        connection).
    """
    con_dets_access = con_dets.get(mg.DBE_MS_ACCESS)
    if not con_dets_access:
        raise my_exceptions.MissingConDets(mg.DBE_MS_ACCESS)
    return con_dets_access.keys()

def get_con_resources(con_dets, default_dbs, db=None):
    """
    When opening from scratch, e.g. clicking on Report Tables from Start,
        no db, so must identify one, but when selecting dbe-db in dropdowns, 
        there will be a db.
    Returns dict with con, cur, dbs, db.
    """
    con_dets_access = con_dets.get(mg.DBE_MS_ACCESS)
    if not con_dets_access:
        raise my_exceptions.MissingConDets(mg.DBE_MS_ACCESS)
    # get the (only) database and use it to get the connection details
    if not db:
        # use default if possible, or fall back to first
        default_db_access = default_dbs.get(mg.DBE_MS_ACCESS) # might be None
        if default_db_access:
            db = default_db_access
        else:
            db = con_dets_access.keys()[0]
    if not con_dets_access.get(db):
        raise Exception(u"No connections for MS Access database %s" % db)
    con_dets_access_db = con_dets_access[db]
    """
    DSN syntax - http://support.microsoft.com/kb/193332 and 
    http://www.codeproject.com/database/connectionstrings.asp ...
        ... ?df=100&forumid=3917&exp=0&select=1598401"""
    # Connection keywords e.g. pwd, must be plain strings not unicode strings.
    database = con_dets_access_db["database"]
    user = con_dets_access_db["user"]
    pwd = con_dets_access_db["pwd"]
    mdw = con_dets_access_db["mdw"]
    DSN = (u"PROVIDER=Microsoft.Jet.OLEDB.4.0;DATA SOURCE=%(db)s;"
           u"USER ID=%(usr)s;PASSWORD=%(pwd)s;"
           u"Jet OLEDB:System Database=%(mdw)s;" % {"db": database, "usr": user, 
                                                    "pwd": pwd, "mdw": mdw})
    try:
        con = adodbapi.connect(DSN)
    except Exception, e:
        raise Exception(u"Unable to connect to MS Access database using "
            u"supplied database: %s, user: %s, " % (database, user) + 
            u"pwd: %s, or mdw: %s.\nCaused by error: %s" % (pwd, mdw, b.ue(e)))
    cur = con.cursor() # must return tuples not dics
    cur.adoconn = con.adoConn # (need to access from just the cursor)
    if not has_tbls(cur, db):
        raise Exception(_("Selected database \"%s\" didn't have any tables.") %
                        db)
    con_resources = {mg.DBE_CON: con, mg.DBE_CUR: cur, mg.DBE_DBS: [db,],
                     mg.DBE_DB: db}
    return con_resources

def get_tbls(cur, db):
    "Get table names given database and cursor. NB not system tables"
    cat = win32com.client.Dispatch(r'ADOX.Catalog')
    cat.ActiveConnection = cur.adoconn
    alltables = cat.Tables
    tbls = []
    for tab in alltables:
        if tab.Type == u"TABLE":
            tbls.append(tab.Name)
    cat = None
    return tbls

def has_tbls(cur, db):
    "Any non-system tables?"
    cat = win32com.client.Dispatch(r'ADOX.Catalog')
    cat.ActiveConnection = cur.adoconn
    alltables = cat.Tables
    for tab in alltables:
        if tab.Type == u"TABLE":
            return True
    return False

def fld_unique(fldname, idxs):
    for idx in idxs:
        if idx[mg.IDX_IS_UNIQUE]:
            if fldname in idx[mg.IDX_FLDS]:
                return True
    return False

def get_flds(cur, db, tbl):
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
        fldname = rs.Fields(u"COLUMN_NAME").Value
        ord_pos = rs.Fields(u"ORDINAL_POSITION").Value
        char_set = rs.Fields(u"CHARACTER_SET_NAME").Value
        extras[fldname] = (ord_pos, char_set)
        rs.MoveNext()
    flds = {}
    idxs, has_unique = get_index_dets(cur, db, tbl)
    for col in cat.Tables(tbl).Columns:
        # build dic of fields, each with dic of characteristics
        fldname = col.Name            
        fldtype = dbe_globals.get_ado_dict().get(col.Type)
        if not fldtype:
            raise Exception(u"Not an MS Access ADO field type %d" % col.Type)
        bolautonum = col.Properties(u"AutoIncrement").Value
        boldata_entry_ok = not bolautonum
        # nullable if it says so (unless it is uniquely indexed yet lacks an
        # autonumber)
        bolnullable = col.Properties(u"Nullable").Value
        if has_unique:
            if fld_unique(fldname, idxs) and not bolautonum:
                bolnullable = False
        bolnumeric = fldtype in dbe_globals.NUMERIC_TYPES
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
                    mg.FLD_COLUMN_DEFAULT: col.Properties(u"Default").Value,
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
    bx_msaccess= wx.StaticBox(scroll, -1, "MS Access")
    # default database
    parent.lbl_msaccess_default_db = wx.StaticText(scroll, -1, 
            _("Default Database - name only e.g. demo.mdb:"))
    parent.lbl_msaccess_default_db.SetFont(lblfont)
    MSACCESS_DEFAULT_DB = parent.msaccess_default_db \
        if parent.msaccess_default_db else ""
    parent.txt_msaccess_default_db = wx.TextCtrl(scroll, -1, 
                                                 MSACCESS_DEFAULT_DB, 
                                                 size=(250,-1))
    parent.txt_msaccess_default_db.Enable(not readonly)
    parent.txt_msaccess_default_db.SetToolTipString(_("Default database"
                                                      " (optional)"))
    # default table
    parent.lbl_msaccess_default_tbl = wx.StaticText(scroll, -1, 
                                                 _("Default Table:"))
    parent.lbl_msaccess_default_tbl.SetFont(lblfont)
    MSACCESS_DEFAULT_TBL = parent.msaccess_default_tbl \
        if parent.msaccess_default_tbl else ""
    parent.txt_msaccess_default_tbl = wx.TextCtrl(scroll, -1, 
                                                  MSACCESS_DEFAULT_TBL, 
                                                  size=(250,-1))
    parent.txt_msaccess_default_tbl.Enable(not readonly)
    parent.txt_msaccess_default_tbl.SetToolTipString(_("Default table"
                                                       " (optional)"))
    parent.szr_msaccess = wx.StaticBoxSizer(bx_msaccess, wx.VERTICAL)
    #3 MS ACCESS INNER
    szr_msaccess_inner = wx.BoxSizer(wx.HORIZONTAL)
    szr_msaccess_inner.Add(parent.lbl_msaccess_default_db, 0, 
                           wx.LEFT|wx.RIGHT, 5)
    szr_msaccess_inner.Add(parent.txt_msaccess_default_db, 1, 
                           wx.GROW|wx.RIGHT, 10)
    szr_msaccess_inner.Add(parent.lbl_msaccess_default_tbl, 0, 
                           wx.LEFT|wx.RIGHT, 5)
    szr_msaccess_inner.Add(parent.txt_msaccess_default_tbl, 1, 
                           wx.GROW|wx.RIGHT, 10)
    parent.szr_msaccess.Add(szr_msaccess_inner, 0)
    col_det_db = {"col_label": _("Database(s)"), 
                  "coltype": settings_grid.COL_TEXT_BROWSE, 
                  "colwidth": 250, 
                  "file_phrase": _("Choose an MS Access database file"), 
                  "file_wildcard": _("MS Access databases") + u" (*.mdb)|*.mdb",
                  "empty_ok": False}
    col_det_sec = {"col_label": _("Security File") + u" (*.mdw) (opt)", 
                  "coltype": settings_grid.COL_TEXT_BROWSE, 
                  "colwidth": 250, 
                  "file_phrase": _("Choose an MS Access security file"), 
                  "file_wildcard": _("MS Access security files") + \
                        u" (*.mdw)|*.mdw",
                  "empty_ok": True}
    col_det_usr = {"col_label": _("User Name (opt)"), 
                  "coltype": settings_grid.COL_STR, 
                  "colwidth": 130, 
                  "file_phrase": None, 
                  "file_wildcard": None,
                  "empty_ok": True}
    col_det_pwd = {"col_label": _("Password (opt)"), 
                  "coltype": settings_grid.COL_PWD, 
                  "colwidth": 130, 
                  "file_phrase": None, 
                  "file_wildcard": None,
                  "empty_ok": True}
    msaccess_col_dets = [col_det_db, col_det_sec, col_det_usr, col_det_pwd]
    parent.msaccess_settings_data = []
    init_settings_data = parent.msaccess_data[:]
    init_settings_data.sort(key=lambda s: s[0])
    parent.msaccess_grid = settings_grid.SettingsEntry(frame=parent, 
                          panel=scroll, readonly=readonly, grid_size=(900, 100), 
                          col_dets=msaccess_col_dets, 
                          init_settings_data=init_settings_data, 
                          settings_data=parent.msaccess_settings_data, 
                          force_focus=True)
    parent.szr_msaccess.Add(parent.msaccess_grid.grid, 1, wx.GROW|wx.ALL, 5)
    szr.Add(parent.szr_msaccess, 0, wx.GROW|wx.ALL, 10)

def get_proj_settings(parent, proj_dic):
    parent.msaccess_default_db = \
        proj_dic[mg.PROJ_DEFAULT_DBS].get(mg.DBE_MS_ACCESS)
    parent.msaccess_default_tbl = \
                            proj_dic[mg.PROJ_DEFAULT_TBLS].get(mg.DBE_MS_ACCESS)
    if proj_dic[mg.PROJ_CON_DETS].get(mg.DBE_MS_ACCESS):
        parent.msaccess_data = [(x["database"], x["mdw"], x["user"], x["pwd"]) \
            for x in proj_dic[mg.PROJ_CON_DETS][mg.DBE_MS_ACCESS].values()]
    else:
        parent.msaccess_data = []

def set_con_det_defaults(parent):
    try:
        parent.msaccess_default_db
    except AttributeError:
        parent.msaccess_default_db = u""
    try:
        parent.msaccess_default_tbl
    except AttributeError:
        parent.msaccess_default_tbl = u""
    try:
        parent.msaccess_data
    except AttributeError:
        parent.msaccess_data = []

def process_con_dets(parent, default_dbs, default_tbls, con_dets):
    """
    Copes with missing default database and table. Will get the first available.
    Namespace multiple databases with same name (presumably in different 
        folders).
    """
    if parent.msaccess_grid.new_is_dirty:
        incomplete_msaccess = True
        has_msaccess_con = False
        wx.MessageBox(_(u"The MS Access details on the new row "
                        u"have not been saved. "
                        u"Select the final field in the new row "
                        u"and press Enter"))
        parent.msaccess_grid.SetFocus()
        return incomplete_msaccess, has_msaccess_con
    parent.msaccess_grid.update_settings_data()
    #pprint.pprint(parent.msaccess_settings_data) # debug
    msaccess_settings = parent.msaccess_settings_data
    if msaccess_settings:
        con_dets_msaccess = {}
        db_names = []
        for msaccess_setting in msaccess_settings:
            db_path = msaccess_setting[0]
            db_name = lib.get_file_name(db_path) # might not be unique
            db_name_key = lib.DbLib.get_unique_db_name_key(db_names, db_name)
            new_msaccess_dic = {}
            new_msaccess_dic[u"database"] = db_path
            new_msaccess_dic[u"mdw"] = msaccess_setting[1]
            new_msaccess_dic[u"user"] = msaccess_setting[2]
            new_msaccess_dic[u"pwd"] = msaccess_setting[3]
            con_dets_msaccess[db_name_key] = new_msaccess_dic
        con_dets[mg.DBE_MS_ACCESS] = con_dets_msaccess
    MSACCESS_DEFAULT_DB = parent.txt_msaccess_default_db.GetValue()
    MSACCESS_DEFAULT_TBL = parent.txt_msaccess_default_tbl.GetValue()
    try:
        has_msaccess_con = con_dets[mg.DBE_MS_ACCESS]
    except KeyError:
        has_msaccess_con = False
    incomplete_msaccess = (MSACCESS_DEFAULT_DB or MSACCESS_DEFAULT_TBL) \
        and not has_msaccess_con
    if incomplete_msaccess:
        wx.MessageBox(_("The MS Access details are incomplete"))
        parent.txt_msaccess_default_db.SetFocus()
    else:
        default_dbs[mg.DBE_MS_ACCESS] = MSACCESS_DEFAULT_DB \
            if MSACCESS_DEFAULT_DB else None            
        default_tbls[mg.DBE_MS_ACCESS] = MSACCESS_DEFAULT_TBL \
            if MSACCESS_DEFAULT_TBL else None
    return incomplete_msaccess, has_msaccess_con
