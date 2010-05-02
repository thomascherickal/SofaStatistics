class MissingConDets(Exception):
    def __init__(self, dbe):
        Exception.__init__(self, u"Missing connection details for %s." % dbe)

class MissingCssException(Exception):
    def __init__(self):
        Exception.__init__(self, "Missing css file.")

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

class TooFewRowsInChiSquareException(Exception):
    def __init__(self):
        Exception.__init__(self, "Not enough rows in contingency table")

class TooFewColsInChiSquareException(Exception):
    def __init__(self):
        Exception.__init__(self, "Not enough columns in contingency table")

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

class NoNodesException(Exception):
    def __init__(self):
        Exception.__init__(self, "Cannot get terminal nodes until " +
                    "there is at least one node added to tree")
