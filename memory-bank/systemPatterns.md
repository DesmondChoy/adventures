# System Patterns

## Architecture Overview
```mermaid
graph TD
    Client[Web Client] <--> WSR[WebSocket Router]
    WSR <--> WSS[WebSocket Service]
    WSS <--> ASM[Adventure State Manager]
    ASM <--> AS[AdventureState]
    ASM <--> CM[Chapter Manager]
    CM <--> LLM[LLM Service]
    CM <--> DB[(Database)]
    WSS <--> IMG[Image Generation Service]
    CM <--> SL[Story Loader]
    SL <--> SF[(Story Files)]

    subgraph Client Side
        LP[localStorage] <--> CSM[Client State Manager]
        CSM <--> Client
    end

    subgraph Core State
        AS
    end

    subgraph Services
        WSS
        ASM
        CM
        LLM
        IMG
    end

    subgraph Content Sources
        CSV[lessons.csv] --> CM
        LLM --> CM
        IMG --> WSS
        SF --> SL
    end
```

## Core Components

### 1. State Management
- **AdventureState** (`app/models/story.py`)
  * Single source of truth for all state
  * Complete state serialization
  * Pre-determined chapter sequence via `planned_chapter_types`
  * Metadata tracking for agency, elements, and challenge types
  * Critical properties preserved during updates:
    - `selected_narrative_elements`, `selected_sensory_details`
    - `selected_theme`, `selected_moral_teaching`, `selected_plot_twist`
    - `metadata`, `planned_chapter_types`, `story_length`

- **Client-Side State** (`app/templates/index.html`)
  * `AdventureStateManager` uses localStorage
  * Exponential backoff (1s to 30s) with max 5 reconnection attempts
  * Automatic state restoration on reconnect

### 2. Chapter Management
- **Chapter Sequencing** (`app/services/chapter_manager.py`)
  * First chapter: STORY
  * Second-to-last chapter: STORY
  * Last chapter: CONCLUSION
  * 50% of remaining chapters: LESSON (subject to available questions)
  * 50% of LESSON chapters: REFLECT (follow LESSON)
  * No consecutive LESSON chapters
  * STORY chapters follow REFLECT chapters

- **Content Sources**
  * LESSON: `lessons.csv` + LLM wrapper
  * STORY: Full LLM generation with choices
  * REFLECT: Narrative-driven follow-up to LESSON
  * CONCLUSION: Resolution without choices

### 3. Story Data Management
- **Story Loader** (`app/data/story_loader.py`)
  * Loads individual story files from `app/data/stories/` directory
  * Combines data into a consistent structure for use by Chapter Manager
  * Provides caching for performance optimization
  * Offers methods for accessing specific story categories
  * Handles error cases gracefully with detailed logging

- **Story Files** (`app/data/stories/*.yaml`)
  * Individual YAML files for each story category
  * Consistent structure across all story files
  * Contains narrative elements, sensory details, and other story components
  * Enables easier maintenance and collaboration

### 4. WebSocket Components
- **Router** (`app/routers/websocket_router.py`)
  * Handles connection lifecycle
  * Validates client messages
  * Works with AdventureStateManager for state handling

- **Service** (`app/services/websocket_service.py`)
  * Processes user choices
  * Manages chapter content generation
  * Handles streaming of content
  * Coordinates with ImageGenerationService

### 5. LLM Integration
- **Prompt Engineering** (`app/services/llm/prompt_engineering.py`)
  * `build_prompt()`: Main entry point for all chapter types
  * `build_system_prompt()`: Creates system context
  * `build_user_prompt()`: Creates chapter-specific prompts
  * `_get_phase_guidance()`: Adds phase-specific guidance

- **Provider Abstraction** (`app/services/llm/providers.py`)
  * Supports GPT-4o and Gemini
  * Standardized response handling
  * Error recovery mechanisms

### 6. Image Generation
- **Service** (`app/services/image_generation_service.py`)
  * Asynchronous processing with `generate_image_async()`
  * 5 retries with exponential backoff
  * Base64 encoding for WebSocket transmission
  * Progressive enhancement (text first, images as available)
  * Enhanced prompt construction with `enhance_prompt()`
  * Visual details extraction from agency options

