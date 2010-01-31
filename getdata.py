from __future__ import print_function
import os
import pprint
import sys
import wx

import my_globals
import config_globals
import lib
import projects

debug = False

def get_db_dets_obj(dbe, default_dbs, default_tbls, con_dets, db=None, 
                    tbl=None):
    """
    Pass in all con_dets (the dbe will be used to select specific con_dets).
    """
    return my_globals.DBE_MODULES[dbe].DbDets(default_dbs, default_tbls, 
                                              con_dets, db, tbl)


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
    
    def getDbTbls(self, cur, db):
        "Must return tbls"
        assert 0, "Must define getDbTbls in subclass"
        
    def getTblFlds(self, cur, db, tbl):
        """
        Must return dic of dics called flds.
        Gets dic of dics for each field with field name as key. Each field dic
            has as keys the FLD_ variables listed in my_globals e.g. 
            FLD_BOLNUMERIC.
        Need enough to present fields in order, validate data entry, 
            and guide labelling and reporting (e.g. numeric or categorical).
        """
        assert 0, "Must define getTblFlds in subclass"
    
    def getIndexDets(self, cur, db, tbl):
        "Must return has_unique, idxs"
        assert 0, "Must define getIndexDets in subclass"
       
    def getDbDets(self):
        """
        Return connection, cursor, and get lists of databases, tables, fields, 
            and index info, based on the database connection details provided.
        Sets db and tbl if not supplied.
        Must return con, cur, dbs, tbls, flds, has_unique, idxs.
        dbs used to make dropdown of all dbe dbs (called more than once).
        """
        assert 0, "Must define getDbDets in subclass"

def make_fld_val_clause_non_numeric(fld_name, val, dbe_gte, quote_obj, 
                                    quote_val):
    debug = False
    clause = "%s %s %s" % (quote_obj(fld_name), dbe_gte, quote_val(val))
    if debug: print(clause)
    return clause
    
def make_fld_val_clause(dbe, flds, fld_name, val, gte=my_globals.GTE_EQUALS):
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
    bolsqlite = (dbe == my_globals.DBE_SQLITE)
    quote_obj = get_obj_quoter_func(dbe)
    quote_val = get_val_quoter_func(dbe)
    dbe_gte = get_gte(dbe, gte)
    bolnumeric = flds[fld_name][my_globals.FLD_BOLNUMERIC]
    boldatetime = flds[fld_name][my_globals.FLD_BOLDATETIME]
    if val is None:
        if gte == my_globals.GTE_EQUALS:
            clause = u"%s IS NULL" % quote_obj(fld_name)
        elif gte == my_globals.GTE_NOT_EQUALS:
            clause = u"%s IS NOT NULL" % quote_obj(fld_name)
        else:
            raise Exception, "Can only use = or " + \
                "%s with missing or Null values." % my_globals.GTE_NOT_EQUALS
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
    return my_globals.DBE_MODULES[dbe].quote_obj

def get_val_quoter_func(dbe):
    """
    Get appropriate function to wrap values e.g. the contents of a string field,
        in dbe-friendly way.
    """
    return my_globals.DBE_MODULES[dbe].quote_val

def get_placeholder(dbe):
    return my_globals.DBE_MODULES[dbe].placeholder

def get_gte(dbe, gte):
    if gte == my_globals.GTE_NOT_EQUALS:
        return my_globals.DBE_MODULES[dbe].gte_not_equals
    return gte

def get_dbe_syntax_elements(dbe):
    """
    Returns if_clause (a string), and 4 functions - quote_obj(), quote_val(), 
        get_placeholder(), and get_summable().
    if_clause receives 3 inputs - the test, result if true, result if false
    e.g. MySQL "IF(%s, %s, %s)"
    Sum and if statements are used to get frequencies in SOFA Statistics.
    """
    return my_globals.DBE_MODULES[dbe].get_syntax_elements()

def setDataConGui(parent, readonly, scroll, szr, lblfont):
    ""
    for dbe in my_globals.DBES:
        my_globals.DBE_MODULES[dbe].setDataConGui(parent, readonly, scroll, 
                                                   szr, lblfont)

def getProjConSettings(parent, proj_dic):
    "Get project connection settings"
    for dbe in my_globals.DBES:
        my_globals.DBE_MODULES[dbe].getProjSettings(parent, proj_dic)

def FldsDic2FldNamesLst(flds_dic):
    # pprint.pprint(flds_dic) # debug
    flds_lst = sorted(flds_dic, key=lambda s: flds_dic[s][my_globals.FLD_SEQ])
    return flds_lst

def setConDetDefaults(parent):
    """
    Check project connection settings to handle missing values and set 
        sensible defaults.
    """
    for dbe in my_globals.DBES:
        my_globals.DBE_MODULES[dbe].setConDetDefaults(parent)

