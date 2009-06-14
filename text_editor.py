"""
TextEditor is the custom grid cell editor - currently only used for the cells
    in the new row.  Needed so that the edited value can be captured when
    navigating away from a cell in editing mode (needed for validation).
"""

import wx
import wx.grid


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
        self.txt = wx.TextCtrl(parent, -1, "")
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
        key_code = event.GetKeyCode()
        if self.debug: print "Starting key was \"%s\"" % chr(key_code)
        if key_code <= 255 :
            self.txt.SetValue(chr(key_code))
            self.txt.SetInsertionPoint(1)
        else:
            event.Skip()

    def Reset(self):
        pass # N/A
    
    def OnTxtEdKeyDown(self, event):
        "We are interested in TAB keypresses"
        if event.GetKeyCode() in [wx.WXK_TAB]:
            evt_row=self.row
            evt_col=self.col
            if self.debug: print "OnTxtEdKeyDown - Hit TAB from row " + \
                "%s col %s" % (evt_row, evt_col)
            self.tbl_editor.ProcessMoveAway(event, KEYBOARD_MOVE, evt_row, 
                                            evt_col)
