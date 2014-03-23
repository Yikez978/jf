from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, create_engine, ForeignKey
from sqlalchemy.orm import relationship, sessionmaker, backref


engine = None
Base = declarative_base()


class File(Base):
    __tablename__ = 'File'

    _id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
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



