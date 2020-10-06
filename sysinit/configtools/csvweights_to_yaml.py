"""
Some people prefer to write their instrument and forecast weight configs in a .csv file

This utility is for you - it will read those files and output a yaml file you can paste into your config
"""

import pandas as pd
import yaml


def instr_weights_csv_to_yaml(filename_input, filename_output):
    """
    Read in a configuration csv file containing instrument weights and output as yaml

    :param filename_input: full path and filename
    :param filename_output: full path and filename
    :return: data written to yaml
    """

    data = pd.read_csv(filename_input)
    data_instruments = data.Instrument.values
    data_weights = data.instrumentWeight

    my_config = dict(
        [
            (instrument, weight)
            for (instrument, weight) in zip(data_instruments, data_weights)
        ]
    )
    my_config_nested = dict(instrument_weights=my_config)

    with open(filename_output, "w") as outfile:
        outfile.write(yaml.dump(my_config_nested, default_flow_style=False))

    return data


def forecast_weights_by_instrument_csv_to_yaml(
        filename_input, filename_output):
    """
    Read in a configuration csv file containing forecast weights, different for each instrument, and output as yaml

    :param filename_input: full path and filename
    :param filename_output: full path and filename
    :return: data written to yaml
    """

    data = pd.read_csv(filename_input)

    data_instruments = list(data.columns)
    forecast_header_column = data_instruments[0]
    data_instruments = data_instruments[1:]

    rule_names = data[forecast_header_column].values

    my_config = {}
    for instrument in data_instruments:

        data_weights = data[instrument].values
        my_config[instrument] = dict(
            [
                (rule_name, float(weight))
                for (rule_name, weight) in zip(rule_names, data_weights)
            ]
        )

    my_config_nested = dict(forecast_weights=my_config)
    with open(filename_output, "w") as outfile:
        outfile.write(yaml.dump(my_config_nested, default_flow_style=False))

    return my_config


def forecast_mapping_csv_to_yaml(filename_input, filename_output):
    """
    Read in a configuration csv file containing forecast mapping, different for each instrument, and output as yaml

    :param filename_input: full path and filename
    :param filename_output: full path and filename
    :return: data written to yaml
    """

    data = pd.read_csv(filename_input)
    data_instruments = data.instrument.values
    data_param_a = data.a_param.values
    data_param_b = data.b_param.values
    data_threshold = data.threshold.values

    my_config = dict(
        [
            (
                instrument,
                dict(
                    a_param=float(a_param),
                    b_param=float(b_param),
                    threshold=float(threshold),
                ),
            )
            for (instrument, a_param, b_param, threshold) in zip(
                data_instruments, data_param_a, data_param_b, data_threshold
            )
        ]
    )
    my_config_nested = dict(forecast_mapping=my_config)

    with open(filename_output, "w") as outfile:
        outfile.write(yaml.dump(my_config_nested, default_flow_style=False))

    return data
