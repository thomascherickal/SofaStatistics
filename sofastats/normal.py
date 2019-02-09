import pylab
from textwrap import dedent
import wx  #@UnusedImport
import wx.html2

from sofastats import basic_lib as b
from sofastats import my_globals as mg
from sofastats import lib
from sofastats import my_exceptions
from sofastats import config_output
from sofastats import config_ui
from sofastats import getdata
from sofastats import output
from sofastats import projects
from sofastats.charting import charting_pylab
from sofastats.stats import core_stats

def get_inputs(paired, var_a, var_label_a, var_b, var_label_b):
    """
    Get variable label and a list of the non-null values (with any additional
    filtering applied).

    NB For a paired sample, the 'variable' is the difference between two
    selected variables.
    """
    dd = mg.DATADETS_OBJ
    unused, tbl_filt = lib.FiltLib.get_tbl_filt(dd.dbe, dd.db, dd.tbl)
    unused, and_filt = lib.FiltLib.get_tbl_filts(tbl_filt)
    objqtr = getdata.get_obj_quoter_func(dd.dbe)
    tblname = getdata.tblname_qtr(dd.dbe, dd.tbl)
    var_a = objqtr(var_a)
    if not paired:
        s = dedent(f"""SELECT {var_a}
            FROM {tblname}
            WHERE {var_a} IS NOT NULL
            {and_filt}
            ORDER BY {var_a} """)
    else:
        var_b = objqtr(var_b)
        s = dedent(f"""SELECT {var_b} - {var_a}
            FROM {tblname}
            WHERE {var_a} IS NOT NULL AND {var_b} IS NOT NULL
            {and_filt} """)
    dd.cur.execute(s)
    vals = [x[0] for x in dd.cur.fetchall()]
    if len(set(vals)) < 2:
        raise my_exceptions.TooFewValsForDisplay
    if not paired:
        data_label = var_label_a
    else:
        data_label = (_('Difference between %(a)s and %(b)s')
            % {'a': var_label_a, 'b': var_label_b})
    return data_label, vals

def get_normal_output(vals, data_label,
        add_to_report, report_name,
        paired, css_fil):
    html = []
    ## normality test (includes both kurtosis and skew)
    n_vals = len(vals)
    USUAL_FAIL_N = 100
    if n_vals < 20:
        msg = _('Need at least 20 values to test normality. Rely entirely '
            'on visual inspection of graph above.')
    else:
        try:
            (unused, p_arr, cskew,
             unused, ckurtosis, unused) = core_stats.normaltest(vals)
            p = p_arr[0]
            if abs(cskew) <= 1:
                sindic = 'a great sign'
            elif abs(cskew) <= 2:
                sindic = 'a good sign'
            else:
                sindic = 'not a good sign'
            skew_msg = (_(
                'Skew (lopsidedness) is %(skew)s which is probably %(indic)s.')
                % {'skew': round(cskew, 3), 'indic': sindic})
            if abs(ckurtosis) <= 1:
                kindic = 'a great sign'
            elif abs(ckurtosis) <= 2:
                kindic = 'a good sign'
            else:
                kindic = 'not a good sign'
            kurtosis_msg = (
                _('Kurtosis (peakedness or flatness) is %(kurt)s which is '
                  'probably %(indic)s.')
                % {'kurt': round(ckurtosis, 3), 'indic': kindic})
            if n_vals > USUAL_FAIL_N:
                msg = (_('Rely on visual inspection of graph. Although the data'
                    ' failed the ideal normality test, most real-world data-'
                    'sets with as many results (%s) would fail for even slight '
                    'differences from the perfect normal curve.') % n_vals + ' '
                    + skew_msg + ' ' + kurtosis_msg)
            else:
                if p < 0.05:
                    msg = (_('The distribution of %s passed one test for '
                        'normality. Confirm or reject based on visual '
                        'inspection of graph.') % data_label
                        + ' ' + skew_msg + u' ' + kurtosis_msg)
                else:
                    msg = (_('Although the distribution of %s is not perfectly '
                        "'normal', it may still be 'normal' enough for use. "
                        'View graph to decide.') % data_label + ' ' + skew_msg
                        + ' ' + kurtosis_msg)
        except Exception:
            msg = _('Unable to calculate normality tests')
    html.append(f'<p>{msg}</p>')
    ## histogram
    charting_pylab.gen_config()
    fig = pylab.figure()
    fig.set_size_inches((8.0, 4.5))  ## see dpi to get image size in pixels
    css_dojo_dic = lib.OutputLib.extract_dojo_style(css_fil)
    item_colours = output.colour_mappings_to_item_colours(
        css_dojo_dic['colour_mappings'])
    line_colour = css_dojo_dic['major_gridline_colour']
    histlbl = 'Histogram of differences' if paired else None
    try:
        charting_pylab.config_hist(fig, vals, data_label, histlbl,
            inner_bg=css_dojo_dic['plot_bg'],
            bar_colour=item_colours[0], line_colour=line_colour,
            thumbnail=False, inc_attrib=True)
    except Exception as e:
        raise my_exceptions.OutputException(
            f'Unable to produce histogram. Reason: {b.ue(e)}')
    output.ensure_imgs_path(
        report_path=mg.INT_IMG_PREFIX_PATH, ext=mg.RPT_SUBFOLDER_SUFFIX)
    img_src = charting_pylab.save_report_img(
        add_to_report, report_name, save_func=pylab.savefig, dpi=100)
    html.append(f'\n{mg.IMG_SRC_START}{img_src}{mg.IMG_SRC_END}')
    output.append_divider(
        html, title='Histogram', indiv_title='Normality check histogram')
    normal_output = '\n'.join(html)
    return normal_output


