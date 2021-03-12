### THIS IS PRETTY UGLY CODE BUT NOT CRITICAL SO NOT TOUCHING FOR NOW...

"""
A cache lives inside each system object, storing preliminary results

It's a dict, with keys that are tuples (stage name, item name)

There are 3 kinds of things in a cache with different levels of persistence:
  - anything that isn't special
  - things that have an 'all' key -
  - _protected - that wouldn't normally be deleted

"""

from syscore.fileutils import get_filename_for_package
import pickle
from functools import wraps

"""
This is used for items which affect an entire system, not just one instrument
"""
ALL_KEYNAME = "All_instruments"

# more useful flags
EMPTY_KEYNAME = object()
MISSING_FROM_CACHE = object()


class cacheRef(object):
    """
    References to use within caches

    """

    def __init__(
            self,
            stage_name,
            itemname,
            instrument_code=ALL_KEYNAME,
            flags="",
            keyname=""):

        self.stage_name = stage_name
        self.itemname = itemname
        self.instrument_code = instrument_code
        self.flags = flags
        self.keyname = keyname

    def __repr__(self):
        if self.keyname == "":
            keystring = ""
        else:
            keystring = "[%s] " % self.keyname

        return "%s in %s for instrument %s %s%s" % (
            self.itemname,
            self.stage_name,
            self.instrument_code,
            keystring,
            self.flags,
        )

    # following code is to make keys hashable and suitable for dict keys
    def __key(self):
        return tuple(v for k, v in sorted(self.__dict__.items()))

    def __eq__(self, other):
        return isinstance(
            other, self.__class__) and self.__key() == other.__key()

    def __hash__(self):
        return hash(self.__key())


class listOfCacheRefs(list):
    """
    a list of cacheRef

    only used to apply filters, or summarise

    can apply filters successively if desired
    """

    def filter_by_stage_name(self, stage_name):
        new_list = [
            cache_ref for cache_ref in self if cache_ref.stage_name == stage_name]

        return listOfCacheRefs(new_list)

    def filter_by_itemname(self, itemname):
        new_list = [
            cache_ref for cache_ref in self if cache_ref.itemname == itemname]

        return listOfCacheRefs(new_list)

    def filter_by_instrument_code(self, instrument_code):
        new_list = [
            cache_ref
            for cache_ref in self
            if cache_ref.instrument_code == instrument_code
        ]

        return listOfCacheRefs(new_list)

    def filter_by_keyname(self, keyname):
        new_list = [
            cache_ref for cache_ref in self if cache_ref.keyname == keyname]

        return listOfCacheRefs(new_list)

    def unique_list_of_stage_names(self):
        return list(set([cache_ref.stage_name for cache_ref in self]))

    def unique_list_of_item_names(self):
        return list(set([cache_ref.itemname for cache_ref in self]))

    def unique_list_of_instrument_codes(self):
        return list(set([cache_ref.instrument_code for cache_ref in self]))

    def unique_list_of_keynames(self):
        return list(set([cache_ref.keyname for cache_ref in self]))


class cacheElement(object):
    """
    Each cache element consists of a value, and some bool values telling us what we can do with it
    """

    def __init__(self, value, protected=False, not_pickable=False):
        self._value = value
        self._protected = protected
        self._not_pickable = not_pickable

    def __repr__(self):
        return str(self._value)

    def value(self):
        return self._value

    def not_pickable(self):
        return self._not_pickable

    def protected(self):
        return self._protected

    def can_be_pickled(self):
        return not self._not_pickable


