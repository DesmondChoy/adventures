from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import base64
import os
import asyncio
import logging
import re
import time
from typing import Any, Dict, Optional
from uuid import uuid4

logger = logging.getLogger("story_app")


def _image_log_context(
    context: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if not context:
        return {}
    return {
        key: context[key]
        for key in (
            "adventure_id",
            "chapter_number",
            "chapter_type",
            "choice_index",
        )
        if context.get(key) is not None
    }


class ImageGenerationService:
    """Service for generating images from text prompts using Gemini."""

    def __init__(self):
        """Initialize Gemini service with the specified model."""
        self.model_name = "gemini-3.1-flash-image"

        api_key = os.getenv("GOOGLE_API_KEY")

        if not api_key:
            logger.warning(
                "GOOGLE_API_KEY is not set in environment variables!"
            )

        # Create a client with the API key
        self.client = genai.Client(api_key=api_key)

    async def generate_image_async(
        self,
        prompt: str,
        retries: int = 5,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Generate image asynchronously and return as base64 string.

        Args:
            prompt: Text description of the image to generate
            retries: Number of retry attempts if generation fails

        Returns:
            Base64 encoded string of the generated image, or None if generation fails
        """
        try:
            # Run in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self._generate_image, prompt, retries, context
            )
        except Exception as e:
            logger.error(f"Image generation failed: {str(e)}")
            return None

    def _generate_image(
        self,
        prompt: str,
        retries: int = 5,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Internal method to call Gemini API.

        Args:
            prompt: Text description of the image to generate
            retries: Number of retry attempts if generation fails

        Returns:
            Base64 encoded string of the generated image, or None if generation fails
        """
        # Validate API key is present
        if not hasattr(self, "client") or not self.client:
            logger.error("Image generation failed: No valid client available")
            return None

        attempt = 0
        last_error = None
        log_context = _image_log_context(context)

        while attempt <= retries:
            llm_call_id = str(uuid4())
            try:
                logger.info(
                    "Gemini image request",
                    extra={
                        "llm_provider": "gemini",
                        "llm_model": self.model_name,
                        "llm_use_case": "image_generation",
                        "llm_call_id": llm_call_id,
                        "llm_prompt": prompt,
                        "llm_prompt_chars": len(prompt),
                        "llm_attempt": attempt + 1,
                        **log_context,
                    },
                )

                # Generate a square 1K image using Nano Banana 2.
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                        image_config=types.ImageConfig(
                            aspect_ratio="1:1",
                            image_size="1K",
                        ),
                    ),
                )

                # Extract image data from response
                image_bytes = None
                for candidate in response.candidates or []:
                    for part in getattr(candidate.content, "parts", None) or []:
                        if part.inline_data and part.inline_data.data:
                            image_bytes = part.inline_data.data
                            break
                    if image_bytes:
                        break

                if image_bytes:
                    try:
                        # Convert to base64
                        # Log essential file size for debug
                        logger.debug(
                            f"Found image data with size: {len(image_bytes)} bytes"
                        )
                        image = Image.open(BytesIO(image_bytes))
                        buffered = BytesIO()
                        image.convert("RGB").save(buffered, format="JPEG")
                        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                        logger.info(
                            "Gemini image response",
                            extra={
                                "llm_provider": "gemini",
                                "llm_model": self.model_name,
                                "llm_use_case": "image_generation",
                                "llm_call_id": llm_call_id,
                                "llm_response_bytes": len(image_bytes),
                                **log_context,
                            },
                        )
                        return img_str
                    except Exception as img_error:
                        logger.error(f"Error processing image data: {str(img_error)}")
                        # Try a different approach if the standard method fails
                        try:
                            # Direct base64 encoding
                            img_str = base64.b64encode(image_bytes).decode("utf-8")
                            logger.info(
                                "Gemini image response",
                                extra={
                                    "llm_provider": "gemini",
                                    "llm_model": self.model_name,
                                    "llm_use_case": "image_generation",
                                    "llm_call_id": llm_call_id,
                                    "llm_response_bytes": len(image_bytes),
                                    "image_encoding_fallback": True,
                                    **log_context,
                                },
                            )
                            return img_str
                        except Exception as alt_error:
                            logger.error(
                                f"Alternative image processing also failed: {str(alt_error)}"
                            )
                            raise

                logger.warning(
                    "Gemini image request returned no image",
                    extra={
                        "llm_provider": "gemini",
                        "llm_model": self.model_name,
                        "llm_use_case": "image_generation",
                        "llm_call_id": llm_call_id,
                        "llm_attempt": attempt + 1,
                        **log_context,
                    },
                )
                # If we got a response but no images, increment attempt and try again
                attempt += 1
                last_error = ValueError(
                    "API returned response but no images were generated"
                )

                if attempt <= retries:
                    backoff_time = 2**attempt
                    logger.info(f"Retrying in {backoff_time} seconds...")
                    time.sleep(backoff_time)
                continue

            except Exception as error:
                logger.exception(
                    "Gemini image request failed",
                    extra={
                        "llm_provider": "gemini",
                        "llm_model": self.model_name,
                        "llm_use_case": "image_generation",
                        "llm_call_id": llm_call_id,
                        "llm_attempt": attempt + 1,
                        "error_type": type(error).__name__,
                        **log_context,
                    },
                )
                last_error = error
                attempt += 1

                if attempt <= retries:
                    # Wait before retry with exponential backoff
                    backoff_time = 2**attempt
                    logger.info(f"Retrying in {backoff_time} seconds...")
                    time.sleep(backoff_time)

        # If we reach here, all attempts failed
        logger.error(f"All {retries + 1} image generation attempts failed for prompt")
        if last_error:
            logger.error(f"Last error: {type(last_error).__name__}: {str(last_error)}")

        return None

    def _lookup_visual_details(self, name):
        """Helper method to look up visual details from categories."""
        # If name is empty or too short, don't attempt lookup
        if not name or len(name.strip()) < 3:
            logger.debug("Name is empty or too short for visual details lookup")
            return ""

        try:
            from app.services.llm.prompt_templates import categories

            # Look for the agency name in all categories
            for category_options in categories.values():
                for option in category_options:
                    option_name = option.split("[")[0].strip().lower()
                    # Use more strict matching to prevent false positives
                    if name.lower() == option_name or (
                        len(name) > 3
                        and name.lower() in option_name
                        and len(name) / len(option_name)
                        > 0.5  # Name must be at least half the length of option
                    ):
                        # Extract visual details from the option
                        option_visual_match = re.search(r"\[(.*?)\]", option)
                        if option_visual_match:
                            logger.debug(
                                f"Found matching visual details for '{name}' in '{option_name}'"
                            )
                            return option_visual_match.group(1)

            # If we get here, no match was found
            logger.debug(f"No matching visual details found for '{name}'")
        except Exception as e:
            logger.error(f"Error looking up visual details: {e}")

        return ""

    async def synthesize_image_prompt(
        self,
        image_scene_description: str,
        protagonist_description: str,
        agency_details: Dict[str, str],
        story_visual_sensory_detail: str,
        character_visuals: Optional[Dict[str, str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Synthesize a coherent image prompt using LLM to combine multiple inputs.

        This function uses Gemini Flash to intelligently combine the protagonist description,
        agency details, scene description, and sensory details into a coherent, optimized
        prompt for image generation.

        Args:
            image_scene_description: A concise summary of the key visual moment in the chapter
            protagonist_description: The base appearance of the main character
            agency_details: Dictionary containing agency category, name, and visual details
            story_visual_sensory_detail: Overall visual mood element for the story's world
            character_visuals: Dictionary of character names and their visual descriptions

        Returns:
            A synthesized prompt string ready for image generation

        Raises:
            Exception: If the LLM call fails or returns invalid content
        """
        try:
            # Import the template from prompt_templates
            from app.services.llm.prompt_templates import IMAGE_SYNTHESIS_PROMPT

            # Log all image synthesis inputs at INFO level for consistent visibility across chapters
            logger.info("\n=== IMAGE SYNTHESIS INPUTS ===")
            logger.debug(f"Scene Description: {image_scene_description}")
            logger.debug(f"Protagonist Description: {protagonist_description}")
            logger.debug(f"Story Visual Sensory Detail: {story_visual_sensory_detail}")

            # Log agency details if available
            if agency_details:
                logger.info("Agency Details:")
                logger.debug(f"- Category: {agency_details.get('category', 'N/A')}")
                logger.debug(f"- Name: {agency_details.get('name', 'N/A')}")
                logger.debug(
                    f"- Visual Details: {agency_details.get('visual_details', 'N/A')}"
                )
            else:
                logger.info("Agency Details: None")

            # Log character visuals
            logger.info("Character Visuals:")
            if character_visuals and len(character_visuals) > 0:
                for name, description in character_visuals.items():
                    logger.debug(f"- {name}: {description}")
            else:
                logger.info("- None available")
            logger.info("================================\n")

            # Format character visuals context
            character_visual_context = ""
            if character_visuals and len(character_visuals) > 0:
                # Format as a list for easier reading
                character_visual_context = "Character Visual Descriptions:\n"
                for name, description in character_visuals.items():
                    character_visual_context += f"- {name}: {description}\n"
            else:
                character_visual_context = "No additional character visuals available"

            # Format the template with the provided inputs
            meta_prompt = IMAGE_SYNTHESIS_PROMPT.format(
                image_scene_description=image_scene_description,
                protagonist_description=protagonist_description,
                agency_category=agency_details.get("category", "N/A"),
                agency_name=agency_details.get("name", "N/A"),
                agency_visual_details=agency_details.get("visual_details", "N/A"),
                story_visual_sensory_detail=story_visual_sensory_detail,
                character_visual_context=character_visual_context,
            )

            # Use Flash Lite for image prompt synthesis
            from app.services.llm.factory import LLMServiceFactory

            llm = LLMServiceFactory.create_for_use_case("image_prompt_synthesis")

            synthesized_prompt = ""
            chunks = []
            response_generator = llm.generate_with_prompt(
                system_prompt="You are a helpful assistant that follows instructions precisely.",
                user_prompt=meta_prompt,
                context={
                    **(context or {}),
                    "skip_paragraph_formatting": True,
                },
            )
            async for chunk in response_generator:
                chunks.append(chunk)
            synthesized_prompt = "".join(chunks).strip()

            # Ensure the prompt is not empty
            if not synthesized_prompt or len(synthesized_prompt) < 10:
                # Use a fallback approach
                fallback_prompt = f"Colorful storybook illustration of this scene: {image_scene_description}. Protagonist: {protagonist_description}. Agency: {agency_details.get('visual_details', '')}. Atmosphere: {story_visual_sensory_detail}."
                logger.info("\n=== USING FALLBACK IMAGE PROMPT ===")
                logger.debug(fallback_prompt)
                logger.info("===================================\n")
                return fallback_prompt

            # Log the synthesized prompt at INFO level
            logger.info("\n=== SYNTHESIZED IMAGE PROMPT ===")
            logger.debug(synthesized_prompt)
            logger.info("===============================\n")

            return synthesized_prompt

        except Exception as e:
            logger.error(f"Error synthesizing image prompt: {str(e)}")
            # Return a fallback prompt
            fallback_prompt = f"Colorful storybook illustration of this scene: {image_scene_description}. Protagonist: {protagonist_description}. Agency: {agency_details.get('visual_details', '')}. Atmosphere: {story_visual_sensory_detail}."

            # Log this fallback prompt too
            logger.info("\n=== USING ERROR FALLBACK IMAGE PROMPT ===")
            logger.debug(fallback_prompt)
            logger.info("========================================\n")

            return fallback_prompt
