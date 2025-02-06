from typing import Any, Dict, Optional, List
import os
from openai import AsyncOpenAI
import google.generativeai as genai
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

        print("\n=== DEBUG: LLM Prompt Request ===")
        print("System Prompt:")
        print(system_prompt)
        print("\nUser Prompt:")
        print(user_prompt)
        print("========================\n")

        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.9,
                stream=True,
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
            print("\n=== ERROR: LLM Request Failed ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print("===============================\n")
            raise  # Re-raise the exception after logging


class GeminiService(BaseLLMService):
    """Google Gemini implementation of the LLM service."""

    def __init__(self, model: str = "gemini-2.0-flash-001"):
        """Initialize Gemini service with the specified model."""
        self.model = model
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("WARNING: GOOGLE_API_KEY is not set in environment variables!")
        genai.configure(api_key=api_key)
        # Initialize with system prompt as part of model configuration
        self.client = genai.GenerativeModel(
            model_name=self.model,
            generation_config=genai.GenerationConfig(
                temperature=0.9,
                max_output_tokens=8000,  # Adjust based on your needs
            ),
        )

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

        print("\n=== DEBUG: LLM Prompt Request ===")
        print("System Prompt:")
        print(system_prompt)
        print("\nUser Prompt:")
        print(user_prompt)
        print("========================\n")

        try:
            # Initialize the model with system prompt
            model = genai.GenerativeModel(
                model_name=self.model,
                system_instruction=system_prompt,
            )

            # Generate content with streaming
            response = model.generate_content(user_prompt, stream=True)

            collected_response = ""
            for chunk in response:
                if chunk.text:
                    collected_response += chunk.text
                    yield chunk.text

            # Log the complete response after streaming
            print("\n=== DEBUG: LLM Response ===")
            print(collected_response)
            print("========================\n")

        except Exception as e:
            print("\n=== ERROR: LLM Request Failed ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print("===============================\n")
            raise  # Re-raise the exception after logging
