from __future__ import print_function

import wx
import wx.grid

class KeyDownEvent(wx.PyCommandEvent):
    "See 3.6.1 in wxPython in Action"
    def __init__(self, evtType, id):
        wx.PyCommandEvent.__init__(self, evtType, id)
    
    def set_key_code(self, keycode):
        self.keycode = keycode
    
    def get_key_code(self):
        return self.keycode

# new event types to pass around
myEVT_TEXT_BROWSE_KEY_DOWN = wx.NewEventType()
# events to bind to
EVT_TEXT_BROWSE_KEY_DOWN = wx.PyEventBinder(myEVT_TEXT_BROWSE_KEY_DOWN, 1)

MY_KEY_TEXT_BROWSE_BROWSE_BTN = 1000 # wx.WXK_SPECIAL20 is 212 and is highest?
MY_KEY_TEXT_BROWSE_MOVE_NEXT = 1001


class TextBrowse(wx.PyControl):
    """
    Custom control with a text box and browse button (to populate text box).
    Handles Enter key and tab key strokes as expected. Tab from text takes you 
        to the Browse button.  Enter in the text disables editor and we go down.
        Tab from the Browse button and we go back to the text.  Enter is allowed 
        to be processed normally.
    NB if Enter hit when in text box, custom event sent for processing.
    """

    def __init__(self, parent, id, grid, file_phrase, wildcard=""):
        wx.Control.__init__(self, parent, -1)
        self.parent = parent
        self.grid = grid
        self.file_phrase = file_phrase
        self.wildcard = wildcard
        self.txt = wx.TextCtrl(self, -1, "", style=wx.TE_PROCESS_ENTER)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.txt.Bind(wx.EVT_KEY_DOWN, self.on_txt_key_down)
        self.btn_browse = wx.Button(self, -1, _("Browse ..."))
        self.btn_browse.Bind(wx.EVT_BUTTON, self.on_btn_browse_click)
        szr = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_margins = 3
        self.btn_margin = 3
        szr.Add(self.txt, 1, wx.RIGHT|wx.LEFT, self.txt_margins)
        szr.Add(self.btn_browse, 0, wx.RIGHT, self.btn_margin)
        szr.SetSizeHints(self)
        self.SetSizer(szr)
        self.Layout()
        
    def on_size(self, event):
        overall_width = self.GetSize()[0]
        btn_width, btn_height = self.btn_browse.GetSize()
        inner_padding = (2*self.txt_margins) + self.btn_margin
        txt_width = overall_width - (btn_width + inner_padding)
        self.txt.SetSize(wx.Size(txt_width, btn_height-2))
        self.txt.SetDimensions(-1, 3, txt_width, -1)
        btn_x_pos = overall_width - (btn_width + self.btn_margin)        
        self.btn_browse.SetDimensions(btn_x_pos, 2, btn_width, btn_height)
        #event.Skip() # otherwise, resizing sets infinite number of EndEdits!    
    
    def on_txt_key_down(self, event):
        """
        http://wiki.wxpython.org/AnotherTutorial ...
        ... #head-999ff1e3fbf5694a51a91cf4ed2140f692da013c
        """
        if event.GetKeyCode() in [wx.WXK_RETURN, wx.WXK_TAB]:
            key_event = KeyDownEvent(myEVT_TEXT_BROWSE_KEY_DOWN, self.GetId())
            key_event.SetEventObject(self)
            key_event.set_key_code(MY_KEY_TEXT_BROWSE_MOVE_NEXT)
            self.GetEventHandler().ProcessEvent(key_event)
        elif event.GetKeyCode() == wx.WXK_ESCAPE:
            key_event = KeyDownEvent(myEVT_TEXT_BROWSE_KEY_DOWN, self.GetId())
            key_event.SetEventObject(self)
            key_event.set_key_code(wx.WXK_ESCAPE)
            self.GetEventHandler().ProcessEvent(key_event)
        else:
            event.Skip()
        
    def on_btn_browse_click(self, event):
        """
        Open dialog and takes the file selected (if any)
        """
        gotval = False
        dlg_get_file = wx.FileDialog(self, message=self.file_phrase, 
                                   wildcard=self.wildcard)
            #defaultDir="spreadsheets", 
            #defaultFile="", )
        #MUST have a parent to enforce modal in Windows
        if dlg_get_file.ShowModal() == wx.ID_OK:
            self.txt.SetValue("%s" % dlg_get_file.GetPath())
            gotval = True
        dlg_get_file.Destroy()
        if gotval:
            key_event = KeyDownEvent(myEVT_TEXT_BROWSE_KEY_DOWN, self.GetId())
            key_event.SetEventObject(self)
            key_event.set_key_code(MY_KEY_TEXT_BROWSE_BROWSE_BTN)
            self.GetEventHandler().ProcessEvent(key_event)
    
    def set_text(self, text):
        self.txt.SetValue(text)
    
    def set_insertion_point(self, i):
        self.txt.SetInsertionPoint(i)
    
    def get_text(self):
        return self.txt.GetValue()
    
    def set_focus(self):
        "Must implement this if I want to call for the custom control"
        self.txt.SetFocus()


