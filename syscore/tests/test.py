
from syscore.accounting import *

from systems.basesystem import System
from systems.account import Account
from systems.tests.testdata import get_test_object_futures_with_portfolios
(portfolio, posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_portfolios()
system=System([portfolio, posobject, combobject, capobject, rules, rawdata, Account()], data, config)

instrument_code="EDOLLAR"

rule_variations=system.rules.trading_rules()
rule_variation_name="ewmac16"

this_stage=system.accounts
price = this_stage.get_daily_price(instrument_code)
get_daily_returns_volatility = this_stage.get_daily_returns_volatility(
    instrument_code)

forecast = this_stage.get_capped_forecast(
                                              instrument_code, rule_variation_name)

accountCurve(percentage=True, price=price, forecast=forecast, get_daily_returns_volatility=get_daily_returns_volatility)


instruments=system.get_instrument_list()

capital = this_stage.get_notional_capital()
ann_risk_target=system.positionSize.get_daily_cash_vol_target()['percentage_vol_target']/100.0

acc_list=[]
for instrument_code in instruments:
    price = this_stage.get_daily_price(instrument_code)
    positions = this_stage.get_notional_position(instrument_code)
    fx = this_stage.get_fx_rate(instrument_code)
    value_of_price_point = this_stage.get_value_of_price_move(
        instrument_code)
    

    ans2=accountCurve(percentage=True, price=price, positions=positions, fx=fx, get_daily_returns_volatility=get_daily_returns_volatility,
                      capital=capital, ann_risk_target=ann_risk_target, value_of_price_point=value_of_price_point)
    acc_list.append(ans2)

acg=accountCurveGroup(acc_list, instruments)
    
    
ans=pandl_with_data(price,  capital=capital, positions=positions, delayfill=delayfill, 
                                       roundpositions=roundpositions,
                                fx=fx, value_of_price_point=value_of_price_point, 
                                
                                get_daily_returns_volatility=get_daily_returns_volatility,
                                ann_risk_target = ann_risk_target)
