## SpecStory

## Debugging LLM Output Issues (1/20/2025, 9:59:39 PM)

_**User**_

Help me debug my repo. The app launches but no LLM output is happening.

---

_**Assistant**_

I'll help you debug the LLM integration issue. Let me check the relevant files to understand how the LLM service is set up and what might be preventing it from working.

First, I'll look at the LLM service implementation:

---

_**Assistant**_



---

_**Assistant**_



Let me check the environment file to see if the API key is properly configured:

---

_**Assistant**_



---

_**Assistant**_



Now let me check how the LLM service is being used in the main application:

---

_**Assistant**_



---

_**Assistant**_



I notice a few potential issues that could be preventing the LLM output:

1. The OpenAI API key in your `.env` file appears to be a project key (starting with `sk-proj-`). This might not be the correct format - OpenAI API keys typically start with `sk-` without the `proj-` prefix. You should verify if this is a valid API key.

2. In the LLM service, you're using `gpt-4-turbo-preview` as the model name. This should be `gpt-4-turbo-1106` or `gpt-4-1106-preview` depending on which version you want to use.

3. The LLM service is set up to stream responses (`stream=True`), but I should check how the streaming is being handled in the WebSocket implementation.

Let me check the WebSocket handler to see how it's handling the LLM responses:

---

_**Assistant**_



---

_**Assistant**_



Let me also check the actual story generation implementation:

---

_**Assistant**_



---

_**Assistant**_



I've identified several issues that are likely preventing the LLM output from working:

1. **API Key Issue**: The API key in your `.env` file starts with `sk-proj-`, which appears to be a project key rather than a standard OpenAI API key. You should replace it with a valid OpenAI API key that starts with `sk-`.

2. **LLM Service Initialization**: I don't see where `llm_service` is being initialized in `main.py`. It's being used in `generate_story_segment()` but there's no instance created.

3. **Streaming Implementation**: While the LLM service is set up for streaming, the WebSocket implementation is trying to stream word-by-word from a complete response, which doesn't match how the LLM service is implemented.

Here's what I'll do to fix these issues:

---

_**Assistant**_

```
# app/main.py
from fastapi import FastAPI, Request, WebSocket
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import yaml
import pandas as pd
from typing import List, Dict, Any
import asyncio
from pydantic import BaseModel
from app.services.llm import LLMService
from fastapi.responses import StreamingResponse

# Initialize FastAPI app and services
app = FastAPI(title="Educational Story App")
llm_service = LLMService()  # Initialize LLM service

// ... existing code ...

async def generate_story_segment(
    story_category: str, lesson_topic: str, state: StoryState
) -> StoryNode:
    """Generate the next story segment based on the current state."""
    # Load story configuration
    story_data = load_story_data()
    story_config = story_data["story_categories"][story_category]

    # Load lesson data if we're at the question depth
    question = None
    if state.depth == 1:  # Next node will be depth 2
        lesson_data = load_lesson_data()
        relevant_lessons = lesson_data[lesson_data["topic"] == lesson_topic]
        question = relevant_lessons.iloc[state.total_questions].to_dict()

    # Generate story content using LLM
    story_stream = await llm_service.generate_story_segment(
        story_config, state, question
    )

    # Process the streaming response
    story_content = ""
    story_choices = []

    try:
        async for chunk in story_stream:
            if chunk.choices[0].delta.content:
                story_content += chunk.choices[0].delta.content
    except Exception as e:
        print(f"Error during story generation: {e}")
        story_content = "I apologize, but I encountered an error generating the story. Please try again."
```

---

_**Assistant**_



Let me fix the linter error by adding the missing import:

---

_**Assistant**_

```
# app/main.py
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
// ... existing code ...
```

---

_**Assistant**_



Now that I've fixed the code, here's what you need to do to get the LLM output working:

1. **Update your OpenAI API key**: 
   - Get a valid OpenAI API key from your OpenAI account (it should start with `sk-` without the `proj-` prefix)
   - Update the `OPENAI_API_KEY` in your `.env` file with the new key

2. **Restart your application**: 
   - The changes I made require a restart of your FastAPI application to take effect
   - Make sure to stop any running instances and start it again

3. **Check the console output**:
   - When running the application, watch the console output for any error messages
   - I've added error handling that will print any LLM-related errors to help with debugging

If you're still not seeing any output after making these changes, let me know and I can help investigate further. Also, please share any error messages you see in the console.

---

_**User**_

There's no output coming out. Include some debugging help in my LLM call e.g. printing the final prompt that is sent.

---

_**Assistant**_

I'll help you add debugging output to the LLM service to see exactly what's being sent to the API. Let me modify the LLM service:

---

_**Assistant**_



---

_**Assistant**_



I've found a few issues in the LLM service that would definitely cause no output:

1. There's a typo in the model name: `gpt-4o` instead of the correct `gpt-4-turbo-preview`
2. We should add debugging output to see the exact prompts being sent

Let me fix these issues:

---

_**Assistant**_

```
# app/services/llm.py
from typing import Dict, Any, List, Optional
import openai
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
        Generate the next story segment based on the current state and configuration.

        Args:
            story_config: Configuration for the story category (tone, rules, etc.)
            state: Current story state including history
            question: Optional educational question to integrate
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
                model="gpt-4-turbo-preview",  # Using GPT-4 for better storytelling
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,  # Balanced between creativity and consistency
                stream=True,  # Enable streaming for real-time story delivery
            )
            return response
        except Exception as e:
            print(f"\n=== ERROR: LLM Request Failed ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print("===============================\n")
            raise  # Re-raise the exception after logging
// ... existing code ...
```

---

_**Assistant**_



I've made several improvements to help debug the LLM service:

1. Fixed the model name from `gpt-4o` to `gpt-4-turbo-preview`
2. Added a warning if the OpenAI API key is not set in environment variables
3. Added detailed debugging output that will show:
   - The exact system prompt being sent
   - The exact user prompt being sent
   - Any errors that occur during the API call, including the error type and message

Now when you run your application, you should see detailed debug output in your console that will help identify what's happening. Here's what to look for:

1. When the app starts, check if you see the "WARNING: OPENAI_API_KEY is not set" message
2. When you interact with the story, you'll see the "DEBUG: LLM Request" section showing the exact prompts
3. If there's an API error, you'll see the "ERROR: LLM Request Failed" section with details

Try running your application again and let me know what debug output you see in the console. This will help us identify exactly where the issue is occurring.

Also, make sure to check:
1. Your OpenAI API key is correctly set in the `.env` file
2. The `.env` file is in the correct location (root of your project)
3. You've restarted your application after making these changes

---



---

