# Upgrading pysystemtrade from version 0.80 to 0.85

WARNING! This a major upgrade, from a very old version of Pandas and relevant Arctic distribution to a much newer one.

## IF YOU HAVE DATA FROM EARLIER VERSIONS

AHL Arctic later versions *cannot* read pandas Series objects. Unfortunately both cash FX prices and adjusted prices are saved in this format. So before upgrading you must run an 'update_multiple_adjusted prices' and an 'update_fx_prices' using the patch version 0.82, ensuring that new data is written for all instruments.

If you do not do this, then you won't be able to read your old adjusted price and spot FX data. The latter can be regenerated from .csv backups, whilst the former will be automatically generated from multiple price data.

As always, it's advisable to back up your data before undertaking any upgrade.

## REQUIREMENTS FOR RUNNING VERSION 0.85.0

This new version has been tested on python 3.8.5, pandas 1.0.5, and Arctic 1.79.2

There is currently an issue running very new versions of pandas with Arctic, hence it's important to get these requirements correct.

## TESTING

Pysystemtrade does not have, to my shame, a comprehensive set of tests. However I've run the standard provided backtests, and also run through the production pipeline, without any issues.