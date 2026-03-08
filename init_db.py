import sys
sys.path.append(".")
from core.database.session import engine, Base

def init_db():
    print("Initializing SAHARYN AI database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("SUCCESS: Tables materialized.")
    except Exception as e:
        print(f"FAILURE: Could not create tables: {e}")

if __name__ == "__main__":
    init_db()
