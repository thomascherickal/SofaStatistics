"""
TextEditor is the custom grid cell editor - currently only used for the cells
    in the new row.  Needed so that the edited value can be captured when
    navigating away from a cell in editing mode (needed for validation).
"""

import wx
import wx.grid

import table_edit


class TextEditor(wx.grid.PyGridCellEditor):
    
    def __init__(self, tbl_editor, row, col, new_row, new_buffer):
        wx.grid.PyGridCellEditor.__init__(self)
        self.debug = False
        self.tbl_editor = tbl_editor
        self.row = row
        self.col = col
        self.new_row = new_row
        self.new_buffer = new_buffer
    
    def BeginEdit(self, row, col, grid):
        if self.debug: print "Editing started"
        val = grid.GetTable().GetValue(row, col)
        self.start_val = val
        self.txt.SetValue(val)
        self.txt.SetFocus()

    def Clone(self):
        return TextEditor(self.tbl_editor, self.row, self.col, self.new_row, 
                          self.new_buffer)
    
    def Create(self, parent, id, evt_handler):
        # created when clicked
        # wx.TE_PROCESS_TAB very important otherwise TAB is swallowed by dialog
        # (but not if grid on a frame or Dialog under Ubuntu - go figure!)
        self.txt = wx.TextCtrl(parent, -1, "", 
                               style=wx.TE_PROCESS_TAB|wx.TE_PROCESS_ENTER)
        self.SetControl(self.txt)
        if evt_handler:
            # so the control itself doesn't handle events but passes to handler
            self.txt.PushEventHandler(evt_handler)
            evt_handler.Bind(wx.EVT_KEY_DOWN, self.OnTxtEdKeyDown)
    
    def EndEdit(self, row, col, grid):
        if self.debug: print "Editing ending"
        changed = False
        val = self.txt.GetValue()
        if val != self.start_val:
            changed = True
            grid.GetTable().SetValue(row, col, val)
        if self.debug:
            print "Value entered was \"%s\"" % val
            print "Editing ended"
        if changed:
            if self.debug: print "Some data in new record has changed"
            self.tbl_editor.dbtbl.new_is_dirty = True
        return changed
        
    def StartingKey(self, event):
        keycode = event.GetKeyCode()
        if self.debug: print "Starting key was \"%s\"" % chr(keycode)
        if keycode <= 255 :
            self.txt.SetValue(chr(keycode))
            self.txt.SetInsertionPoint(1)
        else:
            event.Skip()

    def Reset(self):
        pass # N/A
    
    def OnTxtEdKeyDown(self, event):
        """
        We are interested in TAB and return keypresses.
        NB based on table_edit.TblEditor.OnGridKeyDown
        """
        debug = False
        keycode = event.GetKeyCode()
        if self.debug or debug: 
            print "Keypress %s recognised in custom editor" % keycode
        if keycode in [wx.WXK_TAB, wx.WXK_RETURN]:
            if keycode == wx.WXK_TAB:
                if event.ShiftDown():
                    direction = table_edit.MOVE_LEFT
                else:
                    direction = table_edit.MOVE_RIGHT
            elif keycode == wx.WXK_RETURN:
                direction = table_edit.MOVE_DOWN
            src_row=self.row
            src_col=self.col
            if self.debug or debug: 
                print "OnTxtEdKeyDown - Keypress %s " % keycode + \
                    "in row %s col %s" % (src_row, src_col)
                print "Number fields: %s" % len(self.tbl_editor.flds)
            final_col = (src_col == len(self.tbl_editor.flds) - 1)            
            if final_col and direction in [table_edit.MOVE_RIGHT, 
                                           table_edit.MOVE_DOWN]:
                self.tbl_editor.ProcessCellMove(src_row=self.row, 
                            src_col=self.col, dest_row=None, dest_col=None, 
                            direction=direction)                
                # Do not Skip and send event on its way.
                # Smother the event here so our code can determine where the 
                # selection goes next.  Otherwise, Return will appear in cell 
                # below and trigger other responses.
            else:
                event.Skip()
        else:
            event.Skip()
