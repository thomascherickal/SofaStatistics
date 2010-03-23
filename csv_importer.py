#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import codecs
import csv
import os
import wx

import my_globals as mg
import lib
import dbe_plugins.dbe_sqlite as dbe_sqlite
import getdata
import importer
from my_exceptions import ImportCancelException
from my_exceptions import NewLineInUnquotedException

ROWS_TO_SAMPLE = 500 # fast enough to sample quite a few

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
        csvfile = open(file_path) # don't use "U" - let it 
            # fail if necessary and suggest an automatic cleanup
        sniff_sample = csvfile.read(3072) # 1024 not enough if many fields
        # if too small, will return error about newline inside string
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sniff_sample)
        #has_header = sniffer.has_header(sniff_sample)
        if debug: print(dialect)
    except IOError:
            raise Exception, (u"Unable to find file \"%s\" for importing. "
                              u"Please check that file exists." % file_path)
    except csv.Error, e:
        if unicode(e).startswith("new-line character seen in unquoted field"):
            raise NewLineInUnquotedException
        else:
            raise Exception, unicode(e)
    except Exception, e:
        raise Exception, "Unable to open and sample csv file. " + \
            "Orig error: %s" % e
    return dialect
    
    
class CsvImporter(importer.FileImporter):
    """
    Import csv file into default SOFA SQLite database.
    Needs to identify data types to ensure only consistent data in a field.
    Adds unique index id so can identify unique records with certainty.
    """
    
    def __init__(self, parent, file_path, tbl_name):
        importer.FileImporter.__init__(self, parent, file_path, tbl_name)
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
                    raise ImportCancelException
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
        orig_fld_names = []
        fld_types = []
        for orig_fld_name in reader.fieldnames:
            orig_fld_names.append(orig_fld_name)
            fld_type = importer.assess_sample_fld(sample_data, orig_fld_name)
            fld_types.append(fld_type)
        fld_types = dict(zip(reader.fieldnames, fld_types))
        if not bolhas_rows:
            raise Exception, "No data to import"
        return orig_fld_names, fld_types, sample_data
    
    def get_avg_row_size(self, tmp_reader):
        # loop through at most 5 times
        i = 0
        size = 0
        for row in tmp_reader:
            try:
                values = row.values()
            except AttributeError:
                values = row
            vals = [lib.none2empty(x) for x in values]
            size += len(", ".join(vals))
            i += 1
            if i == 5:
                break
        avg_row_size = float(size)/i
        return avg_row_size

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
        ret = wx.MessageBox(_("The file needs new lines standardised first."
                        " Can SOFA Statistics make a tidied copy for you?"), 
                        caption=_("FIX TEXT?"), style=wx.YES_NO)
        if ret == wx.YES:
            new_file = self.make_tidied_copy(self.file_path)
            wx.MessageBox(_("Please check tidied version \"%s\" "
                            "before importing.  May have line "
                            "breaks in the wrong places.") % new_file)
        else:
            wx.MessageBox(_("Unable to import file in current form"))        

    def import_content(self, progbar, keep_importing, lbl_feedback):
        """
        Get field types dict.  Use it to test each and every item before they 
            are added to database (after adding the records already tested).
        Add to disposable table first and if completely successful, rename
            table to final name.
        """
        debug = False
        wx.BeginBusyCursor()
        try:
            dialect = get_dialect(self.file_path)
        except NewLineInUnquotedException:
            self.fix_text()
            return
        try:
            csvfile = open(self.file_path) # not "U" - insist on _one_ type of 
                # line break
            # get field names
            if self.has_header:
                tmp_reader = csv.DictReader(csvfile, dialect=dialect)
                orig_names = tmp_reader.fieldnames
                ok_fld_names = importer.process_fld_names(orig_names)
            else:
                # get number of fields
                tmp_reader = csv.reader(csvfile, dialect=dialect)
                for row in tmp_reader:
                    if debug: print(row)
                    ok_fld_names = [mg.NEXT_FLD_NAME_TEMPLATE % (x+1,) 
                                    for x in range(len(row))]
                    break
                csvfile.seek(0)
            # estimate number of rows (only has to be good enough for progress)
            tot_size = os.path.getsize(self.file_path)
            row_size = self.get_avg_row_size(tmp_reader)
            if debug:
                print("tot_size: %s" % tot_size)
                print("row_size: %s" % row_size)
            csvfile.seek(0)
            rows_n = float(tot_size)/row_size            
            reader = csv.DictReader(csvfile, dialect=dialect, 
                                    fieldnames=ok_fld_names)
        except csv.Error, e:
            lib.safe_end_cursor()
            if unicode(e).startswith("new-line character seen in unquoted"
                                     " field"):
                self.fix_text()
                return
            else:
                raise Exception, unicode(e)
        except Exception, e:
            lib.safe_end_cursor()
            raise Exception, "Unable to create reader for file. " + \
                "Orig error: %s" % e
        con, cur, unused, unused, unused, unused, unused = \
            getdata.get_default_db_dets()
        sample_n = ROWS_TO_SAMPLE if ROWS_TO_SAMPLE <= rows_n else rows_n
        items_n = rows_n + sample_n + 1 # 1 is for the final tmp to named step
        steps_per_item = importer.get_steps_per_item(items_n)
        orig_fld_names, fld_types, sample_data = self.assess_sample(reader, 
                                    progbar, steps_per_item, keep_importing)
        # NB reader will be at position ready to access records after sample
        remaining_data = list(reader) # must be a list not a reader or can't 
            # start again from beginning of data (e.g. if correction made)
        gauge_start = steps_per_item*sample_n
        try:
            nulled_dots = importer.add_to_tmp_tbl(con, cur, self.file_path, 
                        self.tbl_name, ok_fld_names, orig_fld_names, 
                        fld_types, sample_data, sample_n, remaining_data, 
                        progbar, steps_per_item, gauge_start, keep_importing)
            # so fast only shows last step in progress bar
            importer.tmp_to_named_tbl(con, cur, self.tbl_name, self.file_path, 
                                      progbar, nulled_dots)
        except Exception:
            importer.post_fail_tidy(progbar, con, cur, e)
            return
        cur.close()
        con.commit()
        con.close()
        progbar.SetValue(0)
        