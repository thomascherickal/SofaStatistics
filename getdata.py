import os
import pprint
import wx

import my_globals
import util

# must be before dbe import statements (they have classes based on DbDets)
class DbDets(object):
    
    def __init__ (self, conn_dets, db=None, tbl=None):
        """
        If db or tbl are none, subclasses must select one e.g. the first.
        """
        self.conn_dets = conn_dets
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
        "Must return conn, cur, dbs, tbls, flds"
        assert 0, "Must define getDbDets in subclass"

"""
Include database engine in system if in dbe_plugins folder and os-appropriate.
"""
def import_dbe_plugin(dbe_plugin):
    if dbe_plugin == my_globals.DBE_SQLITE:
        import dbe_plugins.dbe_sqlite as dbe_sqlite
        mod = dbe_sqlite
    elif dbe_plugin == my_globals.DBE_MYSQL:
        import dbe_plugins.dbe_mysql as dbe_mysql
        mod = dbe_mysql
    elif dbe_plugin == my_globals.DBE_MS_ACCESS:
        import dbe_plugins.dbe_ms_access as dbe_ms_access
        mod = dbe_ms_access
    elif dbe_plugin == my_globals.DBE_MS_SQL:
        import dbe_plugins.dbe_ms_sql as dbe_ms_sql
        mod = dbe_ms_sql
    return mod
DBES = []
DBE_MODULES = {}
DBE_PLUGINS = [(my_globals.DBE_SQLITE, "dbe_sqlite"), 
               (my_globals.DBE_MYSQL, "dbe_mysql"), 
               (my_globals.DBE_MS_ACCESS, "dbe_ms_access"), 
               (my_globals.DBE_MS_SQL, "dbe_ms_sql"),]
for dbe_plugin, dbe_mod_name in DBE_PLUGINS:
    for_win_yet_not_win = not util.in_windows() and \
        dbe_plugin in [my_globals.DBE_MS_ACCESS, my_globals.DBE_MS_SQL]
    dbe_plugin_mod = os.path.join(os.path.dirname(__file__), "dbe_plugins", 
                                   "%s.py" % dbe_mod_name)
    if os.path.exists(dbe_plugin_mod):
        if not for_win_yet_not_win: # i.e. OK to add module
            DBES.append(dbe_plugin)
            dbe_mod = import_dbe_plugin(dbe_plugin)
            DBE_MODULES[dbe_plugin] = dbe_mod


def get_obj_quoter_func(dbe):
    """
    Get appropriate function to wrap content e.g. table or field name, 
        in dbe-friendly way.
    """
    return DBE_MODULES[dbe].quote_obj

def get_val_quoter_func(dbe):
    """
    Get appropriate function to wrap values e.g. the contents of a string field,
        in dbe-friendly way.
    """
    return DBE_MODULES[dbe].quote_val

def getDbDetsObj(dbe, conn_dets, db=None, tbl=None):
    """
    Pass in all conn_dets (the dbe will be used to select specific conn_dets).
    """
    return DBE_MODULES[dbe].DbDets(conn_dets, db, tbl)

def setDbInConnDets(dbe, conn_dets, db):
    "Set database in connection details (if appropriate)"
    DBE_MODULES[dbe].setDbInConnDets(conn_dets, db)
    
def getDbeSyntaxElements(dbe):
    """
    Returns if_clause, abs_wrapper_l, abs_wrapper_r - all strings.
    if_clause receives 3 inputs - the test, result if true, result if false
    e.g. MySQL "IF(%s, %s, %s)"
    """
    return DBE_MODULES[dbe].DbeSyntaxElements()

def setDataConnGui(parent, read_only, scroll, szr, lblfont):
    ""
    for dbe in DBES:
        DBE_MODULES[dbe].setDataConnGui(parent, read_only, scroll, szr, 
                                        lblfont)

def getProjConnSettings(parent, proj_dic):
    "Get project connection settings"
    for dbe in DBES:
        DBE_MODULES[dbe].getProjSettings(parent, proj_dic)