- **Agency Choice Image Generation Pattern**
```mermaid
flowchart TD
    subgraph WebSocketService
        stream_and_send_chapter --> |"For Chapter 1\nSTORY type"| build_agency_lookup
        build_agency_lookup --> |"Import categories\ndirectly"| categories[prompt_templates.py\ncategories dictionary]
        build_agency_lookup --> |"Create lookup\nwith variations"| agency_lookup
        stream_and_send_chapter --> |"For each choice"| extract_agency_name
        extract_agency_name --> |"From 'As a...'\nformat"| agency_name
        extract_agency_name --> find_agency_option
        find_agency_option --> |"Try direct match\nwith agency name"| categories
        find_agency_option --> |"Try match with\nfull choice text"| categories
        find_agency_option --> |"Fallback to\nagency_lookup"| agency_lookup
        find_agency_option --> |"If found"| original_option
        find_agency_option --> |"If not found"| use_choice_text
        original_option --> enhance_prompt
        use_choice_text --> enhance_prompt
    end
    
    subgraph ImageGenerationService
        enhance_prompt --> extract_name
        extract_name --> |"Handle 'As a...'\nformat"| clean_name
        enhance_prompt --> extract_visual_details
        extract_visual_details --> |"From square\nbrackets"| visual_details
        enhance_prompt --> |"If no visual details\nin original prompt"| lookup_visual_details
        lookup_visual_details --> |"Import categories\ndirectly"| categories
        lookup_visual_details --> |"Find matching\nagency option"| found_visual_details
        clean_name --> build_components
        visual_details --> build_components
        found_visual_details --> build_components
        build_components --> |"Join with commas"| final_prompt
        final_prompt --> generate_image_async
    end
    
    generate_image_async --> |"Async processing"| _generate_image
    _generate_image --> |"API call with\n5 retries"| image_data
    image_data --> |"Base64 encoded"| WebSocketService
    WebSocketService --> |"Send to client"| Client[Web Client]
```

## Key Patterns

### 1. Story Data Organization Pattern
```mermaid
flowchart TD
    subgraph Story_Data_Organization
        SL[StoryLoader] --> |"Loads"| SF[Story Files]
        SF --> |"Individual files for"| SC[Story Categories]
        SC --> |"Contains"| NE[Narrative Elements]
        SC --> |"Contains"| SD[Sensory Details]
        SC --> |"Contains"| MT[Moral Teachings]
        SC --> |"Contains"| PT[Plot Twists]
        SC --> |"Contains"| TH[Themes]
        
        SL --> |"Provides"| CM[Chapter Manager]
        CM --> |"Selects random"| Elements[Story Elements]
        Elements --> |"Used in"| AS[Adventure State]
    end
    
    subgraph Element_Selection
        CM --> |"Calls"| SRE[select_random_elements]
        SRE --> |"Extracts"| NRE[Non-Random Elements]
        SRE --> |"Randomly selects"| RE[Random Elements]
        NRE --> |"name, description"| AS
        RE --> |"settings, theme, etc."| AS
    end
```

### 2. Agency Pattern
- **First Chapter Choice**
  * Four categories: Items, Companions, Roles, Abilities
  * Stored in `state.metadata["agency"]`
  * Referenced throughout all chapters

- **Agency Evolution**
  * REFLECT chapters: Agency evolves based on answers
  * CLIMAX phase: Agency plays pivotal role
  * CONCLUSION: Agency has meaningful resolution

### 3. Narrative Continuity
- **Story Elements Consistency**
  * Setting, characters, theme maintained
  * Plot twist development across phases
  * Agency references in all chapters

- **Previous Chapter Impact**
  * LESSON: `process_consequences()` generates appropriate story consequences
  * STORY: Continue from chosen path with consequences
  * REFLECT: Build on previous lesson understanding

### 4. Testing Framework
- **Simulation** (`tests/simulations/story_simulation.py`)
  * Generates structured log data
  * Verifies complete workflow

- **Test Files**
  * `tests/simulations/test_simulation_functionality.py`: Verifies sequences, ratios
  * `tests/simulations/test_simulation_errors.py`: Tests error handling
  * `tests/data/test_story_loader.py`: Tests story data loading functionality
  * `tests/data/test_story_elements.py`: Tests random element selection
  * `tests/data/test_chapter_manager.py`: Tests adventure state initialization

### 5. Text Streaming
- **Content Delivery**
  * Word-by-word streaming (0.02s delay)
  * Paragraph breaks (0.1s delay)
  * Markdown formatting support
  * Buffer management for partial content
  * "Chapter" prefix removal with regex pattern `r"^Chapter(?:\s+\d+)?:?\s*"`

