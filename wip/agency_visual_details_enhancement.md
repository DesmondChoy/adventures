# Agency Visual Details Enhancement for Image Generation

## Problem Statement

The current image generation system in Learning Odyssey has a significant limitation in how it represents agency choices in generated images. When a user selects an agency option in Chapter 1 (such as a companion, ability, artifact, or profession), the image generation prompt only includes the name of the agency (e.g., "featuring Element Bender") without any visual details.

This leads to several issues:

1. **Inconsistent Representation**: The image model has no context about what the agency element should look like, resulting in inconsistent or inaccurate visual representations.

2. **Lost Visual Details**: The rich visual descriptions already defined in `prompt_templates.py` (e.g., "a swirling figure with hands sparking flames, splashing water, tossing earth, and twirling breezes in a dance") are not being utilized in the image generation process.

3. **Undifferentiated Agency Types**: There's no distinction between different types of agency (companion, ability, artifact, profession) in how they're described in the prompt, leading to generic phrasing like "featuring X" regardless of what X represents.

4. **Disconnection from Narrative**: The agency element often doesn't appear to be integrated into the scene in a way that reflects its role in the story.

## Root Cause Analysis

The issue stems from how agency choices are stored and referenced in the image generation process:

1. When a user makes an agency choice in Chapter 1, only the choice text is stored in `state.metadata["agency"]` without the visual details that are defined in `prompt_templates.py`.

2. The `enhance_prompt` method in `ImageGenerationService` extracts just the agency name from the stored description and adds it to the prompt with a generic "featuring" prefix.

3. There is no mechanism to look up the original visual details from the `categories` dictionary in `prompt_templates.py` or to determine the agency category (companion, ability, artifact, profession).

## Proposed Solution

We will implement a comprehensive solution that stores the complete agency information at the time of selection and uses it to create more detailed and contextually appropriate image prompts.

### Implementation Steps

1. **Enhance Agency Storage in Chapter 1**:
   - Modify the `process_story_response` function in `app/services/websocket/choice_processor.py` to extract and store additional agency information when the first chapter choice is made.
   - Store the agency category, visual details, and other relevant information in the state metadata.

2. **Update Prompt Enhancement Logic**:
   - Modify the `enhance_prompt` method in `app/services/image_generation_service.py` to use the stored agency details.
   - Implement category-specific prefixes with clearer subject references.
   - Include the visual details in parentheses after the agency name.
   - Remove the story name and visual details from the prompt, focusing on the chapter summary and agency representation.

3. **Add Fallback Mechanism**:
   - Implement a fallback lookup mechanism for cases where visual details might not be stored correctly.
   - This ensures backward compatibility with existing adventures.

### Code Changes

#### 1. Update `process_story_response` in `choice_processor.py`:

```python
# In process_story_response function in choice_processor.py
if (
    previous_chapter.chapter_number == 1
    and previous_chapter.chapter_type == ChapterType.STORY
):
    logger.debug("Processing first chapter agency choice")

    # Extract agency category and visual details
    agency_category = ""
    visual_details = ""
    
    # Try to find the matching agency option
    try:
        from app.services.llm.prompt_templates import categories
        for category_name, category_options in categories.items():
            for option in category_options:
                # Extract the name part (before the bracket)
                option_name = option.split("[")[0].strip()
                # Check if this option matches the choice text
                if option_name.lower() in choice_text.lower() or choice_text.lower() in option_name.lower():
                    agency_category = category_name
                    # Extract visual details from square brackets
                    match = re.search(r"\[(.*?)\]", option)
                    if match:
                        visual_details = match.group(1)
                    break
            if visual_details:
                break
    except Exception as e:
        logger.error(f"Error extracting agency details: {e}")

    # Store agency choice in metadata with visual details
    state.metadata["agency"] = {
        "type": "choice",
        "name": "from Chapter 1",
        "description": choice_text,
        "category": agency_category,
        "visual_details": visual_details,
        "properties": {"strength": 1},
        "growth_history": [],
        "references": [],
    }

    logger.debug(f"Stored agency choice from Chapter 1: {choice_text}")
    logger.debug(f"Agency category: {agency_category}")
    logger.debug(f"Visual details: {visual_details}")
```

