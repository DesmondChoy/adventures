# Product Context

## Purpose
Learning Odyssey transforms traditional education into an engaging, personalized adventure by combining structured lessons with dynamic storytelling. The application creates a unique learning experience where educational content and narrative choices work together to create an immersive journey.

## Problem Space
Traditional educational platforms often lack:
- Dynamic content adaptation
- Engaging narrative integration
- Real-time interaction
- Personalized learning paths

Learning Odyssey solves these challenges through:
1. Pre-defined educational content (`lessons.csv`) with dynamic narrative delivery
2. User-selected topics and adventure length
3. LLM-generated narrative choices and resolutions
4. Real-time state synchronization
5. Agency system with meaningful character choices

## User Experience and Features

1. **Educational Journey:**
   - Users select a setting and lesson topic
   - Make a pivotal agency choice in the first chapter that evolves throughout the journey
   - See visual representations of agency choices through AI-generated images
   - Every adventure is unique based on choices and educational responses

2. **Content Delivery:**
   - Word-by-word streaming creates natural reading experience
   - Markdown formatting enhances text presentation
   - Progressive enhancement (text first, images as they become available)
   - Responsive design for both desktop and mobile

3. **Chapter Types:**
   - **STORY Chapters:**
     * First chapter: Sets up the world and provides agency choice with images
     * Second-to-last chapter: Provides pivotal choices near the climax
     * Other STORY chapters: Advance the narrative with meaningful choices
   
   - **LESSON Chapters:**
     * Uses questions from `lessons.csv` with narrative wrapper
     * Incorporates educational content naturally using Story Object Method
     * Answers impact future chapters
   
   - **REFLECT Chapters:**
     * Follow LESSON chapters to test deeper understanding
     * Unified narrative-driven approach for both correct and incorrect answers
     * Uses Socratic method to guide deeper understanding
     * Evolves the user's agency choice based on their responses
   
   - **CONCLUSION Chapter:**
     * Always the final chapter
     * Resolves all narrative threads
     * Provides a satisfying resolution to the agency journey

4. **Agency System:**
   - First chapter choice from four categories:
     * Magical Items to Craft (lantern, rope, amulet, map, watch, potion)
     * Companions to Choose (owl, fox, squirrel, deer, otter, turtle)
     * Roles or Professions (healer, scholar, guardian, pathfinder, diplomat, craftsperson)
     * Special Abilities (animal whisperer, puzzle master, storyteller, element bender, dream walker, pattern seer)
   - Agency evolves throughout the adventure:
     * Correct answers: Agency is empowered or reveals new capabilities
     * Incorrect answers: Agency adapts to incorporate new knowledge
   - Agency plays pivotal role in climax phase
   - Agency has meaningful resolution in conclusion

5. **Technical Features:**
   - Real-time WebSocket state management
   - Client-side persistence with localStorage
   - Connection management with exponential backoff
   - Provider-agnostic LLM integration
   - Asynchronous image generation
   - Comprehensive error handling and recovery
