## should be imported before any modules which rely on mg.DATADETS_OBJ as dd object
from collections import namedtuple
import pprint
import sys
import wx

from sofastats import basic_lib as b
from sofastats import my_globals as mg
from sofastats import my_exceptions
from sofastats import config_globals
from sofastats import lib
from sofastats.dbe_plugins import dbe_sqlite

debug = False

ReadonlyDets = namedtuple('ReadonlyDets', 'readonly, enabled')

## data resources

"""
Assumed that table names will be case insensitive e.g. tblitems == tblItems.
"""

def get_dbe_resources(dbe, con_dets,
        default_dbs, default_tbls, db=None, tbl=None, *,
        add_checks=False, stop=False):
    """
    If a db and tbl are provided, fail if not able to connect to that table in
    that database. If table missing, try to connect to default or first table in
    database as appropriate. If database missing, try to connect to first
    database with tables. Try to connect if at all possible to meet
    specifications.

    :param list default_dbs: list of strings - one per dbe (might be None for
     this dbe)
    :param str db: may be changing dbe and db together (e.g. dbe-db dropdown).
    :param bool add_checks: only used by SQLite dbe.
    """
    debug = False
    try:
        dbe_resources = {}
        if debug: print("About to update dbe resources with con resources")
        kwargs = {
            mg.PROJ_CON_DETS: con_dets,
            mg.PROJ_DEFAULT_DBS: default_dbs,
            'db': db}
        if dbe == mg.DBE_SQLITE:
            kwargs['add_checks'] = add_checks
        if debug: print(kwargs)
        try:
            dbe_resources.update(mg.DBE_MODULES[dbe].get_con_resources(**kwargs))
        except KeyError:
            raise Exception(
                f"Unable to find {dbe} in DBE_MODULES ({mg.DBE_MODULES})")
        cur = dbe_resources[mg.DBE_CUR]
        #dbs = dbe_resources[mg.DBE_DBS]
        db = dbe_resources[mg.DBE_DB]  ## Try this first.
        
            ## If this database has no tables, try others and reset db.
        if debug: print("About to update dbe resources with db resources")
        db_resources = get_db_resources(dbe, cur, db, default_tbls, tbl)
        dbe_resources.update(db_resources)
        if debug: print("Finished updating dbe resources with db resources")
    except my_exceptions.MalformedDb:
        if stop:
            raise
        else:  ## try once but with add_checks set to True.  Might work :-)
            dbe_resources = get_dbe_resources(dbe, con_dets, default_dbs,
                default_tbls, db, tbl, add_checks=True, stop=True)
            mg.MUST_DEL_TMP = True
    except Exception as e:
        raise Exception(f"Unable to get dbe_resources. Orig error: {e}")
    return dbe_resources

def get_db_resources(dbe, cur, db, default_tbls, tbl):
    debug = False
    tbls = mg.DBE_MODULES[dbe].get_tbls(cur, db)
    if not tbls:
        raise Exception("No Tables")
    if debug: print("About to get tbl")
    if tbl:
        if tbl not in tbls:
            raise Exception(f'Table "{tbl}" not found in tables list')
    else:
        tbl = get_tbl(dbe, db, tbls, default_tbls)
    db_resources = {mg.DBE_TBLS: tbls, mg.DBE_TBL: tbl}
    if debug: print("About to update db_resources with tbl dets")
    db_resources.update(get_tbl_dets(dbe, cur, db, tbl))
    if debug: print("Finished updating db_resources with tbl dets")
    return db_resources

def get_tbl_dets(dbe, cur, db, tbl):
    flds = mg.DBE_MODULES[dbe].get_flds(cur, db, tbl)
    idxs, has_unique = mg.DBE_MODULES[dbe].get_index_dets(cur, db, tbl)
    tbl_dets = {mg.DBE_FLDS: flds, mg.DBE_IDXS: idxs, 
        mg.DBE_HAS_UNIQUE: has_unique}
    return tbl_dets

def get_tbl(dbe, db, tbls, default_tbls):
    """
    Get table name (default if possible otherwise first).
    """
    tbls_lc = [x.lower() for x in tbls]
    default_tbl = default_tbls.get(dbe)
    if default_tbl and default_tbl.lower() in tbls_lc:
        tbl = default_tbl
    else:
        try:
            tbl = tbls[0]
        except IndexError:
            raise Exception(f'No tables found in database "{db}"')
    return tbl

def tblname_qtr(dbe, tblname):
    """
    If any dots in table name, use first dot as split between schema and table
    name.
    """
    objqtr = get_obj_quoter_func(dbe)
    name_parts = tblname.split('.', 1)  ## only want one split if any
    sql = '.'.join([objqtr(x) for x in name_parts])
    return sql

def tblname2parts(dbe, tblname):
    name_parts = tblname.split('.', 1)  ## only want one split if any
    if len(name_parts) != 2:
        raise Exception("Expected schema and table name.")
    return name_parts[0], name_parts[1]


