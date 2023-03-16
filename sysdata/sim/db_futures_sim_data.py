"""
Get data from mongo and arctic used for futures trading

"""

from syscore.constants import arg_not_supplied

from sysdata.arctic.arctic_adjusted_prices import arcticFuturesAdjustedPricesData
from sysdata.arctic.arctic_multiple_prices import arcticFuturesMultiplePricesData
from sysdata.arctic.arctic_spotfx_prices import arcticFxPricesData
from sysdata.csv.csv_instrument_data import csvFuturesInstrumentData
from sysdata.csv.csv_roll_parameters import csvRollParametersData
from sysdata.mongodb.mongo_spread_costs import mongoSpreadCostData
from sysdata.data_blob import dataBlob
from sysdata.sim.futures_sim_data_with_data_blob import genericBlobUsingFuturesSimData

from syslogdiag.log_to_screen import logtoscreen


class dbFuturesSimData(genericBlobUsingFuturesSimData):
    def __init__(
        self, data: dataBlob = arg_not_supplied, log=logtoscreen("dbFuturesSimData")
    ):

        if data is arg_not_supplied:
            data = dataBlob(
                log=log,
                class_list=[
                    arcticFuturesAdjustedPricesData,
                    arcticFuturesMultiplePricesData,
                    arcticFxPricesData,
                    csvFuturesInstrumentData,
                    csvRollParametersData,
                    mongoSpreadCostData,
                ],
            )

        super().__init__(data=data)

    def __repr__(self):
        return "dbFuturesSimData object with %d instruments" % len(
            self.get_instrument_list()
        )


if __name__ == "__main__":
    import doctest

    doctest.testmod()
