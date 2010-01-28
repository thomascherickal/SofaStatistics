class ImportCancelException(Exception):
    def __init__(self):
        Exception.__init__(self, "Importing has been cancelled.")

class InvalidTestSelectionException(Exception):
    def __init__(self):
        Exception.__init__(self, "Invalid test selection.")

class NewLineInUnquotedException(Exception):
    def __init__(self):
        Exception.__init__(self, "New line in unquoted")

class TooManyCellsInChiSquareException(Exception):
    def __init__(self):
        Exception.__init__(self, "Too many cells in contingency table")