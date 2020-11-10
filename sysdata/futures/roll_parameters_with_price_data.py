
from sysobjects.rolls import contractDateWithRollParameters

class rollParametersWithPriceData(object):
    def __init__(self, roll_parameters, dict_of_final_price_data):
        """
        If we combine roll parameters with price data, we can do useful things which are required to calculate precise roll
        calendars.

        :param roll_parameters: object of type rollParameters
        :param dict_of_final_price_data: object of type dictFuturesContractFinalPrices
        """

        self.roll_parameters = roll_parameters
        self.prices = dict_of_final_price_data

    def find_earliest_held_contract_with_data(self):
        """
        Find the earliest contract we can hold in a given list of contract dates
        To hold the contract, it needs to be in the held roll cycle and the list_of_contract_dates
        And it's carry contract needs to be in the priced roll cycle and the list_of_contract_dates

        :return: contract with roll parameters, or None
        """
        list_of_contract_dates = self.prices.sorted_contract_ids()
        final_contract_date = list_of_contract_dates[-1]
        plausible_earliest_contract_date = list_of_contract_dates[0]
        roll_parameters_object = self.roll_parameters
        plausible_earliest_contract = contractDateWithRollParameters(
            roll_parameters_object, plausible_earliest_contract_date
        )

        try_contract = contractWithRollParametersAndPrices(
            plausible_earliest_contract, self.prices
        )

        while try_contract.contract_date <= final_contract_date:
            if try_contract.contract_date in list_of_contract_dates:
                # possible candidate, let's check carry
                try_carry_contract = (
                    try_contract.find_best_carry_contract_with_price_data()
                )
                if try_carry_contract is not None:
                    # Okay this works
                    contract_to_return = try_contract.contract
                    return contract_to_return

            # okay it's not suitable for some reason
            # Let's try another one
            try_contract = try_contract.find_next_held_contract_with_price_data()

        # Nothing found
        return None


class contractWithRollParametersAndPrices(object):
    """
    Including prices in our contract means we can navigate more accurately through roll cycles
    """

    def __init__(
            self,
            contract_with_roll_parameters,
            dict_of_final_price_data):
        """

        :param contract_with_roll_parameters: contractWithRollParameters
        :param dict_of_final_price_data: object of type dictFuturesContractFinalPrices
        """

        self.contract = contract_with_roll_parameters
        self.prices = dict_of_final_price_data

    @property
    def contract_date(self):
        return self.contract.date

    @property
    def want_to_roll(self):
        return self.contract.want_to_roll

    def next_held_contract(self):
        next_held_contract_with_roll_parameters = self.contract.next_held_contract()
        return contractWithRollParametersAndPrices(
            next_held_contract_with_roll_parameters, self.prices
        )

    def next_priced_contract(self):
        next_priced_contract_with_roll_parameters = self.contract.next_priced_contract()
        return contractWithRollParametersAndPrices(
            next_priced_contract_with_roll_parameters, self.prices
        )

    def previous_priced_contract(self):
        previous_priced_contract_with_roll_parameters = (
            self.contract.previous_priced_contract()
        )
        return contractWithRollParametersAndPrices(
            previous_priced_contract_with_roll_parameters, self.prices
        )

    def previous_held_contract(self):
        previous_held_contract_with_roll_parameters = (
            self.contract.previous_held_contract()
        )
        return contractWithRollParametersAndPrices(
            previous_held_contract_with_roll_parameters, self.prices
        )

    def find_next_held_contract_with_price_data(self):
        """
        Finds the first contract in list_of_contract_dates after current_contract, within the held roll cycle
           defined by roll parameters

        :return: a contract object with roll data, or None if we can't find one
        """
        try_contract = self.next_held_contract()
        list_of_contract_dates = self.prices.sorted_contract_ids()
        final_contract_date = list_of_contract_dates[-1]

        while try_contract.contract_date <= final_contract_date:
            if try_contract.contract_date in list_of_contract_dates:
                return try_contract
            try_contract = try_contract.next_held_contract()

        # Nothing found
        return None

    def find_next_priced_contract_with_price_data(self):
        """
        Finds the first contract in list_of_contract_dates after current_contract, within the priced roll cycle
           defined by roll parameters

        :return: a contract object with roll data, or None if we can't find one
        """
        try_contract = self.next_priced_contract()
        list_of_contract_dates = self.prices.sorted_contract_ids()
        final_contract_date = list_of_contract_dates[-1]

        while try_contract.contract_date <= final_contract_date:
            if try_contract.contract_date in list_of_contract_dates:
                return try_contract
            try_contract = try_contract.next_priced_contract()

        # Nothing found
        return None

    def find_previous_priced_contract_with_price_data(self):
        """
        Finds the closest contract in list_of_contract_dates before current_contract, within the priced roll cycle
           defined by roll parameters

        :return: a contract object with roll data, or None if we can't find one
        """
        try_contract = self.previous_priced_contract()
        list_of_contract_dates = self.prices.sorted_contract_ids()
        first_contract_date = list_of_contract_dates[0]

        while try_contract.contract_date >= first_contract_date:
            if try_contract.contract_date in list_of_contract_dates:
                return try_contract
            try_contract = try_contract.previous_priced_contract()

        # Nothing found
        return None

    def find_previous_held_contract_with_price_data(self):
        """
        Finds the closest contract in list_of_contract_dates before current_contract, within the held roll cycle
           defined by roll parameters

        :return: a contract object with roll data, or None if we can't find one
        """
        try_contract = self.previous_held_contract()
        list_of_contract_dates = self.prices.sorted_contract_ids()
        first_contract_date = list_of_contract_dates[0]

        while try_contract.contract_date >= first_contract_date:
            if try_contract.contract_date in list_of_contract_dates:
                return try_contract
            try_contract = try_contract.previous_held_contract()

        # Nothing found
        return None

    def find_best_carry_contract_with_price_data(self):
        """
        Finds the best carry contract in list_of_contract_dates after current_contract, within the roll cycle
           defined by roll parameters

        This will either be the next valid contract, or the first valid preceeding contract in the price cycle

        :return: a contract object with roll data, or None if we can't find one
        """
        carry_offset = self.contract.roll_parameters.carry_offset

        if carry_offset == 1.0:
            best_carry_contract = self.find_next_priced_contract_with_price_data()
        elif carry_offset == -1.0:
            best_carry_contract = self.find_previous_priced_contract_with_price_data()
        else:
            raise Exception("Carry offset should be 1 or -1!")

        return best_carry_contract
