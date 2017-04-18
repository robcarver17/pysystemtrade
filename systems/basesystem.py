import pickle
from sysdata.configdata import Config
from syslogdiag.log import logtoscreen
from syscore.fileutils import get_filename_for_package
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

    def __init__(self,
                 stage_list,
                 data,
                 config=None,
                 log=logtoscreen("base_system")):
        """
        Create a system object for doing simulations or live trading

        :param stage_list: A list of stages
        :type stage_list: list of systems.stage.SystemStage (or anything that
          inherits from it)

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
        setattr(self, "log", log)

        self.config._system_init(self)
        self.data._system_init(self)

        protected = []
        nopickle = []
        stage_names = []

        try:
            iter(stage_list)
        except AssertionError:
            raise Exception("You didn't pass a list into this "
                            "System instance; even just one stage should be "
                            "System([stage_instance])")

        for stage in stage_list:
            """
            This is where we put the methods to store various stages of the
            process
            """

            # Stages have names, which are also how we find them in the system
            # attributes
            sub_name = stage.name

            # Each stage has a link back to the parent system
            # This init sets this, and also passes the log
            stage._system_init(self)

            if sub_name in stage_names:
                raise Exception(
                    "You have duplicate subsystems with the name %s. Remove "
                    "one of them, or change a name." % sub_name)

            setattr(self, sub_name, stage)

            stage_names.append(sub_name)

            # list of attributes / methods of the stage which are protected
            # FIXME more graceful way of doing this
            stage_protected = getattr(stage, "_protected", [])
            stage_protected = [(sub_name, protected_item, "*")
                               for protected_item in stage_protected]
            protected += stage_protected

            stage_nopickle = getattr(stage, "_nopickle", [])
            stage_nopickle = [(sub_name, protected_item, "*")
                              for protected_item in stage_nopickle]
            nopickle += stage_nopickle

        setattr(self, "_stage_names", stage_names)
        """
        The cache hides all intermediate results

        We call optimal_positions and then that propogates back finding all the
        data we need

        The results are then cached in the object. Should we call
        delete_instrument_data (in base class system) then everything related
        to a particular instrument is removed from these 'nodes' except for
        protected items

        This is very useful in live trading when we don't want to update eg
        cross sectional data every sample
        """

        setattr(self, "_cache", dict())
        setattr(self, "_protected", protected)
        setattr(self, "_nopickle", nopickle)

    def __repr__(self):
        sslist = ", ".join(self._stage_names)
        return "System with .config, .data, and .stages: " + sslist

    def set_logging_level(self, new_log_level):
        """
        Set the log level for the system

        :param new_log_level: one of ["off", "terse", "on"]
        :type new_log_level: str

        :returns: None
        """

        self.log.set_logging_level(new_log_level)
        for stage_name in self._stage_names:
            stage = getattr(self, stage_name)
            stage.log.set_logging_level(new_log_level)

    def get_instrument_list(self):
        """
        Get the instrument list

        :returns: list of instrument_code str
        """
        try:
            # if instrument weights specified in config ...
            instrument_list = self.config.instrument_weights.keys()
        except:
            try:
                # alternative place if
                instrument_list = self.config.instruments
            except:
                # okay maybe not, must be in data
                instrument_list = self.data.get_instrument_list()

        instrument_list = sorted(set(list(instrument_list)))
        return instrument_list

    """
    A cache lives inside each system object, storing preliminary results

    It's a dict, with keys that are tuples (stage name, item name)

    There are 3 kinds of things in a cache with different levels of
    persistence:
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

    def partial_cache(self, itemsubset):
        """
        Returns the cache with only some items included

        :param itemsubset: the items to include
        :type itemsubset: list of 3 tuples of str

        :returns: None
        """

        return dict([(itemname, self._cache[itemname])
                     for itemname in itemsubset])

    def pickle_cache(self, relativefilename, fullfilename=None):
        """
        Save everything in the cache to a pickle

        EXCEPT 'nopickle' items

        :param relativefilename: cache location filename in 'dot' format eg
          'systems.basesystem.py' is this file
        :type relativefilename: str

        :param fullfilename: full filename
        :type fullfilename: str


        :returns: None

        """

        if fullfilename is None:
            filename = get_filename_for_package(relativefilename)
        else:
            filename = fullfilename

        itemstopickle = self.get_items_with_data()
        dont_pickle = self.get_nopickle_items()

        itemstopickle = [
            itemname for itemname in itemstopickle
            if itemname not in dont_pickle
        ]

        cache_to_pickle = self.partial_cache(itemstopickle)

        with open(filename, "wb") as fhandle:
            pickle.dump(cache_to_pickle, fhandle)

    def unpickle_cache(self,
                       relativefilename,
                       fullfilename=None,
                       clearcache=True):
        """
        Loads the saved cache

        Note that certain elements (accountCurve objects and optimisers) won't
          be pickled, and so won't be loaded. You will need to regenerate
          these.

        If clearcache is True then we clear the entire cache first. Otherwise we end up with a 'mix'
           - not advised so do at your peril

        :param filename: cache location
        :type filename: filename in 'dot' format eg 'systems.basesystem.py' is this file

        :param clearcache: Clear the entire cache, or overwrite what we have?
        :type clearcache: bool

        :returns: None

        """

        if fullfilename is None:
            filename = get_filename_for_package(relativefilename)
        else:
            filename = fullfilename

        with open(filename, "rb") as fhandle:
            cache_from_pickled = pickle.load(fhandle)

        if clearcache:
            self._cache = dict()

        for itemname in cache_from_pickled.keys():
            self._cache[itemname] = cache_from_pickled[itemname]

    def get_protected_items(self):
        """
        Return items in the cache which are protected
        Resolves wildcards for 3rd position in tuple

        :returns: list of 3 tuple str
        """

        putative_list = self._protected
        itemswithdata = self.get_items_with_data()

        actual_list = []
        for pr in putative_list:
            if pr[2] == "*":  # wildcard
                matched_items = [
                    item for item in itemswithdata
                    if (item[0] == pr[0]) & (item[1] == pr[1])
                ]
                actual_list = actual_list + matched_items
            else:
                actual_list.append(pr)

        return actual_list

    def get_nopickle_items(self):
        """
        Return items in the cache which can't be pickled
        Resolves wildcards for 3rd position in tuple

        :returns: list of 3 tuple str
        """

        putative_list = self._nopickle
        itemswithdata = self.get_items_with_data()

        actual_list = []
        for pr in putative_list:
            if pr[2] == "*":  # wildcard
                matched_items = [
                    item for item in itemswithdata
                    if (item[0] == pr[0]) & (item[1] == pr[1])
                ]
                actual_list = actual_list + matched_items
            else:
                actual_list.append(pr)

        return actual_list

    def get_instrument_codes_for_item(self, itemname):
        """
        Return all the instruments with cache data for a particular itemname

        :param itemname: cache location
        :type itemname: 3 tuple of str: stage name, item identifier, flags eg ("rawdata", "get_fx_rate", "")

        :returns: list of str

        """
        item = self._cache.get(itemname, {})
        return item.keys()

    def get_itemnames_for_stage(self, stagename):
        """
        Returns cache itemnames relevant to a particular stage

        :param stagename: stage name eg rawdata
        :type stagename: str

        :returns: list of 3 tuples of str: stage name, item identifier, flags eg ("rawdata", "get_fx_rate", "")

        """
        cache_refs = [
            itemref for itemref in self._cache.keys() if stagename in itemref
        ]

        return cache_refs

    def get_items_for_instrument(self, instrument_code):
        """
        Return all key items relevant to a particular instrument

        :param instrument_code: relevant instrument
        :type instrument_code: str

        :returns: list of 3 tuples of str: stage name, item identifier, flags eg ("rawdata", "get_fx_rate", "")

        """

        items_with_data = self.get_items_with_data()
        items_code_list = [
            self.get_instrument_codes_for_item(itemname)
            for itemname in items_with_data
        ]
        items_with_instrument_data = [
            itemname
            for (itemname, code_list) in zip(items_with_data, items_code_list)
            if instrument_code in code_list
        ]

        return items_with_instrument_data

    def delete_item(self, itemname):
        """
        Delete everything in cache related to itemname

        :param itemname: cache location
        :type itemname: 3 tuple of str: stage name, item identifier, flags eg ("rawdata", "get_fx_rate", "")

        :returns: deleted content

        WARNING: Will kill protected things as well
        """

        self.log.msg("Deleting %s from cache" % str(itemname))

        if itemname not in self._cache:
            return None

        return self._cache.pop(itemname)

    def delete_items_for_stage(self, stagename, delete_protected=False):
        """
        Delete all items with data for a particular stage

        :param stagename: stage name eg rawdata
        :type stagename: str

        :param deleted_protected: Delete everything, even stuff in self.protected?
        :type delete_protected: bool

        :returns: deleted data

        """

        itemnames = self.get_itemnames_for_stage(stagename)

        if not delete_protected:
            # want to protect stuff
            itemnames = [
                iname for iname in itemnames
                if iname not in self.get_protected_items()
            ]

        return [self.delete_item(iname) for iname in itemnames]

    def delete_items_for_instrument(self,
                                    instrument_code,
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
            item_list = [
                itemname for itemname in item_list
                if itemname not in protected_items
            ]

        deleted_values = [
            self._delete_item_from_cache(itemname, instrument_code)
            for itemname in item_list
        ]

        return deleted_values

    def get_items_across_system(self):
        """
        Returns cross market cache itemnames

        :returns: list of 3 tuples of str: stage name, item identifier, flags eg ("rawdata", "get_fx_rate", "")

        """

        return self.get_items_for_instrument(ALL_KEYNAME)

    def delete_items_across_system(self, delete_protected=False):
        """
        Deletes cross market cache itemnames

        :param deleted_protected: Delete everything, even stuff in self.protected?
        :type delete_protected: bool

        :returns: deleted data

        """

        return self.delete_items_for_instrument(
            ALL_KEYNAME, delete_protected=delete_protected)

    def delete_all_items(self, delete_protected=False):
        """
        Delete everything in the cache

        :param deleted_protected: Delete everything, even stuff in self.protected?
        :type delete_protected: bool

        :returns: deleted data

        """

        item_list = self.get_items_with_data()

        if not delete_protected:
            protected_items = self.get_protected_items()
            item_list = [
                itemname for itemname in item_list
                if itemname not in protected_items
            ]

        deleted_values = [self.delete_item(itemname) for itemname in item_list]

    def get_item_from_cache(self,
                            cache_ref,
                            instrument_code=ALL_KEYNAME,
                            keyname=None):
        """
        Get an item from the cache self._cache

        :param cache_ref: The item to get
        :type cache_ref: 2 or 3 tuple of str: stage name, item identifier, flags eg ("rawdata", "get_fx_rate", "")

        :param instrument_code: The instrument to get it from
        :type instrument_code: str

        :param keyname: The further key (eg rule variation name) to get for a nested item
        :type keyname: str

        :returns: None or item
        """
        if len(cache_ref) == 2:
            cache_ref = (cache_ref[0], cache_ref[1], "")

        if cache_ref not in self._cache:
            # no cache for this item yet
            return None

        if instrument_code not in self._cache[cache_ref]:
            return None

        if keyname is None:
            # one level dict, and we know we have an answer
            return self._cache[cache_ref][instrument_code]
        else:
            if keyname not in self._cache[cache_ref][instrument_code]:
                # missing in nested dict
                return None

            # nested dict and we have an answer
            return self._cache[cache_ref][instrument_code][keyname]

        # should never get here, failsafe
        return None

    def _delete_item_from_cache(self,
                                cache_ref,
                                instrument_code=ALL_KEYNAME,
                                keyname=None):
        """
        Delete an item from the cache self._cache

        Returns the deleted value, or None if not available

        :param cache_ref: The item to get
        :type cache_ref: 2 or 3 tuple of str: stage name, item identifier, flags eg ("rawdata", "get_fx_rate", "")

        :param instrument_code: The instrument to get it from
        :type instrument_code: str

        :param keyname: The further key (eg rule variation name) to get for a nested item
        :type keyname: str

        :returns: None or item
        """

        if len(cache_ref) == 2:
            cache_ref = (cache_ref[0], cache_ref[1], "")

        if cache_ref not in self._cache:
            return None

        if instrument_code not in self._cache[cache_ref]:
            return None

        if keyname is None:
            # one level dict, and we know we have an answer
            return self._cache[cache_ref].pop(instrument_code)
        else:
            if keyname not in self._cache[cache_ref][instrument_code]:
                # missing in nested dict
                return None

            # nested dict and we have an answer
            return self._cache[cache_ref][instrument_code].pop(keyname)

        # should never get here
        return None

    def set_item_in_cache(self,
                          value,
                          cache_ref,
                          instrument_code=ALL_KEYNAME,
                          keyname=None):
        """
        Set an item in a cache to a specific value

        If any part of the cache 'tree' is missing then adds it

        :param value: The value to set to
        :type value: Anything (normally pd.frames or floats)

        :param cache_ref: The item to set
        :type cache_ref: 2 or 3 tuple of str: stage name, item identifier, flags eg ("rawdata", "get_fx_rate", "")

        :param instrument_code: The instrument to set
        :type instrument_code: str

        :param keyname: The further key (eg rule variation name) to set for a nested item
        :type keyname: str

        :returns: None or item
        """

        if len(cache_ref) == 2:
            cache_ref = (cache_ref[0], cache_ref[1], "")

        if cache_ref not in self._cache:
            # no cache for this item yet, let's set one up
            self._cache[cache_ref] = dict()

        if keyname is None:
            # one level dict
            self._cache[cache_ref][instrument_code] = value
        else:
            # nested
            if instrument_code not in self._cache[cache_ref]:
                # missing dict let's add it
                self._cache[cache_ref][instrument_code] = dict()

            self._cache[cache_ref][instrument_code][keyname] = value

        return value

    def calc_or_cache(self,
                      itemname,
                      instrument_code,
                      func,
                      this_stage,
                      *args,
                      flags="",
                      **kwargs):
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

        :param this_stage: stage within system that is calling us
        :type this_stage: system stage

        :param flags: Optional further descriptor for cache item (included in kwargs)
        :type flags: str

        :param args, kwargs: also passed to func if called

        :returns: contents of dict or result of calling function


        """
        #flags=kwargs.pop("flags", "")

        cache_ref = (this_stage.name, itemname, flags)
        value = self.get_item_from_cache(cache_ref, instrument_code)

        if value is None:
            value = func(self, instrument_code, this_stage, *args, **kwargs)
            self.set_item_in_cache(value, cache_ref, instrument_code)

        return value

    def calc_or_cache_nested(self, itemname, instrument_code, keyname, func,
                             this_stage, *args, **kwargs):
        """
        Assumes that self._cache has a key itemname, and that is a nested dict

        If itemname[instrument_code][keyname] exists return it.
        Else call func with arguments: self, instrument_code, keyname, *args
        and **kwargs if we have to call the func updates the dictionary with
        its value

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

        :param this_stage: stage within system that is calling us
        :type this_stage: system stage

        :param args, kwargs: also passed to func if called

        :returns: contents of dict or result of calling function
        """
        flags = kwargs.pop("flags", "")

        cache_ref = (this_stage.name, itemname, flags)

        value = self.get_item_from_cache(cache_ref, instrument_code, keyname)

        if value is None:
            value = func(self, instrument_code, keyname, this_stage, *args,
                         **kwargs)
            self.set_item_in_cache(value, cache_ref, instrument_code, keyname)

        return value


if __name__ == '__main__':
    import doctest
    doctest.testmod()
