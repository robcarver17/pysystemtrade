from syscore.objects import missing_data

def get_capital(data, strategy_name):
    data.add_class_list("mongoCapitalData")
    capital_value = data.mongo_capital.get_current_capital_for_strategy(strategy_name)
    if capital_value is missing_data:
        data.log.error("Capital data is missing for %s" % strategy_name)
        raise Exception("Capital data is missing for %s" % strategy_name)

    data.log.msg("Got capital of %.2f for %s" % (capital_value, strategy_name))

    return capital_value
