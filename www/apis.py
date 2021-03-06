#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Victor Song'

'''
JSON API definition
'''

class APIError(Exception):
    '''
    The base APIError which contains error(required), data(optional) and message(optional).
    '''
    def __init__(self, error, data='', message=''):
        super().__init__(message)
        self.error = error
        self.data = data
        self.message = message

class APIValueError(APIError):
    ''' 
    Indicate the input value has error or invalid. The data specifies the error field of input form
    '''
    def __init__(self, field, message=''):
        super().__init__('value:invalid', field, message)

class APIResourceNotFoundError(APIError):
    '''
    Indicate the resource was not found. The data specifies the resource name.
    '''
    def __init__(self, field, message=''):
        super().__init__('value:notfound', field, message)

class APIPermissionError(APIError):
    '''
    Indicate the api has no permission
    '''
    def __init__(self, field, message=''):
        super().__init__('permission:forbidden', 'permission', message)

class Page(object):
    def __init__(self, item_count: int, page_index:int=1, page_size:int=10):
        self.item_count = item_count
        self.page_size = page_size
        self.page_count = item_count // page_size + (1 if item_count % page_size > 0 else 0)
        if (0 == item_count) or (page_index > self.page_count):
            self.offset = 0
            self.limit = 0
            self.page_index = 1
        else:
            self.page_index = page_index
            self.offset = self.page_size * (page_index - 1)
            self.limit = self.page_size
        self.has_next = self.page_index < self.page_count
        self.has_previous = self.page_index > 1
    
    def __str__(self):
        return 'item_count: %s, page_count: %s, page_index: %s, page_size: %s, offset: %s, limit: %s' % (self.item_count, self.page_count, self.page_index, self.page_size, self.offset, self.limit)
    
    __repr__ = __str__