class DataDets:
    """
    A single place to get the current data state and to alter it in a safe way.

    Includes connection and cursor objects ready to use and based on the
    current database.

    Safe means that no steps will be missed and nothing will be left in an
    inconsistent state.

    proj_dic -- dict including proj notes etc plus default dbe, default dbs,
    default tbls, and con_dets.
    """

    def __init__(self, proj_dic):
        debug = False
        self.set_proj_dic(proj_dic)
        if debug: print("Finished setting proj dic")

    def set_proj_dic(self, proj_dic, dic2restore=None):
        """
        Setting project can have implications for default dbe, default dbs,
        default tbls, dbs, db etc.

        dic2restore --  if it turns to custard, what proj to restore to
        (presumably a previously working one).
        """
        try:
            ## next 3 are dicts with dbes as key (if present)
            con_dets = proj_dic[mg.PROJ_CON_DETS]
            default_dbs = proj_dic[mg.PROJ_DEFAULT_DBS]
            default_tbls = proj_dic[mg.PROJ_DEFAULT_TBLS]
            dbe = proj_dic[mg.PROJ_DBE]
            db = default_dbs.get(dbe)
            tbl = default_tbls.get(dbe)
            add_checks = False
            self.set_dbe(dbe, db, tbl, add_checks, con_dets, default_dbs,
                default_tbls)
        except KeyError as e:
            self.restore_proj_dic(dic2restore)
            raise Exception("Unable to read project dictionary for required "
                f"keys.\nCaused by error: {b.ue(e)}")
        except Exception as e:
            self.restore_proj_dic(dic2restore)
            raise Exception(
                f"Unable to set proj dic.\nCaused by error: {b.ue(e)}")
        ## only change if successful
        self.con_dets = con_dets
        self.default_dbs = default_dbs
        self.default_tbls = default_tbls
        self.proj_dic = proj_dic

    def restore_proj_dic(self, dic2restore):
        "Restore to original project (or default if all else fails)"
        if dic2restore:
            default_proj_dic = config_globals.get_settings_dic(
                subfolder=mg.PROJS_FOLDER, fil_name=mg.DEFAULT_PROJ)
            self.set_proj_dic(dic2restore, default_proj_dic)

    def set_dbe(self, dbe, db=None, tbl=None, add_checks=False,
            con_dets=None, default_dbs=None, default_tbls=None):
        """
        Changing dbe has implications for everything connected.

        May want to refresh dbe and db together (e.g. dbe-db dropdown).

        add_checks -- implemented in SQLite for making strictly typed tables as
        required.
        """
        debug = False
        if debug: print("About to get dbe resources")
        con_dets = con_dets or self.con_dets
        default_dbs = default_dbs or self.default_dbs
        default_tbls = default_tbls or self.default_tbls
        ## free up if in use. MS Access will crash otherwise.
        try:
            self.cur.close()
            self.cur = None
            self.con.close()
            self.con = None
        except Exception:
            pass
        try:
            dbe_resources = get_dbe_resources(dbe, con_dets,
                default_dbs, default_tbls,
                db, tbl, add_checks=add_checks)
        except Exception as e:
            raise Exception(
                f"Unable to get dbe resources.\nCaused by error: {b.ue(e)}")
        self.dbe = dbe  ## only change if getting dbe resources worked
        if debug: print("Finished getting dbe resources")
        self.con = dbe_resources[mg.DBE_CON]
        self.cur = dbe_resources[mg.DBE_CUR]
        self.dbs = dbe_resources[mg.DBE_DBS]
        self.db = dbe_resources[mg.DBE_DB]
        self.tbls = dbe_resources[mg.DBE_TBLS]
        self.tbl = dbe_resources[mg.DBE_TBL]
        self.flds = dbe_resources[mg.DBE_FLDS]
        self.idxs = dbe_resources[mg.DBE_IDXS]
        self.has_unique = dbe_resources[mg.DBE_HAS_UNIQUE]

    def set_db(self, db, tbl=None):
        """
        Changing the db has implications for tbls, tbl etc.
        """
        db_resources = get_db_resources(self.dbe, self.cur, db,
            self.default_tbls, tbl)
        self.db = db  ## only change if getting db resources worked
        self.tbls = db_resources[mg.DBE_TBLS]
        self.tbl = db_resources[mg.DBE_TBL]
        self.flds = db_resources[mg.DBE_FLDS]
        self.idxs = db_resources[mg.DBE_IDXS]
        self.has_unique = db_resources[mg.DBE_HAS_UNIQUE]

    def set_tbl(self, tbl):
        tbl_dets = get_tbl_dets(self.dbe, self.cur, self.db, tbl)
        self.tbl = tbl  ## only change if getting tbl dets worked
        self.flds = tbl_dets[mg.DBE_FLDS]
        self.idxs = tbl_dets[mg.DBE_IDXS]
        self.has_unique = tbl_dets[mg.DBE_HAS_UNIQUE]

    def __str__(self):
        return (f"dbe: {self.dbe}; dbs: {self.dbs}; db: {self.db}; "
            f"tbls: {self.tbls}; tbl: {self.tbl}; flds: {self.flds}; "
            f"idxs: {self.idxs}; has_unique: {self.has_unique}")

