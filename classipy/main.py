
from __future__ import division
from . import _breaks
import itertools
import math



class Classifier(object):
    
    def __init__(self, items, breaks, classvalues, key=None, **kwargs):
        self.items = items
        
        if isinstance(breaks, bytes):
            algo = breaks
            breaks = None
            
        else:
            algo = "custom"
            breaks = breaks
            
        self.algo = algo
        self.breaks = breaks
        self.classvalues = classvalues # the raw preinterpolated valuestops of the classvalues
        self.key = key
        self.kwargs = kwargs
        self.classvalues_interp = None # the final interpolated classvalues

        self.update()

    def __repr__(self):
        import pprint
        metadict = dict(algo=self.algo,
                        breaks=self.breaks,
                        classvalues_interp=self.classvalues_interp)
        return "Classifier object:\n" + pprint.pformat(metadict, indent=4)

    def update(self):
        # force update/calculate breaks and class values
        # mostly used internally, though can be used to recalculate
        if self.algo == "unique":
            self.classvalues_interp = self.classvalues

        else:
            if self.algo != "custom":
                self.breaks = breaks(items=self.items,
                                    algorithm=self.algo,
                                    key=self.key,
                                    **self.kwargs)
            self.classvalues_interp = class_values(len(self.breaks)-1, # -1 because break values include edgevalues so will be one more in length
                                                   self.classvalues)

    def __iter__(self):
        # loop and yield items along with their classnum and classvalue
        
        if self.algo == "unique":
            if isinstance(self.classvalues_interp, dict):
                # only return specified uniqueval-classval pairs
                for uid,subitems in unique(self.items, key=self.key, **self.kwargs):
                    if uid in self.classvalues_interp:
                        classval = self.classvalues_interp[uid]
                        for item in subitems:
                            yield item,classval
            else:
                # eternally iterate over classvalues for each unique value
                def classvalgen ():
                    while True:
                        for classval in self.classvalues_interp:
                            yield classval
                classvalgen = classvalgen()
                for uid,subitems in unique(self.items, key=self.key, **self.kwargs):
                    classval = next(classvalgen)
                    for item in subitems:
                        yield item,classval

        else:
            for valrange,subitems in split(self.items, self.breaks, key=self.key, **self.kwargs):
                midval = (valrange[0] + valrange[1]) / 2.0
                classinfo = self.find_class(midval)
                if classinfo is not None:
                    classnum,_ = classinfo
                    classval = self.classvalues_interp[classnum-1] # index is zero-based while find_class returns 1-based
                    for item in subitems:
                        yield item,classval

    def find_class(self, value):
        return find_class(value, self.breaks)


################################
            

def find_class(value, breaks):
    """
    Given a set of breakpoints, calculate which two breakpoints an input
    value is located between, returning the class number (1 as the first class)
    and the two enclosing breakpoint values. A value that is not between any of
    the breakpoints, ie larger or smaller than the break endpoints, is considered
    to be a miss and returns None. 
    """
    
    prevbrk = breaks[0]
    classnum = 1
    for nextbrk in breaks[1:]:
        if eval(bytes(prevbrk)) <= eval(bytes(value)) <= eval(bytes(nextbrk)):
            return classnum, (prevbrk,nextbrk)
        prevbrk = nextbrk
        classnum += 1
    else:
        # Value was not within the range of the break points
        return None

