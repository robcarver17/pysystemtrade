if __name__ == '__main__':
    from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
    data = csvFuturesSimData()
    print(data.get_instrument_list())
