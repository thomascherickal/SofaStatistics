from __future__ import print_function
from decimal import Decimal
import pprint
import wx
import wx.grid

import my_globals as mg
import lib
import getdata
import dbe_plugins.dbe_sqlite as dbe_sqlite 
import db_tbl
import projects

"""
DbTbl is the link between the grid and the underlying data.
TblEditor is the grid (the Dialog containing the grid).
Cell values are taken from the database in batches and cached for performance
    reasons.
Navigation around inside the grid triggers data saving (cells updated or 
    a new row added). Validation occurs first to ensure that values will be
    acceptable to the underlying database. If not, the cursor stays at the 
    original location.
Because the important methods such as on_select_cell and SetValue occur in 
    a different sequence depending on whether we use the mouse or the keyboard,
    a custom event is added to the end of the event queue. It ensures that 
    validation and decisions about where the cursor can go (or must stay) always 
    happen after the other steps are complete.
If a user enters a value, we see the new value, but nothing happens to the
    database until we move away with either the mouse or keyboard.
save_row() and update_cell() are where actual changes to the database are made.
When update_cell is called, the cache for that row is wiped to force it to be
    updated from the database itself (including data which may be entered in one 
    form and stored in another e.g. dates)
When save_row() is called, the cache is not updated. It is better to force the
    grid to look up the value from the db.  Thus it will show autocreated values
    e.g. timestamp, autoincrement etc
Intended behaviour: tabbing moves left and right. If at end, takes to next line
    if possible. Return moves down if possible or, if at end, to start of next
    line if possible.
"""


class CellMoveEvent(wx.PyCommandEvent):
    "See 3.6.1 in wxPython in Action"
    def __init__(self, evtType, id):
        wx.PyCommandEvent.__init__(self, evtType, id)
    
    def add_dets(self, dest_row=None, dest_col=None, direction=None):
        self.dest_row = dest_row
        self.dest_col = dest_col
        self.direction = direction
    
# new event type to pass around
myEVT_CELL_MOVE = wx.NewEventType()
# event to bind to
EVT_CELL_MOVE = wx.PyEventBinder(myEVT_CELL_MOVE, 1)

def get_display_dims(maxheight, iswindows):
    mywidth = 900
    if iswindows:
        mid_height = 820
        unavailable_height = 40 # 20 OK for normal height taskbars only
    else:
        mid_height = 910
        unavailable_height = 110
    if maxheight <= 620:
        myheight = 600
    elif maxheight <= mid_height:
        myheight = maxheight - unavailable_height
    else:
        mywidth = 1000
        myheight = 800
    return mywidth, myheight


