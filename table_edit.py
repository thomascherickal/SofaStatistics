from decimal import Decimal
import pprint
import util
import wx
import wx.grid

import my_globals
import db_tbl
import getdata
import text_editor

"""
DbTbl is the link between the grid and the underlying data.
TextEditor is the custom grid cell editor - currently only used for the cells
    in the new row.  Needed so that the edited value can be captured when
    navigating away from a cell in editing mode (needed for validation).
TblEditor is the grid (the Dialog containing the grid).
Cell values are taken from the database in batches and cached for performance
    reasons.
Navigation around inside the grid triggers data saving (cells updated or 
    a new row added).  Validation occurs first to ensure that values will be
    acceptable to the underlying database.  If not, the cursor stays at the 
    original location.
Because the important methods such as OnSelectCell and SetValue occur in 
    a different sequence depending on whether we use the mouse or the keyboard,
    a custom event is added to the end of the event queue.  It ensures that 
    validation and decisions about where the cursor can go (or must stay) always 
    happen after the other steps are complete.
If a user enters a value, we see the new value, but nothing happens to the
    database until we move away with either the mouse or keyboard.
SaveRow() and UpdateCell() are where actual changes to the database are made.
When UpdateCell is called, the cache for that row is wiped to force it to be
    updated from the database itself (including data which may be entered in one 
    form and stored in another e.g. dates)
When SaveRow() is called, the cache is not updated.  It is better to force the
    grid to look up the value from the db.  Thus it will show autocreated values
    e.g. timestamp, autoincrement etc
"""
# key move directions
MOVE_LEFT = "move left"
MOVE_RIGHT = "move right"
MOVE_UP = "move up"
MOVE_DOWN = "move down"
# cell move types
MOVING_IN_NEW = "moving in new"
LEAVING_EXISTING = "leaving existing"
LEAVING_NEW = "leaving new"

class CellMoveEvent(wx.PyCommandEvent):
    "See 3.6.1 in wxPython in Action"
    def __init__(self, evtType, id):
        wx.PyCommandEvent.__init__(self, evtType, id)
    
    def AddDets(self, dest_row=None, dest_col=None, key_direction=None):
        self.dest_row = dest_row
        self.dest_col = dest_col
        self.key_direction = key_direction
    
# new event type to pass around
myEVT_CELL_MOVE = wx.NewEventType()
# event to bind to
EVT_CELL_MOVE = wx.PyEventBinder(myEVT_CELL_MOVE, 1)