- **Content Processing Flow**:
```mermaid
flowchart TD
    LLM[LLM Service] -->|Raw response| WSS[WebSocket Service]
    WSS -->|Remove chapter prefix| clean_content
    clean_content -->|Split into paragraphs| paragraphs
    paragraphs -->|Split into words| words
    words -->|Stream with delay| Client
```

### 6. Prompt Engineering Pattern (`app/services/llm/prompt_templates.py`)
- **Prompt Structure and Organization**:
  * Modular template design with separate templates for different chapter types
  * Consistent section ordering across templates
  * Clear delineation between system and user prompts
  * Hierarchical organization for improved readability
  * CRITICAL: Maintain consistent structure across all prompt templates

- **Prompt Flow Architecture**:
```mermaid
flowchart TD
    subgraph Main_Functions
        build_prompt --> build_system_prompt
        build_prompt --> build_user_prompt
    end
    
    subgraph User_Prompt_Builder
        build_user_prompt -->|Get phase guidance|get_phase_guidance
        build_user_prompt --> ChapterSelector{Chapter Type?}
        build_user_prompt --> |"Prepend phase guidance\n(no duplication)"|FinalUserPrompt
        
        ChapterSelector -->|STORY Ch.1| build_first_chapter_prompt
        ChapterSelector -->|STORY Ch.2+| build_story_chapter_prompt
        ChapterSelector -->|LESSON| build_lesson_chapter_prompt
        ChapterSelector -->|REFLECT| build_reflect_chapter_prompt
        ChapterSelector -->|CONCLUSION| build_conclusion_chapter_prompt
    end
    
    subgraph Chapter_Builders
        build_first_chapter_prompt --> build_base_prompt
        build_story_chapter_prompt --> build_base_prompt
        build_lesson_chapter_prompt --> build_base_prompt
        build_reflect_chapter_prompt --> build_base_prompt
        build_conclusion_chapter_prompt --> build_base_prompt
        
        build_first_chapter_prompt --> |Format using|FIRST_CHAPTER_PROMPT
        build_story_chapter_prompt --> |Format using|STORY_CHAPTER_PROMPT
        build_lesson_chapter_prompt --> |Format using|LESSON_CHAPTER_PROMPT
        build_reflect_chapter_prompt --> |Format using|REFLECT_CHAPTER_PROMPT
        build_conclusion_chapter_prompt --> |Format using|CONCLUSION_CHAPTER_PROMPT
    end
    
    subgraph Helper_Functions
        build_base_prompt --> |Returns|story_history
        build_base_prompt --> |Returns|story_phase
        build_base_prompt --> |Returns|chapter_type
        
        get_phase_guidance --> BASE_PHASE_GUIDANCE
        get_phase_guidance --> |If applicable|PLOT_TWIST_GUIDANCE
        get_phase_guidance --> |For Exposition phase|replace_adventure_topic[Replace {adventure_topic} placeholder]
        replace_adventure_topic --> |From metadata|state.metadata["non_random_elements"]["name"]
        
        build_first_chapter_prompt --> get_agency_category
        build_story_chapter_prompt --> |If needed|process_consequences
        build_lesson_chapter_prompt --> format_lesson_answers
        build_reflect_chapter_prompt --> get_reflective_technique
    end
    
    subgraph Templates["prompt_templates.py"]
        SYSTEM_PROMPT_TEMPLATE
        FIRST_CHAPTER_PROMPT
        STORY_CHAPTER_PROMPT
        LESSON_CHAPTER_PROMPT
        REFLECT_CHAPTER_PROMPT
        CONCLUSION_CHAPTER_PROMPT
        BASE_PHASE_GUIDANCE
        PLOT_TWIST_GUIDANCE
    end
    
    build_system_prompt --> SYSTEM_PROMPT_TEMPLATE
    build_system_prompt --> SystemPrompt
```

- **Avoiding Prompt Bloat**:
  * Common causes:
    - Redundant instructions across different sections
    - Overly verbose explanations
    - Multiple sections addressing the same concern
    - Accumulation of ad-hoc fixes without refactoring
    - Excessive formatting instructions that could be consolidated
    - Separate "CRITICAL" sections for related instructions
    - Repetitive emphasis markers (bold, caps, etc.)
  * Prevention strategies:
    - Regular prompt audits to identify and remove redundancies
    - Consolidate similar instructions across templates
    - Focus on essential instructions that drive desired outcomes
    - Maintain balance between clarity and conciseness
    - CRITICAL: Consider token count impact of prompt design decisions