class GridCellTextBrowseEditor(wx.grid.PyGridCellEditor):
    """
    Provides a text box and a browse button (which can populate the text box).
    The text browser can send a special event to the grid frame if Enter key
        pressed while in the text box.
    """
    def __init__(self, grid, file_phrase, wildcard):
        self.debug = False
        wx.grid.PyGridCellEditor.__init__(self)
        self.grid = grid
        self.file_phrase = file_phrase
        self.wildcard = wildcard
    
    def Create(self, parent, id, evt_handler):
        # wxPython
        self.text_browse = TextBrowse(parent, -1, self.grid, self.file_phrase, 
                                      self.wildcard)
        self.SetControl(self.text_browse)
        if evt_handler:
            self.text_browse.PushEventHandler(evt_handler)
    
    def BeginEdit(self, row, col, grid):
        # wxPython
        if self.debug: print("Beginning edit")
        self.text_browse.set_text(grid.GetCellValue(row, col))
        self.text_browse.set_focus()
    
    def StartingKey(self, event):
        # wxPython
        if event.GetKeyCode() <= 255:
            self.text_browse.set_text(chr(event.GetKeyCode()))
            self.text_browse.set_insertion_point(1)
        else:
            event.Skip()
    
    def SetSize(self, rect):
        # wxPython
        self.text_browse.SetDimensions(rect.x, rect.y-2, rect.width, 
                                       rect.height+5, wx.SIZE_ALLOW_MINUS_ONE)
       
    def EndEdit(self, row, col, grid):
        # wxPython
        "TODO - if resized while editing, infinite cycling of this!"
        grid.SetCellValue(row, col, self.text_browse.get_text())
        return True
    
    def Reset(self):
        # wxPython
        pass # N/A
    
    def Clone(self):
        # wxPython
        return GridCellTextBrowseEditor(self.file_phrase, self.wildcard)


class GridCellPwdEditor(wx.grid.PyGridCellEditor):
    """
    Provides a password text box.
    """
    def __init__(self):
        self.debug = False
        wx.grid.PyGridCellEditor.__init__(self)
    
    def Create(self, parent, id, evt_handler):
        # wxPython
        self.pwd_editor = wx.TextCtrl(parent, -1, style=wx.TE_PASSWORD)
        self.SetControl(self.pwd_editor)
        if evt_handler:
            self.pwd_editor.PushEventHandler(evt_handler)
    
    def BeginEdit(self, row, col, grid):
        # wxPython
        if self.debug: print("Beginning edit")
        self.start_val = grid.GetTable().GetValue(row, col)
        self.pwd_editor.SetValue(self.start_val)
        self.pwd_editor.SetInsertionPointEnd()
        self.pwd_editor.SetFocus()
        self.pwd_editor.SetSelection(0, self.pwd_editor.GetLastPosition())
       
    def EndEdit(self, row, col, grid):
        # wxPython
        changed = False
        val = self.pwd_editor.GetValue()
        if val != self.start_val:
            changed = True
            grid.GetTable().SetValue(row, col, val) # update the table
        self.start_val = ""
        # self.pwd_editor.SetValue("")
        return changed
    
    def Reset(self):
        # wxPython
        self.pwd_editor.SetValue(self.start_val)
        self.pwd_editor.SetInsertionPointEnd()
    
    def Clone(self):
        # wxPython
        return GridCellPwdEditor()
       
    
class GridCellPwdRenderer(wx.grid.PyGridCellRenderer):
    
    def __init__(self):
        wx.grid.PyGridCellRenderer.__init__(self)
    
    def Draw(self, grid, attr, dc, rect, row, col, isSelected):
        text = grid.GetCellValue(row, col)
        hAlign, vAlign = attr.GetAlignment()
        bg = wx.WHITE
        dc.SetTextBackground(bg)
        dc.SetTextForeground(attr.GetTextColour())
        font = attr.GetFont()
        font.SetPointSize(font.GetPointSize()+3)
        dc.SetFont(font)
        dc.SetBrush(wx.Brush(bg, wx.SOLID))
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.DrawRectangleRect(rect)
        grid.DrawTextRectangle(dc, len(text)*u"\N{BULLET}", rect, hAlign, 
                               vAlign)
    
    def GetBestSize(self, grid, attr, dc, row, col):
        text = grid.GetCellValue(row, col)
        dc.SetFont(attr.GetFont())
        w, h = dc.GetTextExtent(text)
        return wx.Size(w, h)
    
    def Clone(self):
        return GridCellPwdRenderer()
    