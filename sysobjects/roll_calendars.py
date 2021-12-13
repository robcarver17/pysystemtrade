import datetime
import pandas as pd
import numpy as np

from sysinit.futures.build_roll_calendars import (
    generate_approximate_calendar,
    adjust_to_price_series,
    back_out_roll_calendar_from_multiple_prices,
)
from sysobjects.dict_of_futures_per_contract_prices import (
    dictFuturesContractFinalPrices,
)
from sysobjects.multiple_prices import futuresMultiplePrices

from sysobjects.rolls import rollParameters


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
        rollCalendar,
        dict_of_futures_contract_prices: dictFuturesContractFinalPrices,
        roll_parameters_object: rollParameters,
    ):
        """

        :param roll_parameters_object: roll parameters specific to this instrument
        :param dict_of_futures_contract_prices: dict, keys are contract date ids 'yyyymmdd'
        """

        approx_calendar = generate_approximate_calendar(
            roll_parameters_object, dict_of_futures_contract_prices
        )

        adjusted_calendar = adjust_to_price_series(
            approx_calendar, dict_of_futures_contract_prices
        )

        roll_calendar = rollCalendar(adjusted_calendar)

        return roll_calendar

    @classmethod
    def back_out_from_multiple_prices(
        rollCalendar, multiple_prices: futuresMultiplePrices
    ):
        """

        :param multiple_prices: output from futuresDataForSim.FuturesData.get_current_and_forward_price_data(instrument_code)
               columns: PRICE, FORWARD, FORWARD_CONTRACT, PRICE_CONTRACT

        :return: rollCalendar
        """
        roll_calendar_as_pd = back_out_roll_calendar_from_multiple_prices(
            multiple_prices
        )
        roll_calendar_object = rollCalendar(roll_calendar_as_pd)

        return roll_calendar_object

    def check_if_date_index_monotonic(self) -> bool:
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
        self, dict_of_futures_contract_prices: dictFuturesContractFinalPrices
    ) -> bool:
        """
        Adjust an approximate roll calendar so that we have matching dates on each expiry

        :param dict_of_futures_contract_prices: dict of futuresContractPrices, keys contract date eg yyyymmdd

        :return: bool, True if no problems
        """

        checks_okay = True
        for row_number in range(len(self.index)):
            calendar_row = self.iloc[row_number, :]

            checks_okay_this_row = _check_row_of_row_calendar(
                calendar_row, dict_of_futures_contract_prices
            )

            if not checks_okay_this_row:
                # single failure is a total failure
                checks_okay = False

        return checks_okay


def _check_row_of_row_calendar(
    calendar_row: pd.Series,
    dict_of_futures_contract_prices: dictFuturesContractFinalPrices,
) -> bool:

    current_contract = str(calendar_row.current_contract)
    next_contract = str(calendar_row.next_contract)
    carry_contract = str(calendar_row.carry_contract)
    roll_date = calendar_row.name

    try:
        current_prices = dict_of_futures_contract_prices[current_contract]
    except KeyError:
        print(
            "On roll date %s contract %s is missing from futures prices"
            % (roll_date, current_contract)
        )
        return False
    try:
        next_prices = dict_of_futures_contract_prices[next_contract]
    except KeyError:
        print(
            "On roll date %s contract %s is missing from futures prices"
            % (roll_date, next_contract)
        )
        return False

    try:
        carry_prices = dict_of_futures_contract_prices[carry_contract]
    except KeyError:
        print(
            "On roll date %s contract %s is missing from futures prices"
            % (roll_date, carry_contract)
        )
        return False

    try:
        current_price = current_prices.loc[roll_date]
    except KeyError:
        print("Roll date %s missing from prices for %s" % (roll_date, current_contract))
        return False

    try:
        next_price = next_prices.loc[roll_date]
    except KeyError:
        print("Roll date %s missing from prices for %s" % (roll_date, next_contract))
        return False

    if np.isnan(current_price):
        print("NAN for price on %s for %s " % (roll_date, current_contract))
        return False

    if np.isnan(next_price):
        print("NAN for price on %s for %s " % (roll_date, current_contract))
        return False

    return True