def force_sofa_tbls_refresh(sofa_default_db_cur):
    """
    Sometimes you drop a table, make it, drop it, go to make it and it still
    seems to be there. This seems to force a refresh.

    commit() doesn't seem to solve the problem and it occurs even when only
    one connection in play. 
    """
    SQL_get_tbls = """SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name"""
    try:
        sofa_default_db_cur.execute(SQL_get_tbls)
    except Exception as e:
        raise Exception("force_sofa_tbls_refresh() can only be used for the "
            f"default db\nCaused by error: {b.ue(e)}")

def reset_main_con_if_sofa_default(tblname=None, add_checks=False):
    """
    If the main connection is to the default database, and there has been a
    change e.g. new table, the connection.
    """
    dd = mg.DATADETS_OBJ
    if dd.dbe == mg.DBE_SQLITE and dd.db == mg.SOFA_DB:
        dd.set_dbe(dbe=mg.DBE_SQLITE, db=mg.SOFA_DB, tbl=tblname,
            add_checks=add_checks)

def _get_gen_fldtype_lbl(fldtype):
    """
    Get general field type from specific.
    """
    if fldtype.lower() in dbe_sqlite.NUMERIC_TYPES:
        gen_fldtype = mg.FLDTYPE_NUMERIC_LBL
    elif fldtype.lower() in dbe_sqlite.DATE_TYPES:
        gen_fldtype = mg.FLDTYPE_DATE_LBL
    else:
        gen_fldtype = mg.FLDTYPE_STRING_LBL
    return gen_fldtype

def get_init_settings_data(default_dd, tblname):
    """
    Get ordered list of tuples of field names and field types for named table.
    "Numeric", "Date", "Text".

    Only works for an SQLite database (should be the default one).
    """
    debug = False
    if debug: print(f"default_dd: {default_dd}")
    default_dd.con.commit()
    default_dd.cur.execute("PRAGMA table_info("
        f"{tblname_qtr(default_dd.dbe, tblname)})")
    config = default_dd.cur.fetchall()
    if debug: print(config)
    table_config = [(x[1], _get_gen_fldtype_lbl(fldtype=x[2])) for x in config]
    return table_config

## syntax

def get_val2float_func(dbe):
    """
    Get appropriate syntax to force value to be treated as a float rather than
    an integer e.g. to ensure correct calculation of mean.
    """
    try:
        val2float = mg.DBE_MODULES[dbe].val2float
    except Exception:
        def val2float(val):
            return val
    return val2float 

def get_cartesian_joiner(dbe):
    """
    Get appropriate syntax to cartesian join entities.
    """
    return mg.DBE_MODULES[dbe].cartesian_joiner

def get_obj_quoter_func(dbe):
    """
    Get appropriate function to wrap content e.g. table or field name,
    in dbe-friendly way.
    """
    return mg.DBE_MODULES[dbe].quote_obj

def get_val_quoter_func(dbe):
    """
    Get appropriate function to wrap values e.g. the contents of a string field,
    in dbe-friendly way.
    """
    return mg.DBE_MODULES[dbe].quote_val

def get_first_sql(dbe, quoted_tblname, top_n, order_val=None):
    """
    quoted_tblname -- Must already be quoted.
    """
    return mg.DBE_MODULES[dbe].get_first_sql(quoted_tblname, top_n, order_val)

def get_placeholder(dbe):
    return mg.DBE_MODULES[dbe].placeholder

def get_gte(dbe, gte):
    if gte == mg.GTE_NOT_EQUALS:
        return mg.DBE_MODULES[dbe].gte_not_equals
    return gte

def get_dbe_syntax_elements(dbe):
    """
    Returns if_clause (string), left_obj_quote(string), right_obj_quote
    (string), quote_obj(), quote_val(), placeholder (string), get_summable(),
    gte_not_equals (string).

    if_clause receives 3 inputs - the test, result if true, result if false
    e.g. MySQL "IF(%s, %s, %s)"

    Sum and if statements are used to get frequencies in SOFA Statistics.
    """
    return mg.DBE_MODULES[dbe].get_syntax_elements()
##########################################################################################

def make_fld_val_clause_non_numeric(fldname, val, dbe_gte, flds, quote_obj, 
        quote_val):
    debug = False
    quoted_obj = quote_obj(fldname)
    if debug: print(f"quoted_obj: {quoted_obj}")
    quoted_val = quote_val(val)
    if len(quoted_val) > mg.MAX_VAL_LEN_IN_SQL_CLAUSE:  ## can't do len of raw val when a datetime in Postgresql - datetime.datetime has no len()
        raise my_exceptions.CategoryTooLong(fldname)
    if debug: print(f"quoted_val: {quoted_val}")
    clause = f"{quoted_obj} {dbe_gte} {quoted_val}"
    if debug: print(clause)
    return clause
    
