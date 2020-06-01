from sysexecution.contract_orders import contractOrder
from sysexecution.instrument_orders import instrumentOrder
from syscore.objects import missing_order, ROLL_PSEUDO_STRATEGY
from sysproduction.data.positions import diagPositions
from sysproduction.data.contracts import diagContracts
from sysproduction.data.prices import diagPrices

def create_force_roll_orders(data, instrument_code):
    """

    :param data:
    :param instrument_code:
    :return: tuple; instrument_order (or missing_order), contract_orders
    """
    diag_positions = diagPositions(data)
    roll_state = diag_positions.get_roll_state(instrument_code)
    if roll_state not in ['Force', 'Force_Outright']:
        return missing_order, []

    strategy = ROLL_PSEUDO_STRATEGY
    trade = 0
    instrument_order = instrumentOrder(strategy, instrument_code, trade)

    diag_contracts = diagContracts(data)
    priced_contract_id = diag_contracts.get_priced_contract_id(instrument_code)
    forward_contract_id = diag_contracts.get_forward_contract_id(instrument_code)
    position_in_priced = diag_positions.get_position_for_instrument_and_contract_date(instrument_code, priced_contract_id)

    if roll_state=='Force_Outright':
        contract_orders = create_contract_orders_outright(data,  instrument_code, priced_contract_id, forward_contract_id, position_in_priced)
    elif roll_state=='Force':
        contract_orders = create_contract_orders_spread(data,  instrument_code, priced_contract_id, forward_contract_id, position_in_priced)
    else:
        raise  Exception("Roll state %s not recognised" % roll_state)

    return instrument_order, contract_orders

def create_contract_orders_outright(data, instrument_code,
                                    priced_contract_id, forward_contract_id, position_in_priced):
    diag_prices = diagPrices(data)
    reference_price_priced_contract, reference_price_forward_contract = \
        tuple(diag_prices.get_last_matched_prices_for_contract_list(
            instrument_code, [priced_contract_id, forward_contract_id]))
    strategy = ROLL_PSEUDO_STRATEGY
    first_order = contractOrder(strategy, instrument_code, priced_contract_id, -position_in_priced,
                                reference_price=reference_price_priced_contract)
    second_order = contractOrder(strategy, instrument_code, forward_contract_id, position_in_priced,
                                 reference_price=reference_price_forward_contract)

    return [first_order, second_order]

def create_contract_orders_spread(data, instrument_code,
                                  priced_contract_id, forward_contract_id, position_in_priced):

    diag_prices = diagPrices(data)
    reference_price_priced_contract, reference_price_forward_contract = \
        tuple(diag_prices.get_last_matched_prices_for_contract_list(
            instrument_code, [priced_contract_id, forward_contract_id]))

    strategy = ROLL_PSEUDO_STRATEGY
    contract_id_list = [priced_contract_id, forward_contract_id]
    trade_list = [-position_in_priced, position_in_priced]
    spread_reference_price = reference_price_priced_contract - reference_price_forward_contract

    spread_order = contractOrder(strategy, instrument_code, contract_id_list, trade_list,
                                reference_price=spread_reference_price)

    return [spread_order]
