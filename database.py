from sqlalchemy import UniqueConstraint, create_engine, Column, Integer, String, MetaData, Table, DateTime, func
from databases import Database
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session

from env_vars_helpers import DATABASE_URL


database = Database(DATABASE_URL)
metadata = MetaData()

# Define the SEC data table
sec_table = Table(
    'sec_data',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('cik_str', Integer),
    Column('ticker', String),
    Column('title', String, unique=True),  # Assuming 'title' is the column for company name
    UniqueConstraint('title', name='uq_sec_data_title'),
)

# Define the parent document metadata table
document_metadata_table = Table(
    'document_metadata',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('cik_str', Integer),
    Column('accession_number',Integer),
    Column('primary_document',String),
    Column('document_type', String),
    Column('timestamp', DateTime, default=func.now()), #edit this to be now()
)


engine = create_engine(DATABASE_URL)
metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()