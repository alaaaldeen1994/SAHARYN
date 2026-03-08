import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Build URL from individual components if DATABASE_URL is not set
DB_USER = os.getenv("DB_USER", "saharyn_admin")
DB_PASS = os.getenv("DB_PASSWORD", "secure_pass")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "saharyn_prod")

DEFAULT_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_URL)

# Fallback to SQLite if Postgres fails
if "postgresql" in DATABASE_URL:
    try:
        engine = create_engine(DATABASE_URL, connect_args={'connect_timeout': 2})
        engine.connect()
    except Exception:
        DATABASE_URL = "sqlite:///./saharyn_dev.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={'connect_timeout': 5} if "sqlite" not in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
