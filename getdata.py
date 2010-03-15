from __future__ import print_function
import os
import pprint
import sys
import wx

import my_globals as mg
import config_globals
import lib

debug = False

def get_db_dets_obj(dbe, default_dbs, default_tbls, con_dets, db=None, 
                    tbl=None):
    """
    Pass in all con_dets (the dbe will be used to select specific con_dets).
    """
    return mg.DBE_MODULES[dbe].DbDets(default_dbs, default_tbls, con_dets, db, 
                                      tbl)


# must be before dbe import statements (they have classes based on DbDets)
class DbDets(object):
    
    def __init__ (self, default_dbs, default_tbls, con_dets, db=None, 
                  tbl=None):
        """
        If db or tbl are not supplied subclass must choose 
            e.g. default or first.  And once db identified, must update 
            con_dets.
        """
        # default dbs e.g. {'MySQL': u'demo_db', 'SQLite': u'SOFA_Default_db'}
        self.default_dbs = default_dbs
        # default tbls e.g. {'MySQL': u'demo_tbl', 'SQLite': u'SOFA_Default_tbl'}
        self.default_tbls = default_tbls
        # con_dets e.g. {'MySQL': {'host': u'localhost', 'passwd': ...}
        self.con_dets = con_dets
        self.db = db
        self.tbl = tbl
    
    def get_db_tbls(self, cur, db):
        "Must return tbls"
        assert 0, "Must define get_db_tbls in subclass"
        
    def get_tbl_flds(self, cur, db, tbl):
        """
        Must return dic of dics called flds.
        Gets dic of dics for each field with field name as key. Each field dic
            has as keys the FLD_ variables listed in my_globals e.g. 
            FLD_BOLNUMERIC.
        Need enough to present fields in order, validate data entry, 
            and guide labelling and reporting (e.g. numeric or categorical).
        """
        assert 0, "Must define get_tbl_flds in subclass"
    
    def get_index_dets(self, cur, db, tbl):
        "Must return has_unique, idxs"
        assert 0, "Must define get_index_dets in subclass"
       
    def get_db_dets(self):
        """
        Return connection, cursor, and get lists of databases, tables, fields, 
            and index info, based on the database connection details provided.
        Sets db and tbl if not supplied.
        Must return con, cur, dbs, tbls, flds, has_unique, idxs.
        dbs used to make dropdown of all dbe dbs (called more than once).
        """
        assert 0, "Must define get_db_dets in subclass"

def make_fld_val_clause_non_numeric(fld_name, val, dbe_gte, quote_obj, 
                                    quote_val):
    debug = False
    clause = "%s %s %s" % (quote_obj(fld_name), dbe_gte, quote_val(val))
    if debug: print(clause)
    return clause
    
def make_fld_val_clause(dbe, flds, fld_name, val, gte=mg.GTE_EQUALS):
    """
    Make a filter clause with a field name = a value (numeric or non-numeric).
    quote_obj -- function specific to database engine for quoting objects
    quote_val -- function specific to database engine for quoting values
    Handle val=None.  Treat as Null for clause.
    If a string number is received e.g. u'56' it will be treated as a string
        if the dbe is SQLite and will be treated differently from 56 for 
        filtering.
    """
    debug = False
    bolsqlite = (dbe == mg.DBE_SQLITE)
    quote_obj = get_obj_quoter_func(dbe)
    quote_val = get_val_quoter_func(dbe)
    dbe_gte = get_gte(dbe, gte)
    bolnumeric = flds[fld_name][mg.FLD_BOLNUMERIC]
    boldatetime = flds[fld_name][mg.FLD_BOLDATETIME]
    if val is None:
        if gte == mg.GTE_EQUALS:
            clause = u"%s IS NULL" % quote_obj(fld_name)
        elif gte == mg.GTE_NOT_EQUALS:
            clause = u"%s IS NOT NULL" % quote_obj(fld_name)
        else:
            raise Exception, ("Can only use = or "
                "%s with missing or Null values.") % mg.GTE_NOT_EQUALS
    else:
        num = True
        if not bolnumeric:
            num = False
        elif bolsqlite: # if SQLite may still be non-numeric
            if not lib.is_basic_num(val):
                num = False
        if num:
            clause = u"%s %s %s" % (quote_obj(fld_name), dbe_gte, val)
        else:
            clause = make_fld_val_clause_non_numeric(fld_name, val, dbe_gte, 
                                                     quote_obj, quote_val)
    if debug: print(clause)
    return clause

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