def make_fld_val_clause(dbe, flds, fldname, val, gte=mg.GTE_EQUALS):
    """
    Make a filter clause with a field name = a value (numeric or non-numeric).

    objqtr -- function specific to database engine for quoting objects

    valqtr -- function specific to database engine for quoting values

    Handle val=None. Treat as Null for clause.

    If a string number is received e.g. u'56' it will be treated as a string
    if the dbe is SQLite and will be treated differently from 56 for filtering.
    """
    debug = False
    bolsqlite = (dbe == mg.DBE_SQLITE)
    objqtr = get_obj_quoter_func(dbe)
    valqtr = get_val_quoter_func(dbe)
    dbe_gte = get_gte(dbe, gte)
    bolnumeric = flds[fldname][mg.FLD_BOLNUMERIC]
    #boldatetime = flds[fldname][mg.FLD_BOLDATETIME]
    if val is None:
        if gte == mg.GTE_EQUALS:
            clause = f"{objqtr(fldname)} IS NULL"
        elif gte == mg.GTE_NOT_EQUALS:
            clause = f"{objqtr(fldname)} IS NOT NULL"
        else:
            raise Exception(f"Can only use = or {mg.GTE_NOT_EQUALS} "
                + "with missing or Null values.")
    else:
        num = True
        if not bolnumeric:
            num = False
        elif bolsqlite:  ## if SQLite may still be non-numeric
            if not lib.TypeLib.is_basic_num(val):
                num = False
        if num:
            ## Need repr otherwise truncates decimals e.g. 111.582756811 instead
            ## of 111.58275680743.
            ## MySQL return L on end of longs so strip it off
            val2use = repr(val).strip('L')
            if debug:
                print(f"val2use: {val2use}")
                print(f"val: {val}")
                print(f"str(val): {str(val)}")
                print(float(val2use) == val)
            if float(repr(val).strip('L')) != val:
                ## will not be found using an SQL query
                raise Exception(
                    f"{val2use} is not a suitable value for use as a category")
            clause = f"{objqtr(fldname)} {dbe_gte} {repr(val).strip('L')}"
        else:
            clause = make_fld_val_clause_non_numeric(fldname, val, dbe_gte,
                flds, objqtr, valqtr)
    if debug: print(clause)
    return clause

def set_data_con_gui(parent, readonly, scroll, szr, lblfont):
    ""
    for dbe in mg.DBES:
        mg.DBE_MODULES[dbe].set_data_con_gui(parent, readonly, scroll, szr, 
            lblfont)

def get_proj_con_settings(parent, proj_dic):
    "Get project connection settings"
    for dbe in mg.DBES:
        mg.DBE_MODULES[dbe].get_proj_settings(parent, proj_dic)

def fldsdic_to_fldnames_lst(fldsdic):
    # pprint.pprint(flds_dic) # debug
    fldslst = sorted(fldsdic, key=lambda s: fldsdic[s][mg.FLD_SEQ])
    return fldslst

def set_con_det_defaults(parent):
    """
    Check project connection settings to handle missing values and set 
    sensible defaults.
    """
    for dbe in mg.DBES:
        mg.DBE_MODULES[dbe].set_con_det_defaults(parent)

def process_con_dets(parent, default_dbs, default_tbls, con_dets):
    r"""
    Populate default_dbs, default_tbls, and con_dets.

    con_dets must contain paths ready to record i.e. double backslashes where
    needed in paths.  Cannot use single backslashes as the standard approach
    because want unicode strings and will sometimes encounter \U within such
    string e.g. Vista and Win 7 C:\Users\...

    Returns any_incomplete (partially completed connection details), any_cons 
    (any of them set completely), and completed_dbes. Completed_dbes is so we 
    can ensure the default dbe has con details set for it.

    NB If any incomplete, stop processing and return None for any_cons.
    """
    any_incomplete = False
    any_cons = False
    completed_dbes = []  ## so can check the default dbe has details set
    for dbe in mg.DBES:
        ## has_incomplete means started but some key detail(s) missing
        ## has_con means all required details are completed
        has_incomplete, has_con = mg.DBE_MODULES[dbe].process_con_dets(parent,
            default_dbs, default_tbls, con_dets)
        if has_incomplete:
            return True, None, completed_dbes
        if has_con:
            completed_dbes.append(dbe)
            any_cons = True
    return any_incomplete, any_cons, completed_dbes

def get_db_item(db_name, dbe):
    return f"{db_name} ({dbe})"

