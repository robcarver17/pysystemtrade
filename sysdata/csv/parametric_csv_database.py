"""
This is a base class that is used by csv_futures_contract_prices and csv_adjusted_prices to allow for parametric access to CSV file database 
containing price data for separate futures contracts or adjusted/continuous contracts. 

Please see sysinit/futures/barchart_futures_contract_prices.py for how to use this class (via csvFuturesContractPriceData)

The benefits are two-fold: First there's no need to write separate middle-ware conversion tool to daily process data from other sources 
(such as CSI Data or Barchart) but one can just configure the file naming convention and other parameters and use the original CSV files as they are.
Secondly you can keep all CSV files in separate directories based on the instrument code (or other parameter).

The database is constructed by scanning target 'datapath' directory for .csv files having a suitable filename format.
The format string can contain formatting codes (instrument or broker code, year, month etc) that map the file to a corresponding 
instrument code/contract pair. See below for available formatting codes. Formatting string can also be configured to scan subdirectories
(see below DEFAULT_FILENAME_FORMAT_FOR_SUBDIRECTORIES)

Because data sources have different symbol names for instruments (broker code), we have to map those to match the corresponding instrument code
we have in our database. This is done via ConfigCsvFuturesPrices.broker_symbols dict.

Some instruments might have uncommon unit compared to prices that are fetched from Interactive Brokers
(e.g. JPY contract unit is actually USD/100 Japanese Yen but IB uses unit of USD/Yen ) so a multiplier is used to convert prices
to the unit that IB uses (and is stored in Arctic). This is done with ConfigCsvFuturesPrices.instrument_price_multiplier dict

"""

from pandas.core.frame import DataFrame
from syscore.pdutils import pd_readcsv, DEFAULT_DATE_FORMAT
from sysdata.base_data import baseData
from dataclasses import  dataclass
from syscore.objects import arg_not_supplied, missingData
from sysobjects.contract_dates_and_expiries import contractDate
from syscore.fileutils import get_resolved_pathname, get_filename_for_package
from syscore.dateutils import month_from_contract_letter
import os,re
import numpy as np

INSTRUMENT_CODE = "%{IC}"          # Instrument code. 
MATCH_ALL_CODE = "%{IGNORE}"       # 'Match all' type. Used for ignoring useless fields
BROKER_SYMBOL_CODE = "%{BS}"       # Broker symbol
MONTH_LZ_CODE = "%{MONTH2}"        # month with zero padding
MONTH_CODE = "%{MONTH}"            # month without zero padding
DAY_LZ_CODE = "%{DAY2}"            # day with zero padding
DAY_CODE = "%{DAY}"                # day without zero padding
MONTH_LETTER_CODE = "%{LETTER}"    # Month letter code
YEAR_CODE = "%{YEAR}"              # 4 digit year
YEAR2_CODE = "%{YEAR2}"            # two digit year (century cut off is <50 -> 1950,  >=50 -> 2050)

DEFAULT_FILENAME_FORMAT = "%{IC}_%{YEAR}%{MONTH2}%{DAY2}.csv" # e.g. CRUDE_W_20190900.csv

# Example format for separating files into subdirectories base on instrument code
DEFAULT_FILENAME_FORMAT_FOR_SUBDIRECTORIES = "%{IC}/%{IC}_%{YEAR}%{MONTH2}%{DAY2}.csv" # e.g. CRUDE_W/CRUDE_W_20190900.csv


format_code_to_regexp = { 
    INSTRUMENT_CODE : "[^/]*",          # Instrument code. Just make sure that it doesn't match forward slash
    BROKER_SYMBOL_CODE : ".*",          # Broker symbol
    MATCH_ALL_CODE : ".*",              # 'Match all' type. Used for ignoring useless fields
    YEAR_CODE : "[0-9]{4}",             # Year
    YEAR2_CODE : "[0-9]{2}",            # two digit year (cut off is 1950)
    MONTH_LETTER_CODE : "[FGHJKMNQUVXZfghjkmnquvxz]{1}", # Month letter code
    MONTH_LZ_CODE : "[0-9]{2}",         # mont with zero padding
    MONTH_CODE : "[0-9]{1,2}",          # month without zero padding 
    DAY_LZ_CODE : "[0-9]{2}",           # day with zero padding
    DAY_CODE : "[0-9]{1,2}",            # day without zero padding
    }

