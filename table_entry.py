import wx
import wx.grid
import pprint

import text_browser

COL_STR = "col_string"
COL_INT = "col_integer"
COL_FLOAT = "col_float"
COL_TEXT_BROWSE = "col_button"
COL_DROPDOWN = "col_dropdown"

# move directions
MOVE_LEFT = "move left"
MOVE_RIGHT = "move right"
MOVE_UP = "move up"
MOVE_DOWN = "move down"
MOVE_UP_RIGHT = "move up right"
MOVE_UP_LEFT = "move up left"
MOVE_DOWN_RIGHT = "move down right"
MOVE_DOWN_LEFT = "move down left"
# cell move types
MOVING_IN_EXISTING = "moving in existing"
MOVING_IN_NEW = "moving in new"
LEAVING_EXISTING = "leaving existing"
LEAVING_NEW = "leaving new"

class CellMoveEvent(wx.PyCommandEvent):
    "See 3.6.1 in wxPython in Action"
    def __init__(self, evtType, id):
        wx.PyCommandEvent.__init__(self, evtType, id)
    
    def AddDets(self, dest_row=None, dest_col=None, direction=None):
        self.dest_row = dest_row
        self.dest_col = dest_col
        self.direction = direction
    
# new event type to pass around
myEVT_CELL_MOVE = wx.NewEventType()
# event to bind to
EVT_CELL_MOVE = wx.PyEventBinder(myEVT_CELL_MOVE, 1)


class TableEntryDlg(wx.Dialog):
    def __init__(self, title, grid_size, col_dets, data, new_grid_data, 
                 insert_data_func=None, row_validation_func=None):
        """
        col_dets - see under TableEntry.
        data - list of tuples (must have at least one item, even if only a 
            "rename me".
        new_grid_data - is effectively "returned".  Add details to it in form 
            of a list of tuples.
        insert_data_func - what data do you want to see in a new inserted row 
            (if any).  Must take row index as argument.
        """
        wx.Dialog.__init__(self, None, title=title,
                          size=(400,400), 
                          style=wx.RESIZE_BORDER|wx.CAPTION|wx.CLOSE_BOX|
                              wx.SYSTEM_MENU, pos=(300, 0))
        self.panel = wx.Panel(self)
        self.szrMain = wx.BoxSizer(wx.VERTICAL)
        self.tabentry = TableEntry(self, self.panel, self.szrMain, 1, grid_size, 
                                   col_dets, data, new_grid_data, 
                                   insert_data_func, row_validation_func)
        # Close
        self.SetupButtons()
        # sizers
        self.szrMain.Add(self.szrButtons, 0, wx.ALL, 10)
        self.panel.SetSizer(self.szrMain)
        self.szrMain.SetSizeHints(self)
        self.Layout()
        self.tabentry.grid.SetFocus()
        
    def SetupButtons(self, inc_delete=False, inc_insert=False):
        """
        Separated for text_browser reuse
        """
        btnCancel = wx.Button(self.panel, wx.ID_CANCEL)
        btnCancel.Bind(wx.EVT_BUTTON, self.OnCancel)
        btnOK = wx.Button(self.panel, wx.ID_OK) # must have ID of wx.ID_OK 
        # to trigger validators (no event binding needed) and 
        # for std dialog button layout
        btnOK.Bind(wx.EVT_BUTTON, self.OnOK)
        btnOK.SetDefault()
        if inc_delete:
            btnDelete = wx.Button(self.panel, wx.ID_DELETE)
            btnDelete.Bind(wx.EVT_BUTTON, self.OnDelete)
        if inc_insert:
            btnInsert = wx.Button(self.panel, -1, "Insert Before")
            btnInsert.Bind(wx.EVT_BUTTON, self.OnInsert)
        # using the approach which will follow the platform convention 
        # for standard buttons
        self.szrButtons = wx.StdDialogButtonSizer()
        self.szrButtons.AddButton(btnCancel)
        self.szrButtons.AddButton(btnOK)
        self.szrButtons.Realize()
        if inc_delete:
            self.szrButtons.Insert(0, btnDelete, 0)
        if inc_insert:
            self.szrButtons.Insert(0, btnInsert, 0, wx.RIGHT, 10)

    def OnCancel(self, event):
        # no validation - just get out
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL)

    def OnOK(self, event):
        if not self.panel.Validate(): # runs validators on all assoc controls
            return True
        self.tabentry.UpdateNewGridData()
        self.Destroy()
        self.SetReturnCode(wx.ID_OK)
        
    def OnDelete(self, event):
        if not self.panel.Validate(): # runs validators on all assoc controls
            return True
        selected_rows = self.tabentry.grid.GetSelectedRows()
        if len(selected_rows) == 1:
            row = selected_rows[0]
            if row != self.tabentry.rows_n - 1:
                self.tabentry.DeleteRow(row)
        else:
            wx.MessageBox("Only one row can be deleted at a time")
    
    def OnInsert(self, event):
        """
        Insert before
        """
        if not self.panel.Validate(): # runs validators on all assoc controls
            return True
        selected_rows = self.tabentry.grid.GetSelectedRows()
        if not selected_rows: 
            return
        pos = selected_rows[0]
        self.tabentry.InsertRow(pos)
        
    
