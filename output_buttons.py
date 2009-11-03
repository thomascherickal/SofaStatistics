import wx


class OutputButtons(object):
    
    "The standard buttons used in output dialogs"
    
    def SetupOutputButtons(self):
        #main
        self.btnRun = wx.Button(self.panel, -1, _("RUN"))
        self.btnRun.Bind(wx.EVT_BUTTON, self.OnButtonRun)
        self.chkAddToReport = wx.CheckBox(self.panel, -1, _("Add to\nreport"))
        self.chkAddToReport.SetValue(True)
        self.btnExport = wx.Button(self.panel, -1, _("EXPORT"))
        self.btnExport.Bind(wx.EVT_BUTTON, self.OnButtonExport)
        self.btnHelp = wx.Button(self.panel, wx.ID_HELP)
        self.btnHelp.Bind(wx.EVT_BUTTON, self.OnButtonHelp)
        self.btnClear = wx.Button(self.panel, -1, _("CLEAR"))
        self.btnClear.Bind(wx.EVT_BUTTON, self.OnButtonClear)
        self.btnClose = wx.Button(self.panel, wx.ID_CLOSE)
        self.btnClose.Bind(wx.EVT_BUTTON, self.OnClose)
        # add to sizer
        self.szrButtons = wx.FlexGridSizer(rows=3, cols=1, hgap=5, vgap=5)
        self.szrButtons.AddGrowableRow(2,2) #only relevant if surrounding sizer 
        #  stretched vertically enough by its content
        self.szrButtons.Add(self.btnRun, 0)
        self.szrButtons.Add(self.chkAddToReport)
        self.szrButtons.Add(self.btnExport, 0, wx.TOP, 8)
        self.szrButtons.Add(self.btnHelp, 0)
        self.szrButtons.Add(self.btnClear, 0)
        self.szrButtons.Add(self.btnClose, 1, wx.ALIGN_BOTTOM)