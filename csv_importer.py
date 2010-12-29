#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import codecs
import csv
import locale
import os
import pprint
import wx
import wx.html

import my_globals as mg
import lib
import my_exceptions
import dbe_plugins.dbe_sqlite as dbe_sqlite
import getdata
import importer

ROWS_TO_SAMPLE = 20
ESC_DOUBLE_QUOTE = "\x14" # won't occur naturally and doesn't break csv module
# Shift Out control character in ASCII 
"""
Support for unicode is lacking from the Python 2 series csv module and quite a
    bit of wrapping is required to work around it.  Must wait for Python 3 or
    spend a lot more time on this. But it still put Dörthe in correctly ;-).
See http://docs.python.org/library/csv.html#examples
http://bugs.python.org/issue1606092
"""

def consolidate_line_seps(str):
    for sep in ["\n", "\r", "\r\n"]:
        str = str.replace(sep, os.linesep)
    return str

def ok_delimiter(delimiter):
    try:
        ord_delimiter = ord(delimiter)
        if not 31 < ord_delimiter < 127:
            raise Exception(u"The auto-detected delimiter is unprintable.") 
    except Exception, e:
        raise Exception(u"Unable to assess the auto-detected delimiter")

def get_dialect(file_path):
    debug = False
    try:
        f = open(file_path) # don't use "U" - let it fail if necessary
            # and suggest an automatic cleanup.
        sample_lines = []
        for i, line in enumerate(f.readline()):
            if i < 20:
                sample_lines.append(line)
        sniff_sample = "".join(sample_lines)
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sniff_sample)
        if debug: print(dialect.delimiter)
        try:
            ok_delimiter(dialect.delimiter)
        except Exception, e:
            raise Exception(u"Unable to identify delimiter in csv file. "
                u"\n\nPlease check your csv file can be opened successfully in "
                u"a text editor. If not, SOFA can't import it. SOFA has "
                u"problems with csv files that have been saved in a "
                u"Microsoft-only format."
                u"\n\nIf saving as csv in in Excel, make sure to select "
                u" 'Yes' to leave out features incompatible with csv."
                u"\n\nCaused by error: %s\n" % lib.ue(e))
    except IOError:
            raise Exception(u"Unable to find file \"%s\" for importing. "
                            u"Please check that file exists." % file_path)
    except Exception, e:
        raise Exception(u"Unable to open and sample csv file. "
                        u"\nCaused by error: %s" % lib.ue(e))
    return dialect
    
def get_avg_row_size(rows):
    """
    Measures length of string of comma separated values in bytes.
    Used for progress bar by measuring how many bytes we are through the file.
    Expects to get a list of strings or a dict of strings.
    If a dict, the final item could be a list if there are more items in the
        original row than the dict reader expected.
    If not enough field_names, will use None as key for a list of any extra 
        values.
    """
    debug = False
    size = 0
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
        row_str = u",".join(vals)
        row_size = len(row_str)
        if debug: print(row, row_str, row_size)
        #if debug: print(row_size)
        size += row_size
    avg_row_size = float(size)/i
    return avg_row_size


