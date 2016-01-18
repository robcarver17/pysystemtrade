from sysdata.configdata import Config
"""
This is used for items which affect an entire system, not just one instrument
"""
ALL_KEYNAME = "all"


class System(object):
    '''
    system objects are used for signal processing in a 'tree' like framework

    This is the base class which all systems inherit

    Systems are:

        made up of stages

       take a data, and optionally a config object

    The system only has one method 'of its own' which is get_instrument_list

    '''

    def __init__(self, stage_list, data, config=None):
        """
        Create a system object for doing simulations or live trading

        :param stage_list: A list of stages
        :type stage_list: list of systems.stage.SystemStage (or anything that inherits from it)

        :param data: data for doing simulations
        :type data: sysdata.data.Data (or anything that inherits from that)

        :param config: Optional configuration
        :type config: sysdata.configdata.Config

        :returns: new system object

        >>> from systems.stage import SystemStage
        >>> stage=SystemStage()
        >>> from sysdata.csvdata import csvFuturesData
        >>> data=csvFuturesData()
        >>> System([stage], data)
        System with stages: unnamed

        """

        if config is None:
            # Default - for very dull systems this is sufficient
            config = Config()

        setattr(self, "data", data)
        setattr(self, "config", config)

        protected = []
        stage_names = []

        assert isinstance(stage_list, list)

        for stage in stage_list:

            """
            This is where we put the methods to store various stages of the process

            """

            # Each stage has a link back to the parent system
            setattr(stage, "parent", self)

            # Stages have names, which are also how we find them in the system
            # attributes
            sub_name = stage.name

            if sub_name in stage_names:
                raise Exception(
                    "You have duplicate subsystems with the name %s. Remove "
                    "one of them, or change a name." % sub_name)

            setattr(self, sub_name, stage)

            stage_names.append(sub_name)

            # list of attributes / methods of the stage which are protected
            stage_protected = getattr(stage, "_protected", [])
            protected += stage_protected

        setattr(self, "_stage_names", stage_names)

        """
        The cache hides all intermediate results

        We call optimal_positions and then that propogates back finding all the
        data we need

        The results are then cached in the object. Should we call
            delete_instrument_data (in base class system) then everything
            related to a particular instrument is removed from these 'nodes'

        This is very useful in live trading when we don't want to update eg
            cross sectional data every sample
        """

        setattr(self, "_cache", dict())
        setattr(self, "_protected", protected)

    def __repr__(self):
        sslist = ", ".join(self._stage_names)
        return "System with stages: " + sslist
    
    def get_instrument_list(self):
        """
        Get the instrument list

        :returns: list of instrument_code str
        """
        try:
            ## if instrument weights specified in config ...
            instrument_list = self.config.instrument_weights.keys()
        except:
            ## okay maybe not, must be in data
            instrument_list = self.data.get_instrument_list()

        return instrument_list



    """
    A cache lives inside each system object, storing preliminary results

    There are 3 kinds of things in a cache with different levels of persistence:
      - anything that isn't special
      - things that have an 'all' key -
      - _protected - that wouldn't normally be deleted

    """

    def get_items_with_data(self):
        """
        Return items in the cache with data (or at least key values set)
        :returns: list of str
        """

        return list(self._cache.keys())

    def get_protected_items(self):
        return self._protected

    def get_instrument_codes_for_item(self, itemname):
        item = self._cache.get(itemname, {})
        return item.keys()

    def get_items_for_instrument(self, instrument_code):
        """
        Return all key items which have instrument_code keys

        :returns: list of str
        """

        items_with_data = self.get_items_with_data()
        items_code_list = [self.get_instrument_codes_for_item(itemname) for
                           itemname in items_with_data]
        items_with_instrument_data = [itemname for (itemname, code_list) in zip(
            items_with_data, items_code_list) if instrument_code in code_list]

        return items_with_instrument_data

    def delete_item(self, itemname):
        """
        Delete everything in cache related to itemname

        :param itemname: Instrument to delete
        :type itemname: str

        Will kill protected things as well
        """

        if itemname not in self._cache:
            return None

        return self._cache.pop(itemname)

    def delete_items_for_instrument(self, instrument_code,
                                    delete_protected=False):
        """
        Delete everything in the system relating to an instrument_code

        :param instrument_code: Instrument to delete
        :type instrument_code: str

        :param deleted_protected: Delete everything, even stuff in self.protected?
        :type delete_protected: bool


        When working with a live system we listen to a message bus, if a new
        price is received then we delete things in the cache

        This means when we ask for self.optimal_positions(instrument_code) it
          has to recalc all intermediate steps as the cached

        However we ignore anything in self._protected This is normally cross
        sectional data which we only want to calculate periodically

        if delete_protected is True then we delete that stuff as well
        (this is roughly equivalent to creating the systems object from scratch)

        """
        item_list = self.get_items_for_instrument(instrument_code)
        if not delete_protected:
            protected_items = self.get_protected_items()
            item_list = [itemname for itemname in item_list if itemname not in
                         protected_items]

        deleted_values = [self._delete_item_from_cache(itemname, instrument_code) for
                          itemname in item_list]

        return deleted_values

    def get_items_across_system(self):
        return self.get_items_for_instrument(ALL_KEYNAME)

    def delete_items_across_system(self, delete_protected=False):
        return self.delete_items_for_instrument(
            ALL_KEYNAME, delete_protected=delete_protected)

    def delete_all_items(self, delete_protected=False):
        item_list = self.get_items_with_data()

        if not delete_protected:
            protected_items = self.get_protected_items()
            item_list = [
                itemname for itemname in item_list if itemname not in protected_items]

        deleted_values = [self.delete_item(itemname) for itemname in item_list]

        return deleted_values

    def get_item_from_cache(
            self, itemname, instrument_code=ALL_KEYNAME, keyname=None):
        """
        Get an item from the cache self._cache

        :param itemname: The item to get
        :type itemname: str

        :param instrument_code: The instrument to get it from
        :type instrument_code: str

        :param keyname: The further key (eg rule variation name) to get for a nested item
        :type keyname: str

        :returns: None or item
        """

        if itemname not in self._cache:
            # no cache for this item yet
            return None

        if instrument_code not in self._cache[itemname]:
            return None

        if keyname is None:
            # one level dict, and we know we have an answer
            return self._cache[itemname][instrument_code]
        else:
            if keyname not in self._cache[itemname][instrument_code]:
                # missing in nested dict
                return None

            # nested dict and we have an answer
            return self._cache[itemname][instrument_code][keyname]

        # should never get here, failsafe
        return None

    def _delete_item_from_cache(self, itemname, instrument_code=ALL_KEYNAME,
                                keyname=None):
        """
        Delete an item from the cache self._cache

        Returns the deleted value, or None if not available

        :param itemname: The item to get
        :type itemname: str

        :param instrument_code: The instrument to get it from
        :type instrument_code: str

        :param keyname: The further key (eg rule variation name) to get for a nested item
        :type keyname: str

        :returns: None or item
        """

        if itemname not in self._cache:
            return None

        if instrument_code not in self._cache[itemname]:
            return None

        if keyname is None:
            # one level dict, and we know we have an answer
            return self._cache[itemname].pop(instrument_code)
        else:
            if keyname not in self._cache[itemname][instrument_code]:
                # missing in nested dict
                return None

            # nested dict and we have an answer
            return self._cache[itemname][instrument_code].pop(keyname)

        # should never get here
        return None

    def set_item_in_cache(self, value, itemname, instrument_code=ALL_KEYNAME,
                          keyname=None):
        """
        Set an item in a cache to a specific value

        If any part of the cache 'tree' is missing then adds it

        :param value: The value to set to
        :type value: Anything (normally pd.frames or floats)

        :param itemname: The item to set
        :type itemname: str

        :param instrument_code: The instrument to set
        :type instrument_code: str

        :param keyname: The further key (eg rule variation name) to set for a nested item
        :type keyname: str

        :returns: None or item
        """

        if itemname not in self._cache:
            # no cache for this item yet, let's set one up
            self._cache[itemname] = dict()

        if keyname is None:
            # one level dict
            self._cache[itemname][instrument_code] = value
        else:
            # nested
            if instrument_code not in self._cache[itemname]:
                # missing dict let's add it
                self._cache[itemname][instrument_code] = dict()

            self._cache[itemname][instrument_code][keyname] = value

        return value

    def calc_or_cache(self, itemname, instrument_code, func, *args, **kwargs):
        """
        Assumes that self._cache has an attribute itemname, and that is a dict

        If self._cache.itemname[instrument_code] exists return it. Else call
        func with *args and **kwargs if the latter updates the dictionary

        :param itemname: attribute of object containing a dict
        :type itemname: str

        :param instrument_code: keyname to look for in dict
        :type instrument_code: str

        :param func: function to call if missing from cache. will take self and
            instrument_code as first two args
        :type func: function

        :param args, kwargs: also passed to func if called

        :returns: contents of dict or result of calling function


        """
        value = self.get_item_from_cache(itemname, instrument_code)

        if value is None:
            value = func(self, instrument_code, *args, **kwargs)
            self.set_item_in_cache(value, itemname, instrument_code)

        return value

    def calc_or_cache_nested(self, itemname, instrument_code, keyname, func,
                             *args, **kwargs):
        """
        Assumes that self._cache has a key itemname, and that is a nested dict

        If itemname[instrument_code][keyname] exists return it.
        Else call func with arguments: self, instrument_code, keyname, *args
        and **kwargs if we have to call the func updates the dictionary with
        it's value

        Used for cache within various kinds of objects like config, price,
        data, system...

        :param itemname: cache item to look for
        :type itemname: str

        :param instrument_code: keyname to look for in dict
        :type instrument_code: str

        :param keyname: keyname to look for in nested dict
        :type keyname: valid dict key

        :param func: function to call if missing from cache. will take self and
            instrument_code, keyname as first three args
        :type func: function

        :param args, kwargs: also passed to func if called

        :returns: contents of dict or result of calling function
        """

        value = self.get_item_from_cache(itemname, instrument_code, keyname)

        if value is None:
            value = func(self, instrument_code, keyname, *args, **kwargs)
            self.set_item_in_cache(value, itemname, instrument_code, keyname)

        return value


if __name__ == '__main__':
    import doctest
    doctest.testmod()