class systemCache(dict):
    def __init__(self, parent_system):

        super().__init__()
        self._parent = parent_system  # so we can access the instrument list
        self.set_caching_on()

    @property
    def parent(self):
        return self._parent

    def set_caching_on(self):
        self._caching_on = True

    def set_caching_off(self):
        self._caching_on = False

    def are_we_caching(self):
        return self._caching_on

    def __repr__(self):
        if self.are_we_caching():
            list_of_elements = ", ".join(
                [str(cache_ref) for cache_ref in self.get_items_with_data()]
            )
            return "Cache, elements: " + list_of_elements
        else:
            return "Not using cache"

    def get_items_with_data(self):
        """
        Return items in the cache with data (or at least key values set)
        :returns: list of cacheRef objects
        """

        return listOfCacheRefs(list(self.keys()))

    def partial_cache(self, cache_ref_list):
        """
        Returns the cache with only some items included

        :param cache_ref_list: the items to include
        :type cache_ref_list: list of cacheRef instances

        :returns: systemCache object
        """

        new_cache = systemCache(self.parent)
        for cache_ref in cache_ref_list:
            new_cache[cache_ref] = self[cache_ref]

        return new_cache

    def pickle(self, relativefilename):
        """
        Save everything in the cache to a pickle

        EXCEPT 'not picklable' items

        :param relativefilename: cache location filename in 'dot' format eg 'systems.basesystem.py' is this file
        :type relativefilename: str

        :returns: None

        """

        filename = get_filename_for_package(relativefilename)

        pickable_cache_refs = self._get_pickable_items()

        cache_to_pickle = self.partial_cache(pickable_cache_refs)
        cache_to_pickle_as_dict = cache_to_pickle.as_dict()

        with open(filename, "wb+") as fhandle:
            pickle.dump(cache_to_pickle_as_dict, fhandle)

    def as_dict(self):
        self_as_dict = {}
        for ref_name in self.get_items_with_data():
            self_as_dict[ref_name] = self[ref_name]

        return self_as_dict

    def unpickle(self, relativefilename, clearcache=True):
        """
        Loads the saved cache

        Note that certain elements (accountCurve objects and optimisers) won't
           be pickled, and so won't be loaded. You will need to regenerate
           these.

        If clearcache is True then we clear the entire cache first. Otherwise
          we end up with a 'mix'
           - not advised so do at your peril

        :param filename: cache location
        :type filename: filename in 'dot' format eg 'systems.basesystem.py' is this file

        :param clearcache: Clear the entire cache, or overwrite what we have?
        :type clearcache: bool

        :returns: None

        """

        filename = get_filename_for_package(relativefilename)

        with open(filename, "rb") as fhandle:
            cache_from_pickled = pickle.load(fhandle)

        if clearcache:
            self.clear()

        for itemname in cache_from_pickled.keys():
            self[itemname] = cache_from_pickled[itemname]

    def _get_protected_items(self):
        """
        Return items in the cache which are protected

        :returns: list cache keys
        """

        protected_cache_refs = [
            cache_ref
            for cache_ref in self.get_items_with_data()
            if self[cache_ref].protected()
        ]

        return protected_cache_refs

    def _get_pickable_items(self):
        """
        Return keys of items in the cache which can be pickled

        :returns: list cache keys
        """

        pickable_cache_refs = [
            cache_ref
            for cache_ref in self.get_items_with_data()
            if self[cache_ref].can_be_pickled()
        ]

        return pickable_cache_refs

    def get_cache_refs_for_instrument(self, instrument_code):
        """
        return cache refs for a particular instrument code

        :param instrument_code:
        :return: list of cache refs
        """

        cache_ref_list = self.get_items_with_data()
        cache_ref_list = cache_ref_list.filter_by_instrument_code(
            instrument_code)

        return cache_ref_list

    def get_cacherefs_for_stage(self, stage_name):
        """
        Returns cache itemnames relevant to a particular stage

        :param stage_name: stage name eg rawdata
        :type stage_name: str

        :returns: list of cache refs

        """

        cache_ref_list = self.get_items_with_data()
        cache_ref_list = cache_ref_list.filter_by_stage_name(stage_name)

        return cache_ref_list

    def get_itemnames_for_stage(self, stage_name):
        """
        Returns cache itemnames relevant to a particular stage

        :param stage_name: stage name eg rawdata
        :type stage_name: str

        :returns: list of itemnames

        """

        cache_ref_list = self.get_cacherefs_for_stage(stage_name)
        itemnames = cache_ref_list.unique_list_of_item_names()

        return itemnames

    def get_cache_refs_across_system(self):
        """
        Returns cross market cache cache refs

        :returns: list of cache refs

        """

        return self.get_cache_refs_for_instrument(ALL_KEYNAME)

    def cache_ref_list_with_protected_removed(self, cache_ref_list):
        """

        :param cache_ref_list: A list of cache refs
        :return: A list of cache refs, with anything protected removed
        """

        cache_ref_list = [
            cache_ref for cache_ref in cache_ref_list if not self[cache_ref].protected()]

        return listOfCacheRefs(cache_ref_list)

    def delete_items_for_stage(self, stage_name, delete_protected=False):
        """
        Delete all items with data for a particular stage

        :param stage_name: stage name eg rawdata
        :type stage_name: str

        :param deleted_protected: Delete everything, even stuff in self.protected?
        :type delete_protected: bool

        :returns: deleted data

        """

        cache_ref_list = self.get_cacherefs_for_stage(stage_name)
        self.delete_elements_in_cache_ref_list(
            cache_ref_list, delete_protected=delete_protected
        )

    def delete_items_for_instrument(
            self,
            instrument_code,
            delete_protected=False):
        """
        Delete everything in the system relating to a particular instrument_code

        :param instrument_code: Instrument to delete
        :type instrument_code: str

        :param deleted_protected: Delete everything, even stuff that is protected
        :type delete_protected: bool


        Example of usage: When working with a live system we listen to a message bus, if a new
        price is received then we delete things in the cache

        This means when we ask for self.optimal_positions(instrument_code) it
          has to recalc all intermediate steps as the cached

        However we ignore anything in self._protected This is normally cross
        sectional data which we only want to calculate periodically

        if delete_protected is True then we delete that stuff as well
        (this is roughly equivalent to creating the systems object from scratch)

        """

        cache_ref_list = self.get_cache_refs_for_instrument(instrument_code)
        self.delete_elements_in_cache_ref_list(
            cache_ref_list, delete_protected=delete_protected
        )

    def delete_items_across_system(self, delete_protected=False):
        """
        Deletes cross market cache itemnames (i.e. anything with instrument_code ALL_KEYNAME, normally 'all'

        :param deleted_protected: Delete everything, even stuff in self.protected?
        :type delete_protected: bool

        :returns: nothing

        """

        self.delete_items_for_instrument(
            ALL_KEYNAME, delete_protected=delete_protected)

    def delete_all_items(self, delete_protected=False):
        """
        Delete everything in the cache

        :param deleted_protected: Delete everything, even stuff in self.protected?
        :type delete_protected: bool

        :returns: deleted data

        """

        cache_ref_list = self.get_items_with_data()
        self.delete_elements_in_cache_ref_list(
            cache_ref_list, delete_protected=delete_protected
        )

    def delete_elements_in_cache_ref_list(
            self, cache_ref_list, delete_protected=False):
        """
        Delete everything in the cache

        :param deleted_protected: Delete everything, even stuff in self.protected?
        :type delete_protected: bool

        :returns: nothing

        """

        if not delete_protected:
            cache_ref_list = self.cache_ref_list_with_protected_removed(
                cache_ref_list)

        self._delete_elements_in_cache_ref_list_dangerous(cache_ref_list)

    def _delete_elements_in_cache_ref_list_dangerous(self, cache_ref_list):
        """
        Remove all elements in the given list from the cache
        DO NOT CALL DIRECTLY - doesn't check for protected status

        :param cache_ref_list:
        :return: nothing
        """

        ans = [
            self._delete_single_element_from_cache_dangerous(cache_ref)
            for cache_ref in cache_ref_list
        ]

        return None

    def _delete_single_element_from_cache_dangerous(self, cache_ref):
        """
        Remove the relevant ref from the cache
        DO NOT CALL DIRECTLY - doesn't check for protected status

        :param cache_ref: cacheRef instance
        :return: nothing
        """
        if cache_ref in self:
            del self[cache_ref]

    def set_item_in_cache(
            self,
            value,
            cache_ref,
            protected=False,
            not_pickable=False):
        """
        Set an item in a cache to a specific value.

        :param value: The value to set to
        :type value: Anything (normally pd.frames or floats)

        :param protected: is the item protected from deletion?
        :param nopickle: is the item not capable of pickling?

        :param cache_ref: The item to set
        :type cache_ref: cacheRef


        :returns: nothing
        """

        self[cache_ref] = cacheElement(
            value, protected=protected, not_pickable=not_pickable
        )

    def _get_item_from_cache(self, cache_ref):
        """
        Get the value of an item from the cache self._cache
        Never called directly, use calc_or_cache instead

        :param cache_ref: The item to get
        :type cache_ref: cacheRef

        :returns: MISSING_FROM_CACHE or item value
        """
        cache_element = self.get(cache_ref, MISSING_FROM_CACHE)

        if cache_element is MISSING_FROM_CACHE:
            return MISSING_FROM_CACHE

        return cache_element.value()

    def get_instrument_list(self):
        return self.parent.get_instrument_list()

    def calc_or_cache(
        self,
        func,
        this_stage,
        *args,
        protected=False,
        not_pickable=False,
        instrument_classify=True,
        **kwargs
    ):
        """
        Assumes that self._cache has an attribute itemname, and that is a dict

        If cached item exists return it. Else call
           func with *args and **kwargs; if the latter updates the cache

        :param func: function to call if missing from cache
        :type func: function

        :param this_stage: stage within system that is calling us
        :type this_stage: system stage

        :param args, kwargs: also passed to func if called

        :param instrument_classify: if True then we find an argument that is an instrument code, and add as a cache key

        :param protected: status flag; only set if the value is missing from the dict
        :param nopickle: status flag; only set if the value is missing from the dict

        :returns: contents of cache or result of calling function


        """
        if not self.are_we_caching():
            # not caching, just return the value
            value = func(this_stage, *args, **kwargs)
            return value

        # Turn all the arguments into things we can use to identify the cache
        # element uniquely
        cache_ref = self.cache_ref(
            func,
            this_stage,
            *args,
            instrument_classify=instrument_classify,
            **kwargs)

        value = self._get_item_from_cache(cache_ref)

        if value is MISSING_FROM_CACHE:
            # call the function. Note in the original function 'this_stage' was
            # 'self'
            value = func(this_stage, *args, **kwargs)
            self.set_item_in_cache(
                value,
                cache_ref,
                protected=protected,
                not_pickable=not_pickable)

        return value

    def cache_ref(self, func, this_stage, *args, instrument_classify=True, **kwargs):
        """
        Return cache key

        :param func: function we're calling

        :param this_stage: stage within system that is calling us
        :type this_stage: system stage

        :param instrument_classify: if True then we find an argument that is an instrument code, and add as a cache key

        :returns: str


        """

        # Turn all the arguments into things we can use to identify the cache
        # element uniquely
        itemname = func.__name__  # use name of function as reference in cache
        stage_name = (
            this_stage.name
        )  # use stage_name in case same function used across multiple stages

        if instrument_classify:
            list_of_codes = (
                self.get_instrument_list()
            )  # needed to identify instrument_code amongst args
        else:
            # if we're calling from the base system we don't want infinite
            # recursion
            list_of_codes = []

        (instrument_code, keyname) = resolve_args_to_code_and_key(
            args, list_of_codes
        )  # instrument involved, and/or other keys eg rule name
        flags = resolve_kwargs_to_str(
            kwargs
        )  # used mostly in accounts, eg to identify delayed returns

        cache_ref = cacheRef(
            stage_name, itemname, instrument_code, flags=flags, keyname=keyname
        )

        return cache_ref


