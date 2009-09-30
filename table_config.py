import wx

import table_entry

    
class ConfigTable(table_entry.TableEntryDlg):
    
    def __init__(self, data, new_grid_data):
        """
        data - list of tuples (must have at least one item, even if only a 
            "rename me".
        new_grid_data - add details to it in form of a list of tuples.
        """
        # col_dets - See under table_entry.TableEntry
        col_dets = [{"col_label": "Field Name", 
                     "col_type": table_entry.COL_STR, 
                     "col_width": 100}, 
                    {"col_label": "Data Type", 
                     "col_type": table_entry.COL_DROPDOWN, 
                     "col_width": 100,
                     "dropdown_vals": ["Numeric", "String", "Date"]},
                     ]
        grid_size = (250, 250)
        wx.Dialog.__init__(self, None, title="Configure Data Table",
                          size=(500,400), 
                          style=wx.RESIZE_BORDER|wx.CAPTION|wx.CLOSE_BOX|
                              wx.SYSTEM_MENU)
        self.panel = wx.Panel(self)
        # New controls
        lblTblLabel = wx.StaticText(self.panel, -1, "Variable Label:")
        lblTblLabel.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.txtTblLabel = wx.TextCtrl(self.panel, -1, "table001", size=(250,-1))
        # sizers
        self.szrMain = wx.BoxSizer(wx.VERTICAL)
        self.szrTblLabel = wx.BoxSizer(wx.HORIZONTAL)
        self.szrTblLabel.Add(lblTblLabel, 0, wx.RIGHT, 5)
        self.szrTblLabel.Add(self.txtTblLabel, 1)
        self.szrMain.Add(self.szrTblLabel, 0, wx.GROW|wx.ALL, 10)
        self.tabentry = table_entry.TableEntry(self, self.panel, 
                                               self.szrMain, 2, False, 
                                               grid_size, col_dets, data,  
                                               new_grid_data)
        self.SetupButtons()
        self.szrMain.Add(self.szrButtons, 0, wx.ALL, 10)
        self.panel.SetSizer(self.szrMain)
        self.szrMain.SetSizeHints(self)
        self.Layout()
        self.txtTblLabel.SetFocus()

    def OnOK(self, event):
        """
        Override so we can extend to include table name.
        """
        debug = True
        self.tabentry.UpdateNewGridData()
        self.Destroy()
        self.SetReturnCode(wx.ID_OK)
