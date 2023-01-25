from collections import namedtuple
from copy import copy

from syscore.interactive.input import (
    true_if_answer_is_yes,
    input_field_names_for_named_tuple,
)
from syscore.constants import arg_not_supplied

from sysdata.data_blob import dataBlob

from sysobjects.futures_per_contract_prices import futuresContractPrices

priceFilterConfig = namedtuple(
    "priceFilterConfig",
    [
        "ignore_future_prices",
        "ignore_prices_with_zero_volumes_daily",
        "ignore_prices_with_zero_volumes_intraday",
        "ignore_zero_prices",
        "ignore_negative_prices",
        "max_price_spike",
    ],
)


def apply_price_cleaning(
    data: dataBlob,
    broker_prices_raw: futuresContractPrices,
    cleaning_config=arg_not_supplied,
    daily_data: bool = True,
):

    cleaning_config = get_config_for_price_filtering(
        data=data, cleaning_config=cleaning_config
    )

    log = data.log

    broker_prices = copy(broker_prices_raw)

    ## It's important that the data is in local time zone so that this works
    price_length = len(broker_prices)
    if cleaning_config.ignore_future_prices:
        broker_prices = broker_prices.remove_future_data()
        new_price_length = len(broker_prices)
        if new_price_length < price_length:
            log.msg(
                "Ignoring %d prices with future timestamps"
                % (price_length - new_price_length)
            )
            price_length = new_price_length

    if daily_data:
        ignore_prices_with_zero_volumes = (
            cleaning_config.ignore_prices_with_zero_volumes_daily
        )
    else:
        ignore_prices_with_zero_volumes = (
            cleaning_config.ignore_prices_with_zero_volumes_intraday
        )

    if ignore_prices_with_zero_volumes:
        broker_prices = broker_prices.remove_zero_volumes()
        new_price_length = len(broker_prices)
        if new_price_length < price_length:
            log.msg(
                "Ignoring %d prices with zero volumes"
                % (price_length - new_price_length)
            )
            price_length = new_price_length

    if cleaning_config.ignore_zero_prices:
        broker_prices = broker_prices.remove_zero_prices()
        new_price_length = len(broker_prices)
        if new_price_length < price_length:
            log.msg(
                "Ignoring %d prices with zero prices"
                % (price_length - new_price_length)
            )
            price_length = new_price_length

    if cleaning_config.ignore_negative_prices:
        broker_prices = broker_prices.remove_negative_prices()
        new_price_length = len(broker_prices)
        if new_price_length < price_length:
            log.warn(
                "Ignoring %d prices with negative prices ****COULD BE REAL PRICES****"
                % (price_length - new_price_length)
            )
            price_length = new_price_length  ## not used again but for tidiness

    return broker_prices


"""
FIXME THIS IS HORRIBLE
"""


def get_config_for_price_filtering(
    data: dataBlob, cleaning_config: priceFilterConfig = arg_not_supplied
) -> priceFilterConfig:

    if cleaning_config is not arg_not_supplied:
        ## override
        return cleaning_config

    production_config = data.config

    ignore_future_prices = production_config.get_element_or_missing_data(
        "ignore_future_prices"
    )
    ignore_prices_with_zero_volumes_daily = (
        production_config.get_element_or_missing_data(
            "ignore_prices_with_zero_volumes_daily"
        )
    )
    ignore_prices_with_zero_volumes_intraday = (
        production_config.get_element_or_missing_data(
            "ignore_prices_with_zero_volumes_intraday"
        )
    )
    ignore_zero_prices = production_config.get_element_or_missing_data(
        "ignore_zero_prices"
    )
    ignore_negative_prices = production_config.get_element_or_missing_data(
        "ignore_negative_prices"
    )
    max_price_spike = production_config.get_element_or_missing_data("max_price_spike")

    any_missing = any(
        [
            x is arg_not_supplied
            for x in [
                ignore_future_prices,
                ignore_prices_with_zero_volumes_daily,
                ignore_prices_with_zero_volumes_intraday,
                ignore_zero_prices,
                ignore_negative_prices,
                max_price_spike,
            ]
        ]
    )

    if any_missing:
        error = "Missing config items for price filtering - have you deleted from defaults.yaml?"
        data.log.critical(error)
        raise Exception(error)

    cleaning_config = priceFilterConfig(
        ignore_zero_prices=ignore_zero_prices,
        ignore_negative_prices=ignore_negative_prices,
        ignore_future_prices=ignore_future_prices,
        ignore_prices_with_zero_volumes_daily=ignore_prices_with_zero_volumes_daily,
        ignore_prices_with_zero_volumes_intraday=ignore_prices_with_zero_volumes_intraday,
        max_price_spike=max_price_spike,
    )

    return cleaning_config


def interactively_get_config_overrides_for_cleaning(data) -> priceFilterConfig:
    default_config = get_config_for_price_filtering(data)
    print("Current data cleaning configuration: %s" % str(default_config))
    make_changes = true_if_answer_is_yes("Make changes?")
    if make_changes:
        new_config = input_field_names_for_named_tuple(default_config)
        print("New config %s" % str(new_config))
        return new_config
    else:
        return default_config
