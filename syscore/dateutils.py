"""
Various routines to do with dates
"""
import datetime
import numpy as np

from syscore.genutils import sign

"""
First some constants
"""

CALENDAR_DAYS_IN_YEAR=365.25

BUSINESS_DAYS_IN_YEAR=256.0
ROOT_BDAYS_INYEAR=BUSINESS_DAYS_IN_YEAR**.5

WEEKS_IN_YEAR=CALENDAR_DAYS_IN_YEAR/7.0
ROOT_WEEKS_IN_YEAR=WEEKS_IN_YEAR**.5

MONTHS_IN_YEAR=12.0
ROOT_MONTHS_IN_YEAR=MONTHS_IN_YEAR**.5

def expiry_date(expiry_ident):
    """
    Translates an expiry date which could be "20150305" or "201505" into a datetime
    
    
    :param expiry_ident: Expiry to be processed
    :type days: str or datetime.datetime 
    
    :returns: datetime.datetime or datetime.date
    
    >>> expiry_date('201503')
    datetime.datetime(2015, 3, 1, 0, 0)

    >>> expiry_date('20150305')
    datetime.datetime(2015, 3, 5, 0, 0)
    
    >>> expiry_date(datetime.datetime(2015,5,1))
    datetime.datetime(2015, 5, 1, 0, 0)
    
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
        raise Exception("expiry_date needs to be a string with 4 or 6 digits, ")
       
    ## 'Natural' form is datetime 
    return expiry_date


def expiry_diff(carry_row, floor_date_diff=20):
    """
    Given a pandas row containing CARRY_CONTRACT and PRICE_CONTRACT, both of which represent dates
    
    Return the annualised difference between the dates
    
    :param carry_row: object with attributes CARRY_CONTRACT and PRICE_CONTRACT
    :type carry_row: pandas row, or something that quacks like it
     
    :param floor_date_diff: If date resolves to less than this, floor here (*default* 20)
    :type carry_row: pandas row, or something that quacks like it
    
    :returns: datetime.datetime or datetime.date

     
    """
    if carry_row.PRICE_CONTRACT=="" or carry_row.CARRY_CONTRACT=="":
        return np.nan
    ans=float((expiry_date(carry_row.CARRY_CONTRACT) - expiry_date(carry_row.PRICE_CONTRACT)).days)
    if abs(ans)<floor_date_diff:
        ans=sign(ans)*floor_date_diff
    ans=ans/CALENDAR_DAYS_IN_YEAR
    
    return ans
    
if __name__ == '__main__':
    import doctest
    doctest.testmod()