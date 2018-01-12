from sysdata.data import Data


class FuturesData(Data):
    """
        Get futures specific data

        Extends the Data class to add additional features for asset specific

        Will normally be overriden by a method for a specific data source
        See legacy.py

    """

    def __repr__(self):
        return "FuturesData object with %d instruments" % len(
            self.get_instrument_list())

    def get_instrument_raw_carry_data(self, instrument_code):
        """
        Returns a pd. dataframe with the 4 columns PRICE, CARRY, PRICE_CONTRACT, CARRY_CONTRACT

        These are specifically needed for futures trading

        For other asset classes we'd probably pop in eg equities fundamental data, FX interest rates...

        Normally we'd inherit from this method for a specific data source

        :param instrument_code: instrument to get carry data for
        :type instrument_code: str

        :returns: pd.DataFrame

        """
        # Default method to get instrument price
        # Will usually be overriden when inherited with specific data source
        error_msg = "You have created a FuturesData() object or you probably need to replace this method to do anything useful"
        self.log.critical(error_msg)


class FuturesContract(object):
    """
    Define an individual futures contract

    Must be a monthly expiry

    """
    def __init__(self, instrument_code, contract_month):

        assert type(instrument_code) is str

        try:
            assert type(contract_month) is str
            assert len(contract_month)==6
            assert int(contract_month)
            assert int(contract_month[4:])>0 & int(contract_month[4:])<13
        except:
            raise Exception("contract_month needs to be defined as a str, yyyymm")

        self.instrument_code = instrument_code
        self.contract_month = contract_month

    def __repr__(self):
        return self.instrument_code + " "+ self.contract_month

if __name__ == '__main__':
    import doctest
    doctest.testmod()
