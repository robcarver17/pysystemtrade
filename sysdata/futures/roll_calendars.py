from sysdata.data import baseData
from sysdata.futures.roll_parameters_with_price_data import (
    rollParametersWithPriceData,
    contractWithRollParametersAndPrices,
)

from sysobjects.contract_dates_and_expiries import contractDate
from sysobjects.rolls import contractDateWithRollParameters


import pandas as pd
import numpy as np


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
    def create_from_prices(
        rollCalendar, dict_of_futures_contract_prices, roll_parameters_object
    ):
        """

        :param roll_parameters_object: roll parameters specific to this instrument
        :param dict_of_futures_contract_prices: dict, keys are contract date ids 'yyyymmdd'
        """

        approx_calendar = _generate_approximate_calendar(
            roll_parameters_object, dict_of_futures_contract_prices
        )

        adjusted_calendar = _adjust_to_price_series(
            approx_calendar, dict_of_futures_contract_prices
        )

        roll_calendar = rollCalendar(adjusted_calendar)

        return roll_calendar

    @classmethod
    def back_out_from_current_and_forward_data(
        rollCalendar, current_and_forward_data, roll_parameters_object
    ):
        """

        :param current_and_forward_data: output from futuresDataForSim.FuturesData.get_current_and_forward_price_data(instrument_code)
               columns: PRICE, FORWARD, FORWARD_CONTRACT, PRICE_CONTRACT

        :return: rollCalendar
        """
        current_and_forward_unique = current_and_forward_data[
            ~current_and_forward_data.index.duplicated(keep="last")
        ]

        roll_dates = current_and_forward_unique.index[1:][
            current_and_forward_unique[1:].PRICE_CONTRACT.values
            > current_and_forward_unique[:-1].PRICE_CONTRACT.values
        ]
        days_before = current_and_forward_unique.index[:-1][
            current_and_forward_unique[:-1].PRICE_CONTRACT.values
            < current_and_forward_unique[1:].PRICE_CONTRACT.values
        ]

        # Duplicates are possible (double rolls)

        current_contracts = [
            contractDate(
                current_and_forward_unique.loc[date_index].PRICE_CONTRACT
            ).date
            for date_index in days_before
        ]
        next_contracts = [
            contractDate(
                current_and_forward_unique.loc[date_index].PRICE_CONTRACT
            ).date
            for date_index in roll_dates
        ]
        carry_contracts = [
            contractDate(
                current_and_forward_unique.loc[date_index].CARRY_CONTRACT
            ).date
            for date_index in days_before
        ]

        roll_calendar = pd.DataFrame(
            dict(
                current_contract=current_contracts,
                next_contract=next_contracts,
                carry_contract=carry_contracts,
            ),
            index=roll_dates,
        )

        extra_row = pd.DataFrame(
            dict(
                current_contract=[
                    contractDate(
                        current_and_forward_data.iloc[-1].PRICE_CONTRACT
                    ).date
                ],
                next_contract=[
                    contractDate(
                        current_and_forward_data.iloc[-1].FORWARD_CONTRACT
                    ).date
                ],
                carry_contract=[
                    contractDate(
                        current_and_forward_data.iloc[-1].CARRY_CONTRACT
                    ).date
                ],
            ),
            index=[current_and_forward_data.index[-1]],
        )
        roll_calendar = pd.concat([roll_calendar, extra_row], axis=0)
        roll_calendar_object = rollCalendar(roll_calendar)

        return roll_calendar_object

    def check_if_date_index_monotonic(self):
        if not self.index._is_strictly_monotonic_increasing:
            print(
                "WARNING: Date index not monotonically increasing in following indices:"
            )

            not_monotonic = self.index[1:][self.index[1:] <= self.index[:-1]]
            print(not_monotonic)

            return False
        else:
            return True

    def check_dates_are_valid_for_prices(
            self, dict_of_futures_contract_prices):
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
                print(
                    "On roll date %s contract %s is missing from futures prices" %
                    (roll_date, current_contract))
                checks_okay = False
            try:
                next_prices = dict_of_futures_contract_prices[next_contract]
            except KeyError:
                print(
                    "On roll date %s contract %s is missing from futures prices" %
                    (roll_date, next_contract))
                checks_okay = False

            try:
                carry_prices = dict_of_futures_contract_prices[carry_contract]
            except KeyError:
                print(
                    "On roll date %s contract %s is missing from futures prices" %
                    (roll_date, carry_contract))
                checks_okay = False

            try:
                current_price = current_prices.loc[roll_date]
            except KeyError:
                print(
                    "Roll date %s missing from prices for %s"
                    % (roll_date, current_contract)
                )
                checks_okay = False

            try:
                next_price = next_prices.loc[roll_date]
            except KeyError:
                print(
                    "Roll date %s missing from prices for %s"
                    % (roll_date, next_contract)
                )
                checks_okay = False

            if np.isnan(current_price):
                print(
                    "NAN for price on %s for %s " %
                    (roll_date, current_contract))
                checks_okay = False

            if np.isnan(next_price):
                print(
                    "NAN for price on %s for %s " %
                    (roll_date, current_contract))
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


