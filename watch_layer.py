import os
import time
from queue import Empty

from data_layer import semaphore as sem
from watchdog import observers
from watchdog.events import FileSystemEventHandler
import data_layer
import extra_functions

query = False


def set_query(value):
    global query
    query = value


class MyFileSystemWatcher(FileSystemEventHandler):
    def __init__(self, cache):
        super(FileSystemEventHandler).__init__()
        self.cache = cache

    def on_created(self, event):
        if hasattr(event, 'dest_path'):
            path = extra_functions.split_paths(event.dest_path)
        else:
            path = extra_functions.split_paths(event.src_path)
        if event.is_directory:
            self.cache.put(('created', path[len(path) - 1], 'Folder', path[len(path) - 2], None,
                            None, os.path.join(*path[:len(path) - 1])))
        else:
            _type = path[len(path) - 1].split('.')
            if len(_type) > 1:
                _type = _type[len(_type) - 1]
            else:
                _type = ''
            self.cache.put(('created', path[len(path) - 1], _type, path[len(path) - 2],
                            None, None, os.path.join(*path[:len(path) - 1])))

    def on_deleted(self, event):
        if event.src_path:
            path = extra_functions.split_paths(event.src_path)
            self.cache.put(('deleted', path[len(path) - 1], os.path.join(*path[:len(path) - 1])))

    def on_moved(self, event):
        path = extra_functions.split_paths(event.dest_path)
        if event.src_path:
            old_path = extra_functions.split_paths(event.src_path)
            if event.is_directory:
                self.cache.put(('updated', path[len(path) - 1], 'Folder', path[len(path) - 2], None,
                                None, os.path.join(*path[:len(path) - 1]), old_path[len(old_path) - 1],
                                os.path.join(*old_path[:len(old_path) - 1])))
            else:
                _type = path[len(path) - 1].split('.')
                if len(_type) > 1 and _type[-1]:
                    _type = _type[-1]
                else:
                    _type = ''
                self.cache.put(('updated', path[len(path) - 1], _type, path[len(path) - 2], None,
                                None, os.path.join(*path[:len(path) - 1]), old_path[len(old_path) - 1],
                                os.path.join(*old_path[:len(old_path) - 1])))
        else:
            self.cache.put(('created', path[len(path) - 1], 'Folder', path[len(path) - 2], None,
                            None, os.path.join(*path[:len(path) - 1]), None,
                            None))

    def dispatch(self, event):
        if hasattr(event, 'src_path'):
            home = os.path.expanduser('~')
            if event.src_path == home.encode() + b'/.local/share/JF/database.db-journal':
                return
        if event.event_type == 'created':
            self.on_created(event)
        elif event.event_type == 'deleted':
            self.on_deleted(event)
        elif event.event_type == 'moved':
            self.on_moved(event)
        elif event.event_type == 'modified':
            pass
        else:
            print(event.event_type)


def create_watcher(paths, cache):
    watchers = []
    obj = MyFileSystemWatcher(cache)
    for path in paths:
        watchers.append((observers.Observer(), path))
    for x in range(0, len(watchers)):
        try:
            watchers[x][0].schedule(obj, watchers[x][1], recursive=True)
            watchers[x][0].start()
        except Exception as e:
            print(e.args)
    return watchers


def make_watch(cache, machine=1):
    global query
    data_obj = data_layer.DataLayer()
    while 1:
        time.sleep(2)
        if not cache.empty():
            with sem:
                number = data_obj.get_max_id(machine)
                generation = data_obj.get_max_generation() + 1
                while 1:
                    try:
                        if not query:
                            x = cache.get(timeout=1)
                            if not data_obj:
                                data_obj = data_layer.DataLayer()
                                data_obj.cursor = data_obj.database.cursor()
                            number += 1
                            data_layer.edit_status('watch', [])
                            data_layer.edit_status('watch', [x[1]])
                            if x[0] == 'created':
                                data_obj.insert_data(number, x[1], x[2], x[3], generation, machine,
                                                     real_path=x[6])
                            elif x[0] == 'deleted':
                                g = data_obj.delete_data(x[1], x[2], machine)
                                data_obj.add_action(str(x), g)
                            else:
                                g = data_obj.update_data(x[1:], machine)
                                data_obj.add_action(str(x), g)
                            if query:
                                data_obj.database.commit()
                                data_obj.close()
                                data_obj = None
                                while query:
                                    time.sleep(0.5)
                    except Empty:
                        break
                    except Exception as e:
                        raise e
                    while query:
                        time.sleep(0.5)
                if data_obj:
                    data_obj.edit_date(machine)
                    data_obj.database.commit()
                data_layer.edit_status('watch', [])


def add_multi_platform_watch(paths, cache):
    create_watcher(paths, cache)
    make_watch(cache)
