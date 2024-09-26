import os
from server.database import Base, engine, SQLALCHEMY_DATABASE_URL
from server.models import Chapter, Textbook, Section, Narrative, UserProfile

def rebuild_database():
    # Extract the database file path from the URL
    db_path = SQLALCHEMY_DATABASE_URL.replace('sqlite:///', '').split('?')[0]

    # Delete the existing database file if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Existing database {db_path} deleted.")

    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully!")

    # Set appropriate permissions for the new database file
    os.chmod(db_path, 0o666)
    print(f"Permissions set for {db_path}")

if __name__ == "__main__":
    rebuild_database()
