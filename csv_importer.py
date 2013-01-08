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
import getdata
import importer

ROWS_TO_SHOW_USER = 10 # need to show enough to choose encoding

ERR_NO_DELIM = u"Could not determine delimiter"
ERR_NEW_LINE_IN_UNQUOTED = u"new-line character seen in unquoted field"
ERR_NEW_LINE_IN_STRING = u"newline inside string" #  # Shouldn't happen now I 
# process complete file in csv2utf8_bytelines() rather than trying to limit to 
# n lines for sample to display etc. Would sometimes break inside a string.
# Have to wait for cvs reader stage to be able to reliably tell when a line 
# break is between lines and not within a field.
ESC_DOUBLE_QUOTE = "\x14" # won't occur naturally and doesn't break csv module
# Shift Out control character in ASCII 
"""
Support for unicode is lacking from the Python 2 series csv module and quite a
    bit of wrapping is required to work around it.  Must wait for Python 3 or
    spend a lot more time on this. But it still put Dörthe in correctly ;-).
See http://docs.python.org/library/csv.html#examples
http://bugs.python.org/issue1606092
"""

class MyDialect(csv.Dialect):
    """
    Enough to cope with single column csvs (with or without 
        commas as decimal separators)
    """
    delimiter = ';'
    quotechar = '"'
    doublequote = True
    skipinitialspace = False
    lineterminator = '\n'
    quoting = csv.QUOTE_MINIMAL

def consolidate_line_seps(mystr):
    for sep in ["\n", "\r", "\r\n"]:
        mystr = mystr.replace(sep, os.linesep)
    return mystr

def ok_delimiter(delimiter):
    try:
        ord_delimiter = ord(delimiter)
        if not 31 < ord_delimiter < 127:
            raise Exception(u"The auto-detected delimiter is unprintable.") 
    except Exception:
        raise Exception(u"Unable to assess the auto-detected delimiter")

def has_comma_delim(dialect):
    comma_delimiter = (dialect.delimiter.decode("utf8") == u",")
    return comma_delimiter

def get_possible_encodings(file_path):
    """
    Get list of encodings which potentially work for a sample. Fast enough 
        not to have to sacrifice code readability etc for performance.
    """
    debug = False
    local_encoding = locale.getpreferredencoding()
    if mg.PLATFORM == mg.WINDOWS:
        encodings = ["cp1252", "iso-8859-1", "cp1257", "utf-8", "utf-16", 
                     "big5"]
    else:
        encodings = ["utf-8", "iso-8859-1", "cp1252", "cp1257", "utf-16", 
                     "big5"]
    if local_encoding.lower() not in encodings:
        encodings.insert(0, local_encoding.lower())
    possible_encodings = []
    for encoding in encodings:
        if debug: print("About to test encoding: %s" % encoding)
        try:
            unused = csv2utf8_bytelines(file_path, encoding)
            possible_encodings.append(encoding)
        except Exception:
            continue
    return possible_encodings

def get_sample_rows(file_path):
    debug = False
    try:
        f = open(file_path) # don't use "U" - let it fail if necessary
            # and suggest an automatic cleanup.
        sample_rows = []
        for i, row in enumerate(f):
            if i < 20:
                if debug: print(row)
                sample_rows.append(row)
    except IOError:
            raise Exception(u"Unable to find file \"%s\" for importing. "
                            u"Please check that file exists." % file_path)
    except Exception, e:
        raise Exception(u"Unable to open and sample csv file. "
                        u"\nCaused by error: %s" % lib.ue(e))
    return sample_rows

def get_dialect(sniff_sample):
    debug = False
    try:
        sniffer = csv.Sniffer()
        try:
            dialect = sniffer.sniff(sniff_sample)
        except Exception, e:
            if lib.ue(e).startswith(ERR_NO_DELIM):
                dialect = MyDialect() # try a safe one of my own
            else:
                raise
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
    except Exception, e:
        raise Exception(u"Unable to open and sample csv file. "
                        u"\nCaused by error: %s" % lib.ue(e))
    return dialect