def FldsDic2FldNamesLst(flds_dic):
    # pprint.pprint(flds_dic) # debug
    flds_lst = sorted(flds_dic, key=lambda s: flds_dic[s][my_globals.FLD_SEQ])
    return flds_lst

def getChoiceItem(item_labels, item_val):
    str_val = str(item_val)
    return "%s (%s)" % (item_labels.get(item_val, str_val.title()), str_val)

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

def getSortedChoiceItems(dic_labels, vals):
    """
    dic_labels - could be for either variables of values.
    vals - either variables or values.
    Returns choice_items_sorted.
    """
    choice_items = [getChoiceItem(dic_labels, x) for x in vals]
    choice_items.sort(key=lambda s: s.upper())
    return choice_items

def setConnDetDefaults(parent):
    """
    Check project connection settings to handle missing values and set 
        sensible defaults.
    """
    for dbe in DBES:
        DBE_MODULES[dbe].setConnDetDefaults(parent)

def processConnDets(parent, default_dbs, default_tbls, conn_dets):
    """
    Populate default_dbs, default_tbls, conn_dets.
    Returns any_incomplete (partially completed connection details), 
        any_conns (any of them set completely), and completed_dbes.
        Completed_dbes is so we can ensure the default dbe has conn details 
        set for it.
    NB If any incomplete, stop processing and return None for any_conns.
    """
    any_incomplete = False
    any_conns = False
    completed_dbes = [] # so can check the default dbe has details set
    for dbe in DBES:
        # has_incomplete means started but some key detail(s) missing
        # has_conn means all required details are completed
        has_incomplete, has_conn = \
            DBE_MODULES[dbe].processConnDets(parent, default_dbs, 
                                             default_tbls, conn_dets)
        if has_incomplete:
            return True, None
        if has_conn:
            completed_dbes.append(dbe)
            any_conns = True
    return any_incomplete, any_conns, completed_dbes

def getDbItem(db_name, dbe):
    return "%s (%s)" % (db_name, dbe)

def extractDbDets(choice_text):
    start_idx = choice_text.index("(") + 1
    end_idx = choice_text.index(")")
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
        prep_val = DBE_MODULES[dbe].PrepValue(val, fld_dic)
    except AttributeError:
        debug = False
        if val in [None, "."]: # TODO - use a const without having to import db_tbl
            val2use = None
        elif fld_dic[my_globals.FLD_BOLDATETIME]:
            if val == "":
                val2use = None
            else:
                valid_datetime, timeobj = util.valid_datetime_str(val)
                if not valid_datetime:
                    # will not execute successfully
                    if debug: print "%s is not a valid datetime"
                    val2use = val
                else:
                    if debug: print timeobj
                    # might as well store in same way as MySQL
                    val2use = util.timeobj_to_datetime_str(timeobj)
        else:
            val2use = val
        if debug: print val2use
        prep_val = val2use
    return prep_val

def InsertRow(dbe, conn, cur, tbl_name, data):
    "data = [(value as string (or None), fld_dets), ...]"
    return DBE_MODULES[dbe].InsertRow(conn, cur, tbl_name, data)