class DlgNormality(wx.Dialog, config_ui.ConfigUI):

    def __init__(self, parent, var_labels, var_notes, var_types, val_dics):
        self.title = _('Normal Data?')
        wx.Dialog.__init__(self, parent=parent, title=self.title,
            size=(1024,600),
            style=wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX|wx.RESIZE_BORDER|wx.CLOSE_BOX
            |wx.SYSTEM_MENU|wx.CAPTION|wx.CLIP_CHILDREN)
        config_ui.ConfigUI.__init__(self, autoupdate=True)
        self.output_modules = [
            (None, 'my_globals as mg'),
            (None, 'output'),
            (None, 'getdata'),
            (None, 'normal')]
        self.exiting = False
        self.SetFont(mg.GEN_FONT)
        self.Bind(wx.EVT_CLOSE, self.on_ok)
        self.url_load = True  ## btn_expand
        ## The following properties all required to utilise get_szr_data
        self.var_labels = var_labels
        self.var_notes = var_notes
        self.var_types = var_types
        self.val_dics = val_dics
        self.paired = False
        self.varbox_label_unpaired = _('Variable to Check')
        self.varbox_label_paired = _('Paired Variables to Check')
        self.desc_label_unpaired = _('Select the variable you are interested '
            'in. Is its distribution close enough to the normal curve for use '
            'with tests requiring that?\n\nLook for gross outliers, extreme '
            'skewing, and clustering into groups.')
        self.desc_label_paired = _('Select the paired variables you are '
            'interested in. Looking at the differences, is the distribution '
            'close enough to the normal curve for use with tests requiring '
            'that?\n\nNote: if comparing samples, each sample must be normal '
            'enough. Filter for each sample by right clicking on the table '
            'selector.')
        paired_choices = [_('Single'), _('Paired')]
        self.panel = wx.Panel(self)
        ## szrs
        szr_main = wx.BoxSizer(wx.VERTICAL)
        bxDesc = wx.StaticBox(self.panel, -1, _('Purpose'))
        self.szr_desc = wx.StaticBoxSizer(bxDesc, wx.VERTICAL)
        ## 4 key settings
        self.drop_tbls_panel = self.panel
        self.drop_tbls_system_font_size = False
        self.drop_tbls_sel_evt = self.on_table_sel
        hide_db = projects.get_hide_db()
        self.drop_tbls_idx_in_szr = 3 if not hide_db else 1  ## the 2 database items are missing)
        self.drop_tbls_rmargin = 10
        self.drop_tbls_can_grow = False
        self.szr_data = self.get_szr_data(self.panel, hide_db=hide_db)  ## mixin
        self.drop_tbls_szr = self.szr_data
        getdata.data_dropdown_settings_correct(parent=self)
        self.bx_vars = wx.StaticBox(self.panel, -1, self.varbox_label_unpaired)
        szr_vars = wx.StaticBoxSizer(self.bx_vars, wx.HORIZONTAL)
        ## assembly
        self.lbl_desc = wx.StaticText(self.panel, -1, self.desc_label_unpaired)
        self.szr_desc.Add(self.lbl_desc, 0, wx.ALL, 10)
        self.rad_paired = wx.RadioBox(self.panel, -1, '',
            choices=paired_choices, size=(-1,45), style=wx.RA_SPECIFY_COLS)
        self.rad_paired.SetStringSelection(_('Single'))
        self.rad_paired.Bind(wx.EVT_RADIOBOX, self.on_rad_paired)
        szr_vars.Add(self.rad_paired, 0)
        self.drop_var_a = wx.Choice(self.panel, -1, size=(300, -1))
        self.drop_var_a.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_var_a)
        self.drop_var_a.SetToolTip(
            _('Right click variable to view/edit details'))
        self.drop_var_b = wx.Choice(self.panel, -1, size=(300, -1))
        self.drop_var_b.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_var_b)
        self.drop_var_b.SetToolTip(
            _('Right click variable to view/edit details'))
        self.drop_var_b.Enable(False)
        self.setup_vars(var_a=True, var_b=False)
        szr_vars.Add(self.drop_var_a, 0, wx.ALIGN_BOTTOM|wx.LEFT, 10)
        szr_vars.Add(self.drop_var_b, 0, wx.ALIGN_BOTTOM|wx.LEFT, 10)
        myheight = 100 if mg.MAX_HEIGHT < 800 else 200
        self.szr_output_config = self.get_szr_output_config(self.panel)  ## mixin
        self.szr_output_display = self.get_szr_output_display(
            self.panel, inc_clear=False, idx_style=1)  ## mixin
        self.html = wx.html2.WebView.New(
            self.panel, -1, size=wx.Size(200, myheight))
        if mg.PLATFORM == mg.MAC:
            self.html.Bind(wx.EVT_WINDOW_CREATE, self.on_show)
        else:
            self.Bind(wx.EVT_SHOW, self.on_show)
        szr_lower = wx.BoxSizer(wx.HORIZONTAL)
        szr_lower.Add(self.html, 1, wx.GROW)
        szr_lower.Add(self.szr_output_display, 0, wx.GROW|wx.LEFT, 10)
        szr_main.Add(self.szr_desc, 0, wx.ALL, 10)
        szr_main.Add(self.szr_data, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szr_main.Add(szr_vars, 0, wx.ALL, 10)
        szr_main.Add(self.szr_output_config, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szr_main.Add(szr_lower, 1, wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        #szr_std_btns.Insert(0, self.szr_level, wx.ALIGN_LEFT|wx.ALL, 10)
        self.panel.SetSizer(szr_main)
        self.szr_lst = [self.szr_desc, self.szr_data, szr_vars,
            self.szr_output_config, szr_lower]
        lib.GuiLib.set_size(window=self, szr_lst=self.szr_lst, width_init=1024)

    def on_show(self, _event):
        if self.exiting:
            return
        self.set_output_to_blank()

    def test_config_ok(self):
        if self.paired:
            var_a = self.drop_var_a.GetStringSelection()
            var_b = self.drop_var_b.GetStringSelection()
            if (var_a == var_b):
                wx.MessageBox(_('The two variables must be different'))
                return False
        return True

    def on_btn_run(self, event):
        ## get settings
        cc = output.get_cc()
        run_ok = self.test_config_ok()
        if run_ok:
            ## set vals and data_label
            try:
                self.var_a, unused = self.get_var_a()
            except Exception as e:
                wx.MessageBox(
                    f'Unable to process first variable. Orig error: {e}')
                return
            self.var_label_a = lib.GuiLib.get_item_label(
                item_labels=self.var_labels, item_val=self.var_a)
            if self.paired:
                self.var_b, unused = self.get_var_b()
                self.var_label_b = lib.GuiLib.get_item_label(
                    item_labels=self.var_labels, item_val=self.var_b)
            else:
                self.var_b = None
                self.var_label_b = ''
            ## css_idx is supplied at the time
            get_script_args={
                'css_fil': str(cc[mg.CURRENT_CSS_PATH]),
                'report_name': str(cc[mg.CURRENT_REPORT_PATH]), }
            config_ui.ConfigUI.on_btn_run(self,
                event, get_script_args, new_has_dojo=True)

    def get_script(self, css_idx, css_fil, report_name):
        """
        Build script from inputs

        css_idx needed because of standard interface.
        """
        dd = mg.DATADETS_OBJ
        script_lst = []
        script_lst.append(lib.FiltLib.get_tbl_filt_clause(dd.dbe, dd.db,
            dd.tbl))
        add2report = 'True' if mg.ADD2RPT else 'False'
        script_lst.append(f'add_to_report = {add2report}')
        escaped_report_name = lib.escape_pre_write(report_name)
        script_lst.append(f'report_name = "{escaped_report_name}"')
        paired = 'True' if self.paired else 'False'
        var_b = '"%s"' % self.var_b if self.var_b else "None"
        script_lst.append(f"""\
data_label, vals = normal.get_inputs(
    paired={paired},
    var_a="{self.var_a}", var_label_a="{self.var_label_a}",
    var_b={var_b}, var_label_b="{self.var_label_b}")""")
        escaped_css_fil = lib.escape_pre_write(css_fil)
        script_lst.append(f"""\
normal_output = normal.get_normal_output(
    vals, data_label, add_to_report,
    report_name, paired={paired},
    css_fil="{escaped_css_fil}")""")
        script_lst.append('fil.write(normal_output)')
        return '\n'.join(script_lst)

    def set_size(self):
        horiz_padding = 15 if mg.PLATFORM == mg.MAC else 10
        lib.GuiLib.set_size(window=self, szr_lst=self.szr_lst,
            height_init=560, horiz_padding=horiz_padding)

    def on_rad_paired(self, _event):
        "Respond to selection of single/paired"
        self.paired = (self.rad_paired.GetSelection() == 1)
        if self.paired:
            self.bx_vars.SetLabel(self.varbox_label_paired)
            self.lbl_desc.SetLabel(self.desc_label_paired)
        else:
            self.bx_vars.SetLabel(self.varbox_label_unpaired)
            self.lbl_desc.SetLabel(self.desc_label_unpaired)
        self.drop_var_b.Enable(self.paired)
        self.setup_vars(var_a=True, var_b=self.paired)
        self.set_output_to_blank()
        self.set_size()

    def set_output_to_blank(self):
        if self.paired:
            msg = _('Select two variables and click Check button to see results'
                ' of normality test')
        else:
            msg = _('Select a variable and click Check button to see results of'
                ' normality test')
        self.html.SetPage(f'<p>{msg}</p>', mg.BASE_URL)

    def on_ok(self, event):
        self.exiting = True
        self.Destroy()
        event.Skip()

    def on_database_sel(self, event):
        if config_ui.ConfigUI.on_database_sel(self, event):
            self.setup_vars(var_a=True, var_b=self.paired)
            self.set_output_to_blank()

    def on_table_sel(self, event):
        config_ui.ConfigUI.on_table_sel(self, event)
        self.setup_vars(var_a=True, var_b=self.paired)
        self.set_output_to_blank()

    def on_rclick_tables(self, event):
        config_ui.ConfigUI.on_rclick_tables(self, event)
        #event.Skip() - don't use or will appear twice in Windows!

    def setup_var_a(self, var=None):
        self.setup_vars(var_a=True, var_b=False, var=var)

    def setup_var_b(self, var=None):
        self.setup_vars(var_a=False, var_b=True, var=var)

    def setup_vars(self, var_a=True, var_b=True, var=None):
        var_names = projects.get_approp_var_names(self.var_types,
            min_data_type=mg.VAR_TYPE_QUANT_KEY)
        var_choices, self.sorted_var_names = lib.GuiLib.get_sorted_choice_items(
            dic_labels=self.var_labels, vals=var_names)
        if var_a:
            self.drop_var_a.SetItems(var_choices)
            idx_a = self.sorted_var_names.index(var) if var else 0
            self.drop_var_a.SetSelection(idx_a)
        if var_b:
            self.drop_var_b.SetItems(var_choices)
            idx_b = self.sorted_var_names.index(var) if var else 0
            self.drop_var_b.SetSelection(idx_b)

    def refresh_vars(self):
        output.update_var_dets(dlg=self)

    def _get_var(self, drop):
        idx = drop.GetSelection()
        if idx == -1:
            raise Exception('No items in variable')
        try:
            var = self.sorted_var_names[idx]
        except IndexError as e:
            raise Exception(f'Problem getting var from {self.sorted_var_names} '
                f'with given index ({idx}). Orig error: {e}')
        var_item = drop.GetStringSelection()
        return var, var_item        

    def get_var_a(self):
        return self._get_var(self.drop_var_a)

    def get_var_b(self):
        return self._get_var(self.drop_var_b)

    def on_rclick_var_a(self, _event):
        try:
            var_a, choice_item = self.get_var_a()
        except Exception:
            wx.MessageBox('Unable to edit selection - nothing selected')
            return
        var_label_a = lib.GuiLib.get_item_label(
            item_labels=self.var_labels, item_val=var_a)
        updated = config_output.set_var_props(choice_item, var_a, var_label_a,
            self.var_labels, self.var_notes, self.var_types, self.val_dics)
        if updated:
            self.setup_var_a(var_a)

    def on_rclick_var_b(self, _event):
        try:
            var_b, choice_item = self.get_var_b()
        except Exception:
            wx.MessageBox('Unable to edit selection - nothing selected')
            return
        var_label_b = lib.GuiLib.get_item_label(
            item_labels=self.var_labels, item_val=var_b)
        updated = config_output.set_var_props(choice_item, var_b, var_label_b,
            self.var_labels, self.var_notes, self.var_types, self.val_dics)
        if updated:
            self.setup_var_b(var_b)
