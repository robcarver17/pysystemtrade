import re
from syscore.genutils import highest_common_factor_for_list, sign
from syscore.constants import arg_not_supplied

from sysexecution.trade_qty import tradeQuantity


def extract_fx_balances_from_account_summary(account_summary) -> dict:
    relevant_tag = "TotalCashBalance"

    result = extract_currency_dict_for_tag_from_account_summary(
        account_summary, relevant_tag
    )

    return result


def extract_currency_dict_for_tag_from_account_summary(account_summary, relevant_tag):
    result = dict(
        [
            (summary_item.currency, summary_item.value)
            for summary_item in account_summary
            if summary_item.tag == relevant_tag
        ]
    )

    return result


class positionsFromIB(dict):
    pass


def from_ib_positions_to_dict(
    raw_positions, account_id=arg_not_supplied
) -> positionsFromIB:
    """

    :param raw_positions: list of positions in form Position(...)
    :return: dict of positions as dataframes
    """
    resolved_positions_dict = dict()
    position_methods = dict(
        STK=resolve_ib_stock_position,
        FUT=resolve_ib_future_position,
        CASH=resolve_ib_cash_position,
    )
    for position in raw_positions:
        if account_id is not arg_not_supplied:
            if position.account != account_id:
                continue

        asset_class = position.contract.secType
        method = position_methods.get(asset_class, None)
        if method is None:
            # Resolve unexpected asset classes like cash rather than failing
            method = resolve_ib_cash_position
            # raise Exception("Can't find asset class %s in methods dict" % asset_class)

        resolved_position = method(position)
        asset_class_list = resolved_positions_dict.get(asset_class, [])
        asset_class_list.append(resolved_position)
        resolved_positions_dict[asset_class] = asset_class_list

    resolved_positions_dict = positionsFromIB(resolved_positions_dict)

    return resolved_positions_dict


def resolve_ib_stock_position(position):

    return dict(
        account=position.account,
        symbol=position.contract.symbol,
        multiplier=1.0,
        expiry="",
        exchange=position.contract.exchange,
        currency=position.contract.currency,
        position=position.position,
    )


def resolve_ib_future_position(position):

    return dict(
        account=position.account,
        symbol=position.contract.symbol,
        expiry=position.contract.lastTradeDateOrContractMonth,
        multiplier=float(position.contract.multiplier),
        currency=position.contract.currency,
        position=position.position,
    )


def resolve_ib_cash_position(position):

    return dict(
        account=position.account,
        symbol=position.contract.localSymbol,
        expiry="",
        multiplier=1.0,
        currency=position.contract.currency,
        position=position.position,
    )


def resolveBS_for_list(trade_list: tradeQuantity):
    if len(trade_list) == 1:
        return resolveBS(trade_list[0])
    else:
        return resolveBS_for_calendar_spread(trade_list)


def resolveBS_for_calendar_spread(trade_list: tradeQuantity):
    trade = highest_common_factor_for_list(trade_list)

    trade = sign(trade_list[0]) * trade

    return resolveBS(trade)


def resolveBS(trade: int):
    if trade < 0:
        return "SELL", int(abs(trade))
    return "BUY", int(abs(trade))
