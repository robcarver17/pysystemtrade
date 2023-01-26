from syscore.interactive.input import true_if_answer_is_yes
from sysdata.production.TEMP_old_capital_objects import (
    get_old_capital,
    delete_old_total_capital,
    get_dict_of_capital_by_strategy,
    delete_old_capital_for_strategy,
)
from sysdata.arctic.arctic_capital import arcticCapitalData


def capital_transfer_script():
    print("One off utility to transform old total capital storage into new")
    print(
        "Strongly suggest you have backups and run this when nothing else is running!"
    )
    do_this = true_if_answer_is_yes("Continue?")
    if not do_this:
        return None
    transfer_global_capital()
    transfer_strategy_capital()


def transfer_global_capital():
    original_capital_as_pd = get_old_capital()
    original_capital_as_pd = original_capital_as_pd.ffill()
    print("Original capital")
    print(original_capital_as_pd)

    new_capital_data = arcticCapitalData()
    sure = true_if_answer_is_yes(
        "Happy to delete current 'new' capital and replace with transferred 'old'?"
    )
    if sure:
        new_capital_data.delete_all_global_capital(are_you_really_sure=True)
        new_capital_data.update_df_of_all_global_capital(original_capital_as_pd)
    else:
        return False
    print("New capital")
    print(new_capital_data.get_df_of_all_global_capital())
    sure = true_if_answer_is_yes("Happy to delete old global capital?")
    if sure:
        delete_old_total_capital()
    else:
        print("Old capital not deleted")


def transfer_strategy_capital():
    original_strategy_capital_as_dict = get_dict_of_capital_by_strategy()
    print(original_strategy_capital_as_dict)
    for (
        strategy_name,
        old_capital_for_strategy,
    ) in original_strategy_capital_as_dict.items():
        try:
            transfer_capital_for_specific_strategy(
                strategy_name, old_capital_for_strategy
            )
        except:
            print("Problem with strategy %s - not transferred" % strategy_name)


def transfer_capital_for_specific_strategy(strategy_name, old_capital_for_strategy):
    print("Transferring %s" % strategy_name)
    print("Original capital")
    print(old_capital_for_strategy)

    new_capital_data = arcticCapitalData()
    sure = true_if_answer_is_yes(
        "Happy to delete current 'new' capital and replace with transferred 'old'?"
    )
    if sure:
        new_capital_data.delete_all_capital_for_strategy(
            strategy_name, are_you_really_sure=True
        )
        try:
            new_capital_data.update_capital_pd_df_for_strategy(
                strategy_name, old_capital_for_strategy.to_frame()
            )
        except:
            print(
                "Problem with capital adding %s - probably a data artifact can ignore"
                % str(old_capital_for_strategy)
            )

    else:
        return False
    print("New capital")
    print(new_capital_data.get_capital_pd_df_for_strategy(strategy_name))
    sure = true_if_answer_is_yes("Happy to delete old capital?")
    if sure:
        delete_old_capital_for_strategy(strategy_name)
    else:
        print("Old capital not deleted")


if __name__ == "__main__":
    capital_transfer_script()
