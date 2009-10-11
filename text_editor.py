"""
TextEditor is the custom grid cell editor - currently only used for the cells
    in the new row.  Needed so that the edited value can be captured when
    navigating away from a cell in editing mode (needed for validation).
"""

import wx
import wx.grid

import my_globals


class TextEditor(wx.grid.PyGridCellEditor):
    
    def __init__(self, src_grid, row, col, new_row):
        wx.grid.PyGridCellEditor.__init__(self)
        self.debug = False
        self.src_grid = src_grid
        self.src_grid.val_being_entered[(row, col)] = None # init
        self.row = row
        self.col = col
        self.new_row = new_row
    
    def BeginEdit(self, row, col, grid):
        debug = False
        if self.debug or debug: print "Editing started"
        val = grid.GetTable().GetValue(row, col)
        self.start_val = val
        self.txt.SetValue(val)
        if self.debug or debug: print "Value set to: %s" % val
        self.txt.SetFocus()

    def Clone(self):
        return TextEditor(self.src_grid, self.row, self.col, self.new_row)
    
    def Create(self, parent, id, evt_handler):
        # created when clicked
        # wx.TE_PROCESS_TAB very important otherwise TAB is swallowed by dialog
        # (but not if grid on a frame or Dialog under Ubuntu - go figure!)
        self.txt = wx.TextCtrl(parent, -1, "", style=wx.TE_PROCESS_TAB)
        self.SetControl(self.txt)
        if evt_handler:
            # so the control itself doesn't handle events but passes to handler
            self.txt.PushEventHandler(evt_handler)
            evt_handler.Bind(wx.EVT_KEY_DOWN, self.OnTxtEdKeyDown)
    
    def EndEdit(self, row, col, grid):
        debug = False
        if self.debug or debug: print "Editing ending"
        changed = False
        val = self.txt.GetValue()
        if val != self.start_val:
            changed = True
            grid.GetTable().SetValue(row, col, val)
        if self.debug or debug:
            print "Value entered was \"%s\"" % val
            print "Editing ended"
        if changed:
            if self.debug or debug: print "Some data in new record has changed"
            self.src_grid.SetNewIsDirty(True)
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
        NB based on settings_grid.TblEditor.OnGridKeyDown
        """
        debug = False
        self.src_grid.val_being_entered[(self.row, self.col)] = \
            self.txt.GetValue()        
        keycode = event.GetKeyCode()
        if self.debug or debug: 
            print "Keypress %s recognised in custom editor" % keycode
        if keycode in [wx.WXK_TAB, wx.WXK_RETURN]:
            if keycode == wx.WXK_TAB:
                if event.ShiftDown():
                    direction = my_globals.MOVE_LEFT
                else:
                    direction = my_globals.MOVE_RIGHT
            elif keycode == wx.WXK_RETURN:
                direction = my_globals.MOVE_DOWN
            src_row=self.row
            src_col=self.col
            if self.debug: 
                print "OnTxtEdKeyDown - Keypress %s " % keycode + \
                    "in row %s col %s" % (src_row, src_col)
                print "Number cols: %s" % len(self.src_grid.GetColsN())
            final_col = (src_col == self.src_grid.GetColsN() - 1)            
            if final_col and direction in [my_globals.MOVE_RIGHT, 
                                           my_globals.MOVE_DOWN]:
                self.src_grid.AddCellMoveEvt(direction, dest_row=None, 
                                             dest_col=None)
            else:
                event.Skip()
        else:
            event.Skip()
