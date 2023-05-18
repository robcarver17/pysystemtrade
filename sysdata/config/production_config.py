from sysdata.config.configdata import Config


def get_production_config() -> Config:
    ## For use outside of backtesting part of code
    ## Just returns a default config, which will include the private.yaml stuff

    return Config.default_config()