def get_placeholder(dbe):
    return mg.DBE_MODULES[dbe].placeholder

def get_gte(dbe, gte):
    if gte == mg.GTE_NOT_EQUALS:
        return mg.DBE_MODULES[dbe].gte_not_equals
    return gte

def get_dbe_syntax_elements(dbe):
    """
    Returns if_clause (string), left_obj_quote(string), right_obj_quote 
        (string), quote_obj(), quote_val(), placeholder (string), 
        get_summable(), gte_not_equals (string).
    if_clause receives 3 inputs - the test, result if true, result if false
    e.g. MySQL "IF(%s, %s, %s)"
    Sum and if statements are used to get frequencies in SOFA Statistics.
    """
    return mg.DBE_MODULES[dbe].get_syntax_elements()

def set_data_con_gui(parent, readonly, scroll, szr, lblfont):
    ""
    for dbe in mg.DBES:
        mg.DBE_MODULES[dbe].set_data_con_gui(parent, readonly, scroll, 
                                                     szr, lblfont)

def get_proj_con_settings(parent, proj_dic):
    "Get project connection settings"
    for dbe in mg.DBES:
        mg.DBE_MODULES[dbe].get_proj_settings(parent, proj_dic)

def flds_dic_to_fld_names_lst(flds_dic):
    # pprint.pprint(flds_dic) # debug
    flds_lst = sorted(flds_dic, key=lambda s: flds_dic[s][mg.FLD_SEQ])
    return flds_lst

def set_con_det_defaults(parent):
    """
    Check project connection settings to handle missing values and set 
        sensible defaults.
    """
    for dbe in mg.DBES:
        mg.DBE_MODULES[dbe].set_con_det_defaults(parent)

def process_con_dets(parent, default_dbs, default_tbls, con_dets):
    """
    Populate default_dbs, default_tbls, and con_dets.
    con_dets must contain paths ready to record i.e. double backslashes where
        needed in paths.  Cannot use single backslashes as the standard approach
        because want unicode strings and will sometimes encounter \U within such
        string e.g. Vista and Win 7 C:\Users\...
    Returns any_incomplete (partially completed connection details), 
        any_cons (any of them set completely), and completed_dbes.
        Completed_dbes is so we can ensure the default dbe has con details 
        set for it.
    NB If any incomplete, stop processing and return None for any_cons.
    """
    any_incomplete = False
    any_cons = False
    completed_dbes = [] # so can check the default dbe has details set
    for dbe in mg.DBES:
        # has_incomplete means started but some key detail(s) missing
        # has_con means all required details are completed
        has_incomplete, has_con = mg.DBE_MODULES[dbe].process_con_dets(parent, 
                                            default_dbs, default_tbls, con_dets)
        if has_incomplete:
            return True, None, completed_dbes
        if has_con:
            completed_dbes.append(dbe)
            any_cons = True
    return any_incomplete, any_cons, completed_dbes

def get_db_item(db_name, dbe):
    return u"%s (%s)" % (db_name, dbe)

def extractDbDets(choice_text):
    start_idx = choice_text.index(u"(") + 1
    end_idx = choice_text.index(u")")
    dbe = choice_text[start_idx:end_idx]
    db_name = choice_text[:start_idx - 2]
    return db_name, dbe

