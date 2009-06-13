from decimal import Decimal
import pprint
import util
import wx
import wx.grid

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

MOUSE_MOVE = "mouse move"
KEYBOARD_MOVE = "keyboard move"
MOVING_IN_NEW = "moving in new"
LEAVING_EXISTING = "leaving existing"
LEAVING_NEW = "leaving new"


class TblEditor(wx.Dialog):
    def __init__(self, parent, dbe, conn, cur, db, tbl_name, flds, var_labels,
                 idxs, read_only=True):
        self.debug = True
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
        self.grid.Bind(wx.grid.EVT_GRID_CELL_CHANGE, self.OnCellChange)
        self.grid.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.OnSelectCell)
        self.grid.Bind(wx.EVT_KEY_DOWN, self.OnGridKeyDown)
        self.szrMain.Add(self.grid, 1, wx.GROW)
        self.panel.SetSizer(self.szrMain)
        self.szrMain.SetSizeHints(self)
        self.panel.Layout()
        self.grid.SetFocus()
    
    # processing MOVEMENTS AWAY FROM CELLS e.g. saving values ////////////////
    
    def OnSelectCell(self, event):
        "OnSelectCell is fired when the mouse selects a cell"
        evt_row=self.current_row_idx
        evt_col=self.current_col_idx
        if self.debug: print "OnSelectCell - clicked on row " + \
            "%s col %s" % (evt_row, evt_col)
        self.ProcessMoveAway(event, move_source=MOUSE_MOVE, evt_row, evt_col)

    def OnGridKeyDown(self, event):
        "We are interested in TAB keypresses"
        if event.GetKeyCode() in [wx.WXK_TAB]:
            evt_row=self.current_row_idx
            evt_col=self.current_col_idx
            if self.debug: print "OnGridKeyDown - Hit TAB from row " + \
                "%s col %s" % (evt_row, evt_col)
            self.ProcessMoveAway(event, move_source=KEYBOARD_MOVE, evt_row, 
                                 evt_col)
    
    def ProcessMoveAway(self, event, move_source, evt_row, evt_col):
        """
        Process move away from a cell e.g. by mouse or keyboard.
        Take into account whether a new row or not.
        If on new row, take into account if final column.
        Main task is to decide whether to allow the move.
        If not, no event.Skip().
        Decide based on validation of cell and, if a new row, the row as a 
            whole.
        Don't allow to leave cell in invalid state.
        Check the following:
            If jumping around within new row, cell cannot be invalid.
            If not in a new row (i.e. in existing), cell must be ok to save.
            If leaving new row, must be ready to save whole row.
        If any rules are broken, abort the jump by not running event.Skip()..
        move_source - MOUSE_MOVE, KEYBOARD_MOVE
        """
        if move_source == MOUSE_MOVE:
            move_type, row_if_ok, col_if_ok = \
                self.GetMouseMoveDets(event, evt_row, evt_col)
        elif move_source == KEYBOARD_MOVE:
            move_type, row_if_ok, col_if_ok = \
                self.GetKeyboardMoveDets(event, evt_row, evt_col)
        if move_type == MOVING_IN_NEW:
            ok_to_move = self.MovingInNewRow()
        elif move_type == LEAVING_EXISTING:
            ok_to_move = self.LeavingExistingCell()
        elif move_type == LEAVING_NEW:
            ok_to_move = self.LeavingNewRow(move_source, evt_row, evt_col)
        if ok_to_move:
            self.current_row_idx = row_if_ok
            self.current_col_idx = col_if_ok
            event.Skip() # will allow us to move to the new cell
            
    def GetMouseMoveDets(self, event, evt_row, evt_col):
        """
        Gets move details.
        Returns move_type, row_if_ok, col_if_ok.
        move_type - MOVING_IN_NEW, LEAVING_EXISTING, or LEAVING_NEW.
        Moving in new: the last recorded current row is a new row and 
                the mouse event row is also new.
        Leaving existing: the last recorded current row is not a new row
        Leaving new: the last recorded current row is a new row and 
                the mouse event row is not new.
        evt_row/col is where mouse clicked to i.e. not the cell just left.
        """
        if self.debug: print "In GetMouseMoveDets trying to move to " + \
            "row %s col %s" % (evt_row, evt_col)
        was_new_row = self.NewRow(self.current_row_idx)
        jump_row_new = self.NewRow(evt_row)
        if was_new_row and jump_row_new:
            move_type = MOVING_IN_NEW
        elif not was_new_row:
            move_type = LEAVING_EXISTING
        elif was_new_row and not jump_row_new:
            move_type = LEAVING_NEW
        row_if_ok = evt_row
        col_if_ok = evt_col
        return move_type, row_if_ok, col_if_ok

    def GetKeyboardMoveDets(self, event, evt_row, evt_col):
        """
        Gets move details.
        Returns move_type, row_if_ok, col_if_ok.
        move_type - MOVING_IN_NEW, LEAVING_EXISTING, or LEAVING_NEW.
        Moving in new: the last recorded current row is a new row and the 
            current column is not the final column.
        Leaving existing: the last recorded current row is not a new row
        Leaving new: the last recorded current row is a new row and the current 
            column is the final column.
        evt_row/col is for cell keypress happened in. I.e. cell we're trying
            to leave by tabbing away.
        """
        if self.debug: print "In GetKeyboardMoveDets trying to jump to " + \
            "row %s col %s" % (evt_row, evt_col)
        is_new_row = self.NewRow(self.current_row_idx)
        final_col = (evt_col == len(self.flds) - 1)
        if is_new_row and not final_col:
            move_type = MOVING_IN_NEW
            row_if_ok = evt_row
            col_if_ok = evt_col + 1
        elif not is_new_row:
            move_type = LEAVING_EXISTING
            row_if_ok = evt_row + 1
            col_if_ok = 0
        elif is_new_row and final_col:
            move_type = LEAVING_NEW
            row_if_ok = evt_row + 1
            col_if_ok = 0
        return move_type, row_if_ok, col_if_ok
    
    def LeavingNewRow(self, move_source, evt_row, evt_col):
        """
        Process attempt to leave (a cell in) the new row.
        move_source - MOUSE_MOVE, KEYBOARD_MOVE
        Return OK to move.
        """
        if self.debug: print "Leaving new row - %s" % move_source
        # only attempt to save if value is OK to save
        if not self.CellOKToSave(self.current_row_idx, 
                                 self.current_col_idx):
            ok_to_move = False
        else:
            if move_source == KEYBOARD_MOVE:
                if self.debug: print "New buffer is %s" % self.dbtbl.new_buffer
                if self.dbtbl.new_buffer.get((row, col)) == None:
                    self.dbtbl.new_buffer[(row, col)] = \
                        db_tbl.MISSING_VAL_INDICATOR
            ok_to_move = self.SaveRow(self.current_row_idx)
        return ok_to_move 
    
    def LeavingExistingCell(self):
        """
        Process attempt to leave an existing cell.
        Return OK to move.
        """
        if self.debug: print "Was in existing, ordinary row"
        if not self.CellOKToSave(self.current_row_idx, 
                                 self.current_col_idx):
            ok_to_move = False
        else:
            if self.dbtbl.bol_attempt_cell_update:
                ok_to_move = self.UpdateCell(self.current_row_idx,
                                             self.current_col_idx)
            else:
                ok_to_move = True
        # flush
        self.dbtbl.bol_attempt_cell_update = False
        self.dbtbl.SQL_cell_to_update = None
        self.dbtbl.val_of_cell_to_update = None
        return ok_to_move
    
    def MovingInNewRow(self):
        """
        Process attempt to move away from cell in new row to another cell in the
            same row.
        Return OK to move.
        """
        if self.debug: print "Moving within new row"
        ok_to_move = not self.CellInvalid(self.current_row_idx, 
                                          self.current_col_idx)
        return ok_to_move

    # VALIDATION //////////////////////////////////////////////////////////
    
    def ValueInRange(self, raw_val, fld_dic):
        "NB may be None if N/A e.g. SQLite"
        min = fld_dic[getdata.FLD_NUM_MIN_VAL]
        max = fld_dic[getdata.FLD_NUM_MAX_VAL]        
        if min != None:
            if Decimal(raw_val) < Decimal(str(min)):
                if self.debug: print "%s is < the min of %s" % (raw_val, min)
                return False
        if max != None:
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
            if self.dbtbl.bol_attempt_cell_update:
                raw_val = self.dbtbl.val_of_cell_to_update
            else:
                raw_val = self.grid.GetCellValue(row, col)
            existing_row_data_lst = self.dbtbl.row_vals_dic.get(row)
            if existing_row_data_lst:
                prev_val = str(existing_row_data_lst[col])
            if self.debug: print "prev_val: %s raw_val: %s" % (prev_val,
                                                               raw_val)
            if raw_val == prev_val:
                if self.debug: print "Unchanged"
                return False # i.e. OK
            print "%s is changed!" % raw_val
        fld_dic = self.dbtbl.GetFldDic(col)        
        if self.debug: 
            print "\"%s\"" % raw_val
            print "Field dic is:"
            pprint.pprint(fld_dic)
        if raw_val == db_tbl.MISSING_VAL_INDICATOR:
            return False
        elif not fld_dic[getdata.FLD_DATA_ENTRY_OK]: 
             # i.e. not autonumber, timestamp etc
             # and raw_val != db_tbl.MISSING_VAL_INDICATOR unnecessary
            wx.MessageBox("This field does not accept user data entry.")
            return True # i.e. invalid, not OK
        elif fld_dic[getdata.FLD_BOLNUMERIC]:
            if not util.isNumeric(raw_val):
                wx.MessageBox("\"%s\" is not a valid number.\n\n" % raw_val + \
                              "Either enter a valid number or " + \
                              "the missing value character (.)")
                return True
            if not self.ValueInRange(raw_val, fld_dic):
                if self.debug: print "\"%s\" is invalid for data type" % raw_val
                return True
            return False
        elif fld_dic[getdata.FLD_BOLDATETIME]:
            valid_datetime, _ = util.datetime_str_valid(raw_val)
            if not valid_datetime:
                wx.MessageBox("\"%s\" is not a valid datetime.\n\n" % \
                                raw_val + \
                              "Either enter a valid date/ datetime\n" + \
                              "e.g. 31/3/2009 or 2:30pm 31/3/2009 or " + \
                              "the missing value character (.)")
                return True
            return False
        elif fld_dic[getdata.FLD_BOLTEXT]:
            max_len = fld_dic[getdata.FLD_TEXT_LENGTH]
            if max_len == None: # SQLite returns None if TEXT
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
        if self.debug: print "In GetRawVal for row %s col %s" % (row, col)
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
        if self.debug: print "In CellOKToSave row %s col %s" % (row, col)
        raw_val = self.GetRawVal(row, col)
        fld_dic = self.dbtbl.GetFldDic(col)
        missing_not_nullable_prob = \
            (raw_val == db_tbl.MISSING_VAL_INDICATOR and \
             not fld_dic[getdata.FLD_BOLNULLABLE] and \
             fld_dic[getdata.FLD_DATA_ENTRY_OK])
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
        if self.debug: print "Now updating cell row %s col %s" % (row, col)
        bolUpdatedCell = True
        try:
            self.dbtbl.cur.execute(self.dbtbl.SQL_cell_to_update)
            self.dbtbl.conn.commit()
        except Exception, e:
            if self.debug: 
                print "SaveCell failed to save %s. " % \
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
            if self.debug: print "Just inserted row in SaveRow()"
        else:
            if self.debug: print "Unable to insert row in SaveRow()"
            return False
        try:
            self.SetupNewRow(data)
            return True
        except:
            if self.debug: print "Unable to setup new row"
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
        self.FocusOnNewRow(new_row_idx)
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
            if fld_dic[getdata.FLD_BOLTEXT]:
                txt_len = fld_dic[getdata.FLD_TEXT_LENGTH]
                col_width = txt_len*pix_per_char if txt_len != None \
                    and txt_len < 25 else None # leave for auto
            elif fld_dic[getdata.FLD_BOLNUMERIC]:
                num_len = fld_dic[getdata.FLD_NUM_WIDTH]
                col_width = num_len*pix_per_char if num_len != None else None
            elif fld_dic[getdata.FLD_BOLDATETIME]:
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
        self.grid.ForceRefresh()
        event.Skip()
