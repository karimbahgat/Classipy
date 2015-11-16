
from __future__ import division
from . import _breaks
import itertools

def find_class(value, breaks):
    """
    Given a set of breakpoints, calculate which two breakpoints an input
    value is located between, returning the class number (1 as the first class)
    and the two enclosing breakpoint values. The breakpoints must include the maximum
    and minimum possible value. 
    """
    prevbrk = breaks[0]
    classnum = 1
    for nextbrk in breaks[1:]:
        if value <= nextbrk:
            return classnum, (prevbrk,nextbrk)
        classnum += 1
    else:
        raise Exception("Value was not within the range of the break points")

def class_values(classes, fromval, toval):
    """
    Return x number of class values linearly interpolated
    between a minimum and maximum value.

    - classes: Number of classes values to return. 
    - fromval and toval: can be either a single number or sequences of numbers
        where a classvalue will be interpolated for each sequence number,
        and so both sequences must be equally long. Thus, specifying the from
        and to values as rgb color tuples will create interpolated color gradients.
    """

    def _lerp(val, oldfrom, oldto, newfrom, newto):
        oldrange = oldto - oldfrom
        relval = (val - oldfrom) / float(oldrange)
        newrange = newto - newfrom
        newval = newfrom + newrange * relval
        return newval

    # determine appropriate interp func for either sequenes or single values
    if hasattr(fromval, "__iter__") and hasattr(fromval, "__iter__"):
        if len(fromval) != len(toval):
            raise Exception("If fromval and toval are sequences they must both have the same length")
        def _interpfunc(val):
            classval = [ _lerp(classnum, 0, classes-1, ifromval, itoval)
                         for ifromval,itoval in zip(fromval,toval) ]
            return classval
    else:
        def _interpfunc(val):
            return _lerp(classnum, 0, classes-1, fromval, toval)
    
    # perform
    classvalues = []
    for classnum in range(classes):
        classval = _interpfunc(classnum)
        classvalues.append(classval)

    return classvalues

def breaks(items, algorithm, key=None, **kwargs):
    """
    Only get the break points, including the start and endpoint.
    """
    # sort by key
    if key:
        items = sorted(items, key=key)
        values = [key(item) for item in items]
    else:
        values = items = sorted(items)
        
    # get breaks
    func = _breaks.__dict__[algorithm]
    breaks = func(values, **kwargs)
    
    return breaks

def split(items, breaks, key=None, **kwargs):
    """
    Splits a list of items into n non-overlapping classes based on the
    specified algorithm. Values are either the items themselves or
    a value extracted from the item using the key function. 

    Arguments:

    - **items**: The list of items or values to classify.
    - **breaks**: List of custom break values or the name of the algorithm to use.
        Valid names are:
        - histogram (alias for equal)
        - equal
        - quantile
        - pretty
        - stdev
        - natural
        - headtail
    - **key** (optional): Function used to extract value from each item, defaults to None. 
    - **classes** (optional): The number of classes to group the items into.
    - more...

    Returns:

    - All the input items reorganized into the groups/classes that they belong to,
    as a list of lists of items.
    """

    # sort and get key
    if key:
        items = sorted(items, key=key)
        values = [key(item) for item in items]
    else:
        key = lambda x: x
        values = items = sorted(items)

    # if not custom specified, get break values from algorithm name
    if isinstance(breaks, bytes):
        func = _breaks.__dict__[breaks]
        breaks = func(values, **kwargs)
    else:
        # custom specified breakpoints, ensure endpoints are included
        if breaks[0] != values[0]: breaks.insert(0, values[0])
        if breaks[-1] != values[-1]: breaks.append(values[-1])

    breaks_gen = (brk for brk in breaks)
    loopdict = dict()
    loopdict["prevbrk"] = next(breaks_gen)
    loopdict["nextbrk"] = next(breaks_gen)

    def find_class(item, loopdict=loopdict):
        val = key(item)
        if val > loopdict["nextbrk"]:
            loopdict["prevbrk"] = loopdict["nextbrk"]
            loopdict["nextbrk"] = next(breaks_gen)
        return loopdict["prevbrk"],loopdict["nextbrk"]

    groups = []
    for valrange,members in itertools.groupby(items, key=find_class):
        grp = (valrange, list(members))
        groups.append(grp)
        
    return groups

def unique(items, key=None):
    """
    Bins all same values together, so all bins are unique.
    Only for ints or text values.
    """
    
    # sort and get key
    if key:
        items = sorted(items, key=key)
    else:
        key = lambda x: x
        items = sorted(items)

    groups = []
    for uniq,members in itertools.groupby(items, key=key):
        grp = (uniq, list(members))
        groups.append(grp)

    # maybe add remaining groups if none?
    # ... 
        
    return groups

def membership(items, ranges, key=None):
    """
    Groups can be overlapping/nonexclusive and are based on custom ranges.
    """
    ###
    if not key:
        key = lambda x: x
    ###
    groups = []
    for _min,_max in ranges:
        valitems = ((key(item),item) for item in items)
        members = [item for val,item in valitems if val >= _min and val <= _max]
        groups.append( ((_min,_max), members) )
    return groups

##def rescale(values, newmin, newmax):
##    oldmin, oldmax = max(values), min(values)
##    oldwidth = oldmax - oldmin
##    newwidth = newmax - newmin
##
##    # begin
##    newvalues = []
##    for val in values:
##        relval = (val - oldmin) / oldwidth
##        newval = newmin + newwidth * relval
##        newvalues.append(newval)
##
##    return newvalues
##
##def rescale_single(value, oldmin, oldmax, newmin, newmax):
##    oldwidth = oldmax - oldmin
##    newwidth = newmax - newmin
##
##    # begin
##    relval = (value - oldmin) / oldwidth
##    newval = newmin + newwidth * relval
##    return newval