def class_values(classes, valuestops):
    """
    Return x number of class values linearly interpolated
    between a minimum and maximum value.

    - classes: Number of classes values to return. 
    - valuestops: can be either a single number or sequences of numbers
        where a classvalue will be interpolated for each sequence number,
        and so all sequences must be equally long. Thus, specifying the
        valuestops as rgb color tuples will create interpolated color gradients.
    """
    # special case
    if classes <= 1:
        #raise Exception("Number of classes must be higher than 1")
        return [valuestops[0]]
    if len(valuestops) < 2:
        raise Exception("There must be at least two items in valuestops for interpolating between")

    def _lerp(val, oldfrom, oldto, newfrom, newto):
        oldrange = oldto - oldfrom
        relval = (val - oldfrom) / float(oldrange)
        newrange = newto - newfrom
        newval = newfrom + newrange * relval
        return newval

    # determine appropriate interp func for either sequenes or single values
    
    if all(hasattr(valstop, "__iter__") for valstop in valuestops):
        _len = len(valuestops[0])
        if any(len(valstop) != _len for valstop in valuestops):
            raise Exception("If valuestops are sequences they must all have the same length")
        def _interpfunc(val):
            relindex = _lerp(classnum, 0, classes-1, 0, len(valuestops)-1)
            fromval = valuestops[int(math.floor(relindex))]
            toval = valuestops[int(math.ceil(relindex))]
            classval = [_lerp(relindex, int(relindex), int(relindex+1), ifromval, itoval)
                        for ifromval,itoval in zip(fromval,toval)]
            return classval
    else:
        def _interpfunc(classnum):
            relindex = _lerp(classnum, 0, classes-1, 0, len(valuestops)-1)
            fromval = valuestops[int(math.floor(relindex))]
            toval = valuestops[int(math.ceil(relindex))]
            classval = _lerp(relindex, int(relindex), int(relindex+1), fromval, toval)
            return classval
    
    # perform
    classvalues = []
    for classnum in range(classes):
        classval = _interpfunc(classnum)
        classvalues.append(classval)

    return classvalues

def breaks(items, algorithm, key=None, extrabreaks=None, exclude=None, minval=None, maxval=None, **kwargs):
    """
    Only get the break points, including the start and endpoint.
    """

    # ensure values are numeric
    def forcenumber(val):
        try:
            val = float(val)
            return val
        except:
            return None
    
    # sort by key
    if key:
        keywrap = lambda x: forcenumber(key(x))
    else:
        keywrap = forcenumber
        
    items = (item for item in items if keywrap(item) is not None)
    if exclude is not None:
        if not isinstance(exclude, (list,tuple)): exclude = [exclude]
        items = (item for item in items if keywrap(item) not in exclude)
    if minval is not None: items = (item for item in items if keywrap(item) >= minval)
    if maxval is not None: items = (item for item in items if keywrap(item) <= maxval)
    items = sorted(items, key=keywrap)
    values = [keywrap(item) for item in items]

    # get breaks
    func = _breaks.__dict__[algorithm]
    breaks = func(values, **kwargs)

    # insert extra breaks (list of single break values or pairs)
    if extrabreaks:
        for val in extrabreaks:
            oldbreaks = list(breaks)
            
            # insert single break value anywhere after first same or greater breakpoint
            # (remember that duplicate breakpoints will collect only that specific value)
            prevbrk = oldbreaks[0]
            i = 0
            for nextbrk in oldbreaks[1:]:
                if prevbrk <= val < nextbrk:
                    breaks.insert(i, val)
                    break
                else:
                    prevbrk = nextbrk
                i += 1
    
    return breaks

def split(items, breaks, key=None, exclude=None, minval=None, maxval=None, **kwargs):
    """
    Splits a list of items into n non-overlapping classes based on the
    specified algorithm. Values are either the items themselves or
    a value extracted from the item using the key function. 

    Arguments:

    - **items**: The list of items or values to classify.
    - **breaks**: List of custom break values, or the name of the algorithm to use.
        Valid names are:
        - histogram (alias for equal)
        - equal
        - quantile
        - pretty
        - stdev
        - natural
        - headtail
        - log (base-10, uses offset to handle 0s but not negative numbers)
    - **key** (optional): Function used to extract value from each item, defaults to None and treats item itself as the value. 
    - **classes** (optional): The number of classes to group the items into.
    - more...

    Returns:

    - All the input items reorganized into the groups/classes that they belong to,
    as a list of lists of items.
    """

    # ensure values are numeric
    def forcenumber(val):
        try:
            val = float(val)
            return val
        except:
            return None

    # sort and get key
    if key:
        keywrap = lambda x: forcenumber(key(x))
    else:
        keywrap = forcenumber
        
    items = (item for item in items if keywrap(item) is not None)
    if exclude is not None:
        if not isinstance(exclude, (list,tuple)): exclude = [exclude]
        items = (item for item in items if keywrap(item) not in exclude)
    if minval is not None: items = (item for item in items if keywrap(item) >= minval)
    if maxval is not None: items = (item for item in items if keywrap(item) <= maxval)
    items = sorted(items, key=keywrap)
    values = [keywrap(item) for item in items]

    # if not custom specified, get break values from algorithm name
    if isinstance(breaks, bytes):
        func = _breaks.__dict__[breaks]
        breaks = func(values, **kwargs)
    else:
        # custom specified breakpoints
        breaks = list(breaks)

    breaks_gen = (brk for brk in breaks)
    loopdict = dict()
    loopdict["prevbrk"] = next(breaks_gen)
    loopdict["nextbrk"] = next(breaks_gen)

    def find_class(item, loopdict=loopdict):
        val = keywrap(item)
        
