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
        """Enhance a basic prompt to get better image generation results.

        Args:
            original_prompt: The basic text prompt
            adventure_state: Optional AdventureState object containing story elements
            choice_text: Optional text of the selected choice to include in the prompt

        Returns:
            Enhanced prompt with style guidance and story elements
        """
        # Extract only the name (everything before the first " - " or "[")
        name = original_prompt.split(" - ")[0].split("[")[0].strip()

        # Extract visual details from square brackets if present
        visual_details = ""
        bracket_match = re.search(r"\[(.*?)\]", original_prompt)
        if bracket_match:
            visual_details = bracket_match.group(1)
            logger.debug(f"Extracted visual details: {visual_details}")

        # Check if the name is actually a full choice text starting with "As a..."
        # This happens when the choice text is passed as original_prompt
        as_a_match = re.match(r"As a (\w+\s*\w*)", name)
        if as_a_match:
            # Extract just the agency name from the choice text
            agency_name = as_a_match.group(1).strip()
            logger.debug(f"Extracted agency name from choice text: {agency_name}")
            name = agency_name

        logger.debug(f"Using name for prompt: {name}")

        # Base style guidance
        base_style = "vibrant colors, detailed, whimsical, digital art"

        # If adventure_state is provided, incorporate setting and visual details
        if (
            adventure_state
            and hasattr(adventure_state, "selected_narrative_elements")
            and hasattr(adventure_state, "selected_sensory_details")
        ):
            # Extract setting and visual details if available
            setting = adventure_state.selected_narrative_elements.get(
                "setting_types", ""
            )
            visual = adventure_state.selected_sensory_details.get("visuals", "")

            # Build prompt components with proper comma separation
            components = []

            # Start with the name and visual details
            if visual_details:
                # Use proper formatting for visual details in square brackets
                components.append(f"Fantasy illustration of {name} [{visual_details}]")
            else:
                # If no visual details found in the original prompt, try to find them in the agency lookup
                from app.services.llm.prompt_templates import categories

                try:
                    # Look for the agency name in all categories
                    for category_options in categories.values():
                        for option in category_options:
                            option_name = option.split("[")[0].strip().lower()
                            if (
                                name.lower() == option_name
                                or name.lower() in option_name
                            ):
                                # Extract visual details from the option
                                option_visual_match = re.search(r"\[(.*?)\]", option)
                                if option_visual_match:
                                    option_visual_details = option_visual_match.group(1)
                                    logger.debug(
                                        f"Found visual details from categories: {option_visual_details}"
                                    )
                                    components.append(
                                        f"Fantasy illustration of {name} [{option_visual_details}]"
                                    )
                                    break
                        else:
                            continue
                        break
                    else:
                        # If no match found, use just the name
                        components.append(f"Fantasy illustration of {name}")
                except Exception as e:
                    logger.error(f"Error looking up visual details: {e}")
                    components.append(f"Fantasy illustration of {name}")

            # Add the choice text directly if provided
            if choice_text:
                # Clean up the choice text (remove "Choice X: " prefix if present)
                if choice_text.startswith("Choice ") and ": " in choice_text:
                    clean_choice = choice_text.split(": ", 1)[1]
                else:
                    clean_choice = choice_text
                components.append(clean_choice)

            if setting:
                components.append(f"in a {setting} setting")

            if visual:
                components.append(f"with {visual}")

            components.append(base_style)

            # Join all components with commas
            return ", ".join(components)

        # Default enhancement if no adventure_state is provided
        components = []

        # Start with the name and visual details
        if visual_details:
            components.append(f"Fantasy illustration of {name} [{visual_details}]")
        else:
            components.append(f"Fantasy illustration of {name}")

        # Add the choice text directly if provided
        if choice_text:
            # Clean up the choice text (remove "Choice X: " prefix if present)
            if choice_text.startswith("Choice ") and ": " in choice_text:
                clean_choice = choice_text.split(": ", 1)[1]
            else:
                clean_choice = choice_text
            components.append(clean_choice)

        components.append(base_style)
        return ", ".join(components)