def extract_db_dets(choice_text):
    start_idx = choice_text.index('(') + 1
    end_idx = choice_text.index(')')
    dbe = choice_text[start_idx:end_idx]
    db_name = choice_text[:start_idx - 2]
    return db_name, dbe

def prep_val(dbe, val, fld_dic):
    """
    Prepare raw value for insertion/update via SQL.

    Missing (.) and None -> None.

    Any non-missing/null values in numeric fields are simply passed through.

    Values in datetime fields are returned as datetime strings (if valid) ready 
    to include in SQL.  If not valid, the faulty value is returned as is in the 
    knowledge that it will fail validation later (cell_invalid) and not actually 
    be saved to a database (in db_grid.update_cell()).

    Why is a faulty datetime allowed through?  Because we don't want to have to 
    handle exceptions at this point (things can happen in a different order 
    depending on whether a mouse click or tabbing occurred). It is cleaner to 
    just rely on the validation step which occurs to all data (numbers etc), 
    which not only prevents faulty data being entered, but also gives the user 
    helpful feedback in an orderly way.
    """
    debug = False
    try:
        ## most modules won't need to have a special function
        prep_val = mg.DBE_MODULES[dbe].prep_val(val, fld_dic)
    except AttributeError:
        ## the most common path
        if val in [None, mg.MISSING_VAL_INDICATOR]:
            val2use = None
        elif fld_dic[mg.FLD_BOLDATETIME]:
            if val == '':
                val2use = None
            else:
                try:
                    val2use = lib.DateLib.get_std_datetime_str(val)
                except Exception:
                    ## Will not pass cell validation later and better to
                    ## avoid throwing exceptions in the middle of things.
                    if debug: print(f"{val2use} is not a valid datetime")
                    val2use = val
        else:
            val2use = val
        if debug: print(val2use)
        prep_val = val2use
    return prep_val

def insert_row(tbl_dd, data):
    """
    Returns success (boolean) and message (None or error).
    data = [(value as string (or None), fld_dets), ...]
    """
    debug = False
    (unused, left_obj_quote, right_obj_quote, unused, unused, 
     placeholder, unused, unused, unused) = get_dbe_syntax_elements(tbl_dd.dbe) 
    """
    Modify any values (according to field details) to be ready for insertion.
    Use placeholders in execute statement.
    Commit insert statement.
    TODO - test this in Windows.

    :param list data: [(value as string (or None), fldname, fld_dets), ...]
    """
    if debug: pprint.pprint(data)
    #fld_dics = [x[2] for x in data]
    fldnames = [x[1] for x in data]
    joiner = f"{right_obj_quote}, {left_obj_quote}"
    fldnames_clause = (f" ({left_obj_quote}"
        + joiner.join(fldnames) + f'{right_obj_quote}) ')
    ## e.g. (`fname`, `lname`, `dob` ...)
    fld_placeholders_clause = (' ('
        + ", ".join([placeholder for x in range(len(data))]) + ') ')
    ## e.g. " (%s, %s, %s, ...) or (?, ?, ?, ...)"
    SQL_insert = (f"INSERT INTO {tblname_qtr(tbl_dd.dbe, tbl_dd.tbl)} "
        + fldnames_clause + f"VALUES {fld_placeholders_clause}")
    if debug: print(SQL_insert)
    data_lst = []
    for data_dets in data:
        if debug: pprint.pprint(data_dets)
        val, unused, fld_dic = data_dets
        val2use = prep_val(tbl_dd.dbe, val, fld_dic)
        data_lst.append(val2use)
    data_tup = tuple(data_lst)
    try:
        tbl_dd.cur.execute(SQL_insert, data_tup)
        tbl_dd.con.commit()
        return True, None
    except Exception as e:
        if debug:
            print(
                f"Failed to insert row. SQL: {SQL_insert}, Data: {str(data_tup)}"
                + f"\n\nCaused by error: {b.ue(e)}")
        return False, b.ue(e)

def delete_row(id_fld, row_id):
    """
    Use placeholders in execute statement.
    Commit delete statement.
    NB row_id could be text or a number.
    TODO - test this in Windows.
    """
    debug = False
    dd = mg.DATADETS_OBJ
    objqtr = get_obj_quoter_func(dd.dbe)
    placeholder = get_placeholder(dd.dbe)
    SQL_delete = (f"DELETE FROM {tblname_qtr(dd.dbe, dd.tbl)} "
        + f"WHERE {objqtr(id_fld)} = {placeholder}")
    if debug: print(SQL_delete)
    data_tup = (row_id,)
    try:
        dd.cur.execute(SQL_delete, data_tup)
        dd.con.commit()
        return True, None
    except Exception as e:
        if debug:
            print(f"Failed to delete row. SQL: {SQL_delete}, row id: {row_id}"
                + f"\n\nOriginal error: {b.ue(e)}")
        return False, b.ue(e)

