import google.generativeai as genai
from google.generativeai import types
from PIL import Image
from io import BytesIO
import base64
import os
import asyncio
import logging
import time

logger = logging.getLogger("story_app")


class ImageGenerationService:
    """Service for generating images from text prompts using Gemini's Imagen API."""

    def __init__(self):
        """Initialize Gemini service with the specified model."""
        self.model = "imagen-3.0-generate-002"
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("GOOGLE_API_KEY is not set in environment variables!")
        genai.configure(api_key=api_key)

    async def generate_image_async(self, prompt, retries=2):
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

    def _generate_image(self, prompt, retries=2):
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
                logger.debug(f"Model: {self.model}")
                logger.debug("========================\n")

                # Generate image using the configured API
                response = genai.generate_images(
                    model=self.model,
                    prompt=prompt,
                    generation_config=types.GenerateImagesConfig(
                        number_of_images=1,
                    ),
                )

                if response.images:
                    # Convert to base64
                    image = Image.open(BytesIO(response.images[0].bytes))
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

    def enhance_prompt(self, original_prompt):
        """Enhance a basic prompt to get better image generation results.

        Args:
            original_prompt: The basic text prompt

        Returns:
            Enhanced prompt with style guidance
        """
        # Add style guidance for better, more consistent results
        return f"Fantasy illustration of {original_prompt} in a children's storybook style, vibrant colors, detailed, whimsical, digital art"
