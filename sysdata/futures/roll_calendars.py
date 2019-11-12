from sysdata.data import baseData
from sysdata.futures.rolls import contractDateWithRollParameters
from sysdata.futures.contract_dates_and_expiries import contractDate

import pandas as pd
import numpy as np


def _find_best_matching_roll_date(roll_date, current_prices, next_prices):
    """
    Find the closest valid roll date for which we have overlapping prices

    :param roll_date: datetime.datetime
    :param current_prices: pd.Series
    :param next_prices: pd.Series

    :return: datetime.datetime or
    """

    # Get the list of dates for which
    paired_prices = pd.concat([current_prices, next_prices], axis=1)
    paired_prices_check_match = paired_prices.apply(lambda xlist: not any(np.isnan(xlist)), axis=1)
    paired_prices_matching = paired_prices_check_match[paired_prices_check_match]
    matching_dates = paired_prices_matching.index

    if len(matching_dates)==0:
        # no matching prices
        raise LookupError("No date with a matching price for current and next contract")

    # Find closest distance
    distance_to_roll = matching_dates - roll_date
    distance_to_roll_days = [abs(distance_item.days) for distance_item in distance_to_roll]
    closest_date_index = distance_to_roll_days.index(min(distance_to_roll_days))
    closest_date = matching_dates[closest_date_index]

    return closest_date

def _generate_approximate_calendar(list_of_contract_dates, roll_parameters_object):
    """
    Using a rollData object we work out roughly what the rolls should be (in an ideal world with available prices all the time)
      for contracts held between start_date and end_date

    Called by __init__

    :param list_of_contracts: list of contract_date ids, eg 'yyyymmdd'
    :param roll_parameters_object: rollData

    :return: data frame ready to be rollCalendar
    """

    contracts_with_roll_data = [contractDateWithRollParameters(roll_parameters_object, contract_date)
                                     for contract_date in list_of_contract_dates]

    theoretical_roll_dates=[contract_date.want_to_roll() for contract_date in
                            contracts_with_roll_data]

    # On the roll date we stop holding the current contract, and end up holding the next one
    contracts_to_hold_on_each_roll = contracts_with_roll_data[:-1]
    contract_dates_to_hold_on_each_roll = [contract.contract_date for contract in contracts_to_hold_on_each_roll]

    # We also need a list of the next contract along
    next_contract_along = contracts_with_roll_data[1:]
    contract_dates_next_contact_along = [contract.contract_date for contract in next_contract_along]

    # we don't know what the next contract will be, so we drop the last roll date
    theoretical_roll_dates = theoretical_roll_dates[:-1]

    roll_calendar = pd.DataFrame(dict(current_contract = contract_dates_to_hold_on_each_roll,
                                      next_contract = contract_dates_next_contact_along), index = theoretical_roll_dates)

    return roll_calendar


def _adjust_to_price_series(approx_calendar, dict_of_futures_contract_prices):
    """
    Adjust an approximate roll calendar so that we have matching dates on each expiry


    :param approx_calendar: Approximate roll calendar pd.dataFrame with columns current_contract, next_contract
    :param dict_of_futures_contract_prices: dict of futuresContractPrices, keys contract date eg yyyymmdd

    :return: pd.dataFrame with columns current_contract, next_contract
    """

    adjusted_date_list = []

    for row_number in range(len(approx_calendar.index)):
        calendar_row = approx_calendar.iloc[row_number,:]
        current_contract = calendar_row.current_contract
        next_contract = calendar_row.next_contract
        roll_date = approx_calendar.index[row_number]
        current_prices = dict_of_futures_contract_prices[current_contract]
        next_prices = dict_of_futures_contract_prices[next_contract]

        try:
            adjusted_date = _find_best_matching_roll_date(roll_date, current_prices, next_prices)
        except LookupError:
            raise Exception("Couldn't find matching roll date for contracts %s and %s" % (current_contract, next_contract))

        adjusted_date_list.append(adjusted_date)

    new_calendar = pd.DataFrame(dict(current_contract = approx_calendar.current_contract.values,
                                     next_contract = approx_calendar.next_contract.values),
                                index = adjusted_date_list)

    return new_calendar

