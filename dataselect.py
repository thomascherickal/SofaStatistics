
from __future__ import print_function

import wx
import sys
import pprint

import my_globals
import db_grid
import dbe_plugins.dbe_sqlite as dbe_sqlite
import getdata
import projects
import table_config


class DataSelectDlg(wx.Dialog):
    def __init__(self, parent, proj_name):
        title = "Data in \"%s\" Project" % proj_name
        wx.Dialog.__init__(self, parent=parent, title=title, 
                           style=wx.CAPTION|wx.CLOSE_BOX|
                           wx.SYSTEM_MENU, pos=(300, 100))
        self.parent = parent
        self.panel = wx.Panel(self)
        lblfont = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD)
        self.szrMain = wx.BoxSizer(wx.VERTICAL)
        lblChoose = wx.StaticText(self.panel, -1, 
                                  "Choose an existing data table ...")
        proj_dic = projects.GetProjSettingsDic(proj_name=proj_name)
        self.var_labels, self.var_notes, self.var_types, self.val_dics = \
            projects.GetVarDets(proj_dic["fil_var_dets"])
        self.dbe = proj_dic["default_dbe"]
        self.conn_dets = proj_dic["conn_dets"]
        self.default_dbs = proj_dic["default_dbs"] \
            if proj_dic["default_dbs"] else {}
        self.default_tbls = proj_dic["default_tbls"] \
            if proj_dic["default_tbls"] else {}
        # get various db settings
        dbdetsobj = getdata.getDbDetsObj(self.dbe, self.default_dbs, 
                                         self.default_tbls, self.conn_dets)
        (self.conn, self.cur, self.dbs, self.tbls, self.flds, self.has_unique,  
                self.idxs) = dbdetsobj.getDbDets()
        # set up self.dropDatabases and self.dropTables
        self.db = dbdetsobj.db
        self.tbl = dbdetsobj.tbl
        getdata.setupDataDropdowns(self, self.panel, self.dbe, self.default_dbs, 
                                   self.default_tbls, self.conn_dets, 
                                   self.dbs, self.db, self.tbls, self.tbl)
        self.dropDatabases.Bind(wx.EVT_CHOICE, self.OnDatabaseSel)
        self.dropTables.Bind(wx.EVT_CHOICE, self.OnTableSel)
        self.chkReadOnly = wx.CheckBox(self.panel, -1, "Read Only")
        self.chkReadOnly.SetValue(True)
        btnOpen = wx.Button(self.panel, wx.ID_OPEN)
        btnOpen.Bind(wx.EVT_BUTTON, self.OnOpen)
        self.btnDesign = wx.Button(self.panel, -1, "Design")
        self.btnDesign.Bind(wx.EVT_BUTTON, self.OnDesign)
        szrData = wx.FlexGridSizer(rows=2, cols=2, hgap=5, vgap=5)  
        szrData.AddGrowableCol(1, 1)      
        lblDbs = wx.StaticText(self.panel, -1, "Databases:")
        lblDbs.SetFont(lblfont)        
        szrData.Add(lblDbs, 0, wx.RIGHT, 5)
        szrData.Add(self.dropDatabases, 0)
        self.dropDatabases.Bind(wx.EVT_CHOICE, self.OnDatabaseSel)        
        lblTbls = wx.StaticText(self.panel, -1, "Data tables:")
        lblTbls.SetFont(lblfont)
        szrData.Add(lblTbls, 0, wx.RIGHT, 5)
        szrData.Add(self.dropTables, 1)        
        szrExistingBottom = wx.BoxSizer(wx.HORIZONTAL)
        szrExistingBottom.Add(self.chkReadOnly, 1, wx.TOP|wx.LEFT, 5)
        szrExistingBottom.Add(self.btnDesign, 0, wx.RIGHT, 10)
        szrExistingBottom.Add(btnOpen, 0)
        bxExisting = wx.StaticBox(self.panel, -1, "Existing data tables")
        szrExisting = wx.StaticBoxSizer(bxExisting, wx.VERTICAL)
        szrExisting.Add(szrData, 0, wx.GROW|wx.ALL, 10)
        szrExisting.Add(szrExistingBottom, 0, wx.GROW|wx.ALL, 10)        
        bxNew = wx.StaticBox(self.panel, -1, "")
        szrNew = wx.StaticBoxSizer(bxNew, wx.HORIZONTAL)
        lblMakeNew = wx.StaticText(self.panel, -1, "... or make a new data table")
        btnMakeNew = wx.Button(self.panel, wx.ID_NEW)
        btnMakeNew.Bind(wx.EVT_BUTTON, self.OnNewClick)
        szrNew.Add(lblMakeNew, 1, wx.GROW|wx.ALL, 10)
        szrNew.Add(btnMakeNew, 0, wx.ALL, 10)
        self.lblFeedback = wx.StaticText(self.panel, -1, "")
        btnClose = wx.Button(self.panel, wx.ID_CLOSE)
        btnClose.Bind(wx.EVT_BUTTON, self.OnClose)
        szrBottom = wx.BoxSizer(wx.HORIZONTAL)
        self.szrButtons = wx.BoxSizer(wx.HORIZONTAL)
        self.szrButtons.Add(self.lblFeedback, 1, wx.GROW|wx.ALL, 10)
        self.szrButtons.Add(btnClose, 0, wx.RIGHT)
        szrBottom.Add(self.szrButtons, 1, wx.GROW|wx.RIGHT, 15) # align with New        
        self.szrMain.Add(lblChoose, 0, wx.ALL, 10)
        self.szrMain.Add(szrExisting, 1, wx.LEFT|wx.BOTTOM|wx.RIGHT|wx.GROW, 10)
        self.szrMain.Add(szrNew, 0, wx.GROW|wx.LEFT|wx.BOTTOM|wx.RIGHT, 10)
        self.szrMain.Add(szrBottom, 0, wx.GROW|wx.ALL, 10)
        self.panel.SetSizer(self.szrMain)
        self.szrMain.SetSizeHints(self)
        self.Layout()
        self._DesignButtonEnablement()

    def AddFeedback(self, feedback):
        self.lblFeedback.SetLabel(feedback)
        wx.Yield()
    
    def _DesignButtonEnablement(self):
        """
        Can only open dialog for design details for tables in the default SOFA 
            database (except for the default one).
        """
        self.btnDesign.Enable(self.dbe == my_globals.DBE_SQLITE
                              and self.db == my_globals.SOFA_DEFAULT_DB
                              and self.tbl != my_globals.SOFA_DEFAULT_TBL)       
        
    def OnDatabaseSel(self, event):
        (self.dbe, self.db, self.cur, self.tbls, self.tbl, self.flds, 
                self.has_unique, self.idxs) = getdata.RefreshDbDets(self)
        self.ResetTblDropdown()
        self._DesignButtonEnablement()
        
    def ResetTblDropdown(self):
        self.dropTables.SetItems(self.tbls)
        tbls_lc = [x.lower() for x in self.tbls]
        self.dropTables.SetSelection(tbls_lc.index(self.tbl.lower()))
    
    def OnTableSel(self, event):
        "Reset key data details after table selection."       
        self.tbl, self.flds, self.has_unique, self.idxs = \
            getdata.RefreshTblDets(self)
        self._DesignButtonEnablement()
    
    def OnOpen(self, event):
        ""
        if not self.has_unique:
            wx.MessageBox("Table \"%s\" cannot be opened because it " % \
              self.tbl + \
              "lacks a unique index") # needed for caching even if read only
        else:
            wx.BeginBusyCursor()
            readonly = self.chkReadOnly.IsChecked()
            dlg = db_grid.TblEditor(self, self.dbe, self.conn, 
                                    self.cur, self.db, self.tbl, 
                                    self.flds, self.var_labels, self.idxs,
                                    readonly)
            wx.EndBusyCursor()
            dlg.ShowModal()
        event.Skip()
    
    def _getGenFldType(self, fld_type):
        """
        Get general field type from specific.
        """
        if fld_type.lower() in dbe_sqlite.NUMERIC_TYPES:
            gen_fld_type = my_globals.CONF_NUMERIC
        elif fld_type.lower() in dbe_sqlite.DATE_TYPES:
            gen_fld_type = my_globals.CONF_DATE
        else:
            gen_fld_type = my_globals.CONF_STRING
        return gen_fld_type
    
    def _getTableConfig(self, tbl_name):
        """
        Get ordered list of field names and field types for named table.
        "Numeric", "Date", "String".
        Only works for an SQLite database (should be the default one).
        """
        self.cur.execute("PRAGMA table_info(%s)" % tbl_name)
        table_config = [(x[1], self._getGenFldType(fld_type=x[2])) for x in
                         self.cur.fetchall()]
        return table_config
    
    def OnDesign(self, event):
        """
        Open table config which reads values for the table.
        NB only enabled (for either viewing or editing) for the default SQLite 
            database.
        """
        tbl_name_lst = [self.tbl,]
        data = self._getTableConfig(self.tbl)
        new_grid_data = [] # not allowing change so not used
        
        if not self.chkReadOnly.IsChecked():
            wx.MessageBox("Version %s of " % my_globals.VERSION +
                "SOFA Statistics does not allow users to modify the design " +
                "of existing databases.")
            return
        
        # readonly = self.chkReadOnly.IsChecked() # only make live when can cope 
        # with editing changes
        readonly = True
        
        dlgConfig = table_config.ConfigTable(tbl_name_lst, data, new_grid_data, 
                                             readonly)
        ret = dlgConfig.ShowModal()
    
    def OnNewClick(self, event):
        """
        Get table name (must be unique etc), create empty table in SOFA Default 
            database with that name, and start off with 5 fields ready to 
            rename.  Must be able to add fields, and rename fields.
        """
        debug = False
        tbl_name_lst = [] # not quite worth using validator mechanism ;-)
        data = [("var001", "Numeric")]
        new_grid_data = []
        dlgConfig = table_config.ConfigTable(tbl_name_lst, data, new_grid_data)
        ret = dlgConfig.ShowModal()
        if ret != wx.ID_OK:
            event.Skip()
            return
        # Make new table.  Include unique index on special field prepended as
        # with data imported.
        # Only interested in SQLite when making a fresh SOFA table
        tbl_name = tbl_name_lst[0]
        fld_clause_items = ["sofa_id INTEGER PRIMARY KEY"]
        gen2sqlite_dic = {my_globals.CONF_NUMERIC: "REAL",
                          my_globals.CONF_STRING: "TEXT",
                          my_globals.CONF_DATE: "DATETIME",
                          }
        for fld_name, fld_type in new_grid_data:
            if debug: print("%s %s" % (fld_name, fld_type))
            fld_clause_items.append("%s %s" % (dbe_sqlite.quote_obj(fld_name), 
                                               gen2sqlite_dic[fld_type]))
        fld_clause_items.append("UNIQUE(sofa_id)")
        fld_clause = ", ".join(fld_clause_items)
        SQL_make_tbl = """CREATE TABLE "%s" (%s)""" % (tbl_name, fld_clause)
        conn = dbe_sqlite.GetConn(self.conn_dets, my_globals.SOFA_DEFAULT_DB)
        cur = conn.cursor()
        cur.execute(SQL_make_tbl)
        conn.commit()
        # prepare to connect to the newly created table
        dbe = my_globals.DBE_SQLITE
        dbdetsobj = getdata.getDbDetsObj(dbe, self.default_dbs, 
                                         self.default_tbls, self.conn_dets, 
                                         my_globals.SOFA_DEFAULT_DB, tbl_name)
        (conn, cur, dbs, tbls, flds, has_unique, idxs) = dbdetsobj.getDbDets()
        # update tbl dropdown
        self.tbls = tbls
        self.ResetTblDropdown()
        # open data          
        wx.BeginBusyCursor()
        read_only = False
        dlg = db_grid.TblEditor(self, dbe, conn, cur, 
                                my_globals.SOFA_DEFAULT_DB, tbl_name, flds, 
                                self.var_labels, idxs, read_only)
        wx.EndBusyCursor()
        dlg.ShowModal()
        event.Skip()
    
    def OnClose(self, event):
        self.Destroy()
    