import wx
import pprint

from sofastats import basic_lib as b
from sofastats import my_globals as mg
from sofastats import my_exceptions
from sofastats import lib
from sofastats import getdata
try:
    import psycopg2 as pg
except ImportError as e:
    raise Exception(
        'Not importing PostgreSQL driver. NB SOFA can only work with '
        ' PostgreSQL if its path e.g. "C:\\Program Files\\PostgreSQL\\'
        '10.4\\bin" is added to your Windows PATH variable. See '
        'http://geekswithblogs.net/renso/archive/2009/10/21/'
        'how-to-set-the-windows-path-in-windows-7.aspx'
        f'\nReason: {b.ue(e)}')

## http://www.postgresql.org/docs/8.4/static/datatype.html
BIGINT = 'bigint'  ## "signed eight-byte integer"
#BIGSERIAL = "autoincrementing eight-byte integer'  ## not a real type, only a
##  notational convenience 
## (see http://www.postgresql.org/docs/8.4/static/datatype-numeric.html)
BIT = 'bit'  ## "fixed-length bit string"
BITVARYING = 'bit varying'  ## "variable-length bit string"
BOOLEAN = 'boolean'  ## "logical Boolean (true/false)"
BOX = 'box'  ## "rectangular box on a plane"
BYTEA = 'bytea'  ## "binary data ('byte array')"
CHARVARYING = 'character varying'  ## "variable-length character string"
CHAR = 'character'  ## "fixed-length character string"
CIDR = 'cidr'  ## "IPv4 or IPv6 network address"
CIRCLE = 'circle'  ## "circle on a plane"
DATE = 'date'  ## "calendar date (year, month, day)"
DECIMAL = 'decimal'  ## The types decimal and numeric are equivalent. 
# Both types are part of the SQL standard. 
DOUBLE = 'double precision'  ## "double precision floating-point number (8 bytes)"
INET = 'inet'  ## "IPv4 or IPv6 host address"
INTEGER = 'integer'  ## "signed four-byte integer"
INTERVAL = 'interval'  ## "time span"
LINE = 'line'  ## "infinite line on a plane"
LSEG = 'lseg'  ## "line segment on a plane"
MACADDR = 'macaddr'  ## "MAC (Media Access Control) address"
MONEY = 'money'  ## "currency amount"
NUMERIC = 'numeric'  ## "exact numeric of selectable precision"
PATH = 'path'  ## "geometric path on a plane"
POINT = 'point'  ## "geometric point on a plane"
POLYGON = 'polygon'  ## "closed geometric path on a plane"
REAL = 'real'  ## "single precision floating-point number (4 bytes)"
SMALLINT = 'smallint'  ## "signed two-byte integer"
#SERIAL = "autoincrementing four-byte integer"
TEXT = 'text'  ## "variable-length character string"
TIME = 'time'  ## "time of day"
TIMESTAMP = 'timestamp'  ## "date and time"
TIMESTAMP_WITHOUT_TIMEZONE = 'timestamp without time zone'
TSQUERY = 'tsquery'  ## "text search query"
TSVECTOR = 'tsvector'  ## "text search document"
TXID_SNAPSHOT = 'txid_snapshot'  ## "user-level transaction ID snapshot"
UUID = 'uuid'  ## "universally unique identifier"
XML = 'xml'  ## "XML data"

if_clause = 'CASE WHEN %s THEN %s ELSE %s END'
placeholder = '%s'
left_obj_quote = '"'
right_obj_quote = '"'
gte_not_equals = '!='
cartesian_joiner = ' CROSS JOIN '

def quote_obj(raw_val):
    return f'{left_obj_quote}{raw_val}{right_obj_quote}'

def quote_val(raw_val):
    return lib.DbLib.quote_val(raw_val,
        sql_str_literal_quote="'", sql_esc_str_literal_quote="''")

def get_summable(clause):
    return f'CASE WHEN {clause} THEN 1 ELSE 0 END'

def get_first_sql(quoted_tblname, top_n, order_val=None):
    orderby = f'ORDER BY {quote_obj(order_val)}' if order_val else ''
    return f'SELECT * FROM {quoted_tblname} {orderby} LIMIT {top_n}'

