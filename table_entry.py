import wx
import wx.grid
import pprint

import text_browser

COL_STR = "col_string"
COL_INT = "col_integer"
COL_FLOAT = "col_float"
COL_TEXT_BROWSE = "col_button"


class TableEntryDlg(wx.Dialog):
    def __init__(self, title, grid_size, col_dets, data, new_grid_data):
        """
        col_dets - see under TableEntry.
        data - list of tuples (must have at least one item, even if only a 
            "rename me".
        new_grid_data - is effectively "returned".  Add details to it in form 
            of a list of tuples.
        """
        wx.Dialog.__init__(self, None, title=title,
                          size=(400,400), 
                          style=wx.RESIZE_BORDER|wx.CAPTION|wx.CLOSE_BOX|
                              wx.SYSTEM_MENU, pos=(300, 0))
        self.panel = wx.Panel(self)
        self.szrMain = wx.BoxSizer(wx.VERTICAL)
        self.tabentry = TableEntry(self, self.panel, self.szrMain, 1, grid_size, 
                                   col_dets, data, new_grid_data)
        # Close
        self.SetupButtons()
        # sizers
        self.szrMain.Add(self.szrButtons, 0, wx.ALL, 10)
        self.panel.SetSizer(self.szrMain)
        self.szrMain.SetSizeHints(self)
        self.Layout()
        self.tabentry.grid.SetFocus()
        
    def SetupButtons(self):
        "Separated for text_browser reuse"
        btnCancel = wx.Button(self.panel, wx.ID_CANCEL)
        btnCancel.Bind(wx.EVT_BUTTON, self.OnCancel)            
        btnOK = wx.Button(self.panel, wx.ID_OK) # must have ID of wx.ID_OK 
        # to trigger validators (no event binding needed) and 
        # for std dialog button layout
        btnOK.Bind(wx.EVT_BUTTON, self.OnOK)
        btnOK.SetDefault()
        # using the approach which will follow the platform convention 
        # for standard buttons
        self.szrButtons = wx.StdDialogButtonSizer()
        self.szrButtons.AddButton(btnCancel)
        self.szrButtons.AddButton(btnOK)
        self.szrButtons.Realize()

    def OnCancel(self, event):
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL)

    def OnOK(self, event):
        self.tabentry.UpdateNewGridData()
        self.Destroy()
        self.SetReturnCode(wx.ID_OK)
    
                
