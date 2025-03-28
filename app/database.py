# app/database.py
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os

# Create database engine
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./story_app.db")
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for declarative models
Base = declarative_base()


# Models
class StoryCategory(Base):
    __tablename__ = "story_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)  # Internal name (key)
    display_name = Column(String)  # User-friendly name
    description = Column(Text)
    story_config = Column(Text)  # Store entire config as JSON


class LessonTopic(Base):
    __tablename__ = "lesson_topics"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, index=True)
    subtopic = Column(String, index=True)
    question = Column(Text)
    correct_answer = Column(Text)
    wrong_answer1 = Column(Text)
    wrong_answer2 = Column(Text)
    explanation = Column(Text)
    difficulty_level = Column(String, index=True)  # Changed from Integer to String


class StorySession(Base):
    __tablename__ = "story_sessions"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("story_categories.id"))
    topic_id = Column(Integer, ForeignKey("lesson_topics.id"))
    current_chapter = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    total_questions = Column(Integer, default=0)

    # Relationships
    category = relationship("StoryCategory")
    topic = relationship("LessonTopic")


# Database initialization function
def init_db():
    Base.metadata.create_all(bind=engine)


# Dependency for getting database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
