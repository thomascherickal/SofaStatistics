import os
import wx

import my_globals as mg
import lib
import my_exceptions
import config_dlg
import normal
import projects

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
DIFF_TOP = 125
REL_TOP = DIFF_TOP + 195
QUESTIONS_TOP = REL_TOP + 150
QUESTION_BTNS_TOP = QUESTIONS_TOP + 30
BUTTON1_LEFT = MAIN_LEFT + 20
BUTTON2_LEFT = MAIN_LEFT + 130
CONFIG_LEFT = 560
if mg.PLATFORM == mg.WINDOWS:
     CONFIG_LEFT += 10
BUTTON_LIFT = 0 if mg.PLATFORM == mg.WINDOWS else 4
DIV_LINE_WIDTH = 203
LST_LEFT = 485
LST_WIDTH = 200
LST_TOP = 55
LST_HEIGHT = 220
SCROLL_ALLOWANCE = 20

cc = config_dlg.get_cc()


class StatsSelectDlg(wx.Dialog):
    
    def __init__(self, proj_name, var_labels=None, var_notes=None, 
                 val_dics=None):
        width = 1000
        height = 600
        wx.Dialog.__init__(self, None, title=_("Select Statistical Test"), 
              size=(width,height),
              style=wx.CAPTION|wx.MINIMIZE_BOX|wx.SYSTEM_MENU,
              pos=(mg.HORIZ_OFFSET,0)) # -1 positions it too low on 768 v
        self.proj_name = proj_name
        # Windows doesn't include window decorations
        y_start = self.GetClientSize()[1] - self.GetSize()[1]
        self.SetClientSize(self.GetSize())
        self.panel = wx.Panel(self, size=(width,height)) # needed by Windows
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
        self.rad_direct.SetValue(True)
        self.rad_assisted = wx.RadioButton(self.panel, -1, 
                                          pos=(MAIN_LEFT - 25, 95))
        self.rad_assisted.Bind(wx.EVT_RADIOBUTTON, self.on_radio_assisted_btn)
        # main assisted options
        self.rad_differences = wx.RadioButton(self.panel, -1, 
                                             pos=(MAIN_LEFT, DIFF_TOP), 
                                             style=wx.RB_GROUP)
        self.rad_differences.Bind(wx.EVT_RADIOBUTTON, self.on_radio_diff_btn)
        self.rad_differences.Enable(False)
        self.rad_relationships = wx.RadioButton(self.panel, -1,
                                                pos=(MAIN_LEFT, REL_TOP))
        self.rad_relationships.Bind(wx.EVT_RADIOBUTTON, self.on_radio_rel_btn)
        self.rad_relationships.Enable(False)
        # choices (NB can't use RadioBoxes and wallpaper in Windows)
        # choices line 1
        DIFF_LN_1 = DIFF_TOP + 65
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
        DIFF_LN_2 = DIFF_LN_1 + 45
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
        DIFF_LN_3 = DIFF_LN_2 + 45
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
        # data exploration
        self.groups_label = _("Groups")
        btn_groups = wx.Button(self.panel, -1, self.groups_label,
                                  pos=(BUTTON1_LEFT, QUESTION_BTNS_TOP))
        btn_groups.SetToolTipString(_("Make report tables to see how many "
                                      "groups in data"))
        btn_groups.Bind(wx.EVT_BUTTON, self.on_groups_btn)
        self.normality_label = _("Normality")
        self.normality_msg = _("Use the \"%s\" button at the bottom to assess "
                "the normality of your numerical data") % self.normality_label
        btn_normality = wx.Button(self.panel, -1, self.normality_label,
                                  pos=(BUTTON2_LEFT, QUESTION_BTNS_TOP))
        btn_normality.SetToolTipString(_("Assess the normality of your "
                                         "numerical data"))
        btn_normality.Bind(wx.EVT_BUTTON, self.on_normality_btn)
        self.data_type_label = _("Data Type")
        btn_type = wx.Button(self.panel, -1, self.data_type_label,
                                  pos=(HELP_LEFT, QUESTION_BTNS_TOP))
        btn_type.SetToolTipString(_("Assess data type e.g. categorical, "
                                    "ordered etc"))
        btn_type.Bind(wx.EVT_BUTTON, self.on_type_btn)
        # listbox of tests
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
        self.lst_tests.Bind(wx.EVT_LIST_ITEM_SELECTED, 
                           self.on_list_item_selected)
        self.lst_tests.Bind(wx.EVT_LIST_ITEM_ACTIVATED, 
                           self.on_list_item_activated)
        # tips etc
        self.lbl_tips = wx.StaticText(self.panel, -1,
                                      pos=(LST_LEFT, LST_TOP + LST_HEIGHT + 40))
        self.lbl_tips.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.NORMAL))
        self.lbl_tips.SetForegroundColour(TEXT_BROWN)
        # run test button
        self.btn_config = wx.Button(self.panel, -1, _("CONFIGURE TEST"),
             pos=(CONFIG_LEFT + LST_WIDTH + 55, LST_TOP))
        self.btn_config.Bind(wx.EVT_BUTTON, self.on_config_clicked)
        # close button
        self.btn_close = wx.Button(self.panel, wx.ID_CLOSE, pos=(900,558))
        self.btn_close.Bind(wx.EVT_BUTTON, self.on_close_click)
        self.update_test_tips(STATS_TESTS[0], assisted=False)
        self.lst_tests.SetFocus()
        
    def on_paint(self, event):
        """
        Cannot use static bitmaps and static text to replace.  In windows
            doesn't show background wallpaper.
        NB painting like this sets things behind the controls.
        """
        panel_dc = wx.PaintDC(self.panel)
        panel_dc.DrawBitmap(self.bmp_stats_select, 0, 0, True)
        panel_dc.SetTextForeground(TEXT_BROWN)
        test_sel_txt = _("SELECT A STATISTICAL TEST HERE")
        test_sel_max_width = 350
        test_sel_font_sz = 16 if mg.PLATFORM == mg.MAC else 13
        test_sel_fs = lib.get_font_size_to_fit(text=test_sel_txt, 
                                               max_width=test_sel_max_width, 
                                               font_sz=test_sel_font_sz,
                                               min_font_sz=10)
        panel_dc.SetFont(wx.Font(test_sel_fs, wx.SWISS, wx.NORMAL, wx.BOLD))
        panel_dc.DrawLabel(test_sel_txt, wx.Rect(MAIN_LEFT, 53, 100, 100))
        get_help_txt = _("OR GET HELP CHOOSING BELOW")
        get_help_max_width = 350
        get_help_font_sz = 16 if mg.PLATFORM == mg.MAC else 13
        get_help_fs = lib.get_font_size_to_fit(text=get_help_txt, 
                                               max_width=get_help_max_width, 
                                               font_sz=get_help_font_sz,
                                               min_font_sz=11)
        panel_dc.SetFont(wx.Font(get_help_fs, wx.SWISS, wx.NORMAL, wx.BOLD))
        panel_dc.DrawLabel(get_help_txt, wx.Rect(MAIN_LEFT, 95, 100, 100))
        panel_dc.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        panel_dc.DrawLabel(_("Tests that show if there is a difference"), 
           wx.Rect(BUTTON1_LEFT, DIFF_TOP, 100, 100))
        panel_dc.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.NORMAL))
        diff_txt = lib.get_text_to_draw(_("E.g. Do females have a larger "
                           "vocabulary average than males?"), 300)
        panel_dc.DrawLabel(diff_txt, 
           wx.Rect(BUTTON1_LEFT, DIFF_TOP + 20, 100, 100))
        panel_dc.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        panel_dc.DrawLabel(_("Tests that show if there is a relationship"), 
           wx.Rect(BUTTON1_LEFT, REL_TOP, 100, 100))
        panel_dc.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.NORMAL))
        panel_dc.DrawLabel(_("E.g. Does wealth increase with age?"), 
           wx.Rect(BUTTON1_LEFT, REL_TOP + 27, 100, 100))
        panel_dc.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        panel_dc.DrawLabel(_("Answering questions about your data"), 
           wx.Rect(BUTTON1_LEFT, REL_TOP + 150, 100, 100))
        panel_dc.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        panel_dc.DrawLabel(_("Tips"), 
           wx.Rect(LST_LEFT, LST_TOP + LST_HEIGHT + 20, 100, 100))
        event.Skip()
    
    def on_radio_direct_btn(self, event):        
        self.rad_differences.SetValue(True)
        self.rad_differences.Enable(False)
        self.diff_setup(enable=False)
        self.rad_relationships.Enable(False)
        self.rel_setup(enable=False)
        self.remove_test_indicators()
        self.update_test_tips(None)
        
    def on_radio_assisted_btn(self, event):
        self.rad_differences.Enable(True)
        self.rad_differences.SetValue(True)
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
              "the North, South, East, and West regions"
              "\n\nYou can look at how many groups your data has by clicking "
              "on the \"%s\" button down the bottom and running a Frequency "
              "Table") % self.groups_label)
    
    def examine_normality(self):
        self.var_labels, self.var_notes, self.var_types, self.val_dics = \
                                    lib.get_var_dets(cc[mg.CURRENT_VDTS_PATH])
        dlg = normal.NormalityDlg(self, self.var_labels, self.var_notes, 
                                  self.var_types, self.val_dics)
        dlg.ShowModal()
    
    def on_normal_help1_btn(self, event):
        wx.MessageBox(self.normality_msg)
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
        wx.MessageBox(self.normality_msg)
        event.Skip()

    def on_groups_btn(self, event):
        wx.BeginBusyCursor()
        import report_table
        try:
            dlg = report_table.DlgMakeTable()
            lib.safe_end_cursor()
            dlg.ShowModal()
        except Exception, e:
            msg = _("Unable to open report table")
            wx.MessageBox(msg)
            raise Exception(u"%s.\nCaused by error: %s" % (msg, lib.ue(e)))
        finally:
            lib.safe_end_cursor()
            event.Skip()

    def on_normality_btn(self, event):
        self.examine_normality()
        event.Skip()
    
    def on_type_btn(self, event):
        updated = set() # will get populated with a True to indicate update
        self.var_labels, self.var_notes, self.var_types, self.val_dics = \
                                    lib.get_var_dets(cc[mg.CURRENT_VDTS_PATH])
        dlg = projects.ListVarsDlg(self.var_labels, self.var_notes, 
                                   self.var_types, self.val_dics, updated)
        dlg.ShowModal()
    
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
            self.update_test_tips(test_type, assisted=True)
        self.lst_tests.SetFocus()
    
    def update_test_tips(self, test_type, assisted=True):
        tips_width = 390
        if test_type == TEST_ANOVA:
            if assisted:
                tips = lib.get_text_to_draw(_("The ANOVA (Analysis Of Variance)"
                    " is probably a good choice."), tips_width)
            else:
                tips = lib.get_text_to_draw(_("The ANOVA (Analysis Of Variance)"
                    " is good for seeing if there is a difference in means "
                    "between multiple groups when the data is numerical and "
                    "adequately normal. Generally the ANOVA is robust to "
                    "non-normality."), tips_width)
                tips += u"\n\n"
                tips += lib.get_text_to_draw(_("You can evaluate normality by "
                    "clicking on the \"%s\" button down the bottom left.") % 
                    self.normality_label, tips_width)
        elif test_type == TEST_CHI_SQUARE:
            tips = _("")
        elif test_type == TEST_PEARSONS_R:
            tips = _("")
        elif test_type == TEST_SPEARMANS_R:
            tips = _("")
        elif test_type == TEST_KRUSKAL_WALLIS:
            tips = _("")
        elif test_type == TEST_MANN_WHITNEY:
            if assisted:
                tips = lib.get_text_to_draw(_("The Mann-Whitney is probably a "
                    "good choice.  The Independent t-test may still be "
                    "preferable if your data is numerical and doesn't violate "
                    "normality too much.  Generally the t-test is robust"
                    " to non-normality."),
                    tips_width)
                tips += u"\n\n"
                tips += lib.get_text_to_draw(_("You can evaluate normality by "
                    "clicking on the \"%s\" button down the bottom left.") % 
                    self.normality_label, tips_width)
            else:
                tips = lib.get_text_to_draw(_("The Mann-Whitney is good for "
                    "seeing if there is a difference between two groups when "
                    "the data is at least ordinal (ordered)."), tips_width)
                tips += u"\n\n" 
                tips += lib.get_text_to_draw(_("The Independent t-test may be "
                    "preferable if your data is numerical and doesn't violate "
                    "normality too much.  Generally the t-test is robust"
                    " to non-normality."),
                    tips_width)
        elif test_type == TEST_TTEST_INDEP:
            if assisted:
                tips = lib.get_text_to_draw(_("The Independent t-test is "
                    "probably a good choice.  The Mann-Whitney may still be "
                    "preferable in some cases because of its resistance"
                    " to extreme outliers (isolated high or low values)."), 
                    tips_width)
                tips += u"\n\n"
                tips += lib.get_text_to_draw(_("The Mann-Whitney also copes "
                    "better with small sample sizes e.g. < 20."), tips_width)
                tips += u"\n\n"
                tips += lib.get_text_to_draw(_("You can evaluate normality by "
                    "clicking on the \"%s\" button down the bottom left.")
                    % self.normality_label, tips_width)
            else:
                tips = lib.get_text_to_draw(_("The Independent t-test is good "
                    "for seeing if there is a difference between two groups "
                    "when the data is numerical and adequately normal.  "
                    "Generally the t-test is robust to non-normality."), 
                    tips_width)
                tips += u"\n\n" 
                tips += lib.get_text_to_draw(_("The Mann-Whitney may be "
                    "preferable in some cases because of its resistance"
                    " to extreme outliers (isolated high or low values)."), 
                    tips_width)
                tips += u"\n\n"
                tips += lib.get_text_to_draw(_("It also copes better with small "
                    "sample sizes e.g. < 20."), tips_width)
        elif test_type == TEST_TTEST_PAIRED:
            tips = _("")
        elif test_type == TEST_WILCOXON:
            tips = _("")
        else:
            tips = _("")
        self.lbl_tips.SetLabel(tips)
    
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
            raise Exception(u"indicate_test was passed a test not from the "
                            u"standard list")
        idx = STATS_TESTS.index(test_const)
        self.lst_tests.SetStringItem(idx, 1, "", self.idx_tick)
        self.lst_tests.Select(idx)
    
    def on_list_item_selected(self, event):
        self.respond_to_selection(event)

    def respond_to_selection(self, event):
        idx = self.lst_tests.GetFirstSelected()
        try:
            test_type = STATS_TESTS[idx]
        except Exception:
            event.Skip()
            return
        self.update_test_tips(test_type, assisted=False)

    def on_list_item_activated(self, event):
        self.respond_to_activation(event)

    def on_config_clicked(self, event):
        self.respond_to_activation(event)
    
    def respond_to_activation(self, event):
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
                raise Exception(u"Unknown test")
        except Exception, e:
            wx.MessageBox(_("Unable to connect to data as defined in "
                   "project %s.  Please check your settings.") % self.proj_name)
            raise
        event.Skip()
    
    def on_close_click(self, event):
        self.Destroy()
       