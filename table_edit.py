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
"""

        
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
        self.grid.Bind(wx.grid.EVT_GRID_CELL_CHANGE, self.OnCellChange)
        self.grid.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.OnSelectCell)
        self.grid.Bind(wx.EVT_KEY_DOWN, self.OnGridKeyDown)
        self.szrMain.Add(self.grid, 1, wx.GROW)
        self.panel.SetSizer(self.szrMain)
        self.szrMain.SetSizeHints(self)
        self.panel.Layout()
        self.grid.SetFocus()

    def OnGridKeyDown(self, event):
        if event.GetKeyCode() in [wx.WXK_TAB]:
            row = self.current_row_idx
            col = self.current_col_idx
            if self.dbtbl.NewRow(row):
                if self.debug: print "New buffer is %s" % self.dbtbl.new_buffer
                raw_val = self.dbtbl.new_buffer.get((row, col), 
                                                db_tbl.MISSING_VAL_INDICATOR)
            else:
                raw_val = self.grid.GetCellValue(row, col)
            if self.debug:
                print "[OnGridKeyDown] Tabbing away from field with " + \
                    "value \"%s\"" % raw_val
            if self.NewRow(row):
                if self.debug: print "Tabbing within new row"
                self.dbtbl.new_buffer[(row, col)] = raw_val
                final_col = (col == len(self.flds) - 1)
                if final_col:
                    # only attempt to save if value is OK to save
                    if not self.CellOKToSave(row, col):
                        self.grid.SetFocus()
                        return
                    if self.debug: 
                        print "OnGridKeyDown - Trying to leave new record"
                    saved_ok = self.SaveRow(row)
                    if saved_ok:
                        if self.debug: print "OnGridKeyDown - Was able " + \
                            "to save record after tabbing away"
                    else:
                        # CellOkToSave obviously failed to give correct answer
                        if self.debug: print "OnGridKeyDown - Unable to " + \
                            "save record after tabbing away"
                        wx.MessageBox("Unable to save record - please " + \
                                      "check values")
                    return
        event.Skip()

    def SetNewRowEd(self, new_row_idx):
        "Set new line custom cell editor for new row"
        for col_idx in range(len(self.flds)):
            text_ed = text_editor.TextEditor(self, new_row_idx, col_idx, 
                                new_row=True, new_buffer=self.dbtbl.new_buffer)
            self.grid.SetCellEditor(new_row_idx, col_idx, text_ed)
    
    def FocusOnNewRow(self, new_row_idx):
        "Focus on cell in new row - set current to refer to that cell etc"
        self.grid.SetGridCursor(new_row_idx, 0)
        self.grid.MakeCellVisible(new_row_idx, 0)
        self.current_row_idx = new_row_idx
        self.current_col_idx = 0
    
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
    
    def OnSelectCell(self, event):
        """
        Prevent selection away from a record still in process of being saved,
            whether by mouse or keyboard, unless saved OK.
        Don't allow to leave cell in invalid state.
        Check the following:
            If jumping around within new row, cell cannot be invalid.
            If not in a new row (i.e. in existing), cell must be ok to save.
            If leaving new row, must be ready to save whole row.
        If any rules are broken, abort the jump.
        """
        row = event.GetRow()
        col = event.GetCol()
        was_new_row = self.NewRow(self.current_row_idx)
        jump_row_new = self.NewRow(row)
        if was_new_row and jump_row_new: # jumping within new
            if self.debug: print "Jumping within new row"
            ok_to_move = not self.CellInvalid(self.current_row_idx, 
                                              self.current_col_idx)
        elif not was_new_row:
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
            self.dbtbl.bol_attempt_cell_update = False # unset tag
            self.dbtbl.SQL_cell_to_update = None # to flush out unexpected bugs
            self.dbtbl.val_of_cell_to_update = None # to flush out bugs
        elif was_new_row and not jump_row_new: # leaving new row
            if self.debug: print "Leaving new row"
            # only attempt to save if value is OK to save
            if not self.CellOKToSave(self.current_row_idx, 
                                     self.current_col_idx):
                ok_to_move = False
            else:
                ok_to_move = self.SaveRow(self.current_row_idx)
        if ok_to_move:
            self.current_row_idx = row
            self.current_col_idx = col
            event.Skip() # will allow us to move to the new cell
    
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
    
    def CellOKToSave(self, row, col):
        """
        Cannot be an invalid value (must be valid or missing value).
        And if missing value, must be nullable field.
        """
        raw_val = self.grid.GetCellValue(row, col)
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

    def InitNewRowBuffer(self):
        "Initialise new row buffer"
        self.dbtbl.new_is_dirty = False
        self.dbtbl.new_buffer = {}

    def ResetPrevRowEd(self, prev_row_idx):
        "Set new line custom cell editor for new row"
        for col_idx in range(len(self.flds)):
            self.grid.SetCellEditor(prev_row_idx, col_idx, 
                                    wx.grid.GridCellTextEditor())

    def SetupNewRow(self, data):
        """
        Setup new row ready to receive new data.
        data = [(value as string, fld_name, fld_dets), ...]
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
    
    def UpdateCell(self, row, col):
        """
        Returns boolean - True if updated successfully.
        Update cell and update cache.
        """
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
        try:
            existing_row_data_lst = self.dbtbl.row_vals_dic.get(row)
            if existing_row_data_lst:
                existing_row_data_lst[col] = self.dbtbl.val_of_cell_to_update
        except Exception, e:
            raise Exception, "Failed to update cache when updating cell. " + \
                "Orig error: %s" % e 
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
        
    def OnCellChange(self, event):
        self.grid.ForceRefresh()
        event.Skip()