def row_validation(row, grid, col_dets):
    """
    Very simple as default - each cell must have something unless empty_ok.
    """
    row_valid = True
    for i, col_det in enumerate(col_dets):
        empty_ok = col_det.get("empty_ok", False)
        cell_val = grid.GetCellValue(row=row, col=i)
        if not cell_val and not empty_ok:
            row_valid = False
            break
    return row_valid


class TableEntry(object):
    def __init__(self, frame, panel, szr, vert_share, read_only, grid_size, 
                 col_dets, data, new_grid_data, insert_data_func=None, 
                 row_validation_func=None):
        """
        vert_share - vertical share of sizer supplied.
        col_dets - list of dic.  Keys = "col_label", "col_type", 
            and, optionally, "col_width", "file_phrase", "file_wildcard", 
            "empty_ok", "col_min_val", "col_max_val", "col_precision".
            Also "dropdown_vals" which is a list of values for the dropdown.
        data - list of tuples (must have at least one item, even if only a 
            "rename me".
        new_grid_data - is effectively "returned" - add details to it in form 
            of a list of tuples.
        insert_data_func - return row_data and receive row_idx, grid_data
        row_validation_func - return boolean and receive row, grid, col_dets
        """
        self.debug = False
        self.frame = frame
        self.panel = panel
        self.szr = szr
        self.read_only = read_only
        self.col_dets = col_dets
        self.insert_data_func = insert_data_func
        self.row_validation_func = row_validation_func if row_validation_func \
            else row_validation
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
        self.grid = wx.grid.Grid(self.panel, size=grid_size)        
        self.respond_to_select_cell = True        
        self.rows_n = len(self.data) + 1
        self.cols_n = len(self.col_dets)
        if self.rows_n > 1:
            data_cols_n = len(data[0])
            #pprint.pprint(data) # debug
            if data_cols_n != self.cols_n:
                raise Exception, "There must be one set of column details " + \
                    "per column of data (currently %s details for " + \
                    "%s columns)" % (self.cols_n, data_cols_n)
        self.grid.CreateGrid(numRows=self.rows_n,
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
            for j in range(self.rows_n):
                renderer, editor = self.GetNewRendererEditor(col_idx)
                self.grid.SetCellRenderer(j, col_idx, renderer)
                self.grid.SetCellEditor(j, col_idx, editor)
        # grid event handling
        self.grid.Bind(wx.EVT_KEY_DOWN, self.OnGridKeyDown)
        self.grid.Bind(EVT_CELL_MOVE, self.OnCellMove)        
        self.grid.Bind(wx.grid.EVT_GRID_CELL_CHANGE, self.OnCellChange)
        self.grid.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.OnSelectCell)
        self.grid.Bind(text_browser.EVT_TEXT_BROWSE_KEY_DOWN, 
                       self.OnTextBrowseKeyDown)
        self.frame.Bind(wx.grid.EVT_GRID_EDITOR_SHOWN, self.EditorShown)
        self.frame.Bind(wx.grid.EVT_GRID_EDITOR_HIDDEN, self.EditorHidden)
        self.grid.Bind(wx.grid.EVT_GRID_LABEL_LEFT_CLICK, self.OnLabelClick)        
        # misc
        for col_idx, col_det in enumerate(self.col_dets):
            self.grid.SetColLabelValue(col_idx, col_det["col_label"])
        for i in range(self.rows_n - 1):
            for j in range(self.cols_n):
                self.grid.SetCellValue(row=i, col=j, s=str(data[i][j]))
        self.grid.SetRowLabelValue(self.rows_n - 1, "*")
        self.current_row_idx = self.rows_n - 1
        self.current_col_idx = 0
        self.grid.SetGridCursor(self.rows_n - 1, 0) # triggers OnSelect
        self.grid.MakeCellVisible(self.rows_n - 1, 0)        
        self.szr.Add(self.grid, vert_share, wx.GROW|wx.ALL, 5)
    
    def OnTextBrowseKeyDown(self, event):
        if event.GetKeyCode() in [wx.WXK_RETURN]:
            self.grid.DisableCellEditControl()
            self.grid.MoveCursorDown(expandSelection=False)
    
    def GetNewRendererEditor(self, col_idx):
        """
        For a given column index, return a fresh renderer and editor object.
        Objects must be unique to cell.
        Returns renderer, editor.
        Nearly (but not quite) worth making classes ;-)
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
        elif col_type == COL_DROPDOWN:
            dropdown_vals = self.col_dets[col_idx].get("dropdown_vals")
            if dropdown_vals:
                renderer = wx.grid.GridCellStringRenderer()
                editor = wx.grid.GridCellChoiceEditor(dropdown_vals)
            else:
                raise Exception, "table_entry.GetNewRendererEditor: needed " + \
                    "to supply dropdown_vals"
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

    # processing MOVEMENTS AWAY FROM CELLS e.g. saving values //////////////////
    
    def AddCellMoveEvt(self, direction, dest_row=None, dest_col=None):
        """
        Add special cell move event.
        src_row and src_col - wherever we were last (only updated if a move is 
            validated and allowed).
        dest_row - row we are going to (None if here by keystroke - 
            yet to be determined).
        dest_col - column we are going to (as above).
        direction - MOVE_LEFT, MOVE_RIGHT, MOVE_UP, MOVE_DOWN
        """
        evt_cell_move = CellMoveEvent(myEVT_CELL_MOVE, self.grid.GetId())
        evt_cell_move.AddDets(dest_row, dest_col, direction)
        evt_cell_move.SetEventObject(self.grid)
        self.grid.GetEventHandler().AddPendingEvent(evt_cell_move)
    
    def OnSelectCell(self, event):
        """
        Capture use of move away from a cell.  May be result of mouse click 
            or a keypress.
        """
        debug = True
        if not self.respond_to_select_cell:
            self.respond_to_select_cell = True
            event.Skip()
            return
        src_row=self.current_row_idx # row being moved from
        src_col=self.current_col_idx # col being moved from
        dest_row=event.GetRow()
        dest_col=event.GetCol()
        if dest_row == src_row:
            if dest_col > src_col:
                direction = MOVE_RIGHT
            else:
                direction = MOVE_LEFT
        elif dest_col == src_col:
            if dest_row > src_row:
                direction = MOVE_DOWN
            else:
                direction = MOVE_UP
        elif dest_col > src_col and dest_row > src_row:
                direction = MOVE_DOWN_RIGHT
        elif dest_col > src_col and dest_row < src_row:
                direction = MOVE_UP_RIGHT
        elif dest_col < src_col and dest_row > src_row:
                direction = MOVE_DOWN_LEFT
        elif dest_col < src_col and dest_row < src_row:
                direction = MOVE_UP_LEFT
        else:
            raise Exception, "table_edit.OnSelectCell - where is direction?"
        if self.debug or debug: 
            print "OnSelectCell - selected row: %s, col: %s, direction: %s" % \
            (dest_row, dest_col, direction) + "********************************" 
        self.AddCellMoveEvt(direction, dest_row, dest_col)

    def OnGridKeyDown(self, event):
        """
        Potentially capture use of keypress to move away from a cell.
        The only case where we can't rely on OnSelectCell to take care of
            AddCellMoveEvt for us is if we are moving right or down from the 
            last col after a keypress.
        Must process here.  NB dest row and col yet to be determined.
        """
        debug = True
        keycode = event.GetKeyCode()
        if self.debug or debug: 
            print "OnGridKeyDown - keycode %s pressed" % keycode 
        if keycode in [wx.WXK_TAB, wx.WXK_RETURN]:
            if keycode == wx.WXK_TAB:
                if event.ShiftDown():
                    direction = MOVE_LEFT
                else:
                    direction = MOVE_RIGHT
            elif keycode == wx.WXK_RETURN:
                direction = MOVE_DOWN
            src_row=self.current_row_idx
            src_col=self.current_col_idx
            if self.debug or debug: print "OnGridKeyDown - keypress in row " + \
                "%s col %s ******************************" % (src_row, src_col)
            final_col = (src_col == len(self.col_dets) - 1)
            if final_col and direction in [MOVE_RIGHT, MOVE_DOWN]:
                self.AddCellMoveEvt(direction)
                # Do not Skip and send event on its way.
                # Smother the event here so our code can determine where the 
                # selection goes next.  Otherwise, Return will appear in cell 
                # below and trigger other responses.
            else:
                event.Skip()
        else:
            event.Skip()
    
    def OnCellMove(self, event):
        """
        Response to custom event - used to start process of validating move and
            allowing or disallowing.
        Must occur after steps like SetValue (in case of changing data) so that
            enough information is available to validate data in cell.
        Only update self.current_row_idx and self.current_col_idx once decisions
            have been made.
        Should not get here from a key move left in the first column 
            (not a cell move).
        NB must get the table to refresh itself and thus call SetValue(). Other-
            wise we can't get the value just entered so we can evaluate it for
            validation.
        """
        debug = False
        if self.debug or debug: print "OnCellMove *****************************"
        src_row=self.current_row_idx # row being moved from
        src_col=self.current_col_idx # col being moved from
        dest_row = event.dest_row # row being moved towards
        dest_col = event.dest_col # col being moved towards
        direction = event.direction
        # ProcessCellMove called from text editor as well so keep separate
        self.ProcessCellMove(src_row, src_col, dest_row, dest_col, direction)
        event.Skip()
    
    def ProcessCellMove(self, src_row, src_col, dest_row, dest_col, direction):
        "dest row and col still unknown if from a return or TAB keystroke"
        debug = True
        if self.debug or debug:
            print "ProcessCellMove - " + \
                "source row %s source col %s " % (src_row, src_col) + \
                "dest row %s dest col %s " % (dest_row, dest_col) + \
                "direction: %s" % direction
        move_type, dest_row, dest_col = self.GetMoveDets(src_row, src_col, 
                                        dest_row, dest_col, direction)
        if move_type in [MOVING_IN_EXISTING, LEAVING_EXISTING]:
            move_to_dest = self.LeavingExistingCell()
        elif move_type == MOVING_IN_NEW:
            move_to_dest = self.MovingInNewRow()
        elif move_type == LEAVING_NEW:
            move_to_dest = self.LeavingNewRow(dest_row, dest_col, direction)
        else:
            raise Exception, "ProcessCellMove - Unknown move_type"
        if self.debug or debug:
            print "Move type: %s" % move_type
            print "OK to move to dest?: %s" % move_to_dest
        if move_to_dest:
            self.respond_to_select_cell = False # to prevent infinite loop!
            self.grid.SetGridCursor(dest_row, dest_col)
            self.grid.MakeCellVisible(dest_row, dest_col)
            self.current_row_idx = dest_row
            self.current_col_idx = dest_col
        else:
            pass
            #wx.MessageBox("Stay here at %s %s" % (src_row, src_col))
    
    def GetMoveDets(self, src_row, src_col, dest_row, dest_col, direction):
        """
        Gets move details.
        Returns move_type, dest_row, dest_col.
        move_type - MOVING_IN_EXISTING, MOVING_IN_NEW, LEAVING_EXISTING, or 
            LEAVING_NEW.
        dest_row and dest_col are where we the selection should go unless there 
            is a validation issue.
        dest_row and dest_col may need to be worked out e.g. if cell move caused
            by a tab keypress.
        Take into account whether a new row or not.
        If on new row, take into account if final column.
        Main task is to decide whether to allow the move.
        If not, set focus on source.
        Decide based on validation of cell and, if a new row, the row as a 
            whole.
        Don't allow to leave cell in invalid state.
        Overview of checks made:
            If jumping around within new row, cell cannot be invalid.
            If not in a new row (i.e. in existing), cell must be ok to save.
            If leaving new row, must be ready to save whole row unless a clean
                row and moving up.
        If any rules are broken, put focus on source cell. Otherwise got to
            cell at destination row and col.
        """
        debug = True
        # 1) move type
        final_col = (src_col == len(self.col_dets) - 1)
        was_new_row = self.NewRow(self.current_row_idx)
        if debug: print "Current row idx: %s, src_row: %s, was_new_row: %s" % \
            (self.current_row_idx, src_row, was_new_row)
        dest_row_is_new = self.DestRowIsCurrentNew(src_row, dest_row, direction, 
                                                   final_col)
        if was_new_row and dest_row_is_new:
            move_type = MOVING_IN_NEW
        elif was_new_row and not dest_row_is_new:
            move_type = LEAVING_NEW
        elif not was_new_row and not dest_row_is_new:
            move_type = MOVING_IN_EXISTING
        elif not was_new_row and dest_row_is_new:
            move_type = LEAVING_EXISTING
        else:
            raise Exception, "table_edit.GetMoveDets().  Unknown move."
        # 2) dest row and dest col
        if dest_row is None and dest_col is None: # known if from OnSelectCell
            if final_col and direction in [MOVE_RIGHT, MOVE_DOWN]:
                dest_row = src_row + 1
                dest_col = 0
            else:
                if direction == MOVE_RIGHT:
                    dest_row = src_row
                    dest_col = src_col + 1
                elif direction == MOVE_LEFT:                    
                    dest_row = src_row
                    dest_col = src_col - 1 if src_col > 0 else 0
                elif direction == MOVE_DOWN:
                    dest_row = src_row + 1
                    dest_col = src_col
                else:
                    raise Exception, "table_edit.GetMoveDets no " + \
                        "destination (so from a TAB or Return) yet not a " + \
                        "left, right, or down."
        return move_type, dest_row, dest_col
    
    def DestRowIsCurrentNew(self, src_row, dest_row, direction, final_col):
        """
        Is the destination row (assuming no validation problems) the current 
            new row?
        If currently on the new row and leaving it, the destination row, even 
            if it becomes a new row is not the current new row.
        """
        #organised for clarity not minimal lines of code ;-)
        if self.NewRow(src_row): # new row
            if final_col:
                # only LEFT stays in _current_ new row
                if direction == MOVE_LEFT:
                    dest_row_is_new = True
                else:
                    dest_row_is_new = False
            else: # only left and right stay in _current_ new row
                if direction in [MOVE_LEFT, MOVE_RIGHT]:
                    dest_row_is_new = True # moving sideways within new
                else:
                    dest_row_is_new = False
        elif self.NewRow(src_row + 1): # row just above the new row
            # only down (inc down left and right), or right in final col, 
            # take to new
            if direction in [MOVE_DOWN, MOVE_DOWN_LEFT, MOVE_DOWN_RIGHT] or \
                    (direction == MOVE_RIGHT and final_col):
                dest_row_is_new = True
            else:
                dest_row_is_new = False
        else: # more than one row away from new row
            dest_row_is_new = False
        return dest_row_is_new
    
    def NewRow(self, row):
        "2 rows inc new - new row if idx = 1 i.e. subtract 1"
        new_row = (row == self.rows_n - 1)
        return new_row
    
    def LeavingExistingCell(self):
        """
        Process the attempt to leave an existing cell (whether or not leaving
            existing row).
        Will not move if cell data not OK to save.
        Return move_to_dest.
        """
        if self.debug: print "Was in existing, ordinary row"
        move_to_dest = self.CellOKToSave(self.current_row_idx, 
                                         self.current_col_idx)
        return move_to_dest
    
    def MovingInNewRow(self):
        """
        Process the attempt to move away from a cell in the new row to another 
            cell in the same row.  Will not move if cell is invalid.
        Return move_to_dest.
        """
        debug = False
        if self.debug or debug: print "Moving within new row"
        move_to_dest = not self.CellInvalid(self.current_row_idx, 
                                            self.current_col_idx)
        return move_to_dest
    
    def LeavingNewRow(self, dest_row, dest_col, direction):
        """
        Process the attempt to leave a cell in the new row.
        Always OK to leave new row in an upwards direction if it has not been 
            altered (i.e. not dirty).
        Otherwise, must see if row is OK to Save.  If not, e.g. faulty data, 
            keep selection where it was.  If OK, add new row.
        Return move_to_dest.
        """
        debug = True
        
        
        
        
        is_dirty = False
        
        
        
        
        if self.debug or debug: 
            print "LeavingNewRow - dest row %s dest col %s direction %s" % \
            (dest_row, dest_col, direction)
        if direction in [MOVE_UP, MOVE_UP_RIGHT, MOVE_UP_LEFT] and not is_dirty:
            move_to_dest = True # always OK
        else: # must check OK to move
            move_to_dest = self.CellOKToSave(self.current_row_idx, 
                                             self.current_col_idx)
            if move_to_dest:
                self.AddNewRow()
        return move_to_dest
    
    
    
    # VALIDATION ///////////////////////////////////////////////////////////////
    
    
    
    def CellInvalid(self, row, col):
        return False
    
    def CellOKToSave(self, row, col):
        return True
    
   
    # MISC /////////////////////////////////////////////////////

    def TryToDeleteRow(self):
        """
        Delete row if a row selected and not the data entry row
            and put focus on new line.
        """
        selected_rows = self.grid.GetSelectedRows()
        if len(selected_rows) == 1:
            row = selected_rows[0]
            if not self.NewRow(row):
                self.DeleteRow(row)
    
    def DeleteRow(self, row):
        """
        Delete a row.
        """
        self.grid.DeleteRows(pos=row, numRows=1)
        self.rows_n -= 1
        self.grid.SetRowLabelValue(self.rows_n - 1, "*")
        self.grid.SetGridCursor(self.rows_n - 1, 0)
        self.grid.HideCellEditControl()
        self.grid.ForceRefresh()
        self.SafeLayoutAdjustment()
    
    def EditorShown(self, event):
        # disable resizing until finished
        self.grid.DisableDragColSize()
        self.grid.DisableDragRowSize()
        if event.GetRow() == self.rows_n - 1:
            self.new_editor_shown = True
        event.Skip()
        
    def EditorHidden(self, event):
        # re-enable resizing
        self.grid.EnableDragColSize()
        self.grid.EnableDragRowSize()
        self.new_editor_shown = False
        event.Skip()

    def OnCellChange(self, event):
        debug = True
        if self.debug or debug: print "Cell changed"
        self.grid.ForceRefresh()
        self.SafeLayoutAdjustment()
        event.Skip()

    def InsertRow(self, pos):
        """
        Insert row.
        If data supplied (list), insert values into row.
        Change row labels appropriately.
        """
        grid_data = self.GetGridData()
        self.grid.InsertRows(pos)
        if self.insert_data_func:
            row_data = self.insert_data_func(row_idx=pos, grid_data=grid_data)
            for col_idx in range(len(self.col_dets)):
                renderer, editor = self.GetNewRendererEditor(col_idx)
                self.grid.SetCellRenderer(pos, col_idx, renderer)
                self.grid.SetCellEditor(pos, col_idx, editor)
            for i, value in enumerate(row_data):
                self.grid.SetCellValue(pos, i, value)
        self.rows_n += 1
        # reset label for all rows after insert
        self.UpdateRowLabelsAfter(pos)
        self.grid.SetRowLabelValue(self.rows_n - 1, "*")
    
    def UpdateRowLabelsAfter(self, pos):
        for i in range(pos, self.rows_n - 1):
            self.grid.SetRowLabelValue(i, str(i + 1))
            
    def AddNewRow(self):
        """
        Add new row.
        """
        new_row = self.rows_n # e.g. 1 row 1 new (2 rows), new is 2
        # change label from * and add a new entry row on end of grid
        self.grid.AppendRows()
        # set up cell rendering and editing
        for col_idx in range(self.cols_n):
            renderer, editor = self.GetNewRendererEditor(col_idx)
            self.grid.SetCellRenderer(new_row, col_idx, renderer)
            self.grid.SetCellEditor(new_row, col_idx, editor)
        self.rows_n += 1
        self.grid.SetRowLabelValue(self.rows_n - 2, str(self.rows_n - 1))
        self.grid.SetRowLabelValue(self.rows_n - 1, "*")
        self.SafeLayoutAdjustment()
        
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

    def GetGridData(self):
        """
        Get grid data.
        """
        grid_data = []
        # get data from grid (except for final row (either empty or not saved)
        for i in range(self.rows_n - 1):
            row_data = []
            for j, col_type in enumerate(self.col_dets):
                val = self.grid.GetCellValue(row=i, col=j)
                row_data.append(val)
            grid_data.append(tuple(row_data))
        return grid_data

    def UpdateNewGridData(self):
        """
        Update new_grid_data.  Separated for reuse.
        """
        grid_data = self.GetGridData()
        self.new_grid_data += grid_data    
