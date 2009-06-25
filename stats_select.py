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
MAIN_LEFT = 45


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
        img_stats_select = wx.Image(os.path.join(SCRIPT_PATH, 
                                                 "images", 
                                                 "stats_select.xpm"), 
                           wx.BITMAP_TYPE_XPM)
        self.bmp_stats_select = wx.BitmapFromImage(img_stats_select)
        # direct or assisted
        self.radDirect = wx.RadioButton(self.panel, -1, 
                            pos=(MAIN_LEFT-25, 55), 
                            style=wx.RB_GROUP) # groups all till next RB_GROUP
        self.radDirect.Bind(wx.EVT_RADIOBUTTON, self.OnRadioDirectButton)
        self.radAssisted = wx.RadioButton(self.panel, -1, 
                                          pos=(MAIN_LEFT - 25, 95))
        self.radAssisted.Bind(wx.EVT_RADIOBUTTON, self.OnRadioAssistedButton)
        # main assisted options
        self.radDifferences = wx.RadioButton(self.panel, -1, 
                                             pos=(MAIN_LEFT, 135), 
                                             style=wx.RB_GROUP)
        self.radDifferences.Bind(wx.EVT_RADIOBUTTON, self.OnRadioDiffButton)
        self.radDifferences.Enable(False)
        self.radRelationships = wx.RadioButton(self.panel, -1,
                                               pos=(MAIN_LEFT, 300))
        self.radRelationships.Bind(wx.EVT_RADIOBUTTON, self.OnRadioRelButton)
        self.radRelationships.Enable(False)
        # choices (NB can't use RadioBoxes and wallpaper in Windows)
        # choices line 1
        DIFF_LN_1 = 190
        self.rad2Groups = wx.RadioButton(self.panel, -1, "2 groups", 
                                         style=wx.RB_GROUP,
                                         pos=(MAIN_LEFT + 25, DIFF_LN_1))
        self.rad3Groups = wx.RadioButton(self.panel, -1, "3 or more",
                                         pos=(MAIN_LEFT + 125, DIFF_LN_1))
        self.rad2Groups.Enable(False)
        self.rad3Groups.Enable(False)
        self.btnGroupsHelp = wx.Button(self.panel, -1, "Help", 
                                       pos=(MAIN_LEFT + 255, DIFF_LN_1))
        self.btnGroupsHelp.Enable(False)
        # divider
        wx.StaticLine(self.panel, pos=(MAIN_LEFT + 25, DIFF_LN_1 + 35),
                      size=(190, 1))   
        # choices line 2
        DIFF_LN_2 = 240
        lbl_normal = "Normal"
        lbl_not_normal = "Not normal"
        self.radNormal1 = wx.RadioButton(self.panel, -1, lbl_normal, 
                                         style=wx.RB_GROUP,
                                         pos=(MAIN_LEFT + 25, DIFF_LN_2))
        self.radNotNormal1 = wx.RadioButton(self.panel, -1, lbl_not_normal,
                                            pos=(MAIN_LEFT + 125, DIFF_LN_2))
        self.radNormal1.Enable(False)
        self.radNotNormal1.Enable(False)
        self.btnNormalHelp1 = wx.Button(self.panel, -1, "Help",
                                        pos=(MAIN_LEFT + 255, 
                                             DIFF_LN_2)) 
        self.btnNormalHelp1.Enable(False)
        # choices line 3
        DIFF_LN_3 = 360
        self.radCats = wx.RadioButton(self.panel, -1, "Categories", 
                                      style=wx.RB_GROUP,
                                      pos=(MAIN_LEFT + 25, DIFF_LN_3))
        self.radNums = wx.RadioButton(self.panel, -1, "Numbers",
                                      pos=(MAIN_LEFT + 125, DIFF_LN_3))
        self.radCats.Enable(False)
        self.radNums.Enable(False)
        self.btnTypeHelp = wx.Button(self.panel, -1, "Help", 
                                     pos=(MAIN_LEFT + 255, DIFF_LN_3))
        self.btnTypeHelp.Enable(False)
        # divider
        wx.StaticLine(self.panel, pos=(MAIN_LEFT + 25, DIFF_LN_3 + 35),
                      size=(190, 1))   
        # choices line 4
        DIFF_LN_4 = 410
        self.radNormal2 = wx.RadioButton(self.panel, -1, lbl_normal, 
                                         style=wx.RB_GROUP,
                                         pos=(MAIN_LEFT + 25, DIFF_LN_4))
        self.radNotNormal2 = wx.RadioButton(self.panel, -1, lbl_not_normal,
                                            pos=(MAIN_LEFT + 125, DIFF_LN_4))
        self.radNormal2.Enable(False)
        self.radNotNormal2.Enable(False)
        self.btnNormalHelp2 = wx.Button(self.panel, -1, "Help",
                                        pos=(MAIN_LEFT + 255, 
                                             DIFF_LN_4)) 
        self.btnNormalHelp2.Enable(False)
        

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
        CONFIG_LEFT = 605 if not inwin else 615
        self.btnConfig = wx.Button(self.panel, -1, "CONFIGURE TEST >>>",
                                pos=(CONFIG_LEFT, LST_TOP + LST_HEIGHT + 20))
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
           wx.Rect(MAIN_LEFT, 50, 100, 100))
        panel_dc.DrawLabel("OR GET HELP CHOOSING BELOW", 
           wx.Rect(MAIN_LEFT, 95, 100, 100))
        panel_dc.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        panel_dc.DrawLabel("Tests that show if there is a difference", 
           wx.Rect(MAIN_LEFT + 25, 135, 100, 100))
        panel_dc.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.NORMAL))
        panel_dc.DrawLabel("E.g. Do females have a larger vocabulary than " + \
                           "males?", 
           wx.Rect(MAIN_LEFT + 25, 160, 100, 100))
        panel_dc.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        panel_dc.DrawLabel("Tests that show if there is a relationship", 
           wx.Rect(MAIN_LEFT + 25, 300, 100, 100))
        panel_dc.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.NORMAL))
        panel_dc.DrawLabel("E.g. Does wealth increase with age?", 
           wx.Rect(MAIN_LEFT + 25, 327, 100, 100))
        event.Skip()
        
    def OnRadioDirectButton(self, event):        
        self.radDifferences.SetValue(True)
        self.radDifferences.Enable(False)
        self.DiffSetup(enable=False)
        self.radRelationships.Enable(False)
        self.RelSetup(enable=False)
        
    def OnRadioAssistedButton(self, event):
        self.radDifferences.Enable(True)
        self.DiffSetup(enable=True)
        self.radRelationships.Enable(True)
        self.RelSetup(enable=False)
    
    def OnRadioDiffButton(self, event):
        self.DiffSetup(enable=True)
        self.RelSetup(enable=False)
    
    def OnRadioRelButton(self, event):
        self.RelSetup(enable=True)
        self.DiffSetup(enable=False)
    
    def DiffSetup(self, enable=True):
        "Enable options under Differences section"
        if not enable:
            # set left first
            try:
                self.rad2Groups.SetValue(True)
            except:
                pass
            try:
                self.radNormal1.SetValue(True)
            except:
                pass
        self.rad2Groups.Enable(enable)
        self.rad3Groups.Enable(enable)
        self.btnGroupsHelp.Enable(enable)
        self.radNormal1.Enable(enable)
        self.radNotNormal1.Enable(enable)
        self.btnNormalHelp1.Enable(enable)

    def RelSetup(self, enable=True):
        "Enable options under Relationships section"
        if not enable:
            # set left first
            try:
                self.radCats.SetValue(True)
            except:
                pass
            try:
                self.radNormal2.SetValue(True)
            except:
                pass
        self.radCats.Enable(enable)
        self.radNums.Enable(enable)
        self.btnTypeHelp.Enable(enable)
        self.radNormal2.Enable(enable)
        self.radNotNormal2.Enable(enable)
        self.btnNormalHelp2.Enable(enable)
        
    def OnCloseClick(self, event):
        self.Destroy()
        
if __name__ == "__main__": 
    
    app = wx.PySimpleApp()
    dlg = StatsSelectDlg()
    dlg.ShowModal()
    app.MainLoop()