"""
All default parameters that might be used in a system are stored here

Order of preferences is - passed in command line to calculation method, 
                          stored in system config object
                          found in defaults

"""

system_defaults=dict(
                     volatility_calculation=
                         dict(func="syscore.algos.robust_vol_calc"),
                         
                     forecast_cap=20.0,
                     forecast_scalar=1.0,
                       percentage_vol_target= 16.0,
                     notional_trading_capital= 1e6,
                     base_currency="USD",
                     average_absolute_forecast=10.0
)
