from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from server.database import Base

class Textbook(Base):
    __tablename__ = 'textbooks'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    
    # Relationship with chapters
    chapters = relationship("Chapter", back_populates="textbook")


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(Text)

    # Link to the textbook this chapter belongs to
    textbook_id = Column(Integer, ForeignKey('textbooks.id'))
    textbook = relationship("Textbook", back_populates="chapters")
