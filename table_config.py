import wx

import my_globals
import getdata # must be anything referring to plugin modules
import dbe_plugins.dbe_sqlite as dbe_sqlite
import table_entry

def insert_data(row_idx, grid_data):
    """
    Return list of values to display in inserted row.
    Needs to know row index plus already used variable labels (to prevent 
        collisions).
    """
    nums_used = []
    existing_var_names = [x[0] for x in grid_data]
    for var_name in existing_var_names:
        if not var_name.startswith("var"):
            continue
        try:
            num_used = int(var_name[-3:])
        except ValueError:
            continue
        nums_used.append(num_used)
    free_num = max(nums_used) + 1 if nums_used else 1
    row_data = ["var%03i" % free_num, my_globals.CONF_NUMERIC]
    return row_data

def row_validation(row, grid, col_dets):
    """
    The first column text must be completed and unique (field name) 
        and the second must be from my_globals.CONF_... e.g. "numeric"
    """
    other_fld_names = []
    for i in range(grid.GetNumberRows()):
        if i == row:
            continue
        other_fld_names.append(grid.GetCellValue(row=i, col=0))
    field_name = grid.GetCellValue(row=row, col=0)
    field_type = grid.GetCellValue(row=row, col=1)
    if field_name.strip() == "":
        wx.MessageBox("Please complete a field name")
        return False         
    if field_name in other_fld_names:
        wx.MessageBox("%s has already been used as a field name" % field_name)
        return False
    if field_type not in [my_globals.CONF_NUMERIC, my_globals.CONF_STRING, 
                          my_globals.CONF_DATE]:
        wx.MessageBox("%s is not a valid field type" % field_type)
        return False
    return True

    
class ConfigTable(table_entry.TableEntryDlg):
    
    def __init__(self, data, new_grid_data, insert_data_func=None, 
                 row_validation_func=None):
        """
        data - list of tuples (must have at least one item, even if only a 
            "rename me".
        new_grid_data - add details to it in form of a list of tuples.
        """
        if not insert_data_func:
            insert_data_func = insert_data
        if not row_validation_func:
            row_validation_func = row_validation
        # col_dets - See under table_entry.TableEntry
        col_dets = [{"col_label": "Field Name", 
                     "col_type": table_entry.COL_STR, 
                     "col_width": 100}, 
                    {"col_label": "Data Type", 
                     "col_type": table_entry.COL_DROPDOWN, 
                     "col_width": 100,
                     "dropdown_vals": [my_globals.CONF_NUMERIC, 
                                       my_globals.CONF_STRING, 
                                       my_globals.CONF_DATE]},
                     ]
        grid_size = (250, 250)
        wx.Dialog.__init__(self, None, title="Configure Data Table",
                          size=(500,400), 
                          style=wx.RESIZE_BORDER|wx.CAPTION|wx.CLOSE_BOX|
                              wx.SYSTEM_MENU)
        self.panel = wx.Panel(self)
        # New controls
        lblTblLabel = wx.StaticText(self.panel, -1, "Table Name:")
        lblTblLabel.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.txtTblName = wx.TextCtrl(self.panel, -1, "table001", 
                                       size=(250,-1))
        self.txtTblName.Bind(wx.EVT_KILL_FOCUS, self.OnLeaveTblName)
        # sizers
        self.szrMain = wx.BoxSizer(wx.VERTICAL)
        self.szrTblLabel = wx.BoxSizer(wx.HORIZONTAL)
        self.szrTblLabel.Add(lblTblLabel, 0, wx.RIGHT, 5)
        self.szrTblLabel.Add(self.txtTblName, 1)
        self.szrMain.Add(self.szrTblLabel, 0, wx.GROW|wx.ALL, 10)
        self.tabentry = table_entry.TableEntry(self, self.panel, 
                                               self.szrMain, 2, False, 
                                               grid_size, col_dets, data,  
                                               new_grid_data, insert_data_func,
                                               row_validation_func)
        self.SetupButtons(inc_delete=True, inc_insert=True)
        self.szrMain.Add(self.szrButtons, 0, wx.ALL, 10)
        self.panel.SetSizer(self.szrMain)
        self.szrMain.SetSizeHints(self)
        self.Layout()
        self.txtTblName.SetFocus()

    def OnLeaveTblName(self, event):
        if not self.ValidateTblName(self.txtTblName.GetValue()):
            self.txtTblName.SetFocus()
            self.txtTblName.SetInsertionPoint(0)
        else:
            event.Skip()

    def ValidateTblName(self, tbl_name):
        valid_name, bad_parts = dbe_sqlite.valid_name(tbl_name)
        if not valid_name:
            bad_parts_txt = "'" + ", ".join(bad_parts) + "'"
            msg = "You cannot use %s in a SOFA name.  " % bad_parts_txt + \
                "Use another name?"
            wx.MessageBox(msg)
            return False
        duplicate = getdata.dup_tbl_name(tbl_name)
        if duplicate:
            wx.MessageBox("Cannot use this name.  " + \
                          "A table named \"%s\"" % tbl_name + \
                          "already exists in the default SOFA database")
            return False
        return True

    def OnOK(self, event):
        """
        Override so we can extend to include table name.
        """
        self.tabentry.UpdateNewGridData()
        self.Destroy()
        self.SetReturnCode(wx.ID_OK)
