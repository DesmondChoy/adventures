# WebSocket Disconnection Fix

## Problem

Users are experiencing WebSocket disconnection errors during chapter transitions, specifically between chapters five and six. The error appears in the logs as:

```
Error generating chapter: 

ERROR:    Exception in ASGI application

Traceback (most recent call last):
  File "/usr/local/lib/python3.11/site-packages/uvicorn/protocols/websockets/websockets_impl.py", line 331, in asgi_send
    await self.send(data)  # type: ignore[arg-type]
    ^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.11/site-packages/websockets/legacy/protocol.py", line 620, in send
    await self.ensure_open()
  File "/usr/local/lib/python3.11/site-packages/websockets/legacy/protocol.py", line 930, in ensure_open
    raise self.connection_closed_exc()
websockets.exceptions.ConnectionClosedOK: received 1005 (no status received [internal]); then sent 1005 (no status received [internal])
```

This is followed by a `RuntimeError: Cannot call "send" once a close message has been sent` exception.

## Diagnosis

After analyzing the codebase, I've identified the following issues:

1. **Missing Connection State Checks**: The WebSocket streaming functions in `stream_handler.py` don't check if the connection is still open before sending data.

2. **Inadequate Error Handling**: The streaming functions lack proper exception handling for WebSocket disconnections that occur during streaming.

3. **Continued Streaming After Disconnection**: When a client disconnects during streaming, the server continues to attempt sending data chunks over the closed connection.

4. **No Graceful Termination**: There's no mechanism to gracefully terminate streaming operations when a disconnection is detected.

5. **Critical Timing Issue**: The issue occurs specifically between chapters five and six, suggesting a potential timing or resource-related problem during this transition.

## Implementation Plan

### 1. Create a WebSocket Connection Checker Utility

Add a utility function to check if a WebSocket connection is still open before attempting to send data:

```python
# app/services/websocket/utils.py
from fastapi import WebSocket
import logging

logger = logging.getLogger("story_app")

async def is_connection_open(websocket: WebSocket) -> bool:
    """Check if a WebSocket connection is still open.
    
    Args:
        websocket: The WebSocket connection to check
        
    Returns:
        bool: True if the connection is open, False otherwise
    """
    try:
        # The most reliable way to check if a connection is open is to try a small ping
        # But since FastAPI's WebSocket doesn't expose a direct ping method,
        # we'll check the client's state indirectly
        
        # Check if the WebSocket has a client attribute and it's not None
        if not hasattr(websocket, "client") or websocket.client is None:
            logger.debug("WebSocket connection closed: client attribute is None")
            return False
            
        # Check if the WebSocket has been closed
        if hasattr(websocket, "client_state") and websocket.client_state.name == "DISCONNECTED":
            logger.debug("WebSocket connection closed: client_state is DISCONNECTED")
            return False
            
        # If we can't determine the state, assume it's open
        return True
    except Exception as e:
        logger.error(f"Error checking WebSocket connection state: {str(e)}")
        # If we encounter an error while checking, assume the connection is closed
        return False
```

### 2. Modify Stream Handler Functions

Update the streaming functions in `app/services/websocket/stream_handler.py` to check connection state and handle disconnections gracefully:

#### a. Update `stream_text_content` function:

```python
async def stream_text_content(content: str, websocket: WebSocket) -> None:
    """Stream chapter content word by word to the client."""
    from .utils import is_connection_open
    
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

    for i, paragraph in enumerate(paragraphs):
        # Check if connection is still open before processing each paragraph
        if not await is_connection_open(websocket):
            logger.warning("WebSocket connection closed during text streaming - stopping stream")
            return
            
        # [existing code for dialogue pattern checks]

        # Check if paragraph starts with dialogue (quotation mark)
        if paragraph.strip().startswith('"'):
            # For paragraphs starting with dialogue, handle differently to preserve opening quotes
            words = paragraph.split()
            if len(words) > 0:
                # Find the first word with the quotation mark
                first_word = words[0]

                # Check connection before sending first word
                if not await is_connection_open(websocket):
                    logger.warning("WebSocket connection closed during text streaming - stopping stream")
                    return
                    
                # Send the first word with its quotation mark intact
                try:
                    await websocket.send_text(first_word + " ")
                    await asyncio.sleep(WORD_DELAY)
                except Exception as e:
                    logger.error(f"Error sending text: {str(e)}")
                    return  # Stop streaming if we encounter an error

                # Then stream the rest of the words normally
                for word in words[1:]:
                    # Check connection before sending each word
                    if not await is_connection_open(websocket):
                        logger.warning("WebSocket connection closed during text streaming - stopping stream")
                        return
                        
                    try:
                        await websocket.send_text(word + " ")
                        await asyncio.sleep(WORD_DELAY)
                    except Exception as e:
                        logger.error(f"Error sending text: {str(e)}")
                        return  # Stop streaming if we encounter an error
            else:
                # Fallback if splitting doesn't work as expected
                if not await is_connection_open(websocket):
                    return
                    
                try:
                    await websocket.send_text(paragraph)
                    await asyncio.sleep(PARAGRAPH_DELAY)
                except Exception as e:
                    logger.error(f"Error sending text: {str(e)}")
                    return
        else:
            # For non-dialogue paragraphs, stream normally word by word
            words = paragraph.split()
            for word in words:
                # Check connection before sending each word
                if not await is_connection_open(websocket):
                    logger.warning("WebSocket connection closed during text streaming - stopping stream")
                    return
                    
                try:
                    await websocket.send_text(word + " ")
                    await asyncio.sleep(WORD_DELAY)
                except Exception as e:
                    logger.error(f"Error sending text: {str(e)}")
                    return  # Stop streaming if we encounter an error

        # Check connection before sending paragraph break
        if not await is_connection_open(websocket):
            logger.warning("WebSocket connection closed during text streaming - stopping stream")
            return
            
        try:
            await websocket.send_text("\n\n")
            await asyncio.sleep(PARAGRAPH_DELAY)
        except Exception as e:
            logger.error(f"Error sending text: {str(e)}")
            return  # Stop streaming if we encounter an error
```

#### b. Update `stream_conclusion_content` function:

Apply similar changes to the `stream_conclusion_content` function, adding connection checks and error handling.

#### c. Update `stream_summary_content` function:

Apply similar changes to the `stream_summary_content` function, adding connection checks and error handling.

#### d. Update `send_chapter_data` function:

```python
async def send_chapter_data(
    content_to_stream: str,
    chapter_content: ChapterContent,
    chapter_type: ChapterType,
    chapter_number: int,
    sampled_question: Optional[Dict[str, Any]],
    state: AdventureState,
    websocket: WebSocket
) -> None:
    """Send complete chapter data to the client."""
    from .utils import is_connection_open
    
    # Check connection before sending chapter data
    if not await is_connection_open(websocket):
        logger.warning("WebSocket connection closed before sending chapter data - aborting")
        return
        
    chapter_data = {
        "type": "chapter_update",
        "state": {
            "current_chapter_id": state.current_chapter_id,
            "current_chapter": {
                "chapter_number": chapter_number,
                "content": content_to_stream,
                "chapter_type": chapter_type.value,  # Add chapter type to response
                "chapter_content": {
                    "content": chapter_content.content,
                    "choices": [
                        {"text": choice.text, "next_chapter": choice.next_chapter}
                        for choice in chapter_content.choices
                    ],
                },
                "question": sampled_question,
            },
            # Include chapter_summaries in the response for simulation logging
            "chapter_summaries": state.chapter_summaries,
        },
    }
    logger.debug("\n=== DEBUG: Chapter Update Message ===")
    logger.debug(f"Chapter number: {chapter_number}")
    logger.debug(f"Chapter type: {chapter_type.value}")
    logger.debug(f"Has question: {sampled_question is not None}")
    logger.debug("===================================\n")
    
    try:
        await websocket.send_json(chapter_data)
    except Exception as e:
        logger.error(f"Error sending chapter data: {str(e)}")
        # Don't raise the exception further - just log it and return
```

### 3. Update Choice Processor

Modify the `handle_reveal_summary` function in `app/services/websocket/choice_processor.py` to check connection state and handle disconnections:

```python
async def handle_reveal_summary(
    state: AdventureState,
    state_manager: AdventureStateManager,
    websocket: WebSocket
) -> Tuple[None, None, bool]:
    """Handle the reveal_summary special choice."""
    from .utils import is_connection_open
    
    logger.info("Processing reveal_summary choice")
    logger.info(f"Current state has {len(state.chapters)} chapters")
    logger.info(f"Current chapter summaries: {len(state.chapter_summaries)}")

    # Get the CONCLUSION chapter
    if state.chapters and state.chapters[-1].chapter_type == ChapterType.CONCLUSION:
        conclusion_chapter = state.chapters[-1]
        logger.info(
            f"Found CONCLUSION chapter: {conclusion_chapter.chapter_number}"
        )
        logger.info(
            f"CONCLUSION chapter content length: {len(conclusion_chapter.content)}"
        )

        # Process it like a regular choice with placeholder values
        story_response = StoryResponse(
            chosen_path="reveal_summary", choice_text=" "
        )
        conclusion_chapter.response = story_response
        logger.info(
            "Created placeholder response for CONCLUSION chapter with whitespace"
        )

        await generate_conclusion_chapter_summary(conclusion_chapter, state, websocket)

    # Check if connection is still open before creating and generating the SUMMARY chapter
    if not await is_connection_open(websocket):
        logger.warning("WebSocket connection closed before generating SUMMARY chapter - aborting")
        return None, None, False

    # Create and generate the SUMMARY chapter
    summary_chapter = chapter_manager.create_summary_chapter(state)
    summary_content = await generate_summary_content(state)
    summary_chapter.content = summary_content
    summary_chapter.chapter_content.content = summary_content

    # Add the SUMMARY chapter to the state
    state_manager.append_new_chapter(summary_chapter)

    # Check connection before streaming summary content
    if not await is_connection_open(websocket):
        logger.warning("WebSocket connection closed before streaming summary content - aborting")
        return None, None, False

    try:
        await stream_summary_content(summary_content, websocket)
    except Exception as e:
        logger.error(f"Error streaming summary content: {str(e)}")
        return None, None, False

    # Check connection before sending summary complete data
    if not await is_connection_open(websocket):
        logger.warning("WebSocket connection closed before sending summary complete data - aborting")
        return None, None, False

    try:
        # Send the complete summary data
        await websocket.send_json(
            {
                "type": "summary_complete",
                "state": {
                    "current_chapter_id": state.current_chapter_id,
                    "current_chapter": {
                        "chapter_number": summary_chapter.chapter_number,
                        "content": summary_content,
                        "chapter_type": ChapterType.SUMMARY.value,
                    },
                    "stats": {
                        "total_lessons": state.total_lessons,
                        "correct_lesson_answers": state.correct_lesson_answers,
                        "completion_percentage": round(
                            (state.correct_lesson_answers / state.total_lessons * 100)
                            if state.total_lessons > 0
                            else 0
                        ),
                    },
                    "chapter_summaries": state.chapter_summaries,
                },
            }
        )
    except Exception as e:
        logger.error(f"Error sending summary complete data: {str(e)}")
        return None, None, False

    return None, None, False
```

### 4. Update WebSocket Router

Enhance the error handling in `app/routers/websocket_router.py` to better handle WebSocket disconnections:

```python
@router.websocket("/ws/story/{story_category}/{lesson_topic}")
async def story_websocket(
    websocket: WebSocket, story_category: str, lesson_topic: str, difficulty: str = None
):
    """Handle WebSocket connection for story streaming."""
    await websocket.accept()
    logger.info(
        f"WebSocket connection established for story category: {story_category}, lesson topic: {lesson_topic}, difficulty: {difficulty}"
    )

    # TODO: Implement difficulty toggle in UI to allow users to select difficulty level

    state_manager = AdventureStateManager()

    try:
        while True:
            try:
                data = await websocket.receive_json()
                # Process message as before...
                
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected during message processing")
                break
                
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                try:
                    await websocket.send_text(
                        "\n\nAn error occurred while processing your request. Please try again."
                    )
                except WebSocketDisconnect:
                    logger.info("WebSocket disconnected while sending error message")
                    break
                except Exception as send_error:
                    logger.error(f"Error sending error message: {send_error}")
                    break

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"Unexpected error in WebSocket handler: {e}")
        try:
            await websocket.close(code=1011)  # 1011 = Server error
        except:
            pass  # Ignore errors during close
```

## Testing Strategy

1. **Manual Testing**:
   - Test chapter transitions, especially between chapters five and six
   - Test with intentional client disconnections at various points
   - Verify error handling by simulating network issues

2. **Logging Verification**:
   - Add detailed logging to track connection state
   - Verify logs show proper detection of closed connections
   - Confirm graceful termination of streaming when disconnections occur

3. **Edge Case Testing**:
   - Test with slow network connections
   - Test with multiple rapid chapter transitions
   - Test with browser tab/window closing during streaming

4. **Integration Testing**:
   - Create automated tests that simulate WebSocket disconnections
   - Verify the server properly handles disconnections without errors
   - Ensure state is preserved for reconnection attempts

## Expected Outcomes

1. Elimination of the `websockets.exceptions.ConnectionClosedOK` and `RuntimeError: Cannot call "send" once a close message has been sent` errors in the logs.

2. Graceful handling of client disconnections during chapter transitions.

3. Improved user experience with better error recovery.

4. More robust WebSocket communication throughout the application.