def setupDataDropdowns(parent, panel, dbe, conn_dets, default_dbs, 
                       default_tbls):
    """
    Sets up frame with the following properties: dbe, conn_dets, conn, cur, 
        default_dbs, default_db (possibly None), db (default db if possible), 
        db_choice_items, tbls (for selected db), default_tbl, 
        and tbl_name (default if possible).  Plus flds, has_unique and idxs.
    Adds dropDatabases and dropTables to frame with correct values 
        and default selection.
    """    
    parent.dbe = dbe
    parent.conn_dets = conn_dets
    parent.default_dbs = default_dbs
    if not parent.default_dbs:
        parent.default_dbs = []
        default_db = None
    else:
        default_db = parent.default_dbs.get(parent.dbe)
    parent.default_tbls = default_tbls
    if not default_tbls:
        parent.default_tbls = []
        parent.default_tbl = None
    else:
        parent.default_tbl = parent.default_tbls.get(parent.dbe)
    # for default dbe, get default tbl (or first) and its fields
    # for each other dbe, need to get database details to add to list
    parent.conn, parent.cur, default_dbe_dbs, parent.tbls, parent.flds, \
            parent.has_unique, parent.idxs = \
        getDbDetsObj(parent.dbe, parent.conn_dets, db=default_db, 
                     tbl=parent.default_tbl).getDbDets()
    # databases list needs to be tuple including dbe so can get both from 
    # sequence alone e.g. when identifying selection
    db_choices = [(x, parent.dbe) for x in default_dbe_dbs]      
    dbes = DBES[:]
    dbes.pop(dbes.index(parent.dbe))
    for oth_dbe in dbes: # may not have any connection details
        oth_default_db = parent.default_dbs.get(oth_dbe)
        dbdetsobj = getDbDetsObj(oth_dbe, parent.conn_dets, 
                                 oth_default_db, None)
        try:
            _, _, oth_dbs, _, _, _, _ = dbdetsobj.getDbDets()
            oth_db_choices = [(x, oth_dbe) for x in oth_dbs]
            db_choices.extend(oth_db_choices)
        except Exception, e:
            print str(e)
            pass # no connection possible            
    parent.db = default_db if default_db else default_dbe_dbs[0]
    parent.tbl_name = parent.default_tbl if parent.default_tbl \
        else parent.tbls[0]
    parent.db_choice_items = [getDbItem(x[0], x[1]) for x in db_choices]
    parent.dropDatabases = wx.Choice(panel, -1, 
                                     choices=parent.db_choice_items)
    if default_db:
        # should be correct index if same sort order on choice items 
        # as db list
        dbs = [x[0] for x in db_choices]
        try:
            parent.dropDatabases.SetSelection(dbs.index(default_db))
        except Exception:
            pass # perhaps the default table is not in the default database ;-)
    else:
        # first database of default dbe (which was always first)
        parent.dropDatabases.SetSelection(n=0)
    parent.dropTables = wx.Choice(panel, -1, choices=parent.tbls)
    try:
        idx_default_tbl = parent.tbls.index(parent.default_tbl)
        parent.dropTables.SetSelection(idx_default_tbl)
    except Exception:
        parent.dropTables.SetSelection(n=0)

def ResetDataAfterDbSel(parent):
    """
    Reset dbe, database, cursor, tables, table, tables dropdown, 
        fields, has_unique, and idxs after a database selection.
    """
    db_choice_item = parent.db_choice_items[parent.dropDatabases.GetSelection()]
    db_name, dbe = extractDbDets(db_choice_item)
    parent.dbe = dbe
    parent.db = db_name
    default_tbl = parent.default_tbls.get(parent.dbe) 
    # for default dbe, get default tbl (or first) and its fields
    # for each other dbe, need to get database details to add to list
    dbdetsobj = getDbDetsObj(parent.dbe, parent.conn_dets, db=db_name, 
                             tbl=default_tbl)
    parent.conn, parent.cur, sel_dbe_dbs, parent.tbls, parent.flds, \
            parent.has_unique, parent.idxs = \
        dbdetsobj.getDbDets()
    default_tbl = parent.tbls[0] # default condition
    if parent.default_tbls and parent.default_dbs:
        if parent.db == parent.default_dbs[parent.dbe]:
            default_tbl = parent.default_tbls.get(parent.dbe)
    parent.tbl_name = default_tbl
    parent.dropTables.SetItems(parent.tbls)
    parent.dropTables.SetSelection(parent.tbls.index(default_tbl))
    parent.flds = dbdetsobj.getTblFlds(parent.cur, parent.db, parent.tbl_name)

def ResetDataAfterTblSel(parent):
    "Reset table, fields, has_unique, and idxs after a table selection."
    parent.tbl_name = parent.tbls[parent.dropTables.GetSelection()]
    dbdetsobj = getDbDetsObj(parent.dbe, parent.conn_dets, parent.db, 
                             parent.tbl_name)
    parent.flds = dbdetsobj.getTblFlds(parent.cur, parent.db, parent.tbl_name)
    parent.has_unique, parent.idxs = dbdetsobj.getIndexDets(parent.cur, 
                                                parent.db, parent.tbl_name)    
    