CONTINUOUS_CONTRACT_ID = "10000100"     # placeholder contract date string for continuous/adjusted contracts

@dataclass
class ConfigCsvFuturesPrices:
    input_date_index_name: str = "DATETIME"
    input_date_format: str = DEFAULT_DATE_FORMAT
    input_column_mapping: dict = None
    input_skiprows: int = 0
    input_skipfooter: int = 0
    input_filename_format:str = DEFAULT_FILENAME_FORMAT
    append_default_daily_time: bool = False     # append default time (23:00:00) of daily price data if the input datetime column does not include it
    broker_symbols: dict = arg_not_supplied     # dict of instrument code -> broker symbol mapping
    broker_symbol_ignore_case: bool = True
    continuous_contracts: bool = False          # If scanning for continuous (back-adjusted) contracts then date related codes are ignored

    # some instruments have uncommon unit compared to prices IB reports
    #  (e.g. JPY is USD/100 Japanese Yen but IB data is USD/Yen ) so a multiplier is used 
    # to convert prices to the IB compatible magnitude
    instrument_price_multiplier: dict = arg_not_supplied  


class parametricCsvDatabase(baseData):

    def __init__(
        self,
        log = arg_not_supplied,
        datapath = arg_not_supplied,
        config: ConfigCsvFuturesPrices = arg_not_supplied
    ):    
        super().__init__(log=log)

        if datapath is arg_not_supplied:
            raise Exception("Need to pass datapath")
        self._datapath = datapath
 
        if config is arg_not_supplied:
            config = ConfigCsvFuturesPrices()

        self._config = config

        format = config.input_filename_format

        if INSTRUMENT_CODE not in format and BROKER_SYMBOL_CODE not in format:
            raise Exception("Input filename format string needs instrument code or broker symbol code!")
        if config.continuous_contracts == False:
            if MONTH_CODE not in format and MONTH_LZ_CODE not in format and MONTH_LETTER_CODE not in format:
                raise Exception("Input filename format string needs month code!")
            if YEAR_CODE not in format and YEAR2_CODE not in format:
                raise Exception("Input filename format string needs year code!")

        if BROKER_SYMBOL_CODE in format:
            if config.broker_symbols is arg_not_supplied:
                raise Exception("Input filename format string contains broker symbol code but broker_symbols dictionary not given!")

        if config.broker_symbols is not arg_not_supplied:
            if config.broker_symbol_ignore_case:
                broker_symbols = dict()
                for key, value in config.broker_symbols.items():
                    broker_symbols[key] = value.upper()
                config.broker_symbols = broker_symbols

        self._filename_cache = dict()
        self.update_filename_cache()


    @property
    def config(self):
        return self._config

    @property
    def datapath(self):
        return self._datapath


    def _construct_filename(self, keyname:str):
        """
        Construct (path+)filename using format string and keyname.  Eg %{IC}_%{YEAR}%{MONTH2}.csv -> BITCOIN_201909.csv
        or %{IC}/%{IC}_%{YEAR}%{MONTH2}.csv -> BITCOIN/BITCOIN_201909.csv
        :param keyname: str Key name
        :return Constructed path or file name
        """
        instr_code, contract_date_str = self._contract_tuple_given_keyname(keyname)
        if contract_date_str != CONTINUOUS_CONTRACT_ID:
            contract_date = contractDate(contract_date_str)
        format = self.config.input_filename_format

        if INSTRUMENT_CODE in format:
            format = format.replace(INSTRUMENT_CODE,instr_code)
        if BROKER_SYMBOL_CODE in format:
            broker_symbol = self.broker_symbol_given_instrument_code(instr_code)
            if broker_symbol is missingData:
                raise Exception("Instrument code %s not found in broker symbol dictionary!" % instr_code)
            format = format.replace(BROKER_SYMBOL_CODE,broker_symbol)

        if contract_date_str != CONTINUOUS_CONTRACT_ID:
            if MONTH_LZ_CODE in format:
                format = format.replace(MONTH_LZ_CODE, str(contract_date.month()).zfill(2))
            if MONTH_CODE in format:
                format = format.replace(MONTH_CODE, str(contract_date.month()))
            if MONTH_LETTER_CODE in format:
                format = format.replace(MONTH_LETTER_CODE, contract_date.letter_month())            
            if YEAR_CODE in format:
                format = format.replace(YEAR_CODE, str(contract_date.year()))
            if YEAR2_CODE in format:
                format = format.replace(YEAR_CODE, str(contract_date.year())[2:])
            if DAY_LZ_CODE in format:
                format = format.replace(DAY_LZ_CODE, str(contract_date.day()).zfill(2))
            if DAY_CODE in format:
                format = format.replace(DAY_CODE, str(contract_date.day()))
        if MATCH_ALL_CODE in format:
            raise Exception("Cannot construct filename from format string containing 'match all' type!")
        filename = format

        path = self._datapath
        return get_filename_for_package(path, filename)


    def _convert_format_codes_to_regexp_groups( self, format_string:str, format_code:str):
        """
        Convert format codes (e.g. instrument code %{IC}) to regexp groups. 
        :param format_string: str Format string
        :param format_code: str Format code (e.g. %{IC} or %{LETTER})
        :return Tuple (modified format string, list of group names). Format string has the given format code replaced with corresponding regexp strings
        """
        count = format_string.count(format_code)
        group_names = []
        if count == 0:
            # this conversion type not found in format string
            return format_string, []
        else:
            # if format string has multiple same conversion types (e.g. %{IC}/%{IC}_%{YEAR}%{MONTH2}%{DAY2}.csv) we have to create different group name for each of those
            # because regexp doesn't allow identical group names
            for i in range(count):
                # create placeholder regexp group name: E.g.  %{IC} becomes groupIC0, groupIC1, .. 
                group_name = format_code.replace("%{","group")
                group_name = group_name.replace("}","") + str(i)
                regexp = format_code_to_regexp[ format_code ]
                group_regexp = "(?P<" + group_name + ">" + regexp + "?)"
                # replace one group at a time. So   %{IC}/%{IC}_%{YEAR}%{MONTH2}%{DAY2}.csv
                # becomes first 
                # (?P<groupIC0>.*?)/%{IC}_%{YEAR}%{MONTH2}%{DAY2}.csv   , and then
                # (?P<groupIC0>.*?)/(?P<groupIC1>.*?)_%{YEAR}%{MONTH2}%{DAY2}.csv
                format_string = format_string.replace(format_code, group_regexp, 1)
                group_names.append(group_name)

        # finally return the partially converted format string and group names that we can then use to locate the matched codes later
        return format_string, group_names


    def instrument_code_given_broker_symbol(self, broker_symbol:str):
        for instr_code, symbol in self.config.broker_symbols.items():
            if symbol == broker_symbol:
                return instr_code
            if self.config.broker_symbol_ignore_case:
                if symbol == broker_symbol.upper():
                    return instr_code
        return missingData


    def broker_symbol_given_instrument_code(self, instrument_code:str):
        if instrument_code in self.config.broker_symbols:
            return self.config.broker_symbols[instrument_code]
        return missingData


    def keyname_given_filename( self, filename: str ):
        """
        Convert filename to keyname using a format string defined in ConfigCsvFuturesPrices.input_filename_format
        Format string has conversion codes (e.g. instrument code %{IC} or broker symbol %{BS}) which will be used 
        to resolve instrument name and contract date.
        
        :param filename:str file name
        :return keyname or missingData if filename didn't match the format
        """
        format = self.config.input_filename_format

        # convert each format code from format string first to regular expression ..
        group_names_dict = dict()
        processed_str = format
        for format_code, regexp_single in format_code_to_regexp.items():
            processed_str, group_names = self._convert_format_codes_to_regexp_groups(processed_str, format_code)
            if len(group_names)>0 and format_code != MATCH_ALL_CODE:
                # save group names for checking below
                group_names_dict[ format_code ] = group_names

        pattern = re.compile(processed_str, re.VERBOSE)

        # .. and then check if filename matches the regexp pattern
        match = pattern.match(filename)
        if match:

            # For sanitys sake we still want to check that if a format code has many instances (e.g. %{IC}/%{IC}_%{YEAR}%{MONTH2}%{DAY2}.csv), 
            # so the matched codes will have identical value (e.g. CRUDE_W_mini/CRUDE_W_mini_20190900.csv is a match but CRUDE_W_mini/GOLD_20190900.csv is not)
            for format_conv_type, group_names in group_names_dict.items():
                group_count_per_type = len(group_names)
                if group_count_per_type > 1:
                    match1 = match.group(group_names[0])
                    for idx in range(1,group_count_per_type):
                        match_n = match.group(group_names[idx])
                        if match1 != match_n:
                            print("Warning! Unexpected filename! %s -> %s" % (self.config.input_filename_format, filename))
                            return missingData

            if INSTRUMENT_CODE in format:
                instr_code = match.group(group_names_dict[INSTRUMENT_CODE][0])

            if self.config.continuous_contracts == False:
                if MONTH_LZ_CODE in format:
                    month = match.group(group_names_dict[MONTH_LZ_CODE][0])
                if MONTH_CODE in format:
                    month = match.group(group_names_dict[MONTH_CODE][0])
                day = 0
                if DAY_LZ_CODE in format:
                    day = match.group(group_names_dict[DAY_LZ_CODE][0])
                if DAY_CODE in format:
                    day = match.group(group_names_dict[DAY_CODE][0])
                if MONTH_LETTER_CODE in format:
                    month_letter = match.group((group_names_dict[MONTH_LETTER_CODE][0]))
                    month = month_from_contract_letter(month_letter.upper())
                if YEAR_CODE in format:
                    year = match.group(group_names_dict[YEAR_CODE][0])
                if YEAR2_CODE in format:
                    year = int(match.group(group_names_dict[YEAR2_CODE][0]))
                    if year <= 50:
                        year += 2000
                    else:
                        year += 1900
            if BROKER_SYMBOL_CODE in format:
                broker_symbol = match.group(group_names_dict[BROKER_SYMBOL_CODE][0])
                instr_code = self.instrument_code_given_broker_symbol(broker_symbol)
                if instr_code is missingData:
                    print("Warning! Missing broker symbol %s (file %s)" % (broker_symbol, filename))
                    return missingData
            if self.config.continuous_contracts == True:
                return instr_code + "_" + CONTINUOUS_CONTRACT_ID
            else:
                return instr_code + "_" + str(year) + str(month).zfill(2) + str(day).zfill(2)
        else:
            return missingData


    def update_filename_cache(self):
        path = get_resolved_pathname(self._datapath)
        for root,dirs,files in os.walk(path):
            for filename in files:
                # gets only the sub directory part
                relative_path = os.path.relpath(root,path)
                # get filename with relative part (e.g. "CRUDE_W_mini/CRUDE_W_mini_20190900.csv")
                if relative_path != ".":
                    relative_filename = os.path.join(relative_path, filename)
                else:
                    # we don't want the './' prefix
                    relative_filename = filename
                # deduce the key name using relative filename and format string
                keyname = self.keyname_given_filename(relative_filename)
                if keyname is not missingData:
                    self._filename_cache[keyname] = os.path.join(root, filename)
                else:
                    print("Warning! Filename %s does not conform to format '%s'!" % (relative_filename,self.config.input_filename_format))
        

    def _get_filename_from_cache(self, keyname):
        if keyname in self._filename_cache:
            return self._filename_cache[keyname]
        else:
            return missingData


    def _contract_tuple_given_keyname(self, keyname: str) -> tuple:
        """
        Extract the two parts of a keyname

        We keep control of how we represent stuff inside the class

        :param keyname: str
        :return: tuple instrument_code, contract_date
        """
        keyname_as_list = keyname.split("_")

        if len(keyname_as_list) == 4:
            keyname_as_list = [
                "%s_%s_%s" % (keyname_as_list[0], keyname_as_list[1], keyname_as_list[2]),
                keyname_as_list[3],
            ]


        # It's possible to have GAS_US_20090700.csv, so we only take the second
        if len(keyname_as_list) == 3:
            keyname_as_list = [
                "%s_%s" % (keyname_as_list[0], keyname_as_list[1]),
                keyname_as_list[2],
            ]

        try:
            assert len(keyname_as_list) == 2
        except BaseException:
            self.log.error(
                "Keyname (filename) %s in wrong format should be instrument_contractid" %
                keyname)
        instrument_code, contract_date = tuple(keyname_as_list)

        return instrument_code, contract_date

    def filename_given_key_name(self, keyname: str):
        filename = self._get_filename_from_cache(keyname)
        if filename is missingData:
            filename = self._construct_filename(keyname)
            self._filename_cache[keyname] = filename
        return filename

    def all_keynames_in_library(self) -> list:
        return self._filename_cache.keys()

    def keyname_given_instrument_code(self, instrument_code:str):
        if self.config.continuous_contracts == False:
            raise Exception("Cannot deduce key name from only an instrument code when not processing continuous contracts!")
        return str(instrument_code) + "_" + str(CONTINUOUS_CONTRACT_ID)

    def filename_given_instrument_code(self, instrument_code:str):
        return self.filename_given_key_name( self.keyname_given_instrument_code( instrument_code ) )

    def get_contract_tuples_with_price_data(self) -> list:
        """
        :return: list of futures contracts as tuples
        """
        all_keynames = self.all_keynames_in_library()
        list_of_contract_tuples = [self._contract_tuple_given_keyname(
            keyname) for keyname in all_keynames]

        return list_of_contract_tuples

    def get_list_of_instrument_codes(self) -> list:
        all_keynames = self.all_keynames_in_library()
        list_of_instrument_codes = []
        for keyname in all_keynames:
            (instrument_code, contract_str) = self._contract_tuple_given_keyname(keyname)
            list_of_instrument_codes.append(instrument_code)

        # remove possible duplicates
        list_of_instrument_codes = list(dict.fromkeys(list_of_instrument_codes))

        return list_of_instrument_codes

    def load_and_process_prices(self, filename:str, instrument_code:str) -> DataFrame:
        config = self.config

        date_format = config.input_date_format
        date_time_column = config.input_date_index_name
        input_column_mapping = config.input_column_mapping
        skiprows = config.input_skiprows
        skipfooter = config.input_skipfooter

        instrpricedata = pd_readcsv(
            filename,
            date_index_name=date_time_column,
            date_format=date_format,
            input_column_mapping=input_column_mapping,
            skiprows=skiprows,
            skipfooter=skipfooter,
        )

        # do unit conversion for prices if needed
        if config.instrument_price_multiplier is not arg_not_supplied:
            if instrument_code in config.instrument_price_multiplier:
                mult = config.instrument_price_multiplier[instrument_code]
                if mult != 1:
                    instrpricedata["OPEN"] = instrpricedata["OPEN"] * mult
                    instrpricedata["HIGH"] = instrpricedata["HIGH"] * mult
                    instrpricedata["LOW"] = instrpricedata["LOW"] * mult
                    instrpricedata["FINAL"] = instrpricedata["FINAL"] * mult

        if config.append_default_daily_time:
            # Append date with the default time (23:00:00) of daily data 
            # when it's not included in the datetime column
            p_datetime = instrpricedata.index.values.copy()
            p_datetime = p_datetime + np.timedelta64(23,'h')
            instrpricedata.index = p_datetime
        
        return instrpricedata