def processConDets(parent, default_dbs, default_tbls, con_dets):
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
    for dbe in my_globals.DBES:
        # has_incomplete means started but some key detail(s) missing
        # has_con means all required details are completed
        has_incomplete, has_con = \
            my_globals.DBE_MODULES[dbe].processConDets(parent, default_dbs, 
                                                       default_tbls, con_dets)
        if has_incomplete:
            return True, None, completed_dbes
        if has_con:
            completed_dbes.append(dbe)
            any_cons = True
    return any_incomplete, any_cons, completed_dbes

def getDbItem(db_name, dbe):
    return u"%s (%s)" % (db_name, dbe)

def extractDbDets(choice_text):
    start_idx = choice_text.index(u"(") + 1
    end_idx = choice_text.index(u")")
    dbe = choice_text[start_idx:end_idx]
    db_name = choice_text[:start_idx - 2]
    return db_name, dbe

def PrepValue(dbe, val, fld_dic):
    """
    Prepare raw value for insertion/update via SQL.
    Missing (.) and None -> None.
    Any non-missing/null values in numeric fields are simply passed through.
    Values in datetime fields are returned as datetime strings (if valid) ready 
        to include in SQL.  If not valid, the faulty value is returned as is in 
        the knowledge that it will fail validation later (CellInvalid) and not
        actually be saved to a database (in db_grid.UpdateCell()).
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
        prep_val = my_globals.DBE_MODULES[dbe].PrepValue(val, fld_dic)
    except AttributeError:
        # the most common path
        if val in [None, my_globals.MISSING_VAL_INDICATOR]:
            val2use = None
        elif fld_dic[my_globals.FLD_BOLDATETIME]:
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

def InsertRow(dbe, con, cur, tbl_name, data):
    """
    Returns success (boolean) and message (None or error).
    data = [(value as string (or None), fld_dets), ...]
    """
    return my_globals.DBE_MODULES[dbe].InsertRow(con, cur, tbl_name, data)

def get_data_dropdowns(parent, panel, dbe, default_dbs, default_tbls, con_dets, 
                       dbs_of_default_dbe, db, tbls, tbl):
    """
    Adds dropDatabases and dropTables to frame with correct values 
        and default selection.  NB must have exact same names.
    Adds db_choice_items to parent.
    """
    debug = False
    # databases list needs to be tuple including dbe so can get both from 
    # sequence alone e.g. when identifying selection
    db_choices = [(x, dbe) for x in dbs_of_default_dbe]      
    dbes = my_globals.DBES[:]
    dbes.pop(dbes.index(dbe))
    for oth_dbe in dbes: # may not have any connection details
        oth_default_db = default_dbs.get(oth_dbe)
        dbdetsobj = get_db_dets_obj(oth_dbe, default_dbs, default_tbls, 
                                    con_dets, oth_default_db, None)
        try:
            unused, unused, oth_dbs, unused, unused, unused, unused = \
                dbdetsobj.getDbDets()
            oth_db_choices = [(x, oth_dbe) for x in oth_dbs]
            db_choices.extend(oth_db_choices)
        except Exception, e:
            if debug: print(unicode(e))
            pass # no connection possible
    parent.db_choice_items = [getDbItem(x[0], x[1]) for x in db_choices]
    parent.dropDatabases = wx.Choice(panel, -1, choices=parent.db_choice_items,
                                     size=(300, -1))
    parent.dropDatabases.Bind(wx.EVT_CHOICE, parent.OnDatabaseSel)
    dbs_lc = [x.lower() for x in dbs_of_default_dbe]
    parent.dropDatabases.SetSelection(dbs_lc.index(db.lower()))
    parent.dropTables = wx.Choice(panel, -1, choices=[], size=(300, -1))
    setup_drop_tbls(parent.dropTables, dbe, db, tbls, tbl)
    parent.dropTables.Bind(wx.EVT_CHOICE, parent.OnTableSel)
    return parent.dropDatabases, parent.dropTables

def setup_drop_tbls(dropTables, dbe, db, tbls, tbl):
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
    dropTables.SetItems(tbls_with_filts)
    try:
        dropTables.SetSelection(idx_tbl)
    except NameError:
        raise Exception, "Table \"%s\" not found in tables list" % self.tbl

def refresh_db_dets(parent):
    """
    Returns dbe, db, con, cur, tbls, tbl, flds, has_unique, idxs.
    Responds to a database selection.
    """
    debug = False
    wx.BeginBusyCursor()
    db_choice_item = parent.db_choice_items[parent.dropDatabases.GetSelection()]
    db, dbe = extractDbDets(db_choice_item)
    dbdetsobj = get_db_dets_obj(dbe, parent.default_dbs, parent.default_tbls, 
                                parent.con_dets, db)
    con, cur, dbs, tbls, flds, has_unique, idxs = dbdetsobj.getDbDets()
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
    tbl = parent.tbls[parent.dropTables.GetSelection()]
    dbdetsobj = get_db_dets_obj(parent.dbe, parent.default_dbs, 
                         parent.default_tbls, parent.con_dets, parent.db, tbl)
    flds = dbdetsobj.getTblFlds(parent.cur, parent.db, tbl)
    has_unique, idxs = dbdetsobj.getIndexDets(parent.cur, parent.db, tbl)
    wx.EndBusyCursor()
    return tbl, flds, has_unique, idxs

def GetDefaultDbDets():
    """
    Returns con, cur, dbs, tbls, flds, has_unique, idxs from default
        SOFA SQLite database.
    """
    proj_dic = config_globals.get_settings_dic(subfolder=u"projs", 
                                        fil_name=my_globals.SOFA_DEFAULT_PROJ)
    dbdetsobj = get_db_dets_obj(dbe=my_globals.DBE_SQLITE, 
                                default_dbs=proj_dic["default_dbs"],
                                default_tbls=proj_dic["default_tbls"],
                                con_dets=proj_dic["con_dets"])
    con, cur, dbs, tbls, flds, has_unique, idxs = dbdetsobj.getDbDets()
    return con, cur, dbs, tbls, flds, has_unique, idxs

def dup_tbl_name(tbl_name):
    """
    Duplicate name in default SQLite SOFA database?
    """
    con, unused, unused, tbls, unused, unused, unused = GetDefaultDbDets()
    con.close()
    return tbl_name in tbls

def make_select_renamed_flds_clause(orig_new_names):
    """
    Create a clause ready to put in a select statement which maps old to new 
        names as needed.
    orig_new_names -- [(orig_name, new_name), ...] where orig_name can be None.
    """
    debug = False
    sqlite_quoter = get_obj_quoter_func(my_globals.DBE_SQLITE)
    fld_clause_items = [my_globals.SOFA_ID]
    for orig_name, new_name in orig_new_names:
        if orig_name is None:
            clause = "NULL %s" % sqlite_quoter(new_name)
        elif orig_name == new_name:
            clause = "%s" % sqlite_quoter(new_name)
        else:
            clause = "%s %s" % (sqlite_quoter(orig_name), 
                                sqlite_quoter(new_name))
        fld_clause_items.append(clause)
    fld_clause = u", ".join(fld_clause_items)
    return fld_clause

def get_oth_name_types(config_data):
    oth_name_types = [(x[my_globals.TBL_FLD_NAME], x[my_globals.TBL_FLD_TYPE]) \
                            for x in config_data \
                            if x[my_globals.TBL_FLD_NAME] != my_globals.SOFA_ID]
    return oth_name_types

def get_create_flds_txt(oth_name_types, strict_typing=False):
    """
    Get text clause for use in an SQLite SQL create table statement which 
        defines _all_ the fields i.e. must include the sofa_id.  Because the 
        table will be created inside the default SOFA SQLite database, the text 
        must also define the sofa_id as UNIQUE.
    oth_name_types -- fld_name, fld_type.  Must NOT include sofa_id.  This will 
        be added automatically.
    strict_typing -- add check constraints to fields.
    """
    debug = False
    quoter = get_obj_quoter_func(my_globals.DBE_SQLITE)
    fld_clause_items = [u"%s INTEGER PRIMARY KEY" % quoter(my_globals.SOFA_ID)]
    for fld_name, fld_type in oth_name_types:
        if fld_name == my_globals.SOFA:
            raise Exception, "Do not pass sofa_id into %s" % \
                sys._getframe().f_code.co_name
        if fld_name == "":
            raise Exception, ("Do not pass fields with empty string names into "
                              "%s" % sys._getframe().f_code.co_name)
        tosqlite = my_globals.GEN2SQLITE_DIC[fld_type]
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
    fld_clause_items.append(u"UNIQUE(%s)" % quoter(my_globals.SOFA_ID))
    fld_clause = u", ".join(fld_clause_items)
    return fld_clause

def make_sofa_tbl(con, cur, tbl_name, oth_name_types, strict_typing=False):
    """
    Make a table into the SOFA default database.  Must have autonumber SOFA_ID.
    Optionally may apply type checking constraint on fields (NB no longer able
        to open database outside of this application which using user-defined
        functions in table definitions).
    name_types -- [(fld_name, fld_type), ...].  No need to reference old names 
        or types.
    strict_typing -- uses user-defined functions to apply strict typing via
        check clauses as part of create table statements.
    """
    debug = False
    fld_clause = get_create_flds_txt(oth_name_types, strict_typing)
    SQL_make_tbl = u"""CREATE TABLE "%s" (%s)""" % (tbl_name, fld_clause)
    if debug: print(SQL_make_tbl)
    cur.execute(SQL_make_tbl)
    con.commit()
    if debug: print(u"Successfully created %s" % tbl_name)  