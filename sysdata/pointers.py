from sysdata.parquet.parquet_adjusted_prices import parquetFuturesAdjustedPricesData as og_parquetFuturesAdjustedPricesData
from sysdata.arctic.arctic_adjusted_prices import arcticFuturesAdjustedPricesData

from sysdata.parquet.parquet_capital import parquetCapitalData as og_parquetCapitalData
from sysdata.arctic.arctic_capital import arcticCapitalData

## TO USE ARCTIC RATHER THAN PARQUET, REPLACE THE og_ with the relevant arctic class
parquetFuturesAdjustedPricesData = og_parquetFuturesAdjustedPricesData ## change to arctic if desired
parquetCapitalData = og_parquetCapitalData