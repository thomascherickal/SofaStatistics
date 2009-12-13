import pprint
import string
import wx

import my_globals
import getdata # must be anything referring to plugin modules
import dbe_plugins.dbe_sqlite as dbe_sqlite
import settings_grid

def insert_data(row_idx, grid_data):
    """
    Return list of values to display in inserted row.
    Needs to know row index plus already used variable labels (to prevent 
        collisions).
    """
    nums_used = []
    existing_var_names = [x[0] for x in grid_data]
    for var_name in existing_var_names:
        if not var_name.startswith(u"var"):
            continue
        try:
            num_used = int(var_name[-3:])
        except ValueError:
            continue
        nums_used.append(num_used)
    free_num = max(nums_used) + 1 if nums_used else 1
    row_data = [u"var%03i" % free_num, my_globals.FLD_TYPE_NUMERIC]
    return row_data

def cell_invalidation(row, col, grid, col_dets):
    """
    The first column text must be either empty, or 
        alphanumeric (and underscores), and unique (field name) 
        and the second must be empty or from my_globals.CONF_... e.g. "numeric"
    """
    if col == 0:
        return _invalid_fld_name(row, grid)
    elif col == 1:
        return _invalid_fld_type(row, grid)
    else:
        raise Exception, u"Two many columns for default cell invalidation test"

def _invalid_fld_name(row, grid):
    "Return boolean and string message"
    other_fld_names = []
    for i in range(grid.GetNumberRows()):
        if i == row:
            continue
        other_fld_names.append(grid.GetCellValue(row=i, col=0))
    field_name = grid.GetCellValue(row=row, col=0)
    if field_name.strip() == u"":
        return False, ""
    if not dbe_sqlite.valid_name(field_name):
        msg = _("Field names can only contain letters, numbers, and "
              "underscores")
        return True, msg
    if field_name in other_fld_names:
        msg = _("%s has already been used as a field name") % field_name
        return True, msg
    return False, u""

def _invalid_fld_type(row, grid):
    "Return boolean and string message"
    field_type = grid.GetCellValue(row=row, col=1)
    if field_type.strip() == u"":
        return False, ""
    if field_type not in [my_globals.FLD_TYPE_NUMERIC, 
                          my_globals.FLD_TYPE_STRING, 
                          my_globals.FLD_TYPE_DATE]:
        msg = _("%s is not a valid field type") % field_type
        return True, msg
    return False, u""

def ValidateTblName(tbl_name, name_ok_to_reuse):
    "Returns boolean plus string message"
    valid_name = dbe_sqlite.valid_name(tbl_name)
    if not valid_name:
        msg = _("You can only use letters, numbers and underscores "
            "in a SOFA name.  Use another name?")
        return False, msg
    if tbl_name == name_ok_to_reuse: # we're just editing an existing table
        duplicate = False
    else:
        duplicate = getdata.dup_tbl_name(tbl_name)
    if duplicate:
        msg = _("Cannot use this name.  A table named \"%s\" already exists in"
                " the default SOFA database") % tbl_name
        return False, msg
    return True, u""

class SafeTblNameValidator(wx.PyValidator):
    def __init__(self, name_ok_to_reuse):
        wx.PyValidator.__init__(self)
        self.name_ok_to_reuse = name_ok_to_reuse
        self.Bind(wx.EVT_CHAR, self.OnChar)
    
    def Clone(self):
        return SafeTblNameValidator(self.name_ok_to_reuse)
        
    def Validate(self, win):
        textCtrl = self.GetWindow()
        text = textCtrl.GetValue()
        valid, msg = ValidateTblName(text, self.name_ok_to_reuse)
        if not valid:
            wx.MessageBox(msg)
            textCtrl.SetFocus()
            textCtrl.Refresh()
            return False
        else:
            textCtrl.Refresh()
            return True
    
    def OnChar(self, event):
        # allow backspace and delete (both)
        if event.GetKeyCode() in [wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE, 
                                  wx.WXK_BACK]:
            event.Skip()
            return
        try:
            key = chr(event.GetKeyCode())
        except Exception:
            return
        # allow alphanumeric and underscore
        if key not in string.letters and key not in string.digits \
                and key != "_":
            return
        event.Skip()
    
    def TransferToWindow(self):
        return True
    
    def TransferFromWindow(self):
        return True

    
