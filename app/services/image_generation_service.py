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
                logger.info(f"Generating image for prompt: {prompt}")
                logger.debug("\n=== DEBUG: Image Generation Request ===")
                logger.debug(f"Prompt: {prompt}")
                logger.debug(f"Model: {self.model_name}")
                logger.debug(f"Attempt: {attempt + 1}/{retries + 1}")
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
                else:
                    logger.debug("No generated_images attribute or it is None")
                    logger.debug(f"Response details: {response}")
                logger.debug("========================\n")

                # Extract image data from response
                if response.generated_images:
                    try:
                        # Convert to base64
                        image_bytes = response.generated_images[0].image.image_bytes
                        logger.debug(
                            f"Found image data with size: {len(image_bytes)} bytes"
                        )
                        image = Image.open(BytesIO(image_bytes))
                        buffered = BytesIO()
                        image.save(buffered, format="JPEG")
                        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                        logger.info(
                            f"Successfully generated image for prompt: {prompt}"
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

                logger.warning(f"No images generated for prompt: {prompt}")
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
                logger.error(f"Error type: {type(e).__name__}")
                last_error = e
                attempt += 1

                if attempt <= retries:
                    # Wait before retry with exponential backoff
                    backoff_time = 2**attempt
                    logger.info(f"Retrying in {backoff_time} seconds...")
                    time.sleep(backoff_time)

        # If we reach here, all attempts failed
        logger.error(
            f"All {retries + 1} image generation attempts failed for prompt: {prompt}"
        )
        if last_error:
            logger.error(f"Last error: {type(last_error).__name__}: {str(last_error)}")

        # Return a fallback image for testing if needed
        # Uncomment the following code to provide a fallback test image
        # try:
        #     logger.warning("Using fallback test image")
        #     with open('app/static/images/fallback_image.jpg', 'rb') as img_file:
        #         return base64.b64encode(img_file.read()).decode('utf-8')
        # except Exception as fallback_error:
        #     logger.error(f"Fallback image also failed: {str(fallback_error)}")

        return None

    def enhance_prompt(
        self,
        original_prompt,
        adventure_state=None,
        choice_text=None,
        chapter_summary=None,
    ):
        """Streamlined prompt enhancement with updated order of elements.

        Args:
            original_prompt: The basic text prompt
            adventure_state: Optional AdventureState object containing story elements
            choice_text: Optional text of the selected choice to include in the prompt
            chapter_summary: Optional summary of the current chapter for non-first chapters

        Returns:
            Enhanced prompt with elements in the specified order
        """
        # Base style guidance
        base_style = "vibrant colors, detailed, whimsical, digital art"

        # Build components in the specified order
        components = []

        # Log all input parameters for debugging
        logger.debug(f"enhance_prompt called with:")
        logger.debug(f"  original_prompt: '{original_prompt}'")
        logger.debug(f"  chapter_summary: '{chapter_summary}'")
        if adventure_state:
            logger.debug(
                f"  adventure_state: present with {len(getattr(adventure_state, 'chapters', []))} chapters"
            )
            if (
                hasattr(adventure_state, "metadata")
                and "agency" in adventure_state.metadata
            ):
                logger.debug(
                    f"  agency: {adventure_state.metadata['agency'].get('description', 'None')}"
                )

        # If we have a chapter summary, use that as the main subject
        if chapter_summary:
            logger.debug(f"Using chapter summary in prompt: '{chapter_summary}'")
            # Ensure chapter_summary is not empty or just whitespace
            if chapter_summary and chapter_summary.strip():
                components.append(
                    f"Colorful storybook illustration of this scene: {chapter_summary}"
                )
                logger.debug(f"Added chapter summary to components")
            else:
                logger.warning("Chapter summary is empty or whitespace only")
                # Use a fallback approach - add a generic component
                components.append(
                    "Colorful storybook illustration of a scene from the story"
                )
                logger.debug("Added generic scene component as fallback")
        else:
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
                    agency_name = (
                        re.match(r"(?:[^:]+):\s*([^-]+)", name).group(1).strip()
                    )
                    logger.debug(
                        f"Extracted agency name from choice text: {agency_name}"
                    )
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

            # Start with "Colorful storybook illustration of this scene: [Agency Name with Visual Details]"
            components.append(
                f"Colorful storybook illustration of this scene: {name_with_details}"
            )

        # Add agency information from adventure state regardless of chapter type
        if (
            adventure_state
            and hasattr(adventure_state, "metadata")
            and "agency" in adventure_state.metadata
        ):
            agency = adventure_state.metadata["agency"]
            agency_description = agency.get("description", "")
            agency_visual_details = agency.get("visual_details", "")
            agency_category = agency.get("category", "")

            if agency_description:
                # Extract just the agency name/item without extra details
                agency_name = (
                    agency_description.split(" - ")[0].strip()
                    if " - " in agency_description
                    else agency_description
                )
                if ":" in agency_name:
                    agency_name = agency_name.split(":", 1)[1].strip()

                # If we don't have visual details stored, try to look them up
                if not agency_visual_details:
                    agency_visual_details = self._lookup_visual_details(agency_name)

                # Add appropriate prefix based on agency category
                if agency_category == "Choose a Companion":
                    prefix = "He/she is accompanied by"
                elif agency_category == "Take on a Profession":
                    prefix = "He/she is a"
                elif agency_category == "Gain a Special Ability":
                    prefix = "He/she has the power of"
                elif agency_category == "Craft a Magical Artifact":
                    prefix = "He/she carries a magical"
                else:
                    prefix = "He/she has"

                if agency_visual_details:
                    components.append(
                        f"{prefix} {agency_name} ({agency_visual_details})"
                    )
                else:
                    components.append(f"{prefix} {agency_name}")

                logger.debug(
                    f"Added agency to chapter image with prefix '{prefix}': {agency_name}"
                )
                if agency_visual_details:
                    logger.debug(f"Added visual details: {agency_visual_details}")

        # Join components with appropriate separators
        if len(components) >= 2:
            # Join the first component (illustration) with the second component (agency)
            # using a period instead of a comma
            prompt = f"{components[0]}. {components[1]}"
        else:
            # If there's only one component, just use that
            prompt = components[0]

        # No longer adding base style

        logger.info(f"Enhanced prompt: {prompt}")
        return prompt

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
