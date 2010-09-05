class MissingConDets(Exception):
    def __init__(self, dbe):
        Exception.__init__(self, u"Missing connection details for %s." % dbe)

class MalformedDbError(Exception):
    def __init__(self):
        Exception.__init__(self, u"Malformed database error")
        
class MalformedHtmlError(Exception):
    def __init__(self, html):
        Exception.__init__(self, u"Unable to extract content from malformed "
                           u"HTML. Original HTML: %s" % html)
class MalformedCssDojoError(Exception):
    def __init__(self, text):
        Exception.__init__(self, u"Unable to extract style from malformed "
                           u"dojo css. Original text: %s" % text)

class MissingCssException(Exception):
    def __init__(self, missing_css_fil):
        Exception.__init__(self, u"Missing css file \"%s\"." % missing_css_fil)

class ImportCancelException(Exception):
    def __init__(self):
        Exception.__init__(self, u"Importing has been cancelled.")

class ImportNeededFixException(Exception):
    def __init__(self):
        Exception.__init__(self, u"Import needed fix")

class ImportConfirmationRejected(Exception):
    def __init__(self):
        Exception.__init__(self, _("Unable to process csv file unless settings "
                                   "are confirmed"))
        
class InvalidTestSelectionException(Exception):
    def __init__(self):
        Exception.__init__(self, u"Invalid test selection.")

class TooManyRowsInChiSquareException(Exception):
    def __init__(self):
        Exception.__init__(self, u"Too many rows in contingency table")

class TooManyColsInChiSquareException(Exception):
    def __init__(self):
        Exception.__init__(self, u"Too many columns in contingency table")

class TooFewRowsInChiSquareException(Exception):
    def __init__(self):
        Exception.__init__(self, u"Not enough rows in contingency table")

class TooFewColsInChiSquareException(Exception):
    def __init__(self):
        Exception.__init__(self, u"Not enough columns in contingency table")

class TooManyCellsInChiSquareException(Exception):
    def __init__(self):
        Exception.__init__(self, u"Too many cells in contingency table")
        
class ExcessReportTableCellsException(Exception):
    def __init__(self, max):
        Exception.__init__(self, _("Only allowed %s cells in report table" % 
                                   max))

class TooFewValsForDisplay(Exception):
    def __init__(self):
        Exception.__init__(self, u"Too few values for display")

class NoNodesException(Exception):
    def __init__(self):
        Exception.__init__(self, u"Cannot get terminal nodes until " +
                    u"there is at least one node added to tree")

