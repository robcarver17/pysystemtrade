"""
Suite of functions to analyse a system, and produce configuration that can be saved to a yaml file
"""
from syscore.algos import return_mapping_params
import yaml

class systemDiag(object):
    def __init__(self, system):
        self.system = system

    def instrument_list(self):
        return self.system.get_instrument_list()

    def trading_rules(self):
        return self.system.rules.trading_rules().keys()

    def target_forecast_value(self):
        return self.system.config.average_absolute_forecast


    def check_forecast_scaling(self):
        """
        Check forecast scaling

        Returns a list of tuples, ordered with largest error first

        :param system:
        :return: list of tuples
        """
        system = self.system
        instrument_list = system.get_instrument_list()
        rule_list = self.trading_rules()
        target_forecast_value = self.target_forecast_value()

        results_list = []
        for rule in rule_list:
            for instrument in instrument_list:
                forecast = system.forecastScaleCap.get_capped_forecast(instrument, rule)
                error = forecast_error(forecast, target_forecast_value)
                results_list.append((instrument, rule, error))

        sorted_by_max_error = sorted(results_list, key=lambda tup: tup[2], reverse=True)

        return sorted_by_max_error


    def check_combined_forecast_scaling(self, forecast_type="raw"):
        """
        Check combined forecast scaling

        Returns a list of tuples, ordered with largest error first

        :param system:
        :param forecast_type: raw or final. If raw is specified will be before any forecast scaling is applied
        :return: list of tuples
        """
        system = self.system
        instrument_list = system.get_instrument_list()
        target_forecast_value = self.target_forecast_value()

        try:
            attr_name_dict = dict(raw = '_get_raw_combined_forecast', final = 'get_combined_forecast')
            attr_name = attr_name_dict[forecast_type]
        except KeyError:
            raise Exception("forecast_type must be one of %s" % str(attr_name_dict.keys()))

        try:
            forecast_func = getattr(system.combForecast, attr_name)
        except:
            raise Exception("%s not a method system.combForecast" % attr_name)

        results_list=[]
        for instrument in instrument_list:
            forecast = forecast_func(instrument)

            error = forecast_error(forecast, target_forecast_value)
            results_list.append((instrument, error))

        sorted_by_max_error = sorted(results_list, key=lambda tup: tup[1], reverse=True)

        return sorted_by_max_error

    def forecast_mapping(self, target_position_at_avg_forecast=2.0):
        """
        Fit threshold values for forecasts

        :return: dict, suitable for dropping into a config object or yaml file
        """
        system = self.system
        instrument_list = self.instrument_list()
        avg_forecast = self.target_forecast_value()

        forecast_mapping = {}
        for instrument in instrument_list:
            position = system.portfolio.get_notional_position(instrument)
            forecast = system.combForecast.get_combined_forecast(instrument)
            scalar = position / forecast
            scalar_ewma = scalar.ewm(500).mean()
            position_at_avg_forecast = avg_forecast * scalar_ewma.values[-1]
            print("%s avg position %.2f" % (instrument, position_at_avg_forecast))

            a_param = target_position_at_avg_forecast / position_at_avg_forecast
            if a_param < 1.2:
                ## no need to do anything
                print("Forecast scaling not required for %s" % instrument)
            elif a_param > 1.7:
                print("Warning! Position at avg forecast of %.2f is too small for mapping to work for %s " % (
                position_at_avg_forecast, instrument))
            else:
                (a_param, b_param, threshold_value, capped_value) = return_mapping_params(a_param)
                map_dict = dict(a_param=a_param, b_param=b_param, threshold_value=threshold_value)
                forecast_mapping[instrument] = map_dict

        return forecast_mapping

    def forecast_scalars(self):
        """
        Returns final estimated values for forecast scalars, so they can be written into a config as fixed values

        :return: dict of forecast scalars
        """

        system = self.system
        instrument_list = self.instrument_list()
        rule_list = self.trading_rules()

        use_estimates = system.config.use_forecast_scale_estimates
        if not use_estimates:
            print("Can't output forecast scalar estimates, as they weren't estimated")


        pooling = system.config.forecast_scalar_estimate['pool_instruments']
        if not pooling:
            print("WARNING: No way of putting different forecast scalars for different instruments into config")
        scalar_results = dict()

        for rule in rule_list:
            if not pooling:
                scalar_results[rule] = dict()

            for instrument in instrument_list:
                scalar = float(system.forecastScaleCap.get_forecast_scalar(instrument, rule)[-1])
                if pooling:
                    ## will be overwritten for each instrument
                    scalar_results[rule] = scalar
                else:
                    scalar_results[rule][instrument] = scalar

        return scalar_results

    def forecast_div_multiplier(self):
        """
        Returns final estimated values for FDM, so they can be written into a config as fixed values

        :return: dict
        """

        system = self.system
        instrument_list = self.instrument_list()
        fdm_results = dict()
        for instrument in instrument_list:
            fdm = system.combForecast.get_forecast_diversification_multiplier(instrument).values[-1]
            fdm_results[instrument] = float(fdm)

        return fdm_results

    def forecast_weights(self):
        """
        Returns final estimated values for forecast weights, so they can be written into a config as fixed values

        :return: dict of dicts
        """
        ## forecast weights
        system = self.system
        instrument_list = self.instrument_list()
        forecast_weights = dict()
        for instrument in instrument_list:
            weights = dict(system.combForecast.get_forecast_weights(instrument).iloc[-1])
            weights = dict((rule_name, float(weight)) for rule_name, weight in weights.items())
            forecast_weights[instrument] = weights

        return forecast_weights

    def instrument_weights(self):
        """
        Returns final estimated values for instrument weights, so they can be written into a config as fixed values

        :return: dict
        """
        system = self.system
        instrument_weights = system.portfolio.get_instrument_weights().iloc[-1]
        instrument_weights = dict((key, float(value)) for key,value in instrument_weights.items())

        return instrument_weights

    def instrument_div_multiplier(self):
        """
        Returns final estimated values for instrument diversification multiplier, so it can be written into a config as fixed values

        :return: dict
        """
        system = self.system
        instrument_div_multiplier = float(system.portfolio.get_instrument_diversification_multiplier().values[-1])

        return instrument_div_multiplier

    def output_config_with_estimated_parameters(self, attr_names=['forecast_scalars',
                                                                  'forecast_weights',
                                                                  'forecast_div_multiplier',
                                                                  'forecast_mapping',
                                                                  'instrument_weights',
                                                                  'instrument_div_multiplier']):

        output_dict={}
        for config_item in attr_names:
            dict_function = getattr(self, config_item)
            try:
                dict_value = dict_function()
                output_dict[config_item] = dict_value
            except:
                print("Couldn't get %s will exclude from output" % config_item)

        return output_dict

    def yaml_config_with_estimated_parameters(self, yaml_filename,
                                              attr_names=['forecast_scalars',
                                                                  'forecast_weights',
                                                                  'forecast_div_multiplier',
                                                                  'forecast_mapping',
                                                                  'instrument_weights',
                                                                  'instrument_div_multiplier']):

        output_dict = self.output_config_with_estimated_parameters(attr_names = attr_names)
        with open(yaml_filename, "w") as f:
            yaml.dump(output_dict, f, default_flow_style=False)

def forecast_error(forecast, target_forecast_value):
    abs_size = forecast.abs().mean()
    std_size = forecast.std()
    abs_error = abs(abs_size - target_forecast_value)
    std_error = abs(std_size - target_forecast_value)
    max_error = max([abs_error, std_error])

    return max_error

