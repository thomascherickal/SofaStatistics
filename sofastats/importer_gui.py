import wx #@UnusedImport

from sofastats import basic_lib as b  #@UnresolvedImport
from sofastats import my_globals as mg  #@UnresolvedImport
from sofastats import lib  #@UnresolvedImport
from sofastats import my_exceptions  #@UnresolvedImport
from sofastats import config_output  #@UnresolvedImport
from sofastats import getdata   #@UnresolvedImport # must be before anything referring to plugin modules
from sofastats.importing import importer  #@UnresolvedImport
from sofastats.dbe_plugins import dbe_sqlite  #@UnresolvedImport

FILE_CSV = 'csv'
FILE_EXCEL = 'excel'
FILE_ODS = 'ods'
FILE_UNKNOWN = 'unknown'
FIRST_MISMATCH_TPL = ('\nRow: %(row)s'
    '\nValue: "%(value)s"'
    '\nExpected column type: %(fldtype)s')
ROWS_TO_SHOW_USER = 5  ## only need enough to decide if a header (except for csv when also needing to choose encoding)

def run_gui_import(self):
    run_import(self)


class DlgImportFileSelect(wx.Dialog):
    def __init__(self, parent):
        """
        Make selection based on file extension and possibly inspection of sample
        of rows (e.g. csv dialect).
        """
        title = (_('Select file to import') + ' (csv/tsv/tab/xlsx/ods)')
        wx.Dialog.__init__(self, parent=parent, title=title, size=(550, 300),
            style=wx.CAPTION|wx.CLOSE_BOX|wx.SYSTEM_MENU,
            pos=(mg.HORIZ_OFFSET+100, -1))
        self.CentreOnScreen(wx.VERTICAL)
        self.parent = parent
        self.panel = wx.Panel(self)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.import_status = {mg.CANCEL_IMPORT: False}  ## can change and running script can check on it.
        self.file_type = FILE_UNKNOWN
        config_output.add_icon(frame=self)
        szr_main = wx.BoxSizer(wx.VERTICAL)
        ## file path
        lbl_fpath = wx.StaticText(self.panel, -1, _('Source File:'))
        lbl_fpath.SetFont(mg.LABEL_FONT)
        self.txt_file = wx.TextCtrl(self.panel, -1, '', size=(400,-1))
        self.txt_file.Bind(wx.EVT_CHAR, self.on_file_char)
        self.txt_file.SetFocus()
        btn_fpath = wx.Button(self.panel, -1, _('Browse ...'))
        btn_fpath.Bind(wx.EVT_BUTTON, self.on_btn_fpath)
        btn_fpath.SetDefault()
        btn_fpath.SetToolTip(_('Browse for file locally'))
        ## comment
        lbl_comment = wx.StaticText(self.panel, -1, 
            _('The Source File will be imported into SOFA with the SOFA Table '
              'Name entered below:'))
        ## internal SOFA name
        lbl_int_name = wx.StaticText(self.panel, -1, _('SOFA Table Name:'))
        lbl_int_name.SetFont(mg.LABEL_FONT)
        self.txt_int_name = wx.TextCtrl(self.panel, -1, '', size=(280, -1))
        self.txt_int_name.Bind(wx.EVT_CHAR, self.on_int_name_char)
        ## feedback
        self.lbl_feedback = wx.StaticText(self.panel)
        ## buttons
        btn_help = wx.Button(self.panel, wx.ID_HELP)
        btn_help.Bind(wx.EVT_BUTTON, self.on_btn_help)
        self.btn_cancel = wx.Button(self.panel, wx.ID_CANCEL)
        self.btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        self.btn_cancel.Enable(False)
        self.btn_close = wx.Button(self.panel, wx.ID_CLOSE)
        self.btn_close.Bind(wx.EVT_BUTTON, self.on_close)
        self.btn_import = wx.Button(self.panel, -1, _('IMPORT'))
        self.btn_import.Bind(wx.EVT_BUTTON, self.on_import)
        self.btn_import.Enable(False)
        ## progress
        self.progbar = wx.Gauge(self.panel, -1, mg.IMPORT_GAUGE_STEPS,
            size=(-1, 20), style=wx.GA_HORIZONTAL)
        ## sizers
        szr_fpath = wx.BoxSizer(wx.HORIZONTAL)
        szr_fpath.Add(btn_help, 0, wx.LEFT, 10)
        szr_fpath.Add(lbl_fpath, 0, wx.LEFT, 10)
        szr_fpath.Add(self.txt_file, 1, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szr_get_file = wx.FlexGridSizer(rows=1, cols=2, hgap=0, vgap=0)
        szr_get_file.AddGrowableCol(0,1)  ## idx, propn
        szr_get_file.Add(btn_fpath, 0, wx.ALIGN_RIGHT|wx.RIGHT, 10)
        szr_int_name = wx.FlexGridSizer(rows=1, cols=2, hgap=0, vgap=0)
        szr_int_name.AddGrowableCol(0,1)  ## idx, propn
        szr_int_name.Add(lbl_int_name, 0, wx.ALIGN_RIGHT|wx.RIGHT, 5)
        szr_int_name.Add(self.txt_int_name, 1, wx.ALIGN_RIGHT)
        szr_btns = wx.FlexGridSizer(rows=1, cols=2, hgap=5, vgap=5)
        szr_btns.AddGrowableCol(1,2)  ## idx, propn
        szr_btns.Add(self.btn_cancel, 0)
        szr_btns.Add(self.btn_import, 0, wx.ALIGN_RIGHT)
        szr_close = wx.FlexGridSizer(rows=1, cols=2, hgap=5, vgap=5)
        szr_close.AddGrowableCol(0,2)  ## idx, propn
        szr_close.Add(self.lbl_feedback)        
        szr_close.Add(self.btn_close, 0, wx.ALIGN_RIGHT)
        szr_main.Add(szr_fpath, 0, wx.GROW|wx.TOP, 20)
        szr_main.Add(szr_get_file, 0, wx.GROW|wx.TOP, 10)
        szr_main.Add(lbl_comment, 0, wx.GROW|wx.TOP|wx.LEFT|wx.RIGHT, 10)
        szr_main.Add(szr_int_name, 0, wx.GROW|wx.ALL, 10)
        szr_main.Add(szr_btns, 0, wx.GROW|wx.ALL, 10)
        szr_main.Add(self.progbar, 0, wx.GROW|wx.ALL, 10)
        szr_main.Add(szr_close, 0, wx.GROW|wx.ALL, 10)
        self.panel.SetSizer(szr_main)
        szr_main.SetSizeHints(self)
        self.Layout()

    def on_file_char(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_RETURN:
            self.txt_int_name.SetFocus()
            return
        ## NB callafter to allow data to updated in text ctrl
        wx.CallAfter(self.align_btns_to_completeness)
        event.Skip()

    def on_int_name_char(self, event):
        wx.CallAfter(self.align_btns_to_completeness)
        event.Skip()

    def on_btn_fpath(self, event):
        """
        Open dialog and take the file selected (if any).

        E.g. separate wildcard setting:
            "BMP files (*.bmp)|*.bmp|GIF files (*.gif)|*.gif"
        E.g. consolidated settings: "pictures (*.jpeg,*.png)|*.jpeg;*.png"
        """
        exts = [f'*{x}' for x in mg.IMPORT_EXTENTIONS.values()]
        exts.sort()
        wildcard_comma_bits = ','.join(exts)
        wildcard_semi_colon_bits = ';'.join(exts)
        wildcard = f'Data Files ({wildcard_comma_bits})|{wildcard_semi_colon_bits}'
        dlg_get_file = wx.FileDialog(self, wildcard=wildcard) #, message=..., wildcard=...
        ## defaultDir='spreadsheets', defaultFile='', )
        ## MUST have a parent to enforce modal in Windows
        if dlg_get_file.ShowModal() == wx.ID_OK:
            path = dlg_get_file.GetPath()
            self.txt_file.SetValue(path)
            filestart, unused = importer.get_file_start_ext(path)
            newname = importer.process_tblname(filestart)
            self.txt_int_name.SetValue(newname)
        dlg_get_file.Destroy()
        self.txt_int_name.SetFocus()
        self.align_btns_to_completeness()
        self.btn_import.SetDefault()
        event.Skip()

    def on_btn_help(self, event):
        import webbrowser
        url = 'http://www.sofastatistics.com/wiki/doku.php?id=help:importing'
        webbrowser.open_new_tab(url)
        event.Skip()

    def on_close(self, _event):
        self.Destroy()

    def on_cancel(self, _event):
        self.import_status[mg.CANCEL_IMPORT] = True

    def align_btns_to_completeness(self):
        debug = False
        filename = self.txt_file.GetValue()
        int_name = self.txt_int_name.GetValue()
        complete = (filename != '' and int_name != '')
        if debug:
            print(f'filename: "{filename}" int_name: "{int_name}" '
                f"complete: {complete}")
        self.btn_import.Enable(complete)

    def align_btns_to_importing(self, importing):
        self.btn_close.Enable(not importing)
        self.btn_cancel.Enable(importing)
        self.btn_import.Enable(not importing)

    def on_import(self, event):
        run_gui_import(self)
        event.Skip()


def check_tblname(fpath, tblname, headless):
    """
    Returns tblname (None if no suitable name to use).

    Checks table name and gives user option of correcting it if problems.

    Raises exception if no suitable name selected.
    """
    ## check existing names
    valid, err = dbe_sqlite.valid_tblname(tblname)
    if not valid:
        if headless:
            raise Exception('Faulty SOFA table name.')
        else:
            title = _('FAULTY SOFA TABLE NAME')
            msg = (_('You can only use letters, numbers and underscores in '
                'a SOFA Table Name. Use another name?\nOrig error: %s') % err)
            ret = wx.MessageBox(msg, title, wx.YES_NO|wx.ICON_QUESTION)
            if ret == wx.NO:
                raise Exception('Had a problem with faulty SOFA Table Name but '
                    'user cancelled initial process of resolving it')
            elif ret == wx.YES:
                return None
    duplicate = getdata.dup_tblname(tblname)
    if duplicate:
        if not headless:  ## assume OK to overwrite existing table name with
            ## fresh data if running headless
            title = _('SOFA NAME ALREADY EXISTS')
            msg = _("A table named \"%(tbl)s\" already exists in the SOFA "
                'default database.\n\nDo you want to replace it with the new '
                "data from \"%(fil)s\"?")
            ret = wx.MessageBox(msg % {'tbl': tblname, 'fil': fpath},
                title, wx.YES_NO|wx.ICON_QUESTION)
            if ret == wx.NO:  ## no overwrite so get new one (or else!)
                wx.MessageBox(
                    _('Please change the SOFA Table Name and try again'))
                return None
            elif ret == wx.YES:
                pass  ## use name (overwrite orig)
    return tblname

def run_import(self, force_quickcheck=False):
    """
    Identify type of file by extension and open dialog if needed
    to get any additional choices e.g. separator used in 'csv'.
    """
    headless = False
    headless_has_header = False
    supplied_encoding = None
    dd = mg.DATADETS_OBJ
    self.align_btns_to_importing(importing=True)
    self.progbar.SetValue(0)
    fpath = self.txt_file.GetValue()
    if not fpath:
        wx.MessageBox(_('Please select a file'))
        self.align_btns_to_importing(importing=False)
        self.txt_file.SetFocus()
        return
    ## identify file type
    unused, extension = importer.get_file_start_ext(fpath)
    ext = extension.lower()
    csv_formats = (
        mg.IMPORT_EXTENTIONS['csv'],
        mg.IMPORT_EXTENTIONS['tsv'],
        mg.IMPORT_EXTENTIONS['tab'],
    )
    if ext in csv_formats:
        self.file_type = FILE_CSV
    elif ext == mg.IMPORT_EXTENTIONS['txt']:
        ret = wx.MessageBox(_('SOFA imports txt files as csv or '
            'tab-delimited files.\n\nIs your txt file a valid csv or '
            'tab-delimited file?'), caption=_('CSV FILE?'), style=wx.YES_NO)
        if ret == wx.NO:
            wx.MessageBox(_('Unable to import txt files unless csv or '
                'tab-delimited format inside'))
            self.align_btns_to_importing(importing=False)
            return
        else:
            self.file_type = FILE_CSV
    elif ext == mg.IMPORT_EXTENTIONS['xlsx']:
        self.file_type = FILE_EXCEL
    elif ext == mg.IMPORT_EXTENTIONS['ods']:
        self.file_type = FILE_ODS
    else:
        extra_warning_dets = (
            '. Please convert to xlsx or another supported format first.'
            if ext == mg.IMPORT_EXTENTIONS['xls'] else '')
        unknown_msg = ((
            _("Files with the file name extension '%s' are not supported")
            % extension) + extra_warning_dets)
        self.file_type = FILE_UNKNOWN
        wx.MessageBox(unknown_msg)
        self.align_btns_to_importing(importing=False)
        return
    tblname = self.txt_int_name.GetValue()
    if not tblname:
        wx.MessageBox(_('Please select a SOFA Table Name for the file'))
        self.align_btns_to_importing(importing=False)
        self.txt_int_name.SetFocus()
        return
    if ' ' in tblname:
        empty_spaces_msg = _("SOFA Table Name can't have empty spaces")
        wx.MessageBox(empty_spaces_msg)
        self.align_btns_to_importing(importing=False)
        return
    bad_chars = ['-', ]
    for bad_char in bad_chars:
        if bad_char in tblname:
            bad_char_msg = (
                _("Do not include '%s' in SOFA Table Name") % bad_char)
            wx.MessageBox(bad_char_msg)
            self.align_btns_to_importing(importing=False)
            return
    if tblname[0] in [str(x) for x in range(10)]:
        digit_msg = _('SOFA Table Names cannot start with a digit')
        wx.MessageBox(digit_msg)
        self.align_btns_to_importing(importing=False)
        return
    try:
        final_tblname = check_tblname(fpath, tblname, headless)
        if final_tblname is None:
            self.txt_int_name.SetFocus()
            self.align_btns_to_importing(importing=False)
            self.progbar.SetValue(0)
            return
    except Exception:
        wx.MessageBox(
            _('Please select a suitable SOFA Table Name and try again'))
        self.align_btns_to_importing(importing=False)
        return
    ## import file
    if self.file_type == FILE_CSV:
        from sofastats.importing import csv_importer  #@UnresolvedImport
        file_importer = csv_importer.CsvImporter(self, fpath,
            final_tblname, supplied_encoding,
            headless=headless, headless_has_header=headless_has_header,
            force_quickcheck=force_quickcheck)
    elif self.file_type == FILE_EXCEL:
        from sofastats.importing import excel_importer  #@UnresolvedImport
        file_importer = excel_importer.ExcelImporter(self, fpath, final_tblname,
            headless=headless, headless_has_header=headless_has_header,
            force_quickcheck=force_quickcheck)
    elif self.file_type == FILE_ODS:
        from sofastats.importing import ods_importer  #@UnresolvedImport
        file_importer = ods_importer.OdsImporter(self, fpath, final_tblname,
            headless=headless, headless_has_header=headless_has_header,
            force_quickcheck=force_quickcheck)
    proceed = False
    try:
        proceed = file_importer.get_params()
    except Exception as e:
        wx.MessageBox(
            _('Unable to import data after getting parameters\n\nError')
            + f': {b.ue(e)}')
        lib.GuiLib.safe_end_cursor()
    if proceed:
        try:
            file_importer.import_content(
                self.lbl_feedback, self.import_status, self.progbar)
            dd.set_db(dd.db, tbl=tblname)
            lib.GuiLib.safe_end_cursor()
        except my_exceptions.ImportConfirmationRejected as e:
            lib.GuiLib.safe_end_cursor()
            wx.MessageBox(b.ue(e))
        except my_exceptions.ImportCancel as e:
            lib.GuiLib.safe_end_cursor()
            self.import_status[mg.CANCEL_IMPORT] = False  ## reinit
            wx.MessageBox(b.ue(e))
        except Exception as e:
            self.progbar.SetValue(0)
            lib.GuiLib.safe_end_cursor()
            wx.MessageBox(
                _('Unable to import data\n\nHelp available at %s\n\n')
                % mg.CONTACT + f'Error: {b.ue(e)}')
    self.align_btns_to_importing(importing=False)
