from sysproduction.data.orders import dataOrders

d = dataOrders()

if __name__ == "__main__":

    list_of_order_ids = d.data.db_broker_historic_orders.get_list_of_order_ids()
    for order_id in list_of_order_ids:
        order = d.data.db_broker_historic_orders.get_order_with_orderid(order_id)
        d.data.db_broker_historic_orders._add_order_to_data_no_checking(order)


    list_of_order_ids = d.data.db_contract_historic_orders.get_list_of_order_ids()
    for order_id in list_of_order_ids:
        order = d.data.db_contract_historic_orders.get_order_with_orderid(order_id)
        d.data.db_contract_historic_orders._add_order_to_data_no_checking(order)

    list_of_order_ids = d.data.db_strategy_historic_orders.get_list_of_order_ids()
    for order_id in list_of_order_ids:
        order = d.data.db_strategy_historic_orders.get_order_with_orderid(order_id)
        d.data.db_strategy_historic_orders._add_order_to_data_no_checking(order)