def fix_text(file_path):
    "Should never be called in headless mode"
    ret = wx.MessageBox(_("The file needs new lines standardised first. "
                         "Can SOFA Statistics make a tidied copy for you?"), 
                         caption=_("FIX TEXT?"), style=wx.YES_NO)
    if ret == wx.YES:
        new_file = make_tidied_copy(file_path)
        wx.MessageBox(_(u"Please check tidied version \"%s\" "
                        u"before importing/re-importing. May have line "
                        u"breaks in the wrong places.") % new_file)
    else:
        wx.MessageBox(_("Unable to import file in current form"))

def make_tidied_copy(path):
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

def has_header_row(file_path, sample_rows, delim, comma_dec_sep_ok=False):
    """
    Will return True if nothing but unambiguous strings in first row and 
        anything in other rows that is probably not be a string e.g. a number 
        or a date. Empty strings are not proof of anything so are skipped.
    OK if this fails - we must leave it to the user to identify if a header row 
        or not (and to choose a possible encoding).
    """
    if len(sample_rows) < 2: # a header row needs a following row to be a header
        return False
    delim_str = delim.encode("utf-8") # might fail but not worth expensive 
    # process of working out actual decoding if this fails and OK if fails - 
    # just leave has header row to default.
    if delim_str is None:
        raise Exception(u"Unable to decode import file so header row can be "
                        u"identified")
    first_row_vals = sample_rows[0].split(delim_str)
    second_row_vals = sample_rows[1].split(delim_str)
    row1_types = [lib.get_val_type(val, comma_dec_sep_ok) 
                  for val in first_row_vals]
    row2_types = [lib.get_val_type(val, comma_dec_sep_ok) 
                  for val in second_row_vals]
    str_type = mg.VAL_STRING
    empty_type = mg.VAL_EMPTY_STRING
    non_str_types = [mg.VAL_DATE, mg.VAL_NUMERIC]
    return importer.has_header_row(row1_types, row2_types, str_type, empty_type, 
                                   non_str_types)

def get_prob_has_hdr(sample_rows, file_path, dialect):
    """
    Method used in csv rejects some clear-cut cases where there is a header - 
        ignores any columns which are of mixed type - takes them out of 
        contention. If none survive, always assumes no header as never has any 
        columns to test.
    Need an additional test looking for all strings in top, and anything below 
        that is numeric or a date.
    Must always return a result no matter what even if we don't know and just 
        assume no header i.e. False.
    """
    prob_has_hdr = False
    try:
        sniffer = csv.Sniffer()
        sample_rows = [x.strip("\n") for x in sample_rows]
        hdr_sample = "\n".join(sample_rows)
        prob_has_hdr = sniffer.has_header(hdr_sample)
    except csv.Error, e:
        lib.safe_end_cursor()
        if lib.ue(e).startswith(ERR_NO_DELIM):
            pass # I'll have to try it myself
        elif lib.ue(e).startswith(ERR_NEW_LINE_IN_UNQUOTED):
            fix_text(file_path)
    except Exception, e: # If everything else succeeds don't let this stop things
        pass
    try:
        if not prob_has_hdr:
            # test it myself
            delim = dialect.delimiter.decode("utf8")
            comma_dec_sep_ok = not has_comma_delim(dialect)
            prob_has_hdr = has_header_row(file_path, sample_rows, delim, 
                                          comma_dec_sep_ok)        
    except Exception, e:
        pass
    return prob_has_hdr

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
        row_str = u",".join(vals)
        row_size = len(row_str)
        if debug: print(row, row_str, row_size)
        #if debug: print(row_size)
        size += row_size
    if i is None:
        avg_row_size = 10 # if only one then can be almost anything - progress
            # will flash by any way
    else:
        avg_row_size = float(size)/i
    return avg_row_size


