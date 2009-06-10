import csv
import wx

import importer
import util


class FileImporter(object):
    """
    Import csv file into default SOFA SQLite database.
    Needs to identify data types to ensure only consistent data in a field.
    Checks table name first to ensure no collision.
    Adds unique index id so can identify unique records with certainty.
    """
    
    def __init__(self, file_path, tbl_name):
        "Initialise after checking no naming collision"
        
        
        # TODO - check no naming collision
        
        
        self.file_path = file_path
        self.tbl_name = tbl_name
                
    def GetParams(self):
        """
        Get any user choices required.
        """
        return True
    
    def AssessSampleFld(self, sample_data, fld_name):
        """
        For individual values, if numeric, assume numeric, 
            if date, assume date, 
            if string, either an empty string or an ordinary string.
        For entire field sample, numeric if only contains numeric 
            and empty strings (could be missings).
        Date if only contains dates and empty strings (could be missings).
        String otherwise.   
        Return field type.
        """
        type_set = set()
        numeric_only_set = set([importer.VAL_NUMERIC])
        numeric_or_empt_str_set = set([importer.VAL_NUMERIC, 
                                       importer.VAL_EMPTY_STRING])
        datetime_only_set = set([importer.VAL_DATETIME])
        datetime_or_empt_str_set = set([importer.VAL_DATETIME, 
                                        importer.VAL_EMPTY_STRING])
        for row in sample_data:
            item = row[fld_name]
            if util.isNumeric(item):
                type_set.add(importer.VAL_NUMERIC)
            else:
                boldatetime, time_obj = util.datetime_str_valid(item)
                if boldatetime:
                    type_set.add(importer.VAL_DATETIME)
                elif item == "":
                    type_set.add(importer.VAL_EMPTY_STRING)
                else:
                    type_set.add(importer.VAL_STRING)
        if type_set == numeric_only_set or \
                type_set == numeric_or_empt_str_set:
            fld_type = importer.FLD_NUMERIC
        elif type_set == datetime_only_set or \
                type_set == datetime_or_empt_str_set:
            fld_type = importer.FLD_DATETIME
        else:
            fld_type = importer.FLD_STRING
        return fld_type
    
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
        rows_to_sample = 50
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
            if i == (rows_to_sample - 1):
                break
        fld_types = []
        for fld_name in fld_names:
            fld_type = self.AssessSampleFld(sample_data, fld_name)
            fld_types.append(fld_type)
        fld_types = dict(zip(fld_names, fld_types))
        if not bolhas_rows:
            raise "No data to import"
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
            sample = csvfile.read(1024)
            dialect = sniffer.sniff(sample)
            has_header = sniffer.has_header(sample)
            csvfile.seek(0)
            reader = csv.DictReader(csvfile, dialect=dialect)
        except Exception, e:
            if debug:
                print "Unable to open file.  Orig error: %s" % e
            raise "Unable to open and read file"
        fld_names, fld_types, sample_data = self.AssessDataSample(reader, 
                                                                  has_header)
        # create fresh disposable table to store data in
        print "Field names are: %s" % fld_names
        print "Field types are: %s" % fld_types
        # add sample to disposable table
        print "Sample data is: %s" % sample_data
        # start adding remaining data (if any) to table
        # NB reader will be at position ready to access records after sample
        # check it as we go
        for i, row in enumerate(reader):
            print "Data to test and add: %s - %s" % (i, row)
        # rename table to final name
