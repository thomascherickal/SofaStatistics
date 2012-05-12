from __future__ import print_function
import wx
import wx.grid

import my_globals as mg
import my_exceptions
import lib
import controls

COL_STR = u"col_string"
COL_INT = u"col_integer"
COL_FLOAT = u"col_float"
COL_TEXT_BROWSE = u"col_button"
COL_DROPDOWN = u"col_dropdown"
COL_PWD = u"col_pwd"


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


class SettingsEntryDlg(wx.Dialog):
    def __init__(self, title, grid_size, col_dets, init_settings_data, 
                 settings_data, insert_data_func=None, 
                 row_validation_func=None):
        """
        col_dets -- see under SettingsEntry.
        data -- list of tuples (tuples must have at least one item, even if only 
            a "rename me").  Empty list ok.
        settings_data -- is effectively "returned".  Add details to it in form 
            of a list of tuples.
        insert_data_func -- what data do you want to see in a new inserted row 
            (if any).  Must take row index as argument.
        """
        wx.Dialog.__init__(self, None, title=title, size=(400,400), 
                          style=wx.RESIZE_BORDER|wx.CAPTION|wx.SYSTEM_MENU, 
                          pos=(mg.HORIZ_OFFSET+100,0))
        self.panel = wx.Panel(self)
        self.szr_main = wx.BoxSizer(wx.VERTICAL)
        force_focus = False
        self.tabentry = SettingsEntry(self, self.panel, grid_size, col_dets, 
                              init_settings_data, settings_data, force_focus, 
                              insert_data_func, row_validation_func)
        self.szr_main.Add(self.tabentry.grid, 1, wx.GROW|wx.ALL, 5)
        # Close only
        self.setup_btns()
        # sizers
        self.szr_main.Add(self.szr_btns, 0, wx.ALL, 10)
        self.panel.SetSizer(self.szr_main)
        self.szr_main.SetSizeHints(self)
        self.Layout()
        self.tabentry.grid.SetFocus()
        
    def setup_btns(self, readonly=False):
        """
        Separated for text_browser reuse
        """
        if not readonly:
            btn_cancel = wx.Button(self.panel, wx.ID_CANCEL)
            btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        if readonly:
            btn_ok = wx.Button(self.panel, wx.ID_OK)
        else:
            btn_ok = wx.Button(self.panel, wx.ID_OK, _("Update")) # must have ID 
            # of wx.ID_OK to trigger validators (no event binding needed) and 
            # for std dialog button layout
        btn_ok.Bind(wx.EVT_BUTTON, self.on_ok)
        btn_ok.SetDefault()
        if not readonly:
            btn_delete = wx.Button(self.panel, wx.ID_DELETE)
            btn_delete.Bind(wx.EVT_BUTTON, self.on_delete)
            btn_insert = wx.Button(self.panel, -1, _("Insert Before"))
            btn_insert.Bind(wx.EVT_BUTTON, self.on_insert)
        # using the approach which will follow the platform convention 
        # for standard buttons
        self.szr_btns = wx.StdDialogButtonSizer()
        if not readonly:
            self.szr_btns.AddButton(btn_cancel)
        self.szr_btns.AddButton(btn_ok)
        self.szr_btns.Realize()
        if not readonly:
            self.szr_btns.Insert(0, btn_delete, 0)
            self.szr_btns.Insert(0, btn_insert, 0, wx.RIGHT, 10)

    def on_cancel(self, event):
        # no validation - just get out
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL)

    def on_ok(self, event):
        if not self.panel.Validate(): # runs validators on all assoc controls
            return True
        self.tabentry.update_settings_data()
        self.Destroy()
        self.SetReturnCode(wx.ID_OK)
        
    def on_delete(self, event):
        unused = self.tabentry.try_to_delete_row()
        self.tabentry.grid.SetFocus()
        event.Skip()
    
    def insert_before(self):
        """
        Returns row inserted before (or None if no insertion) and row data (or 
            None if no content added). 
        """
        selected_rows = self.tabentry.grid.GetSelectedRows()
        if not selected_rows: 
            return False, None, None
        pos = selected_rows[0]
        bolinserted, row_data = self.tabentry.insert_row_above(pos)
        return bolinserted, pos, row_data
    
    def on_insert(self, event):
        """
        Insert before.
        """
        unused, unused, unused = self.insert_before()
        self.tabentry.grid.SetFocus()
        event.Skip()
        
    
