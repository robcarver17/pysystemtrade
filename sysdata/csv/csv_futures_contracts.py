from syscore.fileutils import get_filename_for_package
from syscore.objects import arg_not_supplied
from sysdata.futures.contracts import futuresContractData
from syslogdiag.log import logtoscreen
import pandas as pd


class csvFuturesContractData(futuresContractData):
    """
    Get data about instruments from a special configuration used for initialising the system

    """

    def __init__(self, datapath=arg_not_supplied,
                 log=logtoscreen("csvFuturesContractData")):

        super().__init__()

        if datapath is arg_not_supplied:
            raise Exception("Need to pass datapath")

        self.datapath = datapath
        self.name = "Instruments data from %s" % self.datapath
        self.log = log

    def _filename_for_instrument_code(self, instrument_code):
        return get_filename_for_package(
            self.datapath, "%s.csv" %
            instrument_code)

    def write_contract_list_as_df(self, instrument_code, contract_list):
        list_of_expiry = [x.expiry_date.date() for x in contract_list]
        list_of_contract_date = [x.date for x in contract_list]
        list_of_sampling = [x.currently_sampling for x in contract_list]

        df = pd.DataFrame(
            dict(
                date=list_of_contract_date,
                sampling=list_of_sampling,
                expiry=list_of_expiry,
            )
        )
        filename = self._filename_for_instrument_code(instrument_code)
        df.to_csv(filename)
