class ImportCancelException(Exception):
    def __init__(self):
        Exception.__init__(self, "Importing has been cancelled.")

class InvalidTestSelectionException(Exception):
    def __init__(self):
        Exception.__init__(self, "Invalid test selection.")

class NewLineInUnquotedException(Exception):
    def __init__(self):
        Exception.__init__(self, "New line in unquoted")

class TooManyRowsInChiSquareException(Exception):
    def __init__(self):
        Exception.__init__(self, "Too many rows in contingency table")

class TooManyColsInChiSquareException(Exception):
    def __init__(self):
        Exception.__init__(self, "Too many columns in contingency table")

class TooManyCellsInChiSquareException(Exception):
    def __init__(self):
        Exception.__init__(self, "Too many cells in contingency table")
        
class ExcessReportTableCellsException(Exception):
    def __init__(self, max):
        Exception.__init__(self, _("Only allowed %s cells in report table" % 
                                   max))

class TooFewValsForDisplay(Exception):
    def __init__(self):
        Exception.__init__(self, "Too few values for display")