def resolve_args_to_code_and_key(args, list_of_codes):
    """
    Resolves a list of placed args for a function
    Pulls out the first arg that is an instrument_code (in list_of_codes)

    :param args:
    :param list_of_codes:
    :return: (instrument_code, keyname)
    """
    keyname_list = []
    args_to_process = list(args)
    instrument_code = None

    while len(args_to_process) > 0:
        individual_arg = args_to_process.pop()

        # we only take the first arg that is an instrument code
        if instrument_code is None:
            if individual_arg in list_of_codes:
                instrument_code = individual_arg
                continue
        # otherwise add to keynames
        keyname_list.append(str(individual_arg))

    if instrument_code is None:
        # no instrument in arguments, so must be a cross market thing
        instrument_code = ALL_KEYNAME

    # Make into a key that's nicer to look at
    if len(keyname_list) == 0:
        keyname = ""
    elif len(keyname_list) == 1:
        keyname = str(keyname_list[0])
    else:
        keyname = str(keyname_list)

    return (instrument_code, keyname)


def resolve_kwargs_to_str(kwargs):
    """
    Turn a list of named arguments into a flag string representing them,
    eg resolve_flags_to_str(dict(a=1, b=2)
       will return "a=1, b=2"

    :param kwargs: dict of arguments passed to some function
    :return: str
    """

    def resolve_individual_flag(single_flag, kwargs):
        argvalue = str(kwargs[single_flag])
        return "%s=%s" % (single_flag, str(argvalue))

    long_flag_string = [
        resolve_individual_flag(
            single_flag,
            kwargs) for single_flag in kwargs.keys()]

    return ", ".join(long_flag_string)


