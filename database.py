from sqlalchemy import UniqueConstraint, create_engine, Column, Integer, String, MetaData, Table, DateTime, func
from databases import Database
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from env_vars_helpers import DATABASE_URL


database = Database(DATABASE_URL)
metadata = MetaData()

Base = declarative_base()

# Define the SEC data table
class SECData(Base):
    __tablename__ = 'sec_data'

    id = Column(Integer, primary_key=True, autoincrement=True)
    cik_str = Column(Integer)
    ticker = Column(String)
    title = Column(String)


class DocumentMetadata(Base):
    __tablename__ = 'document_metadata'

    id = Column(Integer, primary_key=True, autoincrement=True)
    cik_str = Column(Integer)
    accession_number = Column(String)
    primary_document = Column(String)
    document_type = Column(String)
    timestamp = Column(DateTime)

engine = create_engine(DATABASE_URL)

async def init_db():
    Base.metadata.create_all(bind=engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()