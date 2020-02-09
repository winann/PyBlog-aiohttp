#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Victor Song'

'''
Debug monitor
'''

import sys, subprocess, time, os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

def log(msg: str):
    print('[monitor] %s' % msg)

class MyFileSystemEventHandler(FileSystemEventHandler):
    def __init__(self, func):
        super().__init__()
        self.restart = func
    def on_any_event(self, event):
        if event.src_path.endswith('.py'):
            log('Python source file changed: %s' % event.src_path)
            self.restart()

command = ['echo', 'ok']
process = None

def kill_process():
    global process
    if process:
        log('Kill process [%s]...' % process.pid)
        process.kill()
        process.wait()
        log('Process ended with code %s.' % process.returncode)
        process = None

def start_process():
    global process, command
    log('Start process %s...' % ' '.join(command))
    process = subprocess.Popen(command, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)

def restart_process():
    kill_process()
    start_process()

def start_watch(path, callback):
    observer = Observer()
    observer.schedule(MyFileSystemEventHandler(restart_process), path, recursive=True)
    observer.start()
    log('Watching directory %s...' % path)
    start_process()
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv:
        print('Usage: ./pymonitor.py your-script.py')
        exit(0)
    if 'python3' != argv[0]:
        argv.insert(0, 'python3')
    log('starting monitor...')
    command = argv
    path = os.path.abspath('.')
    start_watch(path, None)