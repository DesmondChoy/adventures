from app.services.chapter_manager import load_story_data, select_random_elements


def test_story_elements():
    # Test loading story data
    story_data = load_story_data()
    story_categories = story_data.get("story_categories", {})
    print(f"Successfully loaded {len(story_categories)} story categories:")
    for category_id in story_categories.keys():
        print(f"  - {category_id}")

    # Test selecting random elements from a story category
    if story_categories:
        story_category = list(story_categories.keys())[0]
        print(f"\nTesting element selection with category: {story_category}")
        try:
            # Select random elements from the story category
            elements = select_random_elements(story_data, story_category)
            print(f"Elements selected successfully!")
            print(f"Non-random elements: {elements['non_random_elements']['name']}")
            print(f"Selected theme: {elements['selected_theme']}")
            print(
                f"Selected setting: {elements['selected_narrative_elements']['settings']}"
            )
            print(f"Selected visual: {elements['selected_sensory_details']['visuals']}")
            print(f"Selected sound: {elements['selected_sensory_details']['sounds']}")
            print(f"Selected smell: {elements['selected_sensory_details']['smells']}")
            print(f"Selected moral teaching: {elements['selected_moral_teaching']}")
            print(f"Selected plot twist: {elements['selected_plot_twist']}")
        except Exception as e:
            print(f"Error selecting elements: {str(e)}")


if __name__ == "__main__":
    test_story_elements()