# http://docs.python.org/library/csv.html
class UnicodeCsvReader(object):
    """
    Sometimes preferable to dict reader because doesn't consume first row.
    Dict readers do when field names not supplied.
    """
    def __init__(self, utf8_encoded_csv_data, dialect=csv.excel, **kwargs):
        # csv.py doesn't do Unicode; encode temporarily as UTF-8:
        try:
            dialect.escapechar = ESC_DOUBLE_QUOTE
            self.csv_reader = csv.reader(utf8_encoded_csv_data, dialect=dialect, 
                                         **kwargs)
        except Exception, e:
            raise Exception(u"Unable to start internal csv reader. "
                            u"\nCaused by error: %s" % lib.ue(e))
        self.i = 0
        
    def __iter__(self):
        debug = False
        if debug: print(u"About to iterate through csv.reader")
        for row in self.csv_reader:
            self.i += 1
            try:
                if debug: print(u"Iterating through csv.reader")
                # decode UTF-8 back to Unicode, cell by cell:
                rowvals = []
                j = 0 # item counter
                for val in row: # empty strings etc but never None
                    if isinstance(val, list):
                        raise Exception(u"Expected text but got a list of "
                                        u"text.\nYou probably forgot to "
                                        u"quote a value containing a value "
                                        u"separator e.g. Feb 11, 2010")
                    j += 1
                    try:
                        uval = val.decode("utf8")
                        rowvals.append(uval)
                    except Exception, e:
                        raise Exception(u"Problem decoding values. "
                                        u"\nCaused by error: %s" % lib.ue(e))
            except Exception, e:
                raise Exception(u"Problem with csv file on row %s, item %s. " %
                                (self.i, j) +
                                u"\nCaused by error: %s" % lib.ue(e))
            yield rowvals
            

class UnicodeCsvDictReader(object):
    """
    If the fieldnames parameter is omitted, the values in the first row of the 
        csv file will be used as the fieldnames. Allows duplicates.
        http://docs.python.org/library/csv.html
    The first row will be consumed and no longer available.
    """
    def __init__(self, utf8_encoded_csv_data, dialect, fieldnames=None):
        # csv.py doesn't do Unicode; encode temporarily as UTF-8:
        try:
            kwargs = {"fieldnames": fieldnames} if fieldnames else {}
            dialect.escapechar = ESC_DOUBLE_QUOTE
            self.csv_dictreader = csv.DictReader(utf8_encoded_csv_data, 
                                                 dialect=dialect, **kwargs)
        except Exception, e:
            raise Exception(u"Unable to start internal csv dict reader. "
                            u"\nCaused by error: %s" % lib.ue(e))
        self.fieldnames = self.csv_dictreader.fieldnames
        self.i = 0 if fieldnames else 1 # if no fieldnames, row 1 was consumed
    
    def __iter__(self):
        """
        Iterates through rows. If no field names were fed in at the start, will
            begin at the second row (the first having been consumed to get the 
            field names).
        If required, decode UTF8-encoded byte string back to Unicode, dict pair 
            by pair.
        """
        debug = False
        verbose = True
        for row in self.csv_dictreader:
            self.i += 1 # row counter
            if debug and verbose:
                if self.i == 84: # change this as needed
                    pprint.pprint(row)
            try:
                unicode_key_value_tups = []
                for keyval in row.items():
                    if debug and verbose: 
                        print("Row: %s KeyVal: %s" % (self.i, keyval))
                    uni_key_val = []
                    for item in keyval:
                        if item is None:
                            item = u"" # be forgiving and effectively right pad
                        if isinstance(item, list):
                            raise Exception(u"Expected text but got a list of "
                                            u"text.\nYou probably forgot to "
                                            u"quote a value containing a value "
                                            u"separator e.g. Feb 11, 2010")
                        if not isinstance(item, unicode):
                            item = item.decode("utf8")
                        uni_key_val.append(item)
                    unicode_key_value_tups.append(tuple(uni_key_val))
            except Exception, e:
                raise Exception(u"Problem with csv file on row %s. " % self.i +
                                u"\nCaused by error: %s" % lib.ue(e))
            yield dict(unicode_key_value_tups)

def escape_double_quotes_in_uni_lines(lines):
    """
    Needed because csv not handling doubled double quotes inside fields.
    """
    escaped_lines = []
    for i, line in enumerate(lines, 1):
        if not isinstance(line, unicode):
            raise Exception(u"Cannot escape double quotes unless a unicode "
                            u"string")
        try:
            escaped_line = line.replace(u"\"\"", u"%s\"" % ESC_DOUBLE_QUOTE).\
                                replace(u"\\\"", u"%s\"" % ESC_DOUBLE_QUOTE)
        except Exception, e:
            raise Exception(u"Error escaping double quotes on line %s" % i +
                            u"\nCaused by error: %s" % lib.ue(e))
        escaped_lines.append(escaped_line)
    return escaped_lines

