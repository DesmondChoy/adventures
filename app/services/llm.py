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
        question: Optional[Dict[str, Any]] = None,
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

        # Check if we're following up on a previous question (any depth)
        if state.history and state.history[-1] in ["correct", "wrong1", "wrong2"]:
            # Get the last choice and determine if it was correct
            last_choice = state.history[-1]
            was_correct = last_choice == "correct"

            # Add consequences guidance to the prompt
            consequences_guidance = self._process_consequences(state, was_correct)

            # If we have a new question, combine consequences with question setup
            if question:
                prompt += f"""Continue the story, acknowledging the previous answer while leading to a new question.

{consequences_guidance}

The story should naturally build towards this question:
{question["question"]}

CRITICAL INSTRUCTIONS:
1. First address the consequences of the previous answer
2. Then naturally transition to a situation where the new question arises
3. The question should emerge from the story events or character interactions
4. DO NOT include any story-based choices or decisions
5. The question should feel like a natural part of the character's journey

The educational answers that will be presented separately are:
- {question["correct_answer"]}
- {question["wrong_answer1"]}
- {question["wrong_answer2"]}"""
            else:
                prompt += f"""Continue the story based on the character's previous answer.

{consequences_guidance}

IMPORTANT:
1. The story should clearly but naturally acknowledge the impact of their previous answer
2. Build towards a natural story decision point
3. The story choices will be provided separately - do not list them in the narrative
4. End the scene at a moment of decision - explicitly list the choices"""

        # Opening scene at depth 1
        elif state.depth == 1 and not state.history:
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
                - {question["wrong_answer2"]}"""
            else:
                prompt += """Generate the opening scene of the story, introducing the setting and main character. 
                The scene should establish the world and protagonist while building towards a natural educational moment.
                
                IMPORTANT: Do not include any story choices or decision points in this scene."""
        # New question without previous answer to address
        elif question:
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
            - {question["wrong_answer2"]}"""
        # Regular story continuation
        else:
            prompt += """Continue the story based on the previous choices, creating meaningful 
            consequences for the character's decisions. Focus on character development and 
            plot progression.
            
            IMPORTANT:
            1. DO NOT include any educational questions or historical facts
            2. Build towards a natural story decision point
            3. The story choices will be provided separately - do not list them in the narrative
            4. End the scene at a moment of decision - explicitly list the choices"""

        return prompt

    def _process_consequences(
        self, state: StoryState, was_correct: Optional[bool] = None
    ) -> str:
        """Generate appropriate story consequences based on question response."""
        if was_correct is None:
            return ""

        if was_correct:
            return """The story should:
            - Acknowledge the character's correct understanding of the question
            - Show how this understanding connects to their current situation
            - Use this success to build confidence for future challenges"""
        else:
            return """The story should:
            - Acknowledge the incorrect answer while maintaining the character's dignity
            - Explain the correct answer in a way that is easy to understand
            - Show how this misunderstanding leads to a valuable learning moment
            - Use this as an opportunity for growth and deeper understanding
            - Connect the correction to their current situation and future challenges"""
