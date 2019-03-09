import csv
import locale
import os
import wx #@UnusedImport
import wx.html2

from .. import basic_lib as b #@UnresolvedImport
from .. import my_globals as mg #@UnresolvedImport
from .. import lib #@UnresolvedImport
from .. import my_exceptions #@UnresolvedImport
from .. import getdata #@UnresolvedImport
from . import importer #@UnresolvedImport

ROWS_TO_SHOW_USER = 10  ## need to show enough to choose encoding
ERR_NO_DELIM = 'Could not determine delimiter'
ERR_NEW_LINE_IN_UNQUOTED = 'new-line character seen in unquoted field'
ERR_NEW_LINE_IN_STRING = 'newline inside string'  ## Shouldn't happen now I 


class DlgImportDisplay(wx.Dialog):
    """
    Show user csv sample assuming first encoding and auto-detected delimiter.
    Let user change encoding and delimiter until happy.
    Also select whether data has a header or not.
    """

    def __init__(self,
            parent, fpath, dialect, encodings, probably_has_hdr, retvals):
        wx.Dialog.__init__(self, parent=parent, 
            title=_('Contents look correct?'),
            style=wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX|wx.RESIZE_BORDER
            |wx.SYSTEM_MENU|wx.CAPTION|wx.CLIP_CHILDREN)
        debug = False
        lib.GuiLib.safe_end_cursor()  ## needed for Mac
        self.parent = parent
        self.fpath = fpath
        self.dialect = dialect
        self.encoding = encodings[0]
        self.retvals = retvals
        panel = wx.Panel(self)
        szr_main = wx.BoxSizer(wx.VERTICAL)
        szr_options = wx.BoxSizer(wx.HORIZONTAL)
        szr_btns = wx.StdDialogButtonSizer()
        lbl_instructions = wx.StaticText(panel, -1, _('If the fields are not '
            'separated correctly, enter a different delimiter.'
            '\n\nDoes the text look correct? If not, try another encoding.'))
        self.delimiter = self.dialect.delimiter
        lbl_delim = wx.StaticText(panel, -1, _('Delimiter:'))
        self.rad_text = wx.RadioButton(
            panel, -1, 'Character', style=wx.RB_GROUP)
        self.rad_text.Bind(wx.EVT_RADIOBUTTON, self.on_rad_text)
        self.char_delim = wx.TextCtrl(panel, -1, self.delimiter, size=(25, -1))
        self.char_delim.Bind(wx.EVT_CHAR, self.on_delim_change)
        self.rad_tab = wx.RadioButton(panel, -1, 'Tab')
        self.rad_tab.Bind(wx.EVT_RADIOBUTTON, self.on_rad_tab)
        tab_delim = (self.delimiter == '\t')
        if tab_delim:
            self.rad_tab.SetValue(True)
            self.char_delim.Disable()
        lbl_encoding = wx.StaticText(panel, -1, _('Encoding:'))
        self.drop_encodings = wx.Choice(panel, -1, choices=encodings)
        self.drop_encodings.SetSelection(0)
        self.drop_encodings.Bind(wx.EVT_CHOICE, self.on_sel_encoding)
        self.chk_has_header = wx.CheckBox(panel, -1, _('Has header row '
            '(Note - SOFA cannot handle multiple header rows)'))
        self.chk_has_header.SetValue(probably_has_hdr)
        szr_options.Add(lbl_delim, 0, wx.RIGHT, 10)
        szr_options.Add(self.rad_text)
        szr_options.Add(self.char_delim, 0, wx.RIGHT, 15)
        szr_options.Add(self.rad_tab, 0, wx.RIGHT, 20)
        szr_options.Add(lbl_encoding, 0, wx.LEFT|wx.RIGHT, 5)
        szr_options.Add(self.drop_encodings, 0, wx.RIGHT, 10)
        str_content, content_height = self.get_content()
        if debug: print(str_content)
        self.html_content = wx.html2.WebView.New(panel, -1,
            size=(500, content_height))
        lib.OutputLib.update_html_ctrl(self.html_content, str_content)
        btn_cancel = wx.Button(panel, wx.ID_CANCEL)
        btn_cancel.Bind(wx.EVT_BUTTON, self.on_btn_cancel)
        btn_ok = wx.Button(panel, wx.ID_OK)
        btn_ok.Bind(wx.EVT_BUTTON, self.on_btn_ok)
        szr_btns.AddButton(btn_cancel)
        szr_btns.AddButton(btn_ok)
        szr_btns.Realize()
        szr_main.Add(lbl_instructions, 0, wx.ALL, 10)
        szr_main.Add(szr_options, 0, wx.ALL, 10)
        szr_main.Add(self.chk_has_header, 0, wx.BOTTOM|wx.LEFT|wx.RIGHT, 10)
        szr_main.Add(self.html_content, 1, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szr_main.Add(szr_btns, 0, wx.GROW|wx.ALL, 10)
        panel.SetSizer(szr_main)
        szr_main.SetSizeHints(self)
        self.Layout()

    def on_rad_tab(self, _event):
        self.delimiter = '\t'
        self.char_delim.Value = ''
        self.char_delim.Disable()
        self.update_delim()

    def on_rad_text(self, _event):
        self.char_delim.Value = ''
        self.char_delim.Enable()
        self.char_delim.SetFocus()

    def update_delim(self):
        tab_delim = self.rad_tab.GetValue()
        if tab_delim:
            self.delimiter = '\t'
        else:
            raw_text_delim = self.char_delim.GetValue()
            if len(raw_text_delim) > 1:
                self.char_delim.SetValue(raw_text_delim[0])
            self.delimiter = self.char_delim.GetValue()
        try:
            self.dialect.delimiter = self.delimiter
            self.set_display()
        except UnicodeEncodeError:
            raise Exception('Delimiter was not encodable as utf-8 as expected')

    def on_delim_change(self, event):
        """
        The delimiter must be a utf-encoded byte string.
        """
        ## NB callafter to allow data to updated in text ctrl
        wx.CallAfter(self.update_delim)
        event.Skip()

    def on_sel_encoding(self, event):
        self.encoding = self.drop_encodings.GetStringSelection()
        self.set_display()
        event.Skip()

    def get_content(self):
        """
        For display in GUI dlg - so makes sense to use the encoding the user has
        selected - whether or not it is a good choice.

        Have to get whole file even though for this part we only need the first
        few lines. No reliable way of breaking into lines pre-csv reader so
        happens at last step.
        """
        try:
            f_csv_sample = open(self.fpath, encoding=self.encoding)
        except Exception as e:
            msg = ('Unable to display the first lines of this CSV file using '
                f'the first selected encoding ({self.encoding}).'
                f'\n\nOrig error: {b.ue(e)}')
            return msg, 100
        try:
            ## Don't use dict reader - consumes first row when we don't know
            ## field names. And if not a header, we might expect some values to
            ## be repeated, which means the row dicts could have fewer fields
            ## than there are actual fields.
            tmp_reader = csv.reader(f_csv_sample, dialect=self.dialect)
        except csv.Error as e:
            lib.GuiLib.safe_end_cursor()
            if b.ue(e).startswith(ERR_NEW_LINE_IN_UNQUOTED):
                CsvSampler._fix_text(self.fpath)
                raise my_exceptions.ImportNeededFix
            else:
                raise
        except Exception as e:
            lib.GuiLib.safe_end_cursor()
            raise Exception('Unable to create reader for file. '
                f'\nCaused by error: {b.ue(e)}')
        try:
            idx = 0
            strdata = []
            for idx, row in enumerate(tmp_reader, 1):
                if row:  ## exclude empty rows
                    strdata.append(row)
                    if len(strdata) >= ROWS_TO_SHOW_USER:
                        break
        except csv.Error as e:
            lib.GuiLib.safe_end_cursor()
            if b.ue(e).startswith(ERR_NEW_LINE_IN_STRING):
                raise Exception(f'Problem with row {idx+1} - '
                    'line break in the middle of a field.')
            else:
                raise
        content, content_height = importer.get_content_dets(strdata)
        return content, content_height
    
    def set_display(self):
        if len(self.dialect.delimiter) > 0:
            try:
                str_content, unused = self.get_content()
                lib.OutputLib.update_html_ctrl(self.html_content, str_content)
            except Exception as e:
                wx.MessageBox('Unable to use the delimiter character supplied.'
                    f'\nCaused by error: {b.ue(e)}')

    def on_btn_cancel(self, _event):
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL)

    def on_btn_ok(self, _event):
        self.retvals.extend([self.encoding, self.chk_has_header.IsChecked()])
        self.Destroy()
        self.SetReturnCode(wx.ID_OK)


