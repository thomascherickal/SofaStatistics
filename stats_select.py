import os

import wx

import util

TEXT_BROWN = (90, 74, 61)
SCRIPT_PATH = util.get_script_path()
TEST_TTEST = "t-test"
TEST_ANOVA = "ANOVA"
TEST_WILCOXON = "Wilcoxon Signed Ranks"
TEST_MANN_WHITNEY = "Mann-Whitney U"
TEST_KRUSKAL_WALLIS = "Kruskal-Wallis H"
TEST_CHI_SQUARE = "Chi Square"
TEST_SPEARMANS = "Spearman's Correlation"
TEST_PEARSONS = "Pearson's Correlation"
STATS_TESTS = [TEST_TTEST, TEST_ANOVA, TEST_WILCOXON, TEST_MANN_WHITNEY,
               TEST_KRUSKAL_WALLIS, TEST_CHI_SQUARE, TEST_SPEARMANS,
               TEST_PEARSONS]
MAIN_LEFT = 30


class StatsSelectDlg(wx.Dialog):
    
    def __init__(self):
        wx.Dialog.__init__(self, None, title="Select Statistical Test", 
              size=(800, 542),
              style=wx.CAPTION|wx.CLOSE_BOX|wx.MINIMIZE_BOX|wx.SYSTEM_MENU,
              pos=(100, 100))
        inwin = util.in_windows()
        # Windows doesn't include window decorations
        y_start = self.GetClientSize()[1] - self.GetSize()[1]
        self.SetClientSize(self.GetSize())
        self.panel = wx.Panel(self, size=(800, 542)) # needed by Windows
        self.panel.Bind(wx.EVT_PAINT, self.OnPaint)        
        # icon
        ib = wx.IconBundle()
        ib.AddIconFromFile(os.path.join(SCRIPT_PATH, 
                                        "images", 
                                        "tinysofa.xpm"), 
                           wx.BITMAP_TYPE_XPM)
        self.SetIcons(ib)
        # background image
        bk = "stats_select_win" if inwin else "stats_select"
        img_stats_select = wx.Image(os.path.join(SCRIPT_PATH, 
                                                 "images", 
                                                 "%s.xpm" % bk ), 
                           wx.BITMAP_TYPE_XPM)
        self.bmp_stats_select = wx.BitmapFromImage(img_stats_select)
        # with or without help
        radDirect = wx.RadioButton(self.panel, -1, pos=(MAIN_LEFT, 55), 
                                   style=wx.RB_SINGLE)
        radDirect.Bind(wx.EVT_RADIOBUTTON, self.OnRadioDirectButton)
        radAssisted = wx.RadioButton(self.panel, -1, pos=(MAIN_LEFT, 85), 
                                     style=wx.RB_SINGLE)
        radAssisted.Bind(wx.EVT_RADIOBUTTON, self.OnRadioAssistedButton)
        # questions
        self.radDifferences = wx.RadioButton(self.panel, -1, 
                                             pos=(MAIN_LEFT, 115), 
                                             style=wx.RB_SINGLE)
        self.radDifferences.Enable(False)
        self.radRelationships = wx.RadioButton(self.panel, -1, 
                                               pos=(MAIN_LEFT, 328), 
                                               style=wx.RB_SINGLE)
        self.radRelationships.Enable(False)
        # choices
        DIFF_LN_1 = 180
        n_group_choices = ["2 groups", "3 or more"]
        if not inwin:
            n_group_choices = ["%s " % x for x in n_group_choices]
        self.radboxNGroups = wx.RadioBox(self.panel, -1, "No. of groups",
                                         choices=n_group_choices,
                                         pos=(MAIN_LEFT + 25, DIFF_LN_1))
        self.radboxNGroups.Enable(False)
        DIFF_LN_2 = 250
        if inwin:
            DIFF_LN_2 += 10
        parametric_choices = ["Normal", "Not"]
        if not inwin:
            parametric_choices = ["%s " % x for x in parametric_choices]
        self.radboxParametric1 = wx.RadioBox(self.panel, -1, "Parametric",
                                             choices=parametric_choices,
                                             pos=(MAIN_LEFT + 25, DIFF_LN_2))
        self.radboxParametric1.Enable(False)
        BUTTON_DROP = 10
        if inwin:
            BUTTON_DROP += 10
        self.btnParametric1 = wx.Button(self.panel, -1, "Help me choose",
                                        pos=(MAIN_LEFT + 165, 
                                             DIFF_LN_2 + BUTTON_DROP)) 
        self.btnParametric1.Enable(False)
        DIFF_LN_3 = 410
        self.radboxNonNumeric = wx.RadioBox(self.panel, -1, 
                                            "Type of Data",
                                            choices=["Categories", "Numbers"],
                                            pos=(MAIN_LEFT + 25, DIFF_LN_3))
        self.radboxNonNumeric.Enable(False)
        self.radboxParametric2 = wx.RadioBox(self.panel, -1, "Parametric",
                                             choices=parametric_choices,
                                             pos=(MAIN_LEFT + 225, DIFF_LN_3))
        self.radboxParametric2.Enable(False)
        self.btnParametric2 = wx.Button(self.panel, -1, "Help me choose",
                                       pos=(MAIN_LEFT + 365, 
                                            DIFF_LN_3 + BUTTON_DROP))
        self.btnParametric2.Enable(False)
        # listbox of tests
        LST_LEFT = 565
        LST_WIDTH = 200
        LST_TOP = 55
        LST_HEIGHT = 210
        self.lstTests = wx.ListCtrl(self.panel, -1, 
                                    pos=(LST_LEFT, LST_TOP), size=(LST_WIDTH, 
                                                                   LST_HEIGHT),
                                    style=wx.LC_REPORT)
        #il = wx.ImageList(16, 16)
        #for img in ["tick", "cross"]:
        #    bmp = wx.Bitmap(os.path.join(SCRIPT_PATH, "images", "%s.png" % img), 
        #                                wx.BITMAP_TYPE_PNG)
        #    il.Add(bmp)
        #self.lstTests.AssignImageList(il, wx.IMAGE_LIST_SMALL)
        self.lstTests.InsertColumn(0, "Statistical Test")
        self.lstTests.SetColumnWidth(0, LST_WIDTH)
        for i, test in enumerate(STATS_TESTS):
            idx = self.lstTests.InsertStringItem(i, test)
            self.lstTests.SetItemImage(idx, 0, 0)
        self.lstTests.Select(0)
        # run test button
        self.btnRun = wx.Button(self.panel, -1, "RUN TEST",
                                pos=(675, LST_TOP + LST_HEIGHT + 20))
        # close button
        self.btnClose = wx.Button(self.panel, wx.ID_CLOSE,
                                  pos=(675, 500))
        self.btnClose.Bind(wx.EVT_BUTTON, self.OnCloseClick)
        
    def OnPaint(self, event):
        """
        Cannot use static bitmaps and static text to replace.  In windows
            doesn't show background wallpaper.
        NB painting like this sets things behind the controls.
        """
        
        panel_dc = wx.PaintDC(self.panel)
        panel_dc.DrawBitmap(self.bmp_stats_select, 0, 0, True)
        panel_dc.SetTextForeground(TEXT_BROWN)
        panel_dc.SetFont(wx.Font(13, wx.SWISS, wx.NORMAL, wx.BOLD))
        panel_dc.DrawLabel("SELECT A STATISTICAL TEST HERE", 
           wx.Rect(MAIN_LEFT + 25, 50, 100, 100))
        panel_dc.DrawLabel("OR GET HELP CHOOSING BELOW", 
           wx.Rect(MAIN_LEFT + 25, 85, 100, 100))
        panel_dc.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        panel_dc.DrawLabel("Tests that show if there is a difference", 
           wx.Rect(MAIN_LEFT + 25, 115, 100, 100))
        panel_dc.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.NORMAL))
        panel_dc.DrawLabel("E.g. Do females have a larger vocabulary than " + \
                           "males?", 
           wx.Rect(MAIN_LEFT, 145, 100, 100))
        panel_dc.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        panel_dc.DrawLabel("Tests that show if there is a relationship", 
           wx.Rect(MAIN_LEFT + 25, 328, 100, 100))
        panel_dc.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.NORMAL))
        panel_dc.DrawLabel("E.g. Does wealth increase with age?", 
           wx.Rect(MAIN_LEFT, 360, 100, 100))
        event.Skip()
    
    def OnRadioDirectButton(self, event):
        self.radDifferences.Enable(False)
        self.radRelationships.Enable(False)
        
    def OnRadioAssistedButton(self, event):
        self.radDifferences.Enable(True)
        self.radRelationships.Enable(True)        
    
    def OnCloseClick(self, event):
        self.Destroy()
        
if __name__ == "__main__": 
    
    app = wx.PySimpleApp()
    dlg = StatsSelectDlg()
    dlg.ShowModal()
    app.MainLoop()