class ConfigTableDlg(settings_grid.SettingsEntryDlg):
    
    debug = False
    
    def __init__(self, tbl_name_lst, data, final_grid_data, readonly=False,
                 insert_data_func=None, cell_invalidation_func=None):
        """
        tbl_name_lst -- passed in as a list so changes can be made without 
            having to return anything. 
        data -- list of tuples (must have at least one tuple in the list, even
            if only a "rename me".
        final_grid_data -- add details to it in form of a list of tuples.
        """
        if tbl_name_lst:
            name_ok_to_reuse = tbl_name_lst[0]
        else:
            name_ok_to_reuse = None
        self.tbl_name_lst = tbl_name_lst
        # set up new grid data based on data
        self.final_grid_data = final_grid_data
        self.init_final_grid_data(data)
        self.readonly = readonly
        if not insert_data_func:
            insert_data_func = insert_data
        if not cell_invalidation_func:
            cell_invalidation_func = cell_invalidation
        # col_dets - See under settings_grid.SettingsEntry
        col_dets = [{"col_label": _("Field Name"), 
                     "col_type": settings_grid.COL_STR, 
                     "col_width": 100}, 
                    {"col_label": _("Data Type"), 
                     "col_type": settings_grid.COL_DROPDOWN, 
                     "col_width": 100,
                     "dropdown_vals": [my_globals.FLD_TYPE_NUMERIC, 
                                       my_globals.FLD_TYPE_STRING, 
                                       my_globals.FLD_TYPE_DATE]},
                     ]
        grid_size = (250, 250)
        wx.Dialog.__init__(self, None, title=_("Configure Data Table"),
                          size=(500,400), 
                          style=wx.RESIZE_BORDER|wx.CAPTION|wx.CLOSE_BOX|
                              wx.SYSTEM_MENU)
        self.panel = wx.Panel(self)
        # New controls
        lblTblLabel = wx.StaticText(self.panel, -1, _("Table Name:"))
        lblTblLabel.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        tbl_name = tbl_name_lst[0] if tbl_name_lst else _("table") + u"001"
        self.txtTblName = wx.TextCtrl(self.panel, -1, tbl_name, size=(250,-1))
        self.txtTblName.Enable(not self.readonly)
        self.txtTblName.SetValidator(SafeTblNameValidator(name_ok_to_reuse))
        # sizers
        self.szrMain = wx.BoxSizer(wx.VERTICAL)
        self.szrTblLabel = wx.BoxSizer(wx.HORIZONTAL)
        self.szrTblLabel.Add(lblTblLabel, 0, wx.RIGHT, 5)
        self.szrTblLabel.Add(self.txtTblName, 1)
        self.szrMain.Add(self.szrTblLabel, 0, wx.GROW|wx.ALL, 10)
        self.tabentry = ConfigTableEntry(self, self.panel, 
                                         self.szrMain, 2, self.readonly, 
                                         grid_size, col_dets, data,  
                                         final_grid_data, insert_data_func,
                                         cell_invalidation_func)
        self.SetupButtons(inc_delete=not self.readonly, 
                          inc_insert=not self.readonly)
        self.szrMain.Add(self.szrButtons, 0, wx.ALL, 10)
        self.panel.SetSizer(self.szrMain)
        self.szrMain.SetSizeHints(self)
        self.Layout()
        self.txtTblName.SetFocus()

    def init_final_grid_data(self, data):
        extra = []
        for row in data:
            new_row = {my_globals.TBL_FLD_NAME: row[0], 
                       my_globals.TBL_FLD_NAME_ORIG: row[0], 
                       my_globals.TBL_FLD_TYPE: row[1], 
                       my_globals.TBL_FLD_TYPE_ORIG: row[1]}
            extra.append(new_row)
        self.final_grid_data += extra
    
    def insert_before(self):
        """
        Returns row inserted before (or None if no insertion) and row data (or 
            None if no content added). 
        """
        selected_rows = self.tabentry.grid.GetSelectedRows()
        if not selected_rows: 
            return None, None
        pos = selected_rows[0]
        if pos == 0:
            wx.MessageBox(_("The %s must always come first") % \
                          my_globals.SOFA_ID)
            return None, None
        row_data = self.tabentry.InsertRowAbove(pos)
        return pos, row_data

    def OnInsert(self, event):
        """
        Insert before.
        Overridden so we can update final_grid_data.
        """
        row_before, row_data = self.insert_before()
        if row_before is not None:
            if self.debug: print("Row we inserted before was %s" % row_before)
            # insert new row into final_grid_data - Nones for original values
            new_row = {my_globals.TBL_FLD_NAME: row_data[0], 
                       my_globals.TBL_FLD_NAME_ORIG: None, 
                       my_globals.TBL_FLD_TYPE: row_data[1], 
                       my_globals.TBL_FLD_TYPE_ORIG: None}
            self.final_grid_data.insert(row_before, new_row)
            if self.debug: pprint.pprint(self.final_grid_data)
        self.tabentry.grid.SetFocus()
        event.Skip()
    
    def OnDelete(self, event):
        "Overridden so we can update final_grid_data."
        row_del = self.tabentry.TryToDeleteRow()
        if row_del is not None:
            if self.debug: print("Row deleted was %s" % row_del)
            # remove row from final_grid_data.
            del self.final_grid_data[row_del]
            if self.debug: pprint.pprint(self.final_grid_data)
        self.tabentry.grid.SetFocus()
        event.Skip()

    def OnOK(self, event):
        """
        Override so we can extend to include table name.
        """
        if not self.readonly:
            # NB must run Validate on the panel because the objects are 
            # contained by that and not the dialog itself. 
            # http://www.nabble.com/validator-not-in-a-dialog-td23112169.html
            if not self.panel.Validate(): # runs validators on all assoc ctrls
                return True
        if self.tbl_name_lst: # empty ready to repopulate
            del self.tbl_name_lst[0]
        self.tbl_name_lst.append(self.txtTblName.GetValue())
        self.tabentry.update_final_grid_data()
        self.Destroy()
        self.SetReturnCode(wx.ID_OK)
        
    
