# app/services/llm.py
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
import os
from app.models.story import StoryState


class LLMService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if not os.getenv("OPENAI_API_KEY"):
            print("WARNING: OPENAI_API_KEY is not set in environment variables!")

    async def generate_story_segment(
        self,
        story_config: Dict[str, Any],
        state: StoryState,
        question: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate the next story segment based on the current state and configuration.

        Args:
            story_config: Configuration for the story category (tone, rules, etc.)
            state: Current story state including history
            question: Optional educational question to integrate
        """
        # Build the system prompt that establishes the storytelling framework
        system_prompt = self._build_system_prompt(story_config)

        # Build the user prompt that includes story state and requirements
        user_prompt = self._build_user_prompt(story_config, state, question)

        # Debug output
        print("\n=== DEBUG: LLM Request ===")
        print("System Prompt:")
        print(system_prompt)
        print("\nUser Prompt:")
        print(user_prompt)
        print("========================\n")

        try:
            # Call the LLM with our prompts
            response = await self.client.chat.completions.create(
                model="gpt-4o-2024-08-06",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,  # Balanced between creativity and consistency
                stream=True,  # Enable streaming for real-time story delivery
            )
            return response
        except Exception as e:
            print(f"\n=== ERROR: LLM Request Failed ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print("===============================\n")
            raise  # Re-raise the exception after logging

    def _build_system_prompt(self, story_config: Dict[str, Any]) -> str:
        """Create a system prompt that establishes the storytelling framework."""
        return f"""
        You are a master storyteller crafting an interactive educational story.
        
        Writing Style:
        - Maintain a {story_config["tone"]} tone throughout the narrative
        - Use vocabulary appropriate for {story_config["vocabulary_level"]}
        - Follow these story rules: {", ".join(story_config["story_rules"])}

        Story Elements to Include:
        - Setting types: {", ".join(story_config["narrative_elements"]["setting_types"])}
        - Character archetypes: {", ".join(story_config["narrative_elements"]["character_archetypes"])}

        Your task is to generate engaging story segments that:
        1. Maintain narrative consistency with previous choices
        2. Create meaningful consequences for user decisions
        3. Seamlessly integrate educational elements when provided
        4. End each segment with clear choice points that advance the story
        5. Use multiple paragraphs separated by blank lines to ensure readability.
           The question and its choices, if any, should appear in a separate paragraph from the main narrative.
        """

    def _build_user_prompt(
        self,
        story_config: Dict[str, Any],
        state: StoryState,
        question: Optional[Dict[str, Any]],
    ) -> str:
        """Create a user prompt that includes story state and current requirements."""
        prompt = f"""Current story state:
- Depth: {state.depth} of 3
- Previous choices: {", ".join(state.history) if state.history else "Story beginning"}

"""

        if state.depth == 1 and not state.history:  # Opening scene at depth 1
            prompt += "Generate the opening scene of the story, introducing the setting and main character."
        elif question:
            # Integrate educational question naturally into the story
            prompt += f"""Continue the story, naturally leading to a situation where the following question 
            can be asked: {question["question"]}

The choices should be:
1. {question["correct_answer"]}
2. {question["wrong_answer1"]}
3. {question["wrong_answer2"]}

The question should feel like a natural part of the story's progression."""
        else:
            # Regular story continuation
            prompt += """Continue the story based on the previous choices, 
            creating meaningful consequences for the character's decisions.
            
End this segment with two clear choices that would lead the story in different directions."""

        return prompt

    def _process_consequences(
        self, state: StoryState, was_correct: Optional[bool] = None
    ) -> str:
        """Generate appropriate story consequences based on question response."""
        if was_correct is None:
            return ""

        return """Based on the character's choice, continue the story while:
        - Acknowledging whether the choice was correct or incorrect
        - Providing a natural explanation for why this was the right/wrong choice
        - Maintaining story flow without breaking immersion
        - Using the outcome to drive the story forward"""