def get_syntax_elements():
    return (if_clause, left_obj_quote, right_obj_quote, quote_obj, quote_val, 
            placeholder, get_summable, gte_not_equals, cartesian_joiner)

def get_dbs_list(con_dets, default_dbs):
    con_resources = get_con_resources(con_dets, default_dbs)
    con_resources[mg.DBE_CUR].close()
    con_resources[mg.DBE_CON].close()
    return con_resources[mg.DBE_DBS]

def get_con_resources(con_dets, default_dbs, db=None):
    """
    Get connection - with a database if possible, else without. If without,
    use connection to identify databases and select one.  Then remake connection
    with selected database and remake cursor.
    """
    debug = False
    con_dets_pgsql = con_dets.get(mg.DBE_PGSQL)
    if not con_dets_pgsql:
        raise my_exceptions.MissingConDets(mg.DBE_PGSQL)
    try:
        if db:
            con_dets_pgsql['database'] = db
        con = pg.connect(**con_dets_pgsql)
    except Exception as e:
        user = con_dets_pgsql.get('user')
        if user != 'postgres' and not db:
            msg = ('Unable to connect to PostgreSQL db. A default database '
                "is required unless the user is 'postgres'."
                f'\nCaused by error: {b.ue(e)}')
        else:
            msg = ('Unable to connect to PostgreSQL db.'
                f'\nCaused by error: {b.ue(e)}')
        raise Exception(msg)
    cur = con.cursor()  ## must return tuples not dics
    ## get database name
    SQL_get_db_names = 'SELECT datname FROM pg_database'
    cur.execute(SQL_get_db_names)
    ## only want dbs with at least one table.
    all_dbs = [x[0] for x in cur.fetchall()]
    dbs = []
    for db4list in all_dbs:
        con_dets_pgsql['database'] = db4list
        try:
            con = pg.connect(**con_dets_pgsql)
        except Exception:
            continue
        cur = con.cursor()
        if has_tbls(cur, db4list):
            dbs.append(db4list)
        cur.close()
        con.close()
    if not dbs:
        raise Exception(
            _('Unable to find any databases that have tables and you have '
            'permission to access.'))
    dbs_lc = [x.lower() for x in dbs]
    ## get db (default if possible otherwise first)
    ## NB db must be accessible from connection
    if not db:
        ## use default if possible, or fall back to first
        default_db_pgsql = default_dbs.get(mg.DBE_PGSQL) # might be None
        db = dbs[0]  ## init
        if default_db_pgsql:
            if default_db_pgsql.lower() in dbs_lc:
                db = default_db_pgsql
        ## need to reset con and cur
        cur.close()
        con.close()
        con_dets_pgsql['database'] = db
        con = pg.connect(**con_dets_pgsql)
        cur = con.cursor()
    else:
        if db.lower() not in dbs_lc:
            raise Exception(
                f'Database "{db}" not available from supplied connection')
        con_dets_pgsql['database'] = db
        con = pg.connect(**con_dets_pgsql)
        cur = con.cursor()
    if debug: pprint.pprint(con_dets)  
    con_resources = {mg.DBE_CON: con, mg.DBE_CUR: cur,
        mg.DBE_DBS: dbs, mg.DBE_DB: db}
    return con_resources

def get_tbls(cur, db):
    """
    Get table names given database and cursor.
    http://www.alberton.info/postgresql_meta_info.html
    """
    SQL_get_tblnames = """SELECT table_schema || '.' || table_name
        FROM information_schema.tables
        WHERE table_type IN('BASE TABLE', 'VIEW')
            AND table_schema NOT IN ('pg_catalog', 'information_schema')"""
    cur.execute(SQL_get_tblnames)
    tbls = [x[0] for x in cur.fetchall()] 
    tbls.sort(key=lambda s: s.upper())
    return tbls

def has_tbls(cur, db):
    "Any non-system tables?  Need to use cursor that matches db"
    SQL_get_tblnames = """SELECT table_schema || '.' || table_name
        FROM information_schema.tables
        WHERE table_type IN('BASE TABLE', 'VIEW')
            AND table_schema NOT IN ('pg_catalog', 'information_schema')"""
    cur.execute(SQL_get_tblnames)
    tbls = [x[0] for x in cur.fetchall()]
    if tbls:
        return True
    return False

