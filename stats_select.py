import os

import wx

import my_globals
import anova
import chisquare
import kruskal_wallis
import mann_whitney
import my_exceptions
import pearsonsr
import projects
import spearmansr
import ttest_indep
import ttest_paired
import util
import wilcoxon

TEXT_BROWN = (90, 74, 61)
TEST_TTEST_INDEP = "Independent t-test"
TEST_TTEST_PAIRED = "Paired t-test"
TEST_ANOVA = "ANOVA"
TEST_WILCOXON = "Wilcoxon Signed Ranks"
TEST_MANN_WHITNEY = "Mann-Whitney U"
TEST_KRUSKAL_WALLIS = "Kruskal-Wallis H"
TEST_CHI_SQUARE = "Chi Square"
TEST_SPEARMANS_R = "Spearman's Correlation"
TEST_PEARSONS_R = "Pearson's Correlation"
STATS_TESTS = [TEST_TTEST_INDEP, TEST_TTEST_PAIRED, TEST_ANOVA, TEST_WILCOXON, 
               TEST_MANN_WHITNEY, TEST_KRUSKAL_WALLIS, TEST_CHI_SQUARE, 
               TEST_SPEARMANS_R, TEST_PEARSONS_R]
MAIN_LEFT = 45
HELP_LEFT = MAIN_LEFT + 235
REL_TOP = 330
BUTTON1_LEFT = MAIN_LEFT + 20
BUTTON2_LEFT = MAIN_LEFT + 130
INWIN = util.in_windows()
CONFIG_LEFT = 620 if not INWIN else 630
BUTTON_LIFT = 0 if INWIN else 4
DIV_LINE_WIDTH = 203


