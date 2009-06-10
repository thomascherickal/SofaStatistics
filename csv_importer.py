import csv
import wx

import importer


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
    
    def AssessDataSample(self, reader, has_header):
        """
        Assess data sample to see if consistent values in fields.
        Returns fld_names, fld_types, sample_data.
        If the data is consistent (i.e. possible to assign field types that
            fit the existing data), fld_types dict will have 
            field names as keys and field types as values.
        In which case, sample_data will be a list of dicts containing the
            first rows of data (no point reading them all again during 
            subsequent steps).
        If the data is not consistent, raise an exception.    

        Sample first 50 rows (at most) to establish field types.  
        If there is a header row, get the field names then skip it.
        For individual values, if numeric, assume numeric, 
            if date, assume date, 
            if string, assume either string or missing value for another type.
        For field sample, numeric if only contains numeric 
            and possible missings.
        Date if only contains dates and possible missings.
        String if only contains strings and possible missings.
        If none of those, unable to process.  Raise an exception which
            provide useful information about the problem with the data.
        The user might be able to manually fix these and try again.        
        """
        rows_to_sample = 2
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
        # TODO - populate fld_types with actual field types
        bogus_types = [importer.FLD_STRING for x in range(len(fld_names))]
        fld_types = dict(zip(fld_names, bogus_types))
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