def get_min_max(fldtype, num_prec, dec_pts, autonum):
    """
    Returns minimum and maximum allowable numeric values.

    num_prec -- precision e.g. 6 for 23.5141
    dec_pts -- scale e.g. 4 for 23.5141
    autonum -- i.e. serial or bigserial

    http://www.postgresql.org/docs/8.4/static/datatype-numeric.html

    We use the following terms below: The scale of a numeric is the count of
    decimal digits in the fractional part, to the right of the decimal point.
    The precision of a numeric is the total count of significant digits in the
    whole number, that is, the number of digits to both sides of the decimal
    point. So the number 23.5141 has a precision of 6 and a scale of 4. Integers
    can be considered to have a scale of zero.
    http://www.postgresql.org/docs/8.4/static/datatype-numeric.html

    NB even though a floating point type will not store values closer to zero
    than a certain level, such values will be accepted here. The database will
    store these as zero.

    TODO - confirm with PostgreSQL.
    """
    if fldtype == SMALLINT:
        min_val = -(2**15)
        max_val = (2**15)-1
    elif fldtype == INTEGER:
        min_val = 1 if autonum else -(2**31)
        max_val = (2**31)-1
    elif fldtype == BIGINT:
        min_val = 1 if autonum else -(2**63)
        max_val = (2**63)-1
    ## http://www.postgresql.org/docs/8.4/static/datatype-money.html
    elif fldtype == MONEY:
        min_val = -92233720368547758.08
        max_val = 92233720368547758.07
    elif fldtype == REAL:
        ## variable-precision, inexact. 6 decimal digits precision.
        min_val = -(2**128)
        max_val = (2**128)-1 # actually, rather a bit less, but this will do
    elif fldtype == DOUBLE:
        ## variable-precision, inexact. 15 decimal digits precision.
        min_val = -(2**1024)
        max_val = (2**1024)-1
    elif fldtype == NUMERIC: #alias of decimal
        ## variable-precision, inexact. 15 decimal digits precision.
        ## postgresql does not require num_prec or dec_pts to be defined
        num_prec = num_prec if num_prec is not None else 5
        dec_pts = dec_pts if dec_pts is not None else 2
        abs_max = 10**(num_prec - dec_pts)
        min_val = -abs_max
        max_val = abs_max
    else:
        min_val = None
        max_val = None
    return min_val, max_val

def get_flds(cur, db, tbl):
    """
    Returns details for set of fields given database, table, and cursor.
    http://archives.postgresql.org/pgsql-sql/2007-01/msg00082.php
    """
    debug = False
    schema, tblname = getdata.tblname2parts(mg.DBE_PGSQL, tbl)
    SQL_get_fld_dets = f"""SELECT columns.column_name
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
            lower(columns.data_type)
            IN (
                {quote_val(SMALLINT)},
                {quote_val(INTEGER)},
                {quote_val(BIGINT)},
                {quote_val(DECIMAL)},
                {quote_val(NUMERIC)},
                {quote_val(REAL)},
                {quote_val(DOUBLE)},
                {quote_val(MONEY)})
        AS bolnumeric,
            position('nextval' in columns.column_default) IS NOT NULL
        AS autonumber,
            columns.numeric_scale
        AS dec_pts,
            columns.numeric_precision
        AS num_precision,
            lower(columns.data_type) IN (
                {quote_val(TIMESTAMP)},
                {quote_val(TIMESTAMP_WITHOUT_TIMEZONE)},
                {quote_val(DATE)},
                {quote_val(TIME)},
                {quote_val(INTERVAL)})
        AS boldatetime,
            lower(columns.data_type) IN (
                {quote_val(TIMESTAMP)}, {quote_val(TIMESTAMP_WITHOUT_TIMEZONE)})
        AS timestamp
        FROM information_schema.columns
        WHERE columns.table_schema::text = {quote_val(schema)}
        AND columns.table_name = {quote_val(tblname)}
        ORDER BY columns.ordinal_position """
    cur.execute(SQL_get_fld_dets)
    fld_dets = cur.fetchall()
    if debug: pprint.pprint(fld_dets)
    ## build dic of fields, each with dic of characteristics
    flds = {}
    for (fldname, ord_pos, nullable, fld_default, fldtype, max_len,
             charset, numeric, autonum, dec_pts, num_prec, boldatetime,
             timestamp) in fld_dets:
        bolnullable = (nullable == 'YES')
        boldata_entry_ok = not (autonum or timestamp)
        bolnumeric = numeric
        fld_txt = not bolnumeric and not boldatetime
        min_val, max_val = get_min_max(fldtype, num_prec, dec_pts, autonum)
        ## http://www.postgresql.org/docs/current/static/datatype-numeric.html
        ## even autonum could start from a negative i.e. signed value
        bolsigned = bolnumeric
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
        flds[fldname] = dets_dic
    return flds

