from __future__ import print_function

import wx

class KeyDownEvent(wx.PyCommandEvent):
    "See 3.6.1 in wxPython in Action"
    def __init__(self, evtType, id):
        wx.PyCommandEvent.__init__(self, evtType, id)
    
    def set_key_code(self, keycode):
        self.keycode = keycode
    
    def get_key_code(self):
        return self.keycode

# new event type to pass around
myEVT_TEXT_BROWSE_KEY_DOWN = wx.NewEventType()
# event to bind to
EVT_TEXT_BROWSE_KEY_DOWN = wx.PyEventBinder(myEVT_TEXT_BROWSE_KEY_DOWN, 1)


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
        self.btn_browse.Bind(wx.EVT_KEY_DOWN, self.on_btn_browse_key_down)
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
        if event.GetKeyCode() in [wx.WXK_RETURN]:
            key_event = KeyDownEvent(myEVT_TEXT_BROWSE_KEY_DOWN, self.GetId())
            key_event.SetEventObject(self)
            key_event.set_key_code(wx.WXK_RETURN)
            self.GetEventHandler().ProcessEvent(key_event)
        elif event.get_key_code() in [wx.WXK_TAB]:
            self.btn_browse.SetFocus()
        else:
            event.Skip()
    
    def on_btn_browse_key_down(self, event):
        """
        Respond to keypresses on the browse button.
        """
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_TAB:
            self.txt.SetFocus()
        else: # e.g. let it be processed
            event.Skip()
    
    def on_btn_browse_click(self, event):
        "Open dialog and takes the file selected (if any)"
        dlg_get_file = wx.FileDialog(self, message=self.file_phrase, 
                                   wildcard=self.wildcard)
            #defaultDir="spreadsheets", 
            #defaultFile="", )
        #MUST have a parent to enforce modal in Windows
        if dlg_get_file.ShowModal() == wx.ID_OK:
            self.txt.SetValue("%s" % dlg_get_file.GetPath())
        dlg_get_file.Destroy()
        self.txt.SetFocus()
    
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
    