def _generate_approximate_calendar(
    roll_parameters_object, dict_of_futures_contract_prices
):
    """
    Using a rollData object we work out roughly what the rolls should be (in an ideal world with available prices all the time)
      for contracts held between start_date and end_date

    Called by __init__

    :param dict_of_futures_contract_prices: dict, keys are contract date ids 'yyyymmdd'
    :param roll_parameters_object: rollData

    :return: data frame ready to be rollCalendar
    """
    roll_parameters_with_price_data = rollParametersWithPriceData(
        roll_parameters_object, dict_of_futures_contract_prices
    )
    earliest_contract_with_roll_data = (
        roll_parameters_with_price_data.find_earliest_held_contract_with_data()
    )

    if earliest_contract_with_roll_data is None:
        raise Exception("Can't find any valid starting contract!")

    final_contract_date = dict_of_futures_contract_prices.last_contract_id()

    current_contract = contractWithRollParametersAndPrices(
        earliest_contract_with_roll_data, dict_of_futures_contract_prices
    )
    theoretical_roll_dates = []
    contract_dates_to_hold_on_each_roll = []
    contract_dates_next_contract_along = []
    carry_contracts_to_hold_on_each_roll = []

    # On the roll date we stop holding the current contract, and end up holding the next one
    # The roll date is the last day we hold the current contract
    while current_contract.contract_date < final_contract_date:

        next_contract = current_contract.find_next_held_contract_with_price_data()
        if next_contract is None:
            # This is a problem UNLESS for the corner case where:
            # The current contract isn't the last contract
            # But the remaining contracts aren't held contracts
            if (
                current_contract.next_held_contract().date
                > final_contract_date
            ):
                # We are done
                break
            else:
                raise Exception(
                    "Can't find good next contract date %s from data when building roll calendar using hold calendar %s" %
                    (carry_contract.date, str(
                        roll_parameters_object.hold_rollcycle), ))

        carry_contract = current_contract.find_best_carry_contract_with_price_data()
        if carry_contract is None:
            raise Exception(
                "Can't find good carry contract %s from data when building roll calendar using hold calendar %s" %
                (current_contract.contract_date, str(
                    roll_parameters_object.hold_rollcycle), ))

        contract_dates_to_hold_on_each_roll.append(
            current_contract.contract_date)
        contract_dates_next_contract_along.append(next_contract.date)
        carry_contracts_to_hold_on_each_roll.append(
            carry_contract.date)

        current_roll_date = current_contract.want_to_roll()
        theoretical_roll_dates.append(current_roll_date)

        current_contract = next_contract

    roll_calendar = pd.DataFrame(
        dict(
            current_contract=contract_dates_to_hold_on_each_roll,
            next_contract=contract_dates_next_contract_along,
            carry_contract=carry_contracts_to_hold_on_each_roll,
        ),
        index=theoretical_roll_dates,
    )

    return roll_calendar


def _adjust_to_price_series(approx_calendar, dict_of_futures_contract_prices):
    """
    Adjust an approximate roll calendar so that we have matching dates on each expiry for price, carry and next contract

    :param approx_calendar: Approximate roll calendar pd.dataFrame with columns current_contract, next_contract, carry_contract
    :param dict_of_futures_contract_prices: dict of futuresContractPrices, keys contract date eg yyyymmdd

    :return: pd.dataFrame with columns current_contract, next_contract
    """

    adjusted_date_list = []
    carry_contracts = []
    current_contracts = []
    next_contracts = []

    for row_number in range(len(approx_calendar.index)):
        calendar_row = approx_calendar.iloc[row_number, :]

        current_contract = calendar_row.current_contract
        current_carry_contract = calendar_row.carry_contract
        next_contract = calendar_row.next_contract

        roll_date = approx_calendar.index[row_number]
        current_prices = dict_of_futures_contract_prices[current_contract]
        next_prices = dict_of_futures_contract_prices[next_contract]

        last_row_in_data = row_number == len(approx_calendar.index) - 1
        carry_comes_afterwards = current_carry_contract > current_contract

        if last_row_in_data or carry_comes_afterwards:
            # Don't need to check that carry exists as there is a good chance
            # it doesn't
            check_carry_exists = False
            # shouldn't be used, but for safety so they don't help previous row
            # values
            next_carry_prices = None
            next_carry_contract = "NA"
        else:
            check_carry_exists = True
            next_calendar_row = approx_calendar.iloc[row_number + 1, :]
            next_carry_contract = next_calendar_row.carry_contract
            next_carry_prices = dict_of_futures_contract_prices[next_carry_contract]

        # This is needed to avoid double rolls
        if row_number > 0:
            last_adjusted_roll_date = adjusted_date_list[-1]
        else:
            last_adjusted_roll_date = None

        try:
            # We use avoid here so that we don't get duplicate dates
            adjusted_date = _find_best_matching_roll_date(
                roll_date,
                current_prices,
                next_prices,
                next_carry_prices,
                avoid_date=last_adjusted_roll_date,
                check_carry_exists=check_carry_exists,
            )
        except LookupError:
            print(
                "Couldn't find matching roll date for contracts %s, %s and %s"
                % (current_contract, next_contract, next_carry_contract)
            )
            print("OK if happens at the end of a roll calendar, otherwise problematic")
            break

        adjusted_date_list.append(adjusted_date)
        current_contracts.append(current_contract)
        carry_contracts.append(current_carry_contract)
        next_contracts.append(next_contract)

    new_calendar = pd.DataFrame(
        dict(
            current_contract=current_contracts,
            next_contract=next_contracts,
            carry_contract=carry_contracts,
        ),
        index=adjusted_date_list,
    )

    return new_calendar


