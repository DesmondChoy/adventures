# app/services/llm.py
from typing import Any, Dict, Optional
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
        Generate the complete story segment (non-streaming).
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
                stream=False,  # Get complete response for non-streaming version
            )

            content = response.choices[0].message.content

            # Log the complete response
            print("\n=== DEBUG: LLM Response ===")
            print(content)
            print("========================\n")

            return content

        except Exception as e:
            print(f"\n=== ERROR: LLM Request Failed ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print("===============================\n")
            raise  # Re-raise the exception after logging

    async def generate_story_stream(
        self,
        story_config: Dict[str, Any],
        state: StoryState,
        question: Optional[Dict[str, Any]] = None,
    ):
        """
        Generate the story segment as a stream of chunks.
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
            stream = await self.client.chat.completions.create(
                model="gpt-4o-2024-08-06",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,  # Balanced between creativity and consistency
                stream=True,  # Enable streaming for real-time story delivery
            )

            collected_response = ""
            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    collected_response += content
                    yield content

            # Log the complete response after streaming
            print("\n=== DEBUG: LLM Response ===")
            print(collected_response)
            print("========================\n")

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

        # Add previous content if it exists
        if state.previous_content:
            prompt += f"""Previous story segment:
{state.previous_content}

"""

        # Opening scene at depth 1
        if state.depth == 1 and not state.history:
            if question:
                prompt += f"""Generate the opening scene of the story, introducing the setting and main character. 
                The scene should establish the world and protagonist while naturally leading to this educational question:
                {question["question"]}

                CRITICAL INSTRUCTIONS:
                1. Create an immersive fantasy world that will subtly connect to {question["question"].split()[0]}'s history
                2. The question should emerge naturally from the story events or character interactions
                3. DO NOT include any story-based choices or decisions
                4. DO NOT use bullet points, numbered lists, or dashes
                5. DO NOT end with "What should X do?" or similar prompts
                6. The question should feel like a natural part of the character's discovery

                The educational answers that will be presented separately are:
                - {question["correct_answer"]}
                - {question["wrong_answer1"]}
                - {question["wrong_answer2"]}

                Example integration:
                "As [Character] explored the ancient library, they discovered a fascinating chronicle that posed an intriguing question: '{question["question"]}'"
                or
                "The wise mentor turned to [Character] and asked about a pivotal moment in history: '{question["question"]}'"
                """
            else:
                prompt += """Generate the opening scene of the story, introducing the setting and main character. 
                The scene should establish the world and protagonist while building towards a natural educational moment.
                
                IMPORTANT: Do not include any story choices or decision points in this scene."""

        # Educational questions at odd depths (3 and above)
        elif question and state.depth % 2 == 1:
            prompt += f"""Continue the story, leading to a situation where the following educational question naturally arises: 
            {question["question"]}

            CRITICAL INSTRUCTIONS:
            1. The story should flow naturally towards the educational question
            2. The question should be asked by a character or emerge from the situation
            3. DO NOT include any story-based choices or decisions
            4. DO NOT use bullet points, numbered lists, or dashes
            5. DO NOT end with "What should X do?" or similar prompts
            6. Focus ONLY on building up to the educational question

            The educational answers that will be presented separately are:
            - {question["correct_answer"]}
            - {question["wrong_answer1"]}
            - {question["wrong_answer2"]}

            Example integration:
            "Professor [Name] paused thoughtfully before asking the class, '{question["question"]}'"
            or
            "[Character] discovered an ancient scroll. Its weathered text posed an intriguing question: '{question["question"]}'"
            """

        # Story-driven choices at even depths
        else:
            prompt += """Continue the story based on the previous choices, creating meaningful 
            consequences for the character's decisions. Focus on character development and 
            plot progression.
            
            IMPORTANT:
            1. DO NOT include any educational questions or historical facts
            2. Build towards a natural story decision point
            3. The story choices will be provided separately - do not list them in the narrative
            4. End the scene at a moment of decision, but DO NOT explicitly list the choices"""

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
