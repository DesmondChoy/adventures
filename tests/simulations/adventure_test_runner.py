"""
Adventure Test Runner

Automated testing script that simulates complete adventure playthroughs
by connecting to the existing WebSocket endpoint and making random choices.
Leverages existing architecture to generate comprehensive logs for analysis.

Usage:
    python tests/simulations/adventure_test_runner.py [--runs N] [--category CATEGORY] [--topic TOPIC]
"""

import asyncio
import websockets
import json
import random
import logging
import sys
import time
import uuid
import argparse
import urllib.parse
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import existing components
from app.data.story_loader import StoryLoader
from app.data.lesson_loader import LessonLoader

# Constants
DEFAULT_RUNS = 1
DEFAULT_PORT = 8000

class AdventureTestRunner:
    """Automated adventure testing using existing WebSocket architecture."""
    
    def __init__(self, base_url: str = "localhost", port: int = DEFAULT_PORT):
        self.base_url = base_url
        self.port = port
        self.run_id = str(uuid.uuid4())[:8]
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M")
        
        # Setup logging
        self.setup_logging()
        
        # Load available categories and topics
        self.story_categories = self.load_story_categories()
        self.lesson_topics = self.load_lesson_topics()
        
    def setup_logging(self):
        """Configure logging to capture all test output."""
        log_dir = Path("logs/simulations")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"adventure_test_{self.timestamp}_{self.run_id}.log"
        
        # Configure logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger("adventure_test_runner")
        self.logger.info(f"Adventure Test Runner started - Run ID: {self.run_id}")
        self.logger.info(f"Logs saved to: {log_file}")
        
    def load_story_categories(self) -> List[str]:
        """Load available story categories using existing loader."""
        try:
            loader = StoryLoader()
            story_data = loader.load_all_stories()
            categories = list(story_data["story_categories"].keys())
            self.logger.info(f"Loaded {len(categories)} story categories: {categories}")
            return categories
        except Exception as e:
            self.logger.error(f"Failed to load story categories: {e}")
            return ["enchanted_forest_tales"]
    
    def load_lesson_topics(self) -> List[str]:
        """Load available lesson topics using existing loader."""
        try:
            loader = LessonLoader()
            lesson_df = loader.load_all_lessons()
            topics = lesson_df["topic"].unique().tolist()
            self.logger.info(f"Loaded {len(topics)} lesson topics: {topics}")
            return topics
        except Exception as e:
            self.logger.error(f"Failed to load lesson topics: {e}")
            return ["Singapore History"]
    
    def get_random_selection(self, category: Optional[str] = None, topic: Optional[str] = None):
        """Get random or specified category and topic."""
        selected_category = category or random.choice(self.story_categories)
        selected_topic = topic or random.choice(self.lesson_topics)
        return selected_category, selected_topic
    
    async def run_single_adventure(self, category: str, topic: str) -> Dict[str, Any]:
        """Run a complete adventure simulation and return results."""
        adventure_id = str(uuid.uuid4())[:8]
        client_uuid = str(uuid.uuid4())
        
        self.logger.info(f"Starting adventure {adventure_id}: {category} / {topic}")
        
        # Construct WebSocket URI with URL encoding
        encoded_category = urllib.parse.quote(category, safe='')
        encoded_topic = urllib.parse.quote(topic, safe='')
        uri = f"ws://{self.base_url}:{self.port}/ws/story/{encoded_category}/{encoded_topic}?client_uuid={client_uuid}"
        
        adventure_stats = {
            "adventure_id": adventure_id,
            "category": category,
            "topic": topic,
            "client_uuid": client_uuid,
            "start_time": time.time(),
            "status": "failed",
            "chapters_completed": 0,
            "choices_made": 0,
            "errors": [],
            "summary_generated": False
        }
        
        try:
            # Use asyncio.wait_for for timeout handling
            async def run_adventure():
                async with websockets.connect(uri, ping_timeout=None, close_timeout=10) as websocket:
                    self.logger.info(f"WebSocket connected for adventure {adventure_id}")
                    
                    # Wait for initial status
                    await self.wait_for_adventure_status(websocket, adventure_stats)
                    
                    # Send start choice
                    await self.send_start_choice(websocket, adventure_stats)
                    
                    # Process chapters until completion
                    await self.process_adventure_chapters(websocket, adventure_stats)
                    
                    # Generate summary if story completed
                    if adventure_stats["status"] == "story_complete":
                        await self.generate_summary(websocket, adventure_stats)
            
            # Run adventure without overall timeout
            await run_adventure()
            
            adventure_stats["end_time"] = time.time()
            adventure_stats["duration"] = adventure_stats["end_time"] - adventure_stats["start_time"]
            
            self.logger.info(f"Adventure {adventure_id} completed successfully")
                
        except Exception as e:
            adventure_stats["errors"].append(str(e))
            adventure_stats["end_time"] = time.time()
            adventure_stats["duration"] = adventure_stats["end_time"] - adventure_stats["start_time"]
            self.logger.error(f"Adventure {adventure_id} failed: {e}")
            
        return adventure_stats
    
    async def wait_for_adventure_status(self, websocket, stats: Dict[str, Any]):
        """Wait for initial adventure status message."""
        self.logger.debug("Waiting for adventure status...")
        
        while True:
            message = await websocket.recv()
            try:
                data = json.loads(message)
                if data.get("type") == "adventure_status":
                    self.logger.info(f"Adventure status: {data.get('status')}")
                    break
            except json.JSONDecodeError:
                # Text content, continue waiting
                continue
    
    async def send_start_choice(self, websocket, stats: Dict[str, Any]):
        """Send the initial start choice."""
        # Import here to avoid circular imports
        from app.services.chapter_manager import ChapterManager
        
        # Generate proper chapter types for 10-chapter story
        planned_types = ChapterManager.determine_chapter_types(
            total_chapters=10, 
            available_questions=3
        )
        # Convert ChapterType enums to strings for JSON serialization
        planned_types_str = [chapter_type.value for chapter_type in planned_types]
        
        start_message = {
            "state": {
                "current_chapter_id": "start",
                "story_length": 10,
                "chapters": [],
                "planned_chapter_types": planned_types_str,
                "metadata": {}
            },
            "choice": "start"
        }
        
        await websocket.send(json.dumps(start_message))
        self.logger.info("Sent start choice")
    
    async def process_adventure_chapters(self, websocket, stats: Dict[str, Any]):
        """Process all adventure chapters, making random choices."""
        current_state = None
        chapter_count = 0
        
        while chapter_count < 15:  # Safety limit (10 chapters + summary + buffer)
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=300)
                
                # Try to parse as JSON
                try:
                    data = json.loads(message)
                    message_type = data.get("type")
                    
                    if message_type == "chapter_update":
                        current_state = data.get("state", {})
                        chapter_count = current_state.get("current_chapter", {}).get("chapter_number", chapter_count)
                        stats["chapters_completed"] = chapter_count
                        self.logger.info(f"Chapter {chapter_count} started")
                        
                    elif message_type == "choices":
                        # Make random choice with realistic human delay
                        choices = data.get("choices", [])
                        if choices and current_state is not None:
                            # Simulate human reading/thinking time (5-15 seconds)
                            think_time = random.uniform(5, 15)
                            self.logger.debug(f"Simulating {think_time:.1f}s think time before choice")
                            await asyncio.sleep(think_time)
                            
                            choice = random.choice(choices)
                            await self.send_choice(websocket, current_state, choice, stats)
                            
                    elif message_type == "story_complete":
                        current_state = data.get("state", {})
                        stats["status"] = "story_complete"
                        self.logger.info("Story completed, summary available")
                        break
                        
                    elif message_type == "error":
                        error_msg = data.get("message", "Unknown error")
                        stats["errors"].append(error_msg)
                        self.logger.error(f"Server error: {error_msg}")
                        
                except json.JSONDecodeError:
                    # Text content (streaming), just log it
                    self.logger.debug(f"Content chunk received ({len(message)} chars)")
                    
            except asyncio.TimeoutError:
                self.logger.warning("Timeout waiting for message")
                break
                
        stats["chapters_completed"] = chapter_count
    
    async def send_choice(self, websocket, state: Dict[str, Any], choice: Dict[str, Any], stats: Dict[str, Any]):
        """Send a choice selection to the server."""
        choice_message = {
            "state": state,
            "choice": {
                "chosen_path": choice["id"],
                "choice_text": choice["text"]
            }
        }
        
        await websocket.send(json.dumps(choice_message))
        stats["choices_made"] += 1
        self.logger.info(f"Made choice: {choice['text'][:50]}...")
    
    async def generate_summary(self, websocket, stats: Dict[str, Any]):
        """Generate adventure summary."""
        # Send reveal summary choice
        summary_message = {
            "state": {},  # Will be populated with current state
            "choice": "reveal_summary"
        }
        
        await websocket.send(json.dumps(summary_message))
        self.logger.info("Requested adventure summary")
        
        # Wait for summary completion
        summary_timeout = 90  # Summary generation can take time
        start_time = time.time()
        
        while time.time() - start_time < summary_timeout:
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=30)
                
                try:
                    data = json.loads(message)
                    if data.get("type") == "summary_complete":
                        stats["summary_generated"] = True
                        self.logger.info("Summary generation completed")
                        break
                except json.JSONDecodeError:
                    # Summary content
                    continue
                    
            except asyncio.TimeoutError:
                self.logger.warning("Timeout during summary generation")
                break
    
    async def run_test_suite(self, num_runs: int, category: Optional[str] = None, topic: Optional[str] = None):
        """Run multiple adventure tests."""
        self.logger.info(f"Starting test suite: {num_runs} runs")
        
        results = []
        successful_runs = 0
        
        for i in range(num_runs):
            test_category, test_topic = self.get_random_selection(category, topic)
            
            self.logger.info(f"Test {i+1}/{num_runs}: {test_category} / {test_topic}")
            
            result = await self.run_single_adventure(test_category, test_topic)
            results.append(result)
            
            if result["status"] == "story_complete":
                successful_runs += 1
            
            # Brief pause between tests
            await asyncio.sleep(2)
        
        # Generate summary report
        self.generate_test_report(results, successful_runs, num_runs)
        
        return results
    
    def generate_test_report(self, results: List[Dict[str, Any]], successful: int, total: int):
        """Generate a summary report of test results."""
        self.logger.info("=" * 60)
        self.logger.info("TEST SUITE SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Total runs: {total}")
        self.logger.info(f"Successful: {successful}")
        self.logger.info(f"Failed: {total - successful}")
        self.logger.info(f"Success rate: {(successful/total)*100:.1f}%")
        
        # Detailed statistics
        total_chapters = sum(r["chapters_completed"] for r in results)
        total_choices = sum(r["choices_made"] for r in results)
        summaries_generated = sum(1 for r in results if r["summary_generated"])
        
        self.logger.info(f"Total chapters generated: {total_chapters}")
        self.logger.info(f"Total choices made: {total_choices}")
        self.logger.info(f"Summaries generated: {summaries_generated}")
        
        # Error analysis
        all_errors = []
        for result in results:
            all_errors.extend(result["errors"])
        
        if all_errors:
            self.logger.info(f"Total errors encountered: {len(all_errors)}")
            unique_errors = list(set(all_errors))
            for error in unique_errors:
                count = all_errors.count(error)
                self.logger.info(f"  {error}: {count} occurrences")
        
        self.logger.info("=" * 60)

async def main():
    """Main entry point for adventure testing."""
    parser = argparse.ArgumentParser(description="Run automated adventure tests")
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS, help="Number of test runs")
    parser.add_argument("--category", type=str, help="Specific story category")
    parser.add_argument("--topic", type=str, help="Specific lesson topic")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Server port")
    parser.add_argument("--host", type=str, default="localhost", help="Server host")
    
    args = parser.parse_args()
    
    # Create test runner
    runner = AdventureTestRunner(base_url=args.host, port=args.port)
    
    # Run tests
    try:
        await runner.run_test_suite(args.runs, args.category, args.topic)
    except KeyboardInterrupt:
        runner.logger.info("Test suite interrupted by user")
    except Exception as e:
        runner.logger.error(f"Test suite failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
