import wx

import my_globals
import getdata # must be anything referring to plugin modules
import dbe_plugins.dbe_sqlite as dbe_sqlite
import string
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
        raise Exception, "Two many columns for default cell invalidation test"

def _invalid_fld_name(row, grid):
    "Return boolean and string message"
    other_fld_names = []
    for i in range(grid.GetNumberRows()):
        if i == row:
            continue
        other_fld_names.append(grid.GetCellValue(row=i, col=0))
    field_name = grid.GetCellValue(row=row, col=0)
    if field_name.strip() == "":
        return False, ""
    if not dbe_sqlite.valid_name(field_name):
        msg = "Field names can only contain letters, numbers, and " + \
              "underscores"
        return True, msg
    if field_name in other_fld_names:
        msg = "%s has already been used as a field name" % field_name
        return True, msg
    return False, ""

def _invalid_fld_type(row, grid):
    "Return boolean and string message"
    field_type = grid.GetCellValue(row=row, col=1)
    if field_type.strip() == "":
        return False, ""
    if field_type not in [my_globals.CONF_NUMERIC, my_globals.CONF_STRING, 
                          my_globals.CONF_DATE]:
        msg = "%s is not a valid field type" % field_type
        return True, msg
    return False, ""

def ValidateTblName(tbl_name):
    "Returns boolean plus string message"
    valid_name = dbe_sqlite.valid_name(tbl_name)
    if not valid_name:
        msg = "You can only use letters, numbers and underscores " + \
            "in a SOFA name.  Use another name?"
        return False, msg
    duplicate = getdata.dup_tbl_name(tbl_name)
    if duplicate:
        msg = "Cannot use this name.  A table named \"%s\"" % tbl_name + \
              "already exists in the default SOFA database"
        return False, msg
    return True, ""

class SafeTblNameValidator(wx.PyValidator):
    def __init__(self):
        wx.PyValidator.__init__(self)        
        self.Bind(wx.EVT_CHAR, self.OnChar)
    
    def Clone(self):
        return SafeTblNameValidator()
        
    def Validate(self, win):
        textCtrl = self.GetWindow()
        text = textCtrl.GetValue()
        valid, msg = ValidateTblName(text)
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
    
    
class ConfigTable(table_entry.TableEntryDlg):
    
    def __init__(self, tbl_name_lst, data, new_grid_data, insert_data_func=None, 
                 cell_invalidation_func=None):
        """
        data - list of tuples (must have at least one item, even if only a 
            "rename me".
        new_grid_data - add details to it in form of a list of tuples.
        """
        self.tbl_name_lst = tbl_name_lst
        if not insert_data_func:
            insert_data_func = insert_data
        if not cell_invalidation_func:
            cell_invalidation_func = cell_invalidation
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
        self.txtTblName = wx.TextCtrl(self.panel, -1, "table001", size=(250,-1))
        self.txtTblName.SetValidator(SafeTblNameValidator())
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
                                               cell_invalidation_func)
        self.SetupButtons(inc_delete=True, inc_insert=True)
        self.szrMain.Add(self.szrButtons, 0, wx.ALL, 10)
        self.panel.SetSizer(self.szrMain)
        self.szrMain.SetSizeHints(self)
        self.Layout()
        self.txtTblName.SetFocus()

    def OnOK(self, event):
        """
        Override so we can extend to include table name.
        """
        # NB must run Validate on the panel because the objects are contained by
        # that and not the dialog itself. 
        # http://www.nabble.com/validator-not-in-a-dialog-td23112169.html
        if not self.panel.Validate(): # runs validators on all assoc controls
            return True
        self.tbl_name_lst.append(self.txtTblName.GetValue())
        self.tabentry.UpdateNewGridData()
        self.Destroy()
        self.SetReturnCode(wx.ID_OK)
