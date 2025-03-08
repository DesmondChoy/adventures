# app/init_data.py
import yaml
import pandas as pd
import json
import random
import logging
from app.database import SessionLocal, init_db
from app.database import StoryCategory, LessonTopic

logger = logging.getLogger("story_app")


def load_story_data():
    """Load and process story categories from individual YAML files."""
    try:
        from app.data.story_loader import StoryLoader

        loader = StoryLoader()
        data = loader.load_all_stories()
        categories = data.get("story_categories", {})
        logger.info(
            "Loaded story data",
            extra={
                "categories": list(categories.keys()),
                "elements_per_category": {
                    cat: list(details.keys()) for cat, details in categories.items()
                },
            },
        )
        return categories
    except Exception as e:
        logger.error("Failed to load story data", extra={"error": str(e)})
        return {}  # Provide empty default value


def load_lesson_data():
    """Load and process lesson data from CSV files in the lessons directory."""
    from app.data.lesson_loader import LessonLoader

    loader = LessonLoader()
    return loader.load_all_lessons()


def sample_question(
    topic: str,
    exclude_questions: list = None,
    difficulty: str = "Reasonably Challenging",
) -> dict:
    """Sample a random question from the specified topic and difficulty, with fallback.

    Args:
        topic: The topic to sample from
        exclude_questions: List of questions to exclude from sampling
        difficulty: Difficulty level ("Reasonably Challenging" or "Very Challenging"), defaults to "Reasonably Challenging"

    Returns:
        dict: Question data including question, answers, and explanation
    """
    # Load data using LessonLoader
    from app.data.lesson_loader import LessonLoader

    loader = LessonLoader()

    # Filter by topic and difficulty if specified
    if difficulty:
        topic_questions = loader.get_lessons_by_topic_and_difficulty(topic, difficulty)

        # Fallback if fewer than 3 questions available
        if len(topic_questions) < 3:
            logger.warning(
                f"Insufficient questions for topic '{topic}' with difficulty '{difficulty}'. "
                f"Falling back to all difficulties."
            )
            topic_questions = loader.get_lessons_by_topic(topic)
    else:
        topic_questions = loader.get_lessons_by_topic(topic)

    # Exclude previously used questions
    if exclude_questions:
        topic_questions = topic_questions[
            ~topic_questions["question"].isin(exclude_questions)
        ]

    if len(topic_questions) == 0:
        raise ValueError(f"No more available questions for topic: {topic}")

    # Sample a random question
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
        "difficulty": sampled["difficulty"],  # Include difficulty in the returned data
    }


def init_story_categories(db, story_data):
    """Initialize story categories in the database."""
    try:
        print("Story data:", story_data)  # Debug print
        for key, category in story_data.items():
            print(f"Processing category: {key}")  # Debug print
            # Create a complete story configuration object
            story_config = {
                "narrative_elements": category["narrative_elements"],
                "sensory_details": category["sensory_details"],
                "themes": category["narrative_elements"]["themes"],
                "moral_teachings": category["narrative_elements"]["moral_teachings"],
                "plot_twists": category["narrative_elements"]["plot_twists"],
            }

            db_category = StoryCategory(
                name=key,
                display_name=category["name"],
                description=category["description"],
                story_config=json.dumps(story_config),
            )
            print(f"Created category object: {db_category.name}")  # Debug print
            db.add(db_category)

            logger.info(
                f"Initialized story category: {key}",
                extra={
                    "category": key,
                    "display_name": category["name"],
                    "elements": list(story_config.keys()),
                },
            )

        db.commit()
        logger.info(
            "Successfully initialized all story categories",
            extra={"total_categories": len(story_data)},
        )
    except Exception as e:
        logger.error(
            "Error initializing story categories",
            extra={"error": str(e)},
            exc_info=True,
        )
        raise


def init_lesson_topics(db, lesson_data):
    """Initialize lesson topics in the database."""
    for _, row in lesson_data.iterrows():
        # Handle both old and new format
        difficulty_level = row.get(
            "difficulty", row.get("difficulty_level", "Reasonably Challenging")
        )

        # Convert numeric difficulty_level to string if needed
        if isinstance(difficulty_level, (int, float)):
            difficulty_level = (
                "Very Challenging" if difficulty_level > 1 else "Reasonably Challenging"
            )

        db_topic = LessonTopic(
            topic=row["topic"],
            subtopic=row["subtopic"],
            question=row["question"],
            correct_answer=row["correct_answer"],
            wrong_answer1=row["wrong_answer1"],
            wrong_answer2=row["wrong_answer2"],
            explanation=row["explanation"],
            difficulty_level=difficulty_level,
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
