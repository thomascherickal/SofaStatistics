import wx


class OutputButtons(object):
    
    "The standard buttons used in output dialogs"
    
    def SetupOutputButtons(self):
        #main
        self.btnRun = wx.Button(self.panel, -1, "RUN")
        self.btnRun.Bind(wx.EVT_BUTTON, self.OnButtonRun)
        #self.btnRun.Bind(wx.EVT_ENTER_WINDOW, self.OnRunEnterWindow)
        #self.btnRun.Bind(wx.EVT_LEAVE_WINDOW, self.BlankStatusBar)        
        self.btnExport = wx.Button(self.panel, -1, "EXPORT")
        self.btnExport.Bind(wx.EVT_BUTTON, self.OnButtonExport)
        #self.btnExport.Bind(wx.EVT_ENTER_WINDOW, self.OnExportEnterWindow)
        #self.btnExport.Bind(wx.EVT_LEAVE_WINDOW, self.BlankStatusBar)
        self.btnHelp = wx.Button(self.panel, wx.ID_HELP)
        self.btnHelp.Bind(wx.EVT_BUTTON, self.OnButtonHelp)
        #self.btnHelp.Bind(wx.EVT_ENTER_WINDOW, self.OnHelpEnterWindow)
        #self.btnHelp.Bind(wx.EVT_LEAVE_WINDOW, self.BlankStatusBar)
        self.btnClear = wx.Button(self.panel, -1, "CLEAR")
        self.btnClear.Bind(wx.EVT_BUTTON, self.OnButtonClear)
        #self.btnClear.Bind(wx.EVT_ENTER_WINDOW, self.OnClearEnterWindow)
        #self.btnClear.Bind(wx.EVT_LEAVE_WINDOW, self.BlankStatusBar)
        self.btnClose = wx.Button(self.panel, wx.ID_CLOSE)
        self.btnClose.Bind(wx.EVT_BUTTON, self.OnClose)
        #self.btnClose.Bind(wx.EVT_ENTER_WINDOW, self.OnCloseEnterWindow)
        #self.btnClose.Bind(wx.EVT_LEAVE_WINDOW, self.BlankStatusBar)
        # add to sizer
        self.szrButtons = wx.FlexGridSizer(rows=3, cols=1, hgap=5, vgap=5)
        self.szrButtons.AddGrowableRow(2,2) #only relevant if surrounding sizer 
        #  stretched vertically enough by its content
        self.szrButtons.Add(self.btnRun, 0, wx.TOP, 0)
        self.szrButtons.Add(self.btnExport, 0)
        self.szrButtons.Add(self.btnHelp, 0)
        self.szrButtons.Add(self.btnClear, 0)
        self.szrButtons.Add(self.btnClose, 1, wx.ALIGN_BOTTOM)
        