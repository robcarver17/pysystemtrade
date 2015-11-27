"""
Various routines to do with dates
"""
import pandas as pd
import datetime
import numpy as np

from syscore.genutils import sign

"""
First some constants
"""

CALENDAR_DAYS_IN_YEAR=365.25
BUSINESS_DAYS_IN_YEAR=256.0

ROOT_BDAYS_INYEAR=BUSINESS_DAYS_IN_YEAR**.5

def expiryDate(expiry_ident):
    """
    Translates an expiry date which could be "20150305" or "201505" into a datetime
    
    """
    
    if type(expiry_ident)==str:
        ## do string expiry calc
        if len(expiry_ident)==6:
            expiry_date=datetime.datetime.strptime(expiry_ident, "%Y%m")
        elif len(expiry_ident)==8:
            expiry_date=datetime.datetime.strptime(expiry_ident, "%Y%m%d")
        else:
            raise Exception("")
    
    elif type(expiry_ident)==datetime.datetime or type(expiry_ident)==datetime.date:
        expiry_date=expiry_ident
    
    else:
        raise Exception("expiryDate needs to ")
       
    ## 'Natural' form is datetime 
    return expiry_date


def expiry_diff(carry_row, min_days=20):
    """
    Given a pandas row containing CARRY_CONTRACT and PRICE_CONTRACT, both of which represent dates
    
    Return the annualised difference between the dates
    
    """
    if carry_row.PRICE_CONTRACT=="" or carry_row.CARRY_CONTRACT=="":
        return np.nan
    ans=float((expiryDate(carry_row.CARRY_CONTRACT) - expiryDate(carry_row.PRICE_CONTRACT)).days)
    if abs(ans)<min_days:
        ans=sign(ans)*min_days
    ans=ans/CALENDAR_DAYS_IN_YEAR
    
    return ans
    
