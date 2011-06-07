import my_globals as mg

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

class NoNodesException(Exception):
    def __init__(self):
        Exception.__init__(self, u"Cannot get terminal nodes until " +
                    u"there is at least one node added to tree")

class ComtypesException(Exception):
    def __init__(self):
        Exception.__init__(self, u"Problem with comtypes."
                           u"\n\nTo fix, please look at help in:"
                           u"\n\nhttp://www.sofastatistics.com/wiki/doku.php?"
                           u"id=help:will_not_start#problems_with_comtypes")

class MatplotlibBackendException(Exception):
    def __init__(self, orig_error):
        Exception.__init__(self, u"Problem with matplotlib backend. You may "
           u"need to install a separate matplotlib library for the wx backend "
           u"e.g. python-matplotlib-wx\n\nOrig error: %s" % orig_error)
        
class InconsistentFileDateException(Exception):
    def __init__(self):
        Exception.__init__(self, _(u"SOFA has detected an inconsistent file "
                              u"date. Is your system date/time set correctly?"))

# Output exceptions - trapped as a group in output usually
class OutputException(Exception):
    pass

class TooManyCellsInChiSquareException(OutputException):
    def __init__(self):
        OutputException.__init__(self, _("Please select variables which have "
                "fewer different values. More than %s cells in contingency "
                "table.") % mg.MAX_CHI_CELLS)

class TooManyRowsInChiSquareException(OutputException):
    def __init__(self):
        OutputException.__init__(self, _("Please select a variable with no "
                        "more than %s values for Group A.") % mg.MAX_CHI_DIMS)

class TooManyColsInChiSquareException(OutputException):
    def __init__(self):
        OutputException.__init__(self, _("Please select a variable with no "
            "more than %s values for Group B.") % mg.MAX_CHI_DIMS)

class TooFewRowsInChiSquareException(OutputException):
    def __init__(self):
        OutputException.__init__(self, _("Please select a variable with at "
                        "least %s values for Group A.") % mg.MIN_CHI_DIMS)

class TooFewColsInChiSquareException(OutputException):
    def __init__(self):
        OutputException.__init__(self, _("Please select a variable with at "
                        "least %s values for Group B.") % mg.MIN_CHI_DIMS)

class TooFewValsInSamplesForAnalysisException(OutputException):
    def __init__(self):
        OutputException.__init__(self, u"At least two values are needed in "
                           u"each group to run the analysis. Please check "
                           u"filtering or source data.")

class ExcessReportTableCellsException(OutputException):
    def __init__(self, max):
        OutputException.__init__(self, _(u"Only allowed %s cells in "
                                         u"report table") % max)

class TooFewValsForDisplay(OutputException):
    def __init__(self, min_n=None):
        msg = (u"Not enough data to display. Please check variables "
               u"and any filtering.")
        if min_n:
            msg += " Need at least %s values." % min_n
        OutputException.__init__(self, msg)

class TooFewSamplesForAnalysisException(OutputException):
    def __init__(self):
        OutputException.__init__(self, u"At least two samples with non-missing "
                           u"data needed to run the analysis. Please check "
                           u"filtering or source data.")

class TooManySlicesInPieChart(OutputException):
    def __init__(self):
        OutputException.__init__(self, _("Too many slices in Pie Chart. "
                                         "More than %s.") % mg.MAX_PIE_SLICES)

class TooManySeriesInChart(OutputException):
    def __init__(self, max_items):
        OutputException.__init__(self, _(u"Too many series in chart. More "
                                         "than %s.") % max_items)

class TooManyValsInChartSeries(OutputException):
    def __init__(self, fld_measure, max_items):
        OutputException.__init__(self, u"Too many values to display for %s. " 
                           % fld_measure + u"More than %s." % max_items)

class TooManyChartsInSeries(OutputException):
    def __init__(self, fld_chart_by_name, max_items):
        OutputException.__init__(self, u"Too many charts to display for "
                "\"%s\". " % fld_chart_by_name + u"More than %s." % max_items)

class TooManyBoxplotsInSeries(OutputException):
    def __init__(self, fld_gp_by, max_items):
        OutputException.__init__(self, u"Too many boxplots to display for %s. " 
                           % fld_gp_by + u"More than %s." % max_items)
