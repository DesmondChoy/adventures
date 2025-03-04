from app.data.story_loader import StoryLoader


def test_story_loader():
    loader = StoryLoader()
    data = loader.load_all_stories()
    story_categories = data.get("story_categories", {})
    print(f"Successfully loaded {len(story_categories)} story categories:")
    for category_id, category_data in story_categories.items():
        print(f"  - {category_id}: {category_data.get('name', 'Unknown')}")


if __name__ == "__main__":
    test_story_loader()
