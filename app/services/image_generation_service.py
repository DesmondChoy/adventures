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

logger = logging.getLogger("story_app")


class ImageGenerationService:
    """Service for generating images from text prompts using Gemini's Imagen API."""

    def __init__(self):
        """Initialize Gemini service with the specified model."""
        self.model_name = "imagen-3.0-generate-002"
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("GOOGLE_API_KEY is not set in environment variables!")

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
        attempt = 0
        while attempt <= retries:
            try:
                logger.info(f"Generating image for prompt: {prompt}")
                logger.debug("\n=== DEBUG: Image Generation Request ===")
                logger.debug(f"Prompt: {prompt}")
                logger.debug(f"Model: {self.model_name}")
                logger.debug("========================\n")

                # Generate image using the client's models interface
                response = self.client.models.generate_images(
                    model=self.model_name,
                    prompt=prompt,
                    config=GenerateImagesConfig(number_of_images=1),
                )

                # Log response structure for debugging
                logger.debug("\n=== DEBUG: Image Generation Response ===")
                logger.debug(f"Response type: {type(response)}")
                # logger.debug(f"Response attributes: {dir(response)}")
                if (
                    hasattr(response, "generated_images")
                    and response.generated_images is not None
                ):
                    logger.debug(
                        f"Generated images count: {len(response.generated_images)}"
                    )
                    if response.generated_images:
                        logger.debug(
                            f"First image type: {type(response.generated_images[0])}"
                        )
                        # logger.debug(
                        #     f"First image attributes: {dir(response.generated_images[0])}"
                        # )
                else:
                    logger.debug("No generated_images attribute or it is None")
                logger.debug("========================\n")

                # Extract image data from response
                if response.generated_images:
                    # Convert to base64
                    image_bytes = response.generated_images[0].image.image_bytes
                    logger.debug(
                        f"Found image data with size: {len(image_bytes)} bytes"
                    )
                    image = Image.open(BytesIO(image_bytes))
                    buffered = BytesIO()
                    image.save(buffered, format="JPEG")
                    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                    logger.info(f"Successfully generated image for prompt: {prompt}")
                    return img_str
                logger.warning(f"No images generated for prompt: {prompt}")
                return None
            except Exception as e:
                logger.error(f"Image generation attempt {attempt + 1} failed: {str(e)}")
                attempt += 1
                if attempt <= retries:
                    # Wait before retry with exponential backoff
                    backoff_time = 2**attempt
                    logger.info(f"Retrying in {backoff_time} seconds...")
                    time.sleep(backoff_time)

        return None

    def enhance_prompt(self, original_prompt, adventure_state=None, choice_text=None):
        """Streamlined prompt enhancement with updated order of elements.

        Args:
            original_prompt: The basic text prompt
            adventure_state: Optional AdventureState object containing story elements
            choice_text: Optional text of the selected choice to include in the prompt

        Returns:
            Enhanced prompt with elements in the specified order
        """
        # Extract the combined name and visual details up to the closing bracket
        name_with_details = ""
        full_bracket_match = re.match(r"(.*?\])", original_prompt)
        if full_bracket_match:
            name_with_details = full_bracket_match.group(1).strip()
            logger.debug(f"Extracted name with visual details: {name_with_details}")
        else:
            # Fallback to just extracting the name if no bracket is found
            name = original_prompt.split(" - ")[0].strip()

            # Handle agency name extraction from choice text if needed
            if re.match(r"(?:[^:]+):\s*([^-]+)", name):
                agency_name = re.match(r"(?:[^:]+):\s*([^-]+)", name).group(1).strip()
                logger.debug(f"Extracted agency name from choice text: {agency_name}")
                name = agency_name
            elif re.match(r"As a (\w+\s*\w*)", name):
                as_a_match = re.match(r"As a (\w+\s*\w*)", name)
                agency_name = as_a_match.group(1).strip()
                logger.debug(
                    f"Extracted agency name from legacy 'As a' format: {agency_name}"
                )
                name = agency_name

            name_with_details = name
            logger.debug(f"Using name without visual details: {name}")

            # Try to look up visual details for this name
            visual_details = self._lookup_visual_details(name)
            if visual_details:
                name_with_details = f"{name} [{visual_details}]"
                logger.debug(f"Added visual details from lookup: {visual_details}")

        # Base style guidance
        base_style = "vibrant colors, detailed, whimsical, digital art"

        # Build components in the specified order
        components = []

        # 1. Start with "Fantasy illustration of [Agency Name with Visual Details]"
        components.append(f"Fantasy illustration of {name_with_details}")

        # 2. Add story name if available
        story_name = ""
        if (
            adventure_state
            and hasattr(adventure_state, "metadata")
            and "non_random_elements" in adventure_state.metadata
        ):
            story_name = adventure_state.metadata["non_random_elements"].get("name", "")
            if story_name:
                components.append(f"in {story_name}")
                logger.debug(f"Added story name: {story_name}")

        # 3. Add sensory details from adventure state if available
        if adventure_state and hasattr(adventure_state, "selected_sensory_details"):
            visual = adventure_state.selected_sensory_details.get("visuals", "")
            if visual:
                components.append(f"with {visual}")
                logger.debug(f"Added sensory details: {visual}")

        # 4. Add base style
        components.append(base_style)

        # Join all components with commas
        prompt = ", ".join(components)
        logger.info(f"Enhanced prompt: {prompt}")
        return prompt

    def _lookup_visual_details(self, name):
        """Helper method to look up visual details from categories."""
        try:
            from app.services.llm.prompt_templates import categories

            # Look for the agency name in all categories
            for category_options in categories.values():
                for option in category_options:
                    option_name = option.split("[")[0].strip().lower()
                    if name.lower() == option_name or name.lower() in option_name:
                        # Extract visual details from the option
                        option_visual_match = re.search(r"\[(.*?)\]", option)
                        if option_visual_match:
                            return option_visual_match.group(1)
        except Exception as e:
            logger.error(f"Error looking up visual details: {e}")

        return ""
