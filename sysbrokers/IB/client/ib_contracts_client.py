from copy import copy
from ib_insync import util, ComboLeg, Contract

from sysbrokers.IB.client.ib_client import ibClient
from sysbrokers.IB.ib_instruments import ib_futures_instrument_just_symbol, futuresInstrumentWithIBConfigData, \
    ib_futures_instrument
from sysbrokers.IB.ib_trading_hours import get_trading_hours
from sysbrokers.IB.ib_contracts import (
    resolve_multiple_expiries,
    ibcontractWithLegs)
from sysbrokers.IB.ib_positions import resolveBS


from syscore.objects import missing_contract
from syscore.genutils import list_of_ints_with_highest_common_factor_positive_first

from syslogdiag.log import logger

from sysobjects.contracts import futuresContract



class ibContractsClient(ibClient):
    def broker_get_futures_contract_list(
            self, futures_instrument_with_ib_data: futuresInstrumentWithIBConfigData) -> list:

        specific_log = self.log.setup(
            instrument_code=futures_instrument_with_ib_data.instrument_code
        )

        ibcontract_pattern = ib_futures_instrument(
            futures_instrument_with_ib_data)
        contract_list = self.ib_get_contract_chain(
            ibcontract_pattern, log=specific_log)
        # if no contracts found will be empty

        # Extract expiry date strings from these
        contract_dates = [
            ibcontract.lastTradeDateOrContractMonth for ibcontract in contract_list]

        return contract_dates



    def broker_get_single_contract_expiry_date(
            self, futures_contract_with_ib_data: futuresContract) -> str:
        """
        Return the exact expiry date for a given contract

        :param futures_contract_with_ib_data:  contract where instrument has ib metadata
        :return: YYYYMMDD str
        """
        specific_log = futures_contract_with_ib_data.specific_log(self.log)
        if futures_contract_with_ib_data.is_spread_contract():
            specific_log.warn("Can only find expiry for single leg contract!")
            return missing_contract

        ibcontract = self.ib_futures_contract(
            futures_contract_with_ib_data, always_return_single_leg=True)

        if ibcontract is missing_contract:
            return missing_contract

        expiry_date = ibcontract.lastTradeDateOrContractMonth

        return expiry_date



    def ib_get_trading_hours(self, contract_object_with_ib_data: futuresContract):
        ib_contract = self.ib_futures_contract(
            contract_object_with_ib_data, always_return_single_leg=True
        )
        if ib_contract is missing_contract:
            return missing_contract

        ib_contract_details = self.ib.reqContractDetails(ib_contract)[0]

        try:
            trading_hours = get_trading_hours(ib_contract_details)
        except Exception as e:
            self.log.warn("%s when getting trading hours!" % e)
            return missing_contract

        return trading_hours

    def ib_get_min_tick_size(self, contract_object_with_ib_data: futuresContract):
        ib_contract = self.ib_futures_contract(
            contract_object_with_ib_data, always_return_single_leg=True
        )
        if ib_contract is missing_contract:
            return missing_contract

        ib_contract_details = self.ib.reqContractDetails(ib_contract)[0]

        try:
            min_tick = ib_contract_details.minTick
        except Exception as e:
            self.log.warn("%s when getting min tick size from %s!" % (e, ib_contract_details))
            return missing_contract

        return min_tick

    def ib_futures_contract(
        self,
        futures_contract_with_ib_data,
        always_return_single_leg=False,
        trade_list_for_multiple_legs=None,
        return_leg_data=False,
    ):
        """
        Return a complete and unique IB contract that matches contract_object_with_ib_data
        Doesn't actually get the data from IB, tries to get from cache

        :param futures_contract_with_ib_data: contract, containing instrument metadata suitable for IB
        :return: a single ib contract object
        """
        contract_object_to_use = copy(futures_contract_with_ib_data)
        if always_return_single_leg and contract_object_to_use.is_spread_contract():
            contract_object_to_use = contract_object_to_use.new_contract_with_first_contract_date()

        if getattr(self, "_futures_contract_cache", None) is None:
            self._futures_contract_cache = {}

        if not contract_object_to_use.is_spread_contract():
            trade_list_suffix = ""
        else:
            # WANT TO TREAT EG -2,2 AND -4,4 AS THE SAME BUT DIFFERENT FROM
            # -2,1 OR -1,2,-1...
            trade_list_suffix = str(
                list_of_ints_with_highest_common_factor_positive_first(
                    trade_list_for_multiple_legs
                )
            )

        cache = self._futures_contract_cache
        key = contract_object_to_use.key + trade_list_suffix

        ibcontract_with_legs = cache.get(key, missing_contract)
        if ibcontract_with_legs is missing_contract:
            ibcontract_with_legs = self._get_ib_futures_contract(
                contract_object_to_use,
                trade_list_for_multiple_legs=trade_list_for_multiple_legs,
            )
            cache[key] = ibcontract_with_legs

        if return_leg_data:
            return ibcontract_with_legs
        else:
            return ibcontract_with_legs.ibcontract


    def _get_ib_futures_contract(
        self, contract_object_with_ib_data, trade_list_for_multiple_legs=None
    ):
        """
        Return a complete and unique IB contract that matches futures_contract_object
        This is expensive so not called directly, only by ib_futures_contract which does caching

        :param contract_object_with_ib_data: contract, containing instrument metadata suitable for IB
        :return: a single ib contract object
        """
        # Convert to IB world
        instrument_object_with_metadata = contract_object_with_ib_data.instrument

        if contract_object_with_ib_data.is_spread_contract():
            ibcontract, legs = self._get_spread_ib_futures_contract(
                instrument_object_with_metadata,
                contract_object_with_ib_data.contract_date,
                trade_list_for_multiple_legs=trade_list_for_multiple_legs,
            )
        else:
            ibcontract = self._get_vanilla_ib_futures_contract(
                instrument_object_with_metadata,
                contract_object_with_ib_data.contract_date,
            )
            legs = []

        ibcontract_with_legs = ibcontractWithLegs(ibcontract, legs=legs)

        return ibcontract_with_legs

    def _get_vanilla_ib_futures_contract(
        self, futures_instrument_with_ib_data: futuresInstrumentWithIBConfigData, contract_date
    ):
        """
        Return a complete and unique IB contract that matches contract_object_with_ib_data
        This is expensive so not called directly, only by ib_futures_contract which does caching

        :param contract_object_with_ib_data: contract, containing instrument metadata suitable for IB
        :return: a single ib contract object
        """

        # The contract date might be 'yyyymm' or 'yyyymmdd'
        ibcontract = ib_futures_instrument(futures_instrument_with_ib_data)

        contract_day_passed = contract_date.is_day_defined()
        if contract_day_passed:
            # Already have the expiry
            pass
        else:
            # Don't have the expiry so lose the days at the end so it's just
            # 'YYYYMM'
            contract_date = str(contract_date.date_str)[:6]

        ibcontract.lastTradeDateOrContractMonth = contract_date

        # We allow multiple contracts in case we have 'yyyymm' and not
        # specified expiry date for VIX
        ibcontract_list = self.ib_get_contract_chain(ibcontract)

        if len(ibcontract_list) == 0:
            # No contracts found
            return missing_contract

        if len(ibcontract_list) == 1:
            # OK no hassle, only one contract no confusion
            resolved_contract = ibcontract_list[0]
        else:
            # It might be a contract with weekly expiries (probably VIX)
            # We need to find the right one
            try:
                resolved_contract = resolve_multiple_expiries(
                    ibcontract_list, futures_instrument_with_ib_data
                )
            except Exception as exception:
                self.log.warn(
                    "%s could not resolve contracts: %s"
                    % (str(futures_instrument_with_ib_data), exception.args[0])
                )

                return missing_contract

        return resolved_contract

    def _get_spread_ib_futures_contract(
        self,
        futures_instrument_with_ib_data: futuresInstrumentWithIBConfigData,
        contract_date,
        trade_list_for_multiple_legs=[-1, 1],
    ):
        """
        Return a complete and unique IB contract that matches contract_object_with_ib_data
        This is expensive so not called directly, only by ib_futures_contract which does caching

        :param contract_object_with_ib_data: contract, containing instrument metadata suitable for IB
        :return: a single ib contract object
        """
        # Convert to IB world
        ibcontract = ib_futures_instrument(futures_instrument_with_ib_data)
        ibcontract.secType = "BAG"

        list_of_contract_dates = contract_date.list_of_single_contract_dates
        resolved_legs = [
            self._get_vanilla_ib_futures_contract(
                futures_instrument_with_ib_data, contract_date
            )
            for contract_date in list_of_contract_dates
        ]

        ratio_list = list_of_ints_with_highest_common_factor_positive_first(
            trade_list_for_multiple_legs
        )

        def _get_ib_combo_leg(ratio, resolved_leg):

            leg = ComboLeg()
            leg.conId = int(resolved_leg.conId)
            leg.exchange = str(resolved_leg.exchange)

            action, size = resolveBS(ratio)

            leg.ratio = int(size)
            leg.action = str(action)

            return leg

        ibcontract.comboLegs = [
            _get_ib_combo_leg(ratio, resolved_leg)
            for ratio, resolved_leg in zip(ratio_list, resolved_legs)
        ]

        return ibcontract, resolved_legs

    def ib_resolve_unique_contract(self, ibcontract_pattern, log:logger=None):
        """
        Returns the 'resolved' IB contract based on a pattern. We expect a unique contract.

        :param ibcontract_pattern: ibContract
        :param log: log object
        :return: ibContract or missing_contract
        """
        if log is None:
            log = self.log

        contract_chain = self.ib_get_contract_chain(
            ibcontract_pattern, log=log)

        if len(contract_chain) > 1:
            log.warn(
                "Got multiple contracts for %s when only expected a single contract: Check contract date" %
                str(ibcontract_pattern))
            return missing_contract
        if len(contract_chain) == 0:
            log.warn("Failed to resolve contract %s" % str(ibcontract_pattern))
            return missing_contract

        resolved_contract = contract_chain[0]

        return resolved_contract

    def ib_get_contract_with_conId(self, symbol, conId):
        ibcontract_pattern = ib_futures_instrument_just_symbol(symbol)
        contract_chain = self.ib_get_contract_chain(ibcontract_pattern)
        conId_list = [contract.conId for contract in contract_chain]
        try:
            contract_idx = conId_list.index(conId)
        except ValueError:
            return missing_contract
        required_contract = contract_chain[contract_idx]

        return required_contract

    def ib_get_contract_chain(self, ibcontract_pattern, log=None):
        """
        Get all the IB contracts matching a pattern.

        :param ibcontract_pattern: ibContract which may not fully specify the contract
        :param log: log object
        :return: list of ibContracts
        """

        if log is None:
            log = self.log

        new_contract_details_list = self.ib.reqContractDetails(
            ibcontract_pattern)

        ibcontract_list = [
            contract_details.contract for contract_details in new_contract_details_list]

        return ibcontract_list