class TableEntry(object):
    def __init__(self, frame, panel, szr, vert_share, read_only, grid_size, 
                 col_dets, data, new_grid_data):
        """
        vert_share - vertical share of sizer supplied.
        col_dets - list of dic.  Keys = "col_label", "col_type", 
            and, optionally, "col_width", "file_phrase", "file_wildcard", 
            "empty_ok", "col_min_val", "col_max_val", "col_precision".
        data - list of tuples (must have at least one item, even if only a 
            "rename me".
        new_grid_data - is effectively "returned" - add details to it in form 
            of a list of tuples.
        """
        self.frame = frame
        self.panel = panel
        self.szr = szr
        self.read_only = read_only
        self.col_dets = col_dets
        self.SetupGrid(grid_size, data, new_grid_data)
        self.szr.Add(self.grid, vert_share, wx.GROW|wx.ALL, 5)

    def SetupGrid(self, size, data, new_grid_data):
        """
        Set up grid.  Convenient to separate so can reuse when subclassing,
            perhaps to add extra controls.
        """
        # store any fixed min col_widths
        self.col_widths = [None for x in range(len(self.col_dets))] # initialise
        for col_idx, col_det in enumerate(self.col_dets):
            if col_det.get("col_width"):
                self.col_widths[col_idx] = col_det["col_width"]
        data.sort(key=lambda s: s[0])
        self.data = data
        self.new_grid_data = new_grid_data
        self.prev_vals = []
        self.new_editor_shown = False
        # grid control
        self.grid = wx.grid.Grid(self.panel, size=size)
        self.rows_n = len(self.data) # data rows only - not inc new entry row
        self.cols_n = len(self.col_dets)
        if self.rows_n:
            data_cols_n = len(data[0])
            #pprint.pprint(data) # debug
            if data_cols_n != self.cols_n:
                raise Exception, "There must be one set of column details " + \
                    "per column of data (currently %s details for " + \
                    "%s columns)" % (self.cols_n, data_cols_n)
        self.grid.CreateGrid(numRows=self.rows_n + 1, # plus data entry row
                             numCols=self.cols_n)
        self.grid.EnableEditing(not self.read_only)
        # Set any col min widths specifically specified
        for col_idx in range(len(self.col_dets)):
            col_width = self.col_widths[col_idx]
            if col_width:
                self.grid.SetColMinimalWidth(col_idx, col_width)
                self.grid.SetColSize(col_idx, col_width)
                # otherwise will only see effect after resizing
            else:
                self.grid.AutoSizeColumn(col_idx, setAsMin=False)
        self.grid.ForceRefresh()
        # set col rendering and editing (string is default)
        for col_idx, col_det in enumerate(self.col_dets):
            col_type = col_det["col_type"]
            if col_type == COL_INT:
                self.grid.SetColFormatNumber(col_idx)
            elif col_type == COL_FLOAT:
                width, precision = self.GetWidthPrecision(col_idx)
                self.grid.SetColFormatFloat(col_idx, width, precision)
            # must set editor cell by cell amazingly
            for j in range(self.rows_n + 1):
                renderer, editor = self.GetNewRendererEditor(col_idx)
                self.grid.SetCellRenderer(j, col_idx, renderer)
                self.grid.SetCellEditor(j, col_idx, editor)
        # grid event handling
        self.grid.Bind(text_browser.EVT_TEXT_BROWSE_KEY_DOWN, 
                       self.OnTextBrowseKeyDown)        
        self.grid.Bind(wx.grid.EVT_GRID_CELL_CHANGE, self.OnCellChange)
        self.grid.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.OnSelectCell)
        self.frame.Bind(wx.grid.EVT_GRID_EDITOR_SHOWN, self.EditorShown)
        self.frame.Bind(wx.grid.EVT_GRID_EDITOR_HIDDEN, self.EditorHidden)
        self.grid.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.grid.Bind(wx.grid.EVT_GRID_LABEL_LEFT_CLICK, self.OnLabelClick)
        for col_idx, col_det in enumerate(self.col_dets):
            self.grid.SetColLabelValue(col_idx, col_det["col_label"])
        for i in range(self.rows_n):
            for j in range(self.cols_n):
                self.grid.SetCellValue(row=i, col=j, s=str(data[i][j]))
        self.grid.SetRowLabelValue(self.rows_n, "*")
        self.grid.SetGridCursor(self.rows_n, 0)
        self.grid.MakeCellVisible(self.rows_n, 0)
    
    def OnTextBrowseKeyDown(self, event):
        if event.GetKeyCode() in [wx.WXK_RETURN]:
            self.grid.DisableCellEditControl()
            self.grid.MoveCursorDown(expandSelection=False)
    
    def GetNewRendererEditor(self, col_idx):
        """
        For a given column index, return a fresh renderer and editor object.
        Objects must be unique to cell.
        Returns renderer, editor.
        Nearly (but not quite) making classes ;-)
        """
        col_type = self.col_dets[col_idx]["col_type"]
        if col_type == COL_INT:
            min = self.col_dets[col_idx].get("col_min_val", -1) # -1 no minimum
            max = self.col_dets[col_idx].get("col_max_val", min)
            renderer = wx.grid.GridCellNumberRenderer()
            editor = wx.grid.GridCellNumberEditor(min, max)
        elif col_type == COL_FLOAT:
            width, precision = self.GetWidthPrecision(col_idx)
            renderer = wx.grid.GridCellFloatRenderer(width, precision)
            editor = wx.grid.GridCellFloatEditor(width, precision)
        elif col_type == COL_TEXT_BROWSE:
            renderer = wx.grid.GridCellStringRenderer()
            file_phrase = self.col_dets[col_idx].get("file_phrase", "")
            # use * - *.* will not pickup files without extensions in Ubuntu
            wildcard = self.col_dets[col_idx].get("file_wildcard", 
                                                  "Any file (*)|*")
            editor = text_browser.GridCellTextBrowseEditor(file_phrase, 
                                                           wildcard)
        else:
            renderer = wx.grid.GridCellStringRenderer()
            editor = wx.grid.GridCellTextEditor()
        return renderer, editor

    def GetWidthPrecision(self, col_idx):
        """
        Returns width, precision.
        """
        width = self.col_dets[col_idx].get("col_width", 5)
        precision = self.col_dets[col_idx].get("col_precision", 1)
        return width, precision

    def OnLabelClick(self, event):
        "Need to give grid the focus so can process keystrokes e.g. delete"
        self.grid.SetFocus()
        event.Skip()

    def OnKeyDown(self, event):
        """
        http://wiki.wxpython.org/AnotherTutorial#head-999ff1e3fbf5694a51a91cf4ed2140f692da013c
        """
        if event.GetKeyCode() in [wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE]:
            self.TryToDeleteRow()
        else:
            event.Skip()

    def TryToDeleteRow(self):
        """
        Delete row if a row selected and not the data entry row
            and put focus on new line.
        """
        selected_rows = self.grid.GetSelectedRows()
        if len(selected_rows) == 1:
            row = selected_rows[0]
            if row != self.rows_n:
                self.grid.DeleteRows(pos=row, numRows=1)
                self.rows_n -= 1
                self.grid.SetRowLabelValue(self.rows_n, "*")
                self.grid.SetGridCursor(self.rows_n, 0)
                self.grid.HideCellEditControl()
                self.grid.ForceRefresh()
                self.SafeLayoutAdjustment()
    
    def EditorShown(self, event):
        # disable resizing until finished
        self.grid.DisableDragColSize()
        self.grid.DisableDragRowSize()
        if event.GetRow() == self.rows_n:
            self.new_editor_shown = True
        event.Skip()
        
    def EditorHidden(self, event):
        # re-enable resizing
        self.grid.EnableDragColSize()
        self.grid.EnableDragRowSize()
        self.new_editor_shown = False
        event.Skip()
        
    def OnSelectCell(self, event):
        "Store value in case we need to undo"
        row = event.GetRow()
        col = event.GetCol()
        try:
            prev_val = self.grid.GetCellValue(row, col)
            prev_tup = ((row, col), prev_val)
            self.prev_vals.append(prev_tup)
        except Exception, e:
            pass
        if len(self.prev_vals) > 2: # only need two to manage undos
            self.prev_vals.pop(0)
        new_entry = (row == self.rows_n)
        if new_entry:
            if (self.new_editor_shown or self.RowHasData(row)):
                self.grid.SetRowLabelValue(self.rows_n, "...")
            else:
                self.grid.SetRowLabelValue(self.rows_n, "*")
        event.Skip() # continue - I'm only being a man-in-the-middle ;-)

    def OnCellChange(self, event):
        row = event.GetRow()
        col = event.GetCol()
        new_entry = (row == self.rows_n) # if 3 rows (0,1,2) 
            # row 3 will be the new entry one
        if new_entry:
            if self.ValidRow(row=row):
                self.AddRow(row)
                event.Skip()
            else:
                self.grid.SetRowLabelValue(self.rows_n, "...")
                #print "Can't save new record - not valid"
                self.SafeLayoutAdjustment()
                event.Skip()
        else:
            if not self.ValidRow(row=row):
                #print "Invalid row"
                self.UndoCell(row, col)
            else:
                self.SafeLayoutAdjustment()
    
    def AddRow(self, row):
        ""
        # change label from * and add a new entry row on end of grid
        self.grid.AppendRows()
        # set up cell rendering and editing
        for col_idx in range(self.cols_n):
            renderer, editor = self.GetNewRendererEditor(col_idx)
            self.grid.SetCellRenderer(row + 1, col_idx, renderer)
            self.grid.SetCellEditor(row + 1, col_idx, editor)
        self.grid.SetRowLabelValue(self.rows_n, str(self.rows_n + 1))
        self.rows_n += 1
        self.grid.SetRowLabelValue(self.rows_n, "*")
        self.SafeLayoutAdjustment()
        # jump to first cell
        self.grid.SetGridCursor(self.rows_n, 0)
        # ensure we scroll there completely
        self.grid.MakeCellVisible(self.rows_n, 0)
        
    def SafeLayoutAdjustment(self):
        """
        Uses CallAfter to avoid infinite recursion.
        http://lists.wxwidgets.org/pipermail/wxpython-users/2007-April/063536.html
        """
        wx.CallAfter(self.RunSafeLayoutAdjustment)
    
    def RunSafeLayoutAdjustment(self):
        for col_idx in range(len(self.col_dets)):
            current_width = self.grid.GetColSize(col_idx)
            # identify optimal width according to content
            self.grid.AutoSizeColumn(col_idx, setAsMin=False)
            new_width = self.grid.GetColSize(col_idx)
            if new_width < current_width: # only the user can shrink a column
                # restore to current size
                self.grid.SetColSize(col_idx, current_width)
        # otherwise will only see effect after resizing
        self.grid.ForceRefresh()
    
    def UndoCell(self, row, col):
        """
        Restore original value.
        If more than one, this will be because we have selected another 
            cell while editing another.  The select event fires first adding 
            another item to prev_vals.
        NB not activated on number and float formatted cells.  These will 
            default to zero if you try to save '' to them.
        """
        for (prev_row, prev_col), prev_val in self.prev_vals:
            if prev_row == row and prev_col == col:
                self.grid.SetCellValue(row, col, prev_val)
                break

    def ValidRow(self, row):
        """
        Is row valid?
        Very simple as default - each cell must have something unless empty_ok.
        """
        row_complete = True
        for i, col_det in enumerate(self.col_dets):
            empty_ok = col_det.get("empty_ok", False)
            cell_val = self.grid.GetCellValue(row=row, col=i)
            if not cell_val and not empty_ok:
                row_complete = False
                break
        return row_complete

    def RowHasData(self, row):
        """
        Has the row got any data stored yet?
        NB data won't be picked up if you are in the middle of entering it.
        """
        has_data = False
        for i in range(self.cols_n):
            cell_val = self.grid.GetCellValue(row=row, col=i)
            if cell_val:
                has_data = True
                break
        return has_data

    def UpdateNewGridData(self):
        """
        Update new_grid_data.  Separated for reuse.
        """
        # get data from grid (except for final row (either empty or not saved)
        for i in range(self.rows_n):
            row_data = []
            for j, col_type in enumerate(self.col_dets):
                val = self.grid.GetCellValue(row=i, col=j)
                row_data.append(val)
            self.new_grid_data.append(tuple(row_data))
