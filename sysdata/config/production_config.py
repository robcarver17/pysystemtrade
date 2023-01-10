from sysdata.config.configdata import default_config, Config


def get_production_config() -> Config:
    ## For use outside of backtesting part of code
    ## Just returns a default config, which will include the private.yaml stuff

    return default_config()
