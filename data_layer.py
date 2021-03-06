import sqlite3
import uuid as uu
import socket
import os
import sys
from threading import Semaphore
import time
import datetime

import extra_functions as ef

query = False
status = {'main': [], 'watch': [], 'network': []}
status_sem = Semaphore()


def edit_status(key, value):
    global status
    with status_sem:
        status[key] = value


def set_query(value):
    global query
    query = value


__author__ = 'Roly'
semaphore = Semaphore()
login = os.path.expanduser('~')


class DataLayer:
    def __init__(self, database_url=login + '/.local/share/JF/database.db'):
        self.database_url = database_url
        self.database = sqlite3.connect(self.database_url, check_same_thread=False)
        # self.database.execute('PRAGMA read_uncommitted = FALSE ')
        self.cursor = self.database.cursor()
        # self.database.isolation_level = 'DEFERRED'

    def create_databases(self):
        cursor = self.database.cursor()
        cursor.execute(
            'CREATE TABLE Login (password VARCHAR)')
        cursor.execute(
            'CREATE TABLE File (_id INTEGER PRIMARY KEY AUTOINCREMENT,id INTEGER, name_ext VARCHAR , root VARCHAR, '
            'file_type VARCHAR, parent INTEGER REFERENCES File(id), generation  INTEGER, '
            'machine INTEGER REFERENCES Metadata(id), date_modified INTEGER)')
        cursor.execute('CREATE INDEX name_index ON  File (name_ext)')
        cursor.execute('CREATE INDEX id_index ON  File (id)')
        cursor.execute(
            'CREATE TABLE Metadata (id INTEGER PRIMARY KEY AUTOINCREMENT,uuid VARCHAR, '
            'pc_name VARCHAR, last_generation INTEGER, own INTEGER, my_generation INTEGER, device INTEGER,'
            ' size VARCHAR, date_modified VARCHAR)')
        cursor.execute(
            'CREATE TABLE Journal '
            '(id INTEGER PRIMARY KEY AUTOINCREMENT, actio VARCHAR, machine INTEGER REFERENCES Metadata(id))')
        self.database.commit()
        cursor.close()

    def close(self):
        self.database.close()

    def get_action_from_machine(self, machine):
        cursor = self.database.cursor()
        ret = cursor.execute('SELECT actio FROM Journal WHERE machine=?', (machine,))
        return ret

    def delete_actions_from_machine(self, machine):
        cursor = self.database.cursor()
        cursor.execute('DELETE FROM Journal WHERE machine=?', (machine,))
        self.database.commit()
        cursor.close()

    def add_action(self, action, generation):
        if generation:
            cursor = self.database.cursor()
            for x in cursor.execute('SELECT id FROM Metadata WHERE my_generation>=? AND OWN != 1', (int(generation),)):
                self.cursor.execute('INSERT INTO Journal VALUES (?,?,?)', (None, action, x[0]))
            self.database.commit()
            cursor.close()

    def get_last_generation(self, uuid):
        cursor = self.database.cursor()
        for value in cursor.execute('SELECT last_generation FROM Metadata WHERE uuid =?', (uuid,)):
            cursor.close()
            return value[0]

    def update_name(self, uuid, name):
        cursor = self.database.cursor()
        cursor.execute('UPDATE Metadata SET pc_name=? WHERE uuid=?', (name, uuid))
        try:
            self.database.commit()
        except sqlite3.OperationalError:
            pass
        cursor.close()

    def get_all_databases_elements(self, table):
        cursor = self.database.cursor()
        execute = 'SELECT * FROM ' + table
        cursor.execute(execute)
        return cursor

    def get_max_generation(self, machine=1):
        cursor = self.database.cursor()
        for value in cursor.execute('SELECT max(generation) FROM File WHERE machine=?', (machine,)):
            cursor.close()
            return value[0]

    def insert_password(self, password):
        with semaphore:
            cursor = self.database.cursor()
            p = self.get_password()
            if p:
                cursor.execute('DELETE FROM Login WHERE password =?', (p,))
            cursor.execute('INSERT INTO Login VALUES (?)', (password,))
            self.database.commit()
            cursor.close()

    def get_password(self):
        cursor = self.database.cursor()
        for value in cursor.execute('SELECT password FROM Login'):
            cursor.close()
            return value[0]

    def get_files(self, generation, peer):
        cursor = self.database.cursor()
        return cursor.execute('SELECT * FROM File WHERE generation>=? AND machine=? ORDER BY id ASC',
                              (int(generation), int(peer)))

    def insert_peer(self, uuid=None, pc_name=None, memory=0, size=0, date=0):
        cursor = self.database.cursor()
        if not uuid and not pc_name:
            cursor.execute('INSERT INTO Metadata VALUES (?,?,?,?,?,?,?,?,?)',
                           (None, str(uu.uuid4()), socket.gethostname(), -1, 1, -1, memory, size, date))
        else:
            try:
                cursor.execute('INSERT INTO Metadata VALUES (?,?,?,?,?,?,?,?)',
                               (None, uuid.decode(), pc_name, -1, 0, -1, memory, size, date))
            except AttributeError:
                cursor.execute('INSERT INTO Metadata VALUES (?,?,?,?,?,?,?,?,?)',
                               (None, str(uuid), pc_name, -1, 0, -1, memory, size, date))
        self.database.commit()
        cursor.close()

    def edit_generation(self, uuid, generation):
        cursor = self.database.cursor()
        # execute = 'UPDATE Metadata SET last_generation = '' + str(generation) + ' WHERE uuid = ' + str(uuid)
        generation = int(generation) + 1
        cursor.execute('UPDATE Metadata SET last_generation=?   WHERE uuid = ?', (generation, str(uuid)))
        self.database.commit()
        cursor.close()

    def edit_my_generation(self, uuid, generation):
        generation = int(generation)
        cursor = self.database.cursor()
        with semaphore:
            cursor.execute('UPDATE Metadata SET my_generation=? WHERE uuid=?', (generation, uuid))
            try:
                self.database.commit()
            except sqlite3.OperationalError:
                pass
        cursor.close()

    def get_uuid_from_peer(self, owner=1):
        cursor = self.database.cursor()
        for value in self.cursor.execute('SELECT id FROM Metadata WHERE own =?', (owner,)):
            cursor.close()
            return value[0]

    def get_id_from_peer(self, owner=1):
        cursor = self.database.cursor()
        for value in cursor.execute('SELECT uuid FROM Metadata WHERE own =?', (owner,)):
            cursor.close()
            return value[0]

    def insert_file(self, id, file_name, parent, file_type, root, generation, peer, date=0):
        self.cursor.execute('INSERT INTO File VALUES (?,?,?,?,?,?,?,?,?)',
                            (None, id, file_name, root, file_type, parent, generation, peer, date))

    def insert_data(self, id, file_name, file_type, parent, generation, peer=None, first=False, real_path=None,
                    date=None):
        if not first and real_path:
            try:
                _date = ef.get_date(real_path)
            except FileNotFoundError:
                _date = 0
            if date:
                _date = date
            paren = self.get_parent(parent, real_path, peer)
            self.insert_file(id, file_name, paren, file_type, '', generation, peer, _date)
        elif not real_path and not first:
            if date:
                self.insert_file(id, file_name, parent, file_type, '', generation, peer, date)
            else:
                self.insert_file(id, file_name, parent, file_type, '', generation, peer)
        else:
            if date:
                self.insert_file(id, file_name, -1, file_type, parent, generation, peer, date)
            else:
                self.insert_file(id, file_name, -1, file_type, parent, generation, peer)

    def delete_data(self, name, real_path, machine):
        cursor2 = self.database.cursor()
        # peer = self.get_uuid_from_peer()
        parent = self.get_parent(name, real_path, machine)
        gen = None
        if machine == 1:
            cursor = self.database.cursor()

            for x in cursor.execute('SELECT generation FROM File WHERE name_ext=? AND parent=? AND machine = ?',
                                    (name, parent, machine)):
                gen = x
                break
            cursor.close()

        cursor2.execute('DELETE FROM File WHERE name_ext=? AND parent=? AND machine = ?', (name, parent, machine))
        self.database.commit()
        cursor2.close()
        if gen:
            return gen[0]
        return None

    def get_parent(self, path, real_path, peer):
        cursor = self.database.cursor()
        tmp = []
        for value in cursor.execute('SELECT * FROM File WHERE id=? AND machine=?', (1, peer)):
            tmp.append(value)
        if len(tmp) == 1:
            walk = real_path.split(tmp[0][3])
            if len(walk) == 1 or not walk[1]:
                return tmp[0][1]
            if os.sep in walk[1]:
                walk = walk[1].split(os.sep)
            if sys.platform == 'linux':
                walk.pop(0)
            tmp = tmp[0]
            while len(walk):
                folder = walk[0]
                walk.pop(0)
                for value in cursor.execute('SELECT * FROM File WHERE name_ext=? AND parent=?',
                                            (folder, tmp[1])):
                    tmp = value
            cursor.close()
            return tmp[1]
            # real_paths = [self.get_address(x[0], peer) for x in tmp]
            # for x in range(len(real_paths) - 1, -1, -1):
            # if real_paths[x] == real_path:
            # return tmp[x][0]
            # raise Exception('Error')

        else:
            raise Exception('Error in database')

    def edit_date(self, machine):
        self.cursor.execute('UPDATE Metadata SET date_modified=? WHERE id=? AND device=1',
                            (datetime.datetime.now().timestamp(), machine))
        self.database.commit()

    def dynamic_insert_data(self, path, dirs, files, session_count, total_files, count, real_path, peer, generation=0):
        global query
        parent = self.get_parent(path, real_path, peer)
        for dir in dirs:
            count += 1
            try:
                date = ef.get_date(real_path + os.sep + dir)
            except FileNotFoundError:
                date = 0
            self.insert_file(total_files, dir, parent=parent, file_type='Folder', generation=0, root='',
                             peer=peer,
                             date=date)
            if count > 100000:
                self.database.commit()
                count = 0
            if query:
                self.database.commit()
                while query:
                    time.sleep(0.5)
            total_files += 1
        for file in files:
            count += 1
            try:
                date = ef.get_date(real_path + os.sep + file)
            except FileNotFoundError:
                date = 0
            _type = file.split('.')
            self.insert_file(file_name=file, file_type='' + _type[len(_type) - 1], parent=parent, generation=0,
                             root='', peer=peer, id=total_files, date=date)
            if count > 100000:
                self.database.commit()
                count = 0
            if query:
                self.database.commit()
                while query:
                    time.sleep(0.5)
            total_files += 1
        return session_count, total_files, count

    def get_element(self, item, peer):
        for x in self.cursor.execute('SELECT * FROM File WHERE id=? AND machine=?', (item, peer)):
            return x

    def get_address(self, item, peer):
        item = self.get_element(item, peer)
        address = ''
        while 1:
            if item[5] == -1:
                break
            address = str(item[2]) + os.sep + address
            tm = item[5], item[7]
            item = self.get_element(item[5], item[7])
            if not item:
                print(str(tm))
            if item[3]:
                address = str(item[3]) + os.sep + address
        return address[:len(address) - 1]

    def update_data(self, data, peer):
        parent = self.get_parent(data[len(data) - 2], data[len(data) - 1], peer)
        new_parent = self.get_parent(data[2], data[5], peer)
        cursor = self.database.cursor()
        gen = None
        if peer == 1:
            for x in cursor.execute('SELECT generation FROM File WHERE name_ext=? AND parent=? AND machine = ?',
                                    (data[len(data) - 2], parent, peer)):
                gen = x
                break
            cursor.close()
        self.cursor.execute('UPDATE File SET name_ext=?, parent=? WHERE name_ext=? AND parent=? AND machine=?',
                            (data[0], new_parent, data[len(data) - 2], parent, peer))
        self.database.commit()
        if gen:
            return gen[0]
        return None

    def get_devices(self):
        cursor = self.database.cursor()
        res = []
        for x in cursor.execute('SELECT id, pc_name, device, size FROM Metadata'):
            res.append(x)
        cursor.close()
        return res

    def get_device(self, name):
        cursor = self.database.cursor()
        res = []
        for x in cursor.execute('SELECT id, pc_name, device, size FROM Metadata WHERE pc_name=?', (name,)):
            res.append(x)
        cursor.close()
        return res

    def get_memory_devices(self):
        cursor = self.database.cursor()
        res = []
        for x in cursor.execute('SELECT uuid, date_modified, pc_name, size FROM Metadata WHERE device=1'):
            res.append((x[0], ef.convert_dates(datetime.datetime.now().timestamp(), float(x[1])), x[2], x[3]))
        cursor.close()
        return res

    def find_data(self, word_list, machine=1):
        cursor = self.database.cursor()
        query = 'SELECT * FROM File WHERE '
        cont = 0
        l = len(word_list)
        while cont < l:
            if cont == 0:
                query += 'name_ext LIKE ?'
            else:
                query += ' AND name_ext LIKE ?'
            cont += 1
        query += ' AND machine=' + str(machine) + ' ORDER BY date_modified DESC'
        word_list = ['%' + x + '%' for x in word_list]
        return cursor.execute(query, word_list)

    def get_cursor(self):
        return self.database.cursor()

    def get_peer_from_uuid(self, name):
        cursor = self.database.cursor()
        for value in cursor.execute('SELECT pc_name FROM Metadata WHERE id == ?', (name,)):
            cursor.close()
            return value[0]
        cursor.close()

    def get_peer_from_id(self, id):
        cursor = self.database.cursor()
        for value in cursor.execute('SELECT uuid FROM Metadata WHERE id=?', (id,)):
            cursor.close()
            return value[0]

    def get_id_from_uuid(self, uuid):
        cursor = self.database.cursor()
        for value in cursor.execute('SELECT id FROM Metadata WHERE uuid=?', (uuid,)):
            cursor.close()
            return value[0]

    def get_max_id(self, machine=1):
        cursor = self.database.cursor()
        for value in cursor.execute('SELECT max(id) FROM File WHERE machine=?', (machine,)):
            number = int(value[0])
            cursor.close()
            return number

    def get_id_from_device(self, device):
        cursor = self.database.cursor()
        _id = None
        for x in cursor.execute('SELECT id FROM Metadata WHERE uuid=?', (device,)):
            _id = x[0]
            break
        cursor.close()
        return _id

    def delete_drive(self, device):
        cursor = self.database.cursor()
        cursor.execute('DELETE FROM File WHERE machine = ?', (device,))
        cursor.execute('DELETE FROM Metadata WHERE id = ?', (device,))
        self.database.commit()
        cursor.close()

    def delete_files_from_drive(self, _id):
        cursor = self.database.cursor()
        cursor.execute('DELETE FROM File WHERE machine = ?', (_id,))
        self.database.commit()
        cursor.close()


if __name__ == '__main__':
    data = DataLayer('database.db')
    # data.create_databases()
    print(data.cursor.execute('DELETE FROM File WHERE id=2'))
    data.database.commit()
    data.close()
