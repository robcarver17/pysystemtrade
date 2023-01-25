none_type = type(None)


class named_object:
    def __init__(self, name):
        self._name = str(name)

    def __repr__(self):
        return self._name


missing_instrument = named_object("missing instrument")
missing_file = named_object("missing file")
missing_data = named_object("missing data")
market_closed = named_object("market closed")
fill_exceeds_trade = named_object("fill too big for trade")
arg_not_supplied = named_object("arg not supplied")
user_exit = named_object("exit")


class status(named_object):
    pass


success = status("success")
failure = status("failure")