# null decorator doesn't do antyihng
def null_decorator(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


# generic decorator for caching
def stage_access_cache_decorator(protected=False, not_pickable=False):
    """

    :param protected: is this protected from casual deletion?
    :param not_pickable: can this not be saved using the pickle function (complex objects)
    :return: decorator function
    """

    # this pattern from Beazleys book; function inside function to get
    # arguments to wrapper
    def decorate(func):
        @wraps(func)
        # note 'self' as always called from inside stage class
        def wrapper(self, *args, **kwargs):
            system = self.parent
            this_stage = self

            ans = system.cache.calc_or_cache(
                func,
                this_stage,
                *args,
                protected=protected,
                not_pickable=not_pickable,
                instrument_classify=True,
                **kwargs
            )

            return ans

        return wrapper

    return decorate


# generic decorator for caching in base system
def base_system_cache(protected=False, not_pickable=False):
    """

    :param protected: is this protected from casual deletion?
    :param not_pickable: can this not be saved using the pickle function (complex objects)
    :return: decorator function
    """

    # this pattern from Beazleys book; function inside function to get
    # arguments to wrapper
    def decorate(func):
        @wraps(func)
        # note 'self' as always called from inside system class
        def wrapper(self, *args, **kwargs):
            system = self

            # instrument_classify has to be false, else infinite loop
            ans = system.cache.calc_or_cache(
                func,
                system,
                *args,
                protected=protected,
                not_pickable=not_pickable,
                instrument_classify=False,
                **kwargs
            )

            return ans

        return wrapper

    return decorate


# actual decoraters used, snappier names for 'stage wiring'
input = null_decorator
dont_cache = null_decorator
diagnostic = stage_access_cache_decorator
output = stage_access_cache_decorator
