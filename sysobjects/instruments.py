from dataclasses import  dataclass
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
        return futuresInstrument(input_dict['instrument_code'])

    def as_dict(self):
        # Might seem pointless, but (a) is used in original code, (b) gives a nice consistent feel
        return dict(instrument_code = self.instrument_code)

    def __eq__(self, other):
        return self.instrument_code == other.instrument_code

    def key(self):
        return self.instrument_code

    def __repr__(self):
        return str(self.instrument_code)

@dataclass
class instrumentMetaData:
    Description: str = ""
    Pointsize: float = 0.0
    Currency: str =  ""
    AssetClass: str = ""
    Slippage:  float = 0.0
    PerBlock:  float = 0.0
    Percentage: float = 0.0
    PerTrade:  float = 0.0

    def as_dict(self) -> dict:
        keys = self.__dataclass_fields__.keys()
        self_as_dict = dict([(key, getattr(self, key)) for key in keys])

        return self_as_dict

    @classmethod
    def from_dict(instrumentMetaData, input_dict):
        keys = instrumentMetaData.__dataclass_fields__.keys()
        args_list = [input_dict[key] for key in keys]

        return instrumentMetaData(*args_list)

@dataclass
class futuresInstrumentWithMetaData:
    instrument: futuresInstrument
    meta_data: instrumentMetaData

    @property
    def instrument_code(self) ->str:
        return self.instrument.instrument_code

    @property
    def key(self) ->str:
        return self.instrument_code

    def as_dict(self)-> dict:
        meta_data_dict = self.meta_data.as_dict()
        meta_data_dict['instrument_code'] = self.instrument_code

        return meta_data_dict

    @classmethod
    def from_dict(futuresInstrumentWithMetaData, input_dict):
        instrument_code = input_dict.pop('instrument_code')
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

class listOffuturesInstrumentWithMetaData(list):
    def as_df(self):
        instrument_codes = [instrument_object.instrument_code for instrument_object in self]
        meta_data_keys = [
            instrument_object.meta_data.as_dict().keys()
            for instrument_object in self
        ]
        meta_data_keys_flattened = [
            item for sublist in meta_data_keys for item in sublist
        ]
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