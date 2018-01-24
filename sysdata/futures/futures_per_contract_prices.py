import pandas as pd
from sysdata.data import baseData

class futuresData(pd.DataFrame):
    """
    Data frame in specific format containing per contract information
    """

    def __init__(self, data):

        data_present = list(data.columns)
        data_present.sort()

        try:
            assert data_present == ['OPEN', 'CLOSE', 'HIGH', 'LOW', 'SETTLE', 'VOLUME', 'OPEN_INTEREST']
        except AssertionError:
            raise Exception("futuresData has to conform to pattern")

        super().__init__(data)



class futuresContractPriceData(baseData):
    """
    Extends the baseData object to a data source that reads in prices for specific futures contracts

    This would normally be extended further for information from a specific source eg quandl, mongodb
    """

    def __repr__(self):
        return "Individual futures prices"

    def __getitem__(self, keyname):
        """
         convenience method to get the price, make it look like a dict

        :param keyname: instrument to get prices for
        :type keyname: str

        :returns: pd.DataFrame
        """

        raise Exception("__getitem__ not defined for baseData class: use a class where it has been overriden")


    def keys(self):
        """
        list of things in this data set (futures contracts, instruments...)

        :returns: list of str

        >>> data=Data()
        >>> data.keys()
        []
        """
        return []

