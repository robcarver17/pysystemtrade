"""
Custom exceptions
"""


class missingInstrument(Exception):
    pass


class missingContract(Exception):
    pass


class missingData(Exception):
    pass

class missingFile(Exception):
    pass

class existingData(Exception):
    pass


class orderCannotBeModified(Exception):
    pass


class ContractNotFound(Exception):
    pass
