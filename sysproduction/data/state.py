



class diagState(object):
    def __init__(self, data):
        # Check data has the right elements to do this

        data.add_class_list("mongoRollStateData")
        self.data = data

    def get_roll_state(self, instrument_code):
        return self.data.mongo_roll_state.get_roll_state(instrument_code)