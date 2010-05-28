import os

import wx

import my_globals as mg
import lib
import my_exceptions
#import anova # import as needed for performance
#import chisquare
import config_dlg
#import kruskal_wallis
#import mann_whitney
import normal
#import pearsonsr
#import spearmansr
#import ttest_indep
#import ttest_paired
#import wilcoxon

TEXT_BROWN = (90, 74, 61)
TEST_ANOVA = _("ANOVA")
TEST_CHI_SQUARE = _("Chi Square")
TEST_PEARSONS_R = _("Correlation - Pearson's")
TEST_SPEARMANS_R = _("Correlation - Spearman's")
TEST_KRUSKAL_WALLIS = _("Kruskal-Wallis H")
TEST_MANN_WHITNEY = _("Mann-Whitney U")
TEST_TTEST_INDEP = _("t-test - independent")
TEST_TTEST_PAIRED = _("t-test - paired")
TEST_WILCOXON = _("Wilcoxon Signed Ranks")
STATS_TESTS = [TEST_ANOVA, TEST_CHI_SQUARE, TEST_PEARSONS_R, TEST_SPEARMANS_R,
               TEST_KRUSKAL_WALLIS, TEST_MANN_WHITNEY, TEST_TTEST_INDEP, 
               TEST_TTEST_PAIRED, TEST_WILCOXON]
MAIN_LEFT = 45
HELP_LEFT = MAIN_LEFT + 235
REL_TOP = 330
BUTTON1_LEFT = MAIN_LEFT + 20
BUTTON2_LEFT = MAIN_LEFT + 130
CONFIG_LEFT = 620 if mg.PLATFORM != mg.WINDOWS else 630
BUTTON_LIFT = 0 if mg.PLATFORM == mg.WINDOWS else 4
DIV_LINE_WIDTH = 203

cc = config_dlg.get_cc()