def cell_invalidation(frame, val, row, col, grid, col_dets):
    "Return boolean and string message"
    return False, u""

def cell_response(self, val, row, col, grid, col_dets):
    pass


class SettingsEntry(object):
    
    def __init__(self, frame, panel, readonly, grid_size, col_dets, 
                 init_settings_data, settings_data, force_focus=False, 
                 insert_data_func=None, cell_invalidation_func=None, 
                 cell_response_func=None):
        """
        col_dets - list of dic.  Keys = "col_label", "coltype", 
            and, optionally, "colwidth", "file_phrase", "file_wildcard", 
            "empty_ok", "col_min_val", "col_max_val", "col_precision".
            Also "dropdown_vals" which is a list of values for the dropdown.
        init_settings_data - list of tuples (must have at least one item, even 
            if only a "rename me").
        settings_data - is effectively "returned" - add details to it in form 
            of a list of tuples.
        force_focus -- force focus - needed sometimes and better without others.
        insert_data_func - return row_data and receive row_idx, grid_data
        cell_invalidation_func - return boolean, and string message 
            and receives row, col, grid, col_dets
        cell_response_func -- some code run when leaving a valid cell e.g. might
            tell user something about the value they just entered
        """
        self.debug = False
        self.new_is_dirty = False
        self.frame = frame
        self.panel = panel
        self.readonly = readonly
        self.col_dets = col_dets
        self.force_focus = force_focus
        self.insert_data_func = insert_data_func
        self.cell_invalidation_func = cell_invalidation_func \
            if cell_invalidation_func else cell_invalidation
        self.cell_response_func = cell_response_func \
            if cell_response_func else cell_response
        # store any fixed min colwidths
        self.colwidths = [None for x in range(len(self.col_dets))] # init
        for col_idx, col_det in enumerate(self.col_dets):
            if col_det.get("colwidth"):
                self.colwidths[col_idx] = col_det["colwidth"]
        self.init_settings_data = init_settings_data
        self.settings_data = settings_data
        self.any_editor_shown = False
        self.new_editor_shown = False
        # grid control
        self.grid = wx.grid.Grid(self.panel, size=grid_size)        
        self.respond_to_select_cell = True      
        self.rows_n = len(self.init_settings_data)
        if not readonly:
            self.rows_n += 1
        self.cols_n = len(self.col_dets)
        if self.rows_n > 1:
            data_cols_n = len(init_settings_data[0])
            #pprint.pprint(init_settings_data) # debug
            if data_cols_n != self.cols_n:
                raise Exception(u"There must be one set of column details per"
                                u" column of data (currently %s details for "
                                u"%s columns)" % (self.cols_n, data_cols_n))
        self.grid.CreateGrid(numRows=self.rows_n, numCols=self.cols_n)
        self.grid.EnableEditing(not self.readonly)
        # Set any col min widths specifically specified
        for col_idx in range(len(self.col_dets)):
            colwidth = self.colwidths[col_idx]
            if colwidth:
                self.grid.SetColMinimalWidth(col_idx, colwidth)
                self.grid.SetColSize(col_idx, colwidth)
                # otherwise will only see effect after resizing
            else:
                self.grid.AutoSizeColumn(col_idx, setAsMin=False)
        self.grid.ForceRefresh()
        # set col rendering and editing (string is default)
        for col_idx, col_det in enumerate(self.col_dets):
            coltype = col_det["coltype"]
            if coltype == COL_INT:
                self.grid.SetColFormatNumber(col_idx)
            elif coltype == COL_FLOAT:
                width, precision = self.get_width_precision(col_idx)
                self.grid.SetColFormatFloat(col_idx, width, precision)
            # must set editor cell by cell amazingly
            for row_idx in range(self.rows_n):
                renderer, editor = self.get_new_renderer_editor(col_idx)
                self.grid.SetCellRenderer(row_idx, col_idx, renderer)
                self.grid.SetCellEditor(row_idx, col_idx, editor)
        # set min row height if text browser used
        for col_idx, col_det in enumerate(self.col_dets):
            coltype = col_det["coltype"]
            if coltype == COL_TEXT_BROWSE:
                self.grid.SetDefaultRowSize(30)
                break
        # unlike normal grids, we can assume limited number of rows
        self.grid.SetRowLabelSize(40)
        # grid event handling
        self.grid.Bind(wx.EVT_KEY_DOWN, self.on_grid_key_down)
        self.grid.Bind(EVT_CELL_MOVE, self.on_cell_move)
        self.grid.Bind(wx.grid.EVT_GRID_CELL_CHANGE, self.on_cell_change)
        self.grid.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.on_select_cell)
        
        self.grid.Bind(wx.grid.EVT_GRID_CELL_LEFT_CLICK, self.on_mouse_cell)
        self.grid.Bind(wx.grid.EVT_GRID_CELL_LEFT_DCLICK, self.on_mouse_cell)
        
        self.grid.Bind(controls.EVT_TEXT_BROWSE_KEY_DOWN, 
                       self.on_text_browse_key_down)
        self.frame.Bind(wx.grid.EVT_GRID_EDITOR_CREATED, 
                        self.on_grid_editor_created)
        self.frame.Bind(wx.grid.EVT_GRID_EDITOR_SHOWN, self.on_editor_shown)
        self.frame.Bind(wx.grid.EVT_GRID_EDITOR_HIDDEN, self.on_editor_hidden)
        self.grid.Bind(wx.grid.EVT_GRID_LABEL_LEFT_CLICK, self.on_label_click)
        # misc
        for col_idx, col_det in enumerate(self.col_dets):
            self.grid.SetColLabelValue(col_idx, col_det["col_label"])
        self.rows_to_fill = self.rows_n if self.readonly else self.rows_n - 1
        for i in range(self.rows_to_fill):
            for j in range(self.cols_n):
                self.grid.SetCellValue(row=i, col=j, 
                                       s=unicode(init_settings_data[i][j]))
        if not self.readonly:
                self.grid.SetRowLabelValue(self.rows_n - 1, mg.NEW_IS_READY)
        self.current_col_idx = 0
        if self.readonly:
            self.current_row_idx = 0
            self.grid.SetGridCursor(0, 0)
        else:
            self.current_row_idx = self.rows_n - 1
            self.grid.SetGridCursor(self.rows_n - 1, 0) # triggers OnSelect
            self.grid.MakeCellVisible(self.rows_n - 1, 0)
        self.control = None
    
    def get_new_renderer_editor(self, col_idx):
        """
        For a given column index, return a fresh renderer and editor object.
        Objects must be unique to cell.
        Returns renderer, editor.
        Nearly (but not quite) worth making classes ;-)
        """
        coltype = self.col_dets[col_idx]["coltype"]
        if coltype == COL_INT:
            min = self.col_dets[col_idx].get("col_min_val", -1) # -1 no minimum
            max = self.col_dets[col_idx].get("col_max_val", min)
            renderer = wx.grid.GridCellNumberRenderer()
            editor = wx.grid.GridCellNumberEditor(min, max)
        elif coltype == COL_FLOAT:
            width, precision = self.get_width_precision(col_idx)
            renderer = wx.grid.GridCellFloatRenderer(width, precision)
            editor = wx.grid.GridCellFloatEditor(width, precision)
        elif coltype == COL_TEXT_BROWSE:
            renderer = wx.grid.GridCellStringRenderer()
            file_phrase = self.col_dets[col_idx].get("file_phrase", "")
            # use * - *.* will not pickup files without extensions in Ubuntu
            wildcard = self.col_dets[col_idx].get("file_wildcard", 
                                                  _("Any file") + u" (*)|*")
            editor = controls.GridCellTextBrowseEditor(self.grid, file_phrase, 
                                                       wildcard)
        elif coltype == COL_DROPDOWN:
            dropdown_vals = self.col_dets[col_idx].get("dropdown_vals")
            if dropdown_vals:
                renderer = wx.grid.GridCellStringRenderer()
                editor = wx.grid.GridCellChoiceEditor(dropdown_vals)
            else:
                raise Exception(u"settings_grid.get_new_renderer_editor: "
                                u"needed to supply dropdown_vals")
        elif coltype == COL_PWD:
            renderer = controls.GridCellPwdRenderer()
            editor = controls.GridCellPwdEditor()
        else:
            renderer = wx.grid.GridCellStringRenderer()
            editor = wx.grid.GridCellTextEditor()
        return renderer, editor

    def get_width_precision(self, col_idx):
        """
        Returns width, precision.
        """
        width = self.col_dets[col_idx].get("colwidth", 5)
        precision = self.col_dets[col_idx].get("col_precision", 1)
        return width, precision

    def on_label_click(self, event):
        "Need to give grid the focus so can process keystrokes e.g. delete"
        self.grid.SetFocus()
        event.Skip()

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
            raise Exception(u"settings_grid.on_select_cell - where is "
                            u"direction?")
        if self.debug or debug: 
            print(u"on_select_cell - selected row: %s, col: %s, direction: %s" %
            (dest_row, dest_col, direction) + u"******************************") 
        self.add_cell_move_evt(direction, dest_row, dest_col)

    def on_mouse_cell(self, event):
        self.update_new_is_dirty()
        event.Skip()

    def on_grid_editor_created(self, event):
        """
        Need to bind KeyDown to the control itself e.g. a choice control.
        wx.WANTS_CHARS makes it work.
        """
        debug = False
        self.control = event.GetControl()
        if debug: 
            print("Created editor: %s" % self.control)
            if isinstance(self.control, wx.ComboBox):
                self.update_new_is_dirty()
                print("Selected combobox")
        self.control.WindowStyle |= wx.WANTS_CHARS
        self.control.Bind(wx.EVT_KEY_DOWN, self.on_grid_key_down)
        event.Skip()

    def on_grid_key_down(self, event):
        """
        Potentially capture use of keypress to move away from a cell.
        The only case where we can't rely on on_select_cell to take care of
            add_cell_move_evt for us is if we are moving right or down from the 
            last col after a keypress.
        Must process here. NB dest row and col yet to be determined.
        If a single row is selected, the key is a delete, and we are not inside 
            and editor, delete selected row if possible.
        """
        debug = False
        keycode = event.GetKeyCode()
        if self.debug or debug: 
            print(u"on_grid_key_down - keycode %s pressed" % keycode)
        if (keycode in [wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE] 
                and not self.readonly):
            # None if no deletion occurs
            if self.try_to_delete_row(assume_row_deletion_attempt=False):
                # don't skip. Smother event so delete not entered anywhere.
                return
            else:
                if not self.any_editor_shown:
                    # set to empty string
                    self.grid.SetCellValue(self.current_row_idx, 
                                           self.current_col_idx, u"")
                else:
                    event.Skip()
        elif keycode in [wx.WXK_TAB, wx.WXK_RETURN]:
            if keycode == wx.WXK_TAB:
                if event.ShiftDown():
                    direction = mg.MOVE_LEFT
                else:
                    direction = mg.MOVE_RIGHT
            elif keycode == wx.WXK_RETURN:
                direction = mg.MOVE_DOWN
            src_row=self.current_row_idx
            src_col=self.current_col_idx
            if self.debug or debug: print(u"on_grid_key_down - keypress in row "
                u"%s col %s *****************************" % (src_row, src_col))
            final_col = (src_col == len(self.col_dets) - 1)
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
                event.Skip()
                return
        else:
            self.update_new_is_dirty()
            event.Skip()
            return
    
    def update_new_is_dirty(self):
        debug = False
        if self.is_new_row(self.current_row_idx):
            self.new_is_dirty = True
            if debug: print("Updated new_is_dirty to True")
            self.grid.SetRowLabelValue(self.current_row_idx, mg.NEW_IS_DIRTY)
        else:
            self.grid.SetRowLabelValue(self.get_new_row_idx(), mg.NEW_IS_READY)
    
    def on_text_browse_key_down(self, event):
        """
        Text browser - hit enter from text box part of composite control OR 
            clicked on Browse button.  
            If the final col, will go to left of new line.  Otherwise, will just
            move right.
        NB we only get here if editing the text browser.  If in the cell 
            otherwise, enter will move you down, which is consistent with all 
            other controls.
        """
        keycode = event.get_key_code() # custom event class
        if keycode in [controls.MY_KEY_TEXT_BROWSE_MOVE_NEXT, 
                       controls.MY_KEY_TEXT_BROWSE_BROWSE_BTN]:
            self.grid.DisableCellEditControl()
            self.add_cell_move_evt(mg.MOVE_RIGHT)
        elif keycode == wx.WXK_ESCAPE:
            self.grid.DisableCellEditControl()
            self.grid.SetFocus()
            
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
            print(u"settings_grid.on_cell_move src_row: %s src_col %s " %
                (src_row, src_col) + u"dest_row: %s dest_col: %s " %
                (dest_row, dest_col) + u"direction %s" % direction)
        # process_cell_move called from text editor as well so keep separate
        self.process_cell_move(src_ctrl, src_row, src_col, dest_row, dest_col, 
                               direction)
        # only SetFocus if moving.  Otherwise if this is embedded, we can't set
        # the focus anywhere else (because it triggers EVT_CELL_MOVE and then
        # we grab the focus again below!).
        moved = ((src_row, src_col) != (dest_row, dest_col))
        if self.force_focus and moved:
            self.grid.SetFocus()
            # http://www.nabble.com/Setting-focus-to-grid-td17920756.html
            for window in self.grid.GetChildren():
                window.SetFocus()
        event.Skip()
    
    def process_cell_move(self, src_ctrl, src_row, src_col, dest_row, dest_col, 
                          direction):
        """
        dest row and col still unknown if from a return or TAB keystroke.
        So is the direction (could be down or down_left if end of line).
        Returns stayed_still, saved_new_row (needed for table config).
        """
        debug = False
        saved_new_row = False
        stayed_still = True
        if self.debug or debug:
            print(u"process_cell_move - " +
                u"source row %s source col %s " % (src_row, src_col) +
                u"dest row %s dest col %s " % (dest_row, dest_col) +
                u"direction: %s" % direction)
        move_type, dest_row, dest_col = self.get_move_dets(src_row, src_col, 
                                                dest_row, dest_col, direction)
        if move_type in [mg.MOVING_IN_EXISTING, mg.LEAVING_EXISTING]:
            move_to_dest = self.leaving_existing_cell()
        elif move_type == mg.MOVING_IN_NEW:
            move_to_dest = self.moving_in_new_row()
        elif move_type == mg.LEAVING_NEW:
            move_to_dest, saved_new_row = self.leaving_new_row(dest_row, 
                                                            dest_col, direction)
        else:
            raise Exception(u"process_cell_move - Unknown move_type")
        if self.debug or debug:
            print(u"move_type: %s move_to_dest: %s " % (move_type, 
                                                        move_to_dest) +
                  u"dest_row: %s dest_col: %s" % (dest_row, dest_col))
            
        if move_to_dest:
            stayed_still = False
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
                    my_exceptions.DoNothingException("OK if source control has "
                                        "no ability to set insertion point.")
        return stayed_still, saved_new_row
    
    def get_move_dets(self, src_row, src_col, dest_row, dest_col, direction):
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
        debug = False
        # 1) move type
        final_col = (src_col == len(self.col_dets) - 1)
        was_new_row = self.is_new_row(self.current_row_idx)
        dest_row_is_new = self.dest_row_is_current_new(src_row, dest_row, 
                                                       direction, final_col)
        if debug or self.debug:
            print(u"Current row idx: %s, src_row: %s, was_new_row: %s, "
                  u"dest_row_is_new: %s" % (self.current_row_idx, src_row, 
                                            was_new_row, dest_row_is_new))
        if was_new_row and dest_row_is_new:
            move_type = mg.MOVING_IN_NEW
        elif was_new_row and not dest_row_is_new:
            move_type = mg.LEAVING_NEW
        elif not was_new_row and not dest_row_is_new:
            move_type = mg.MOVING_IN_EXISTING
        elif not was_new_row and dest_row_is_new:
            move_type = mg.LEAVING_EXISTING
        else:
            raise Exception(u"settings_grid.get_move_dets().  Unknown move.")
        # 2) dest row and dest col
        if dest_row is None and dest_col is None: # known if from on_select_cell
            if final_col and direction in [mg.MOVE_RIGHT, mg.MOVE_DOWN]:
                dest_row = src_row + 1
                dest_col = 0
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
                    raise Exception(u"settings_grid.get_move_dets no "
                                u"destination (so from a TAB or Return) yet "
                                u"not a left, right, or down.")
        return move_type, dest_row, dest_col
    
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
    
    def is_new_row(self, row):
        "e.g. if 2 rows inc new - new row if idx = 1 i.e. subtract 1"
        debug = False
        if debug: print("row: %s; rows_to_fill: %s" % (row, self.rows_to_fill))
        new_row = (row == self.rows_to_fill)
        return new_row
    
    def get_new_row_idx(self):
        """
        if 2 rows to fill then the final row (2) will be the new one - 
            not zero-based indexing.
        """
        return self.rows_to_fill
    
    def leaving_existing_cell(self):
        """
        Process the attempt to leave an existing cell (whether or not leaving
            existing row).
        Will not move if cell data not OK to save.
        Return move_to_dest.
        """
        debug = False
        if self.debug or debug: print(u"Was in existing, ordinary row")
        move_to_dest, msg = self.cell_ok_to_save(self.current_row_idx, 
                                                 self.current_col_idx)
        if msg: wx.MessageBox(msg)
        return move_to_dest
    
    def moving_in_new_row(self):
        """
        Process the attempt to move away from a cell in the new row to another 
            cell in the same row.  Will not move if cell is invalid.
        Return move_to_dest.
        """
        debug = False
        if self.debug or debug: print(u"Moving within new row")
        row = self.current_row_idx
        col = self.current_col_idx
        invalid, msg = self.cell_invalid(row, col)
        if msg: wx.MessageBox(msg)
        move_to_dest = not invalid 
        return move_to_dest
    
    def leaving_new_row(self, dest_row, dest_col, direction):
        """
        Process the attempt to leave a cell in the new row.
        Always OK to leave new row in an upwards direction if it has not been 
            altered (i.e. not dirty).
        Otherwise, must see if row is OK to Save.  If not, e.g. faulty data, 
            keep selection where it was.  If OK, add new row.
        NB actual direction could be down_left instead of down if in final col.
        Return move_to_dest, saved_new_row (used by table config when processing 
            cell move).
        """
        debug = False
        saved_new_row = False
        is_dirty = self.is_dirty(self.current_row_idx)
        if self.debug or debug: 
            print(u"leaving_new_row - dest row %s dest col %s " %
                  (dest_row, dest_col) +
                  u"original direction %s dirty %s" % (direction, is_dirty))
        if direction in [mg.MOVE_UP, mg.MOVE_UP_RIGHT, mg.MOVE_UP_LEFT] \
                and not is_dirty:
            move_to_dest = True # always OK
            self.new_is_dirty = False
        else: # must check OK to move
            ok_to_save, msg = self.cell_ok_to_save(self.current_row_idx, 
                                                   self.current_col_idx)
            if not ok_to_save:
                wx.MessageBox(msg)
                move_to_dest = False
            elif not self.row_ok_to_save(row=self.current_row_idx,
                                   col2skip=self.current_col_idx): # just passed
                move_to_dest = False
            else:
                move_to_dest = True
            if move_to_dest:
                self.add_new_row()
                if debug or self.debug: print("Added new row")
                saved_new_row = True
                self.new_is_dirty = False
        return move_to_dest, saved_new_row
    
    # VALIDATION ///////////////////////////////////////////////////////////////
    
    def is_dirty(self, row):
        "Dirty means there are some values which are not empty strings"
        for col_idx in range(len(self.col_dets)):
            if self.grid.GetCellValue(row, col_idx) != "":
                return True
        return False
    
    def cell_invalid(self, row, col):
        """
        Return boolean and string message.
        NB must flush values in any open editors onto grid.
        """
        self.grid.DisableCellEditControl()
        val = self.get_val(row, col)
        return self.cell_invalidation_func(self.frame, val, row, col, self.grid, 
                                           self.col_dets)
    
    def get_val(self, row, col):
        """
        What was the value of a cell?
        If it has just been edited, GetCellValue(), will not have caught up yet.  
        Need to get version stored by editor. So MUST close editors which 
            presumably flushes the value to where it becomes available to
            GetCellValue().
        """
        self.grid.DisableCellEditControl()
        val = self.grid.GetCellValue(row, col)
        return val
    
    def cell_ok_to_save(self, row, col):
        """
        Cannot be an invalid value (must be valid or empty string).
        And if empty string value, must be empty ok.
        Returns boolean and string message.
        """
        debug = False
        empty_ok = self.col_dets[col].get(u"empty_ok", False)
        cell_val = self.get_val(row, col)
        if self.debug or debug:
            print(u"cell_ok_to_save - row: %s, col: %s, " % (row, col) +
                u"empty_ok: %s, cell_val: %s" % (empty_ok, cell_val))
        empty_not_ok_prob = (cell_val == "" and not empty_ok)
        invalid, msg = self.cell_invalid(row, col)
        if not invalid:
            self.cell_response_func(self.frame, cell_val, row, col, self.grid, 
                                    self.col_dets)
        if not msg and empty_not_ok_prob:
            msg = _("Data cell cannot be empty.")
        ok_to_save = not invalid and not empty_not_ok_prob
        return ok_to_save, msg

    def row_ok_to_save(self, row, col2skip=None):
        """
        Each cell must be OK to save. NB validation may be stricter than what 
            the database will accept into its fields e.g. must be one of three 
            strings ("Numeric", "Text", or "Date").
        col2skip -- so we can skip validating a cell that has just passed e.g. 
            in leaving_new_row 
        """
        if self.debug: print(u"row_ok_to_save - row %s" % row)
        for col_idx, col_det in enumerate(self.col_dets):
            if col_idx == col2skip:
                continue
            ok_to_save, msg = self.cell_ok_to_save(row=row, col=col_idx)
            if not ok_to_save:
                wx.MessageBox(_("Unable to save new row.  Invalid value "
                                "in the \"%(col_label)s\" column. %(msg)s") % \
                                {"col_label": col_det["col_label"], "msg": msg})
                return False
        return True
    
    # MISC /////////////////////////////////////////////////////////////////////

    def get_cols_n(self):
        return len(self.col_dets)
    
    def ok_to_delete_row(self, row):
        """
        Can delete any row except the new row.
        Cannot delete if in middle of editing a cell.
        Returns boolean and msg.
        """
        if self.is_new_row(row):
            return False, _("Unable to delete new row")
        elif self.new_is_dirty:
            return False, _("Cannot delete a row while in the middle of making "
                            "a new one")
        elif self.any_editor_shown:
            return False, _("Cannot delete a row while in the middle of editing"
                            " a cell")  
        else:
            return True, None
    
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
            row = selected_rows[0]
            ok_to_delete, msg = self.ok_to_delete_row(row)
            if ok_to_delete:
                self.delete_row(row)
                return row
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
    
    def delete_row(self, row):
        """
        Delete a row.
        row -- row index (not necessarily same as id value).
        If the currently selected cell is in a row below that being deleted,
            move up one.
        Move to the correct cell and set self.respond_to_select_cell to False.
        Assumed to be OK because not shifting cell as such.  Just following it 
            :-) or jumping to a cell in an already-validated row.
        """
        self.grid.DeleteRows(pos=row, numRows=1)
        self.reset_row_n(change=-1)
        self.grid.SetRowLabelValue(self.rows_n - 1, mg.NEW_IS_READY)
        self.grid.HideCellEditControl()
        self.grid.ForceRefresh()
        self.safe_layout_adjustment()
        self.respond_to_select_cell = False
        if row < self.current_row_idx:
            self.current_row_idx -= 1
            self.grid.SetGridCursor(self.current_row_idx, self.current_col_idx)
        self.grid.SetFocus()
    
    def on_editor_shown(self, event):
        # disable resizing until finished
        self.grid.DisableDragColSize()
        self.grid.DisableDragRowSize()
        self.any_editor_shown = True
        if event.GetRow() == self.rows_n - 1:
            self.new_editor_shown = True
        event.Skip()
        
    def on_editor_hidden(self, event):
        # re-enable resizing
        self.grid.EnableDragColSize()
        self.grid.EnableDragRowSize()
        self.any_editor_shown = False
        self.new_editor_shown = False
        event.Skip()

    def on_cell_change(self, event):
        debug = False
        if debug: print("Current row idx is: %s" % self.current_row_idx)
        self.update_new_is_dirty()
        if self.debug or debug: print(u"Cell changed")
        self.grid.ForceRefresh()
        self.safe_layout_adjustment()
        event.Skip()

    def insert_row_above(self, pos):
        """
        Insert row above selected row.
        If data supplied (list), insert values into row.
        Change row labels appropriately.
        If below the rows being inserted, jump down a row and set 
            self.respond_to_select_cell to False. Assumed to be OK because not 
            shifting cell as such.  Just following it :-)
        Returns bolinserted, and row_data (list if content put into inserted 
            row, None if not).
        """
        if self.new_is_dirty:
            wx.MessageBox(_("Cannot insert a row while in the middle of making "
                            "a new one"))
            return False, None
        grid_data = self.get_grid_data() # only needed to prevent field name
        # collisions
        row_idx = pos
        self.grid.InsertRows(row_idx)
        row_data = None
        if self.insert_data_func:
            row_data = self.insert_data_func(row_idx, grid_data)
            for col_idx in range(len(self.col_dets)):
                renderer, editor = self.get_new_renderer_editor(col_idx)
                self.grid.SetCellRenderer(row_idx, col_idx, renderer)
                self.grid.SetCellEditor(row_idx, col_idx, editor)
            for i, value in enumerate(row_data):
                self.grid.SetCellValue(row_idx, i, value)
        self.reset_row_n(change=1)
        # reset label for all rows after insert
        self.update_next_row_labels(row_idx)
        self.grid.SetRowLabelValue(self.rows_n - 1, mg.NEW_IS_READY)
        if row_idx <= self.current_row_idx: # inserting above our selected cell
            self.current_row_idx += 1
            self.grid.SetGridCursor(self.current_row_idx, self.current_col_idx)
        self.grid.SetFocus()
        return True, row_data
    
    def update_next_row_labels(self, pos):
        for i in range(pos, self.rows_n - 1):
            self.grid.SetRowLabelValue(i, unicode(i + 1))
    
    def reset_row_n(self, change=1):
        "Reset rows_n and rows_to_fill by incrementing or decrementing."
        self.rows_n += change
        self.rows_to_fill += change
    
    def add_new_row(self):
        """
        Add new row.
        """
        self.new_is_dirty = False
        new_row_idx = self.rows_n # e.g. 1 row 1 new (2 rows), new is 2
        # change label from * and add a new entry row on end of grid
        self.grid.AppendRows()
        # set up cell rendering and editing
        for col_idx in range(self.cols_n):
            renderer, editor = self.get_new_renderer_editor(col_idx)
            self.grid.SetCellRenderer(new_row_idx, col_idx, renderer)
            self.grid.SetCellEditor(new_row_idx, col_idx, editor)
        self.reset_row_n(change=1)
        self.grid.SetRowLabelValue(self.rows_n - 2, unicode(self.rows_n - 1))
        self.grid.SetRowLabelValue(self.rows_n - 1, mg.NEW_IS_READY)
        self.safe_layout_adjustment()
        
    def safe_layout_adjustment(self):
        """
        Uses CallAfter to avoid infinite recursion.
        http://lists.wxwidgets.org/pipermail/wxpython-users/2007-April/063536.html
        """
        wx.CallAfter(self.run_safe_layout_adjustment)
    
    def run_safe_layout_adjustment(self):
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

    def row_has_data(self, row):
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

    def get_grid_data(self):
        """
        Get data from grid.
        If readonly, get all rows.
        If not readonly, get all but final row (either empty or not saved).
        Only returns values - not types etc.
        """
        grid_data = []
        data_rows_n = self.rows_n if self.readonly else self.rows_n - 1 
        for row_idx in range(data_rows_n):
            row_data = []
            for col_idx in range(len(self.col_dets)):
                val = self.grid.GetCellValue(row=row_idx, col=col_idx)
                row_data.append(lib.fix_eols(val))
            grid_data.append(tuple(row_data))
        return grid_data

    def update_settings_data(self):
        """
        Update settings_data. Separated for reuse. NB clear it first so can 
            refresh repeatedly.
        """
        grid_data = self.get_grid_data()
        # need to stay pointed to same memory but empty it
        while True:
            try:
                del self.settings_data[0]
            except IndexError:
                break
        self.settings_data += grid_data
        