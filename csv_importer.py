import csv
import wx

import dbe_plugins.dbe_sqlite as dbe_sqlite
import importer
import util

ROWS_TO_SAMPLE = 50


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
    
    def AssessDataSample(self, reader, has_header):
        """
        Assess data sample to identify field types based on values in fields.
        If a field has mixed data types will define as string.
        Returns fld_names, fld_types, sample_data.
        fld_types - dict with field names as keys and field types as values.
        sample_data - list of dicts containing the first rows of data 
            (no point reading them all again during subsequent steps).   
        Sample first N rows (at most) to establish field types.  
        If there is a header row, get the field names.     
        """
        bolhas_rows = False
        sample_data = []
        if has_header:
            fld_names = reader.fieldnames
        for i, row in enumerate(reader): # NB if has_header, starts at first data row
            if not has_header:
                fld_names = ["Fld_%s" % i+1 for x in range(len(row))]
            bolhas_rows = True
            # process row
            sample_data.append(row)
            if i == (ROWS_TO_SAMPLE - 1):
                break
        fld_types = []
        for fld_name in fld_names:
            fld_type = importer.AssessSampleFld(sample_data, fld_name)
            fld_types.append(fld_type)
        fld_types = dict(zip(fld_names, fld_types))
        if not bolhas_rows:
            raise Exception, "No data to import"
        return fld_names, fld_types, sample_data
    
    def ImportContent(self):
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
            sniff_sample = csvfile.read(1024)
            dialect = sniffer.sniff(sniff_sample)
            has_header = sniffer.has_header(sniff_sample)
            csvfile.seek(0)
            reader = csv.DictReader(csvfile, dialect=dialect)
        except Exception, e:
            if debug:
                print "Unable to open file.  Orig error: %s" % e
            raise Exception, "Unable to open and read file"
        fld_names, fld_types, sample_data = self.AssessDataSample(reader, 
                                                                  has_header)
        # NB reader will be at position ready to access records after sample
        importer.AddToTable(self.file_path, self.tbl_name, 
                            fld_names, fld_types, sample_data, 
                            remaining_data=reader)