class StatsSelectDlg(wx.Dialog):
    
    def __init__(self, proj_name, var_labels=None, var_notes=None, 
                 val_dics=None):
        wx.Dialog.__init__(self, None, title=_("Select Statistical Test"), 
              size=(800,542),
              style=wx.CAPTION|wx.MINIMIZE_BOX|wx.SYSTEM_MENU,
              pos=(100,100))
        self.proj_name = proj_name
        # Windows doesn't include window decorations
        y_start = self.GetClientSize()[1] - self.GetSize()[1]
        self.SetClientSize(self.GetSize())
        self.panel = wx.Panel(self, size=(800, 542)) # needed by Windows
        self.panel.SetBackgroundColour(wx.Colour(205, 217, 215))
        self.panel.Bind(wx.EVT_PAINT, self.on_paint)        
        config_dlg.add_icon(frame=self)
        # background image
        img_stats_select = wx.Image(os.path.join(mg.SCRIPT_PATH, u"images", 
                                                 u"stats_select.xpm"), 
                           wx.BITMAP_TYPE_XPM)
        self.bmp_stats_select = wx.BitmapFromImage(img_stats_select)
        # direct or assisted
        self.rad_direct = wx.RadioButton(self.panel, -1, 
                            pos=(MAIN_LEFT-25, 55), 
                            style=wx.RB_GROUP) # groups all till next RB_GROUP
        self.rad_direct.Bind(wx.EVT_RADIOBUTTON, self.on_radio_direct_btn)
        self.rad_assisted = wx.RadioButton(self.panel, -1, 
                                          pos=(MAIN_LEFT - 25, 95))
        self.rad_assisted.Bind(wx.EVT_RADIOBUTTON, self.on_radio_assisted_btn)
        # main assisted options
        self.rad_differences = wx.RadioButton(self.panel, -1, 
                                             pos=(MAIN_LEFT, 135), 
                                             style=wx.RB_GROUP)
        self.rad_differences.Bind(wx.EVT_RADIOBUTTON, self.on_radio_diff_btn)
        self.rad_differences.Enable(False)
        self.rad_relationships = wx.RadioButton(self.panel, -1,
                                                pos=(MAIN_LEFT, REL_TOP))
        self.rad_relationships.Bind(wx.EVT_RADIOBUTTON, self.on_radio_rel_btn)
        self.rad_relationships.Enable(False)
        # choices (NB can't use RadioBoxes and wallpaper in Windows)
        # choices line 1
        DIFF_LN_1 = 190
        self.rad_2groups = wx.RadioButton(self.panel, -1, _("2 groups"), 
                                          style=wx.RB_GROUP,
                                          pos=(BUTTON1_LEFT, DIFF_LN_1))
        self.rad_2groups.Bind(wx.EVT_RADIOBUTTON, self.on_radio2_groups_btn)
        self.rad_3groups = wx.RadioButton(self.panel, -1, _("3 or more"),
                                         pos=(BUTTON2_LEFT, DIFF_LN_1))
        self.rad_3groups.Bind(wx.EVT_RADIOBUTTON, self.on_radio3_groups_btn)
        self.rad_2groups.Enable(False)
        self.rad_3groups.Enable(False)
        self.btn_groups_help = wx.Button(self.panel, wx.ID_HELP, 
                                         pos=(HELP_LEFT, DIFF_LN_1-BUTTON_LIFT))
        self.btn_groups_help.Enable(False)
        self.btn_groups_help.Bind(wx.EVT_BUTTON, self.on_groups_help_btn)
        # divider
        wx.StaticLine(self.panel, pos=(BUTTON1_LEFT, DIFF_LN_1 + 30),
                      size=(DIV_LINE_WIDTH, 1))   
        # choices line 2
        DIFF_LN_2 = 235
        lbl_normal = _("Normal")
        lbl_not_normal = _("Not normal")
        self.rad_normal1 = wx.RadioButton(self.panel, -1, lbl_normal, 
                                         style=wx.RB_GROUP,
                                         pos=(BUTTON1_LEFT, DIFF_LN_2))
        self.rad_normal1.Bind(wx.EVT_RADIOBUTTON, self.on_radio_btn)
        self.rad_not_normal1 = wx.RadioButton(self.panel, -1, lbl_not_normal,
                                            pos=(BUTTON2_LEFT, DIFF_LN_2))
        self.rad_not_normal1.Bind(wx.EVT_RADIOBUTTON, self.on_radio_btn)
        self.rad_normal1.Enable(False)
        self.rad_not_normal1.Enable(False)
        self.btn_normal_help1 = wx.Button(self.panel, wx.ID_HELP,
                                       pos=(HELP_LEFT, DIFF_LN_2 - BUTTON_LIFT))
        self.btn_normal_help1.Bind(wx.EVT_BUTTON, self.on_normal_help1_btn)
        self.btn_normal_help1.Enable(False)
        # divider
        wx.StaticLine(self.panel, pos=(BUTTON1_LEFT, DIFF_LN_2 + 30),
                      size=(DIV_LINE_WIDTH, 1))
        # choices line 3
        DIFF_LN_3 = 280
        self.rad_indep = wx.RadioButton(self.panel, -1, _("Independent"), 
                                       style=wx.RB_GROUP,
                                       pos=(BUTTON1_LEFT, DIFF_LN_3))
        self.rad_indep.Bind(wx.EVT_RADIOBUTTON, self.on_radio_btn)
        self.rad_paired = wx.RadioButton(self.panel, -1, _("Paired"),
                                         pos=(BUTTON2_LEFT, DIFF_LN_3))
        self.rad_paired.Bind(wx.EVT_RADIOBUTTON, self.on_radio_btn)
        self.rad_indep.Enable(False)
        self.rad_paired.Enable(False)
        self.btn_indep_help = wx.Button(self.panel, wx.ID_HELP,
                                        pos=(HELP_LEFT, DIFF_LN_3 - BUTTON_LIFT))
        self.btn_indep_help.Bind(wx.EVT_BUTTON, self.on_indep_help_btn)
        self.btn_indep_help.Enable(False)
        # choices line 4
        DIFF_LN_4 = REL_TOP + 60
        self.rad_nominal = wx.RadioButton(self.panel, -1, _("Names Only"), 
                                          style=wx.RB_GROUP,
                                          pos=(BUTTON1_LEFT, DIFF_LN_4))
        self.rad_nominal.Bind(wx.EVT_RADIOBUTTON, self.on_radio_nominal_btn)
        self.rad_ordered = wx.RadioButton(self.panel, -1, _("Ordered"),
                                      pos=(BUTTON2_LEFT, DIFF_LN_4))
        self.rad_ordered.Bind(wx.EVT_RADIOBUTTON, self.on_radio_ordered_btn)
        self.rad_nominal.Enable(False)
        self.rad_ordered.Enable(False)
        self.btn_type_help = wx.Button(self.panel, wx.ID_HELP, 
                                       pos=(HELP_LEFT, DIFF_LN_4 - BUTTON_LIFT))
        self.btn_type_help.Bind(wx.EVT_BUTTON, self.on_type_help_btn)
        self.btn_type_help.Enable(False)
        # divider
        wx.StaticLine(self.panel, pos=(BUTTON1_LEFT, DIFF_LN_4 + 30),
                      size=(DIV_LINE_WIDTH, 1))   
        # choices line 4
        DIFF_LN_5 = REL_TOP + 105
        self.rad_normal2 = wx.RadioButton(self.panel, -1, lbl_normal, 
                                         style=wx.RB_GROUP,
                                         pos=(BUTTON1_LEFT, DIFF_LN_5))
        self.rad_normal2.Bind(wx.EVT_RADIOBUTTON, self.on_radio_btn)
        self.rad_not_normal2 = wx.RadioButton(self.panel, -1, lbl_not_normal,
                                            pos=(BUTTON2_LEFT, DIFF_LN_5))
        self.rad_not_normal2.Bind(wx.EVT_RADIOBUTTON, self.on_radio_btn)
        self.rad_normal2.Enable(False)
        self.rad_not_normal2.Enable(False)
        self.btn_normal_help2 = wx.Button(self.panel, wx.ID_HELP,
                                          pos=(HELP_LEFT, DIFF_LN_5))
        self.btn_normal_help2.Bind(wx.EVT_BUTTON, self.on_normal_help2_btn)
        self.btn_normal_help2.Enable(False)
        # listbox of tests
        LST_LEFT = 555
        LST_WIDTH = 200
        LST_TOP = 55
        LST_HEIGHT = 220
        SCROLL_ALLOWANCE = 20
        self.lst_tests = wx.ListCtrl(self.panel, -1, pos=(LST_LEFT, LST_TOP), 
                                size=(LST_WIDTH + SCROLL_ALLOWANCE, LST_HEIGHT),
                                style=wx.LC_REPORT)
        il = wx.ImageList(16, 16)
        self.idx_tick = 0
        self.idx_blank = 1
        tick = u"tickwin" if mg.PLATFORM == mg.WINDOWS else u"tick"
        for img in [tick, u"blank"]:
            bmp = wx.Bitmap(os.path.join(mg.SCRIPT_PATH, u"images", 
                                         u"%s.png" % img), wx.BITMAP_TYPE_PNG)
            il.Add(bmp)
        self.lst_tests.AssignImageList(il, wx.IMAGE_LIST_SMALL)
        self.lst_tests.InsertColumn(0, _("Statistical Test"))
        self.lst_tests.SetColumnWidth(0, LST_WIDTH - 25)
        self.lst_tests.InsertColumn(1, u"")
        self.lst_tests.SetColumnWidth(1, 25)
        for i, test in enumerate(STATS_TESTS):
            idx = self.lst_tests.InsertStringItem(i, test)
            self.lst_tests.SetStringItem(i, 1, u"", self.idx_blank)
        idx = self.lst_tests.InsertStringItem(i+1, u"")
        self.lst_tests.Select(0)
        self.lst_tests.Bind(wx.EVT_LIST_ITEM_ACTIVATED, 
                           self.on_list_item_selected)
        # run test button
        self.btn_config = wx.Button(self.panel, -1, 
                                    _("CONFIGURE TEST") + " >>>",
                                   pos=(CONFIG_LEFT, LST_TOP + LST_HEIGHT + 20))
        self.btn_config.Bind(wx.EVT_BUTTON, self.on_config_clicked)
        # close button
        self.btn_close = wx.Button(self.panel, wx.ID_CLOSE, pos=(675,500))
        self.btn_close.Bind(wx.EVT_BUTTON, self.on_close_click)
        
    def on_paint(self, event):
        """
        Cannot use static bitmaps and static text to replace.  In windows
            doesn't show background wallpaper.
        NB painting like this sets things behind the controls.
        """
        panel_dc = wx.PaintDC(self.panel)
        panel_dc.DrawBitmap(self.bmp_stats_select, 0, 0, True)
        panel_dc.SetTextForeground(TEXT_BROWN)
        panel_dc.SetFont(wx.Font(13, wx.SWISS, wx.NORMAL, wx.BOLD))
        panel_dc.DrawLabel(_("SELECT A STATISTICAL TEST HERE"), 
           wx.Rect(MAIN_LEFT, 53, 100, 100))
        panel_dc.DrawLabel(_("OR GET HELP CHOOSING BELOW"), 
           wx.Rect(MAIN_LEFT, 95, 100, 100))
        panel_dc.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        panel_dc.DrawLabel(_("Tests that show if there is a difference"), 
           wx.Rect(BUTTON1_LEFT, 135, 100, 100))
        panel_dc.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.NORMAL))
        panel_dc.DrawLabel(_("E.g. Do females have a larger vocabulary "
                           "average than males?"), 
           wx.Rect(BUTTON1_LEFT, 160, 100, 100))
        panel_dc.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        panel_dc.DrawLabel(_("Tests that show if there is a relationship"), 
           wx.Rect(BUTTON1_LEFT, REL_TOP, 100, 100))
        panel_dc.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.NORMAL))
        panel_dc.DrawLabel(_("E.g. Does wealth increase with age?"), 
           wx.Rect(BUTTON1_LEFT, REL_TOP + 27, 100, 100))
        event.Skip()
    
    def on_radio_direct_btn(self, event):        
        self.rad_differences.SetValue(True)
        self.rad_differences.Enable(False)
        self.diff_setup(enable=False)
        self.rad_relationships.Enable(False)
        self.rel_setup(enable=False)
        self.remove_test_indicators()
        
    def on_radio_assisted_btn(self, event):
        self.rad_differences.Enable(True)
        self.diff_setup(enable=True)
        self.rad_relationships.Enable(True)
        self.rel_setup(enable=False)
        # tick first test
        self.lst_tests.SetStringItem(0, 1, "", self.idx_tick)
        self.lst_tests.Select(0)
        self.respond_to_assisted_choices()
    
    def on_radio_diff_btn(self, event):
        self.diff_setup(enable=True)
        self.rel_setup(enable=False)
        self.respond_to_assisted_choices()
    
    def on_radio_rel_btn(self, event):
        self.rel_setup(enable=True)
        self.diff_setup(enable=False)
        self.respond_to_assisted_choices()
    
    def diff_setup(self, enable=True):
        "Enable options under Differences section"
        if not enable:
            # set left first
            try:
                self.rad_2groups.SetValue(True)
            except:
                pass
            try:
                self.rad_normal1.SetValue(True)
            except:
                pass
        self.rad_2groups.Enable(enable)
        self.rad_3groups.Enable(enable)
        self.btn_groups_help.Enable(enable)
        self.rad_normal1.Enable(enable)
        self.rad_not_normal1.Enable(enable)
        self.btn_normal_help1.Enable(enable)
        self.indep_setup(enable=enable)
    
    def on_radio2_groups_btn(self, event):
        self.indep_setup(enable=True)
        self.respond_to_assisted_choices()
    
    def on_radio3_groups_btn(self, event):
        self.indep_setup(enable=False)
        self.respond_to_assisted_choices()

    def on_groups_help_btn(self, event):
        wx.MessageBox(_("Are you looking at the difference between two "
          "groups or more?"
          "\n\nExample with 2 groups: average vocabulary of Males vs "
          "Females."
          "\n\nExample with 3 or more groups: average sales figures for "
          "the North, South, East, and West regions"))
    
    def examine_normality(self, paired=False):
        self.var_labels, self.var_notes, self.var_types, self.val_dics = \
                                    lib.get_var_dets(cc[mg.CURRENT_VDTS_PATH])
        dlg = normal.NormalityDlg(self, self.var_labels, self.var_notes, 
                                  self.var_types, self.val_dics, paired)
        dlg.ShowModal()
    
    def on_normal_help1_btn(self, event):
        paired = self.rad_paired.GetValue()
        self.examine_normality(paired)
        event.Skip()
    
    def indep_setup(self, enable=True):
        # set left first
        try:
            self.rad_indep.SetValue(True)
        except:
            pass
        self.rad_indep.Enable(enable)
        self.rad_paired.Enable(enable)
        self.btn_indep_help.Enable(enable)
        
    def on_indep_help_btn(self, event):
        wx.MessageBox(_("Is your data for each group recorded in different "
          "rows (independent) or together on same row (paired)?"
          "\n\nExample of Independent data: if looking at Male vs Female "
          "vocabulary we do not have both male and female scores in the "
          "same rows. Male and Female data is independent."
          "\n\nExample of Paired data: if looking at mental ability in the "
          "Morning vs the Evening we might have one row per person with "
          "both time periods in the same row. Morning and Evening data is "
          "paired."))
        
    def rel_setup(self, enable=True):
        "Enable options under Relationships section"
        if not enable:
            # set left first
            try:
                self.rad_nominal.SetValue(True)
            except:
                pass
        self.rad_nominal.Enable(enable)
        self.rad_ordered.Enable(enable)
        self.btn_type_help.Enable(enable)
        self.normal_rel_setup(enable=False) # only set to True when cat selected
    
    def on_radio_nominal_btn(self, event):
        self.normal_rel_setup(enable=False)
        self.respond_to_assisted_choices()
    
    def on_radio_ordered_btn(self, event):
        self.normal_rel_setup(enable=True)
        self.respond_to_assisted_choices()
    
    def on_type_help_btn(self, event):
        wx.MessageBox(_("Names only data (Nominal) is just labels or names. "
          "Ordered data has a sense of order and includes Ordinal (order "
          "but no amount) and Quantitative (actual numbers)."
          "\n\nExample of Names Only data: sports codes ('Soccer', "
          "'Badminton', 'Skiing' etc)"
          "\n\nExample of Ordered data: ratings of restaurant "
          "service standards (1 - Very Poor, 2 - Poor, 3 - Average etc)."))
    
    def on_normal_help2_btn(self, event):
        self.examine_normality()
        event.Skip()
    
    def normal_rel_setup(self, enable=True):
        # set left first
        try:
            self.rad_normal2.SetValue(True)
        except:
            pass
        self.rad_normal2.Enable(enable)
        self.rad_not_normal2.Enable(enable)
        self.btn_normal_help2.Enable(enable)
    
    def remove_test_indicators(self):
        for i, test in enumerate(STATS_TESTS):
            self.lst_tests.SetStringItem(i, 1, "", self.idx_blank)
            self.lst_tests.Select(i, on=0)
    
    def on_radio_btn(self, event):
        self.respond_to_assisted_choices()
    
    def respond_to_assisted_choices(self):
        test_type = self.select_test()
        if test_type:
            self.remove_test_indicators()
            self.indicate_test(test_type)
    
    def select_test(self):
        """
        Select which test meets the criteria selected.
        Returns test_type from STATS_TESTS.
        STATS_TESTS = [TEST_TTEST_INDEP, TEST_TTEST_PAIRED, TEST_ANOVA, 
            TEST_WILCOXON, TEST_MANN_WHITNEY, TEST_KRUSKAL_WALLIS, 
            TEST_CHI_SQUARE, TEST_SPEARMANS_R, TEST_PEARSONS_R
        """
        if self.rad_differences.GetValue():
            if self.rad_2groups.GetValue():
                if self.rad_normal1.GetValue():
                    if self.rad_indep.GetValue():
                        test_type = TEST_TTEST_INDEP
                    elif self.rad_paired.GetValue():
                        test_type = TEST_TTEST_PAIRED
                    else:
                        raise my_exceptions.InvalidTestSelectionException
                elif self.rad_not_normal1.GetValue():
                    if self.rad_indep.GetValue():
                        test_type = TEST_MANN_WHITNEY
                    elif self.rad_paired.GetValue():
                        test_type = TEST_WILCOXON
                    else:
                        raise my_exceptions.InvalidTestSelectionException
                else:
                    raise my_exceptions.InvalidTestSelectionException
            elif self.rad_3groups.GetValue():
                if self.rad_normal1.GetValue():
                    test_type = TEST_ANOVA
                else:
                    test_type = TEST_KRUSKAL_WALLIS
            else:
                raise my_exceptions.InvalidTestSelectionException
        elif self.rad_relationships.GetValue():
            if self.rad_nominal.GetValue():
                test_type = TEST_CHI_SQUARE
            elif self.rad_ordered.GetValue():
                if self.rad_normal2.GetValue():
                    test_type = TEST_PEARSONS_R
                elif self.rad_not_normal2.GetValue():
                    test_type = TEST_SPEARMANS_R
                else:
                    raise my_exceptions.InvalidTestSelectionException 
            else:
                raise my_exceptions.InvalidTestSelectionException
        else:
            test_type = None
        return test_type
    
    def indicate_test(self, test_const):
        "Select a test in the listbox with a tick and a selection."
        if test_const not in STATS_TESTS:
            raise Exception, (u"indicate_test was passed a test not from the "
                              u"standard list")
        idx=STATS_TESTS.index(test_const)
        self.lst_tests.SetStringItem(idx, 1, "", self.idx_tick)
        self.lst_tests.Select(idx)
    
    def on_list_item_selected(self, event):
        self.respond_to_selection(event)
    
    def on_config_clicked(self, event):
        self.respond_to_selection(event)
    
    def respond_to_selection(self, event):
        idx = self.lst_tests.GetFirstSelected()
        try:
            sel_test = STATS_TESTS[idx]
        except Exception:
            wx.MessageBox(_("Please select a statistical test on the list"))
            event.Skip()
            return
        try:
            if sel_test == TEST_TTEST_INDEP:
                import ttest_indep
                dlg = ttest_indep.DlgConfig(_("Configure Independent t-test"))
                dlg.ShowModal()        
            elif sel_test == TEST_TTEST_PAIRED:
                import ttest_paired
                dlg = ttest_paired.DlgConfig(
                                        _("Configure Paired Samples t-test"))
                dlg.ShowModal()
            elif sel_test == TEST_ANOVA:
                import anova
                dlg = anova.DlgConfig(_("Configure ANOVA test"), 
                                      takes_range=True)
                dlg.ShowModal()
            elif sel_test == TEST_WILCOXON:
                import wilcoxon
                dlg = wilcoxon.DlgConfig(
                                    _("Configure Wilcoxon Signed Ranks test"))
                dlg.ShowModal()
            elif sel_test == TEST_MANN_WHITNEY:
                import mann_whitney
                dlg = mann_whitney.DlgConfig(_("Configure Mann Whitney U test"))
                dlg.ShowModal()
            elif sel_test == TEST_KRUSKAL_WALLIS:
                import kruskal_wallis
                dlg = kruskal_wallis.DlgConfig(
                                        _("Configure Kruskal Wallis H test"), 
                                        takes_range=True)
                dlg.ShowModal()
            elif sel_test == TEST_CHI_SQUARE:
                import chisquare
                dlg = chisquare.DlgConfig(_("Configure Chi Square test"))
                dlg.ShowModal()
            elif sel_test == TEST_PEARSONS_R:
                import pearsonsr
                dlg = pearsonsr.DlgConfig(_("Configure Pearson's R test"))
                dlg.ShowModal()
            elif sel_test == TEST_SPEARMANS_R:
                import spearmansr
                dlg = spearmansr.DlgConfig(_("Configure Spearman's R test"))
                dlg.ShowModal()
            else:
                raise Exception, "Unknown test"
        except Exception, e:
            wx.MessageBox(_("Unable to connect to data as defined in " 
                "project %s.  Please check your settings." % self.proj_name))
            raise Exception, unicode(e)
        event.Skip()
    
    def on_close_click(self, event):
        self.Destroy()
       