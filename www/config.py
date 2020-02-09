#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Victor Song'

'''
Configuration
'''

import config_default

class Dict(dict):
    '''
    Simple dict but support access as x.y style.
    '''
    def __init__(self, names=(), values=(), **kw):
        super().__init__(kw)
        for k, v in zip(names, values):
            self[k] = v
    
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError("'Dict' object has no attribute '%s'" % key)
    
    def __setattr__(self, key, value):
        self[key] = value

def merge(defaults: dict, override: dict) -> dict:
    r = {}
    for k, v in defaults.items():
        if k in override:
            if isinstance(v, dict):
                r[k] = merge(v, override[k])
            else:
                r[k] = override[k]
        else:
            r[k] = v
    return r

def toDict(dic: dict) -> dict:
    d = Dict()
    for k, v in dic.items():
        d[k] = toDict(v) if isinstance(v, dict) else v
    return d

configs = config_default.configs

try:
    import config_override
    configs = merge(configs, config_override.configs)
except ImportError:
    pass
configs = toDict(configs)