from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, create_engine, ForeignKey
from sqlalchemy.orm import relationship, sessionmaker, backref
import time


engine = None
Base = declarative_base()


class File(Base):
    __tablename__ = 'File'

    _id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, index=True)
    root = Column(String)
    file_type = Column(String)
    parent_id = Column(Integer, ForeignKey('File._id'))
    parent = relationship('File', backref=backref('child_folder', remote_side=[_id]))

    def __init__(self, name, file_type, parent, root=None):
        self.name = name
        self.parent_id = parent
        self.file_type = file_type
        self.root = root

    def __repr__(self):
        return "<File: \n Name=’%s’,\n Type=’%s’ \n Parent: '%s'>" % (
            self.name, self.file_type, self.parent_id)


def create_database():
    engine = create_engine('sqlite:///database.db')
    Base.metadata.create_all(engine)
    return engine


def connect_database():
    engine = create_engine('sqlite:///database.db')
    return  engine


def get_database_all_elements(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    var = session.query(File).all()
    session.close()
    return var


def get_engine():
    return engine if engine else connect_database()


def insert_data(engine, file_name, file_type, paren, first=False):
    Session = sessionmaker(bind=engine)
    session = Session()
    if not first:
        parent = None
        for x in session.query(File).filter_by(name=paren):
            parent = x
        tmp = File(name=file_name, file_type=file_type, parent=parent._id)
    else:
        tmp = File(name=file_name, file_type=file_type, parent=-1, root=paren)
    session.add(tmp)
    session.commit()
    session.close()


def delete_data(engine, file_name):
    session = get_session(engine)
    session.query(File).filter_by(name=file_name).delete()
    session.commit()
    session.close()


def get_session(engine):
    Session = sessionmaker(bind=engine)
    return Session()


def do_commit(session):
    time1 = time.time()
    session.commit()
    return time.time() - time1


def dynamic_insert_data(session, path, dirs, files, f, session_count, total_files, count, list_file_tmp):
    parent = list_file_tmp[path]
    for x in dirs:
        tmp = File(name=x, file_type='Folder', parent=parent)
        list_file_tmp[x] = total_files
        session.add(tmp)
        total_files += 1
        session_count = len(session.new)
        if session_count == count:
            a = do_commit(session)
            f.write('Elements: ' + str(session_count) + ' time: ' + str(a) + ' prop: ' + str(a / count) + ' prop2: '
                    + str(count / a) + '\n')
            count += 1
            session_count = 0
    for x in files:
        _type = x.split('.')
        tmp = File(name=x, file_type='File: ' + _type[len(_type) - 1], parent=parent)
        total_files += 1
        session.add(tmp)
        session_count = len(session.new)
        if session_count == count:
            a = do_commit(session)
            f.write('Elements: ' + str(session_count) + ' time: ' + str(a) + ' prop: ' + str(a / count) + ' prop2: '
                    + str(count / a) + '\n')
            count += 1
            session_count = 0
    return session, session_count, total_files, count, list_file_tmp


def get_address(engine, item):
    address = ''
    Session = sessionmaker(bind=engine)
    session = Session()
    while 1:
        if item.parent_id == -1:
            break
        address = str(item.name) + '/' + address
        item = session.query(File).filter_by(_id=item.parent_id).first()
    if item.root:
        address = str(item.root) + '/' + address
    return address[:len(address) - 1]


def find_data(engine, words_list):
    Session = sessionmaker(bind=engine)
    session = Session()
    a = session.query(File).filter(File.name.like('%' + words_list[0] + '%'))
    return a
