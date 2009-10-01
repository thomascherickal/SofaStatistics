import csv
import os
import wx

import dbe_plugins.dbe_sqlite as dbe_sqlite
import getdata
import util
from my_exceptions import ImportCancelException
import importer

ROWS_TO_SAMPLE = 500 # fast enough to sample quite a few


class FileImporter(object):
    """
    Import csv file into default SOFA SQLite database.
    Needs to identify data types to ensure only consistent data in a field.
    Adds unique index id so can identify unique records with certainty.
    """
    
    def __init__(self, file_path, tbl_name):                    
        self.file_path = file_path
        self.tbl_name = tbl_name
        
    def GetParams(self):
        """
        Get any user choices required.
        """
        return True
    
    def AssessDataSample(self, reader, has_header, progBackup, gauge_chunk, 
                         keep_importing):
        """
        Assess data sample to identify field types based on values in fields.
        If a field has mixed data types will define as string.
        Returns fld_types, sample_data.
        fld_types - dict with field names as keys and field types as values.
        sample_data - list of dicts containing the first rows of data 
            (no point reading them all again during subsequent steps).   
        Sample first N rows (at most) to establish field types.   
        """
        bolhas_rows = False
        sample_data = []
        for i, row in enumerate(reader):
            if i % 50 == 0:
                wx.Yield()
                if keep_importing == set([False]):
                    progBackup.SetValue(0)
                    raise ImportCancelException
            if has_header and i == 0:
                continue # skip first line
            bolhas_rows = True
            # process row
            sample_data.append(row)
            gauge_val = i*gauge_chunk
            progBackup.SetValue(gauge_val)
            if i == (ROWS_TO_SAMPLE - 1):
                break
        fld_types = []
        for fld_name in reader.fieldnames:
            fld_type = importer.AssessSampleFld(sample_data, fld_name)
            fld_types.append(fld_type)
        fld_types = dict(zip(reader.fieldnames, fld_types))
        if not bolhas_rows:
            raise Exception, "No data to import"
        return fld_types, sample_data
    
    def getAvgRowSize(self, tmp_reader):
        # loop through at most 5 times
        i = 0
        size = 0
        for row in tmp_reader:
            try:
                values = row.values()
            except AttributeError:
                values = row
            size += len(", ".join(values))
            i += 1
            if i == 5:
                break
        avg_row_size = float(size)/i
        return avg_row_size
        
    def ImportContent(self, progBackup, keep_importing):
        """
        Get field types dict.  Use it to test each and every item before they 
            are added to database (after adding the records already tested).
        Add to disposable table first and if completely successful, rename
            table to final name.
        """
        debug = False
        try:
            csvfile = open(self.file_path)
            sniffer = csv.Sniffer()
            sniff_sample = csvfile.read(3072) # 1024 not enough if many fields
            # if too small, will return error about newline inside string
            dialect = sniffer.sniff(sniff_sample)
            has_header = sniffer.has_header(sniff_sample)
        except Exception, e:
            raise Exception, "Unable to open and sample csv file. " + \
                "Orig error: %s" % e
        try:
            csvfile.seek(0)
            # get field names
            if has_header:
                tmp_reader = csv.DictReader(csvfile, dialect=dialect)
                fld_names = tmp_reader.fieldnames
            else:
                # get number of fields
                tmp_reader = csv.reader(csvfile, dialect=dialect)
                for row in tmp_reader:
                    if debug: print row
                    fld_names = ["Fld_%s" % (x+1,) for x in range(len(row))]
                    break
                csvfile.seek(0)
            # estimate number of rows (only has to be good enough for progress)
            tot_size = os.path.getsize(self.file_path)
            row_size = self.getAvgRowSize(tmp_reader)
            if debug:
                print "tot_size: %s" % tot_size
                print "row_size: %s" % row_size
            csvfile.seek(0)
            n_rows = float(tot_size)/row_size            
            reader = csv.DictReader(csvfile, dialect=dialect, 
                                    fieldnames=fld_names)
        except Exception, e:
            raise Exception, "Unable to create reader for file. " + \
                "Orig error: %s" % e
        conn, cur, _, _, _, _, _ = getdata.GetDefaultDbDets()
        sample_n = ROWS_TO_SAMPLE if ROWS_TO_SAMPLE <= n_rows else n_rows
        gauge_chunk = importer.getGaugeChunkSize(n_rows, sample_n)
        fld_types, sample_data = self.AssessDataSample(reader, has_header, 
                                        progBackup, gauge_chunk, keep_importing)
        # NB reader will be at position ready to access records after sample
        remaining_data = list(reader) # must be a list not a reader or can't 
        # start again from beginning of data (e.g. if correction made)
        importer.AddToTmpTable(conn, cur, self.file_path, self.tbl_name, 
                               fld_names, fld_types, sample_data, sample_n,
                               remaining_data, progBackup, gauge_chunk, 
                               keep_importing)
        importer.TmpToNamedTbl(conn, cur, self.tbl_name, self.file_path, 
                               progBackup)
        cur.close()
        conn.commit()
        conn.close()
        progBackup.SetValue(0)
        