#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Victor Song'

'''
Web 框架
'''

import asyncio, functools, inspect, logging, os
from urllib import parse
from aiohttp import web
from apis import APIError

def get(path):
    '''
    Define decorator @get('/path')
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'GET'
        wrapper.__route__ = path
        return wrapper
    return decorator

def post(path):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'POST'
        wrapper.__route__ = path
        return wrapper
    return decorator

def get_required_kw_args(func):
    args = []
    params = inspect.signature(func).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)

def get_name_kw_args(func):
    args = []
    params = inspect.signature(func).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)

def has_named_kw_args(func):
    params = inspect.signature(func).parameters
    for _, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True

def has_var_kw_arg(func):
    params = inspect.signature(func).parameters
    for _, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True

def has_request_arg(func):
    signature = inspect.signature(func)
    params = signature.parameters
    found = False
    for name, param in params.items():
        if 'request' == name:
            found = True
            continue
        if found and (param.kind != inspect.Parameter.VAR_KEYWORD and param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY):
            raise ValueError('request parameter must be the last named parameter in function: %s%s' % (func.__name__, str(signature)))
    return found

class RequestHandler(object):
    def __init__(self, app, func):
        self._app = app
        self._func = func
        self._has_request_arg = has_request_arg(func)
        self._has_var_kw_arg = has_var_kw_arg(func)
        self._has_named_kw_args = has_named_kw_args(func)
        self._named_kw_args = get_name_kw_args(func)
        self._required_kw_args = get_required_kw_args(func)
    async def __call__(self, request: web.Request):
        kw = None
        if self._has_var_kw_arg or self._has_named_kw_args or self._has_request_arg:
            if 'POST' == request.method:
                if not request.content_type:
                    return web.HTTPBadRequest('Missing Content-Type.')
                ct = request.content_type.lower()
                if ct.startswith('application/json'):
                    params = await request.json()
                    if not isinstance(params, dict):
                        return web.HTTPBadRequest('JSON body must be object')
                    kw = params
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                    params = await request.post()
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest('Unsupport Content-Type: %s' % request.content_type)
            if 'GET' == request.method:
                query_string = request.query_string
                if query_string:
                    kw = dict()
                    for k, v in parse.parse_qs(query_string, True).items():
                        kw[k] = v[0]
        if kw is None:
            kw = dict(**request.match_info)
        else:
            if not self._has_var_kw_arg and self._named_kw_args:
                copy = dict()
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy
            for k, v in request.match_info.items():
                if k in kw:
                    logging.warning('Duplicate arg name in named arg and kw arg: %s' % k)
                kw[k] = v
        if self._has_request_arg:
            kw['request'] = request
        if self._required_kw_args:
            for name in self._required_kw_args:
                if not name in kw:
                    return web.HTTPBadRequest('Missing argument: %s' % name)
        logging.info('call with args: %s' % str(kw))
        try:
            r = await self._func(**kw)
            return r
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)

def add_static(app):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    app.router.add_static('/static/', path)
    logging.info('add static %s => %s' % ('/static/', path))
    
def add_route(app, func):
    method = getattr(func, '__method__', None)
    path = getattr(func, '__route__', None)
    if path is None or method is None:
        raise ValueError('@get or @post not define in %s.' % str(func))
    if not asyncio.iscoroutinefunction(func) and not inspect.isgenerator(func):
        func = asyncio.coroutine(func)
    logging.info('add route %s %s => %s(%s)' % (method, path, func.__name__, ', '.join(inspect.signature(func).parameters.keys())))
    app.router.add_route(method, path, RequestHandler(app, func))

def add_routes(app, module_name: str):
    n = module_name.rfind('.')
    if (-1) == n:
        mod = __import__(module_name, globals(), locals())
        print(mod)
    else:
        name = module_name[n + 1:]
        mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
    for attr in dir (mod):
        if attr.startswith('_'):
            continue
        func = getattr(mod, attr)
        if callable(func):
            method = getattr(func,'__method__', None)
            path = getattr(func, '__route__', None)
            if method and path:
                add_route(app, func)