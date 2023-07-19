none_type = type(None)


class named_object:
    def __init__(self, name):
        self._name = str(name)

    def __repr__(self):
        return self._name


arg_not_supplied = named_object("arg not supplied")
user_exit = named_object("exit")


class status(named_object):
    pass


success = status("success")
failure = status("failure")
