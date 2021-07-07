from sysexecution.tick_data import dataFrameOfRecentTicks
from sysexecution.stack_handler.stackHandlerCore import stackHandlerCore
from sysobjects.contracts import futuresContract

class stackHandlerAdditionalSampling(stackHandlerCore):

    def refresh_additional_sampling_all_instruments(self):
        all_contracts = self.get_all_instruments_priced_contracts()
        for contract in all_contracts:
            self.refresh_sampling_for_contract(contract)

    def get_all_instruments_priced_contracts(self):
        ## Cache for speed
        priced_contracts = getattr(self, "_all_priced_contracts", None)
        if priced_contracts is None:
            priced_contracts = self._get_all_instruments_priced_contracts_from_db()
            self._all_priced_contracts = priced_contracts

        return priced_contracts

    def _get_all_instruments_priced_contracts_from_db(self):
        instrument_list = self._get_all_instruments()
        data_contracts = self.data_contracts
        priced_contracts = [data_contracts.get_priced_contract_id(instrument_code)
                            for instrument_code in instrument_list]

        return priced_contracts


    def _get_all_instruments(self):
        diag_prices = self.diag_prices
        instrument_list = diag_prices.get_list_of_instruments_with_contract_prices()

        return instrument_list

    def refresh_sampling_for_contract(self, contract: futuresContract):

        okay_to_sample = self.is_contract_currently_okay_to_sample(contract)
        if not okay_to_sample:
            return None

        self.refresh_sampling_without_checks(contract)


    def is_contract_currently_okay_to_sample(self, contract:futuresContract) -> bool:
        data_broker = self.data_broker
        okay_to_sample =\
            data_broker.is_contract_conservatively_okay_to_trade(contract)

        return okay_to_sample


    def refresh_sampling_without_checks(self, contract: futuresContract):
        average_spread = self.get_average_spread(contract)
        self.add_spread_data_to_db(contract, average_spread)

    def get_average_spread(self, contract:futuresContract) -> float:
        data_broker = self.data_broker
        tick_data = data_broker.get_recent_bid_ask_tick_data_for_contract_object(contract)

        average_spread = tick_data.average_bid_offer_spread()

        return average_spread

    def add_spread_data_to_db(self, contract: futuresContract,
                              average_spread: float):

        ## we store by instrument
        instrument_code = contract.instrument_code
        update_prices = self.update_prices

        update_prices.add_spread_entry(instrument_code, spread=average_spread)

    def mark_contract_sampled(self, contract:futuresContract):
        key = contract.key
        store = self.sampling_store

        if key not in store:
            store.append(key)

        self.sampling_store = store

    @property
    def sampling_store(self)-> list:
        sampling_store = getattr(self, "_sampling_store", None)
        if sampling_store is None:
            sampling_store = []
            self._sampling_store = sampling_store

        return sampling_store

    @sampling_store.setter
    def sampling_store(self, new_store):
        self._sampling_store = new_store