def get_index_dets(cur, db, tbl):
    """
    db -- needed by some dbes sharing interface.
    has_unique - boolean
    idxs = [idx0, idx1, ...]
    each idx is a dict name, is_unique, flds
    http://www.alberton.info/postgresql_meta_info.html
    """
    debug = False
    schema, tblname = getdata.tblname2parts(mg.DBE_PGSQL, tbl)
    SQL_get_main_index_dets = f"""SELECT relname, indkey, indisunique
        FROM pg_class, pg_index
        WHERE pg_class.oid = pg_index.indexrelid
        AND pg_class.oid IN (
        SELECT indexrelid
        FROM pg_index 
        INNER JOIN pg_class
        ON pg_class.oid=pg_index.indrelid
        INNER JOIN pg_namespace n
        ON pg_class.relnamespace = n.oid
        WHERE n.nspname = {quote_val(schema)}
        AND pg_class.relname={quote_val(tblname)})"""
    if debug: print(SQL_get_main_index_dets)
    cur.execute(SQL_get_main_index_dets)
    main_index_dets = cur.fetchall()
    idxs = []
    has_unique = False
    for idxname, indkey, unique_index in main_index_dets:
        fldnames = []
        if unique_index:
            has_unique = True
        ## get field names
        fld_oids = indkey.replace(' ', ', ')
        SQL_get_idx_flds = f"""SELECT t.relname, a.attname
           FROM pg_index c
           LEFT JOIN pg_class t
           ON c.indrelid  = t.oid
           INNER JOIN pg_namespace n
           ON t.relnamespace = n.oid
           LEFT JOIN pg_attribute a
           ON a.attrelid = t.oid
           AND a.attnum = ANY(indkey)
           WHERE n.nspname = {quote_val(schema)}
           AND t.relname = {quote_val(tblname)}
           AND a.attnum IN({fld_oids}) """
        cur.execute(SQL_get_idx_flds)
        fldnames = [x[1] for x in cur.fetchall()]
        idx_dic = {mg.IDX_NAME: idxname, mg.IDX_IS_UNIQUE: unique_index, 
            mg.IDX_FLDS: fldnames}
        idxs.append(idx_dic)
    debug = False
    if debug:
        pprint.pprint(idxs)
        print(has_unique)
    return idxs, has_unique

