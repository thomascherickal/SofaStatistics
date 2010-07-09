#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import codecs
import csv
import locale
import os
import pprint
import wx

import my_globals as mg
import lib
import my_exceptions
import dbe_plugins.dbe_sqlite as dbe_sqlite
import getdata
import importer

ROWS_TO_SAMPLE = 20

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

def get_dialect(file_path):
    debug = False
    try:
        csvfile = open(file_path) # don't use "U" - let it fail if necessary
            # and suggest an automatic cleanup.
        sniff_sample = csvfile.readline()
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sniff_sample)
        if debug: print(dialect)
    except IOError:
            raise Exception(u"Unable to find file \"%s\" for importing. "
                            u"Please check that file exists." % file_path)
    except Exception, e:
        raise Exception(u"Unable to open and sample csv file. "
                        u"Caused by error: %s" % lib.ue(e))
    return dialect
    
def get_avg_row_size(rows):
    """
    Measures length of string of comma separated values in bytes.
    Used for progress bar by measuring how many bytes we are through the file.
    Expects to get a list of strings or a dict of strings.
    If a dict, the final item could be a list if there are more items in the
        original row than the dict reader expected.
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
    
    def __init__(self, utf8_encoded_csv_data, dialect=csv.excel, **kwargs):
        # csv.py doesn't do Unicode; encode temporarily as UTF-8:
        try:
            self.csv_reader = csv.reader(utf8_encoded_csv_data, dialect=dialect, 
                                         **kwargs)
        except Exception, e:
            raise Exception(u"Unable to start internal csv reader. "
                            u"Caused by error: %s" % lib.ue(e))
    def __iter__(self):
        debug = False
        if debug: print(u"About to iterate through csv.reader")
        for row in self.csv_reader:
            if debug: print(u"Iterating through csv.reader")
            # decode UTF-8 back to Unicode, cell by cell:
            rowvals = []
            for val in row:
                try:
                    if val is None:
                        raise Exception(u"Missing value in csv file")
                    uval = val.decode("utf8")
                    rowvals.append(uval)
                except Exception, e:
                    raise Exception(u"Problem decoding values. "
                                    u"Caused by error: %s" % lib.ue(e))
            yield rowvals


class UnicodeCsvDictReader(object):
    
    def __init__(self, utf8_encoded_csv_data, dialect=csv.excel, **kwargs):
        # csv.py doesn't do Unicode; encode temporarily as UTF-8:
        try:
            self.csv_dictreader = csv.DictReader(utf8_encoded_csv_data,
                                                 dialect=dialect, **kwargs)
        except Exception, e:
            raise Exception(u"Unable to start internal csv reader. "
                            u"Caused by error: %s" % lib.ue(e))
        self.fieldnames = self.csv_dictreader.fieldnames
        
    def __iter__(self):
        """
        If required, decode UTF8-encoded byte string back to Unicode, dict pair 
            by pair.
        """
        for row in self.csv_dictreader:
            unicode_key_value_tups = []
            for key_val in row.items():
                uni_key_val = []
                for item in key_val:
                    if item is None:
                        raise Exception(u"Missing value in csv file")
                    if not isinstance(item, unicode):
                        item = item.decode("utf8")
                    uni_key_val.append(item)
                unicode_key_value_tups.append(tuple(uni_key_val))
            yield dict(unicode_key_value_tups)

def encode_lines_as_utf8(uni_lines):
    utf8_encoded_lines = []
    for uni_line in uni_lines:
        try:
            utf8_encoded_line = uni_line.encode("utf8")
            utf8_encoded_lines.append(utf8_encoded_line)
        except Exception, e:
            raise Exception(u"Unable to encode decoded data as utf8. "
                            u"Caused by error: %s" % lib.ue(e))
    return utf8_encoded_lines

def csv_to_utf8_byte_lines(file_path, encoding, n_lines=None):
    """
    The csv module infamously only accepts lines of bytes encoded as utf-8.
    NB we have no idea what the original encoding was or which computer or OS or 
        locale it was done on.  Eventually we could use chardet module to 
        sensibly guess but in meantime try up to two - local encoding then utf-8
    """
    debug = False
    try:
        f = codecs.open(file_path, encoding=encoding)
    except IOError, e:
        raise Exception(u"Unable to open file for re-encoding. "
                        u"Caused by error: %s" % lib.ue(e))
    # this bit can fail even if the open succeeded
    uni_lines = []
    for i, line in enumerate(f, 1):
        uni_lines.append(line)
        if n_lines is not None:
            if i >= n_lines:
                break
    utf8_byte_lines = encode_lines_as_utf8(uni_lines)
    if debug:
        print(repr(utf8_byte_lines))
    return utf8_byte_lines


class DlgImportDisplay(wx.Dialog):
    
    def __init__(self, parent, content, encoding, n_lines):
        wx.Dialog.__init__(self, parent=parent, 
                           title=_("Contents look correct?"), 
                           style=wx.CAPTION|wx.SYSTEM_MENU)
        self.parent = parent
        panel = wx.Panel(self)
        szr_main = wx.BoxSizer(wx.VERTICAL)
        szr_btns = wx.FlexGridSizer(rows=1, cols=3, hgap=5, vgap=0)
        szr_btns.AddGrowableCol(1,2) # idx, propn
        lbl_instructions = wx.StaticText(panel, -1, _("Do the contents look "
            "correct? If not, SOFA will try again with a different format "
            "(encoding)"))
        lbl_encoding = wx.StaticText(panel, -1, _("Encoding: %s" % encoding))
        content_height = 25*n_lines
        content_height = 300 if content_height > 300 else content_height
        txt_content = wx.TextCtrl(panel, -1, content, 
                                  size=(500,content_height), 
                                  style=wx.TE_MULTILINE)
        btn_not_ok = wx.Button(panel, -1, _("Not OK"))
        btn_not_ok.Bind(wx.EVT_BUTTON, self.on_btn_not_ok)
        btn_cancel = wx.Button(panel, wx.ID_CANCEL)
        btn_cancel.Bind(wx.EVT_BUTTON, self.on_btn_cancel)
        btn_ok = wx.Button(panel, -1, _("Content OK"))
        btn_ok.Bind(wx.EVT_BUTTON, self.on_btn_ok)
        szr_btns.Add(btn_not_ok, 0)
        szr_btns.Add(btn_cancel, 0)
        szr_btns.Add(btn_ok, 0)
        szr_main.Add(lbl_instructions, 0, wx.ALL, 10)
        szr_main.Add(lbl_encoding, 0, wx.ALL, 10)
        szr_main.Add(txt_content, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szr_main.Add(szr_btns, 0, wx.GROW|wx.ALL, 10)
        panel.SetSizer(szr_main)
        szr_main.SetSizeHints(self)
        self.Layout()
        
    def on_btn_not_ok(self, event):
        self.Destroy()
        self.SetReturnCode(mg.RET_ENCODING_NOT_OK)
        
    def on_btn_cancel(self, event):
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL)
        
    def on_btn_ok(self, event):
        self.Destroy()
        self.SetReturnCode(mg.RET_ENCODING_OK)


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
        
    def assess_sample(self, reader, progbar, steps_per_item, keep_importing):
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
                if keep_importing == set([False]):
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
                                orig_fld_name, orig_fld_names, allow_none=False)
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

    def get_utf8_encoded_csv_sample(self):
        """
        Get correctly encoded data.  Try encoding until get first successful
            sample. Give user choice to use it or keep going.
        Windows is always trickier - less likely to be utf-8 from the start. 
            Many of these encodings will "work" even though they are not the 
            encoding used to create them in the first place. That's why the user 
            is given a choice. Could use chardets somehow as well.
        """
        debug = False
        local_encoding = locale.getpreferredencoding()
        if mg.PLATFORM == mg.WINDOWS:
            encodings = [local_encoding, "cp1252", "iso-8859-1", "cp1257", 
                         "utf8", "big5"]
        else:
            encodings = [local_encoding, "utf8", "iso-8859-1", "cp1252", 
                         "cp1257", "big5"]
        ok_encoding = False
        rejected_encoding = False
        for encoding in encodings:
            try:
                if self.has_header:
                    utf8_encoded_csv_sample = \
                                csv_to_utf8_byte_lines(self.file_path, encoding, 
                                                       n_lines=ROWS_TO_SAMPLE+1)
                else:
                    utf8_encoded_csv_sample = \
                                csv_to_utf8_byte_lines(self.file_path, encoding, 
                                                       n_lines=ROWS_TO_SAMPLE)
                # give user choice to reject encoding
                decoded_lines = []
                for line in utf8_encoded_csv_sample:
                    decoded_lines.append(line.decode("utf8"))
                dlg = DlgImportDisplay(parent=self.parent, 
                                       content=u"".join(decoded_lines),
                                       encoding=encoding, 
                                       n_lines=len(decoded_lines))
                ret = dlg.ShowModal()
                if ret == mg.RET_ENCODING_OK:
                    ok_encoding = True
                    break
                elif ret == wx.ID_CANCEL:
                    rejected_encoding = True
                    break
                else:
                    rejected_encoding = True # but keep trying if possible
            except Exception, e:
                continue
        if not ok_encoding:
            if rejected_encoding:
                raise my_exceptions.ImportEncodingRejected
            else:
                raise Exception(u"No suitable encodings were found")
        return encoding, utf8_encoded_csv_sample

    def get_init_csv_details(self, dialect):
        """
        Get various details about csv from a sample.
        """
        debug = False
        try:
            encoding, utf8_encoded_csv_sample = \
                                            self.get_utf8_encoded_csv_sample()
            # get field names
            if self.has_header:
                if debug: print(u"About to get dictreader")
                tmp_reader = UnicodeCsvDictReader(utf8_encoded_csv_sample, 
                                                  dialect=dialect)
                if debug: print(u"Got dictreader")
                orig_names = tmp_reader.fieldnames
                if debug: print(u"Got field names from dictreader")
                ok_fld_names = importer.process_fld_names(orig_names)
            else:
                # get number of fields from first row
                if debug: print(u"About to get plain reader")
                tmp_reader = UnicodeCsvReader(utf8_encoded_csv_sample, 
                                              dialect=dialect)
                if debug: print(u"Got plain reader")
                for row in tmp_reader:
                    if debug:
                        print(u"Looking at first row") 
                        print(row)
                    ok_fld_names = [mg.NEXT_FLD_NAME_TEMPLATE % (x+1,) 
                                    for x in range(len(row))]
                    break
            if debug: print("Got field names")
            row_size = self.get_avg_row_size(tmp_reader)
            # If not enough field_names, will use None as key for a list of any 
            # extra values.
        except my_exceptions.ImportEncodingRejected:
            raise
        except csv.Error, e:
            lib.safe_end_cursor()
            if lib.ue(e).startswith("new-line character seen in unquoted "
                                    "field"):
                self.fix_text()
                raise my_exceptions.ImportNeededFixException
            else:
                raise
        except Exception, e:
            lib.safe_end_cursor()
            raise Exception(u"Unable to create reader for file. "
                            u"Caused by error: %s" % lib.ue(e))
        return encoding, ok_fld_names, row_size

    def import_content(self, progbar, keep_importing, lbl_feedback):
        """
        Get field types dict.  Use it to test each and every item before they 
            are added to database (after adding the records already tested).
        Add to disposable table first and if completely successful, rename
            table to final name.
        """
        debug = False
        wx.BeginBusyCursor()
        if debug: print(u"About to get dialect")
        dialect = get_dialect(self.file_path)
        if debug: print(u"Got \"%s\" dialect successfully" % dialect)
        try:
            encoding, ok_fld_names, row_size = \
                                            self.get_init_csv_details(dialect)
        except my_exceptions.ImportNeededFixException:
            lib.safe_end_cursor()
            return
        except my_exceptions.ImportEncodingRejected:
            lib.safe_end_cursor()
            raise Exception(u"Unable to process csv file unless a format "
                            u"(encoding) is selected.")
        except Exception, e:
            lib.safe_end_cursor()
            raise Exception(u"Unable to get initial csv details. "
                            u"Caused by error: %s" % lib.ue(e))
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
                            u"Caused by error: %s" % lib.ue(e))
        try:
            utf8_encoded_csv_data = csv_to_utf8_byte_lines(self.file_path, 
                                                           encoding)
            reader = UnicodeCsvDictReader(utf8_encoded_csv_data, 
                                          dialect=dialect, 
                                          fieldnames=ok_fld_names)
        except Exception, e:
            lib.safe_end_cursor()
            raise Exception(u"Unable to create reader for file. "
                            u"Caused by error: %s" % lib.ue(e)) 
        default_dd = getdata.get_default_db_dets()
        sample_n = ROWS_TO_SAMPLE if ROWS_TO_SAMPLE <= rows_n else rows_n
        items_n = rows_n + sample_n + 1 # 1 is for the final tmp to named step
        steps_per_item = importer.get_steps_per_item(items_n)
        try:
            orig_fld_names, fld_types, sample_data = \
                            self.assess_sample(reader, progbar, steps_per_item, 
                                               keep_importing)
        except Exception, e:
            importer.post_fail_tidy(progbar, default_dd.con, default_dd.cur, e)
            raise
        # NB reader will be at position ready to access records after sample
        remaining_data = list(reader) # must be a list not a reader or can't 
            # start again from beginning of data (e.g. if correction made)
        gauge_start = steps_per_item*sample_n
        try:
            nulled_dots = importer.add_to_tmp_tbl(
                                default_dd.con, default_dd.cur, self.file_path, 
                                self.tbl_name, self.has_header, 
                                ok_fld_names, orig_fld_names, fld_types, 
                                sample_data, sample_n, remaining_data, 
                                progbar, steps_per_item, gauge_start, 
                                keep_importing, allow_none=False)
            # so fast only shows last step in progress bar
            importer.tmp_to_named_tbl(default_dd.con, default_dd.cur, 
                                      self.tbl_name, self.file_path, 
                                      progbar, nulled_dots)
        except Exception, e:
            importer.post_fail_tidy(progbar, default_dd.con, default_dd.cur, e)
            raise
        default_dd.cur.close()
        default_dd.con.commit()
        default_dd.con.close()
        progbar.SetValue(0)
        