def _find_best_matching_roll_date(
    roll_date,
    current_prices,
    next_prices,
    carry_prices,
    avoid_date=None,
    check_carry_exists=True,
):
    """
    Find the closest valid roll date for which we have overlapping prices
    If avoid_date is passed, get the next date after that

    :param roll_date: datetime.datetime
    :param current_prices: pd.Series
    :param next_prices: pd.Series
    :param avoid_date: datetime.datetime
    :param check_carry_exists: bool

    :return: datetime.datetime or
    """

    # Get the list of dates for which a roll is possible
    if check_carry_exists:
        paired_prices = pd.concat(
            [current_prices, next_prices, carry_prices], axis=1)
    else:
        paired_prices = pd.concat([current_prices, next_prices], axis=1)

    paired_prices_check_match = paired_prices.apply(
        lambda xlist: not any(np.isnan(xlist)), axis=1
    )
    paired_prices_matching = paired_prices_check_match[paired_prices_check_match]
    matching_dates = paired_prices_matching.index
    matching_dates.sort_values()

    if avoid_date is not None:
        # Remove matching dates before avoid dates
        matching_dates = matching_dates[matching_dates > avoid_date]

    if len(matching_dates) == 0:
        # no matching prices
        raise LookupError("No date with a matching price")

    # Find closest distance
    distance_to_roll = matching_dates - roll_date
    distance_to_roll_days = [
        abs(distance_item.days) for distance_item in distance_to_roll
    ]
    closest_date_index = distance_to_roll_days.index(
        min(distance_to_roll_days))
    closest_date = matching_dates[closest_date_index]

    return closest_date


def _add_carry_calendar(
    roll_calendar, roll_parameters_object, dict_of_futures_contract_prices
):
    """
    :param roll_calendar: pdDataFrame with current_contract and next_contract
    :param roll_parameters_object: rollData
    :return: data frame ready to be rollCalendar
    """

    list_of_contract_dates = list(roll_calendar.current_contract.values)
    contracts_with_roll_data = [
        contractDateWithRollParameters(roll_parameters_object, str(contract_date))
        for contract_date in list_of_contract_dates
    ]

    carry_contract_dates = [contract.carry_contract(
    ).date for contract in contracts_with_roll_data]

    # Special case if first carry contract missing with a negative offset
    first_carry_contract = carry_contract_dates[0]
    if first_carry_contract not in dict_of_futures_contract_prices:
        # drop the first roll entirely
        carry_contract_dates.pop(0)

        # do the same with the calendar or will misalign
        first_roll_date = roll_calendar.index[0]
        roll_calendar = roll_calendar.drop(first_roll_date)

    roll_calendar["carry_contract"] = carry_contract_dates

    return roll_calendar


USE_CHILD_CLASS_ROLL_CALENDAR_ERROR = (
    "You need to use a child class of rollCalendarData"
)


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
                self._delete_roll_calendar_data_without_any_warning_be_careful(
                    instrument_code
                )
                self.log.terse(
                    "Deleted roll calendar for %s" %
                    instrument_code)

            else:
                # doesn't exist anyway
                self.log.warn(
                    "Tried to delete roll calendar for non existent instrument code %s" %
                    instrument_code)
        else:
            self.log.error(
                "You need to call delete_roll_calendar with a flag to be sure"
            )

    def _delete_roll_calendar_data_without_any_warning_be_careful(
            instrument_code):
        raise NotImplementedError(USE_CHILD_CLASS_ROLL_CALENDAR_ERROR)

    def is_code_in_data(self, instrument_code):
        if instrument_code in self.get_list_of_instruments():
            return True
        else:
            return False

    def add_roll_calendar(
        self, roll_calendar, instrument_code, ignore_duplication=False
    ):

        self.log.label(instrument_code=instrument_code)

        if self.is_code_in_data(instrument_code):
            if ignore_duplication:
                pass
            else:
                raise self.log.warn(
                    "There is already %s in the data, you have to delete it first" %
                    instrument_code)

        self._add_roll_calendar_without_checking_for_existing_entry(
            roll_calendar, instrument_code
        )

        self.log.terse(
            "Added roll calendar for instrument %s" %
            instrument_code)

    def _add_roll_calendar_without_checking_for_existing_entry(
        self, roll_calendar, instrument_code
    ):
        raise NotImplementedError(USE_CHILD_CLASS_ROLL_CALENDAR_ERROR)
