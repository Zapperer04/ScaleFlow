import sys
import os

sys.path.append(os.path.abspath('.'))
try:
    from models import Base, engine
    # Drop all tables first
    Base.metadata.drop_all(engine)
    print("Dropped all tables in container database.")
    # Recreate all tables
    Base.metadata.create_all(engine)
    print("Recreated all tables in container database.")
except Exception as e:
    print(f"Error dropping/recreating tables: {e}")
