import numpy as np
from copy import copy
from syscore.constants import arg_not_supplied
from syscore.genutils import flatten_list
from dataclasses import dataclass
import pandas as pd

EMPTY_INSTRUMENT = ""


class futuresInstrument(object):
    def __init__(self, instrument_code: str):
        self._instrument_code = instrument_code

    @property
    def instrument_code(self):
        return self._instrument_code

    def empty(self):
        return self.instrument_code == EMPTY_INSTRUMENT

    @classmethod
    def create_from_dict(futuresInstrument, input_dict):
        # Might seem pointless, but (a) is used in original code, (b) gives a nice consistent feel
        return futuresInstrument(input_dict["instrument_code"])

    def as_dict(self):
        # Might seem pointless, but (a) is used in original code, (b) gives a nice consistent feel
        return dict(instrument_code=self.instrument_code)

    def __eq__(self, other):
        return self.instrument_code == other.instrument_code

    @property
    def key(self):
        return self.instrument_code

    def __repr__(self):
        return str(self.instrument_code)


META_FIELD_LIST = [
    "Description",
    "Pointsize",
    "Currency",
    "AssetClass",
    "Slippage",
    "PerBlock",
    "Percentage",
    "PerTrade",
    "Region",
]


def _zero_if_nan(x):
    if np.isnan(x):
        return 0
    else:
        return x


NO_REGION = "NO_REGION"


def _string_if_nan(x, string=NO_REGION):
    if np.isnan(x):
        return string
    else:
        return x


class instrumentMetaData(object):
    def __init__(
        self,
        Description: str = "",
        Pointsize: float = 0.0,
        Currency: str = "",
        AssetClass: str = "",
        Slippage: float = 0.0,
        PerBlock: float = 0.0,
        Percentage: float = 0.0,
        PerTrade: float = 0.0,
        Region: str = "",
    ):

        self.Description = Description
        self.Currency = Currency
        self.Pointsize = _zero_if_nan(Pointsize)
        self.AssetClass = AssetClass
        self.Slippage = _zero_if_nan(Slippage)
        self.PerBlock = _zero_if_nan(PerBlock)
        self.Percentage = _zero_if_nan(Percentage)
        self.PerTrade = _zero_if_nan(PerTrade)
        self.Region = Region

    def as_dict(self) -> dict:
        keys = META_FIELD_LIST
        self_as_dict = dict([(key, getattr(self, key)) for key in keys])

        return self_as_dict

    @classmethod
    def from_dict(instrumentMetaData, input_dict):
        keys = list(input_dict.keys())
        args_list = [input_dict[key] for key in keys]

        return instrumentMetaData(*args_list)

    def __eq__(self, other):
        return self.as_dict() == other.as_dict()

    def __repr__(self):
        return str(self.as_dict())


@dataclass
class futuresInstrumentWithMetaData:
    instrument: futuresInstrument
    meta_data: instrumentMetaData

    @property
    def instrument_code(self) -> str:
        return self.instrument.instrument_code

    @property
    def key(self) -> str:
        return self.instrument_code

    def as_dict(self) -> dict:
        meta_data_dict = self.meta_data.as_dict()
        meta_data_dict["instrument_code"] = self.instrument_code

        return meta_data_dict

    @classmethod
    def from_dict(futuresInstrumentWithMetaData, input_dict):
        instrument_code = input_dict.pop("instrument_code")
        instrument = futuresInstrument(instrument_code)
        meta_data = instrumentMetaData.from_dict(input_dict)

        return futuresInstrumentWithMetaData(instrument, meta_data)

    @classmethod
    def create_empty(futuresInstrumentWithMetaData):
        instrument = futuresInstrument(EMPTY_INSTRUMENT)
        meta_data = instrumentMetaData()

        instrument_with_metadata = futuresInstrumentWithMetaData(instrument, meta_data)

        return instrument_with_metadata

    def empty(self):
        return self.instrument.empty()

    def __eq__(self, other):
        instrument_matches = self.instrument == other.instrument
        meta_data_matches = self.meta_data == other.meta_data

        return instrument_matches and meta_data_matches


class listOfFuturesInstrumentWithMetaData(list):
    def as_df(self):
        instrument_codes = [
            instrument_object.instrument_code for instrument_object in self
        ]
        meta_data_keys = [
            instrument_object.meta_data.as_dict().keys() for instrument_object in self
        ]
        meta_data_keys_flattened = flatten_list(meta_data_keys)
        meta_data_keys_unique = list(set(meta_data_keys_flattened))

        meta_data_as_lists = dict(
            [
                (
                    metadata_name,
                    [
                        getattr(instrument_object.meta_data, metadata_name)
                        for instrument_object in self
                    ],
                )
                for metadata_name in meta_data_keys_unique
            ]
        )

        meta_data_as_dataframe = pd.DataFrame(
            meta_data_as_lists, index=instrument_codes
        )

        return meta_data_as_dataframe


