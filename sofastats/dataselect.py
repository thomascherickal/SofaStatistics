import pprint
import wx

from sofastats import basic_lib as b
from sofastats import my_globals as mg
from sofastats import config_globals
from sofastats import lib
from sofastats import db_grid
from sofastats.dbe_plugins import dbe_sqlite
from sofastats import getdata
from sofastats import output
from sofastats import projects
from sofastats.tables import table_config


class DlgDataSelect(wx.Dialog):
    def __init__(self, parent, proj_name):
        title = _("Data in \"%s\" Project") % proj_name
        wx.Dialog.__init__(self, parent=parent, title=title,
            style=wx.CAPTION|wx.CLOSE_BOX|wx.SYSTEM_MENU,
            pos=(mg.HORIZ_OFFSET+100,-1))
        self.parent = parent
        self.panel = wx.Panel(self)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        bx_existing = wx.StaticBox(self.panel, -1, _('Existing data tables'))
        bx_new = wx.StaticBox(self.panel, -1, '')
        wx.BeginBusyCursor()
        self.szr_main = wx.BoxSizer(wx.VERTICAL)
        lbl_choose = wx.StaticText(self.panel, -1, 
            _('Choose an existing data table ...'), size=(480,20))
        proj_dic = config_globals.get_settings_dic(subfolder=mg.PROJS_FOLDER, 
            fil_name=proj_name)
        output.update_var_dets(dlg=self)
        self.chk_read_only = wx.CheckBox(self.panel, -1, _('Read Only'))
        self.chk_read_only.SetValue(True)
        self.btn_delete = wx.Button(self.panel, -1, _('Delete'))
        self.btn_delete.Bind(wx.EVT_BUTTON, self.on_delete)
        self.btn_design = wx.Button(self.panel, -1, _('Design'))
        self.btn_design.Bind(wx.EVT_BUTTON, self.on_design)
        btn_open = wx.Button(self.panel, wx.ID_OPEN)
        btn_open.Bind(wx.EVT_BUTTON, self.on_open)
        self.szr_data = wx.FlexGridSizer(rows=2, cols=2, hgap=5, vgap=5)
        ## key settings
        self.drop_tbls_panel = self.panel
        self.drop_tbls_system_font_size = True
        hide_db = projects.get_hide_db()
        self.drop_tbls_idx_in_szr = 3 if not hide_db else 1  ## the 2 database items are missing)
        self.drop_tbls_sel_evt = self.on_table_sel
        self.drop_tbls_rmargin = 0
        self.drop_tbls_can_grow = True
        self.drop_tbls_szr = self.szr_data
        getdata.data_dropdown_settings_correct(parent=self)
        ## set up self.drop_dbs and self.drop_tbls
        default_dbs = proj_dic[mg.PROJ_DEFAULT_DBS]
        (self.drop_dbs, self.drop_tbls,
         self.db_choice_items,
         self.selected_dbe_db_idx) = getdata.get_data_dropdowns(self,
                                                        self.panel, default_dbs)
        self.szr_data.AddGrowableCol(1, 1)      
        lbl_dbs = wx.StaticText(self.panel, -1, _('Databases:'))
        lbl_dbs.SetFont(mg.LABEL_FONT)
        if not hide_db:
            self.szr_data.Add(lbl_dbs, 0, wx.RIGHT, 5)
            self.szr_data.Add(self.drop_dbs, 1, wx.GROW)
        else:
            lbl_dbs.Hide()
            self.drop_dbs.Hide()
        lbl_tbls = wx.StaticText(self.panel, -1, _('Data tables:'))
        lbl_tbls.SetFont(mg.LABEL_FONT)
        self.szr_data.Add(lbl_tbls, 0, wx.RIGHT, 5)
        self.szr_data.Add(self.drop_tbls, 1, wx.GROW)        
        szr_existing_bottom = wx.FlexGridSizer(rows=1, cols=4, hgap=5, vgap=50)
        szr_existing_bottom.AddGrowableCol(2,2)  ## idx, propn
        szr_existing_bottom.Add(self.btn_delete, 0, wx.RIGHT, 10)
        szr_existing_bottom.Add(self.btn_design, 0)
        szr_existing_bottom.Add(self.chk_read_only, 0, wx.ALIGN_RIGHT)
        szr_existing_bottom.Add(btn_open, 0, wx.ALIGN_RIGHT)
        szr_existing = wx.StaticBoxSizer(bx_existing, wx.VERTICAL)
        szr_existing.Add(self.szr_data, 0, wx.GROW|wx.ALL, 10)
        szr_existing.Add(szr_existing_bottom, 0, wx.GROW|wx.ALL, 10)
        szr_new = wx.StaticBoxSizer(bx_new, wx.HORIZONTAL)
        lbl_new_extra = '' if hide_db else _(' to the default SOFA database')
        lbl_new = wx.StaticText(self.panel, -1, _('... or add a new data table') 
            + lbl_new_extra)
        btn_new = wx.Button(self.panel, wx.ID_NEW)
        btn_new.Bind(wx.EVT_BUTTON, self.on_new)
        szr_new.Add(lbl_new, 1, wx.GROW|wx.ALL, 10)
        szr_new.Add(btn_new, 0, wx.ALL, 10)
        self.lbl_feedback = wx.StaticText(self.panel, -1, '')
        btn_close = wx.Button(self.panel, wx.ID_CLOSE)
        btn_close.Bind(wx.EVT_BUTTON, self.on_close)
        szr_bottom = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_btns = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_btns.Add(self.lbl_feedback, 1, wx.GROW|wx.ALL, 10)
        self.szr_btns.Add(btn_close, 0)
        szr_bottom.Add(self.szr_btns, 1, wx.GROW|wx.RIGHT, 15)  ## align with New        
        self.szr_main.Add(lbl_choose, 0, wx.ALL, 10)
        self.szr_main.Add(
            szr_existing, 1, wx.LEFT|wx.BOTTOM|wx.RIGHT|wx.GROW, 10)
        self.szr_main.Add(szr_new, 0, wx.GROW|wx.LEFT|wx.BOTTOM|wx.RIGHT, 10)
        self.szr_main.Add(szr_bottom, 0, wx.GROW|wx.ALL, 10)
        self.panel.SetSizer(self.szr_main)
        self.szr_main.SetSizeHints(self)
        self.Layout()
        self.ctrl_enablement()
        lib.GuiLib.safe_end_cursor()

    def add_feedback(self, feedback):
        self.lbl_feedback.SetLabel(feedback)
        wx.Yield()

    def ctrl_enablement(self):
        """
        Can only design tables in the default SOFA database.

        Only need read only option if outside the default sofa database.
        """
        dd = mg.DATADETS_OBJ
        sofa_default_db = (dd.dbe == mg.DBE_SQLITE and dd.db == mg.SOFA_DB)
        self.btn_design.Enable(sofa_default_db)
        delete_enable = (sofa_default_db and dd.tbl != mg.DEMO_TBL)
        self.btn_delete.Enable(delete_enable)
        read_only_settings = getdata.get_read_only_settings()
        self.chk_read_only.SetValue(read_only_settings.read_only)
        self.chk_read_only.Enable(read_only_settings.enabled)

    def on_database_sel(self, _event):
        if getdata.refresh_db_dets(self):
            self.reset_tbl_dropdown()
            self.ctrl_enablement()

    def reset_tbl_dropdown(self):
        "Set tables dropdown items and select item according to dd.tbl"
        parent = self
        parent.drop_tbls = getdata.get_fresh_drop_tbls(
            parent, parent.drop_tbls_szr, parent.drop_tbls_panel)

    def on_table_sel(self, _event):
        "Reset key data details after table selection."       
        getdata.refresh_tbl_dets(self)
        self.ctrl_enablement()

    def on_open(self, event):
        db_grid.open_database(self, event)

    def on_delete(self, event):
        """
        Delete selected table (giving user choice to back out).
        """
        dd = mg.DATADETS_OBJ
        if wx.MessageBox(_("Do you wish to delete \"%s\"?") % dd.tbl, 
            caption=_('DELETE'), style=wx.YES_NO|wx.NO_DEFAULT) == wx.YES:
            try:
                dbe_tblname = getdata.tblname_qtr(dd.dbe, dd.tbl)
                dd.cur.execute(f'DROP TABLE IF EXISTS {dbe_tblname}')
                dd.con.commit()
                dd.set_db(dd.db)  ## refresh tbls downwards
                self.reset_tbl_dropdown()
                self.ctrl_enablement()
            except Exception as e:
                wx.MessageBox(f'Unable to delete "{dd.tbl}". '
                    f'Caused by error: {b.ue(e)}')
        event.Skip()

    def on_design(self, _event):
        """
        Open table config dlg which starts with the design settings for the
        table (fld names and types).

        NB only enabled (for either viewing or editing) for the default SQLite
        database.

        No need to change the data_dets because we are using the same one.
        """
        debug = False
        dd = mg.DATADETS_OBJ
        read_only = False  ## only read only if the demo table
        sofa_demo_tbl = (
            dd.dbe == mg.DBE_SQLITE
            and dd.db == mg.SOFA_DB
            and dd.tbl == mg.DEMO_TBL)
        if sofa_demo_tbl and not read_only:
            wx.MessageBox(
                _('The design of the default SOFA table cannot be changed'))
            self.chk_read_only.SetValue(True)
            read_only = True
        ## table config dialog
        tblname_lst = [dd.tbl, ]
        init_fld_settings = getdata.get_init_settings_data(dd, dd.tbl)
        if debug: print(f'Initial table_config data: {init_fld_settings}')
        fld_settings = []  ## can read final result at the end
        dlg_config = table_config.DlgConfigTable(
            self.var_labels, self.val_dics,
            tblname_lst, init_fld_settings, fld_settings,
            read_only=read_only, new=False)
        ret = dlg_config.ShowModal()
        if debug: pprint.pprint(fld_settings)
        if ret == mg.RET_CHANGED_DESIGN and not read_only:
            if debug: print(f'Flds before: {dd.flds}')
            returned_tblname = tblname_lst[0]
            dd.set_dbe(dbe=mg.DBE_SQLITE, db=mg.SOFA_DB, tbl=returned_tblname)
            if debug: print(f'Flds after: {dd.flds}')
            self.reset_tbl_dropdown()
            output.update_var_dets(dlg=self)

    def on_new(self, event):
        """
        Get table name (must be unique etc), create empty table in SOFA Default
        database with that name, and start off with 5 fields ready to rename.

        Must be able to add fields, and rename fields.
        """
        debug = False
        dd = mg.DATADETS_OBJ
        sofa_default_db = (dd.dbe == mg.DBE_SQLITE and dd.db == mg.SOFA_DB)
        try:
            con = dbe_sqlite.get_con(dd.con_dets, mg.SOFA_DB)
            ## Not dd.con because we may fail making a new one and need to
            ## stick with the original
            con.close()
        except Exception:
            wx.MessageBox(_('The current project does not include a link to the'
                ' default SOFA database so a new table cannot be made there.'))
            return
        ## switch dd if necessary i.e. if default sofa db not already selected
        if not sofa_default_db:
            dbe2restore = dd.dbe
            db2restore = dd.db
            tbl2restore = dd.tbl
            dd.set_dbe(dbe=mg.DBE_SQLITE, db=mg.SOFA_DB)
        ## table config dialog
        tblname_lst = [] # not quite worth using validator mechanism ;-)
        init_fld_settings = [
            ('sofa_id', mg.FLDTYPE_NUMERIC_LBL),
            ('var001', mg.FLDTYPE_NUMERIC_LBL),]
        fld_settings = []  ## can read final result at the end
        if debug: print(mg.DATADETS_OBJ)
        dlg_config = table_config.DlgConfigTable(self.var_labels, self.val_dics,
            tblname_lst, init_fld_settings, fld_settings,
            read_only=False, new=True)
        ret = dlg_config.ShowModal()
        if debug: pprint.pprint(fld_settings)
        if ret != mg.RET_CHANGED_DESIGN:
            event.Skip()
            return
        ## update tbl dropdown
        if debug: print(mg.DATADETS_OBJ)
        if sofa_default_db:
            self.reset_tbl_dropdown()  ## won't be affected otherwise
        ## open data
        wx.BeginBusyCursor()
        dlg = db_grid.TblEditor(self, self.var_labels, self.var_notes,
            self.var_types, self.val_dics, read_only=False)
        lib.GuiLib.safe_end_cursor()
        dlg.ShowModal()
        ## restore dd to original if necessary
        if not sofa_default_db:
            dd.set_dbe(dbe=dbe2restore, db=db2restore, tbl=tbl2restore)
        self.ctrl_enablement()
        event.Skip()

    def on_close(self, _event):
        self.Destroy()