def encode_lines_as_utf8(uni_lines):
    utf8_encoded_lines = []
    for uni_line in uni_lines:
        try:
            utf8_encoded_line = uni_line.encode("utf8")
            utf8_encoded_lines.append(utf8_encoded_line)
        except Exception, e:
            raise Exception(u"Unable to encode decoded data as utf8. "
                            u"\nCaused by error: %s" % lib.ue(e))
    return utf8_encoded_lines

def csv_to_utf8_byte_lines(file_path, encoding, n_lines=None, strict=True):
    """
    The csv module infamously only accepts lines of bytes encoded as utf-8.
    Need to do the escaping of double quotes here so we can deal with a unicode
        string and not a byte string.
    NB we have no idea what the original encoding was or which computer or OS or 
        locale it was done on.  Eventually we could use chardet module to 
        sensibly guess but in meantime try several - including the local 
        encoding then utf-8 etc.
    """
    debug = False
    try:
        errors = "strict" if strict else "replace"
        f = codecs.open(file_path, encoding=encoding, errors=errors)
    except IOError, e:
        raise Exception(u"Unable to open file for re-encoding. "
                        u"\nCaused by error: %s" % lib.ue(e))
    # this bit can fail even if the open succeeded
    uni_lines = []
    for i, line in enumerate(f, 1):
        uni_lines.append(line)
        if n_lines is not None:
            if i >= n_lines:
                break
    escaped_uni_lines = escape_double_quotes_in_uni_lines(uni_lines)
    utf8_byte_lines = encode_lines_as_utf8(escaped_uni_lines)
    if debug:
        print(repr(utf8_byte_lines))
    return utf8_byte_lines


