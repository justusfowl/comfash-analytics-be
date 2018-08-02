from sqlalchemy import create_engine, Column, Table, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (
    Integer, SmallInteger, String, Date, DateTime, Float, Boolean, Text, LargeBinary)

from scrapy.utils.project import get_project_settings

DeclarativeBase = declarative_base()

def db_connect():
    """
    Performs database connection using database settings from settings.py.
    Returns sqlalchemy engine instance
    """
    return create_engine(get_project_settings().get("CONNECTION_STRING"))

def create_table(engine):
    DeclarativeBase.metadata.create_all(engine)

class Inspiration_Image(DeclarativeBase):
    __tablename__ = 'tblinspirations'
    urlHash = Column(String(600), primary_key=True)
    url = Column(String(5000))
    classifyPath = Column(String(5000))
    sourcePage = Column(String(5000))
    isRejected = Column(SmallInteger())

    def __repr__(self):
        return "<inspiration_image(urlHash='%s', url='%s')>" % (
                                self.urlHash, self.url)

