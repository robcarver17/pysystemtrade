"""
All default parameters that might be used in a system are stored here

Order of preferences is - passed in command line to calculation method, 
                          stored in system config object
                          found in defaults

"""

system_defaults=dict(
                     volatility_calculation=
                         dict(func="syscore.algos.robust_vol_calc"))
