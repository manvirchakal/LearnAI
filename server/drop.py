from server.database import Base, engine
from server.models import Chapter, Textbook

# Drop the 'chapters' and 'textbooks' tables
Base.metadata.drop_all(bind=engine, tables=[Chapter.__table__, Textbook.__table__])

# Recreate the 'chapters' and 'textbooks' tables
Base.metadata.create_all(bind=engine)

print("Tables dropped and recreated successfully!")
