# app/init_data.py
import yaml
import pandas as pd
import json
from app.database import SessionLocal, init_db
from app.database import StoryCategory, LessonTopic


def load_story_data():
    """Load and process story categories from YAML file."""
    with open("app/data/stories.yaml", "r") as f:
        data = yaml.safe_load(f)
    return data["story_categories"]


def load_lesson_data():
    """Load and process lesson data from CSV file."""
    return pd.read_csv("app/data/lessons.csv")


def init_story_categories(db, story_data):
    """Initialize story categories in the database."""
    for key, category in story_data.items():
        db_category = StoryCategory(
            name=key,
            description=category["description"],
            tone=category["tone"],
            narrative_elements=json.dumps(category["narrative_elements"]),
            story_rules=json.dumps(category["story_rules"]),
            vocabulary_level=category["vocabulary_level"],
        )
        db.add(db_category)
    db.commit()


def init_lesson_topics(db, lesson_data):
    """Initialize lesson topics in the database."""
    for _, row in lesson_data.iterrows():
        db_topic = LessonTopic(
            topic=row["topic"],
            subtopic=row["subtopic"],
            question=row["question"],
            correct_answer=row["correct_answer"],
            wrong_answer1=row["wrong_answer1"],
            wrong_answer2=row["wrong_answer2"],
            explanation=row["explanation"],
            difficulty_level=row["difficulty_level"],
        )
        db.add(db_topic)
    db.commit()


def main():
    """Main initialization function."""
    # Initialize database schema
    init_db()

    # Get database session
    db = SessionLocal()

    try:
        # Load data from files
        story_data = load_story_data()
        lesson_data = load_lesson_data()

        # Initialize database with data
        init_story_categories(db, story_data)
        init_lesson_topics(db, lesson_data)

        print("Database initialized successfully!")

    except Exception as e:
        print(f"Error initializing database: {e}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
