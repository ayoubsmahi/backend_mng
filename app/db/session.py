import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# This looks for a "DATABASE_URL" set by Render. 
# If it doesn't find one, it falls back to your local drone_db.
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+psycopg2://drone:dronepass@localhost:5432/drone_db"
)

# Fix for Render: Render sometimes gives a URL starting with 'postgres://'
# but SQLAlchemy requires 'postgresql://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