def get_readonly_settings():
    """
    Can always edit the default database (apart from demo_tbl) so disabled and
    True.
    """
    dd = mg.DATADETS_OBJ
    sofa_default_db = (dd.dbe == mg.DBE_SQLITE and dd.db == mg.SOFA_DB)
    enabled = not sofa_default_db
    readonly = True
    if sofa_default_db:
        readonly = (dd.tbl == mg.DEMO_TBL)
    return ReadonlyDets(readonly, enabled)

## Assumption - drop_tbls is always named as such
def data_dropdown_settings_correct(parent):
    try:
        parent.drop_tbls_panel
        parent.drop_tbls_szr
        parent.drop_tbls_idx_in_szr
        parent.drop_tbls_sel_evt
        parent.drop_tbls_system_font_size
        parent.drop_tbls_rmargin
        parent.drop_tbls_can_grow
    except AttributeError:
        raise Exception("Working with dropdowns requires all the settings to "
            "be available e.g. self.drop_tbls_panel")

def get_data_dropdowns(parent, panel, default_dbs):
    """
    Returns drop_dbs and drop_tbls to frame with correct values and default
    selection. Also returns some settings to store in the frame.

    Note - must have exact same names.
    """
    debug = False
    ## Databases list needs to be tuple including dbe so can get both from
    ## sequence alone e.g. when identifying selection.
    dd = mg.DATADETS_OBJ
    ## Can't just use dbs list for dd - sqlite etc may have multiple dbs but
    ## only one per con.
    dbe_dbs_list = mg.DBE_MODULES[dd.dbe].get_dbs_list(dd.con_dets, default_dbs)
    db_choices = [(x, dd.dbe) for x in dbe_dbs_list]
    dbes = mg.DBES[:]
    dbes.pop(dbes.index(dd.dbe))
    for oth_dbe in dbes:  ## may not have any connection details
        try:
            oth_dbe_dbs_list = mg.DBE_MODULES[oth_dbe].get_dbs_list(
                dd.con_dets, default_dbs)
            oth_db_choices = [(x, oth_dbe) for x in oth_dbe_dbs_list]
            db_choices.extend(oth_db_choices)
        except my_exceptions.MissingConDets as e:
            if debug: print(str(e))
            pass  ## no connection possible
        except Exception as e:
            wx.MessageBox(_("Unable to connect to %(oth_dbe)s using the details"
                " provided.\nCaused by error: %(e)s") % {"oth_dbe": oth_dbe,
                "e": b.ue(e)})
    db_choice_items = [get_db_item(x[0], x[1]) for x in db_choices]
    drop_dbs = wx.Choice(
        panel, -1, choices=db_choice_items, size=wx.DefaultSize)
    if not parent.drop_tbls_system_font_size:
        drop_dbs.SetFont(mg.GEN_FONT)
    drop_dbs.Bind(wx.EVT_CHOICE, parent.on_database_sel)
    dbs_lc = [x.lower() for x in dd.dbs]
    selected_dbe_db_idx = dbs_lc.index(dd.db.lower())
    drop_dbs.SetSelection(selected_dbe_db_idx)
    tbls_with_filts, idx_tbl = get_tblnames_and_idx()
    drop_tbls = wx.Choice(
        panel, -1, choices=tbls_with_filts, size=wx.DefaultSize)  #size=(mg.STD_DROP_WIDTH,-1))
    extra_drop_tbls_setup(parent, drop_tbls, idx_tbl)
    return drop_dbs, drop_tbls, db_choice_items, selected_dbe_db_idx

def get_tblnames_and_idx():
    dd = mg.DATADETS_OBJ
    tbls_with_filts = []
    idx_tbl = None
    for i, tblname in enumerate(dd.tbls):
        if tblname.lower() == dd.tbl.lower():
            idx_tbl = i
        unused, tbl_filt = lib.FiltLib.get_tbl_filt(dd.dbe, dd.db, tblname)
        if tbl_filt:
            tbl_with_filt = f"{tblname} {_('(filtered)')}"
        else:
            tbl_with_filt = tblname
        tbls_with_filts.append(tbl_with_filt)
    return tbls_with_filts, idx_tbl

def extra_drop_tbls_setup(parent, drop_tbls, idx_tbl):
    dd = mg.DATADETS_OBJ
    try:
        drop_tbls.SetSelection(idx_tbl)
    except NameError:
        raise Exception(f'Table "{dd.tbl}" not found in tables list')
    if not parent.drop_tbls_system_font_size:
        drop_tbls.SetFont(mg.GEN_FONT)
    try:
        parent.drop_tbls_sel_evt
    except AttributeError:
        raise Exception("Must define self.drop_tbls_sel_evt first")
    drop_tbls.Bind(wx.EVT_CHOICE, parent.drop_tbls_sel_evt)
    
