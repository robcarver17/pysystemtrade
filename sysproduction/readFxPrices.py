"""
Client facing read FX prices
"""

from sysdata.arctic.arctic_spotfx_prices import arcticFxPricesData
from syslogdiag.log import logtoscreen as logger

def read_fx_prices(currency_code: str, tail_size:int = 20):
    """
    Retrieve FX prices from a database, print last tail_size rows

    Will only work for codes in database, so won't do cross rate conversions to find a non existent rate

    :param currency_code: The currency code, for example 'GBPUSD'
    :param tail_size: The length of the tail to print
    :return: None, but print results
    """

    log=logger("read_fx_prices")

    arcticfxdata = arcticFxPricesData(log=log.setup(component="arcticFxPricesData"))

    list_of_codes_all = arcticfxdata.get_list_of_fxcodes()

    try:
        assert currency_code in list_of_codes_all
    except:
        raise Exception("Currency code %s not in possible codes %s" % (currency_code, list_of_codes_all))
    fx_prices = arcticfxdata.get_fx_prices(currency_code)

    print("/n Last %d FX rates for %s \n\n" % (tail_size, currency_code))
    print(fx_prices.tail(tail_size))

