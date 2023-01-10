from systems.provided.rules.ewmac import ewmac


def mr_wings(price, vol, Lfast=4):
    Lslow = Lfast * 4
    ewmac_signal = ewmac(price, vol, Lfast, Lslow)
    ewmac_std = ewmac_signal.rolling(5000, min_periods=3).std()
    ewmac_signal[ewmac_signal.abs() < ewmac_std * 3] = 0.0
    mr_signal = -ewmac_signal

    return mr_signal
