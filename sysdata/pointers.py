from sysdata.parquet.parquet_adjusted_prices import parquetFuturesAdjustedPricesData as og_parquetFuturesAdjustedPricesData
from sysdata.arctic.arctic_adjusted_prices import arcticFuturesAdjustedPricesData

from sysdata.parquet.parquet_capital import parquetCapitalData as og_parquetCapitalData
from sysdata.arctic.arctic_capital import arcticCapitalData
from sysdata.arctic.arctic_futures_per_contract_prices import arcticFuturesContractPriceData
from sysdata.parquet.parquet_futures_per_contract_prices import parquetFuturesContractPriceData as og_parquetFuturesContractPriceData
from sysdata.data_blob import get_parquet_root_directory
from sysdata.config.production_config import get_production_config

try:
    parquet_root = get_parquet_root_directory(get_production_config())
except:
    ## fine if not using parquet
    pass

## TO USE ARCTIC RATHER THAN PARQUET, REPLACE THE og_ with the relevant arctic class
parquetFuturesAdjustedPricesData = og_parquetFuturesAdjustedPricesData ## change to arctic if desired
parquet_futures_adjusted_price_data = parquetFuturesAdjustedPricesData(parquet_root) ## replace with arcticFuturesContractPriceData() if desired

parquetCapitalData = og_parquetCapitalData

parquetFuturesContractPriceData = og_parquetFuturesContractPriceData
parquet_futures_contract_price_data = parquetFuturesContractPriceData(parquet_root)