class assetClassesAndInstruments(dict):
    def __repr__(self):
        return str(self.as_pd())

    def get_instrument_list(self) -> list:
        return list(self.keys())

    @classmethod
    def from_pd_series(self, pd_series: pd.Series):
        instruments = list(pd_series.index)
        asset_classes = list(pd_series.values)
        as_dict = dict(
            [
                (instrument_code, asset_class)
                for instrument_code, asset_class in zip(instruments, asset_classes)
            ]
        )

        return assetClassesAndInstruments(as_dict)

    def all_asset_classes(self) -> list:
        asset_classes = list(self.values())
        unique_asset_classes = list(set(asset_classes))
        unique_asset_classes.sort()

        return unique_asset_classes

    def as_pd(self) -> pd.Series:
        instruments = [key for key in self.keys()]
        asset_classes = [value for value in self.values()]

        return pd.Series(asset_classes, index=instruments)

    def all_instruments_in_asset_class(
        self, asset_class: str, must_be_in=arg_not_supplied
    ) -> list:

        asset_class_instrument_list = [
            instrument
            for instrument, item_asset_class in self.items()
            if item_asset_class == asset_class
        ]

        if must_be_in is arg_not_supplied:
            return asset_class_instrument_list

        ## we need to filter
        filtered_asset_class_instrument_list = [
            instrument
            for instrument in asset_class_instrument_list
            if instrument in must_be_in
        ]

        return filtered_asset_class_instrument_list


class instrumentCosts(object):
    def __init__(
        self,
        price_slippage: float = 0.0,
        value_of_block_commission: float = 0.0,
        percentage_cost: float = 0.0,
        value_of_pertrade_commission: float = 0.0,
    ):
        self._price_slippage = price_slippage
        self._value_of_block_commission = value_of_block_commission
        self._percentage_cost = percentage_cost
        self._value_of_pertrade_commission = value_of_pertrade_commission

    @classmethod
    def from_meta_data(instrumentCosts, meta_data: instrumentMetaData):
        return instrumentCosts(
            price_slippage=meta_data.Slippage,
            value_of_block_commission=meta_data.PerBlock,
            percentage_cost=meta_data.Percentage,
            value_of_pertrade_commission=meta_data.PerTrade,
        )

    def __repr__(self):
        return (
            "instrumentCosts slippage %f block_commission %f percentage cost %f per trade commission %f "
            % (
                self.price_slippage,
                self.value_of_block_commission,
                self.percentage_cost,
                self.value_of_pertrade_commission,
            )
        )

    def commission_only(self):
        new_costs = instrumentCosts(
            price_slippage=0.0,
            value_of_block_commission=self.value_of_block_commission,
            percentage_cost=self.percentage_cost,
            value_of_pertrade_commission=self.value_of_pertrade_commission,
        )

        return new_costs

    def spread_only(self):
        new_costs = instrumentCosts(
            price_slippage=self.price_slippage,
            value_of_block_commission=0,
            percentage_cost=0,
            value_of_pertrade_commission=0,
        )

        return new_costs

    @property
    def price_slippage(self):
        return self._price_slippage

    @property
    def value_of_block_commission(self):
        return self._value_of_block_commission

    @property
    def percentage_cost(self):
        return self._percentage_cost

    @property
    def value_of_pertrade_commission(self):
        return self._value_of_pertrade_commission

    def calculate_cost_percentage_terms(
        self, blocks_traded: float, block_price_multiplier: float, price: float
    ) -> float:
        cost_in_currency_terms = self.calculate_cost_instrument_currency(
            blocks_traded, block_price_multiplier=block_price_multiplier, price=price
        )

        value_per_block = price * block_price_multiplier
        total_value = blocks_traded * value_per_block
        cost_in_percentage_terms = cost_in_currency_terms / total_value

        return cost_in_percentage_terms

    def calculate_cost_instrument_currency(
        self, blocks_traded: float, block_price_multiplier: float, price: float
    ) -> float:

        value_per_block = price * block_price_multiplier
        slippage = self.calculate_slippage_instrument_currency(
            blocks_traded, block_price_multiplier=block_price_multiplier
        )

        commission = self.calculate_total_commission(
            blocks_traded, value_per_block=value_per_block
        )

        return slippage + commission

    def calculate_total_commission(self, blocks_traded: float, value_per_block: float):
        ### YOU WILL NEED TO CHANGE THIS IF YOUR BROKER HAS A MORE COMPLEX STRUCTURE
        per_trade_commission = self.calculate_per_trade_commission()
        per_block_commission = self.calculate_cost_per_block_commission(blocks_traded)
        percentage_commission = self.calculate_percentage_commission(
            blocks_traded, value_per_block
        )

        return max([per_block_commission, per_trade_commission, percentage_commission])

    def calculate_slippage_instrument_currency(
        self, blocks_traded: float, block_price_multiplier: float
    ) -> float:
        return abs(blocks_traded) * self.price_slippage * block_price_multiplier

    def calculate_per_trade_commission(self):
        return self.value_of_pertrade_commission

    def calculate_cost_per_block_commission(self, blocks_traded):
        return abs(blocks_traded) * self.value_of_block_commission

    def calculate_percentage_commission(self, blocks_traded, price_per_block):
        trade_value = self.calculate_trade_value(blocks_traded, price_per_block)
        return self._percentage_cost * trade_value

    def calculate_trade_value(self, blocks_traded, value_per_block):
        return abs(blocks_traded) * value_per_block
