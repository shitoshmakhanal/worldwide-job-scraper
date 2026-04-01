from sqlalchemy import (create_engine, text, Column, String,
                        Integer, Float, DateTime, Text, Boolean)
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.sql import func
from dotenv import load_dotenv
from loguru import logger
import os

load_dotenv()

DATABASE_URL = (
    f"postgresql+psycopg2://"
    f"{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}"
    f"/{os.getenv('DB_NAME')}"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass

class Job(Base):
    __tablename__ = "jobs"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    title         = Column(String(500), nullable=False)
    company       = Column(String(500))
    location      = Column(String(500))
    country       = Column(String(100))
    region        = Column(String(100))
    salary_raw    = Column(String(200))
    salary_min    = Column(Float)
    salary_max    = Column(Float)
    salary_currency = Column(String(10))
    job_type      = Column(String(100))
    job_level     = Column(String(100))
    category      = Column(String(300))
    skills        = Column(Text)
    description   = Column(Text)
    deadline      = Column(String(100))
    posted_date   = Column(String(100))
    job_url       = Column(String(1000))
    source        = Column(String(100))
    scraped_at    = Column(DateTime, server_default=func.now())
    is_active     = Column(Boolean, default=True)

class ScraperLog(Base):
    __tablename__ = "scraper_logs"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    source      = Column(String(100))
    jobs_found  = Column(Integer)
    jobs_new    = Column(Integer)
    status      = Column(String(50))
    error       = Column(Text)
    ran_at      = Column(DateTime, server_default=func.now())

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(engine)
    logger.success("Database tables created successfully")

def test_connection():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.success("Database connected successfully")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()
    init_db()