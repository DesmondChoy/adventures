from app.data.lesson_loader import LessonLoader

# Create a file to write the output
with open("test_results.txt", "w") as f:
    # Create a loader instance
    loader = LessonLoader()

    # Clear any existing cache
    loader.clear_cache()

    # Get all lessons
    all_lessons = loader.load_all_lessons()
    f.write(f"Total lessons: {len(all_lessons)}\n")

    # Get available topics
    topics = loader.get_available_topics()
    f.write(f"Available topics: {topics}\n")

    # Get available difficulties
    difficulties = loader.get_available_difficulties()
    f.write(f"Available difficulties: {difficulties}\n")

    # Get Human Body lessons
    human_body_lessons = loader.get_lessons_by_topic("Human Body")
    f.write(f"Human Body lessons: {len(human_body_lessons)}\n")

    # Get lessons by difficulty
    reasonably_challenging = loader.get_lessons_by_difficulty("Reasonably Challenging")
    f.write(f"Reasonably Challenging lessons: {len(reasonably_challenging)}\n")

    # Get Human Body lessons with Reasonably Challenging difficulty
    human_body_rc = loader.get_lessons_by_topic_and_difficulty(
        "Human Body", "Reasonably Challenging"
    )
    f.write(f"Human Body + Reasonably Challenging: {len(human_body_rc)}\n")

print("Test completed. Results written to test_results.txt")