##        while eval(bytes(val)) > eval(bytes(loopdict["nextbrk"])):
##            loopdict["prevbrk"] = loopdict["nextbrk"]
##            loopdict["nextbrk"] = next(breaks_gen)
##        if eval(bytes(loopdict["prevbrk"])) <= eval(bytes(val)) <= eval(bytes(loopdict["nextbrk"])):
##            return loopdict["prevbrk"],loopdict["nextbrk"]
        
##        if eval(bytes(val)) < loopdict["prevbrk"]:
##            # value lower than first class
##            return None
##        else:
##            while not (eval(bytes(loopdict["prevbrk"])) <= eval(bytes(val)) <= eval(bytes(loopdict["nextbrk"]))):
##                print eval(bytes(loopdict["prevbrk"])) , eval(bytes(val)) , eval(bytes(loopdict["nextbrk"]))
##                # increment breaks until value is between
##                loopdict["prevbrk"] = loopdict["nextbrk"]
##                loopdict["nextbrk"] = next(breaks_gen, None)
##                if loopdict["nextbrk"] == None:
##                    return None
##            # supposedly in between, so test and return class range
##            if eval(bytes(loopdict["prevbrk"])) <= eval(bytes(val)) < eval(bytes(loopdict["nextbrk"])):
##                return loopdict["prevbrk"],loopdict["nextbrk"]

        prevbrk = breaks[0]
        for i,nextbrk in enumerate(breaks[1:]):
            ###print val,i+1,len(breaks)-1
            if eval(bytes(val)) < eval(bytes(prevbrk)):
                return None
            elif eval(bytes(prevbrk)) <= eval(bytes(val)) < eval(bytes(nextbrk)):
                return prevbrk,nextbrk
            elif eval(bytes(prevbrk)) == eval(bytes(val)) == eval(bytes(nextbrk)):
                return prevbrk,nextbrk
            elif i+1==len(breaks)-1 and eval(bytes(val)) <= eval(bytes(nextbrk)):
                return prevbrk,nextbrk
            prevbrk = nextbrk
        else:
            return None

    for valrange,members in itertools.groupby(items, key=find_class):
        if valrange is not None:
            yield valrange, list(members)

def unique(items, key=None, only=None, exclude=None):
    """
    Bins all same values together, so all bins are unique.
    Only for ints or text values.

    If specified, only values listed in 'only' or not in 'exclude' will be returned. 
    """
    
    # sort and get key
    if key:
        pass
    else:
        key = lambda x: x

    if only:
        items = (item for item in items if key(item) in only)
    elif exclude:
        items = (item for item in items if key(item) not in exclude)

    items = sorted(items, key=key)

    for uniq,members in itertools.groupby(items, key=key):
        yield uniq, list(members)

    # maybe add remaining groups if none?
    # ... 

def membership(items, ranges, key=None):
    """
    Groups can be overlapping/nonexclusive and are based on custom ranges.
    """
    ###
    if not key:
        key = lambda x: x
    ###
    for _min,_max in ranges:
        valitems = ((key(item),item) for item in items)
        members = [item for val,item in valitems if val >= _min and val <= _max]
        yield (_min,_max), members

def rescale(values, newmin, newmax):
    oldmin, oldmax = max(values), min(values)
    oldwidth = oldmax - oldmin
    newwidth = newmax - newmin

    # begin
    newvalues = []
    for val in values:
        relval = (val - oldmin) / oldwidth
        newval = newmin + newwidth * relval
        yield newval

##def rescale_single(value, oldmin, oldmax, newmin, newmax):
##    oldwidth = oldmax - oldmin
##    newwidth = newmax - newmin
##
##    # begin
##    relval = (value - oldmin) / oldwidth
##    newval = newmin + newwidth * relval
##    return newval