# http://docs.python.org/library/csv.html
class UnicodeCsvReader(object):
    """
    Sometimes preferable to dict reader because doesn't consume first row.
    Dict readers do when field names not supplied.
    Also copes with duplicate field names rather than returning a dict with one 
        value per unique field value for the first row (shorter than original 
        sequence).
    """
    def __init__(self, utf8_encoded_csv_data, dialect=csv.excel, **kwargs):
        # csv.py doesn't do Unicode; encode temporarily as UTF-8:
        debug = False
        try:
            dialect.escapechar = ESC_DOUBLE_QUOTE
            if debug: print(dialect.delimiter)
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
        csv file will be used as the field names. Allows duplicates.
        http://docs.python.org/library/csv.html
    The first row will be consumed and no longer be available.
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

def get_decoded_unilines(file_path, bom2rem, encoding):
    """
    Going to need to trim, decode whole file, replace \r with \n, 
        split into lines.
    An expensive process given we only want a finite number of lines but no 
        alternative if boms in text - they make the file mess up returning 
        lines broken at the correct places. Sometimes a line is just
        "\x00" (the nul byte).
    """
    debug = False
    byte_content = open(file_path, "rb").read()
    len2rem = len(bom2rem)
    byte_content = byte_content[len2rem:]
    decoded_file = byte_content.decode(encoding)
    if debug: print(repr(decoded_file))
    tidied = decoded_file.replace("\r", "")
    if debug: print(repr(tidied))
    split_lines = tidied.split("\n")
    return split_lines
    
def csv2utf8_bytelines(file_path, encoding, strict=True):
    """
    The csv module infamously only accepts lines of bytes encoded as utf-8.
    Need to do the escaping of double quotes here so we can deal with a unicode
        string and not a byte string.
    NB we have no idea what the original encoding was or which computer or OS or 
        locale it was done on. Eventually we could use chardet module to 
        sensibly guess but in meantime try several - including the local 
        encoding then utf-8 etc.
    Order matters. '\xff\xfe' starts utf-16 BOM but also starts 
        '\xff\xfe\x00\x00' the utf-32 BOM. Do the larger one first.
    From codecs:
    
    BOM_UTF8 = '\xef\xbb\xbf'

    BOM_UTF32 = '\xff\xfe\x00\x00'
    BOM64_LE = '\xff\xfe\x00\x00'
    BOM_UTF32_LE = '\xff\xfe\x00\x00'
    
    BOM_UTF16_BE = '\xfe\xff'
    BOM32_BE = '\xfe\xff'
    BOM_BE = '\xfe\xff'
    
    BOM_UTF16 = '\xff\xfe'
    BOM = '\xff\xfe'
    BOM_LE = '\xff\xfe'
    BOM_UTF16_LE = '\xff\xfe'
    BOM32_LE = '\xff\xfe'
    
    BOM_UTF32_BE = '\x00\x00\xfe\xff'
    BOM64_BE = '\x00\x00\xfe\xff'
    We used to have the option of limiting the number of lines returned. Buggy 
        because line breaks can happen inside csv lines. Only safe to restrict 
        lines once passed through csv readers.
    """
    debug = False
    unilines = []
    # if bom available, use or reject supplied encoding according to bom
    try:
        # should be super fast and only once or twice per entire CSV file
        init_content = open(file_path, "rb").read(20) # 20s enough for length of longest bom
        boms = [(codecs.BOM_UTF8, ["utf-8"]), # order matters - see above
                (codecs.BOM_UTF32, ["utf-32"]), 
                (codecs.BOM_UTF16_BE, ["utf-16"]),
                (codecs.BOM_UTF16, ["utf-16"]), 
                (codecs.BOM_UTF32_BE, ["utf-32"]),]
        for bom2rem, encodings2try in boms:
            if init_content.startswith(bom2rem):
                if encoding in encodings2try:
                    # Going to need to trim, decode whole file,
                    # replace \r with \n, split into lines, take n lines.
                    if debug: wx.MessageBox(u"Good encoding: %s" % encoding)
                    decoded_unilines = get_decoded_unilines(file_path, bom2rem,
                                                            encoding)
                    unilines.extend(decoded_unilines)
                    break
                else:
                    raise Exception(u"Found bom for a different encoding. "
                                 u"Cannot use the encoding supplied to decode.")
    except Exception, e:
        raise Exception(u"Unable to recode CSV content. Orig error: %s" % 
                        lib.ue(e))
    # no boms to guide us - try what we have and see if it "works".
    # Note - may get something malformed which fails after the file read when we 
    # try to iterate through lines.
    if not unilines:
        try:
            errors = "strict" if strict else "replace"
            f = codecs.open(file_path, encoding=encoding, errors=errors)
        except IOError, e:
            raise Exception(u"Unable to open file for re-encoding. "
                            u"\nCaused by error: %s" % lib.ue(e))
        for line in f:
            unilines.append(line)
    if not unilines:
        raise Exception(u"No lines in CSV to process")
    escaped_unilines = escape_double_quotes_in_uni_lines(unilines)
    utf8_bytelines = encode_lines_as_utf8(escaped_unilines)
    if debug:
        print(repr(utf8_bytelines))
        wx.MessageBox("Adding %s to list" % encoding)
    return utf8_bytelines