class StatsSelectDlg(wx.Dialog):
    
    def __init__(self, dbe, conn_dets, default_dbs=None, 
                 default_tbls=None, fil_labels="", fil_css="", fil_report="", 
                 fil_script="", var_labels=None, var_notes=None, 
                 val_dics=None):
        wx.Dialog.__init__(self, None, title="Select Statistical Test", 
              size=(800, 542),
              style=wx.CAPTION|wx.CLOSE_BOX|wx.MINIMIZE_BOX|wx.SYSTEM_MENU,
              pos=(100, 100))
        self.dbe = dbe
        self.conn_dets = conn_dets
        self.default_dbs = default_dbs
        self.default_tbls = default_tbls
        self.fil_labels = fil_labels
        self.fil_css = fil_css
        self.fil_report = fil_report
        self.fil_script = fil_script        
        self.var_labels, self.var_notes, self.val_dics = \
            projects.GetLabels(fil_labels)
        # Windows doesn't include window decorations
        y_start = self.GetClientSize()[1] - self.GetSize()[1]
        self.SetClientSize(self.GetSize())
        self.panel = wx.Panel(self, size=(800, 542)) # needed by Windows
        self.panel.SetBackgroundColour(wx.Colour(205, 217, 215))
        self.panel.Bind(wx.EVT_PAINT, self.OnPaint)        
        # icon
        ib = wx.IconBundle()
        ib.AddIconFromFile(os.path.join(my_globals.SCRIPT_PATH, 
                                        "images", 
                                        "tinysofa.xpm"), 
                           wx.BITMAP_TYPE_XPM)
        self.SetIcons(ib)
        # background image
        img_stats_select = wx.Image(os.path.join(my_globals.SCRIPT_PATH, 
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
                                               pos=(MAIN_LEFT, REL_TOP))
        self.radRelationships.Bind(wx.EVT_RADIOBUTTON, self.OnRadioRelButton)
        self.radRelationships.Enable(False)
        # choices (NB can't use RadioBoxes and wallpaper in Windows)
        # choices line 1
        DIFF_LN_1 = 190
        self.rad2Groups = wx.RadioButton(self.panel, -1, "2 groups", 
                                         style=wx.RB_GROUP,
                                         pos=(BUTTON1_LEFT, DIFF_LN_1))
        self.rad2Groups.Bind(wx.EVT_RADIOBUTTON, self.OnRadio2GroupsButton)
        self.rad3Groups = wx.RadioButton(self.panel, -1, "3 or more",
                                         pos=(BUTTON2_LEFT, DIFF_LN_1))
        self.rad3Groups.Bind(wx.EVT_RADIOBUTTON, self.OnRadio3GroupsButton)
        self.rad2Groups.Enable(False)
        self.rad3Groups.Enable(False)
        self.btnGroupsHelp = wx.Button(self.panel, wx.ID_HELP, 
                                       pos=(HELP_LEFT, DIFF_LN_1 - BUTTON_LIFT))
        self.btnGroupsHelp.Enable(False)
        self.btnGroupsHelp.Bind(wx.EVT_BUTTON, self.OnGroupsHelpButton)
        # divider
        wx.StaticLine(self.panel, pos=(BUTTON1_LEFT, DIFF_LN_1 + 30),
                      size=(DIV_LINE_WIDTH, 1))   
        # choices line 2
        DIFF_LN_2 = 235
        lbl_normal = "Normal"
        lbl_not_normal = "Not normal"
        self.radNormal1 = wx.RadioButton(self.panel, -1, lbl_normal, 
                                         style=wx.RB_GROUP,
                                         pos=(BUTTON1_LEFT, DIFF_LN_2))
        self.radNormal1.Bind(wx.EVT_RADIOBUTTON, self.OnRadioButton)
        self.radNotNormal1 = wx.RadioButton(self.panel, -1, lbl_not_normal,
                                            pos=(BUTTON2_LEFT, DIFF_LN_2))
        self.radNotNormal1.Bind(wx.EVT_RADIOBUTTON, self.OnRadioButton)
        self.radNormal1.Enable(False)
        self.radNotNormal1.Enable(False)
        self.btnNormalHelp1 = wx.Button(self.panel, wx.ID_HELP,
                                    pos=(HELP_LEFT, DIFF_LN_2 - BUTTON_LIFT))
        self.btnNormalHelp1.Bind(wx.EVT_BUTTON, self.OnNormalHelp1Button)
        self.btnNormalHelp1.Enable(False)
        # divider
        wx.StaticLine(self.panel, pos=(BUTTON1_LEFT, DIFF_LN_2 + 30),
                      size=(DIV_LINE_WIDTH, 1))
        # choices line 3
        DIFF_LN_3 = 280
        self.radIndep = wx.RadioButton(self.panel, -1, "Independent", 
                                       style=wx.RB_GROUP,
                                       pos=(BUTTON1_LEFT, DIFF_LN_3))
        self.radIndep.Bind(wx.EVT_RADIOBUTTON, self.OnRadioButton)
        self.radPaired = wx.RadioButton(self.panel, -1, "Paired",
                                        pos=(BUTTON2_LEFT, DIFF_LN_3))
        self.radPaired.Bind(wx.EVT_RADIOBUTTON, self.OnRadioButton)
        self.radIndep.Enable(False)
        self.radPaired.Enable(False)
        self.btnIndepHelp = wx.Button(self.panel, wx.ID_HELP,
                                       pos=(HELP_LEFT, DIFF_LN_3 - BUTTON_LIFT))
        self.btnIndepHelp.Bind(wx.EVT_BUTTON, self.OnIndepHelpButton)
        self.btnIndepHelp.Enable(False)
        # choices line 4
        DIFF_LN_4 = REL_TOP + 60
        self.radNominal = wx.RadioButton(self.panel, -1, "Names Only", 
                                      style=wx.RB_GROUP,
                                      pos=(BUTTON1_LEFT, DIFF_LN_4))
        self.radNominal.Bind(wx.EVT_RADIOBUTTON, self.OnRadioNominalButton)
        self.radOrdered = wx.RadioButton(self.panel, -1, "Ordered",
                                      pos=(BUTTON2_LEFT, DIFF_LN_4))
        self.radOrdered.Bind(wx.EVT_RADIOBUTTON, self.OnRadioOrderedButton)
        self.radNominal.Enable(False)
        self.radOrdered.Enable(False)
        self.btnTypeHelp = wx.Button(self.panel, wx.ID_HELP, 
                                     pos=(HELP_LEFT, DIFF_LN_4 - BUTTON_LIFT))
        self.btnTypeHelp.Bind(wx.EVT_BUTTON, self.OnTypeHelpButton)
        self.btnTypeHelp.Enable(False)
        # divider
        wx.StaticLine(self.panel, pos=(BUTTON1_LEFT, DIFF_LN_4 + 30),
                      size=(DIV_LINE_WIDTH, 1))   
        # choices line 4
        DIFF_LN_5 = REL_TOP + 105
        self.radNormal2 = wx.RadioButton(self.panel, -1, lbl_normal, 
                                         style=wx.RB_GROUP,
                                         pos=(BUTTON1_LEFT, DIFF_LN_5))
        self.radNormal2.Bind(wx.EVT_RADIOBUTTON, self.OnRadioButton)
        self.radNotNormal2 = wx.RadioButton(self.panel, -1, lbl_not_normal,
                                            pos=(BUTTON2_LEFT, DIFF_LN_5))
        self.radNotNormal2.Bind(wx.EVT_RADIOBUTTON, self.OnRadioButton)
        self.radNormal2.Enable(False)
        self.radNotNormal2.Enable(False)
        self.btnNormalHelp2 = wx.Button(self.panel, wx.ID_HELP,
                                        pos=(HELP_LEFT, DIFF_LN_5))
        self.btnNormalHelp2.Bind(wx.EVT_BUTTON, self.OnNormalHelp2Button)
        self.btnNormalHelp2.Enable(False)
        # listbox of tests
        LST_LEFT = 555
        LST_WIDTH = 200
        LST_TOP = 55
        LST_HEIGHT = 220
        SCROLL_ALLOWANCE = 20
        self.lstTests = wx.ListCtrl(self.panel, -1, pos=(LST_LEFT, LST_TOP), 
                                size=(LST_WIDTH + SCROLL_ALLOWANCE, LST_HEIGHT),
                                style=wx.LC_REPORT)
        il = wx.ImageList(16, 16)
        self.idx_tick = 0
        self.idx_blank = 1
        tick = "tickwin" if INWIN else "tick"
        for img in [tick, "blank"]:
            bmp = wx.Bitmap(os.path.join(my_globals.SCRIPT_PATH, "images", 
                                         "%s.png" % img), 
                                         wx.BITMAP_TYPE_PNG)
            il.Add(bmp)
        self.lstTests.AssignImageList(il, wx.IMAGE_LIST_SMALL)
        self.lstTests.InsertColumn(0, "Statistical Test")
        self.lstTests.SetColumnWidth(0, LST_WIDTH - 25)
        self.lstTests.InsertColumn(1, "")
        self.lstTests.SetColumnWidth(1, 25)
        for i, test in enumerate(STATS_TESTS):
            idx = self.lstTests.InsertStringItem(i, test)
            self.lstTests.SetStringItem(i, 1, "", self.idx_blank)
        idx = self.lstTests.InsertStringItem(i+1, "")
        self.lstTests.Select(0)
        # run test button
        self.btnConfig = wx.Button(self.panel, -1, "CONFIGURE TEST >>>",
                                pos=(CONFIG_LEFT, LST_TOP + LST_HEIGHT + 20))
        self.btnConfig.Bind(wx.EVT_BUTTON, self.OnConfigClicked)
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
           wx.Rect(MAIN_LEFT, 53, 100, 100))
        panel_dc.DrawLabel("OR GET HELP CHOOSING BELOW", 
           wx.Rect(MAIN_LEFT, 95, 100, 100))
        panel_dc.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        panel_dc.DrawLabel("Tests that show if there is a difference", 
           wx.Rect(BUTTON1_LEFT, 135, 100, 100))
        panel_dc.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.NORMAL))
        panel_dc.DrawLabel("E.g. Do females have a larger vocabulary " + \
                           "average than males?", 
           wx.Rect(BUTTON1_LEFT, 160, 100, 100))
        panel_dc.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        panel_dc.DrawLabel("Tests that show if there is a relationship", 
           wx.Rect(BUTTON1_LEFT, REL_TOP, 100, 100))
        panel_dc.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.NORMAL))
        panel_dc.DrawLabel("E.g. Does wealth increase with age?", 
           wx.Rect(BUTTON1_LEFT, REL_TOP + 27, 100, 100))
        event.Skip()
        
    def OnRadioDirectButton(self, event):        
        self.radDifferences.SetValue(True)
        self.radDifferences.Enable(False)
        self.DiffSetup(enable=False)
        self.radRelationships.Enable(False)
        self.RelSetup(enable=False)
        self.RemoveTestIndicators()
        
    def OnRadioAssistedButton(self, event):
        self.radDifferences.Enable(True)
        self.DiffSetup(enable=True)
        self.radRelationships.Enable(True)
        self.RelSetup(enable=False)
        # tick first test
        self.lstTests.SetStringItem(0, 1, "", self.idx_tick)
        self.lstTests.Select(0)
        self.RespondToAssistedChoices()
    
    def OnRadioDiffButton(self, event):
        self.DiffSetup(enable=True)
        self.RelSetup(enable=False)
        self.RespondToAssistedChoices()
    
    def OnRadioRelButton(self, event):
        self.RelSetup(enable=True)
        self.DiffSetup(enable=False)
        self.RespondToAssistedChoices()
    
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
        self.IndepSetup(enable=True)
    
    def OnRadio2GroupsButton(self, event):
        self.IndepSetup(enable=True)
        self.RespondToAssistedChoices()
    
    def OnRadio3GroupsButton(self, event):
        self.IndepSetup(enable=False)
        self.RespondToAssistedChoices()

    def OnGroupsHelpButton(self, event):
        wx.MessageBox("Are you looking at the difference between two " + \
          "groups or more?" + \
          "\n\nExample with 2 groups: average vocabulary of Males vs " + \
          "Females." + \
          "\n\nExample with 3 or more groups: average sales figures for " + \
          "the North, South, East, and West regions")
        
    def OnNormalHelp1Button(self, event):
        wx.MessageBox("Under construction")
    
    def IndepSetup(self, enable=True):
        # set left first
        try:
            self.radIndep.SetValue(True)
        except:
            pass
        self.radIndep.Enable(enable)
        self.radPaired.Enable(enable)
        self.btnIndepHelp.Enable(enable)
        
    def OnIndepHelpButton(self, event):
        wx.MessageBox("Is your data for each group recorded in different " + \
          "rows (independent) or together on same row (paired)?" + \
          "\n\nExample of Independent data: if looking at Male vs Female " + \
          "vocabulary we do not have both male and female scores in the " + \
          "same rows. Male and Female data is independent." + \
          "\n\nExample of Paired data: if looking at mental ability in the " + \
          "Morning vs the Evening we might have one row per person with " + \
          "both time periods in the same row. Morning and Evening data is " + \
          "paired.")
        
    def RelSetup(self, enable=True):
        "Enable options under Relationships section"
        if not enable:
            # set left first
            try:
                self.radNominal.SetValue(True)
            except:
                pass
        self.radNominal.Enable(enable)
        self.radOrdered.Enable(enable)
        self.btnTypeHelp.Enable(enable)
        self.NormalRelSetup(enable=False) # only set to True when cat selected
    
    def OnRadioNominalButton(self, event):
        self.NormalRelSetup(enable=False)
        self.RespondToAssistedChoices()
    
    def OnRadioOrderedButton(self, event):
        self.NormalRelSetup(enable=True)
        self.RespondToAssistedChoices()
    
    def OnTypeHelpButton(self, event):
        wx.MessageBox("Names only data (Nominal) is just labels or names. " + \
          "Ordered data has a sense of order and includes Ordinal (order " + \
          "but no amount) and Quantitative (actual numbers)." + \
          "\n\nExample of Names Only data: sports codes ('Soccer', " + \
          "'Badminton', 'Skiing' etc)" + \
          "\n\nExample of Ordered data: ratings of restaurant " + \
          "service standards (1 - Very Poor, 2 - Poor, 3 - Average etc).")
    
    def OnNormalHelp2Button(self, event):
        wx.MessageBox("Under construction")
    
    def NormalRelSetup(self, enable=True):
        # set left first
        try:
            self.radNormal2.SetValue(True)
        except:
            pass
        self.radNormal2.Enable(enable)
        self.radNotNormal2.Enable(enable)
        self.btnNormalHelp2.Enable(enable)
    
    def RemoveTestIndicators(self):
        for i, test in enumerate(STATS_TESTS):
            self.lstTests.SetStringItem(i, 1, "", self.idx_blank)
            self.lstTests.Select(i, on=0)
    
    def OnRadioButton(self, event):
        self.RespondToAssistedChoices()
    
    def RespondToAssistedChoices(self):
        test_type = self.SelectTest()
        if test_type:
            self.RemoveTestIndicators()
            self.IndicateTest(test_type)
    
    def SelectTest(self):
        """
        Select which test meets the criteria selected.
        Returns test_type from STATS_TESTS.
        STATS_TESTS = [TEST_TTEST_INDEP, TEST_TTEST_PAIRED, TEST_ANOVA, 
            TEST_WILCOXON, TEST_MANN_WHITNEY, TEST_KRUSKAL_WALLIS, 
            TEST_CHI_SQUARE, TEST_SPEARMANS_R, TEST_PEARSONS_R
        """
        if self.radDifferences.GetValue():
            if self.rad2Groups.GetValue():
                if self.radNormal1.GetValue():
                    if self.radIndep.GetValue():
                        test_type = TEST_TTEST_INDEP
                    elif self.radPaired.GetValue():
                        test_type = TEST_TTEST_PAIRED
                    else:
                        raise my_exceptions.InvalidTestSelectionException
                elif self.radNotNormal1.GetValue():
                    if self.radIndep.GetValue():
                        test_type = TEST_MANN_WHITNEY
                    elif self.radPaired.GetValue():
                        test_type = TEST_WILCOXON
                    else:
                        raise my_exceptions.InvalidTestSelectionException
                else:
                    raise my_exceptions.InvalidTestSelectionException
            elif self.rad3Groups.GetValue():
                if self.radNormal1.GetValue():
                    test_type = TEST_ANOVA
                else:
                    test_type = TEST_KRUSKAL_WALLIS
            else:
                raise my_exceptions.InvalidTestSelectionException
        elif self.radRelationships.GetValue():
            if self.radNominal.GetValue():
                test_type = TEST_CHI_SQUARE
            elif self.radOrdered.GetValue():
                if self.radNormal2.GetValue():
                    test_type = TEST_PEARSONS_R
                elif self.radNotNormal2.GetValue():
                    test_type = TEST_SPEARMANS_R
                else:
                    raise my_exceptions.InvalidTestSelectionException 
            else:
                raise my_exceptions.InvalidTestSelectionException
        else:
            test_type = None
        return test_type
    
    def IndicateTest(self, test_const):
        "Select a test in the listbox with a tick and a selection."
        if test_const not in STATS_TESTS:
            raise Exception, "IndicateTest was passed a test not from the " + \
                "standard list"
        idx=STATS_TESTS.index(test_const)
        self.lstTests.SetStringItem(idx, 1, "", self.idx_tick)
        self.lstTests.Select(idx)
    
    def OnConfigClicked(self, event):
        idx = self.lstTests.GetFirstSelected()
        try:
            sel_test = STATS_TESTS[idx]
        except Exception:
            wx.MessageBox("Please select a statistical test on the list")
            event.Skip()
            return
        if sel_test == TEST_TTEST_INDEP:
            dlg = ttest_indep.DlgConfig("Configure Independent t-test", 
                self.dbe, self.conn_dets, self.default_dbs, self.default_tbls, 
                self.fil_labels, self.fil_css, self.fil_report, self.fil_script)
            dlg.ShowModal()        
        elif sel_test == TEST_TTEST_PAIRED:
            dlg = ttest_paired.DlgConfig("Configure Paired Samples t-test", 
                self.dbe, self.conn_dets, self.default_dbs, self.default_tbls, 
                self.fil_labels, self.fil_css, self.fil_report, self.fil_script)
            dlg.ShowModal()
        elif sel_test == TEST_ANOVA:
            dlg = anova.DlgConfig("Configure ANOVA test", 
                self.dbe, self.conn_dets, self.default_dbs, self.default_tbls, 
                self.fil_labels, self.fil_css, self.fil_report, self.fil_script,
                takes_range=True)
            dlg.ShowModal()
        elif sel_test == TEST_WILCOXON:
            dlg = wilcoxon.DlgConfig("Configure Wilcoxon Signed Ranks test", 
                self.dbe, self.conn_dets, self.default_dbs, self.default_tbls, 
                self.fil_labels, self.fil_css, self.fil_report, self.fil_script)
            dlg.ShowModal()
        elif sel_test == TEST_MANN_WHITNEY:
            dlg = mann_whitney.DlgConfig("Configure Mann Whitney U test", 
                self.dbe, self.conn_dets, self.default_dbs, self.default_tbls, 
                self.fil_labels, self.fil_css, self.fil_report, self.fil_script)
            dlg.ShowModal()
        elif sel_test == TEST_KRUSKAL_WALLIS:
            dlg = kruskal_wallis.DlgConfig("Configure Kruskal Wallis H test", 
                self.dbe, self.conn_dets, self.default_dbs, self.default_tbls, 
                self.fil_labels, self.fil_css, self.fil_report, self.fil_script,
                takes_range=True)
            dlg.ShowModal()
        elif sel_test == TEST_CHI_SQUARE:
            dlg = chisquare.DlgConfig("Configure Chi Square test", 
                self.dbe, self.conn_dets, self.default_dbs, self.default_tbls, 
                self.fil_labels, self.fil_css, self.fil_report, self.fil_script,
                num_vars_only=False)
            dlg.ShowModal()
        elif sel_test == TEST_PEARSONS_R:
            dlg = pearsonsr.DlgConfig("Configure Pearson's R test", 
                self.dbe, self.conn_dets, self.default_dbs, self.default_tbls, 
                self.fil_labels, self.fil_css, self.fil_report, self.fil_script)
            dlg.ShowModal()
        elif sel_test == TEST_SPEARMANS_R:
            dlg = spearmansr.DlgConfig("Configure Spearman's R test", 
                self.dbe, self.conn_dets, self.default_dbs, self.default_tbls, 
                self.fil_labels, self.fil_css, self.fil_report, self.fil_script)
            dlg.ShowModal()
        else:
            raise Exception, "Unknown test"
        event.Skip()
    
    def OnCloseClick(self, event):
        self.Destroy()
       