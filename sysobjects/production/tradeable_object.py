from sysobjects.instruments import futuresInstrument
from sysobjects.contracts import futuresContract
from sysobjects.contract_dates_and_expiries import contractDate


class tradeableObject(object):
    """
    Anything we can trade

    Could be an instrument, or contract. This is the base class
    """

    def __init__(self, object_name):
        # probably overridden with nicer entry
        self._key = object_name

    def __repr__(self):
        return self.key

    @classmethod
    def from_key(tradeableObject, object_name):
        return tradeableObject(object_name)

    def __eq__(self, other):
        return self.key == other.key

    @property
    def key(self):
        # probably overridden
        return self._key


class listOfInstrumentStrategies(list):
    def unique_join_with_other_list(self, other):
        return listOfInstrumentStrategies(set(list(self + other)))

    def get_list_of_strategies(self) -> list:
        list_of_strategies = list(
            set([instrument_strategy.strategy_name for instrument_strategy in self])
        )

        return list_of_strategies

    def get_list_of_instruments_for_strategy(self, strategy_name: str) -> list:
        list_of_instrument_strategies = (
            self.get_list_of_instrument_strategies_for_strategy(strategy_name)
        )
        list_of_instruments = [
            instrument_strategy.instrument_code
            for instrument_strategy in list_of_instrument_strategies
        ]

        return list_of_instruments

    def get_list_of_instrument_strategies_for_strategy(self, strategy_name: str):
        list_of_instrument_strategies = [
            instrument_strategy
            for instrument_strategy in self
            if instrument_strategy.strategy_name == strategy_name
        ]

        return list_of_instrument_strategies

    def filter_to_remove_list_of_instruments(self, list_of_instruments_to_remove: list):
        filtered_list = [
            instrument_strategy
            for instrument_strategy in self
            if instrument_strategy.instrument_code not in list_of_instruments_to_remove
        ]
        return listOfInstrumentStrategies(filtered_list)

    def filter_to_remove_list_of_strategies(self, list_of_strategies_to_remove: list):
        filtered_list = [
            instrument_strategy
            for instrument_strategy in self
            if instrument_strategy.strategy_name not in list_of_strategies_to_remove
        ]
        return listOfInstrumentStrategies(filtered_list)


STRATEGY_NAME_KEY = "strategy_name"
INSTRUMENT_CODE_KEY = "instrument_code"


class instrumentStrategy(tradeableObject):
    def __init__(self, strategy_name: str, instrument_code: str):
        instrument_object = futuresInstrument(instrument_code)
        self._instrument = instrument_object
        self._strategy_name = strategy_name

    def __hash__(self):
        return self.instrument_code.__hash__() + self.strategy_name.__hash__()

    def __repr__(self):
        return self.key

    @property
    def key(self):
        return "%s %s" % (self.strategy_name, str(self.instrument))

    @property
    def old_key(self):
        return self.strategy_name + "/" + str(self.instrument)

    def __eq__(self, other):
        if self.instrument != other.instrument:
            return False

        if self.strategy_name != other.strategy_name:
            return False

        return True

    @property
    def instrument(self):
        return self._instrument

    @property
    def instrument_code(self):
        return self.instrument.instrument_code

    @property
    def strategy_name(self):
        return self._strategy_name

    def as_dict(self):
        return {
            STRATEGY_NAME_KEY: self.strategy_name,
            INSTRUMENT_CODE_KEY: self.instrument_code,
        }

    @classmethod
    def from_dict(instrumentStrategy, attr_dict):
        return instrumentStrategy(
            attr_dict[STRATEGY_NAME_KEY], attr_dict[INSTRUMENT_CODE_KEY]
        )

    @classmethod
    def from_key(instrumentStrategy, key):
        if key.find("/") > -1:
            strategy_name, instrument_code = key.split("/")
        else:
            strategy_name, instrument_code = key.split(" ")
        return instrumentStrategy(
            strategy_name=strategy_name, instrument_code=instrument_code
        )


class futuresContractStrategy(tradeableObject):
    def __init__(self, strategy_name: str, instrument_code: str, contract_id):
        """

        :param strategy_name: str
        :param instrument_code: str
        :param contract_id: a single contract_order_id YYYYMM, or a list of contract IDS YYYYMM for a spread order
        """
        self._contract_date = contractDate(contract_id)
        self._instrument = futuresInstrument(instrument_code)
        self._strategy_name = strategy_name

    @classmethod
    def from_strategy_name_and_contract_object(
        futuresContractStrategy, strategy_name: str, futures_contract: futuresContract
    ):
        return futuresContractStrategy(
            strategy_name=strategy_name,
            contract_id=futures_contract.date_str,
            instrument_code=futures_contract.instrument_code,
        )

    def __eq__(self, other):
        if self.instrument != other.instrument:
            return False

        if self.strategy_name != other.strategy_name:
            return False

        if self.contract_date != other.contract_date:
            return False

        return True

    @property
    def futures_contract(self) -> futuresContract:
        return futuresContract(self.instrument, self.contract_date)

    @property
    def instrument_strategy(self) -> instrumentStrategy:
        return instrumentStrategy(
            instrument_code=self.instrument_code, strategy_name=self.strategy_name
        )

    @classmethod
    def from_key(instrumentTradeableObject, key):
        strategy_name, instrument_code, contract_id_str = key.split("/")

        return instrumentTradeableObject(
            strategy_name, instrument_code, contract_id_str
        )

    @property
    def contract_date(self):
        return self._contract_date

    @property
    def contract_date_key(self):
        return self.contract_date.key

    @property
    def alt_contract_date_key(self):
        if len(self.contract_date_key) == 6:
            return self.contract_date_key + "00"

        if len(self.contract_date_key) == 8:
            return self.contract_date_key[:6]

    @property
    def strategy_name(self):
        return self._strategy_name

    @property
    def instrument_code(self):
        return self.instrument.instrument_code

    @property
    def instrument(self):
        return self._instrument

    @property
    def key(self):
        return "/".join(
            [self.strategy_name, self.instrument_code, self.contract_date_key]
        )

    @property
    def alt_key(self):
        return "/".join(
            [self.strategy_name, self.instrument_code, self.alt_contract_date_key]
        )

    def sort_idx_for_contracts(self) -> list:
        return self.contract_date.index_of_sorted_contract_dates()

    def sort_contracts_with_idx(self, idx_list: list):
        self.contract_date.sort_with_idx(idx_list)
