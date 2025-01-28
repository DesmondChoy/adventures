from typing import Any, Dict, Optional, List
import os
from openai import AsyncOpenAI
from app.models.story import StoryState
from app.services.llm.base import BaseLLMService
from app.services.llm.prompt_engineering import build_system_prompt, build_user_prompt


class OpenAIService(BaseLLMService):
    """OpenAI implementation of the LLM service."""

    def __init__(self, model: str = "gpt-4o-2024-08-06"):
        self.model = model
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if not os.getenv("OPENAI_API_KEY"):
            print("WARNING: OPENAI_API_KEY is not set in environment variables!")

    async def generate_story_stream(
        self,
        story_config: Dict[str, Any],
        state: StoryState,
        question: Optional[Dict[str, Any]] = None,
        previous_questions: Optional[List[Dict[str, Any]]] = None,
    ):
        """Generate the story segment as a stream of chunks."""
        # Build prompts using the shared prompt engineering module
        system_prompt = build_system_prompt(story_config)
        user_prompt = build_user_prompt(
            story_config, state, question, previous_questions
        )

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
                model=self.model,
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
