from app.data.lesson_loader import LessonLoader

loader = LessonLoader()
print(f"Available topics: {loader.get_available_topics()}")
print(f"Available difficulties: {loader.get_available_difficulties()}")
print(f"Total lessons: {len(loader.load_all_lessons())}")
print(f"Farm Animals lessons: {len(loader.get_lessons_by_topic('Farm Animals'))}")
print(
    f"Reasonably Challenging lessons: {len(loader.get_lessons_by_difficulty('Reasonably Challenging'))}"
)
print(
    f"Farm Animals + Reasonably Challenging: {len(loader.get_lessons_by_topic_and_difficulty('Farm Animals', 'Reasonably Challenging'))}"
)
