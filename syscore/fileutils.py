import os
import sys

"""
IMPORTANT: for this to work all modules must be imported into namespace
"""
import syscore

def get_pathname_for_package(package_name, paths_or_files=[]):
    """
    Returns the filename of part of a package
    
    :param package_name: Name of python package
    :type str:
    
    :param path: Subdirectory within 
        
    :returns: full pathname of package
    
    """
    
    d = os.path.dirname(sys.modules[package_name].__file__)

    if len(paths_or_files)==0:
        return d
    
    last_item_in_list=paths_or_files.pop()

    pathname = os.path.join(get_pathname_for_package(package_name, paths_or_files),  last_item_in_list)

    return pathname

if __name__ == '__main__':
    import doctest
    doctest.testmod()