"""
Utilities I can't put anywhere else...
"""

from math import copysign



def str_of_int(x):
    """
    Returns the string of int of x, handling nan's or whatever
    """
    if type(x) is int:
        return str(x)
    try:
        return str(int(x))
    except:
        return ""
    
    

def sign(x):
    """
    Return the sign of x (float or int)
    """
    return copysign(1, x)

