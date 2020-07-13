import re
from syscore.genutils import highest_common_factor_for_list, sign
from syscore.objects import arg_not_supplied, missing_data

def from_ib_positions_to_dict(raw_positions, account_id = arg_not_supplied):
    """

    :param raw_positions: list of positions in form Position(...)
    :return: dict of positions as dataframes
    """
    resolved_positions_dict = dict()
    position_methods = dict(STK = resolve_ib_stock_position, FUT = resolve_ib_future_position,
                            CASH = resolve_ib_cash_position)
    for position in raw_positions:
        if account_id is not arg_not_supplied:
            if position.account != account_id:
                continue

        asset_class = position.contract.secType
        method = position_methods.get(asset_class, None)
        if method is None:
            raise Exception("Can't find asset class %s in methods dict" % asset_class)

        resolved_position = method(position)
        asset_class_list = resolved_positions_dict.get(asset_class, [])
        asset_class_list.append(resolved_position)
        resolved_positions_dict[asset_class] = asset_class_list

    return resolved_positions_dict

def resolve_ib_stock_position(position):

    return dict(account = position.account, symbol = position.contract.symbol,
                multiplier = 1.0, expiry = "",
                exchange = position.contract.exchange, currency = position.contract.currency,
                position = position.position)

def resolve_ib_future_position(position):

    return dict(account = position.account, symbol = position.contract.symbol, expiry = position.contract.lastTradeDateOrContractMonth,
                multiplier = float(position.contract.multiplier), currency = position.contract.currency,
                position = position.position)

def resolve_ib_cash_position(position):

    return dict(account = position.account, symbol = position.contract.localSymbol,
                expiry = "", multiplier = 1.0,
                currency = position.contract.currency, position = position.position)

def resolveBS(trade):
    if trade<0:
        return "SELL", int(abs(trade))
    return "BUY", int(abs(trade))

def resolveBS_for_list(trade_list):
    ## result is always positive
    trade = highest_common_factor_for_list(trade_list)

    trade = sign(trade_list[0])* trade

    return resolveBS(trade)
