from google import genai
from google.genai.types import GenerateImagesConfig
from PIL import Image
from io import BytesIO
import base64
import os
import asyncio
import logging
import re
import time
from typing import Dict, Optional
from app.services.llm import LLMService

logger = logging.getLogger("story_app")


class ImageGenerationService:
    """Service for generating images from text prompts using Gemini's Imagen API."""

    def __init__(self):
        """Initialize Gemini service with the specified model."""
        self.model_name = "imagen-3.0-generate-002"

        # First try to load from environment variables
        api_key = os.getenv("GOOGLE_API_KEY")

        # If not found in environment, try loading from .env file
        if not api_key:
            try:
                # Try to manually read from .env file
                with open(".env", "r") as env_file:
                    for line in env_file:
                        if line.startswith("GOOGLE_API_KEY="):
                            api_key = line.strip().split("=", 1)[1]
                            # Remove quotes if present
                            api_key = api_key.strip("'\"")
                            logger.info(
                                "Successfully loaded GOOGLE_API_KEY from .env file"
                            )
                            break
            except Exception as e:
                logger.error(f"Error loading API key from .env file: {str(e)}")

        if not api_key:
            logger.warning(
                "GOOGLE_API_KEY is not set in environment variables or .env file!"
            )

        # Create a client with the API key
        self.client = genai.Client(api_key=api_key)

    async def generate_image_async(self, prompt, retries=5):
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
                None, self._generate_image, prompt, retries
            )
        except Exception as e:
            logger.error(f"Image generation failed: {str(e)}")
            return None

    def _generate_image(self, prompt, retries=5):
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

        while attempt <= retries:
            try:
                # Only log the complete prompt and model/attempt info - essential for debugging
                logger.info("\n" + "=" * 50)
                logger.info("COMPLETE IMAGE PROMPT SENT TO MODEL:")
                logger.info(f"{prompt}")
                logger.info(
                    f"Model: {self.model_name} | Attempt: {attempt + 1}/{retries + 1}"
                )
                logger.info("=" * 50 + "\n")

                # Generate image using the client's models interface
                response = self.client.models.generate_images(
                    model=self.model_name,
                    prompt=prompt,
                    config=GenerateImagesConfig(number_of_images=1),
                )

                # Extract image data from response
                if response.generated_images:
                    try:
                        # Convert to base64
                        image_bytes = response.generated_images[0].image.image_bytes
                        # Log essential file size for debug
                        logger.debug(
                            f"Found image data with size: {len(image_bytes)} bytes"
                        )
                        image = Image.open(BytesIO(image_bytes))
                        buffered = BytesIO()
                        image.save(buffered, format="JPEG")
                        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                        logger.info(
                            f"Successfully generated image for prompt: {prompt[:50]}..."
                        )
                        return img_str
                    except Exception as img_error:
                        logger.error(f"Error processing image data: {str(img_error)}")
                        # Try a different approach if the standard method fails
                        try:
                            # Direct base64 encoding
                            img_str = base64.b64encode(image_bytes).decode("utf-8")
                            logger.info(
                                f"Successfully generated image using alternative method"
                            )
                            return img_str
                        except Exception as alt_error:
                            logger.error(
                                f"Alternative image processing also failed: {str(alt_error)}"
                            )
                            raise

                logger.warning(f"No images generated for prompt (attempt {attempt + 1}/{retries + 1})")
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

            except Exception as e:
                logger.error(f"Image generation attempt {attempt + 1} failed: {str(e)}")
                last_error = e
                attempt += 1

                if attempt <= retries:
                    # Wait before retry with exponential backoff
                    backoff_time = 2**attempt
                    logger.info(f"Retrying in {backoff_time} seconds...")
                    time.sleep(backoff_time)

        # If we reach here, all attempts failed
        logger.error(
            f"All {retries + 1} image generation attempts failed for prompt"
        )
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
        character_visuals: Dict[str, str] = None,
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

            # Use LLMService to call Gemini Flash
            llm = LLMService()

            # Check if we're using Gemini or OpenAI
            is_gemini = (
                isinstance(llm, LLMService) or "Gemini" in llm.__class__.__name__
            )

            synthesized_prompt = ""
            # For Gemini, use a direct approach instead of streaming
            if is_gemini:
                try:
                    # Initialize the model with system prompt
                    from google import generativeai as genai

                    # Use Gemini Flash
                    model_name = "gemini-2.0-flash"
                    model = genai.GenerativeModel(
                        model_name=model_name,
                        system_instruction="You are a helpful assistant that follows instructions precisely.",
                    )

                    # Generate content without streaming
                    response = model.generate_content(meta_prompt)

                    # Extract the text directly
                    synthesized_prompt = response.text.strip()
                except Exception as e:
                    logger.error(f"Error with direct Gemini call: {str(e)}")
                    # Fallback to streaming approach
                    logger.info("Falling back to LLMService")

                    chunks = []

                    # Create a minimal AdventureState-like object with just what we need
                    class MinimalState:
                        def __init__(self):
                            self.current_chapter_id = "image_prompt_synthesis"
                            self.story_length = 1
                            self.chapters = []
                            self.metadata = {"prompt_override": True}

                    async for chunk in llm.generate_chapter_stream(
                        story_config={},
                        state=MinimalState(),
                        question=None,
                        previous_lessons=None,
                        context={"prompt_override": meta_prompt},
                    ):
                        chunks.append(chunk)
                    synthesized_prompt = "".join(chunks).strip()
            else:
                # For OpenAI, use the streaming approach
                chunks = []

                # Create a minimal AdventureState-like object with just what we need
                class MinimalState:
                    def __init__(self):
                        self.current_chapter_id = "image_prompt_synthesis"
                        self.story_length = 1
                        self.chapters = []
                        self.metadata = {"prompt_override": True}

                async for chunk in llm.generate_chapter_stream(
                    story_config={},
                    state=MinimalState(),
                    question=None,
                    previous_lessons=None,
                    context={"prompt_override": meta_prompt},
                ):
                    chunks.append(chunk)
                synthesized_prompt = "".join(chunks).strip()

            # Ensure the prompt is not empty
            if not synthesized_prompt or len(synthesized_prompt) < 10:
                # Use a fallback approach
                fallback_prompt = f"Colorful storybook illustration of this scene: {image_scene_description}. Protagonist: {protagonist_description}. Agency: {agency_details.get('visual_details', '')}. Atmosphere: {story_visual_sensory_detail}."
                return fallback_prompt

            return synthesized_prompt

        except Exception as e:
            logger.error(f"Error synthesizing image prompt: {str(e)}")
            # Return a fallback prompt
            fallback_prompt = f"Colorful storybook illustration of this scene: {image_scene_description}. Protagonist: {protagonist_description}. Agency: {agency_details.get('visual_details', '')}. Atmosphere: {story_visual_sensory_detail}."
            return fallback_prompt