#### 2. Update `enhance_prompt` in `image_generation_service.py`:

```python
# Build components in the specified order
components = []

# If we have a chapter summary, use that as the main subject
if chapter_summary:
    # Ensure chapter_summary is not empty or just whitespace
    if chapter_summary and chapter_summary.strip():
        components.append(f"Fantasy illustration of {chapter_summary}")
    else:
        # Use a fallback approach - add a generic component
        components.append("Fantasy illustration of a scene from the story")
else:
    # Extract the combined name and visual details up to the closing bracket
    name_with_details = ""
    full_bracket_match = re.match(r"(.*?\])", original_prompt)
    if full_bracket_match:
        name_with_details = full_bracket_match.group(1).strip()
    else:
        # Fallback to just extracting the name if no bracket is found
        name = original_prompt.split(" - ")[0].strip()

        # Handle agency name extraction from choice text if needed
        if re.match(r"(?:[^:]+):\s*([^-]+)", name):
            agency_name = (
                re.match(r"(?:[^:]+):\s*([^-]+)", name).group(1).strip()
            )
            name = agency_name
        elif re.match(r"As a (\w+\s*\w*)", name):
            as_a_match = re.match(r"As a (\w+\s*\w*)", name)
            agency_name = as_a_match.group(1).strip()
            name = agency_name

        name_with_details = name

        # Try to look up visual details for this name
        visual_details = self._lookup_visual_details(name)
        if visual_details:
            name_with_details = f"{name} [{visual_details}]"

    # Start with "Fantasy illustration of [Agency Name with Visual Details]"
    components.append(f"Fantasy illustration of {name_with_details}")

# Add agency information from adventure state regardless of chapter type
if (
    adventure_state
    and hasattr(adventure_state, "metadata")
    and "agency" in adventure_state.metadata
):
    agency = adventure_state.metadata["agency"]
    agency_description = agency.get("description", "")
    agency_visual_details = agency.get("visual_details", "")
    agency_category = agency.get("category", "")
    
    if agency_description:
        # Extract just the agency name/item without extra details
        agency_name = (
            agency_description.split(" - ")[0].strip()
            if " - " in agency_description
            else agency_description
        )
        if ":" in agency_name:
            agency_name = agency_name.split(":", 1)[1].strip()
        
        # If we don't have visual details stored, try to look them up
        if not agency_visual_details:
            agency_visual_details = self._lookup_visual_details(agency_name)
            
        # Add appropriate prefix based on agency category
        if agency_category == "Choose a Companion":
            prefix = "He/she is accompanied by"
        elif agency_category == "Take on a Profession":
            prefix = "He/she is a"
        elif agency_category == "Gain a Special Ability":
            prefix = "He/she has the power of"
        elif agency_category == "Craft a Magical Artifact":
            prefix = "He/she carries a magical"
        else:
            prefix = "He/she has"
            
        if agency_visual_details:
            components.append(f"{prefix} {agency_name} ({agency_visual_details})")
        else:
            components.append(f"{prefix} {agency_name}")

# Add base style
components.append(base_style)

# Join all components with commas
prompt = ", ".join(components)
return prompt
```

### Expected Results

With these changes, the image generation prompts will be much more detailed and contextually appropriate. For example:

**Before:**
```
Fantasy illustration of A giant mushroom pulses blue light in a forest clearing, illuminating the forest floor with spiderwebs. Shimmering bees swarm the mushroom as massive webs glow with intricate patterns., featuring Element Bender, in Festival of Lights & Colors, with Rainbow Cascade: A waterfall refracting sunlight into vivid arcs, shimmering more brilliantly after acts of harmony or camaraderie., vibrant colors, detailed, whimsical, digital art
```

**After:**
```
Fantasy illustration of A giant mushroom pulses blue light in a forest clearing, illuminating the forest floor with spiderwebs. Shimmering bees swarm the mushroom as massive webs glow with intricate patterns., He/she has the power of Element Bender (a swirling figure with hands sparking flames, splashing water, tossing earth, and twirling breezes in a dance), vibrant colors, detailed, whimsical, digital art
```

This will result in more consistent and accurate visual representations of agency elements in the generated images, enhancing the overall storytelling experience.
