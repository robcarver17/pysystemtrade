"""
Functions to calculate capital multiplier
"""

def fixed_capital(system, **ignored_args):
    pandl  = system.accounts.portfolio().percent()
    pandl[:]=1.0
    
    return pandl

def full_compounding(system, **ignored_args):
    pass

def half_compounding(system, **ignored_args):
    pass
