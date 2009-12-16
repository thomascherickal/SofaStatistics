from __future__ import print_function
import os
import pprint
import wx

import my_globals
import projects
import util

debug = False

def getDbDetsObj(dbe, default_dbs, default_tbls, con_dets, db=None, tbl=None):
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
    return my_globals.DBE_MODULES[dbe].get_placeholder()

def getDbeSyntaxElements(dbe):
    """
    Returns if_clause (a string), and 4 functions - quote_obj(), quote_val(), 
        get_placeholder(), and get_summable().
    if_clause receives 3 inputs - the test, result if true, result if false
    e.g. MySQL "IF(%s, %s, %s)"
    Sum and if statements are used to get frequencies in SOFA Statistics.
    """
    return my_globals.DBE_MODULES[dbe].DbeSyntaxElements()

def setDataConGui(parent, read_only, scroll, szr, lblfont):
    ""
    for dbe in my_globals.DBES:
        my_globals.DBE_MODULES[dbe].setDataConGui(parent, read_only, scroll, 
                                                   szr, lblfont)

def getProjConSettings(parent, proj_dic):
    "Get project connection settings"
    for dbe in my_globals.DBES:
        my_globals.DBE_MODULES[dbe].getProjSettings(parent, proj_dic)

def FldsDic2FldNamesLst(flds_dic):
    # pprint.pprint(flds_dic) # debug
    flds_lst = sorted(flds_dic, key=lambda s: flds_dic[s][my_globals.FLD_SEQ])
    return flds_lst

def get_choice_item(item_labels, item_val):
    val_label = util.any2unicode(item_val)
    return u"%s (%s)" % (item_labels.get(item_val, val_label.title()), 
                         val_label)

def extractChoiceDets(choice_text):
    """
    Extract name, label from item e.g. return "gender"
        and "Gender" from "Gender (gender)".
    Returns as string (even if original was a number etc).
    If not in this format, e.g. special col measures label, handle differently.
    """
    try:
        start_idx = choice_text.index("(") + 1
        end_idx = choice_text.index(")")
        item_val = choice_text[start_idx:end_idx]
        item_label = choice_text[:start_idx - 2]
    except Exception:
        item_val = choice_text
        item_label = choice_text        
    return item_val, item_label

def get_sorted_choice_items(dic_labels, vals):
    """
    Sorted by label, not name.
    dic_labels - could be for either variables of values.
    vals - either variables or values.
    Returns choice_items_sorted, orig_items_sorted.
    http://www.python.org/doc/faq/programming/#i-want-to-do-a-complicated- ...
        ... sort-can-you-do-a-schwartzian-transform-in-python
    """
    sorted_vals = vals
    sorted_vals.sort(key=lambda s: get_choice_item(dic_labels, s).upper())
    choice_items = [get_choice_item(dic_labels, x) for x in sorted_vals]
    return choice_items, sorted_vals

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
    Prepare raw value e.g. datetime, for insertion/update via SQL
    NB accepts faulty datettime formats and will create faulty SQL.
    Validation happens later and if it fails, the SQL will never run.
    """
    try:
        prep_val = my_globals.DBE_MODULES[dbe].PrepValue(val, fld_dic)
    except AttributeError:
        debug = False
        if val in [None, u"."]: # TODO - use a const without having to import db_tbl
            val2use = None
        elif fld_dic[my_globals.FLD_BOLDATETIME]:
            if val == u"":
                val2use = None
            else:
                valid_datetime, timeobj = util.valid_datetime_str(val)
                if not valid_datetime:
                    # will not execute successfully
                    if debug: print(u"%s is not a valid datetime")
                    val2use = val
                else:
                    if debug: print(timeobj)
                    # might as well store in same way as MySQL
                    val2use = util.timeobj_to_datetime_str(timeobj)
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

def setup_data_dropdowns(parent, panel, dbe, default_dbs, default_tbls, 
                         con_dets, dbs_of_default_dbe, db, tbls, tbl):
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
        dbdetsobj = getDbDetsObj(oth_dbe, default_dbs, default_tbls, con_dets, 
                                 oth_default_db, None)
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
    parent.dropTables = wx.Choice(panel, -1, choices=tbls, size=(300, -1))
    parent.dropTables.Bind(wx.EVT_CHOICE, parent.OnTableSel)
    tbls_lc = [x.lower() for x in tbls]
    parent.dropTables.SetSelection(tbls_lc.index(tbl.lower()))
    return parent.dropDatabases, parent.dropTables

def refresh_db_dets(parent):
    """
    Returns dbe, db, con, cur, tbls, tbl, flds, has_unique, idxs.
    Responds to a database selection.
    """
    debug = False
    wx.BeginBusyCursor()
    db_choice_item = parent.db_choice_items[parent.dropDatabases.GetSelection()]
    db, dbe = extractDbDets(db_choice_item)
    dbdetsobj = getDbDetsObj(dbe, parent.default_dbs, parent.default_tbls, 
                             parent.con_dets, db)
    con, cur, dbs, tbls, flds, has_unique, idxs = dbdetsobj.getDbDets()
    db = dbdetsobj.db
    tbl = dbdetsobj.tbl
    if debug:
        print(u"Db is: %s" % db)
        print(u"Tbl is: %s" % tbl)
    wx.EndBusyCursor()
    return dbe, db, con, cur, tbls, tbl, flds, has_unique, idxs

def RefreshTblDets(parent):
    "Reset table, fields, has_unique, and idxs after a table selection."
    wx.BeginBusyCursor()
    tbl = parent.tbls[parent.dropTables.GetSelection()]
    dbdetsobj = getDbDetsObj(parent.dbe, parent.default_dbs, 
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
    proj_dic = projects.GetProjSettingsDic(my_globals.SOFA_DEFAULT_PROJ)
    dbdetsobj = getDbDetsObj(dbe=my_globals.DBE_SQLITE, 
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

def make_create_tbl_fld_clause(name_types, strict_typing=False):
    """
    Make clause for defining fields in default SOFA SQLite database.
    Starts with autonumber SOFA_ID.
    """
    debug = False
    sqlite_quoter = get_obj_quoter_func(my_globals.DBE_SQLITE)
    fld_clause_items = [u"%s INTEGER PRIMARY KEY" % \
                        sqlite_quoter(my_globals.SOFA_ID)]
    for fld_name, fld_type in name_types:
        tosqlite = my_globals.GEN2SQLITE_DIC[fld_type]
        if strict_typing:
            check = tosqlite["check_clause"] % \
                {"fld_name": sqlite_quoter(fld_name)}
        else:
            check = ""
        if debug: 
            print(u"%s %s %s" % (fld_name, fld_type, check))
        clause = u"%(fld_name)s %(fld_type)s %(check_clause)s" % \
                            {"fld_name": sqlite_quoter(fld_name), 
                            "fld_type": tosqlite["sqlite_type"],
                            "check_clause": check}
        fld_clause_items.append(clause)
    fld_clause_items.append(u"UNIQUE(%s)" % sqlite_quoter(my_globals.SOFA_ID))
    fld_clause = u", ".join(fld_clause_items)
    return fld_clause

def make_sofa_tbl(con, cur, tbl_name, name_types, strict_typing=False):
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
    fld_clause = make_create_tbl_fld_clause(name_types, strict_typing)
    SQL_make_tbl = u"""CREATE TABLE "%s" (%s)""" % (tbl_name, fld_clause)
    if debug: print(SQL_make_tbl)
    cur.execute(SQL_make_tbl)
    con.commit()
    if debug: print(u"Successfully created %s" % tbl_name)  