class DlgImportDisplay(wx.Dialog):
    
    """
    Show user csv sample assuming first encoding and auto-detected delimiter.
    Let user change encoding and delimiter until happy.
    Also select whether data has a header or not. 
    """
    
    def __init__(self, parent, file_path, dialect, encodings, retvals):
        wx.Dialog.__init__(self, parent=parent, 
                           title=_("Contents look correct?"), 
                           style=wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX|\
                           wx.RESIZE_BORDER|wx.SYSTEM_MENU|wx.CAPTION|\
                           wx.CLIP_CHILDREN)
        lib.safe_end_cursor() # needed for Mac
        self.parent = parent
        self.file_path = file_path
        self.dialect = dialect
        self.encoding = encodings[0]
        self.retvals = retvals
        panel = wx.Panel(self)
        szr_main = wx.BoxSizer(wx.VERTICAL)
        szr_options = wx.BoxSizer(wx.HORIZONTAL)
        szr_btns = wx.StdDialogButtonSizer()
        lbl_instructions = wx.StaticText(panel, -1, _("If the fields are not "
                            "separated correctly, enter a different delimiter "
                            "(\",\" and \";\" are common choices)."
                            "\n\nDoes the text look "
                            "correct? If not, try another encoding."))
        self.udelimiter = self.dialect.delimiter.decode("utf8")
        lbl_delim = wx.StaticText(panel, -1, _("Delimiter"))
        self.txt_delim = wx.TextCtrl(panel, -1, self.udelimiter)
        self.txt_delim.Bind(wx.EVT_CHAR, self.on_delim_change)
        lbl_encoding = wx.StaticText(panel, -1, _("Encoding"))
        self.drop_encodings = wx.Choice(panel, -1, choices=encodings)
        self.drop_encodings.SetSelection(0)
        self.drop_encodings.Bind(wx.EVT_CHOICE, self.on_sel_encoding)
        self.chk_has_header = wx.CheckBox(panel, -1, _("Has header row"))
        szr_options.Add(lbl_delim, 0, wx.RIGHT, 5)
        szr_options.Add(self.txt_delim, 0, wx.GROW|wx.RIGHT, 10)
        szr_options.Add(lbl_encoding, 0, wx.RIGHT, 5)
        szr_options.Add(self.drop_encodings, 0, wx.GROW|wx.RIGHT, 10)
        szr_options.Add(self.chk_has_header, 0)
        content, content_height = self.get_content()
        self.html_content = wx.html.HtmlWindow(panel, -1, 
                                               size=(500,content_height))
        self.html_content.SetPage(content)
        btn_cancel = wx.Button(panel, wx.ID_CANCEL)
        btn_cancel.Bind(wx.EVT_BUTTON, self.on_btn_cancel)
        btn_ok = wx.Button(panel, wx.ID_OK)
        btn_ok.Bind(wx.EVT_BUTTON, self.on_btn_ok)
        szr_btns.AddButton(btn_cancel)
        szr_btns.AddButton(btn_ok)
        szr_btns.Realize()
        szr_main.Add(lbl_instructions, 0, wx.ALL, 10)
        szr_main.Add(szr_options, 0, wx.GROW|wx.ALL, 10)
        szr_main.Add(self.html_content, 1, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szr_main.Add(szr_btns, 0, wx.GROW|wx.ALL, 10)
        panel.SetSizer(szr_main)
        szr_main.SetSizeHints(self)
        self.Layout()
    
    def update_delim(self):
        self.udelimiter = self.txt_delim.GetValue()
        try:
            self.dialect.delimiter = self.udelimiter.encode("utf8")
            self.set_display()
        except UnicodeEncodeError:
            raise Exception(u"Delimiter was not encodable as utf-8 as expected")
        
    def on_delim_change(self, event):
        """
        The delimiter must be a utf-encoded byte string.
        """
        # NB callafter to allow data to updated in text ctrl
        wx.CallAfter(self.update_delim)
        event.Skip()

    def on_sel_encoding(self, event):
        self.encoding = self.drop_encodings.GetStringSelection()
        self.set_display()
        event.Skip()
    
    def get_content(self):
        debug = False
        self.utf8_encoded_csv_sample = csv_to_utf8_byte_lines(self.file_path,
                                          self.encoding, n_lines=ROWS_TO_SAMPLE)
        try:
            # don't use dict reader - consumes first row when we don't know
            # field names.  And if not a header, we might expect some values to
            # be repeated, which means the row dicts could have fewer fields
            # than there are actual fields.
            tmp_reader = UnicodeCsvReader(self.utf8_encoded_csv_sample, 
                                          dialect=self.dialect)
        except csv.Error, e:
            lib.safe_end_cursor()
            if lib.ue(e).startswith(u"new-line character seen in unquoted "
                                    u"field"):
                self.fix_text()
                raise my_exceptions.ImportNeededFixException
            else:
                raise
        except Exception, e:
            lib.safe_end_cursor()
            raise Exception(u"Unable to create reader for file. "
                            u"\nCaused by error: %s" % lib.ue(e))
        decoded_lines = [] # init
        rows = [x for x in tmp_reader if x] # exclude empty rows
        try:
            max_row_len = max([len(x) for x in rows])
        except Exception, e:
            max_row_len = None
        for row in rows:
            len_row = len(row)
            if debug: print(len_row, row)
            if len_row < max_row_len:
                # right pad sequence with empty str (to become empty str cells)
                row += [u"" for x in range(max_row_len - len_row)]
            line = u"<tr><td>" + u"</td><td>".join(row) + u"</td></tr>"
            decoded_lines.append(line)
        trows = u"\n".join(decoded_lines)
        content = u"<table border='1' style='border-collapse: collapse;'>" + \
                                    u"<tbody>\n" + trows + u"\n</tbody></table>"
        n_lines_actual = len(decoded_lines)
        content_height = 35*n_lines_actual
        content_height = 300 if content_height > 300 else content_height
        return content, content_height
    
    def set_display(self):
        if len(self.dialect.delimiter) > 0:
            try:
                content, unused = self.get_content()
                self.html_content.SetPage(content)
            except Exception, e:
                wx.MessageBox(u"Unable to use the delimiter character supplied."
                              u"\nCaused by error: %s" % lib.ue(e))
    
    def on_btn_cancel(self, event):
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL)
        
    def on_btn_ok(self, event):
        self.retvals.extend([self.encoding, self.chk_has_header.IsChecked(), 
                             self.utf8_encoded_csv_sample])
        self.Destroy()
        self.SetReturnCode(wx.ID_OK)