class ConfigTableEntry(settings_grid.SettingsEntry):
    """
    final_grid_data should be returned as a list of dicts with the keys:
    my_globals.TBL_FLD_NAME, etc
    """
    
    def __init__(self, frame, panel, szr, vert_share, read_only, grid_size, 
                col_dets, data, final_grid_data, insert_data_func=None, 
                cell_invalidation_func=None):
        force_focus = False
        settings_grid.SettingsEntry.__init__(self, frame, panel, szr, 
            vert_share, read_only, grid_size, col_dets, data, final_grid_data, 
            force_focus, insert_data_func, cell_invalidation_func)
        self.debug = False # otherwise set in the parent class ;-)
        # disable first row (SOFA_ID)
        attr = wx.grid.GridCellAttr()
        attr.SetReadOnly(True)
        self.grid.SetRowAttr(0, attr)
    
    def OnCellMove(self, event):
        debug = False
        src_row, left_row = settings_grid.SettingsEntry.OnCellMove(self, event)
        if left_row:
            if self.debug or debug: print("Row moved from was %s" % src_row)
            # For row we're leaving, fill in new details.
            # If an existing row, leave original values alone.
            fld_name = self.grid.GetCellValue(src_row, 0)
            fld_type = self.grid.GetCellValue(src_row, 1)
            try:
                self.final_grid_data[src_row][my_globals.TBL_FLD_NAME] = \
                    fld_name
                self.final_grid_data[src_row][my_globals.TBL_FLD_TYPE] = \
                    fld_type
            except IndexError: # leaving what was the new row
                new_row = {my_globals.TBL_FLD_NAME: fld_name, 
                           my_globals.TBL_FLD_NAME_ORIG: None, 
                           my_globals.TBL_FLD_TYPE: fld_type, 
                           my_globals.TBL_FLD_TYPE_ORIG: None}
                self.final_grid_data.append(new_row)
            if self.debug or debug: pprint.pprint(self.final_grid_data)
                
    def update_final_grid_data(self):
        """
        Update final_grid_data.  Overridden so we can include original field 
            details (needed when making new version of the original table).
        Fill in details of fld_names and fld_types (leaving original versions
            untouched).
        """
        debug = False
        grid_data = self.get_grid_data() # only saved data
        if debug: 
            print(grid_data)
            pprint.pprint(self.final_grid_data)
        for i, row in enumerate(grid_data):
            if debug: print(row)
            self.final_grid_data[i][my_globals.TBL_FLD_NAME] = row[0]
            self.final_grid_data[i][my_globals.TBL_FLD_TYPE] = row[1]
        if self.debug or debug: pprint.pprint(self.final_grid_data)
    
    def ok_to_delete_row(self, row):
        """
        Can delete any row except the new row or the SOFA_ID row
        Returns boolean and msg.
        """
        if self.NewRow(row):
            return False, _("Unable to delete new row")
        elif row == 0:
            return False, _("Unable to delete sofa id row")
        else:
            return True, None