class TblEditor(wx.Dialog):
    def __init__(self, parent, var_labels, var_notes, var_types, val_dics, 
                 readonly=True, set_col_widths=True):
        self.debug = False
        dd = getdata.get_dd()
        self.readonly = readonly
        title = _("Data from ") + "%s.%s" % (dd.db, dd.tbl)
        if self.readonly:
            title += _(" (Read Only)")
        wx.Dialog.__init__(self, None, title=title, 
                           pos=(mg.HORIZ_OFFSET, 0), 
                           style=wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX|\
                           wx.RESIZE_BORDER|wx.CLOSE_BOX|wx.SYSTEM_MENU|\
                           wx.CAPTION|wx.CLIP_CHILDREN)
        self.parent = parent
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.var_labels = var_labels
        self.var_notes = var_notes
        self.var_types = var_types
        self.val_dics = val_dics
        self.panel = wx.Panel(self, -1)
        self.szr_main = wx.BoxSizer(wx.VERTICAL)
        width_grid = 500
        height_grid = 500
        self.grid = wx.grid.Grid(self.panel, size=(width_grid, height_grid))
        self.grid.EnableEditing(not self.readonly)
        self.dbtbl = db_tbl.DbTbl(self.grid, var_labels, self.readonly)
        self.grid.SetTable(self.dbtbl, takeOwnership=True)
        self.readonly_cols = []
        if self.readonly:
            col2select = 0
            self.grid.SetGridCursor(0, col2select)
            self.current_row_idx = 0
            self.current_col_idx = col2select
            for idx_col in range(len(dd.flds)):
                attr = wx.grid.GridCellAttr()
                attr.SetBackgroundColour(mg.READONLY_COLOUR)
                self.grid.SetColAttr(idx_col, attr)
        else:
            # disable any columns which do not allow data entry and set colour
            col2select = None # first editable col
            for idx_col in range(len(dd.flds)):
                fld_dic = self.dbtbl.get_fld_dic(idx_col)
                if not fld_dic[mg.FLD_DATA_ENTRY_OK]:
                    self.readonly_cols.append(idx_col)
                    attr = wx.grid.GridCellAttr()
                    attr.SetReadOnly(True)
                    attr.SetBackgroundColour(mg.READONLY_COLOUR)
                    self.grid.SetColAttr(idx_col, attr)
                elif col2select is None: # set once
                    col2select = idx_col
            col2select = 0 if col2select is None else col2select
            # start at new line
            new_row_idx = self.dbtbl.GetNumberRows() - 1
            self.focus_on_new_row(new_row_idx, col2select)
            self.current_row_idx = new_row_idx
            self.current_col_idx = col2select
            self.set_new_row_ed(new_row_idx)
        self.col2select = col2select # used to determine where cursor should 
            # land when moving from end of new row.
        self.any_editor_shown = False
        if set_col_widths:
            self.set_col_widths()
        self.grid.GetGridColLabelWindow().SetToolTipString(_("Right click "
                                            "variable to view/edit details"))
        self.respond_to_select_cell = True
        self.control = None
        self.grid.Bind(wx.grid.EVT_GRID_CELL_CHANGE, self.on_cell_change)
        self.grid.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.on_select_cell)
        self.grid.Bind(wx.EVT_KEY_DOWN, self.on_grid_key_down)
        self.grid.Bind(EVT_CELL_MOVE, self.on_cell_move)
        self.Bind(wx.grid.EVT_GRID_EDITOR_CREATED, self.on_grid_editor_created)
        self.Bind(wx.grid.EVT_GRID_EDITOR_SHOWN, self.on_editor_shown)
        self.Bind(wx.grid.EVT_GRID_EDITOR_HIDDEN, self.on_editor_hidden)
        self.prev_row_col = (None, None)
        self.grid.GetGridWindow().Bind(wx.EVT_MOTION, self.on_mouse_move)
        self.grid.Bind(wx.grid.EVT_GRID_LABEL_RIGHT_CLICK, 
                       self.on_label_rclick)
        szr_bottom = wx.FlexGridSizer(rows=1, cols=2, hgap=5, vgap=5)
        szr_bottom.AddGrowableCol(0,2) # idx, propn
        btn_size_cols = wx.Button(self.panel, -1, _("Resize column widths"))
        btn_size_cols.Bind(wx.EVT_BUTTON, self.on_size_cols)
        btn_close = wx.Button(self.panel, wx.ID_CLOSE)
        btn_close.Bind(wx.EVT_BUTTON, self.on_close)
        szr_bottom.Add(btn_size_cols, 0)
        szr_bottom.Add(btn_close, 0, wx.ALIGN_RIGHT)
        self.szr_main.Add(self.grid, 1, wx.GROW)
        self.szr_main.Add(szr_bottom, 0, wx.GROW|wx.ALL, 5)
        self.panel.SetSizer(self.szr_main)
        szr_lst = [self.grid, szr_bottom]
        iswindows = (mg.PLATFORM == mg.WINDOWS)
        mywidth, myheight = get_display_dims(maxheight=mg.MAX_HEIGHT,
                                             iswindows=iswindows)
        lib.set_size(window=self, szr_lst=szr_lst, width_init=mywidth, 
                     height_init=myheight)
        self.grid.SetFocus()
    
    # processing MOVEMENTS AWAY FROM CELLS e.g. saving values //////////////////
    
    def add_cell_move_evt(self, direction, dest_row=None, dest_col=None):
        """
        Add special cell move event.
        src_row and src_col - wherever we were last (only updated if a move is 
            validated and allowed).
        dest_row - row we are going to (None if here by keystroke - 
            yet to be determined).
        dest_col - column we are going to (as above).
        direction - MOVE_LEFT, MOVE_RIGHT, MOVE_UP, etc
        """
        evt_cell_move = CellMoveEvent(myEVT_CELL_MOVE, self.grid.GetId())
        evt_cell_move.add_dets(dest_row, dest_col, direction)
        evt_cell_move.SetEventObject(self.grid)
        self.grid.GetEventHandler().AddPendingEvent(evt_cell_move)
    
    def on_select_cell(self, event):
        """
        Capture use of move away from a cell. May be result of mouse click 
            or a keypress.
        """
        debug = False
        see_native_bvr = False
        if see_native_bvr:
            print("SHOWING NATIVE BVR !!!!!!!")
            event.Skip()
            return
        if not self.respond_to_select_cell:
            self.respond_to_select_cell = True
            event.Skip()
            return
        src_row = self.current_row_idx # row being moved from
        src_col = self.current_col_idx # col being moved from
        dest_row = event.GetRow()
        dest_col = event.GetCol()
        if dest_row == src_row:
            if dest_col > src_col:
                direction = mg.MOVE_RIGHT
            else:
                direction = mg.MOVE_LEFT
        elif dest_col == src_col:
            if dest_row > src_row:
                direction = mg.MOVE_DOWN
            else:
                direction = mg.MOVE_UP
        elif dest_col > src_col and dest_row > src_row:
                direction = mg.MOVE_DOWN_RIGHT
        elif dest_col > src_col and dest_row < src_row:
                direction = mg.MOVE_UP_RIGHT
        elif dest_col < src_col and dest_row > src_row:
                direction = mg.MOVE_DOWN_LEFT
        elif dest_col < src_col and dest_row < src_row:
                direction = mg.MOVE_UP_LEFT
        else:
            raise Exception(u"db_grid.on_select_cell - where is direction?")
        if self.debug or debug: 
            print("on_select_cell - selected row: %s, col: %s, direction: %s" %
            (dest_row, dest_col, direction) + "*******************************") 
        self.add_cell_move_evt(direction, dest_row, dest_col)
        
    def on_grid_key_down(self, event):
        """
        Normally we let on_select_cell handle cell navigation instead.
        The only case where we can't rely on on_select_cell to take care of
            add_cell_move_evt for us is if we are moving right or down from the 
            last col after a keypress.
        Potentially capture use of keypress to move away from a cell.
        Must process here. NB dest row and col yet to be determined.
        """
        debug = True
        see_native_bvr = False
        if see_native_bvr:
            print("SHOWING NATIVE BVR !!!!!!!")
            event.Skip()
            return
        dd = getdata.get_dd()
        keycode = event.GetKeyCode()
        if self.debug or debug: 
            print("on_grid_key_down - keycode %s pressed" % keycode)
        if not self.dbtbl.readonly and keycode in [wx.WXK_DELETE, 
                                                   wx.WXK_NUMPAD_DELETE]:
            # None if no deletion occurs
            if self.try_to_delete_row(assume_row_deletion_attempt=False):
                # don't skip. Smother event so delete not entered anywhere.
                return
            else:
                # set to missing value instead of empty string
                row = self.current_row_idx
                col = self.current_col_idx
                self.dbtbl.SetValue(row, col, mg.MISSING_VAL_INDICATOR)
                self.dbtbl.force_refresh()
                try: # won't work if new row
                    self.dbtbl.row_vals_dic[row][col] = mg.MISSING_VAL_INDICATOR
                except Exception, e:
                    pass
                # Don't set self.dbtbl.new_is_dirty = True because of 
                # a deletion only.
                #new_row = self.dbtbl.is_new_row(row)
                #if new_row:
                #    self.dbtbl.new_is_dirty = True
        elif keycode in [wx.WXK_TAB, wx.WXK_RETURN]:
            if keycode == wx.WXK_TAB:
                if event.ShiftDown():
                    direction = mg.MOVE_LEFT
                else:
                    direction = mg.MOVE_RIGHT
            elif keycode == wx.WXK_RETURN:
                direction = mg.MOVE_DOWN # the native bvr
            src_row=self.current_row_idx
            src_col=self.current_col_idx
            if self.debug or debug: 
                print("on_grid_key_down - keypress in row %s col %s"
                      " ******************************" % (src_row, src_col))
            final_col = (src_col == len(dd.flds) - 1)
            if final_col and direction in [mg.MOVE_RIGHT, mg.MOVE_DOWN]:
                self.add_cell_move_evt(direction)
                """
                Do not Skip and send event on its way.
                Smother the event here so our code can determine where the 
                    selection goes next. Matters when a Return which will 
                    otherwise natively appear in cell below and trigger other 
                    responses.
                """
            elif keycode == wx.WXK_RETURN:
                # A return but not at the end - normally would go down but we 
                # want to go right. Whether OK to or not will be decided when 
                # event processed.
                self.add_cell_move_evt(direction=mg.MOVE_RIGHT)
                """
                Do not Skip and send event on its way.
                Smother the event here so our code can determine where the 
                    selection goes next. Otherwise Return will cause us to 
                    natively appear in cell below and trigger other responses.
                """
            else:
                # For a TAB, will natively move right (or left with Shift) 
                # stopping at either end.
                event.Skip()
        else: # presumably entering a value :-)
            event.Skip()
            
    def ok_to_delete_row(self, row):
        """
        Can delete any row except the new row.
        Cannot delete if in middle of editing a cell.
        Returns boolean and msg.
        """
        if self.is_new_row(row):
            return False, _("Unable to delete new row")
        elif self.dbtbl.new_is_dirty:
            return False, _("Cannot delete a row while in the middle of making "
                            "a new one")
        elif self.any_editor_shown:
            return False, _("Cannot delete a row while in the middle of editing"
                            " a cell")  
        else:
            return True, None
    
    def reset_row_n(self, change=1):
        "Reset rows_n and rows_to_fill by incrementing or decrementing."
        self.dbtbl.rows_n += change
        self.dbtbl.rows_to_fill += change
    
    def try_to_delete_row(self, assume_row_deletion_attempt=True):
        """
        Delete row if a row selected and not the data entry row
            and put focus on new line.
        Return row idx deleted (or None if deletion did not occur).
        If it is assumed there was a row deletion attempt (e.g. clicked a delete 
            button), then warn if no selection.  If no such assumption, silently
            cope with situation where no selection.
        """
        selected_rows = self.grid.GetSelectedRows()
        sel_rows_n = len(selected_rows)
        if sel_rows_n == 1:
            row_idx = selected_rows[0]
            ok_to_delete, msg = self.ok_to_delete_row(row_idx)
            if ok_to_delete:
                id_fld = self.dbtbl.id_col_name
                try:
                    row_id = self.dbtbl.row_ids_lst[row_idx]
                except IndexError:
                    wx.MessageBox(_("Unable to delete row - id not found in "
                                    "list"))
                    return None
                deleted, msg = getdata.delete_row(id_fld, row_id)
                if deleted:
                    self.grid.DeleteRows(row_idx, numRows=1)
                    self.reset_row_n(change=-1)
                    self.grid.SetRowLabelValue(self.dbtbl.rows_n - 1, 
                                               mg.NEW_IS_READY)
                    self.grid.HideCellEditControl()
                    self.grid.BeginBatch()
                    msg = wx.grid.GridTableMessage(self.dbtbl, 
                            wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, row_idx, 1)
                    self.grid.ProcessTableMessage(msg)
                    msg = wx.grid.GridTableMessage(self.dbtbl, 
                                        wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
                    self.grid.ProcessTableMessage(msg)
                    self.grid.EndBatch()
                    self.grid.ForceRefresh()
                    self.respond_to_select_cell = False
                    if row_idx < self.current_row_idx:
                        self.current_row_idx -= 1
                        self.grid.SetGridCursor(self.current_row_idx, 
                                                self.current_col_idx)
                    self.grid.SetFocus()
                else:
                    wx.MessageBox(_("Unable to delete row - underlying table "
                                    "did not approve the change"))
                    return None
                # reset anything relying on this row still existing
                del self.dbtbl.row_ids_lst[row_idx]
                self.dbtbl.row_vals_dic = {} # wiped completely - need to 
                    # rebuild again as needed.
                return row_idx
            else:
                wx.MessageBox(msg)
        elif sel_rows_n == 0:
            if assume_row_deletion_attempt:
                wx.MessageBox(_("Please select a row first (click to the left "
                                "of the row)"))
            else:
                pass
        else:
            wx.MessageBox(_("Can only delete one row at a time"))
        return None
    
    def DeleteRows(self, pos, numRows):
        # wxPython
        return True
    
    def on_cell_move(self, event):
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
        src_ctrl = self.control
        src_row=self.current_row_idx # row being moved from
        src_col=self.current_col_idx # col being moved from
        dest_row = event.dest_row # row being moved towards
        dest_col = event.dest_col # col being moved towards
        direction = event.direction
        if self.debug or debug: 
            print("settings_grid.on_cell_move src_row: %s src_col %s " %
                 (src_row, src_col) + "dest_row: %s dest_col: %s " %
                 (dest_row, dest_col) + "direction %s" % direction)
        # process_cell_move called from text editor as well so keep separate
        self.process_cell_move(src_ctrl, src_row, src_col, dest_row, dest_col, 
                               direction)
        event.Skip()
    
    def process_cell_move(self, src_ctrl, src_row, src_col, dest_row, dest_col, 
                          direction):
        """
        dest row and col still unknown if from a return or TAB keystroke.
        So is the direction (could be down or down_left if end of line).
        """
        debug = False
        self.dbtbl.force_refresh()
        if self.debug or debug:
            print("process_cell_move - " +
                  "source row %s source col %s " % (src_row, src_col) +
                  "dest row %s dest col %s " % (dest_row, dest_col) +
                  "direction: %s" % direction)
        (was_final_col, was_new_row, 
         was_final_row, move_type, 
         dest_row, dest_col) = self.get_move_dets(src_row, src_col, dest_row, 
                                                  dest_col, direction)
        if move_type in [mg.MOVING_IN_EXISTING, mg.LEAVING_EXISTING]:
            move_to_dest = self.leaving_existing_cell(was_final_col, 
                                                      was_final_row, direction)
        elif move_type == mg.MOVING_IN_NEW:
            move_to_dest = self.moving_in_new_row()
        elif move_type == mg.LEAVING_NEW:
            move_to_dest = self.leaving_new_row(dest_row, dest_col, direction)
        else:
            raise Exception(u"process_cell_move - Unknown move_type")
        if self.debug or debug:
            print("Move type: %s" % move_type)
            print("OK to move to dest?: %s" % move_to_dest)
        if move_to_dest:
            self.respond_to_select_cell = False # to prevent infinite loop!
            self.grid.SetGridCursor(dest_row, dest_col)
            self.grid.MakeCellVisible(dest_row, dest_col)
            self.current_row_idx = dest_row
            self.current_col_idx = dest_col
        else:
            if debug: print("Stay here at %s %s" % (src_row, src_col))
            #self.respond_to_select_cell = False # to prevent infinite loop!
            if src_ctrl:
                if debug: 
                    print("Last control was: %s" % src_ctrl)
                    print("Control text: %s" % src_ctrl.GetValue())
                self.grid.EnableCellEditControl(enable=True)
                try:
                    src_ctrl.SetInsertionPointEnd()
                except Exception:
                    pass
    
    def get_move_dets(self, src_row, src_col, dest_row, dest_col, direction):
        """
        Gets move details.
        Returns (was_final_col, was_new_row, was_final_row, move_type, dest_row, 
                dest_col).
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
        debug = False
        dd = getdata.get_dd()
        # 1) move type
        was_final_col = (src_col == len(dd.flds) - 1)
        was_new_row = self.is_new_row(self.current_row_idx)
        was_final_row = self.is_final_row(self.current_row_idx)
        if debug: print("Current row idx: %s, src_row: %s, was_new_row: %s" %
            (self.current_row_idx, src_row, was_new_row))
        dest_row_is_new = self.dest_row_is_current_new(src_row, dest_row, 
                                                       direction, was_final_col)
        if was_new_row and dest_row_is_new:
            move_type = mg.MOVING_IN_NEW
        elif was_new_row and not dest_row_is_new:
            move_type = mg.LEAVING_NEW
        elif not was_new_row and not dest_row_is_new:
            move_type = mg.MOVING_IN_EXISTING
        elif not was_new_row and dest_row_is_new:
            move_type = mg.LEAVING_EXISTING
        else:
            raise Exception(u"db_grid.GetMoveDets().  Unknown move.")
        # 2) dest row and dest col
        if dest_row is None and dest_col is None: # known if from on_select_cell
            if was_final_col and direction in [mg.MOVE_RIGHT, mg.MOVE_DOWN]:
                dest_row = src_row + 1
                dest_col = self.col2select
            else:
                if direction == mg.MOVE_RIGHT:
                    dest_row = src_row
                    dest_col = src_col + 1
                elif direction == mg.MOVE_LEFT:                    
                    dest_row = src_row
                    dest_col = src_col - 1 if src_col > 0 else 0
                elif direction == mg.MOVE_DOWN:
                    dest_row = src_row + 1
                    dest_col = src_col
                else:
                    raise Exception(u"db_grid.GetMoveDets no destination (so "
                                    u"from a TAB or Return) yet not a left, "
                                    u"right, or down.")
        return (was_final_col, was_new_row, was_final_row, move_type, dest_row, 
                dest_col)
    
    def dest_row_is_current_new(self, src_row, dest_row, direction, final_col):
        """
        Is the destination row (assuming no validation problems) the current 
            new row?
        If currently on the new row and leaving it, the destination row, even 
            if it becomes a new row is not the current new row.
        """
        #organised for clarity not minimal lines of code ;-)
        if self.is_new_row(src_row): # new row
            if final_col:
                # only LEFT stays in _current_ new row
                if direction == mg.MOVE_LEFT:
                    dest_row_is_new = True
                else:
                    dest_row_is_new = False
            else: # only left and right stay in _current_ new row
                if direction in [mg.MOVE_LEFT, mg.MOVE_RIGHT]:
                    dest_row_is_new = True # moving sideways within new
                else:
                    dest_row_is_new = False
        elif self.is_new_row(src_row + 1): # row just above the new row
            # only down (inc down left and right), or right in final col, 
            # take to new
            if direction in [mg.MOVE_DOWN, mg.MOVE_DOWN_LEFT, 
                             mg.MOVE_DOWN_RIGHT] or \
                    (direction == mg.MOVE_RIGHT and final_col):
                dest_row_is_new = True
            else:
                dest_row_is_new = False
        else: # more than one row away from new row
            dest_row_is_new = False
        return dest_row_is_new
    
    def leaving_existing_cell(self, was_final_col, was_final_row, direction):
        """
        Process the attempt to leave an existing cell (whether or not leaving
            existing row).
        Will not move if cell data not OK to save 
            OR readonly table and in final row and column and moving right or
            down.
        Will update a cell if there is changed data and if it is valid.
        Return move_to_dest.
        """
        debug = False
        if self.debug or debug: print("Was in existing, ordinary row")
        if self.dbtbl.readonly:
            move_to_dest = not (was_final_row and was_final_col 
                                and direction in(mg.MOVE_RIGHT, mg.MOVE_DOWN))
        else:
            if not self.cell_ok_to_save(self.current_row_idx, 
                                        self.current_col_idx):
                move_to_dest = False
            else:
                if self.dbtbl.bol_attempt_cell_update:
                    move_to_dest = self.update_cell(self.current_row_idx,
                                                    self.current_col_idx)
                else:
                    move_to_dest = True
        # flush
        self.dbtbl.bol_attempt_cell_update = False
        self.dbtbl.SQL_cell_to_update = None
        self.dbtbl.val_of_cell_to_update = None
        return move_to_dest
    
    def moving_in_new_row(self):
        """
        Process the attempt to move away from a cell in the new row to another 
            cell in the same row.  Will not move if cell is invalid.
        Return move_to_dest.
        """
        debug = False
        if self.debug or debug: print("Moving within new row")
        move_to_dest = not self.cell_invalid(self.current_row_idx, 
                                             self.current_col_idx)
        return move_to_dest
    
    def leaving_new_row(self, dest_row, dest_col, direction):
        """
        Process the attempt to leave a cell in the new row.
        Always OK to leave new row in an upwards direction if it has not been 
            altered (i.e. not dirty).
        Otherwise, must see if row is OK to Save and successfully saved.  If 
            either is not the case e.g. faulty data, keep selection where it
            was.
        NB actual direction could be down_left instead of down if in final col.
        Return move_to_dest.
        """
        debug = False
        if self.debug or debug: 
            print("leaving_new_row - dest row %s dest col %s orig directn %s" %
                (dest_row, dest_col, direction))
        if direction in [mg.MOVE_UP, mg.MOVE_UP_RIGHT, mg.MOVE_UP_LEFT] and \
                not self.dbtbl.new_is_dirty:
            move_to_dest = True # always OK
        else: # must check OK to move
            if not self.cell_ok_to_save(self.current_row_idx, 
                                        self.current_col_idx):
                move_to_dest = False
            elif not self.row_ok_to_save(row=self.current_row_idx, 
                                   col2skip=self.current_col_idx): # just passed
                move_to_dest = False
            else:
                move_to_dest = self.save_row(self.current_row_idx)
            if move_to_dest:
                self.dbtbl.new_is_dirty = False
        return move_to_dest

    # VALIDATION ///////////////////////////////////////////////////////////////

    def value_in_range(self, raw_val, fld_dic):
        "NB may be None if N/A e.g. SQLite"
        min = fld_dic[mg.FLD_NUM_MIN_VAL]
        max = fld_dic[mg.FLD_NUM_MAX_VAL]        
        if min is not None:
            if Decimal(raw_val) < Decimal(unicode(min)):
                if self.debug: print("%s is < the min of %s" % (raw_val, min))
                return False
        if max is not None:
            if Decimal(raw_val) > Decimal(unicode(max)):
                if self.debug: print("%s is > the max of %s" % (raw_val, max))
                return False
        if self.debug: print("%s was accepted" % raw_val)
        return True
    
    def cell_invalid(self, row, col):
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
        debug = False
        if self.debug or debug: 
            print("In cell_invalid for row %s col %s" % (row, col))
        cell_invalid = False # innocent until proven guilty
        if self.dbtbl.is_new_row(row):
            if self.debug or debug:
                print("New buffer is %s" % self.dbtbl.new_buffer)
            raw_val = self.dbtbl.new_buffer.get((row, col), 
                                            mg.MISSING_VAL_INDICATOR)
        else:
            raw_val = self.get_raw_val(row, col)
            existing_row_data_lst = self.dbtbl.row_vals_dic.get(row)
            if existing_row_data_lst:
                prev_val = unicode(existing_row_data_lst[col])
            if self.debug or debug: 
                print("prev_val: %s raw_val: %s" % (prev_val,  raw_val))
            if raw_val == prev_val:
                if self.debug or debug: print("Unchanged")
                return False # i.e. OK
            if self.debug or debug: print("%s is changed!" % raw_val)
        fld_dic = self.dbtbl.get_fld_dic(col)        
        if self.debug or debug: 
            print("\"%s\"" % raw_val)
            print("Field dic is:")
            pprint.pprint(fld_dic)
        if raw_val == mg.MISSING_VAL_INDICATOR or raw_val is None:
            return False
        elif not fld_dic[mg.FLD_DATA_ENTRY_OK]: 
             # i.e. not autonumber, timestamp etc
             # and raw_val != mg.MISSING_VAL_INDICATOR unnecessary
            raise Exception(u"This field should have been read only")
        elif fld_dic[mg.FLD_BOLNUMERIC]:
            if not lib.is_numeric(raw_val):
                wx.MessageBox(_("\"%s\" is not a valid number.\n\n"
                              "Either enter a valid number or "
                              "the missing value character (.)") % raw_val)
                return True
            if not self.value_in_range(raw_val, fld_dic):
                wx.MessageBox("\"%s\" " % raw_val + \
                              _("is invalid for data type ") + \
                              "%s" % self.dbtbl.get_fld_name(col))
                return True
            return False
        elif fld_dic[mg.FLD_BOLDATETIME]:
            usable_datetime = lib.is_usable_datetime_str(raw_val)
            if not usable_datetime:
                eg1 = mg.OK_DATE_FORMAT_EXAMPLES[0]
                eg2 = mg.OK_DATE_FORMAT_EXAMPLES[1]
                wx.MessageBox(u"\"%s\" " % raw_val + \
                      _(" is not a valid datetime.\n\n"
                        "Either enter a valid date/ datetime\n") + \
                      _("e.g. %(eg1)s or %(eg2)s") % {"eg1": eg1, "eg2": eg2} +
                      _("\nor the missing value character (.)"))
                return True
            return False
        elif fld_dic[mg.FLD_BOLTEXT]:
            max_len = fld_dic[mg.FLD_TEXT_LENGTH]
            if max_len is None: # SQLite returns None if TEXT
                return False
            if len(raw_val) > max_len:
                wx.MessageBox(u"\"%s\" " % raw_val +
                      _("is longer than the maximum of %s. Either enter a "
                        "shorter value or the missing value character (.)")
                      % max_len)
                return True
            return False
        else:
            raise Exception(u"Field supposedly not numeric, datetime, or text")
    
    def get_raw_val(self, row, col):
        """
        What was the value of a cell?
        NB always returned as a string.
        If it has just been edited, GetCellValue(), which calls 
            dbtbl.GetValue(), will not work.  It will get the cached version
            which is now out-of-date (we presumably just changed it).
        Need to get version stored by editor. So MUST close editors which 
            presumably flushes the value to where it becomes available to
            GetCellValue().
        """
        debug = False
        if self.dbtbl.bol_attempt_cell_update:
            raw_val = self.dbtbl.val_of_cell_to_update
            if self.debug or debug:
                cell_val_unhidden = self.grid.GetCellValue(row, col)
                self.grid.DisableCellEditControl()
                cell_val_hidden = self.grid.GetCellValue(row, col)
                print("""val_of_cell_to_update: %s, cell_val_unhidden: %s, 
                      cell_val_hidden: %s""" % (raw_val, cell_val_unhidden, 
                                                cell_val_hidden))
        else:
            self.grid.DisableCellEditControl()
            raw_val = self.grid.GetCellValue(row, col)
        return raw_val
    
    def cell_ok_to_save(self, row, col):
        """
        Cannot be an invalid value (must be valid or missing value).
        And if missing value, must be nullable field.
        """
        debug = False
        if self.debug or debug: 
            print("cell_ok_to_save - row %s col %s" % (row, col))
        raw_val = self.get_raw_val(row, col)
        fld_dic = self.dbtbl.get_fld_dic(col)
        missing_not_nullable_prob = \
            (raw_val == mg.MISSING_VAL_INDICATOR and \
                not fld_dic[mg.FLD_BOLNULLABLE] and \
             fld_dic[mg.FLD_DATA_ENTRY_OK])
        if missing_not_nullable_prob:
            fld_name = self.dbtbl.get_fld_name(col)
            wx.MessageBox(_("%s will not allow missing values to "
                          "be stored") % fld_name)
        ok_to_save = not self.cell_invalid(row, col) and \
            not missing_not_nullable_prob
        return ok_to_save

    def row_ok_to_save(self, row, col2skip=None):
        """
        Each cell must be OK to save.  NB validation may be stricter than what 
            the database will accept into its fields e.g. must be one of three 
            strings ("Numeric", "Text", or "Date").
        col2skip -- so we can skip validating a cell that has just passed e.g. 
            in leaving_new_row 
        """
        dd = getdata.get_dd()
        if self.debug: print("row_ok_to_save - row %s" % row)
        for col_idx in range(len(dd.flds)):
            if col_idx == col2skip:
                continue
            if not self.cell_ok_to_save(row=row, col=col_idx):
                wx.MessageBox(_("Unable to save new row.  Invalid value "
                              "in column") + u"%s" % (col_idx + 1))
                return False
        return True

    # CHANGING DATA /////////////////////////////////////////////////////////
       
    def update_cell(self, row, col):
        """
        Returns boolean - True if updated successfully.
        Update cell.
        Clear row from cache so forced to update with database values e.g. 
            typed in 2pm and stored in CCYY-MM-DD HH:mm:ss as today's date time 
            stamp but at 2pm.
        """
        debug = False
        dd = getdata.get_dd()
        if self.debug or debug: print("update_cell - row %s col %s" % (row, col))
        bol_updated_cell = True
        try:
            dd.con.commit()
            dd.cur.execute(self.dbtbl.sql_cell_to_update)
            dd.con.commit()
        except Exception, e:
            if self.debug or debug: 
                print(u"update_cell failed to save %s. " %
                      self.dbtbl.sql_cell_to_update + u"\nCaused by error: %s"
                      % lib.ue(e))
            bol_updated_cell = False
            wx.MessageBox(_("Unable to save change to database. %s") % 
                          lib.ue(e))
        if self.dbtbl.row_vals_dic.get(row):
            del self.dbtbl.row_vals_dic[row] # force a fresh read
        self.dbtbl.grid.ForceRefresh()
        return bol_updated_cell
    
    def save_row(self, row):
        """
        Only supplies insert_row() with the tuples for cols to be inserted.  
            Not autonumber or timestamp etc.
        Updates rows_n and rows_to_fill as part of process
        """
        dd = getdata.get_dd()
        data = []
        for col in range(len(dd.flds)):
            fld_name = self.dbtbl.fld_names[col]
            fld_dic = dd.flds[fld_name]
            if not fld_dic[mg.FLD_DATA_ENTRY_OK]:
                continue
            raw_val = self.dbtbl.new_buffer.get((row, col), None)
            if raw_val == mg.MISSING_VAL_INDICATOR:
                raw_val = None
            data.append((raw_val, fld_name, fld_dic))
        row_inserted, msg = getdata.insert_row(dd, data)
        if row_inserted:
            if self.debug: print("save_row - Just inserted row")
        else:
            if self.debug: print("save_row - Unable to insert row")
            wx.MessageBox(_("Unable to insert row. %s") % msg)
            return False
        try:
            self.setup_new_row(data)
            return True
        except:
            if self.debug: print("save_row - Unable to setup new row")
            return False

    def setup_new_row(self, data):
        """
        Setup new row ready to receive new data.
        data = [(value as string (or None), fld_name, fld_dets), ...]
        """
        self.dbtbl.set_row_ids_lst()
        self.dbtbl.set_num_rows() # need to refresh
        new_row_idx = self.dbtbl.rows_n - 1
        data_tup = tuple([x[0] for x in data])
        # do not add to row_vals_dic - force it to look it up from the db
        # will thus show autocreated values e.g. timestamp, autoincrement etc
        self.display_new_row()
        self.reset_row_labels(new_row_idx)
        self.init_new_row_buffer()
        self.set_new_row_ed(new_row_idx)
    
    def display_new_row(self):
        "Display a new entry row on end of grid"
        self.dbtbl.display_new_row()
    
    def reset_row_labels(self, row):
        "Reset new row label and restore previous new row label to default"
        prev_row = row - 1
        self.grid.SetRowLabelValue(prev_row, unicode(prev_row))
        self.grid.SetRowLabelValue(row, mg.NEW_IS_READY)
    
    def init_new_row_buffer(self):
        "Initialise new row buffer"
        self.dbtbl.new_is_dirty = False
        self.dbtbl.new_buffer = {}
    
    def focus_on_new_row(self, new_row_idx, col2select):
        "Focus on cell in new row"
        self.grid.SetGridCursor(new_row_idx, col2select)
        self.grid.MakeCellVisible(new_row_idx, col2select)

    def set_new_row_ed(self, row_idx):
        "Set cell editor for cells in new row"
        dd = getdata.get_dd()
        for col_idx in range(len(dd.flds)):
            self.grid.SetCellEditor(row_idx, col_idx, 
                                    wx.grid.GridCellTextEditor())

    # MISC //////////////////////////////////////////////////////////////////
    
    def on_grid_editor_created(self, event):
        """
        Need to identify control just opened. Might need to return to it and
            set insertion point.
        """
        debug = False
        self.control = event.GetControl()
        if debug: print("Created editor: %s" % self.control)
        event.Skip()    
    
    def on_label_rclick(self, event):
        debug = False
        col = event.GetCol()
        if col >= 0:
            if debug: wx.MessageBox("Col %s was clicked" % col)
            var_name = self.dbtbl.fld_names[col]
            var_label = self.var_labels.get(var_name, "")
            choice_item = lib.get_choice_item(self.var_labels, var_name)
            projects.set_var_props(choice_item, var_name, var_label,
                                   self.var_labels, self.var_notes,
                                   self.var_types, self.val_dics)
    
    def get_cell_tooltip(self, col, raw_val):
        """
        Get tooltip for cell based on value dict if possible.
        raw_val is always a string - won't necessarily match vals dic e.g. "5"
            won't match {5: "5's label"}.
        """
        debug = False
        fld_name = self.dbtbl.fld_names[col]
        fld_val_dic = self.val_dics.get(fld_name, {})
        tip = fld_val_dic.get(raw_val)
        if tip is None:
            try:
                tip = fld_val_dic.get(int(raw_val))
            except Exception:
                pass
        if tip is None:
            try:
                tip = fld_val_dic.get(float(raw_val))
            except Exception:
                pass
        if tip is None:
            tip = raw_val
        if debug: print(tip)
        return tip

    def on_editor_shown(self, event):
        self.any_editor_shown = True
        event.Skip()
        
    def on_editor_hidden(self, event):
        self.any_editor_shown = False
        event.Skip()
        
    def on_mouse_move(self, event):
        """
        Only respond if no cell editor is currently open.
        Only respond if a change in row or col.
        See http://wiki.wxpython.org/wxGrid%20ToolTips
        """
        if self.any_editor_shown:
            event.Skip()
            return
        x, y = self.grid.CalcUnscrolledPosition(event.GetPosition())
        row = self.grid.YToRow(y)
        col = self.grid.XToCol(x)
        if (row, col) != self.prev_row_col and row >= 0 and col >= 0:
            self.prev_row_col = (row, col)
            raw_val = self.get_raw_val(row, col)
            if raw_val == mg.MISSING_VAL_INDICATOR:
                tip = _("Missing value")
            else:
                tip = self.get_cell_tooltip(col, raw_val)
                if self.readonly or col in self.readonly_cols:
                    tip = _(u"%s (Read only column)") % tip
            self.grid.GetGridWindow().SetToolTipString(tip)
        event.Skip()
        
    def get_cols_n(self):
        dd = getdata.get_dd()
        return len(dd.flds)
    
    def on_size_cols(self, event):
        if self.dbtbl.rows_n < 2000:
            self.set_col_widths()
        else:
            ret = wx.MessageBox(_("This table has %(rows)s rows and "
                                "%(cols)s columns. Do you wish to resize?") %
                                {u"rows": self.dbtbl.rows_n, 
                                 u"cols": self.get_cols_n()},
                                _("Proceed with resizing columns"), 
                                style=wx.YES_NO|wx.ICON_QUESTION)
            if ret == wx.YES:
                self.set_col_widths()
        self.grid.SetFocus()
        event.Skip()
    
    def set_col_widths(self):
        "Set column widths based on display widths of fields"
        debug = False
        dd = getdata.get_dd()
        wx.BeginBusyCursor()
        self.parent.add_feedback("Setting column widths " + \
                    "(%s columns for %s rows)..." % (self.dbtbl.GetNumberCols(), 
                                                     self.dbtbl.rows_n))
        pix_per_char = 8
        sorted_fld_names = getdata.flds_dic_to_fld_names_lst(dd.flds)
        for col_idx, fld_name in enumerate(sorted_fld_names):
            fld_dic = dd.flds[fld_name]
            col_width = None
            if fld_dic[mg.FLD_BOLTEXT]:
                txt_len = fld_dic[mg.FLD_TEXT_LENGTH]
                col_width = txt_len*pix_per_char if txt_len is not None \
                    and txt_len < 25 else None # leave for auto
            elif fld_dic[mg.FLD_BOLNUMERIC]:
                num_len = fld_dic[mg.FLD_NUM_WIDTH]
                col_width = num_len*pix_per_char if num_len is not None \
                    else None
            elif fld_dic[mg.FLD_BOLDATETIME]:
                col_width = 170
            if col_width:
                if debug or self.debug: 
                    print("Width of %s set to %s" % (fld_name, col_width))
                self.grid.SetColSize(col_idx, col_width)
            else:
                if debug or self.debug: print("Autosizing %s" % fld_name)
                self.grid.AutoSizeColumn(col_idx, setAsMin=False)            
            fld_name_width = len(fld_name)*pix_per_char
            # if actual column width is small and the label width is larger,
            # use label width.
            self.grid.ForceRefresh()
            actual_width = self.grid.GetColSize(col_idx)
            if actual_width < 15*pix_per_char \
                    and actual_width < fld_name_width:
                self.grid.SetColSize(col_idx, fld_name_width)
            if debug or self.debug: 
                print("%s %s" % (fld_name, self.grid.GetColSize(col_idx)))
        self.parent.add_feedback("")
        lib.safe_end_cursor()
    
    def is_new_row(self, row):
        new_row = self.dbtbl.is_new_row(row)
        return new_row
    
    def is_final_row(self, row):
        final_row = self.dbtbl.is_final_row(row)
        return final_row
        
    def on_cell_change(self, event):
        debug = False
        row = event.GetRow()
        new_row = self.dbtbl.is_new_row(row)
        if new_row:
            self.dbtbl.new_is_dirty = True
        if debug: print("Cell changed")
        self.grid.ForceRefresh()
        event.Skip()
    
    def on_close(self, event):
        self.parent.update_var_dets()
        self.Destroy()