def get_fresh_drop_tbls(parent, szr, panel):
    """
    Destroy the existing dropdown widget, create a new one (with the non-system 
    font size), feed it back into the sizer.
    """
    szr.Remove(parent.drop_tbls_idx_in_szr)  ## remove from sizer before destroying
    parent.drop_tbls.Destroy()
    tbls_with_filts, idx_tbl = get_tblnames_and_idx()
    drop_tbls = wx.Choice(
        panel, -1, choices=tbls_with_filts, size=wx.DefaultSize)
    extra_drop_tbls_setup(parent, drop_tbls, idx_tbl)
    flag = wx.RIGHT
    if parent.drop_tbls_can_grow:
        flag |= wx.GROW
    szr.Insert(parent.drop_tbls_idx_in_szr, drop_tbls, 0, flag,
        parent.drop_tbls_rmargin)
    panel.Layout()
    return drop_tbls

def set_parent_db_dets(parent, dbe, db):
    """
    Set all parent database details including drop down.
    """
    dd = mg.DATADETS_OBJ
    dd.set_dbe(dbe, db)
    parent.dbe = dd.dbe
    parent.db = dd.db
    parent.con = dd.con
    parent.cur = dd.cur
    parent.tbls = dd.tbls
    parent.tbl = dd.tbl
    parent.flds = dd.flds
    parent.idxs = dd.idxs
    parent.has_unique = dd.has_unique
    parent.drop_tbls = get_fresh_drop_tbls(parent, parent.drop_tbls_szr,
        parent.drop_tbls_panel)
    
def refresh_db_dets(parent):
    """
    Responds to a database selection.

    When the database dropdowns are created, the selected idx is stored. If
    need to undo, we set selection to that and also reset all database details. 
    If ok to accept change, reset the selected idx to what has just been 
    selected.

    Returns False if no change (so we can avoid all the updating).
    """
    debug = False
    # only go through step if a change made
    orig_selected_dbe_db_idx = parent.selected_dbe_db_idx
    if parent.drop_dbs.GetSelection() == orig_selected_dbe_db_idx:
        if debug: print("No change so nothing to do")
        return False
    if debug: print("Was change - so plenty of work ahead")
    wx.BeginBusyCursor()
    db_choice_item = parent.db_choice_items[parent.drop_dbs.GetSelection()]
    db, dbe = extract_db_dets(db_choice_item)
    try:
        set_parent_db_dets(parent, dbe, db)
        # successful so can now change
        parent.selected_dbe_db_idx = parent.drop_dbs.GetSelection()
    except Exception as e:
        wx.MessageBox(_("Experienced problem refreshing database details.") +
            "\nCaused by error %s" % b.ue(e))
        # roll back
        orig_db_choice_item = parent.db_choice_items[orig_selected_dbe_db_idx]
        orig_db, orig_dbe = extract_db_dets(orig_db_choice_item)
        set_parent_db_dets(parent, orig_dbe, orig_db)
        parent.drop_dbs.SetSelection(orig_selected_dbe_db_idx)
    finally:
        lib.GuiLib.safe_end_cursor()
    return True

def refresh_tbl_dets(parent):
    """
    Reset table, fields, has_unique, and idxs after a table selection.
    Run anything like reset_tbl_dropdown first.
    """
    wx.BeginBusyCursor()
    dd = mg.DATADETS_OBJ
    try:
        tbl = dd.tbls[parent.drop_tbls.GetSelection()]
        dd.set_tbl(tbl)
        parent.tbl = dd.tbl
        parent.flds = dd.flds
        parent.idxs = dd.idxs
        parent.has_unique = dd.has_unique
    except Exception:
        wx.MessageBox(_("Experienced problem refreshing table details"))
        raise
    finally:
        lib.GuiLib.safe_end_cursor()

def get_default_db_dets():
    """
    Returns con, cur, dbs, tbls, flds, idxs, has_unique from default
    SOFA SQLite database.
    """
    proj_dic = config_globals.get_settings_dic(subfolder=mg.PROJS_FOLDER, 
        fil_name=mg.DEFAULT_PROJ)
    default_dd = DataDets(proj_dic)
    default_dd.set_dbe(dbe=mg.DBE_SQLITE, db=mg.SOFA_DB)
    dbe_sqlite.add_funcs_to_con(default_dd.con) # otherwise the functions aren't available if needed raising sqlite3.OperationalError: no such function: is_numeric
    return default_dd

def dup_tblname(tblname):
    """
    Duplicate name in default SQLite SOFA database?
    """
    default_dd = get_default_db_dets()
    default_dd.con.close()
    return tblname in default_dd.tbls

