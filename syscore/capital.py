"""
Functions to calculate capital multiplier

Change to pass what is needed
"""

def fixed_capital(system, **ignored_args):
    pandl  = system.accounts.portfolio().percent()
    pandl[:]=1.0
    
    return pandl

def full_compounding(system, **ignored_args):
    pandl  = system.accounts.portfolio().percent().curve()
    pandl = pandl / 100.0
    return pandl

def half_compounding(system, **ignored_args):
    pass