def _add_carry_calendar(roll_calendar, roll_parameters_object):
    """

    :param roll_calendar: pdDataFrame with current_contract and next_contract
    :param roll_parameters_object: rollData

    :return: data frame ready to be rollCalendar
    """

    list_of_contract_dates = list(roll_calendar.current_contract.values)
    contracts_with_roll_data = [contractDateWithRollParameters(roll_parameters_object, str(contract_date))
                                     for contract_date in list_of_contract_dates]

    carry_contracts = [contract.carry_contract().contract_date for contract in contracts_with_roll_data]

    roll_calendar['carry_contract'] = carry_contracts

    return roll_calendar

class rollCalendar(pd.DataFrame):
    """
    A roll calendar is a dataframe telling us when we have rolled futures contracts in the past (or would have in a backtest)

    It has a datetime index, and two columns; current_contract and next_contract

    Normally a roll calendar would be created using the following process: (and this is what __init__ does)
     - start with a list of futures contracts and some rollParameters
     - using a rollParameters object we work out roughly what the rolls should be (in an ideal world with available prices all the time)
     - then using a list of futures contract price data we shift the rolls around so that rolls are possible on a given date

    Another way of getting a roll calendar is to back it out from an existing 'carry data' (eg as we have in legacy csv)

    Sometimes you need to manually hack roll calendars, so it's also useful to have a csv convenience method for read/write

    When combined with a list of futures contract price data a roll calendar can be used to create a back adjusted price series
    This can then be stored.
    (We don't create these 'on line' as it's a bit slow. We can add additional rows to a back adjusted price series just
        from the current price. Then the re-adjustment can happen again on each roll. Could use Arctic vintage method here?)

    """

    @classmethod
    def create_from_prices(rollCalendar,  dict_of_futures_contract_prices, roll_parameters_object):
        """

        :param roll_parameters_object: roll parameters specific to this instrument
        :param dict_of_futures_contract_prices: dict, keys are contract date ids 'yyyymmdd'
        """

        list_of_contract_dates = dict_of_futures_contract_prices.sorted_contract_ids()

        approx_calendar = _generate_approximate_calendar(list_of_contract_dates, roll_parameters_object)

        adjusted_calendar = _adjust_to_price_series(approx_calendar, dict_of_futures_contract_prices)

        adjusted_calendar_with_carry = _add_carry_calendar(adjusted_calendar, roll_parameters_object)
        roll_calendar = rollCalendar(adjusted_calendar_with_carry)

        return roll_calendar

    @classmethod
    def back_out_from_current_and_forward_data(rollCalendar, current_and_forward_data, roll_parameters_object):
        """

        :param current_and_forward_data: output from futuresDataForSim.FuturesData.get_current_and_forward_price_data(instrument_code)
               columns: PRICE, FORWARD, FORWARD_CONTRACT, PRICE_CONTRACT

        :return: rollCalendar
        """
        current_and_forward_unique = current_and_forward_data[~current_and_forward_data.index.duplicated(keep='last')]

        roll_dates = current_and_forward_unique.index[1:][current_and_forward_unique[1:].PRICE_CONTRACT.values>current_and_forward_unique[:-1].PRICE_CONTRACT.values]
        days_before = current_and_forward_unique.index[:-1][current_and_forward_unique[:-1].PRICE_CONTRACT.values<current_and_forward_unique[1:].PRICE_CONTRACT.values]

        ## Duplicates are possible (double rolls)

        current_contracts = [contractDate(current_and_forward_unique.loc[date_index].PRICE_CONTRACT).contract_date for date_index in days_before]
        next_contracts = [contractDate(current_and_forward_unique.loc[date_index].PRICE_CONTRACT).contract_date for date_index in roll_dates]

        roll_calendar = pd.DataFrame(dict(current_contract = current_contracts,
                                          next_contract = next_contracts), index = roll_dates)

        roll_calendar_with_carry = _add_carry_calendar(roll_calendar, roll_parameters_object)
        roll_calendar_object = rollCalendar(roll_calendar_with_carry)

        return roll_calendar_object



    def check_if_date_index_monotonic(self):
        if not self.index._is_strictly_monotonic_increasing:
            print("WARNING: Date index not monotonically increasing in following indices:")

            not_monotonic = self.index[1:][self.index[1:]<=self.index[:-1]]
            print(not_monotonic)

            return False
        else:
            return True

    def check_dates_are_valid_for_prices(self, dict_of_futures_contract_prices):
        """
        Adjust an approximate roll calendar so that we have matching dates on each expiry

        :param dict_of_futures_contract_prices: dict of futuresContractPrices, keys contract date eg yyyymmdd

        :return: bool, True if no problems
        """

        checks_okay = True
        for row_number in range(len(self.index)):
            calendar_row = self.iloc[row_number, :]
            current_contract = calendar_row.current_contract
            next_contract = calendar_row.next_contract
            carry_contract = calendar_row.carry_contract
            roll_date = self.index[row_number]

            try:
                current_prices = dict_of_futures_contract_prices[current_contract]
            except KeyError:
                print("On roll date %s contract %s is missing from futures prices" % (roll_date, current_contract))
                checks_okay = False
            try:
                next_prices = dict_of_futures_contract_prices[next_contract]
            except KeyError:
                print("On roll date %s contract %s is missing from futures prices" % (roll_date, next_contract))
                checks_okay = False

            try:
                carry_prices = dict_of_futures_contract_prices[carry_contract]
            except KeyError:
                print("On roll date %s contract %s is missing from futures prices" % (roll_date, carry_contract))
                checks_okay = False

            try:
                current_price = current_prices.loc[roll_date]
            except KeyError:
                print("Roll date %s missing from prices for %s" % (roll_date, current_contract))
                checks_okay = False

            try:
                next_price = next_prices.loc[roll_date]
            except KeyError:
                print("Roll date %s missing from prices for %s" % (roll_date, next_contract))
                checks_okay = False

            if np.isnan(current_price):
                print("NAN for price on %s for %s " % (roll_date, current_contract))
                checks_okay = False

            if np.isnan(next_price):
                print("NAN for price on %s for %s " % (roll_date, current_contract))
                checks_okay = False

        return checks_okay

    def last_current_contract(self):
        """
        Returns the oldest contract in the final row of the row calendar

        :return: contractDate
        """

        final_row = self.tail(1).values
        last_contract_numeric = final_row.max()
        last_contract = contractDate(str(last_contract_numeric))

        return last_contract

