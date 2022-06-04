"""
Cache related things go here

Copyright (c) 2022 Ben Z

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
"""

from collections import OrderedDict
from models import Translated, Detected
import typing


class Cache:
    """
    LRU based cache to store api calls, 2 will usually be created, one for translations, and one for detections, respectively
    """
    
    def __init__(self, capacity: int = 1000) -> None:
        """
        Cache Init
        
        Parameters
        ----------
        capacity: int
            The amount of items to be stored in the cache
            Default 1,000
            
        """
        self.cache = OrderedDict()
        self.capacity = capacity

    def get(self, key: int) -> typing.Union[Translated, Detected]:
        """
        Retrieve a key
        """
        if key not in self.cache:
            return -1
        else:
            self.cache.move_to_end(key)
            return self.cache[key]

    def add(self, key: int, value: int) -> None:
        """
        Add a key and value to the cache
        """
        self.cache[key] = value
        self.cache.move_to_end(key)
        if len(self.cache) > self.capacity:
            self.cache.popitem(last = False)
