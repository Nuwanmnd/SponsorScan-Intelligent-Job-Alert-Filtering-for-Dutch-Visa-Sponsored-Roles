import os
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Date, Boolean, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database Setup
DB_FILE = "jobs.db"
DATABASE_URL = f"sqlite:///{DB_FILE}"

Base = declarative_base()

class Sponsor(Base):
    __tablename__ = 'sponsors'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)      # Original name from IND
    clean_name = Column(String, unique=True, index=True) # Normalized for matching
    kvk = Column(String, nullable=True)    # KvK number if available
    
    def __repr__(self):
        return f"<Sponsor(name='{self.name}')>"

class Job(Base):
    __tablename__ = 'jobs'
    
    id = Column(Integer, primary_key=True, index=True)
    date_found = Column(Date, default=datetime.date.today, index=True) # Requested to be prominent
    title = Column(String, index=True)
    company = Column(String, index=True)
    link = Column(String, nullable=True)
    status = Column(String, default="pending", index=True) # pending, applied, rejected, approved
    email_id = Column(String, nullable=True) # To trace back to source email/prevent dupes via email ID too?
    
    # Composite unique constraint to prevent duplicates of (Company + Title)
    # We might want to allow same job if it's re-posted months later? 
    # For now, let's keep it simple and just rely on the main.py deduplication logic 
    # or add a constraint here.
    # __table_args__ = (UniqueConstraint('company', 'title', name='_company_title_uc'),)

    def __repr__(self):
        return f"<Job(title='{self.title}', company='{self.company}', status='{self.status}')>"

# Init Engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Creates the database tables."""
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    print(f"Initializing database: {DB_FILE}")
    init_db()
    print("Database initialized successfully.")
