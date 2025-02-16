# app/init_data.py
import yaml
import pandas as pd
import json
from app.database import SessionLocal, init_db
from app.database import StoryCategory, LessonTopic
import random


def load_story_data():
    """Load and process story categories from YAML file."""
    with open("app/data/stories.yaml", "r") as f:
        data = yaml.safe_load(f)
    return data["story_categories"]


def load_lesson_data():
    """Load and process lesson data from CSV file."""
    return pd.read_csv("app/data/lessons.csv")


def sample_question(topic: str, exclude_questions: list = None) -> dict:
    """Sample a random question from the specified topic, excluding any previously used questions.

    Args:
        topic: The topic to sample from
        exclude_questions: List of questions to exclude from sampling

    Returns:
        dict: Question data including question, answers, and explanation
    """
    df = load_lesson_data()
    topic_questions = df[df["topic"] == topic]

    if exclude_questions:
        topic_questions = topic_questions[
            ~topic_questions["question"].isin(exclude_questions)
        ]

    if len(topic_questions) == 0:
        raise ValueError(f"No more available questions for topic: {topic}")

    sampled = topic_questions.sample(n=1).iloc[0]

    # Create list of all answers and randomize their order
    all_answers = [
        {"text": sampled["correct_answer"], "is_correct": True},
        {"text": sampled["wrong_answer1"], "is_correct": False},
        {"text": sampled["wrong_answer2"], "is_correct": False},
    ]
    randomized_answers = random.sample(all_answers, k=len(all_answers))

    return {
        "question": sampled["question"],
        "answers": randomized_answers,
        "explanation": sampled["explanation"],
        "topic": sampled["topic"],
        "subtopic": sampled["subtopic"],
    }


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