class CsvData:
    """
    Wanted ability to reset so made custom class
    """

    def __init__(self, fpath, encoding, dialect, fldnames, *, has_header):
        self.fpath = fpath
        self.encoding = encoding
        self.dialect = dialect
        self.fldnames = fldnames
        self.has_header = has_header
        self.reset()


    def reset(self):
        f = open(self.fpath, encoding=self.encoding)
        self.reader = csv.DictReader(
            f, dialect=self.dialect, fieldnames=self.fldnames)
        if self.has_header:
            ## Need to consume first row so we only supply the data rows.
            ## DictReader will only consume first row if we do NOT supply field
            ## names (which we are).
            for _header_row in self.reader:
                #print(_header_row)
                break  ## discard

    def __iter__(self):
        for row in self.reader:
            yield row


class MyDialect(csv.Dialect):
    """
    Enough to cope with single column csvs (with or without commas as decimal
    separators)
    """
    delimiter = ';'
    quotechar = '"'
    doublequote = True
    skipinitialspace = False
    lineterminator = '\n'
    quoting = csv.QUOTE_MINIMAL


class CsvSampler:

    @staticmethod
    def get_sample_rows(fpath):
        debug = False
        possible_encodings = CsvSampler.get_possible_encodings(
            fpath, first_only=True)
        if not possible_encodings:
            raise Exception(
                f"Unable to open '{fpath}' - standard encodings failed")
        try:
            f = open(fpath, encoding=possible_encodings[0])
            sample_rows = []
            for i, row in enumerate(f):
                if i < 20:
                    if debug: print(row)
                    sample_rows.append(row)
        except IOError:
                raise Exception(f'Unable to find file "{fpath}" for importing. '
                    'Please check that file exists.')
        except Exception as e:
            raise Exception('Unable to open and sample file. '
                f'\nCaused by error: {b.ue(e)}')
        return sample_rows

    @staticmethod
    def _fix_text(fpath):
        "Should never be called in headless mode"
        ret = wx.MessageBox(_('The file needs new lines standardised first. '
            'Can SOFA Statistics make a tidied copy for you?'), 
             caption=_('FIX TEXT?'), style=wx.YES_NO)
        if ret == wx.YES:
            new_file = CsvSampler._make_tidied_copy(fpath)
            wx.MessageBox(_("Please check tidied version \"%s\" before "
                "importing/re-importing. May have line breaks in the wrong "
                "places.") % new_file)
        else:
            wx.MessageBox(_('Unable to import file in current form'))

    @staticmethod
    def _ok_delimiter(delimiter):
        try:
            ord_delimiter = ord(delimiter)
            printable = (31 < ord_delimiter < 127)
            if not (printable or '\t'):
                raise Exception('The auto-detected delimiter is unprintable.') 
        except Exception:
            raise Exception('Unable to assess the auto-detected delimiter')


    @staticmethod
    def get_dialect(sniff_sample):
        debug = False
        try:
            sniffer = csv.Sniffer()
            try:
                if debug: print(sniff_sample)
                dialect = sniffer.sniff(
                    sniff_sample, delimiters=['\t', ',', ';'])  ## feeding in tab as part of delimiters means it is picked up even if field contents are not quoted
            except Exception as e:
                if b.ue(e).startswith(ERR_NO_DELIM):
                    dialect = MyDialect()  ## try a safe one of my own
                else:
                    raise
            if debug: print(dialect.delimiter)
            try:
                CsvSampler._ok_delimiter(dialect.delimiter)
            except Exception as e:
                raise Exception('Unable to identify delimiter in csv file. '
                    '\n\nPlease check your csv file can be opened successfully '
                    "in a text editor. If not, SOFA can't import it. SOFA has "
                    'problems with csv files that have been saved in a '
                    'Microsoft-only format'
                    '.\n\nIf saving as csv in in Excel, make sure to select '
                    " 'Yes' to leave out features incompatible with csv."
                    f'\n\nCaused by error: {b.ue(e)}\n')
        except Exception as e:
            raise Exception('Unable to open and sample csv file. '
                f'\nCaused by error: {b.ue(e)}')
        return dialect

    @staticmethod
    def _has_header_row(sample_rows, delim, *, comma_dec_sep_ok=False):
        """
        Will return True if nothing but unambiguous strings in first row and
        anything in other rows that is probably not be a string e.g. a number
        or a date. Empty strings are not proof of anything so are skipped. OK if
        this fails - we must leave it to the user to identify if a header row or
        not (and to choose a possible encoding).
        """
        if len(sample_rows) < 2:  ## a header row needs a following row to be a header
            return False
        delim_str = delim.encode('utf-8')  ## might fail but not worth expensive
        ## process of working out actual decoding if this fails and OK if fails
        ## - just leave has header row to default.
        if delim_str is None:
            raise Exception(
                'Unable to decode import file so header row can be identified')
        first_row_vals = sample_rows[0].split(delim_str)
        second_row_vals = sample_rows[1].split(delim_str)
        row1_types = [lib.get_val_type(val, comma_dec_sep_ok)
            for val in first_row_vals]
        row2_types = [lib.get_val_type(val, comma_dec_sep_ok)
            for val in second_row_vals]
        str_type = mg.VAL_STRING
        empty_type = mg.VAL_EMPTY_STRING
        non_str_types = [mg.VAL_DATE, mg.VAL_NUMERIC]
        return importer.has_header_row(
            row1_types, row2_types, str_type, empty_type, non_str_types)

    @staticmethod
    def get_prob_has_hdr(sample_rows, fpath, dialect):
        """
        Method used in csv rejects some clear-cut cases where there is a header
        - ignores any columns which are of mixed type - takes them out of
        contention.

        If none survive, always assumes no header as never has any columns to
        test.

        Need an additional test looking for all strings in top, and anything
        below that is numeric or a date.

        Must always return a result no matter what even if we don't know and
        just assume no header i.e. False.
        """
        prob_has_hdr = False
        try:
            sniffer = csv.Sniffer()
            sample_rows = [x.strip('\n') for x in sample_rows]
            hdr_sample = '\n'.join(sample_rows)
            prob_has_hdr = sniffer.has_header(hdr_sample)
        except csv.Error as e:
            lib.GuiLib.safe_end_cursor()
            if b.ue(e).startswith(ERR_NO_DELIM):
                pass  ## I'll have to try it myself
            elif b.ue(e).startswith(ERR_NEW_LINE_IN_UNQUOTED):
                CsvSampler._fix_text(fpath)
        except Exception as e:  ## If everything else succeeds don't let this stop things
            pass
        try:
            if not prob_has_hdr:
                ## test it myself
                delim = dialect.delimiter
                comma_dec_sep_ok = (dialect.delimiter != ',')
                prob_has_hdr = CsvSampler._has_header_row(
                    fpath, sample_rows, delim, comma_dec_sep_ok=comma_dec_sep_ok)        
        except Exception as e:
            pass
        return prob_has_hdr

    @staticmethod
    def get_possible_encodings(fpath, *, first_only=False):
        """
        Get list of encodings which potentially work for a sample. Fast enough
        not to have to sacrifice code readability etc for performance.

        See http://rspeer.github.io/blog/2014/03/30/unicode-deadbeef/ for
        defense of whitelisting encodings.
        """
        debug = False
        MS_GREMLINS_ENCODING = 'cp1252'
        local_encoding = locale.getpreferredencoding()
        if mg.PLATFORM == mg.WINDOWS:
            encodings = [MS_GREMLINS_ENCODING, 'iso-8859-1', 'cp1257',
                'utf-8', 'utf-16', 'big5']
        else:
            encodings = [
                'utf-8', 'iso-8859-1', MS_GREMLINS_ENCODING, 'cp1257',
                'utf-16', 'big5']
        if local_encoding.lower() not in encodings:
            encodings.insert(0, local_encoding.lower())
        possible_encodings = []
        for encoding in encodings:
            if debug: print(f'About to test encoding: {encoding}')
            try:
                with open(fpath, encoding=encoding) as f:
                    f.read()
            except Exception:
                continue
            else:
                possible_encodings.append(encoding)
                if first_only:
                    break
        return possible_encodings

    @staticmethod
    def _make_tidied_copy(path):
        """
        Return renamed copy with line separators all turned to the one type
        appropriate to the OS.

        NB file may be broken csv so may need manual correction.
        """
        pathstart = path.parent
        filestart = path.stem
        extension = path.suffix 
        new_file = pathstart / f'{filestart}_tidied{extension}'
        with open(path) as f:
            raw = f.read()
        newstr = CsvImporter.consolidate_line_seps(raw)
        with open(new_file, 'w') as f:
            f.write(newstr)
        return new_file


