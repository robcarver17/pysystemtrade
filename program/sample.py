

if __name__ == '__main__':
    import matplotlib.pyplot as plt
    from sysdata.config.configdata import Config

    # from private.first_system.futures_system import futures_system
    # system = futures_system()
    from systems.provided.futures_chapter15.basesystem import *
    system = futures_system(config=Config())


    a  =  system.config.duplicate_instruments['exclude']

    a = system.config.exclude_instrument_lists['trading_restrictions']
    print(a)

    # system.accounts.portfolio().curve().plot()  ## re-run the final backtest
    # plt.show()