class TblEditor(wx.Dialog):
    def __init__(self, parent, dbe, conn, cur, db, tbl_name, flds, var_labels,
                 idxs, read_only=True):
        self.debug = False
        wx.Dialog.__init__(self, None, 
                           title="Data from %s.%s" % (db, tbl_name),
                           size=(500, 500), pos=(300, 0),
                           style=wx.MINIMIZE_BOX | wx.MAXIMIZE_BOX | \
                           wx.RESIZE_BORDER | wx.SYSTEM_MENU | \
                           wx.CAPTION | wx.CLOSE_BOX | \
                           wx.CLIP_CHILDREN)
        self.parent = parent
        self.dbe = dbe
        self.conn = conn
        self.cur = cur
        self.tbl_name = tbl_name
        self.flds = flds
        self.panel = wx.Panel(self, -1)
        self.szrMain = wx.BoxSizer(wx.VERTICAL)
        self.grid = wx.grid.Grid(self.panel, size=(500, 600))
        self.grid.EnableEditing(not read_only)
        self.dbtbl = db_tbl.DbTbl(self.grid, self.dbe, self.conn, self.cur, 
                                  tbl_name, self.flds, var_labels, idxs, 
                                  read_only)
        self.grid.SetTable(self.dbtbl, takeOwnership=True)
        if read_only:
            self.grid.SetGridCursor(0, 0)
            self.current_row_idx = 0
            self.current_col_idx = 0
        else:
            # start at new line
            new_row_idx = self.dbtbl.GetNumberRows() - 1
            self.FocusOnNewRow(new_row_idx)
            self.SetNewRowEd(new_row_idx)
        self.SetColWidths()
        self.respond_to_select_cell = True
        self.grid.Bind(wx.grid.EVT_GRID_CELL_CHANGE, self.OnCellChange)
        self.grid.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.OnSelectCell)
        self.grid.Bind(wx.EVT_KEY_DOWN, self.OnGridKeyDown)
        self.grid.Bind(EVT_CELL_MOVE, self.OnCellMove)
        self.szrMain.Add(self.grid, 1, wx.GROW)
        self.panel.SetSizer(self.szrMain)
        self.szrMain.SetSizeHints(self)
        self.panel.Layout()
        self.grid.SetFocus()
    
    # processing MOVEMENTS AWAY FROM CELLS e.g. saving values ////////////////
    
    def AddCellMoveEvt(self, dest_row=None, dest_col=None, key_direction=None):
        """
        Add special cell move event.
        dest_row - row we are going to (None if here by keystroke - 
            yet to be determined).
        dest_col - column we are going to (as above).
        key_direction - MOVE_LEFT, MOVE_RIGHT, MOVE_UP, MOVE_DOWN
        """
        evt_cell_move = CellMoveEvent(myEVT_CELL_MOVE, self.grid.GetId())
        evt_cell_move.AddDets(dest_row, dest_col, key_direction)
        evt_cell_move.SetEventObject(self.grid)
        self.grid.GetEventHandler().AddPendingEvent(evt_cell_move)
    
    def OnSelectCell(self, event):
        """
        Capture use of move away from a cell.  May be result of mouse click 
            or a keypress.
        """
        if not self.respond_to_select_cell:
            self.respond_to_select_cell = True
            event.Skip()
            return
        dest_row=event.GetRow()
        dest_col=event.GetCol()
        if self.debug: print "OnSelectCell - selected row %s col %s " % \
            (dest_row, dest_col) + "**********************************" 
        self.AddCellMoveEvt(dest_row, dest_col)
        
    def OnGridKeyDown(self, event):
        """
        Capture use of keypress to move away from a cell.
        The only case where we can't rely on OnSelectCell to take care of
            AddCellMoveEvt for us is if we are moving right from the last col
            after a keypress.
        """
        keycode = event.GetKeyCode()
        if self.debug: 
            print "OnGridKeyDown - keycode %s pressed" % keycode 
        if keycode in [wx.WXK_TAB, wx.WXK_RETURN]:
            if event.ShiftDown() and keycode == wx.WXK_TAB:
                key_direction = MOVE_LEFT
            else:
                key_direction = MOVE_RIGHT
            src_row=self.current_row_idx
            src_col=self.current_col_idx
            if self.debug: print "OnGridKeyDown - keypress in row " + \
                "%s col %s ******************************" % (src_row, src_col)
            final_col = (src_col == len(self.flds) - 1)
            if final_col and key_direction == MOVE_RIGHT:
                self.AddCellMoveEvt(dest_row=None, dest_col=None, 
                                    key_direction=MOVE_RIGHT)
                event.Skip()
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
        if self.debug: print "OnCellMove ************************************"
        src_row=self.current_row_idx # row being moved from
        src_col=self.current_col_idx # col being moved from
        dest_row = event.dest_row # row being moved towards
        dest_col = event.dest_col # col being moved towards
        key_direction = event.key_direction
        self.ProcessCellMove(src_row, src_col, dest_row, dest_col, 
                             key_direction)
        event.Skip()
    
    def ProcessCellMove(self, src_row, src_col, dest_row, dest_col, 
                        key_direction):
        self.dbtbl.ForceRefresh()
        if self.debug:
            print "ProcessCellMove - " + \
                "source row %s source col %s " % (src_row, src_col) + \
                "dest row %s dest col %s " % (dest_row, dest_col) + \
                "key direction: %s" % key_direction
        move_type, dest_row, dest_col = self.GetMoveDets(src_row, src_col, 
                                        dest_row, dest_col, key_direction)
        if move_type == LEAVING_EXISTING:
            move_to_dest = self.LeavingExistingCell()
        elif move_type == MOVING_IN_NEW:
            move_to_dest = self.MovingInNewRow()
        elif move_type == LEAVING_NEW:
            move_to_dest = self.LeavingNewRow(dest_row, dest_col)
        else:
            raise Exception, "ProcessCellMove - Unknown move_type"
        if self.debug:
            print "Move type: %s" % move_type
            print "OK to move to dest?: %s" % move_to_dest
        if move_to_dest:
            self.respond_to_select_cell = False # to prevent infinite loop!
            self.grid.SetGridCursor(dest_row, dest_col)
            self.grid.MakeCellVisible(dest_row, dest_col)
            self.current_row_idx = dest_row
            self.current_col_idx = dest_col
    
    def GetMoveDets(self, src_row, src_col, dest_row, dest_col, key_direction):
        """
        Gets move details.
        Returns move_type, dest_row, dest_col.
        move_type - MOVING_IN_NEW, LEAVING_EXISTING, or LEAVING_NEW.
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
            If leaving new row, must be ready to save whole row.
        If any rules are broken, put focus on source cell. Otherwise got to
            cell at destination row and col.
        """            
        # 1) move type
        final_col = (src_col == len(self.flds) - 1)
        was_new_row = self.NewRow(self.current_row_idx)
        dest_row_is_new = self.DestRowIsNew(src_row, dest_row, key_direction, 
                                            final_col)
        if was_new_row and dest_row_is_new:
            move_type = MOVING_IN_NEW
        elif not was_new_row:
            move_type = LEAVING_EXISTING
        elif was_new_row and not dest_row_is_new:
            move_type = LEAVING_NEW
        # 2) dest row and dest col
        if key_direction: # otherwise ok as is
            if key_direction == MOVE_RIGHT and final_col:
                dest_row = src_row + 1
                dest_col = 0
            else:
                dest_row = src_row
                if key_direction == MOVE_RIGHT:
                    dest_col = src_col + 1
                else:
                    dest_col = src_col - 1
        return move_type, dest_row, dest_col
    
    def DestRowIsNew(self, src_row, dest_row, key_direction, final_col):
        "Is the destination row the new row?"
        if key_direction:
            if self.NewRow(src_row) and key_direction == MOVE_RIGHT \
                    and not final_col:
                dest_row_is_new = True
            elif self.NewRow(src_row) and not key_direction == MOVE_RIGHT:
                # Should not get here from a move left in the first column 
                # (not a cell move) - see OnCellMove.
                dest_row_is_new = True
            else:
                dest_row_is_new = False
        elif dest_row is not None:
            dest_row_is_new = self.NewRow(dest_row)
        else:
            raise Exception, "Not a key move yet no destination row stored"
        return dest_row_is_new
    
    def LeavingExistingCell(self):
        """
        Process the attempt to leave an existing cell.
        Will not move if cell data not OK to save.
        Will update a cell if there is changed data and if it is valid.
        Return move_to_dest.
        """
        if self.debug: print "Was in existing, ordinary row"
        if not self.CellOKToSave(self.current_row_idx, 
                                 self.current_col_idx):
            move_to_dest = False
        else:
            if self.dbtbl.bol_attempt_cell_update:
                move_to_dest = self.UpdateCell(self.current_row_idx,
                                               self.current_col_idx)
            else:
                move_to_dest = True
        # flush
        self.dbtbl.bol_attempt_cell_update = False
        self.dbtbl.SQL_cell_to_update = None
        self.dbtbl.val_of_cell_to_update = None
        return move_to_dest
    
    def MovingInNewRow(self):
        """
        Process the attempt to move away from a cell in the new row to another 
            cell in the same row.  Will not move if cell is invalid.
        Return move_to_dest.
        """
        if self.debug: print "Moving within new row"
        move_to_dest = not self.CellInvalid(self.current_row_idx, 
                                            self.current_col_idx)
        return move_to_dest
    
    def LeavingNewRow(self, dest_row, dest_col):
        """
        Process the attempt to leave a cell in the new row.
        Will not move if the cell is not OK to save or if the attempt to save 
            the row failed.
        Return move_to_dest.
        """
        if self.debug: print "LeavingNewRow - dest row %s dest col %s" % \
            (dest_row, dest_col)
        # only attempt to save if new row is dirty and value is OK to save
        if self.dbtbl.new_is_dirty:
            if not self.CellOKToSave(self.current_row_idx, 
                                     self.current_col_idx):
                move_to_dest = False
            else:
                move_to_dest = self.SaveRow(self.current_row_idx)
        else:
            move_to_dest = True
        return move_to_dest

    # VALIDATION //////////////////////////////////////////////////////////
    
    def ValueInRange(self, raw_val, fld_dic):
        "NB may be None if N/A e.g. SQLite"
        min = fld_dic[my_globals.FLD_NUM_MIN_VAL]
        max = fld_dic[my_globals.FLD_NUM_MAX_VAL]        
        if min is not None:
            if Decimal(raw_val) < Decimal(str(min)):
                if self.debug: print "%s is < the min of %s" % (raw_val, min)
                return False
        if max is not None:
            if Decimal(raw_val) > Decimal(str(max)):
                if self.debug: print "%s is > the max of %s" % (raw_val, max)
                return False
        if self.debug: print "%s was accepted" % raw_val
        return True
    
    def CellInvalid(self, row, col):
        """
        Does a cell contain a value which shouldn't be allowed (even
            temporarily)?
        Values which are OK to allow temporarily are missing values 
            where data is required (for saving).
        If field numeric, value must be numeric ;-)
            Cannot be negative if unsigned.
            Must not be too big (turn 1.00 into 1 first etc).
            And if a not decimal, cannot have decimal places.
        If field is datetime, value must be valid date (or datetime).
        If field is text, cannot be longer than maximum length.
        """
        if self.debug: print "In CellInvalid for row %s col %s" % (row, col)
        cell_invalid = False # innocent until proven guilty
        if self.dbtbl.NewRow(row):
            if self.debug: print "New buffer is %s" % self.dbtbl.new_buffer
            raw_val = self.dbtbl.new_buffer.get((row, col), 
                                                db_tbl.MISSING_VAL_INDICATOR)
        else:
            raw_val = self.GetRawVal(row, col)
            existing_row_data_lst = self.dbtbl.row_vals_dic.get(row)
            if existing_row_data_lst:
                prev_val = str(existing_row_data_lst[col])
            if self.debug: print "prev_val: %s raw_val: %s" % (prev_val, 
                                                               raw_val)
            if raw_val == prev_val:
                if self.debug: print "Unchanged"
                return False # i.e. OK
            if self.debug: print "%s is changed!" % raw_val
        fld_dic = self.dbtbl.GetFldDic(col)        
        if self.debug: 
            print "\"%s\"" % raw_val
            print "Field dic is:"
            pprint.pprint(fld_dic)
        if raw_val == db_tbl.MISSING_VAL_INDICATOR or raw_val is None:
            return False
        elif not fld_dic[my_globals.FLD_DATA_ENTRY_OK]: 
             # i.e. not autonumber, timestamp etc
             # and raw_val != db_tbl.MISSING_VAL_INDICATOR unnecessary
            wx.MessageBox("This field does not accept user data entry.")
            return True # i.e. invalid, not OK
        elif fld_dic[my_globals.FLD_BOLNUMERIC]:
            if not util.isNumeric(raw_val):
                wx.MessageBox("\"%s\" is not a valid number.\n\n" % raw_val + \
                              "Either enter a valid number or " + \
                              "the missing value character (.)")
                return True
            if not self.ValueInRange(raw_val, fld_dic):
                if self.debug: print "\"%s\" is invalid for data type" % raw_val
                return True
            return False
        elif fld_dic[my_globals.FLD_BOLDATETIME]:
            valid_datetime, _ = util.valid_datetime_str(raw_val)
            if not valid_datetime:
                wx.MessageBox("\"%s\" is not a valid datetime.\n\n" % \
                                raw_val + \
                              "Either enter a valid date/ datetime\n" + \
                              "e.g. 31/3/2009 or 2:30pm 31/3/2009\nor " + \
                              "the missing value character (.)")
                return True
            return False
        elif fld_dic[my_globals.FLD_BOLTEXT]:
            max_len = fld_dic[my_globals.FLD_TEXT_LENGTH]
            if max_len is None: # SQLite returns None if TEXT
                return False
            if len(raw_val) > max_len:
                wx.MessageBox("\"%s\" is longer than the maximum of %s" % \
                              (raw_val, max_len) + "Either enter a shorter" + \
                              "value or the missing value character (.)")
                return True
            return False
        else:
            raise Exception, "Field supposedly not numeric, datetime, or text"
    
    def GetRawVal(self, row, col):
        """
        What was the value of a cell?
        If it has just been edited, GetCellValue(), which calls 
            dbtbl.GetValue(), will not work.  It will get the cached version
            which is now out-of-date (we presumably just changed it).
        """
        if self.debug: print "GetRawVal - row %s col %s" % (row, col)
        if self.dbtbl.bol_attempt_cell_update:
            raw_val = self.dbtbl.val_of_cell_to_update
        else:
            raw_val = self.grid.GetCellValue(row, col)
        return raw_val
    
    def CellOKToSave(self, row, col):
        """
        Cannot be an invalid value (must be valid or missing value).
        And if missing value, must be nullable field.
        """
        if self.debug: print "CellOKToSave - row %s col %s" % (row, col)
        raw_val = self.GetRawVal(row, col)
        fld_dic = self.dbtbl.GetFldDic(col)
        missing_not_nullable_prob = \
            (raw_val == db_tbl.MISSING_VAL_INDICATOR and \
             not fld_dic[my_globals.FLD_BOLNULLABLE] and \
             fld_dic[my_globals.FLD_DATA_ENTRY_OK])
        if missing_not_nullable_prob:
            wx.MessageBox("This field will not allow missing values to " + \
                          "be stored")
        ok_to_save = not self.CellInvalid(row, col) and \
            not missing_not_nullable_prob
        return ok_to_save

    # CHANGING DATA /////////////////////////////////////////////////////////
       
    def UpdateCell(self, row, col):
        """
        Returns boolean - True if updated successfully.
        Update cell.
        Clear row from cache so forced to update with database values e.g. 
            typed in 2pm and stored in CCYY-MM-DD HH:mm:ss as today's date time 
            stamp but at 2pm.
        """
        if self.debug: print "UpdateCell - row %s col %s" % (row, col)
        bolUpdatedCell = True
        try:
            self.dbtbl.cur.execute(self.dbtbl.SQL_cell_to_update)
            self.dbtbl.conn.commit()
        except Exception, e:
            if self.debug: 
                print "UpdateCell failed to save %s. " % \
                    self.dbtbl.SQL_cell_to_update + \
                    "Orig error: %s" % e
            bolUpdatedCell = False
        if self.dbtbl.row_vals_dic.get(row):
            del self.dbtbl.row_vals_dic[row] # force a fresh read
        self.dbtbl.grid.ForceRefresh()
        return bolUpdatedCell
    
    def SaveRow(self, row):
        data = []
        fld_names = getdata.FldsDic2FldNamesLst(self.flds) # sorted list
        for col in range(len(self.flds)):
            raw_val = self.dbtbl.new_buffer.get((row, col), None)
            if raw_val == db_tbl.MISSING_VAL_INDICATOR:
                raw_val = None
            fld_name = fld_names[col]
            fld_dic = self.flds[fld_name]
            data.append((raw_val, fld_name, fld_dic))
        row_inserted = getdata.InsertRow(self.dbe, self.conn, self.cur, 
                                         self.tbl_name, data)
        if row_inserted:
            if self.debug: print "SaveRow - Just inserted row"
        else:
            if self.debug: print "SaveRow - Unable to insert row"
            return False
        try:
            self.SetupNewRow(data)
            return True
        except:
            if self.debug: print "SaveRow - Unable to setup new row"
            return False

    def SetupNewRow(self, data):
        """
        Setup new row ready to receive new data.
        data = [(value as string (or None), fld_name, fld_dets), ...]
        """
        self.dbtbl.SetRowIdDic()
        self.dbtbl.SetNumberRows() # need to refresh        
        new_row_idx = self.dbtbl.GetNumberRows() - 1
        data_tup = tuple([x[0] for x in data])
        # do not add to row_vals_dic - force it to look it up from the db
        # will thus show autocreated values e.g. timestamp, autoincrement etc
        self.DisplayNewRow()
        self.ResetRowLabels(new_row_idx)
        self.InitNewRowBuffer()
        self.ResetPrevRowEd(new_row_idx - 1)
        self.SetNewRowEd(new_row_idx)
    
    def DisplayNewRow(self):
        "Display a new entry row on end of grid"
        self.dbtbl.DisplayNewRow()
    
    def ResetRowLabels(self, row):
        "Reset new row label and restore previous new row label to default"
        prev_row = row - 1
        self.grid.SetRowLabelValue(prev_row, str(prev_row))
        self.grid.SetRowLabelValue(row, "*")
    
    def InitNewRowBuffer(self):
        "Initialise new row buffer"
        self.dbtbl.new_is_dirty = False
        self.dbtbl.new_buffer = {}
    
    def FocusOnNewRow(self, new_row_idx):
        "Focus on cell in new row - set current to refer to that cell etc"
        self.grid.SetGridCursor(new_row_idx, 0)
        self.grid.MakeCellVisible(new_row_idx, 0)
        self.current_row_idx = new_row_idx
        self.current_col_idx = 0

    def ResetPrevRowEd(self, prev_row_idx):
        "Set new line custom cell editor for new row"
        for col_idx in range(len(self.flds)):
            self.grid.SetCellEditor(prev_row_idx, col_idx, 
                                    wx.grid.GridCellTextEditor())

    def SetNewRowEd(self, new_row_idx):
        "Set new line custom cell editor for new row"
        for col_idx in range(len(self.flds)):
            text_ed = text_editor.TextEditor(self, new_row_idx, col_idx, 
                                new_row=True, new_buffer=self.dbtbl.new_buffer)
            self.grid.SetCellEditor(new_row_idx, col_idx, text_ed)

    # MISC //////////////////////////////////////////////////////////////////
    
    def SetColWidths(self):
        "Set column widths based on display widths of fields"
        self.parent.AddFeedback("Setting column widths " + \
            "(%s columns for %s rows)..." % (self.dbtbl.GetNumberCols(), 
                                             self.dbtbl.GetNumberRows()))
        pix_per_char = 8
        sorted_fld_names = getdata.FldsDic2FldNamesLst(self.flds)
        for col_idx, fld_name in enumerate(sorted_fld_names):
            fld_dic = self.flds[fld_name]
            col_width = None
            if fld_dic[my_globals.FLD_BOLTEXT]:
                txt_len = fld_dic[my_globals.FLD_TEXT_LENGTH]
                col_width = txt_len*pix_per_char if txt_len is not None \
                    and txt_len < 25 else None # leave for auto
            elif fld_dic[my_globals.FLD_BOLNUMERIC]:
                num_len = fld_dic[my_globals.FLD_NUM_WIDTH]
                col_width = num_len*pix_per_char if num_len is not None \
                    else None
            elif fld_dic[my_globals.FLD_BOLDATETIME]:
                col_width = 170
            if col_width:
                if self.debug: print "Width of %s set to %s" % (fld_name, 
                                                                col_width)
                self.grid.SetColSize(col_idx, col_width)
            else:
                if self.debug: print "Autosizing %s" % fld_name
                self.grid.AutoSizeColumn(col_idx, setAsMin=False)            
            fld_name_width = len(fld_name)*pix_per_char
            # if actual column width is small and the label width is larger,
            # use label width.
            self.grid.ForceRefresh()
            actual_width = self.grid.GetColSize(col_idx)
            if actual_width < 15*pix_per_char \
                    and actual_width < fld_name_width:
                self.grid.SetColSize(col_idx, fld_name_width)
            if self.debug: print "%s %s" % (fld_name, 
                                            self.grid.GetColSize(col_idx))
        self.parent.AddFeedback("")
    
    def NewRow(self, row):
        new_row = self.dbtbl.NewRow(row)
        return new_row
        
    def OnCellChange(self, event):
        debug = False
        if debug: print "Cell changed"
        self.grid.ForceRefresh()
        event.Skip()