class CsvImporter(importer.FileImporter):

    def __init__(self, parent, fpath, tblname,
            supplied_encoding, *,
            headless, headless_has_header, force_quickcheck=False):
        self.parent = parent
        importer.FileImporter.__init__(self, self.parent, fpath, tblname,
            headless=headless, headless_has_header=headless_has_header,
            supplied_encoding=supplied_encoding)
        self.ext = 'CSV'
        self.force_quickcheck = force_quickcheck

    def set_params(self):
        pass  ## cover all this in more complex fashion handling encoding and delimiters

    @staticmethod
    def consolidate_line_seps(mystr):
        for sep in ('\n', '\r', '\r\n'):
            mystr = mystr.replace(sep, os.linesep)
        return mystr

    def assess_sample(self, reader, progbar, steps_per_item, import_status,
            comma_delimiter, faulty2missing_fld_list, ok_fldnames):
        """
        Assess data sample to identify field types based on values in fields.

        If a field has mixed data types will define as string.

        Returns fldtypes, sample_data.

        fldtypes - dict with original (uncorrected) field names as keys and
        field types as values.

        sample_data - list of dicts containing the first rows of data
        (no point reading them all again during subsequent steps).

        Sample first N data rows (at most) to establish field types.
        """
        debug = False
        bolhas_rows = False
        sample_data = []
        for i, row in enumerate(reader):
            if debug:
                if i < 10:
                    print(row)
            if i % 50 == 0:
                if not self.headless:
                    wx.Yield()
                if import_status[mg.CANCEL_IMPORT]:
                    progbar.SetValue(0)
                    raise my_exceptions.ImportCancel
            if self.has_header and i == 0:
                continue  ## skip first line
            bolhas_rows = True
            ## process row
            sample_data.append(row)  ## include Nones even if going to change to
                ## empty strings or whatever later.
            gauge_val = min(i*steps_per_item, mg.IMPORT_GAUGE_STEPS)
            progbar.SetValue(gauge_val)
            if self.headless:
                i2break = ROWS_TO_SHOW_USER
            else:
                i2break = (ROWS_TO_SHOW_USER if self.has_header 
                    else ROWS_TO_SHOW_USER - 1)
            if i == i2break:
                break
        fldtypes = []
        for ok_fldname in ok_fldnames:
            fldtype = importer.assess_sample_fld(sample_data, 
                ok_fldname, ok_fldnames, faulty2missing_fld_list,
                has_header=self.has_header, allow_none=False,
                comma_dec_sep_ok=not comma_delimiter, headless=self.headless)
            fldtypes.append(fldtype)
        fldtypes = dict(zip(ok_fldnames, fldtypes))
        if not bolhas_rows:
            raise Exception('No data to import')
        return fldtypes, sample_data

    def _get_confirmed_sample_dets(self):
        """
        Get dialect, encoding, and has_header for sample of CSV.

        Try encodings until get first success. Give user choice to use it or
        keep going.

        Windows is always trickier - less likely to be utf-8 from the start.
        Many of these encodings will "work" even though they are not the
        encoding used to create them in the first place. That's why the user is
        given a choice. Could use chardets somehow as well.
        """
        sample_rows = CsvSampler.get_sample_rows(self.fpath)
        sniff_sample = ''.join(sample_rows)
        dialect = CsvSampler.get_dialect(sniff_sample)
        if self.headless and (self.supplied_encoding is None and 
                self.headless_has_header is None):
            raise Exception(
                'Must supply encoding and header status if running headless')
        if self.headless:
            encoding = self.supplied_encoding
            has_header = self.headless_has_header
        else:
            probably_has_hdr = CsvSampler.get_prob_has_hdr(
                sample_rows, self.fpath, dialect)
            encodings = CsvSampler.get_possible_encodings(self.fpath)
            if not encodings:
                raise Exception(
                    _('Data could not be processed using available encodings'))
            ## give user choice to change encoding, delimiter, and say if has header
            retvals = []  ## populate inside dlg
            dlg = DlgImportDisplay(self.parent, self.fpath, dialect, encodings,
                probably_has_hdr, retvals)
            ret = dlg.ShowModal()
            if ret != wx.ID_OK:
                raise my_exceptions.ImportConfirmationRejected
            encoding, has_header = retvals
        return dialect, encoding, has_header

    @staticmethod
    def _get_avg_row_size(rows):
        """
        Measures length of string of comma separated values in bytes.

        Used for progress bar by measuring how many bytes we are through the
        file.

        Expects to get a list of strings or a dict of strings.

        If a dict, the final item could be a list if there are more items in the
        original row than the dict reader expected.

        If not enough field_names, will use None as key for a list of any extra
        values.
        """
        debug = False
        size = 0
        i = None
        for i, row in enumerate(rows, 1):
            try:
                values = row.values()
            except AttributeError:
                values = row
            vals = []
            for value in values:
                if isinstance(value, list):
                    vals.extend([lib.none2empty(x) for x in value])
                else:
                    vals.append(lib.none2empty(value))
            row_str = ','.join(vals)
            row_size = len(row_str)
            if debug: print(row, row_str, row_size)
            if debug: print(row_size)
            size += row_size
        if i is None:
            avg_row_size = 10  ## if only one then can be almost anything -
                ## progress will flash by any way
        else:
            avg_row_size = float(size)/i
        return avg_row_size

    def get_init_csv_details(self):
        """
        Get various details about csv from a sample.
        """
        debug = False
        ok_fldnames = []
        try:
            dialect, encoding, self.has_header = self._get_confirmed_sample_dets()
        except my_exceptions.ImportConfirmationRejected as e:
            lib.GuiLib.safe_end_cursor()
            raise
        except Exception as e:
            lib.GuiLib.safe_end_cursor()
            raise Exception('Unable to get sample of csv with details. '
                f'\nCaused by error: {b.ue(e)}')
        if not self.headless:
            wx.BeginBusyCursor()
        if self.has_header:
            try:
                ## 1st row will be consumed to get field names
                with open(self.fpath, encoding=encoding) as f:
                    tmp_reader = csv.DictReader(f, dialect=dialect)
                    ok_fldnames = importer.process_fldnames(
                        tmp_reader.fieldnames,
                        headless=self.headless,
                        force_quickcheck=self.force_quickcheck)
            except Exception as e:
                ## should have already been successfully through this in
                ## get_confirmed_sample_dets()
                lib.GuiLib.safe_end_cursor()
                raise Exception('Unable to get sample of csv with details. '
                    f'\nCaused by error: {b.ue(e)}')
        else:
            try:
                with open(self.fpath, encoding=encoding) as f:
                    tmp_reader = csv.reader(f, dialect=dialect)
                    for row in tmp_reader:
                        if debug: print(row)
                        ok_fldnames = [mg.NEXT_FLDNAME_TEMPLATE % (x+1,)
                            for x in range(len(row))]
                        break  ## get number of fields from first row (not consumed because not using dictreader
            except Exception as e:
                ## should have already been successfully through this in
                ## get_confirmed_sample_dets()
                lib.GuiLib.safe_end_cursor()
                raise Exception('Unable to get sample of csv with details. '
                    f'\nCaused by error: {b.ue(e)}')
        if not ok_fldnames:
            raise Exception('Unable to get ok field names')
        with open(self.fpath, encoding=encoding) as f:
            tmp_reader = csv.reader(f, dialect=dialect)
            row_size = self._get_avg_row_size(tmp_reader)
        return dialect, encoding, ok_fldnames, row_size

    def _estimate_rows_n(self, row_size):
        """
        Estimate number of rows (only has to be good enough for progress
        estimation)
        """
        debug = False
        try:
            tot_size = os.path.getsize(self.fpath)  ## in bytes
            if debug:
                print(f'tot_size: {tot_size}')
                print(f'row_size: {row_size}')
            rows_n = float(tot_size)/row_size
            ## If not enough field_names, will use None as key for a list of any
            ## extra values.
        except Exception as e:
            lib.GuiLib.safe_end_cursor()
            raise Exception('Unable to get count of rows. '
                f'\nCaused by error: {b.ue(e)}')
        return rows_n

    def _get_fldtypes(self, dialect, encoding, ok_fldnames,
            progbar, steps_per_item,
            import_status, comma_delimiter,
            faulty2missing_fld_list):
        with open(self.fpath, encoding=encoding) as f:
            try:  ## we supply field names so will start with first data row
                reader = csv.DictReader(
                    f, dialect=dialect, fieldnames=ok_fldnames)
                fldtypes, _sample_data = self.assess_sample(reader, progbar,
                    steps_per_item, import_status, comma_delimiter,
                    faulty2missing_fld_list, ok_fldnames)
            except Exception as e:
                lib.GuiLib.safe_end_cursor()
                raise Exception('Unable to create reader for file. '
                    f'\nCaused by error: {b.ue(e)}')
        return fldtypes

    def import_content(self,
            lbl_feedback=None, import_status=None, progbar=None):
        """
        Get field types dict. Use it to test each and every item before they
        are added to database (after adding the records already tested).

        Add to disposable table first and if completely successful, rename
        table to final name.
        """
        debug = False
        ## understand what sort of data we have (encoding, dialect etc)
        if lbl_feedback is None: lbl_feedback = importer.DummyLabel()
        if import_status is None:
            import_status = importer.dummy_import_status.copy()
        if progbar is None: progbar = importer.DummyProgBar()
        faulty2missing_fld_list = []
        if not self.headless:
            wx.BeginBusyCursor()
        try:
            (dialect, encoding, 
             ok_fldnames, row_size) = self.get_init_csv_details()
        except my_exceptions.ImportNeededFix:
            lib.GuiLib.safe_end_cursor()
            return
        except my_exceptions.ImportConfirmationRejected as e:
            lib.GuiLib.safe_end_cursor()
            raise
        except Exception as e:
            lib.GuiLib.safe_end_cursor()
            raise Exception('Unable to get initial csv details. '
                f'\nCaused by error: {b.ue(e)}')
        rows_n = self._estimate_rows_n(row_size)
        sample_n = min(ROWS_TO_SHOW_USER, rows_n)
        items_n = rows_n + sample_n + 1  ## 1 is for the final tmp to named step
        steps_per_item = importer.get_steps_per_item(items_n)
        comma_delimiter = (dialect.delimiter == ',')
        fldtypes = self._get_fldtypes(dialect, encoding, ok_fldnames,
            progbar, steps_per_item,
            import_status, comma_delimiter,
            faulty2missing_fld_list)
        ## now import data
        default_dd = getdata.get_default_db_dets()
        con, cur = default_dd.con, default_dd.cur
        try:
            data = CsvData(self.fpath, encoding, dialect, ok_fldnames,
                has_header=self.has_header)
            if debug:
                print('About to print rows')
                for row in data:
                    print(row)
                data.reset()
            gauge_start = steps_per_item*sample_n
            feedback = {mg.NULLED_DOTS_KEY: False}
            importer.add_to_tmp_tbl(
                feedback, import_status,
                con, cur,
                self.tblname, ok_fldnames, fldtypes,
                faulty2missing_fld_list, data,
                progbar, rows_n, steps_per_item, gauge_start,
                allow_none=False, comma_dec_sep_ok=not comma_delimiter,
                has_header=self.has_header, headless=self.headless)
            ## so fast only shows last step in progress bar
            importer.tmp_to_named_tbl(con, cur,
                self.tblname, progbar, feedback[mg.NULLED_DOTS_KEY],
                headless=self.headless)
        except Exception as e:
            importer.post_fail_tidy(progbar, default_dd.con, default_dd.cur)
            raise
        cur.close()
        con.commit()
        con.close()
        progbar.SetValue(0)
