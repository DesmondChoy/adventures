from app.services.chapter_manager import ChapterManager, load_story_data


def test_chapter_manager():
    # Test loading story data
    story_data = load_story_data()
    story_categories = story_data.get("story_categories", {})
    print(f"Successfully loaded {len(story_categories)} story categories:")
    for category_id in story_categories.keys():
        print(f"  - {category_id}")

    # Test initializing adventure state with a story category
    if story_categories:
        story_category = list(story_categories.keys())[0]
        print(
            f"\nTesting adventure state initialization with category: {story_category}"
        )
        try:
            # Initialize with 10 chapters and a dummy lesson topic
            state = ChapterManager.initialize_adventure_state(
                10, "math", story_category
            )
            print(f"Adventure state initialized successfully!")
            print(f"Story length: {state.story_length}")
            print(f"Chapter types: {[ct.value for ct in state.planned_chapter_types]}")
            print(f"Selected theme: {state.selected_theme}")
            print(
                f"Selected setting: {state.selected_narrative_elements.get('settings', 'None')}"
            )
        except Exception as e:
            print(f"Error initializing adventure state: {str(e)}")


if __name__ == "__main__":
    test_chapter_manager()
