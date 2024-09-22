from server.database import Base, engine
from server.models import Chapter, Textbook, Section, Narrative, UserProfile

# Drop all tables
Base.metadata.drop_all(bind=engine)

# Recreate all tables
Base.metadata.create_all(bind=engine)

print("All tables dropped and recreated successfully!")