class DlgImportDisplay(wx.Dialog):
    
    """
    Show user csv sample assuming first encoding and auto-detected delimiter.
    Let user change encoding and delimiter until happy.
    Also select whether data has a header or not. 
    """
    
    def __init__(self, parent, file_path, dialect, encodings, probably_has_hdr,
                 retvals):
        wx.Dialog.__init__(self, parent=parent, 
                           title=_("Contents look correct?"), 
                           style=wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX|\
                           wx.RESIZE_BORDER|wx.SYSTEM_MENU|wx.CAPTION|\
                           wx.CLIP_CHILDREN)
        debug = False
        lib.safe_end_cursor() # needed for Mac
        self.parent = parent
        self.file_path = file_path
        self.dialect = dialect
        self.encoding = encodings[0]
        self.retvals = retvals
        panel = wx.Panel(self)
        szr_main = wx.BoxSizer(wx.VERTICAL)
        szr_options = wx.BoxSizer(wx.HORIZONTAL)
        szr_header = wx.BoxSizer(wx.VERTICAL)
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
        self.chk_has_header.SetValue(probably_has_hdr)
        lbl_hdr_warning = wx.StaticText(panel, -1, _(u"Note - SOFA cannot "
                                            u"handle multiple header rows."))
        szr_options.Add(lbl_delim, 0, wx.RIGHT, 5)
        szr_options.Add(self.txt_delim, 0, wx.RIGHT, 10)
        szr_options.Add(lbl_encoding, 0, wx.RIGHT, 5)
        szr_options.Add(self.drop_encodings, 0, wx.RIGHT, 10)
        szr_header.Add(self.chk_has_header, 0)
        szr_header.Add(lbl_hdr_warning, 0)
        szr_options.Add(szr_header, 0)
        content, content_height = self.get_content()
        if debug: print(content)
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
        """
        For display in GUI dlg - so makes sense to use the encoding the user has 
            selected - whether or not it is a good choice.
        Have to get whole file even though for this part we only need the first 
            few lines. No reliable way of breaking into lines pre-csv reader so
            happens at last step.
        """
        try:
            self.utf8_encoded_csv_sample = csv2utf8_bytelines(self.file_path, 
                                                              self.encoding)
        except Exception, e:
            msg = (u"Unable to display the first lines of this CSV file using "
                   u"the first selected encoding (%s).\n\nOrig error: %s" % 
                   (self.encoding, lib.ue(e)))
            return msg, 100
        try:
            # don't use dict reader - consumes first row when we don't know
            # field names. And if not a header, we might expect some values to
            # be repeated, which means the row dicts could have fewer fields
            # than there are actual fields.
            tmp_reader = UnicodeCsvReader(self.utf8_encoded_csv_sample, 
                                          dialect=self.dialect)
        except csv.Error, e:
            lib.safe_end_cursor()
            if lib.ue(e).startswith(ERR_NEW_LINE_IN_UNQUOTED):
                fix_text(self.file_path)
                raise my_exceptions.ImportNeededFix
            else:
                raise
        except Exception, e:
            lib.safe_end_cursor()
            raise Exception(u"Unable to create reader for file. "
                            u"\nCaused by error: %s" % lib.ue(e))
        try:
            i = 0
            strdata = []
            for i, row in enumerate(tmp_reader, 1):
                if row:  # exclude empty rows
                    strdata.append(row)
                    if len(strdata) >= ROWS_TO_SHOW_USER:
                        break
        except csv.Error, e:
            lib.safe_end_cursor()
            if lib.ue(e).startswith(ERR_NEW_LINE_IN_STRING):
                raise Exception(u"Problem with row %s - line break in the "
                                u"middle of a field." % str(i+1))
            else:
                raise
        content, content_height = importer.get_content_dets(strdata)
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
    
    def __init__(self, parent, file_path, tblname, headless, 
                 headless_has_header, supplied_encoding):
        self.parent = parent
        importer.FileImporter.__init__(self, self.parent, file_path, tblname, 
                                       headless, headless_has_header, 
                                       supplied_encoding)
        self.ext = u"CSV"
        
    def assess_sample(self, reader, progbar, steps_per_item, import_status, 
                      comma_delimiter, faulty2missing_fld_list):
        """
        Assess data sample to identify field types based on values in fields.
        If a field has mixed data types will define as string.
        Returns ok_fldnames, fldtypes, sample_data.
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
                continue # skip first line
            bolhas_rows = True
            # process row
            sample_data.append(row) # include Nones even if going to change to 
                # empty strings or whatever later.
            gauge_val = i*steps_per_item
            progbar.SetValue(gauge_val)
            i2break = (ROWS_TO_SHOW_USER if self.has_header 
                       else ROWS_TO_SHOW_USER - 1)
            if i == i2break:
                break
        fldtypes = []
        ok_fldnames = lib.get_unique_fldnames(reader.fieldnames)
        for ok_fldname in ok_fldnames:
            fldtype = importer.assess_sample_fld(sample_data, self.has_header,
                                    ok_fldname, ok_fldnames, 
                                    faulty2missing_fld_list, allow_none=False,
                                    comma_dec_sep_ok=not comma_delimiter)
            fldtypes.append(fldtype)
        fldtypes = dict(zip(ok_fldnames, fldtypes))
        if not bolhas_rows:
            raise Exception(u"No data to import")
        return ok_fldnames, fldtypes, sample_data
    
    def get_avg_row_size(self, tmp_reader):
        """
        Expects to get a list of strings or a dict of strings.
        If a dict, the final item could be a list if there are more items in the
            original row than the dict reader expected.
        """
        return get_avg_row_size(rows=tmp_reader)
                      
    def get_sample_with_dets(self):
        """
        Get correctly encoded data. Try encoding until get first successful
            sample. Give user choice to use it or keep going.
        Also get details -- dialect, encoding, has_header.
        Windows is always trickier - less likely to be utf-8 from the start. 
            Many of these encodings will "work" even though they are not the 
            encoding used to create them in the first place. That's why the user 
            is given a choice. Could use chardets somehow as well.
        """
        sample_rows = get_sample_rows(self.file_path)
        sniff_sample = "".join(sample_rows) # not u"" but ""
            # otherwise error: "delimiter" must be an 1-character string
        dialect = get_dialect(sniff_sample)
        if self.headless and (self.supplied_encoding is None and 
                         self.headless_has_header is None):
            raise Exception("Must supply encoding and header status if "
                            "running headless")
        if self.headless:
            encoding = self.supplied_encoding
            has_header = self.headless_has_header
            utf8_encoded_csv_sample = csv2utf8_bytelines(self.file_path,
                                                         encoding)
        else:
            probably_has_hdr = get_prob_has_hdr(sample_rows, self.file_path, 
                                                dialect)
            encodings = get_possible_encodings(self.file_path)
            if not encodings:
                raise Exception(_("Data could not be processed using available "
                                  "encodings"))
            # give user choice to change encoding, delimiter, and say if has header
            retvals = [] # populate inside dlg
            dlg = DlgImportDisplay(self.parent, self.file_path, dialect, 
                                   encodings, probably_has_hdr, retvals)
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
            lib.safe_end_cursor()
            raise
        except Exception, e:
            lib.safe_end_cursor()
            raise Exception(u"Unable to get sample of csv with details. "
                            u"\nCaused by error: %s" % lib.ue(e))
        if not self.headless:
            wx.BeginBusyCursor()
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
            ok_fldnames = importer.process_fldnames(tmp_reader.fieldnames,
                                                    self.headless)
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
                ok_fldnames = [mg.NEXT_FLDNAME_TEMPLATE % (x+1,) 
                               for x in range(len(row))]
                break
        if not ok_fldnames:
            raise Exception(u"Unable to get ok field names")
        row_size = self.get_avg_row_size(tmp_reader)
        return dialect, encoding, ok_fldnames, row_size

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
        if not self.headless:
            wx.BeginBusyCursor()
        try:
            (dialect, encoding, 
             ok_fldnames, row_size) = self.get_init_csv_details()
        except my_exceptions.ImportNeededFix:
            lib.safe_end_cursor()
            return
        except my_exceptions.ImportConfirmationRejected, e:
            lib.safe_end_cursor()
            raise
        except Exception, e:
            lib.safe_end_cursor()
            raise Exception(u"Unable to get initial csv details. "
                            u"\nCaused by error: %s" % lib.ue(e))
        comma_delimiter = has_comma_delim(dialect)
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
            utf8_encoded_csv_data = csv2utf8_bytelines(self.file_path, 
                                                       encoding, strict=False)
            # we supply field names so will start with first row
            reader = UnicodeCsvDictReader(utf8_encoded_csv_data, 
                                          dialect=dialect, 
                                          fieldnames=ok_fldnames)
        except Exception, e:
            lib.safe_end_cursor()
            raise Exception(u"Unable to create reader for file. "
                            u"\nCaused by error: %s" % lib.ue(e)) 
        default_dd = getdata.get_default_db_dets()
        sample_n = min(ROWS_TO_SHOW_USER, rows_n)
        items_n = rows_n + sample_n + 1 # 1 is for the final tmp to named step
        steps_per_item = importer.get_steps_per_item(items_n)
        try:
            (ok_fldnames, fldtypes, 
             sample_data) = self.assess_sample(reader, progbar, steps_per_item, 
                                               import_status, comma_delimiter, 
                                               faulty2missing_fld_list)
            # NB reader will be at position ready to access records after sample
            data = sample_data + list(reader) # must be a list not a reader or 
                # can't start again from start of data (e.g. if correction made)
            gauge_start = steps_per_item*sample_n
            feedback = {mg.NULLED_DOTS: False}
            importer.add_to_tmp_tbl(feedback, import_status, default_dd.con, 
                default_dd.cur, self.file_path, self.tblname, self.has_header, 
                ok_fldnames, fldtypes, faulty2missing_fld_list, data, progbar, 
                steps_per_item, gauge_start, allow_none=False, 
                comma_dec_sep_ok=not comma_delimiter)
            # so fast only shows last step in progress bar
            importer.tmp_to_named_tbl(default_dd.con, default_dd.cur, 
                                      self.tblname, self.file_path, 
                                      progbar, feedback[mg.NULLED_DOTS],
                                      self.headless)
        except Exception, e:
            importer.post_fail_tidy(progbar, default_dd.con, default_dd.cur)
            raise
        default_dd.cur.close()
        default_dd.con.commit()
        default_dd.con.close()
        progbar.SetValue(0)
        