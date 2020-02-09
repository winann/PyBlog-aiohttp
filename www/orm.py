#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Victor Song'

'''
关系对象映射
'''

import asyncio, logging
import aiomysql

def log(sql: str, args: tuple = ()):
    ''' 自定义 log '''
    logging.info('SQL: %s', sql)

async def create_pool(loop, **kw):
    ''' 创建 SQL 链接 '''
    logging.info('create database connection pool...')
    global __pool
    __pool = await aiomysql.create_pool(
        loop=loop,
        maxsize=10,
        host=kw.get('host', 'localhost'),
        port=kw.get('port', 3306),
        user=kw['user'],
        password=kw['password'],
        db = kw['db'],
        # charset=kw.get('charset', 'utf8'),
        autocommit=kw.get('autocommit', True),
    )

async def select(sql: str, args, size: int=None):
    ''' 查询语句 '''
    log(sql, args=args)
    global __pool
    async with __pool.get() as connect:
        async with connect.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(sql.replace('?', '%s'), args or ())
            if size:
                result = await cursor.fetchmany(size)
            else:
                result = await cursor.fetchall()
            logging.info('rows returned: %s', len(result))
        return result

async def execute(sql: str, args, autocommit: bool = True):
    ''' 执行增删改语句 '''
    global __pool
    async with __pool.get() as connect:
        if not autocommit:
            connect.begin()
        try:
            async with connect.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(sql.replace('?', '%s'), args or ())
                affected = cursor.rowcount
            if not autocommit:
                connect.commit()
        except BaseException as e:
            if not autocommit:
                await connect.rollback()
            logging.error(e)
            raise e
        return affected

class Field(object):
    ''' 各种字段的父类 
    Attributes:
        name: 字段的名称
        column_type: 列的类型
        primary_key: 主键
        default: 默认值
    '''
    def __init__(self, name: str, column_type: str, primary_key: bool, default):
        ''' 初始化方法 '''
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default
    def __str__(self):
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)

class StringField(Field):
    ''' 字符串呀 '''
    def __init__(self, name: str = None, primary_key: bool = False, default=None, ddl='varchar(100)'):
        super().__init__(name, ddl, primary_key, default)

class BooleanField(Field):
    ''' Bool 值 '''
    def __init__(self, name=None, defalt=False):
        super().__init__(name, 'boolean', False, defalt)

class IntegerField(Field):
    ''' 整型 '''
    def __init__(self, name: str = None, primary_key: bool = False, default=0):
        super().__init__(name, 'bigint', primary_key, default)

class FloatField(Field):
    ''' 浮点型 '''
    def __init__(self, name: str = None, primary_key: bool = False, default=0.0):
        super().__init__(name, 'real', primary_key, default)

class TextField(Field):
    ''' Text 类型 '''
    def __init__(self, name: str = None, default=None):
        super().__init__(name, 'text', False, default)

def create_args_strings(num: int):
    ''' 创建 SQL 参数字符串 '''
    l = []
    for _ in range(num):
        l.append('?')
    return ', '.join(l)

class ModelMetaclass(type):
    ''' 所有 Model 类的创建魔术代码，用于定义各个 Model 的数据库操作属性 '''
    def __new__(cls, name, bases, attrs):
        if 'Model' == name:
            return type.__new__(cls, name, bases, attrs)
        table_name = attrs.get('__table__', name)
        logging.info('found model: %s (table: %s)' % (name, table_name))
        mapping = dict()
        fields = []
        primaty_key = None
        for k, v in attrs.items():
            if isinstance(v, Field):
                logging.info('  found mapping: %s ==> %s' % (k, v))
                mapping[k] = v
                if v.primary_key:
                    if primaty_key:
                        raise ValueError('Duplicate primary key for field: %s' % k)
                    primaty_key = k
                else:
                    fields.append(k)
        if not primaty_key:
            raise ValueError('Primary key not found.')
        for k in mapping.keys():
            attrs.pop(k)
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))
        attrs['__mapping__'] = mapping
        attrs['__table__'] = table_name
        attrs['__primary_key__'] = primaty_key
        attrs['__fields__'] = fields
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaty_key, ', '.join(escaped_fields), table_name)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (table_name, ', '.join(escaped_fields), primaty_key, create_args_strings(len(fields) + 1))
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (table_name, ', '.join(map(lambda f: '%s=?' % (mapping.get(f).name or f), fields)), primaty_key)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (table_name, primaty_key)
        return type.__new__(cls, name, bases, attrs)

class Model(dict, metaclass=ModelMetaclass):
    def __init__(self, **kw):
        super().__init__(**kw)
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'model' object has no attribute '%s'" % key)
    def __setattr__(self, key, value):
        self[key] = value
    def getValue(self, key):
        return getattr(self, key, None)
    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mapping__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s:%s' % (key, str(value)))
                setattr(self, key, value)
        return value
    @classmethod
    async def findAll(cls, where=None, args=None, **kw):
        ''' find object by where clause. '''
        sql = [cls.__select__]
        if where:
            sql.append('where ')
            sql.append(where)
        if not args:
            args = []
        order_by = kw.get('orderBy', None)
        if order_by:
            sql.append('order by ')
            sql.append(order_by)
        limit = kw.get('limit', None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                sql.append(limit)
            elif isinstance(limit, tuple) and 2 == len(limit):
                sql.append('?,?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))
        result = await select(' '.join(sql), args)
        return [cls(**r) for r in result]
    @classmethod
    async def find_number(cls, selectField, where=None, args=None):
        ''' find number by select and where. '''
        sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)
        result = await select(' '.join(sql), args, 1)
        if 0 == len(result):
            return None
        return result[0]['_num_']

    @classmethod
    async def find(cls, pk):
        ' find object by primary key '
        result = await select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
        if 0 == len(result):
            return None
        return cls(**result[0])

    async def save(self):
        ' Save object to database '
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = await execute(self.__insert__, args)
        if 1 != rows:
            logging.warn('Failed to insert record: affected rows: %s' % rows)
    async def update(self):
        ' update object to database '
        args = list(map(self.getValue, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = await execute(self.__update__, args)
        if 1 != rows:
            logging.warn('Failed to update by primary key: affected rows: %s' % rows)
    async def remove(self):
        ' delete object from database '
        args = [self.getValue(self.__primary_key__)]
        rows = await execute(self.__delete__, args)
        if 1 != rows:
            logging.warn('Failed to remove by primary key: affeted rows:%s' % rows)