def make_flds_clause(settings_data):
    """
    Create a clause ready to put in a select statement which takes into account
    original and new names if an existing field which has changed name. Does not
    include the sofa_id. NB a new field will only have a new name so the orig
    name will be None.

    settings_data -- dict with TBL_FLDNAME, TBL_FLDNAME_ORIG, TBL_FLDTYPE,
    TBL_FLDTYPE_ORIG. Includes row with sofa_id.
    """
    debug = False
    objqtr = get_obj_quoter_func(mg.DBE_SQLITE)
    ## Get orig_name, new_name tuples for all fields in final table apart
    ## from the sofa_id.
    orig_new_names = [(x[mg.TBL_FLDNAME_ORIG], x[mg.TBL_FLDNAME])
        for x in settings_data if x[mg.TBL_FLDNAME_ORIG] != mg.SOFA_ID]
    if debug:
        print(f"settings_data: {settings_data}")
        print(f"orig_new_names: {orig_new_names}")
    fld_clause_items = []
    for orig_name, new_name in orig_new_names:
        qorig_name = objqtr(orig_name)
        qnew_name = objqtr(new_name)
        if orig_name is None:
            clause = f"NULL {qnew_name}"
        elif orig_name == new_name:
            clause = qnew_name
        else:
            clause = f"{qorig_name} {qnew_name}"
        fld_clause_items.append(clause)
    fld_clause = ', '.join(fld_clause_items)
    return fld_clause

def get_oth_name_types(settings_data):
    """
    Returns name, type tuples for all fields except for the sofa_id.

    settings_data -- dict with TBL_FLDNAME, TBL_FLDNAME_ORIG, TBL_FLDTYPE,
    TBL_FLDTYPE_ORIG. Includes row with sofa_id.
    """
    oth_name_types = [(x[mg.TBL_FLDNAME], mg.FLDTYPE_LBL2KEY[x[mg.TBL_FLDTYPE]])
        for x in settings_data if x[mg.TBL_FLDNAME] != mg.SOFA_ID]
    if not oth_name_types:
        raise Exception(_("Must always be at least one field in addition to the"
            f' "{mg.SOFA_ID}" field'))
    return oth_name_types

def get_create_flds_txt(oth_name_types, *,
        strict_typing=False, inc_sofa_id=True):
    """
    Get text clause which defines fields for use in an SQLite create table
    statement. The table will be created inside the default SOFA SQLite
    database. If the sofa_id is included, the text must define the sofa_id as
    UNIQUE.

    oth_name_types -- ok_fldname, fldtype. Does not include sofa_id. The
    sofa_id can be added below if required.

    strict_typing -- add check constraints to fields.
    """
    debug = False
    objqtr = get_obj_quoter_func(mg.DBE_SQLITE)
    sofa_id = objqtr(mg.SOFA_ID)
    if inc_sofa_id:
        fld_clause_items = [f"{sofa_id} INTEGER PRIMARY KEY", ]
    else:
        fld_clause_items = []
    for fldname, fldtype in oth_name_types:
        if fldname == mg.SOFA_ID:
            raise Exception(
                f"Do not pass sofa_id into {sys._getframe().f_code.co_name}")
        if fldname == '':
            raise Exception("Do not pass fields with empty string names into "
                f"{sys._getframe().f_code.co_name}")
        tosqlite = mg.GEN2SQLITE_DIC[fldtype]
        if strict_typing:
            check = tosqlite['check_clause'] % {"fldname": objqtr(fldname)}
        else:
            check = ''
        if debug: print(f"{fldname} {fldtype} {check}")
        clause = f"{objqtr(fldname)} {tosqlite['sqlite_type']} {check}"
        if debug: print(f"clause: {clause}")
        fld_clause_items.append(clause)
    if inc_sofa_id:
        fld_clause_items.append(f"UNIQUE({sofa_id})")
    fld_clause = ', '.join(fld_clause_items)
    return fld_clause

def make_sofa_tbl(con, cur, tblname, oth_name_types, *,
        strict_typing=False, headless=False):
    """
    Make a table into the SOFA default database. Must have autonumber SOFA_ID.

    Optionally may apply type checking constraint on fields (NB no longer able
    to open database outside of this application which using user-defined
    functions in table definitions).

    :param list oth_name_types: [(ok_fldname, fldtype), ...]. No need to
     reference old names or types.
    :param bool strict_typing: uses user-defined functions to apply strict
     typing via check clauses as part of create table statements.
    """
    debug = False
    fld_clause = get_create_flds_txt(oth_name_types,
        strict_typing=strict_typing, inc_sofa_id=True)
    SQL_make_tbl = f'CREATE TABLE "{tblname}" ({fld_clause})'
    if debug: print(SQL_make_tbl)
    cur.execute(SQL_make_tbl)
    con.commit()
    if debug: print(f"Successfully created {tblname}")
    force_sofa_tbls_refresh(sofa_default_db_cur=cur)
    if not headless:
        ## If the main data connection is to this (default sofa) database it
        ## must be reconnected to ensure the change has been registered.
        dd = mg.DATADETS_OBJ
        if dd.dbe == mg.DBE_SQLITE and dd.db == mg.SOFA_DB:
            dd.set_dbe(dbe=mg.DBE_SQLITE, db=mg.SOFA_DB, tbl=tblname,
                add_checks=False)