class CsvImporter(importer.FileImporter):
    """
    Import csv file into default SOFA SQLite database.
    Needs to identify data types to ensure only consistent data in a field.
    Adds unique index id so can identify unique records with certainty.
    """
    
    def __init__(self, parent, file_path, tbl_name):
        self.parent = parent
        importer.FileImporter.__init__(self, self.parent, file_path, tbl_name)
        self.ext = u"CSV"
        
    def assess_sample(self, reader, progbar, steps_per_item, import_status, 
                      comma_delimiter, faulty2missing_fld_list):
        """
        Assess data sample to identify field types based on values in fields.
        If a field has mixed data types will define as string.
        Returns orig_fld_names, fld_types, sample_data.
        fld_types - dict with original (uncorrected) field names as keys and 
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
                wx.Yield()
                if import_status[mg.CANCEL_IMPORT]:
                    progbar.SetValue(0)
                    raise my_exceptions.ImportCancelException
            if self.has_header and i == 0:
                continue # skip first line
            bolhas_rows = True
            # process row
            sample_data.append(row) # include Nones even if going to change to 
                # empty strings or whatever later.
            gauge_val = i*steps_per_item
            progbar.SetValue(gauge_val)
            i2break = ROWS_TO_SAMPLE if self.has_header else ROWS_TO_SAMPLE - 1
            if i == i2break:
                break
        fld_types = []
        orig_fld_names = reader.fieldnames
        for orig_fld_name in orig_fld_names:
            fld_type = importer.assess_sample_fld(sample_data, self.has_header,
                                orig_fld_name, orig_fld_names, 
                                faulty2missing_fld_list, allow_none=False,
                                comma_dec_sep_ok=not comma_delimiter)
            fld_types.append(fld_type)
        fld_types = dict(zip(orig_fld_names, fld_types))
        if not bolhas_rows:
            raise Exception(u"No data to import")
        return orig_fld_names, fld_types, sample_data
    
    def get_avg_row_size(self, tmp_reader):
        """
        Expects to get a list of strings or a dict of strings.
        If a dict, the final item could be a list if there are more items in the
            original row than the dict reader expected.
        """
        return get_avg_row_size(rows=tmp_reader)

    def make_tidied_copy(self, path):
        """
        Return renamed copy with line separators all turned to the one type
            appropriate to the OS.
        NB file may be broken csv so may need manual correction.
        """
        pathstart, filename = os.path.split(path)
        filestart, extension = os.path.splitext(filename)
        new_file = os.path.join(pathstart, filestart + "_tidied" + extension)
        f = open(path)
        raw = f.read()
        f.close()
        newstr = consolidate_line_seps(raw)
        f = open(new_file, "w")
        f.write(newstr)
        f.close()
        return new_file

    def fix_text(self):
        ret = wx.MessageBox(_("The file needs new lines standardised first. "
                             "Can SOFA Statistics make a tidied copy for you?"), 
                             caption=_("FIX TEXT?"), style=wx.YES_NO)
        if ret == wx.YES:
            new_file = self.make_tidied_copy(self.file_path)
            wx.MessageBox(_("Please check tidied version \"%s\" "
                            "before importing.  May have line "
                            "breaks in the wrong places.") % new_file)
        else:
            wx.MessageBox(_("Unable to import file in current form"))

    def get_possible_encodings(self):
        """
        Get list of encodings which potentially work for a sample.  Fast enough 
            not to have to sacrifice code readability etc for performance.
        """
        local_encoding = locale.getpreferredencoding()
        if mg.PLATFORM == mg.WINDOWS:
            encodings = ["cp1252", "iso-8859-1", "cp1257", "utf-8", "big5"]
        else:
            encodings = ["utf-8", "iso-8859-1", "cp1252", "cp1257", "big5"]
        if local_encoding.lower() not in encodings:
            encodings.insert(0, local_encoding.lower())
        possible_encodings = []
        for encoding in encodings:
            try:
                utf8_encoded_csv_sample = csv_to_utf8_byte_lines(self.file_path, 
                                            encoding, n_lines=ROWS_TO_SAMPLE)
                possible_encodings.append(encoding)
            except Exception, e:
                continue
        return possible_encodings
                      
    def get_sample_with_dets(self):
        """
        Get correctly encoded data.  Try encoding until get first successful
            sample. Give user choice to use it or keep going.
        Also get details -- dialect, encoding, has_header.
        Windows is always trickier - less likely to be utf-8 from the start. 
            Many of these encodings will "work" even though they are not the 
            encoding used to create them in the first place. That's why the user 
            is given a choice. Could use chardets somehow as well.
        """
        debug = False
        dialect = get_dialect(self.file_path)
        encodings = self.get_possible_encodings()
        if not encodings:
            raise Exception(_("Data could not be processed using available "
                              "encodings"))
        # give user choice to change encoding, delimiter, and say if has header
        retvals = [] # populate inside dlg
        dlg = DlgImportDisplay(self.parent, self.file_path, dialect, encodings, 
                               retvals)
        ret = dlg.ShowModal()
        if ret != wx.ID_OK:
            raise my_exceptions.ImportConfirmationRejected
        (encoding, has_header, utf8_encoded_csv_sample) = retvals
        return dialect, encoding, has_header, utf8_encoded_csv_sample

    def get_init_csv_details(self):
        """
        Get various details about csv from a sample.
        """
        debug = False
        try:
            (dialect, encoding, self.has_header, 
             utf8_encoded_csv_sample) = self.get_sample_with_dets()
        except my_exceptions.ImportConfirmationRejected, e:
            raise
        except Exception, e:
            lib.safe_end_cursor()
            raise Exception(u"Unable to get sample of csv with details. "
                            u"\nCaused by error: %s" % lib.ue(e))
        if self.has_header:
            try:
                # 1st row will be consumed to get field names
                tmp_reader = UnicodeCsvDictReader(utf8_encoded_csv_sample, 
                                                  dialect=dialect)
            except Exception, e:
                # should have already been successfully through this in 
                # get_sample_with_dets()
                lib.safe_end_cursor()
                raise Exception(u"Unable to get sample of csv with details. "
                                u"\nCaused by error: %s" % lib.ue(e)) 
            orig_names = tmp_reader.fieldnames
            ok_fld_names = importer.process_fld_names(orig_names)
        else: # get number of fields from first row (not consumed because not 
            # using dictreader.
            try:
                tmp_reader = UnicodeCsvReader(utf8_encoded_csv_sample, 
                                              dialect=dialect)
            except Exception, e:
                # should have already been successfully through this in 
                # get_sample_with_dets()
                lib.safe_end_cursor()
                raise Exception(u"Unable to get sample of csv with details. "
                                u"\nCaused by error: %s" % lib.ue(e)) 
            for row in tmp_reader:
                if debug: print(row)
                ok_fld_names = [mg.NEXT_FLD_NAME_TEMPLATE % (x+1,) 
                               for x in range(len(row))]
                break
        if not ok_fld_names:
            raise Exception(u"Unable to get ok field names")
        row_size = self.get_avg_row_size(tmp_reader)
        return dialect, encoding, ok_fld_names, row_size

    def get_params(self):
        return True # cover all this in more complex fashion handling encoding 
            #and delimiters

    def import_content(self, progbar, import_status, lbl_feedback):
        """
        Get field types dict.  Use it to test each and every item before they 
            are added to database (after adding the records already tested).
        Add to disposable table first and if completely successful, rename
            table to final name.
        """
        debug = False
        faulty2missing_fld_list = []
        wx.BeginBusyCursor()
        try:
            (dialect, encoding, 
             ok_fld_names, row_size) = self.get_init_csv_details()
        except my_exceptions.ImportNeededFixException:
            lib.safe_end_cursor()
            return
        except my_exceptions.ImportConfirmationRejected, e:
            lib.safe_end_cursor()
            raise
        except Exception, e:
            lib.safe_end_cursor()
            raise Exception(u"Unable to get initial csv details. "
                            u"\nCaused by error: %s" % lib.ue(e))
        comma_delimiter = (dialect.delimiter.decode("utf8") == u",")
        try:
            # estimate number of rows (only has to be good enough for progress)
            tot_size = os.path.getsize(self.file_path) # in bytes
            if debug:
                print("tot_size: %s" % tot_size)
                print("row_size: %s" % row_size)
            rows_n = float(tot_size)/row_size
            # If not enough field_names, will use None as key for a list of any 
            # extra values.
        except Exception, e:
            lib.safe_end_cursor()
            raise Exception(u"Unable to get count of rows. "
                            u"\nCaused by error: %s" % lib.ue(e))
        try:
            utf8_encoded_csv_data = csv_to_utf8_byte_lines(self.file_path, 
                                                        encoding, strict=False)
            # we supply field names so will start with first row
            reader = UnicodeCsvDictReader(utf8_encoded_csv_data, 
                                          dialect=dialect, 
                                          fieldnames=ok_fld_names)
        except Exception, e:
            lib.safe_end_cursor()
            raise Exception(u"Unable to create reader for file. "
                            u"\nCaused by error: %s" % lib.ue(e)) 
        default_dd = getdata.get_default_db_dets()
        sample_n = ROWS_TO_SAMPLE if ROWS_TO_SAMPLE <= rows_n else rows_n
        items_n = rows_n + sample_n + 1 # 1 is for the final tmp to named step
        steps_per_item = importer.get_steps_per_item(items_n)
        try:
            (orig_fld_names, fld_types, 
             sample_data) = self.assess_sample(reader, progbar, steps_per_item, 
                                               import_status, comma_delimiter, 
                                               faulty2missing_fld_list)
            # NB reader will be at position ready to access records after sample
            data = sample_data + list(reader) # must be a list not a reader or 
                # can't start again from start of data (e.g. if correction made)
            gauge_start = steps_per_item*sample_n
            feedback = {mg.NULLED_DOTS: False}
            importer.add_to_tmp_tbl(feedback, import_status, default_dd.con, 
                default_dd.cur, self.file_path, self.tbl_name, self.has_header, 
                ok_fld_names, orig_fld_names, fld_types, 
                faulty2missing_fld_list, data, progbar, steps_per_item, 
                gauge_start, allow_none=False, 
                comma_dec_sep_ok=not comma_delimiter)
            # so fast only shows last step in progress bar
            importer.tmp_to_named_tbl(default_dd.con, default_dd.cur, 
                                      self.tbl_name, self.file_path, 
                                      progbar, feedback[mg.NULLED_DOTS])
        except Exception, e:
            importer.post_fail_tidy(progbar, default_dd.con, default_dd.cur)
            raise
        default_dd.cur.close()
        default_dd.con.commit()
        default_dd.con.close()
        progbar.SetValue(0)
        