def set_data_con_gui(parent, scroll, szr, lblfont, *, read_only=False):
    bx_pgsql= wx.StaticBox(scroll, -1, 'PostgreSQL')
    ## default database
    parent.lbl_pgsql_default_db = wx.StaticText(
        scroll, -1, _('Default Database:'))
    parent.lbl_pgsql_default_db.SetFont(lblfont)
    pgsql_default_db = (
        parent.pgsql_default_db if parent.pgsql_default_db else '')
    parent.txt_pgsql_default_db = wx.TextCtrl(
        scroll, -1, pgsql_default_db, size=(250, -1))
    parent.txt_pgsql_default_db.Enable(not read_only)
    parent.txt_pgsql_default_db.SetToolTip(
        _('Default database (optional if user is postgres)'))
    ## default table
    parent.lbl_pgsql_default_tbl = wx.StaticText(
        scroll, -1, _('Default Table (schema.table):'))
    parent.lbl_pgsql_default_tbl.SetFont(lblfont)
    pgsql_default_tbl = (
        parent.pgsql_default_tbl if parent.pgsql_default_tbl else '')
    parent.txt_pgsql_default_tbl = wx.TextCtrl(
        scroll, -1, pgsql_default_tbl, size=(250, -1))
    parent.txt_pgsql_default_tbl.Enable(not read_only)
    parent.txt_pgsql_default_tbl.SetToolTip(
        _('Default table (optional). Schema optional if public'))
    ## host
    parent.lbl_pgsql_host = wx.StaticText(scroll, -1, _('Host:'))
    parent.lbl_pgsql_host.SetFont(lblfont)
    pgsql_host = parent.pgsql_host if parent.pgsql_host else ''
    parent.txt_pgsql_host = wx.TextCtrl(scroll, -1, pgsql_host, size=(100,-1))
    parent.txt_pgsql_host.Enable(not read_only)
    parent.txt_pgsql_host.SetToolTip(_('Host e.g. localhost, or remote:3307'))
    ## 5432 is the default port for PostgreSQL
    ## user
    parent.lbl_pgsql_user = wx.StaticText(scroll, -1, _('User:'))
    parent.lbl_pgsql_user.SetFont(lblfont)
    pgsql_user = parent.pgsql_user if parent.pgsql_user else ''
    parent.txt_pgsql_user = wx.TextCtrl(scroll, -1, pgsql_user, size=(100, -1))
    parent.txt_pgsql_user.Enable(not read_only)
    parent.txt_pgsql_user.SetToolTip(_('User e.g. postgres'))
    ## password
    parent.lbl_pgsql_pwd = wx.StaticText(scroll, -1, _('Password:'))
    parent.lbl_pgsql_pwd.SetFont(lblfont)
    pgsql_pwd = parent.pgsql_pwd if parent.pgsql_pwd else ''
    parent.txt_pgsql_pwd = wx.TextCtrl(
        scroll, -1, pgsql_pwd, size=(300, -1), style=wx.TE_PASSWORD)
    parent.txt_pgsql_pwd.Enable(not read_only)
    parent.txt_pgsql_pwd.SetToolTip(_('Password'))
    ## 2 pgsql
    parent.szr_pgsql = wx.StaticBoxSizer(bx_pgsql, wx.VERTICAL)
    ## 3 pgsql INNER
    ## 4 pgsql INNER TOP
    szr_pgsql_inner_top = wx.BoxSizer(wx.HORIZONTAL)
    ## default database
    szr_pgsql_inner_top.Add(
        parent.lbl_pgsql_default_db, 0, wx.LEFT|wx.RIGHT, 5)
    szr_pgsql_inner_top.Add(
        parent.txt_pgsql_default_db, 0, wx.GROW|wx.RIGHT, 10)
    ## default table
    szr_pgsql_inner_top.Add(
        parent.lbl_pgsql_default_tbl, 0, wx.LEFT|wx.RIGHT, 5)
    szr_pgsql_inner_top.Add(
        parent.txt_pgsql_default_tbl, 0, wx.GROW|wx.RIGHT, 10)
    ## 4 pgsql INNER BOTTOM
    szr_pgsql_inner_btm = wx.BoxSizer(wx.HORIZONTAL)
    ## host
    szr_pgsql_inner_btm.Add(parent.lbl_pgsql_host, 0, wx.LEFT|wx.RIGHT, 5)
    szr_pgsql_inner_btm.Add(parent.txt_pgsql_host, 0, wx.RIGHT, 10)
    ## user
    szr_pgsql_inner_btm.Add(parent.lbl_pgsql_user, 0, wx.LEFT|wx.RIGHT, 5)
    szr_pgsql_inner_btm.Add(parent.txt_pgsql_user, 0, wx.RIGHT, 10)
    ## password
    szr_pgsql_inner_btm.Add(parent.lbl_pgsql_pwd, 0, wx.LEFT|wx.RIGHT, 5)
    szr_pgsql_inner_btm.Add(parent.txt_pgsql_pwd, 1, wx.GROW|wx.RIGHT, 10)
    #2 combine
    parent.szr_pgsql.Add(szr_pgsql_inner_top, 0, wx.GROW|wx.ALL, 5)
    parent.szr_pgsql.Add(szr_pgsql_inner_btm, 0, wx.ALL, 5)
    szr.Add(parent.szr_pgsql, 0, wx.GROW|wx.ALL, 10)