def prep_val(dbe, val, fld_dic):
    """
    Prepare raw value for insertion/update via SQL.
    Missing (.) and None -> None.
    Any non-missing/null values in numeric fields are simply passed through.
    Values in datetime fields are returned as datetime strings (if valid) ready 
        to include in SQL.  If not valid, the faulty value is returned as is in 
        the knowledge that it will fail validation later (cell_invalid) and not
        actually be saved to a database (in db_grid.update_cell()).
    Why is a faulty datetime allowed through?  Because we don't want to have to 
        handle exceptions at this point (things can happen in a different order 
        depending on whether a mouse click or tabbing occurred).
        It is cleaner to just rely on the validation step which occurs to all 
        data (numbers etc), which not only prevents faulty data being entered, 
        but also gives the user helpful feedback in an orderly way.
    """
    debug = False
    try:
        # most modules won't need to have a special function
        prep_val = mg.DBE_MODULES[dbe].prep_val(val, fld_dic)
    except AttributeError:
        # the most common path
        if val in [None, mg.MISSING_VAL_INDICATOR]:
            val2use = None
        elif fld_dic[mg.FLD_BOLDATETIME]:
            if val == u"":
                val2use = None
            else:
                try:
                    val2use = lib.get_std_datetime_str(val)
                except Exception:
                    # will not pass cell validation later and better to
                    # avoid throwing exceptions in the middle of things
                    if debug: print(u"%s is not a valid datetime")
                    val2use = val                   
        else:
            val2use = val
        if debug: print(val2use)
        prep_val = val2use
    return prep_val

def insert_row(dbe, con, cur, tbl_name, data):
    """
    Returns success (boolean) and message (None or error).
    data = [(value as string (or None), fld_dets), ...]
    """
    (unused, left_obj_quote, right_obj_quote, quote_obj, quote_val, placeholder, 
        unused, unused) = get_dbe_syntax_elements(dbe) 
    """
    data = [(value as string (or None), fld_name, fld_dets), ...]
    Modify any values (according to field details) to be ready for insertion.
    Use placeholders in execute statement.
    Commit insert statement.
    TODO - test this in Windows.
    """
    debug = False
    if debug: pprint.pprint(data)
    fld_dics = [x[2] for x in data]
    fld_names = [x[1] for x in data]
    joiner = u"%s, %s" % (right_obj_quote, left_obj_quote)
    fld_names_clause = u" (%s" % left_obj_quote + \
        joiner.join(fld_names) + u"%s) " % right_obj_quote
    # e.g. (`fname`, `lname`, `dob` ...)
    fld_placeholders_clause = " (" + \
        u", ".join([placeholder for x in range(len(data))]) + u") "
    # e.g. " (%s, %s, %s, ...) or (?, ?, ?, ...)"
    SQL_insert = u"INSERT INTO %s " % quote_obj(tbl_name) + fld_names_clause + \
        u"VALUES %s" % fld_placeholders_clause
    if debug: print(SQL_insert)
    data_lst = []
    for i, data_dets in enumerate(data):
        if debug: pprint.pprint(data_dets)
        val, fld_name, fld_dic = data_dets
        val2use = prep_val(dbe, val, fld_dic)
        data_lst.append(val2use)
    data_tup = tuple(data_lst)
    msg = None
    try:
        cur.execute(SQL_insert, data_tup)
        con.commit()
        return True, None
    except Exception, e:
        if debug: print(u"Failed to insert row.  SQL: %s, Data: %s" %
            (SQL_insert, unicode(data_tup)) + u"\n\nOriginal error: %s" % e)
        return False, u"%s" % e

