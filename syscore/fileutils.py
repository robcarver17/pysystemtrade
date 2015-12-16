import os
import sys
import systems

def get_pathname_for_package(*args):
    """
    Returns the filename of part of a package
    
    :param package_name: Name of python package
    :type str:
    
    :param path: Subdirectory within 
        
    :returns: full pathname of package
    
    """
    args=list(args)
    package_name=args[0]    
    paths_or_files=args[1:]
    d = os.path.dirname(sys.modules[package_name].__file__)

    if len(paths_or_files)==0:
        return d
    
    last_item_in_list=args.pop()
    pathname = os.path.join(get_pathname_for_package(*args),  last_item_in_list)

    return pathname

if __name__ == '__main__':
    import doctest
    doctest.testmod()