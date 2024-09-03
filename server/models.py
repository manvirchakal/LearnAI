from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from server.database import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    
    textbooks = relationship("Textbook", back_populates="owner")

class Textbook(Base):
    __tablename__ = 'textbooks'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    
    chapters = relationship("Chapter", back_populates="textbook")
    
    owner = relationship("User", back_populates="textbooks")

class Chapter(Base):
    __tablename__ = 'chapters'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(Text)  # This column is defined here
    textbook_id = Column(Integer, ForeignKey('textbooks.id'))
    
    sections = relationship("Section", back_populates="chapter")
    
    textbook = relationship("Textbook", back_populates="chapters")

class Section(Base):
    __tablename__ = 'sections'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(Text)
    chapter_id = Column(Integer, ForeignKey('chapters.id'))
    
    chapter = relationship("Chapter", back_populates="sections")