def delete_row(dbe, con, cur, tbl_name, id_fld, row_id):
    """
    Use placeholders in execute statement.
    Commit delete statement.
    NB row_id could be text or a number.
    TODO - test this in Windows.
    """
    debug = False
    quote_obj = get_obj_quoter_func(dbe)
    placeholder = get_placeholder(dbe)
    SQL_delete = u"DELETE FROM %s " % quote_obj(tbl_name) + \
        u"WHERE %s = %s" % (quote_obj(id_fld), placeholder)
    if debug: print(SQL_delete)
    data_tup = (row_id,)
    try:
        cur.execute(SQL_delete, data_tup)
        con.commit()
        return True, None
    except Exception, e:
        if debug: print(u"Failed to delete row.  SQL: %s, row id: %s" %
            (SQL_delete, row_id) + u"\n\nOriginal error: %s" % e)
        return False, u"%s" % e

def get_data_dropdowns(parent, panel, dbe, default_dbs, default_tbls, con_dets, 
                       dbs_of_default_dbe, db, tbls, tbl):
    """
    Adds drop_dbs and drop_tbls to frame with correct values 
        and default selection.  NB must have exact same names.
    Adds db_choice_items to parent.
    """
    debug = False
    # databases list needs to be tuple including dbe so can get both from 
    # sequence alone e.g. when identifying selection
    db_choices = [(x, dbe) for x in dbs_of_default_dbe]      
    dbes = mg.DBES[:]
    dbes.pop(dbes.index(dbe))
    for oth_dbe in dbes: # may not have any connection details
        oth_default_db = default_dbs.get(oth_dbe)
        dbdetsobj = get_db_dets_obj(oth_dbe, default_dbs, default_tbls, 
                                    con_dets, oth_default_db, None)
        try:
            unused, unused, oth_dbs, unused, unused, unused, unused = \
                dbdetsobj.get_db_dets()
            oth_db_choices = [(x, oth_dbe) for x in oth_dbs]
            db_choices.extend(oth_db_choices)
        except Exception, e:
            if debug: print(unicode(e))
            pass # no connection possible
    parent.db_choice_items = [get_db_item(x[0], x[1]) for x in db_choices]
    parent.drop_dbs = wx.Choice(panel, -1, choices=parent.db_choice_items,
                                size=(300,-1))
    parent.drop_dbs.Bind(wx.EVT_CHOICE, parent.on_database_sel)
    dbs_lc = [x.lower() for x in dbs_of_default_dbe]
    parent.drop_dbs.SetSelection(dbs_lc.index(db.lower()))
    parent.drop_tbls = wx.Choice(panel, -1, choices=[], size=(300,-1))
    setup_drop_tbls(parent.drop_tbls, dbe, db, tbls, tbl)
    parent.drop_tbls.Bind(wx.EVT_CHOICE, parent.on_table_sel)
    return parent.drop_dbs, parent.drop_tbls

def setup_drop_tbls(drop_tbls, dbe, db, tbls, tbl):
    """
    Set-up tables dropdown.  Any tables with filtering should have (filtered)
        appended to end of name.
    """
    debug = False
    tbls_with_filts = []
    for i, tbl_name in enumerate(tbls):
        if tbl_name == tbl:
            idx_tbl = i
        tbl_filt_label, tbl_filt = lib.get_tbl_filt(dbe, db, tbl_name)
        if tbl_filt:
            tbl_with_filt = "%s %s" % (tbl_name, _("(filtered)"))
        else:
            tbl_with_filt = tbl_name
        tbls_with_filts.append(tbl_with_filt)
    drop_tbls.SetItems(tbls_with_filts)
    try:
        drop_tbls.SetSelection(idx_tbl)
    except NameError:
        raise Exception, "Table \"%s\" not found in tables list" % self.tbl

def refresh_default_dbs_tbls(dbe, default_dbs, default_tbls):
    """
    Check to see what the default database and table has been for this database
        engine.  If available, override the defaults taken from the project file
        for this point on (until session closed).
    """
    recent_db = mg.DB_DEFAULTS.get(dbe)
    if recent_db:
        default_dbs[dbe] = recent_db
    recent_tbl = mg.TBL_DEFAULTS.get(dbe)
    if recent_tbl:
        default_tbls[dbe] = recent_tbl

