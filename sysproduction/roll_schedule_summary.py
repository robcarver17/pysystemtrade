#!/usr/bin/env python
# coding: utf-8

import numpy as np
import pandas as pd

from sysproduction.data.prices import diagPrices
from sysdata.data_blob import dataBlob
from sysproduction.reporting.roll_report import get_roll_data_for_instrument

#########
#
# simple summary of roll status for all instruments where we have contract prices
#
# will output to .csv (easy to read) and to terminal
#
########


def roll_summary(to_file=True, to_terminal=True):
    '''Docstring to come'''
    
    d = diagPrices()

    instrument_list = sorted(d.get_list_of_instruments_with_contract_prices())

    results = dict()
    with dataBlob(log_name="Summarise-Portfolio-Roll-Status") as data:
        for instrument in instrument_list:
            try:
                results_dict_code = get_roll_data_for_instrument(instrument, data)
                results[instrument] = results_dict_code
            except AttributeError:
                print("Can't get roll data for %s" % instrument)

    output = pd.DataFrame(columns=list(results[list(results.keys())[0]].keys()))
    for instrument in results:
        output.loc[instrument] = results[instrument]
    output.volumes = output.volumes.apply(_round_list)
    output = output.sort_values(by='code')


    if to_terminal:
        roll_summary_to_terminal(output)
    
    if to_file:
        output.to_csv('roll-summary.csv', index=False)
        print('\nsaved roll-summary.csv')


def roll_summary_to_terminal(output):
    '''Docstring to come'''
    title = 'Roll summary'
    warnings = list()
    print(f"{'='*len(title)}\n{title}\n{'='*len(title)}\n")
    for instrument in output.index:
        roll_exp = output.loc[instrument, 'roll_expiry']
        print(f"{instrument}: {output.loc[instrument, 'status']}\nroll_exp {roll_exp}\tprice_exp {output.loc[instrument, 'price_expiry']}\tcarry_exp {output.loc[instrument, 'carry_expiry']}\n")
        if roll_exp < 1:
            warnings.append(f"{instrument} roll is overdue, has roll_expiry {roll_exp}")
            printf("*** CHECK ROLL EXPIRY FOR {instrument} ***\n")
        elif roll_exp < 7:
            warnings.append(f"{instrument} has roll expiry in less than a week's time, in {roll_exp} days")
    if len(warnings) > 0:
        print('----\nROLL WARNINGS\n----')
        for warning in warnings:
            print(warning)


def _round_list(list_, decimal_places=1):
    '''Utility function to round all floats in a list; converts list to array,
       rounds, and returns as list.
    '''
    return list(np.around(np.array(list_), decimal_places))


if __name__=='__main__':
    roll_summary()