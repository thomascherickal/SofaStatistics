import csv
import wx


class FileImporter(object):
    """
    Import csv file into default SOFA SQLite database.
    Needs to identify data types to ensure only consistent data in a field.
    Checks table name first to ensure no collision.
    Adds unique index id so can identify unique records with certainty.
    """
    
    def __init__(self, file_path, tbl_name):
        """"""
        debug = True
        self.file_path = file_path
        self.tbl_name = tbl_name
        if debug:
            print "My file path is '%s' and the table name is '%s'" % \
                (file_path, tbl_name)
                
    def GetParams(self):
        """
        Get any user choices required.
        """
        return True
        
    def ImportContent(self):
        """
        Sample first 50 rows to establish field types.
        Create dict with field names as keys and field types as values.
        Use this dict to test each and every items before added to database.
        For individual values, if numeric, assume numeric, 
            if date, assume date, 
            if string, assume either string or missing value for another type.
        For field sample, numeric if only contains numeric 
            and possible missings.
        Date if only contains dates and possible missings.
        String if only contains strings and possible missings.
        If none of those, unable to process.  Provide useful message about 
            issue with records.
        Add to disposable table first and if completely successful, rename
            table to final name.
        """
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
        for i, row in enumerate(reader):
            if has_header and i == 0:
                print reader.fieldnames
            else:
                print row