def refresh_db_dets(parent):
    """
    Returns dbe, db, con, cur, tbls, tbl, flds, has_unique, idxs.
    Responds to a database selection.
    """
    debug = False
    wx.BeginBusyCursor()
    db_choice_item = parent.db_choice_items[parent.drop_dbs.GetSelection()]
    db, dbe = extractDbDets(db_choice_item)
    # update globals - will be used in refresh ...
    mg.DBE_DEFAULT = dbe
    mg.DB_DEFAULTS[dbe] = db
    refresh_default_dbs_tbls(dbe, parent.default_dbs, parent.default_tbls)
    dbdetsobj = get_db_dets_obj(dbe, parent.default_dbs, parent.default_tbls, 
                                parent.con_dets, db)
    con, cur, dbs, tbls, flds, has_unique, idxs = dbdetsobj.get_db_dets()
    db = dbdetsobj.db
    tbl = dbdetsobj.tbl
    if debug:
        print(u"Db is: %s" % db)
        print(u"Tbl is: %s" % tbl)
    wx.EndBusyCursor()
    return dbe, db, con, cur, tbls, tbl, flds, has_unique, idxs

def refresh_tbl_dets(parent):
    "Reset table, fields, has_unique, and idxs after a table selection."
    wx.BeginBusyCursor()
    tbl = parent.tbls[parent.drop_tbls.GetSelection()]
    dbdetsobj = get_db_dets_obj(parent.dbe, parent.default_dbs, 
                         parent.default_tbls, parent.con_dets, parent.db, tbl)
    flds = dbdetsobj.get_tbl_flds(parent.cur, parent.db, tbl)
    has_unique, idxs = dbdetsobj.get_index_dets(parent.cur, parent.db, tbl)
    wx.EndBusyCursor()
    return tbl, flds, has_unique, idxs

def get_default_db_dets():
    """
    Returns con, cur, dbs, tbls, flds, has_unique, idxs from default
        SOFA SQLite database.
    """
    proj_dic = config_globals.get_settings_dic(subfolder=u"projs", 
                                        fil_name=mg.SOFA_DEFAULT_PROJ)
    dbdetsobj = get_db_dets_obj(dbe=mg.DBE_SQLITE, 
                                default_dbs=proj_dic["default_dbs"],
                                default_tbls=proj_dic["default_tbls"],
                                con_dets=proj_dic["con_dets"])
    con, cur, dbs, tbls, flds, has_unique, idxs = dbdetsobj.get_db_dets()
    return con, cur, dbs, tbls, flds, has_unique, idxs

def dup_tbl_name(tbl_name):
    """
    Duplicate name in default SQLite SOFA database?
    """
    con, unused, unused, tbls, unused, unused, unused = get_default_db_dets()
    con.close()
    return tbl_name in tbls

def make_flds_clause(config_data):
    """
    Create a clause ready to put in a select statement which takes into account
        original and new names if an existing field which has changed name. 
        Does not include the sofa_id.  NB a new field will only have a new name 
        so the orig name will be None.
    config_data -- dict with TBL_FLD_NAME, TBL_FLD_NAME_ORIG, TBL_FLD_TYPE,
        TBL_FLD_TYPE_ORIG. Includes row with sofa_id.
    """
    debug = False
    sqlite_quoter = get_obj_quoter_func(mg.DBE_SQLITE)
    # get orig_name, new_name tuples for all fields in final table apart 
    # from the sofa_id.
    orig_new_names = [(x[mg.TBL_FLD_NAME_ORIG], x[mg.TBL_FLD_NAME])
                       for x in config_data 
                       if x[mg.TBL_FLD_NAME_ORIG] != mg.SOFA_ID]
    if debug:
        print("config_data: %s" % config_data)
        print("orig_new_names: %s" % orig_new_names)
    fld_clause_items = []
    for orig_name, new_name in orig_new_names:
        qorig_name = sqlite_quoter(orig_name)
        qnew_name = sqlite_quoter(new_name)
        if orig_name is None:
            clause = u"NULL %s" % qnew_name
        elif orig_name == new_name:
            clause = u"%s" % qnew_name
        else:
            clause = u"%s %s" % (qorig_name, qnew_name)
        fld_clause_items.append(clause)
    fld_clause = u", ".join(fld_clause_items)
    return fld_clause

