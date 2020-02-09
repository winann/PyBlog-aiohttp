#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Victor Song'

'''
部署工具
'''

from fabric import Connection, task, Config
from datetime import datetime

_TAR_FILE = 'dist-pyblog.tar.gz'
_REMOTE_TMP_TAR = '/root/Workspace/tmp/%s' % _TAR_FILE
_REMOTE_BASE_DIR = '/root/Workspace/PyBlog'

def build(c):
    includes = ['static', 'templates', '*.py']
    excludes = ['test', '.*', '*.pyc', '*.pyo']
    c.local('rm -rf dist/%s' % _TAR_FILE)
    with c.cd('www'):
        cmd = ['tar', '--dereference', '-czvf', '../dist/%s' % _TAR_FILE]
        cmd.extend(['--exclude=\'%s\'' % ex for ex in excludes])
        cmd.extend(includes)
        c.local(' '.join(cmd))

def transfer(c):
    newdir = 'www-%s' % datetime.now().strftime('%y-%m-%d_%H.%M.%S')
    c.run('rm -f %s' % _REMOTE_TMP_TAR)
    c.put('dist/%s' % _TAR_FILE, _REMOTE_TMP_TAR)
    with c.cd(_REMOTE_BASE_DIR):
        c.run('mkdir %s' % newdir)
    with c.cd('%s/%s' % (_REMOTE_BASE_DIR, newdir)):
        c.run('tar -xzvf %s' % _REMOTE_TMP_TAR)
    with c.cd(_REMOTE_BASE_DIR):
        c.run('rm -f www')
        c.run('ln -s %s www' % newdir)
        # c.run('chown www-data:www-data www')
        # c.run('chown -R www-data:www-data %s' % newdir)
    
    # 重启 pyblog
    # c.run('supervisorctl stop pyblog')
    # c.run('supervisorctl start pyblog')
    # c.run('/etc/init.d/nginx reload')

@task
def deploy(c):
    build(c)
    transfer(c)