USE_CHILD_CLASS_ROLL_CALENDAR_ERROR = "You need to use a child class of rollCalendarData"


class rollCalendarData(baseData):
    """
    Class to read / write roll calendars

    We wouldn't normally use this base class, but inherit from it for a specific data source eg Arctic
    """

    def __repr__(self):
        return "rollCalendarData base class - DO NOT USE"

    def keys(self):
        return self.get_list_of_instruments()

    def get_list_of_instruments(self):
        raise NotImplementedError(USE_CHILD_CLASS_ROLL_CALENDAR_ERROR)

    def get_roll_calendar(self, instrument_code):
        if self.is_code_in_data(instrument_code):
            return self._get_roll_calendar_without_checking(instrument_code)
        else:
            return rollCalendar.create_empty()

    def _get_roll_calendar_without_checking(self, instrument_code):
        raise NotImplementedError(USE_CHILD_CLASS_ROLL_CALENDAR_ERROR)

    def __getitem__(self, instrument_code):
        return self.get_roll_calendar(instrument_code)

    def delete_roll_calendar(self, instrument_code, are_you_sure=False):
        self.log.label(instrument_code=instrument_code)

        if are_you_sure:
            if self.is_code_in_data(instrument_code):
                self._delete_roll_calendar_data_without_any_warning_be_careful(instrument_code)
                self.log.terse("Deleted roll calendar for %s" % instrument_code)

            else:
                ## doesn't exist anyway
                self.log.warn("Tried to delete roll calendar for non existent instrument code %s" % instrument_code)
        else:
            self.log.error("You need to call delete_roll_calendar with a flag to be sure")

    def _delete_roll_calendar_data_without_any_warning_be_careful(instrument_code):
        raise NotImplementedError(USE_CHILD_CLASS_ROLL_CALENDAR_ERROR)

    def is_code_in_data(self, instrument_code):
        if instrument_code in self.get_list_of_instruments():
            return True
        else:
            return False

    def add_roll_calendar(self, roll_calendar, instrument_code, ignore_duplication=False):

        self.log.label(instrument_code=instrument_code)

        if self.is_code_in_data(instrument_code):
            if ignore_duplication:
                pass
            else:
                raise self.log.warn("There is already %s in the data, you have to delete it first" % instrument_code)

        self._add_roll_calendar_without_checking_for_existing_entry(roll_calendar, instrument_code)

        self.log.terse("Added roll calendar for instrument %s" % instrument_code)

    def _add_roll_calendar_without_checking_for_existing_entry(self, roll_calendar, instrument_code):
        raise NotImplementedError(USE_CHILD_CLASS_ROLL_CALENDAR_ERROR)
