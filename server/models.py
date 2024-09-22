from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from server.database import Base

class Textbook(Base):
    __tablename__ = 'textbooks'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)

    chapters = relationship("Chapter", back_populates="textbook")

class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(Text)
    textbook_id = Column(Integer, ForeignKey("textbooks.id"))

    textbook = relationship("Textbook", back_populates="chapters")
    sections = relationship("Section", back_populates="chapter")
    narrative = relationship("Narrative", back_populates="chapter", uselist=False)

class Section(Base):
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(Text)
    chapter_id = Column(Integer, ForeignKey("chapters.id"))

    chapter = relationship("Chapter", back_populates="sections")

class Narrative(Base):
    __tablename__ = "narratives"

    id = Column(Integer, primary_key=True, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), unique=True)
    content = Column(Text)

    chapter = relationship("Chapter", back_populates="narrative")

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)
    learning_profile = Column(Text)  # Changed from JSON to Text