def get_proj_settings(parent, proj_dic):
    parent.pgsql_default_db = proj_dic[mg.PROJ_DEFAULT_DBS].get(mg.DBE_PGSQL)
    parent.pgsql_default_tbl = proj_dic[mg.PROJ_DEFAULT_TBLS].get(mg.DBE_PGSQL)
    ## optional (although if any pgsql, for eg, must have all)
    if proj_dic[mg.PROJ_CON_DETS].get(mg.DBE_PGSQL):
        pgsql_dic = proj_dic[mg.PROJ_CON_DETS][mg.DBE_PGSQL]
        parent.pgsql_host = pgsql_dic['host']
        try:
            parent.pgsql_host = parent.pgsql_host + ':' + pgsql_dic['port']
        except KeyError:
            pass
        parent.pgsql_user = pgsql_dic['user']
        parent.pgsql_pwd = pgsql_dic['password']
    else:
        parent.pgsql_host, parent.pgsql_user, parent.pgsql_pwd = '', '', ''

def set_con_det_defaults(parent):
    try:
        parent.pgsql_default_db
    except AttributeError:
        parent.pgsql_default_db = ''
    try:
        parent.pgsql_default_tbl
    except AttributeError: 
        parent.pgsql_default_tbl = ''
    try:
        parent.pgsql_host
    except AttributeError: 
        parent.pgsql_host = ''
    try:
        parent.pgsql_user
    except AttributeError: 
        parent.pgsql_user = ''
    try:            
        parent.pgsql_pwd
    except AttributeError: 
        parent.pgsql_pwd = ''

def process_con_dets(parent, default_dbs, default_tbls, con_dets):
    """
    Copes with missing default database and table. Will get the first available.
    Must have a default db if user not 'postgres'.
    """
    default_db = parent.txt_pgsql_default_db.GetValue()
    pgsql_default_db = default_db if default_db else None
    default_tbl = parent.txt_pgsql_default_tbl.GetValue()
    lacks_schema = '.' not in default_tbl
    if lacks_schema:
        default_tbl = f'public.{default_tbl}'
    pgsql_default_tbl = default_tbl if default_tbl else None    
    pgsql_host = parent.txt_pgsql_host.GetValue()
    pgsql_user = parent.txt_pgsql_user.GetValue()
    pgsql_pwd = parent.txt_pgsql_pwd.GetValue()
    has_pgsql_con = pgsql_host and pgsql_user  ## allow blank password
    missing_db = pgsql_user != 'postgres' and not pgsql_default_db
    dirty = (
        pgsql_host or pgsql_user or pgsql_pwd
        or pgsql_default_db or pgsql_default_tbl)
    incomplete_pgsql = dirty and (not has_pgsql_con or missing_db)
    if incomplete_pgsql:
        msg = _('The PostgreSQL details are incomplete.')
        if missing_db:
            msg += _(
                " A default database is required unless the user is 'postgres'")
        wx.MessageBox(msg)
        parent.txt_pgsql_default_db.SetFocus()
    default_dbs[mg.DBE_PGSQL] = (
        pgsql_default_db if pgsql_default_db else None)    
    default_tbls[mg.DBE_PGSQL] = (
        pgsql_default_tbl if pgsql_default_tbl else None)
    if has_pgsql_con:
        con_dets_pgsql = {'user': pgsql_user, 'password': pgsql_pwd}
        host_bits = pgsql_host.split(':')
        if 1 <= len(host_bits) <= 2:
            host = host_bits[0].strip()
            con_dets_pgsql['host'] = host
            if len(host_bits) == 2:
                port = host_bits[1].strip()
                con_dets_pgsql['port'] = port
        else:
            raise Exception("Not expected number of parts split by ':'")
        con_dets[mg.DBE_PGSQL] = con_dets_pgsql
    return incomplete_pgsql, has_pgsql_con
