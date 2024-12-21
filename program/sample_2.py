if __name__ == '__main__':

    from systems.provided.futures_chapter15.basesystem import *
    system = futures_system()
    print(system.accounts.get_actual_capital())


