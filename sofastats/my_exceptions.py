from . import my_globals as mg

class Mismatch(Exception):
    def __init__(self, fldname, expected_fldtype, details):
        debug = False
        if debug: print('A mismatch exception')
        self.fldname = fldname
        self.expected_fldtype = expected_fldtype
        self.details = details
        Exception.__init__(self,
            f'Found data not matching expected column type.\n\n{details}')

class MissingConDets(Exception):
    def __init__(self, dbe):
        Exception.__init__(self, f'Missing connection details for {dbe}.')

class MalformedDb(Exception):
    def __init__(self):
        Exception.__init__(self, 'Malformed database error')
        
class MalformedHtml(Exception):
    def __init__(self, msg):
        Exception.__init__(self,
            f'Unable to extract content from malformed HTML. {msg}')
class MalformedCssDojo(Exception):
    def __init__(self, text):
        Exception.__init__(self,
            'Unable to extract style from malformed dojo css. '
            f'Original text: {text}')

class MissingCss(Exception):
    def __init__(self, missing_css_fil):
        Exception.__init__(self, f'Missing css file "{missing_css_fil}".')
        
class ExportCancel(Exception):
    def __init__(self):
        Exception.__init__(self, 'Exporting has been cancelled.')

class ImportCancel(Exception):
    def __init__(self):
        Exception.__init__(self, 'Importing has been cancelled.')

class ImportNeededFix(Exception):
    def __init__(self):
        Exception.__init__(self, 'Import needed fix')

class ImportConfirmationRejected(Exception):
    def __init__(self):
        Exception.__init__(self,
            _('Unable to process csv file unless settings are confirmed'))

class InvalidTestSelection(Exception):
    def __init__(self):
        Exception.__init__(self, 'Invalid test selection.')

class NoNodes(Exception):
    def __init__(self):
        Exception.__init__(self,
            'Cannot get terminal nodes until at least one node added to tree')

class ComtypesException(Exception):
    def __init__(self):
        Exception.__init__(self, 
            'Problem with comtypes.'
            '\n\nTo fix, please look at help in:'
            '\n\nhttp://www.sofastatistics.com/wiki/doku.php?'
            'id=help:will_not_start#problems_with_comtypes')

class MatplotlibBackendException(Exception):
    def __init__(self, orig_error):
        Exception.__init__(self, 'Problem with matplotlib backend. You may '
           'need to install a separate matplotlib library for the wx backend '
           f'e.g. python-matplotlib-wx\n\nOrig error: {orig_error}')
        
class InconsistentFileDate(Exception):
    def __init__(self):
        Exception.__init__(self,
            _('SOFA has detected an inconsistent file date. '
              'Is your system date/time set correctly?'))

class NeedViableInput(Exception):
    def __init__(self):
        Exception.__init__(self, _('Waiting for viable report to be run ...'))

## Output exceptions - trapped as a group in output usually
class OutputException(Exception):
    pass

class InvalidTimeSeriesInput(OutputException):
    def __init__(self, fldname):
        OutputException.__init__(self, _("The \"%s\" field can't be "
            "used as a category for a time series analysis. It has at least "
            "one value that can't be converted into a date.") % fldname)

class CategoryTooLong(OutputException):
    def __init__(self, fldname):
        OutputException.__init__(self, _("The \"%(fldname)s\" field can't be "
            'used as a category. It has values longer than %(max_val)s.')
            % {'fldname': fldname, 'max_val': mg.MAX_VAL_LEN_IN_SQL_CLAUSE})
        
class TooManyCellsInChiSquare(OutputException):
    def __init__(self):
        OutputException.__init__(self, _('Please select variables which have '
            'fewer different values. More than %s cells in contingency table.')
            % mg.MAX_CHI_CELLS)

class TooManyRowsInChiSquare(OutputException):
    def __init__(self):
        OutputException.__init__(self,
            _('Please select a variable with no more than %s different row '
              'values for Group A.') % mg.MAX_CHI_DIMS)

class TooManyColsInChiSquare(OutputException):
    def __init__(self):
        OutputException.__init__(self,
            _('Please select a variable with no more than %s different column '
              'values for Group B.') % mg.MAX_CHI_DIMS)

class TooFewRowsInChiSquare(OutputException):
    def __init__(self):
        OutputException.__init__(self,
            _('Please select a variable with at least %s different row values '
              'for Group A.') % mg.MIN_CHI_DIMS)

class TooFewColsInChiSquare(OutputException):
    def __init__(self):
        OutputException.__init__(self,
            _('Please select a variable with at least %s different column '
              'values for Group B.') % mg.MIN_CHI_DIMS)

class TooFewValsInSamplesForAnalysis(OutputException):
    def __init__(self, gp_fldname, gp_val):
        OutputException.__init__(self, 'At least two values are needed in '
            'each group to run the analysis. Please check filtering or source '
            f'data. Not enough records in group {gp_val} for {gp_fldname}')

class ExcessReportTableCells(OutputException):
    def __init__(self, max_cells):
        OutputException.__init__(self,
            _('Only allowed %s cells in report table') % max_cells)

class TooFewValsForDisplay(OutputException):
    def __init__(self, min_n=None):
        msg = ('Not enough data to display. Please check variables and any '
            'filtering.')
        if min_n:
            msg += f' Need at least {min_n} values.'
        OutputException.__init__(self, msg)

class TooFewSamplesForAnalysis(OutputException):
    def __init__(self):
        OutputException.__init__(self,
            'At least two samples with non-missing data needed to run the '
            'analysis. Please check filtering or source data.')

class InadequateVariability(OutputException):
    def __init__(self):
        OutputException.__init__(self,
            'Not enough variability in the data to allow analysis.')

class TooManySlicesInPieChart(OutputException):
    def __init__(self):
        OutputException.__init__(self,
            _('Too many slices in Pie Chart. More than %s.')
            % mg.MAX_PIE_SLICES)

class TooManySeriesInChart(OutputException):
    def __init__(self, max_items):
        OutputException.__init__(self,
            _('Too many series in chart. More than %s.') % max_items)

class TooManyValsInChartSeries(OutputException):
    def __init__(self, fld_measure, max_items):
        OutputException.__init__(self,
            f'Too many values to display for {fld_measure}. '
            f'More than {max_items}.') 

class TooManyChartsInSeries(OutputException):
    def __init__(self, fld_chart_by_name, max_items):
        OutputException.__init__(self,
            f'Too many charts to display for "{fld_chart_by_name}". '
            f'More than {max_items}.')

class TooManyBoxplotsInSeries(OutputException):
    def __init__(self, fld_gp_by, max_items):
        OutputException.__init__(self,
            f'Too many boxplots to display for {fld_gp_by}. '
            f'More than {max_items}.')

class TooFewBoxplotsInSeries(OutputException):
    def __init__(self):
        OutputException.__init__(self,
            'Too few boxplots to display. Inadequate variability or number of '
            'values.')
