import pandas as pd

from systems.stage import SystemStage
from systems.basesystem import ALL_KEYNAME
from syscore.pdutils import multiply_df_single_column, fix_weights_vs_pdm
from systems.defaults import system_defaults


class PortfoliosFixed(SystemStage):
    """
    Stage for portfolios

    Gets the position, accounts for instrument weights and diversification multiplier

    This version involves fixed weights and multipliers.

    Note: At this stage we're dealing with a notional, fixed, amount of capital.
         We'll need to work out p&l to scale positions properly

    KEY INPUT: system.positionSize.get_subsystem_position(instrument_code)
                found in self.get_subsystem_position(instrument_code)

    KEY OUTPUT: system.portfolio.get_notional_position(instrument_code)

    Name: portfolio
    """

    def __init__(self):
        """
        Create a SystemStage for creating portfolios


        """
        protected = ["get_instrument_weights",
                     "get_instrument_diversification_multiplier", "get_raw_instrument_weights"]

        setattr(self, "_protected", protected)

        setattr(self, "name", "portfolio")

    def get_subsystem_position(self, instrument_code):
        """
        Get the position assuming all capital in one position, from a previous module

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame

        KEY INPUT

        >>> from systems.tests.testdata import get_test_object_futures_with_pos_sizing
        >>> from systems.basesystem import System
        >>> (posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_pos_sizing()
        >>> system=System([rawdata, rules, posobject, combobject, capobject,PortfoliosFixed()], data, config)
        >>>
        >>> ## from config
        >>> system.portfolio.get_subsystem_position("EDOLLAR").tail(2)
                    ss_position
        2015-04-21     7.989637
        2015-04-22     6.875228

        """

        return self.parent.positionSize.get_subsystem_position(instrument_code)

    def get_raw_instrument_weights(self):
        """
        Get the instrument weights

        These are 'raw' because we need to account for potentially missing positions, and weights that don't add up.

        From: (a) passed into subsystem when created
              (b) ... if not found then: in system.config.instrument_weights

        :returns: TxK pd.DataFrame containing weights, columns are instrument names, T covers all subsystem positions

        >>> from systems.tests.testdata import get_test_object_futures_with_pos_sizing
        >>> from systems.basesystem import System
        >>> (posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_pos_sizing()
        >>> config.instrument_weights=dict(EDOLLAR=0.1, US10=0.9)
        >>> system=System([rawdata, rules, posobject, combobject, capobject,PortfoliosFixed()], data, config)
        >>>
        >>> ## from config
        >>> system.portfolio.get_instrument_weights().tail(2)
                    EDOLLAR  US10
        2015-04-21      0.1   0.9
        2015-04-22      0.1   0.9
        >>>
        >>> del(config.instrument_weights)
        >>> system2=System([rawdata, rules, posobject, combobject, capobject,PortfoliosFixed()], data, config)
        >>> system2.portfolio.get_instrument_weights().tail(2)
        WARNING: No instrument weights  - using equal weights of 0.5000 over all 2 instruments in data
                    EDOLLAR  US10
        2015-04-21      0.5   0.5
        2015-04-22      0.5   0.5
        """
        def _get_instrument_weights(system, an_ignored_variable, this_stage):

            try:
                instrument_weights = system.config.instrument_weights
            except:
                instruments = self.parent.data.get_instrument_list()
                weight = 1.0 / len(instruments)

                print("WARNING: No instrument weights  - using equal weights of %.4f over all %d instruments in data" %
                      (weight, len(instruments)))
                instrument_weights = dict(
                    [(instrument_code, weight) for instrument_code in instruments])

            # Now we have a dict, fixed_weights.
            # Need to turn into a timeseries covering the range of forecast
            # dates
            instrument_list = sorted(instrument_weights.keys())

            subsys_ts = [
                this_stage.get_subsystem_position(instrument_code).index
                for instrument_code in instrument_list]

            earliest_date = min([min(fts) for fts in subsys_ts])
            latest_date = max([max(fts) for fts in subsys_ts])

            # this will be daily, but will be resampled later
            weight_ts = pd.date_range(start=earliest_date, end=latest_date)

            instrument_weights_weights = dict([
                (instrument_code, pd.Series([instrument_weights[
                 instrument_code]] * len(weight_ts), index=weight_ts))
                for instrument_code in instrument_list])

            instrument_weights_weights = pd.concat(
                instrument_weights_weights, axis=1)
            instrument_weights_weights.columns = instrument_list

            return instrument_weights_weights

        instrument_weights = self.parent.calc_or_cache(
            "get_raw_instrument_weights", ALL_KEYNAME, _get_instrument_weights, self)
        return instrument_weights

    def get_instrument_weights(self):
        """
        Get the time series of instrument weights, accounting for potentially missing positions, and weights that don't add up.

        :returns: TxK pd.DataFrame containing weights, columns are instrument names, T covers all subsystem positions


        """
        def _get_clean_instrument_weights(
                system, an_ignored_variable, this_stage):

            raw_instr_weights = this_stage.get_raw_instrument_weights()
            instrument_list = list(raw_instr_weights.columns)

            subsys_positions = [this_stage.get_subsystem_position(instrument_code)
                                for instrument_code in instrument_list]

            subsys_positions = pd.concat(subsys_positions, axis=1).ffill()
            subsys_positions.columns = instrument_list

            instrument_weights = fix_weights_vs_pdm(
                raw_instr_weights, subsys_positions)

            return instrument_weights

        instrument_weights = self.parent.calc_or_cache(
            "get_instrument_weights", ALL_KEYNAME, _get_clean_instrument_weights, self)
        return instrument_weights

    def get_instrument_diversification_multiplier(self):
        """
        Get the instrument diversification multiplier

        :returns: TxK pd.DataFrame containing weights, columns are instrument names, T covers all subsystem positions

        >>> from systems.tests.testdata import get_test_object_futures_with_pos_sizing
        >>> from systems.basesystem import System
        >>> (posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_pos_sizing()
        >>> system=System([rawdata, rules, posobject, combobject, capobject,PortfoliosFixed()], data, config)
        >>>
        >>> ## from config
        >>> system.portfolio.get_instrument_diversification_multiplier().tail(2)
                    idm
        2015-04-21  1.2
        2015-04-22  1.2
        >>>
        >>> ## from defaults
        >>> del(config.instrument_div_multiplier)
        >>> system2=System([rawdata, rules, posobject, combobject, capobject,PortfoliosFixed()], data, config)
        >>> system2.portfolio.get_instrument_diversification_multiplier().tail(2)
                    idm
        2015-04-21    1
        2015-04-22    1
        """
        def _get_instrument_div_multiplier(
                system, an_ignored_variable, this_stage):

            if hasattr(system.config, "instrument_div_multiplier"):
                div_mult = system.config.instrument_div_multiplier
            elif "instrument_div_multiplier" in system_defaults:
                div_mult = system_defaults["instrument_div_multiplier"]
            else:
                raise Exception(
                    "Instrument div. multiplier must be in system.config or system_defaults")

            # Now we have a fixed weight
            # Need to turn into a timeseries covering the range of forecast
            # dates

            # this will be daily, but will be resampled later
            weight_ts = this_stage.get_instrument_weights().index

            ts_idm = pd.Series([div_mult] * len(weight_ts),
                               index=weight_ts).to_frame("idm")

            return ts_idm

        instrument_div_multiplier = self.parent.calc_or_cache(
            "get_instrument_diversification_multiplier", ALL_KEYNAME, _get_instrument_div_multiplier, self)
        return instrument_div_multiplier

    def get_notional_position(self, instrument_code):
        """
        Gets the position, accounts for instrument weights and diversification multiplier

        Note: At this stage we're dealing with a notional, fixed, amount of capital.
             We'll need to work out p&l to scale positions properly

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame

        KEY OUTPUT
        >>> from systems.tests.testdata import get_test_object_futures_with_pos_sizing
        >>> from systems.basesystem import System
        >>> (posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_pos_sizing()
        >>> system=System([rawdata, rules, posobject, combobject, capobject,PortfoliosFixed()], data, config)
        >>>
        >>> ## from config
        >>> system.portfolio.get_notional_position("EDOLLAR").tail(2)
                         pos
        2015-04-21  4.793782
        2015-04-22  4.125137
        >>>

        """
        def _get_notional_position(system, instrument_code, this_stage):
            idm = this_stage.get_instrument_diversification_multiplier()
            instr_weights = this_stage.get_instrument_weights()
            subsys_position = this_stage.get_subsystem_position(
                instrument_code)

            inst_weight_this_code = instr_weights[
                instrument_code].to_frame("weight")

            inst_weight_this_code = inst_weight_this_code.reindex(
                subsys_position.index).ffill()
            idm = idm.reindex(subsys_position.index).ffill()

            multiplier = multiply_df_single_column(inst_weight_this_code, idm)
            notional_position = multiply_df_single_column(
                subsys_position, multiplier)
            notional_position.columns = ['pos']

            return notional_position

        notional_position = self.parent.calc_or_cache(
            "get_notional_position", instrument_code, _get_notional_position, self)
        return notional_position


if __name__ == '__main__':
    import doctest
    doctest.testmod()