def get_oth_name_types(config_data):
    """
    Returns name, type tuples for all fields except for the sofa_id.
    config_data -- dict with TBL_FLD_NAME, TBL_FLD_NAME_ORIG, TBL_FLD_TYPE,
        TBL_FLD_TYPE_ORIG. Includes row with sofa_id.
    """
    oth_name_types = [(x[mg.TBL_FLD_NAME], x[mg.TBL_FLD_TYPE])
                            for x in config_data
                            if x[mg.TBL_FLD_NAME] != mg.SOFA_ID]
    return oth_name_types

def get_create_flds_txt(oth_name_types, strict_typing=False, inc_sofa_id=True):
    """
    Get text clause which defines fields for use in an SQLite create table 
        statement. The table will be created inside the default SOFA SQLite 
        database.  If the sofa_id is included, the text must define the sofa_id 
        as UNIQUE.
    oth_name_types -- ok_fld_name, fld_type.  Does not include sofa_id. The 
        sofa_id can be added below if required.
    strict_typing -- add check constraints to fields.
    """
    debug = False
    quoter = get_obj_quoter_func(mg.DBE_SQLITE)
    sofa_id = quoter(mg.SOFA_ID)
    if inc_sofa_id:
        fld_clause_items = [u"%s INTEGER PRIMARY KEY" % sofa_id]
    else:
        fld_clause_items = []
    for fld_name, fld_type in oth_name_types:
        if fld_name == mg.SOFA_ID:
            raise Exception, "Do not pass sofa_id into %s" % \
                sys._getframe().f_code.co_name
        if fld_name == "":
            raise Exception, ("Do not pass fields with empty string names into "
                              "%s" % sys._getframe().f_code.co_name)
        tosqlite = mg.GEN2SQLITE_DIC[fld_type]
        if strict_typing:
            check = tosqlite["check_clause"] % {"fld_name": quoter(fld_name)}
        else:
            check = ""
        if debug: print(u"%s %s %s" % (fld_name, fld_type, check))
        clause = u"%(fld_name)s %(fld_type)s %(check_clause)s" % \
                                            {"fld_name": quoter(fld_name), 
                                            "fld_type": tosqlite["sqlite_type"],
                                            "check_clause": check}
        fld_clause_items.append(clause)
    if inc_sofa_id:
        fld_clause_items.append(u"UNIQUE(%s)" % sofa_id)
    fld_clause = u", ".join(fld_clause_items)
    return fld_clause

def make_sofa_tbl(con, cur, tbl_name, oth_name_types, strict_typing=False):
    """
    Make a table into the SOFA default database.  Must have autonumber SOFA_ID.
    Optionally may apply type checking constraint on fields (NB no longer able
        to open database outside of this application which using user-defined
        functions in table definitions).
    oth_name_types -- [(ok_fld_name, fld_type), ...].  No need to reference 
        old names or types.
    strict_typing -- uses user-defined functions to apply strict typing via
        check clauses as part of create table statements.
    """
    debug = False
    fld_clause = get_create_flds_txt(oth_name_types, 
                                     strict_typing=strict_typing, 
                                     inc_sofa_id=True)
    SQL_make_tbl = u"""CREATE TABLE "%s" (%s)""" % (tbl_name, fld_clause)
    if debug: print(SQL_make_tbl)
    cur.execute(SQL_make_tbl)
    con.commit()
    if debug: print(u"Successfully created %s" % tbl_name)
     