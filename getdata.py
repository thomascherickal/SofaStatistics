import os
import pprint
import wx

import util

# must be before dbe import statements (they have classes based on DbDets)
class DbDets(object):
    
    def __init__ (self, conn_dets, db=None, tbl=None):
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
            has as keys the FLD_ variables listed below e.g. FLD_BOLNUMERIC.
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
# also used as labels in dropdowns
DBE_SQLITE = "SQLite"
DBE_MYSQL = "MySQL"
DBE_MS_ACCESS = "MS Access"
def import_dbe_plugin(dbe_plugin):
    if dbe_plugin == DBE_SQLITE:
        import dbe_plugins.dbe_sqlite as dbe_sqlite
        mod = dbe_sqlite
    elif dbe_plugin == DBE_MYSQL:
        import dbe_plugins.dbe_mysql as dbe_mysql
        mod = dbe_mysql
    elif dbe_plugin == DBE_MS_ACCESS:
        import dbe_plugins.dbe_ms_access as dbe_ms_access
        mod = dbe_ms_access
    return mod
DBES = []
DBE_MODULES = {}
DBE_PLUGINS = [(DBE_SQLITE, "dbe_sqlite"), (DBE_MYSQL, "dbe_mysql"), 
               (DBE_MS_ACCESS, "dbe_ms_access")]
for dbe_plugin, dbe_mod_name in DBE_PLUGINS:
    dbe_plugin_mod = os.path.join(util.get_script_path(), "dbe_plugins", 
                                   "%s.py" % dbe_mod_name)
    if os.path.exists(dbe_plugin_mod):
        if not (not util.in_windows() and dbe_plugin == DBE_MS_ACCESS):
            DBES.append(dbe_plugin)
            dbe_mod = import_dbe_plugin(dbe_plugin)
            DBE_MODULES[dbe_plugin] = dbe_mod
# misc field dets
FLD_SEQ = "field sequence"
FLD_BOLNULLABLE = "field nullable"
FLD_DATA_ENTRY_OK = "data entry ok" # e.g. not autonumber, timestamp etc
FLD_COLUMN_DEFAULT = "field default"
# test
FLD_BOLTEXT = "field text"
FLD_TEXT_LENGTH = "field text length"
FLD_CHARSET = "field charset"
# numbers
FLD_BOLNUMERIC = "field numeric"
FLD_BOLAUTONUMBER = "field autonumber"
FLD_DECPTS = "field decpts"
FLD_NUM_WIDTH = "field numeric display width" # used for column display only
FLD_BOL_NUM_SIGNED = "field numeric signed"
FLD_NUM_MIN_VAL = "field numeric minimum value"
FLD_NUM_MAX_VAL = "field numeric maximum value"
# datetime
FLD_BOLDATETIME = "field datetime"
# indexes
IDX_NAME = "index name"
IDX_IS_UNIQUE = "index is unique"
IDX_FLDS = "index fields"

def getDbDetsObj(dbe, conn_dets, db, tbl):
    return DBE_MODULES[dbe].DbDets(conn_dets, db, tbl)

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
    flds_lst = sorted(flds_dic, key=lambda s: flds_dic[s][FLD_SEQ])
    return flds_lst

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

def InsertRow(dbe, conn, cur, tbl_name, data):
    """
    data = [(value as string, fld_dets), ...]
    """
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
    