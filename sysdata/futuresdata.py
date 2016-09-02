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


if __name__ == '__main__':
    import doctest
    doctest.testmod()
