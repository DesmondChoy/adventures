# Streamlined Prompts for Learning Odyssey

This document explains the streamlined prompt engineering approach for the Learning Odyssey application, focusing on reducing redundancy and improving clarity in LLM prompts.

## Overview

The streamlined prompt approach addresses several issues in the original prompt structure:

1. **Redundant CRITICAL RULES sections** - Multiple sections with overlapping rules
2. **Scattered agency instructions** - Agency guidance spread across different sections
3. **Excessive verbosity** - Unnecessarily complex instructions
4. **Structural inefficiency** - Poor organization of related information

## Key Improvements

### 1. Consolidated CRITICAL RULES

The streamlined approach consolidates all critical rules into a single comprehensive section organized by categories:

```markdown
# CRITICAL RULES
1. **Narrative Structure**: Begin directly (never with "Chapter X"), end at natural decision points, maintain consistent elements
2. **Content Development**: Incorporate sensory details naturally, develop theme organically, balance entertainment with learning
3. **Educational Integration**: Ensure lessons feel organic to the story, never forced or artificial
4. **Agency Integration**: Weave the character's pivotal choice naturally throughout, showing its evolution and impact
5. **Format Requirements**: Follow exact choice format instructions, never list choices within narrative text
```

### 2. Integrated Agency Instructions

Agency instructions are now integrated with storytelling approach and critical rules:

```markdown
# Storytelling Approach & Agency Integration
1. Maintain narrative consistency with meaningful consequences for decisions
2. Seamlessly integrate educational content while developing theme/moral teaching organically
3. Structure content with multiple paragraphs and blank lines for readability
4. Incorporate sensory details naturally to enhance immersion
5. The character's pivotal first-chapter choice (item, companion, role, or ability):
   - Represents a core aspect of their identity
   - Must be referenced consistently throughout ALL chapters
   - Should evolve as the character learns and grows
   - Will play a crucial role in the story's climax
   - Should feel like a natural part of the narrative
```

### 3. Improved Organization

The streamlined approach organizes the prompt into a clearer structure:

- **System Prompt**:
  - Storyteller Role
  - Story Elements
  - Storytelling Approach & Agency Integration (consolidated)
  - CRITICAL RULES (consolidated)

- **User Prompt for First Chapter**:
  - Current Context
  - Story History
  - Phase Guidance
  - Story Chapter Instructions
  - Agency Choice & Critical Requirements (consolidated)

### 4. Reduced Redundancy

Each instruction appears only once, eliminating repetition across multiple sections.

### 5. Enhanced Clarity

Instructions are presented in a clear, categorized manner with logical grouping of related information.

## Implementation

### Files

- `streamlined_prompt_templates.py`: Contains the streamlined templates
- `streamlined_prompt_engineering.py`: Contains functions to generate prompts using the streamlined templates
- `test_streamlined_prompts.py`: Demonstrates the differences between original and streamlined prompts

### Usage

To use the streamlined prompts in your code:

```python
from app.services.llm.streamlined_prompt_engineering import build_streamlined_prompt

# Get both system and user prompts
system_prompt, user_prompt = build_streamlined_prompt(state, lesson_question, previous_lessons)

# Or get them individually
from app.services.llm.streamlined_prompt_engineering import (
    build_streamlined_system_prompt,
    build_streamlined_first_chapter_prompt
)

system_prompt = build_streamlined_system_prompt(state)
first_chapter_prompt = build_streamlined_first_chapter_prompt(state)
```

### Integration

To integrate with the existing LLM service:

1. Import the streamlined prompt functions in your LLM service
2. Use the streamlined functions for the first chapter
3. Continue using the original functions for other chapters, or extend the streamlined approach to cover them as well

Example integration in `app/services/llm/providers.py`:

```python
from app.services.llm.streamlined_prompt_engineering import build_streamlined_prompt

# In your LLM generation function
if state.current_chapter_number == 1 and state.planned_chapter_types[0] == ChapterType.STORY:
    # Use streamlined prompts for first chapter
    system_prompt, user_prompt = build_streamlined_prompt(state)
else:
    # Use original prompts for other chapters
    system_prompt = build_system_prompt(state)
    user_prompt = build_user_prompt(state, lesson_question, previous_lessons)
```

## Testing

Run the test script to see a side-by-side comparison of the original and streamlined prompts:

```bash
python -m app.services.llm.test_streamlined_prompts
```

## Benefits

1. **Improved LLM Comprehension**: Clearer instructions lead to better LLM understanding
2. **Reduced Token Usage**: More concise prompts use fewer tokens
3. **Better Maintainability**: Consolidated rules are easier to update
4. **Enhanced Consistency**: Single source of truth for critical rules
5. **Clearer Agency Integration**: More natural incorporation of agency elements

## Future Enhancements

The current implementation focuses on streamlining the first chapter prompt. Future enhancements could include:

1. Extending the streamlined approach to other chapter types (LESSON, REFLECT, CONCLUSION)
2. Further optimizing token usage while maintaining clarity
3. Implementing A/B testing to compare LLM output quality between original and streamlined prompts
