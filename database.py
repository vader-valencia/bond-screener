import os
from dotenv import load_dotenv
from sqlalchemy import UniqueConstraint, create_engine, Column, Integer, String, MetaData, Table
from databases import Database
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session

load_dotenv()

# Database Configuration
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PWD = os.getenv("POSTGRES_PWD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PWD}@localhost:5432/{POSTGRES_DB}"
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

engine = create_engine(DATABASE_URL)
metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()