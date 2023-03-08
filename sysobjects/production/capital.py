LIST_OF_COMPOUND_METHODS = ["full", "half", "fixed"]


class totalCapitalUpdater(object):
    """
    All values must be set, we only include as named keywords to avoid mixups
    """

    def __init__(
        self,
        new_broker_account_value: float,
        prev_total_capital: float,
        prev_maximum_capital: float,
        prev_broker_account_value: float,
        prev_pandl_cum_acc: float,
        calc_method: str,
    ):

        self._new_broker_account_value = new_broker_account_value
        self._calc_method = calc_method
        self._prev_broker_account_value = prev_broker_account_value
        self._prev_total_capital = prev_total_capital
        self._prev_maximum_capital = prev_maximum_capital
        self._prev_pandl_cum_acc = prev_pandl_cum_acc

    @property
    def calc_method(self):
        return self._calc_method

    @property
    def new_broker_account_value(self) -> float:
        return self._new_broker_account_value

    @property
    def prev_broker_account_value(self) -> float:
        return self._prev_broker_account_value

    @property
    def prev_total_capital(self) -> float:
        return self._prev_total_capital

    @property
    def prev_maximum_capital(self) -> float:
        return self._prev_maximum_capital

    @property
    def prev_pandl_cum_acc(self) -> float:
        return self._prev_pandl_cum_acc

    @property
    def new_total_capital(self) -> float:
        try:
            new_total_capital = getattr(self, "_new_total_capital")
        except AttributeError:
            raise Exception(
                "Need to run calculate_new_total_and_max_capital_given_pandl()"
            )

        return new_total_capital

    @property
    def new_maximum_capital(self) -> float:
        try:
            new_max_capital = getattr(self, "_new_maximum_capital")
        except AttributeError:
            raise Exception(
                "Need to run calculate_new_total_and_max_capital_given_pandl()"
            )

        return new_max_capital

    @property
    def new_acc_pandl(self) -> float:
        try:
            new_acc_pandl = getattr(self, "_new_acc_pandl")
        except AttributeError:
            raise Exception(
                "Need to run calculate_new_total_and_max_capital_given_pandl()"
            )
        return new_acc_pandl

    @property
    def profit_and_loss(self) -> float:
        return self.new_broker_account_value - self.prev_broker_account_value

    def check_pandl_size(self, check_limit: float = 0.1):
        profit_and_loss = self.profit_and_loss
        prev_broker_account_value = self.prev_broker_account_value

        abs_perc_change = abs(profit_and_loss / prev_broker_account_value)
        if abs_perc_change > check_limit:
            raise LargeCapitalChange(
                "New capital with new account value of %0.f profit of %.0f is more than %.1f%% away from original of %.0f, limit is %.1f%%"
                % (
                    self.new_broker_account_value,
                    profit_and_loss,
                    abs_perc_change * 100,
                    prev_broker_account_value,
                    check_limit,
                )
            )

    def calculate_new_total_and_max_capital_given_pandl(self):
        """
        Calculate capital depending on method

        Saves result into objects

        :param profit_and_loss: float
        :return: new capital
        """
        calc_method = self.calc_method
        if calc_method == "full":
            self._full_capital_calculation()
        elif calc_method == "half":
            self._half_capital_calculation()
        elif calc_method == "fixed":
            self._fixed_capital_calculation()
        else:
            raise Exception("Capital method should be one of full, half or fixed")

        prev_acc_pandl = self.prev_pandl_cum_acc
        new_acc_pandl = prev_acc_pandl + self.profit_and_loss
        self._new_acc_pandl = new_acc_pandl

    def _full_capital_calculation(self):
        """
        Update capital accumullating all p&l

        :param profit_and_loss: float
        :return: new capital
        """

        prev_total_capital = self.prev_total_capital
        new_total_capital = prev_total_capital + self.profit_and_loss

        if new_total_capital < 0:
            new_total_capital = 0

        # We don't really use maximum capital but set it to the same as capital
        # for tidieness
        new_maximum_capital = new_total_capital

        self._new_maximum_capital = new_maximum_capital
        self._new_total_capital = new_total_capital

    def _half_capital_calculation(self):
        """
        Update capital accumallating losses, but not profits about HWM (maximum capital)

        :param profit_and_loss: float
        :return: new capital
        """
        profit_and_loss = self.profit_and_loss
        prev_total_capital = self.prev_total_capital
        prev_maximum_capital = self.prev_maximum_capital

        new_total_capital = min(
            prev_total_capital + profit_and_loss, prev_maximum_capital
        )
        if new_total_capital < 0:
            new_total_capital = 0

        # Max is unchanged
        new_maximum_capital = prev_maximum_capital

        self._new_maximum_capital = new_maximum_capital
        self._new_total_capital = new_total_capital

    def _fixed_capital_calculation(self):
        """
        'Update' capital but capital is fixed

        :param profit_and_loss: float
        :return: new capital
        """

        prev_total_capital = self.prev_total_capital
        new_total_capital = prev_total_capital

        # We don't really use maximum capital but set it to the same as capital
        # for tidieness
        new_maximum_capital = new_total_capital

        self._new_maximum_capital = new_maximum_capital
        self._new_total_capital = new_total_capital


class LargeCapitalChange(ValueError):
    pass
