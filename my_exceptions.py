class ImportCancelException(Exception):
    def __init__(self):
        Exception.__init__(self, "Importing has been cancelled.")
