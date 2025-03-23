"""
Question processing functionality for extracting educational questions.
"""

import logging
import re
from typing import Dict, Any, List

from app.models.story import AdventureState
from app.services.summary.helpers import ChapterTypeHelper

logger = logging.getLogger("summary_service.question_processor")


class QuestionProcessor:
    """Processes educational questions from adventure state."""
    
    @staticmethod
    def extract_educational_questions(state: AdventureState) -> List[Dict[str, Any]]:
        """Extract educational questions from LESSON chapters.

        Args:
            state: The adventure state to process

        Returns:
            List of educational question objects with the expected structure
        """
        questions = []
        logger.info("\n=== Extracting Educational Questions ===")
        all_found_questions = []

        # METHOD 1: Check if lesson_questions exists in the state (preferred source)
        if QuestionProcessor._extract_questions_from_state(state, questions, all_found_questions):
            return QuestionProcessor._normalize_questions(questions)

        # METHOD 2: If no questions from lesson_questions, extract from LESSON chapters
        if QuestionProcessor._extract_questions_from_chapters(state, questions, all_found_questions):
            return QuestionProcessor._normalize_questions(questions)

        # METHOD 3: Look for lesson_questions in simulation_metadata if present
        if QuestionProcessor._extract_questions_from_metadata(state, questions, all_found_questions):
            return QuestionProcessor._normalize_questions(questions)

        # METHOD 4: Generate fallback questions if needed
        if not questions:
            logger.warning("No questions found using any method")
            QuestionProcessor._create_fallback_questions(state, questions, all_found_questions)

        return QuestionProcessor._normalize_questions(questions)
    
    @staticmethod
    def _extract_questions_from_state(state: AdventureState, 
                                     questions: List[Dict[str, Any]], 
                                     all_found_questions: List) -> bool:
        """Extract questions from state.lesson_questions.
        
        Returns:
            True if questions were found, False otherwise
        """
        if not hasattr(state, "lesson_questions") or not state.lesson_questions:
            return False
            
        logger.info(f"Found {len(state.lesson_questions)} questions in state.lesson_questions")
        all_found_questions.extend(state.lesson_questions)

        # Process each question from lesson_questions
        for i, question_data in enumerate(state.lesson_questions):
            try:
                logger.info(f"Processing question {i + 1} from lesson_questions")

                # Skip non-dictionary question data
                if not isinstance(question_data, dict):
                    logger.warning(f"Skipping non-dictionary question data: {type(question_data)}")
                    continue

                # Extract question text (required field)
                question_text = question_data.get("question", "")
                if not question_text:
                    logger.warning("Question has no text, skipping")
                    continue

                # Extract user's answer
                user_answer = "No answer recorded"
                for key in ["chosen_answer", "userAnswer", "user_answer", "selected_answer"]:
                    if key in question_data and question_data[key]:
                        user_answer = question_data[key]
                        logger.info(f"Found user answer in '{key}': {user_answer[:50]}...")
                        break

                # Extract correctness information
                is_correct = False
                for key in ["is_correct", "isCorrect"]:
                    if key in question_data:
                        is_correct = bool(question_data[key])
                        logger.info(f"Found correctness in '{key}': {is_correct}")
                        break

                # Extract explanation
                explanation = ""
                if "explanation" in question_data:
                    explanation = question_data["explanation"]
                    logger.info(f"Found explanation: {explanation[:50]}...")

                # Build the standardized question object with snake_case keys
                question_obj = {
                    "question": question_text,
                    "user_answer": user_answer,
                    "is_correct": is_correct,
                    "explanation": explanation,
                }

                # Add correct answer if user's answer was incorrect
                if not is_correct:
                    correct_answer = None

                    # Try various formats for correct answer
                    for key in ["correct_answer", "correctAnswer"]:
                        if key in question_data and question_data[key]:
                            correct_answer = question_data[key]
                            logger.info(f"Found correct answer in '{key}': {correct_answer}")
                            break

                    # If no direct correct answer, check answers array
                    if not correct_answer and "answers" in question_data:
                        for answer in question_data["answers"]:
                            if isinstance(answer, dict) and answer.get("is_correct", False):
                                correct_answer = answer.get("text", "")
                                if correct_answer:
                                    logger.info(f"Found correct answer in answers array: {correct_answer}")
                                    break

                    # Add correct answer to question object if found
                    if correct_answer:
                        question_obj["correct_answer"] = correct_answer

                # Add the processed question to our list
                questions.append(question_obj)
                logger.info(f"Successfully processed question: '{question_text[:50]}...'")

            except Exception as e:
                logger.error(f"Error processing question {i + 1}: {str(e)}")
                # Continue processing other questions
                
        return len(questions) > 0
    
    @staticmethod
    def _extract_questions_from_chapters(state: AdventureState, 
                                        questions: List[Dict[str, Any]], 
                                        all_found_questions: List) -> bool:
        """Extract questions from LESSON chapters.
        
        Returns:
            True if questions were found, False otherwise
        """
        logger.info("Extracting from LESSON chapters")

        # Find all LESSON chapters with questions
        lesson_chapters = []

        for chapter in state.chapters:
            try:
                # Determine if this is a LESSON chapter
                if not ChapterTypeHelper.is_lesson_chapter(chapter.chapter_type):
                    continue
                    
                logger.info(f"Found LESSON chapter {chapter.chapter_number}")
                lesson_chapters.append(chapter)

                # Check for question data in this chapter
                question_data = None

                # Try to get question from various sources
                if hasattr(chapter, "question") and chapter.question:
                    question_data = chapter.question
                    logger.info(f"Found question data in chapter.question: {str(question_data)[:50]}...")
                    all_found_questions.append(question_data)

                if not question_data:
                    continue

                # Get response data for the question if available
                response_data = None
                user_answer = "No answer recorded"
                is_correct = False

                if hasattr(chapter, "response") and chapter.response:
                    response_data = chapter.response
                    logger.info(f"Found response data: {str(response_data)[:50]}...")

                    # Extract user answer from response
                    if hasattr(response_data, "chosen_answer"):
                        user_answer = response_data.chosen_answer
                        logger.info(f"Found user answer in response.chosen_answer: {user_answer}")
                    elif isinstance(response_data, dict) and "chosen_answer" in response_data:
                        user_answer = response_data["chosen_answer"]
                        logger.info(f"Found user answer in response dict: {user_answer}")

                    # Extract correctness from response
                    if hasattr(response_data, "is_correct"):
                        is_correct = bool(response_data.is_correct)
                        logger.info(f"Found is_correct in response.is_correct: {is_correct}")
                    elif isinstance(response_data, dict) and "is_correct" in response_data:
                        is_correct = bool(response_data["is_correct"])
                        logger.info(f"Found is_correct in response dict: {is_correct}")

                # Get question text
                question_text = ""
                explanation = ""

                # Handle question_data as both dict and object
                if isinstance(question_data, dict):
                    question_text = question_data.get("question", "")
                    explanation = question_data.get("explanation", "")
                else:
                    if hasattr(question_data, "question"):
                        question_text = question_data.question
                    if hasattr(question_data, "explanation"):
                        explanation = question_data.explanation

                if not question_text:
                    logger.warning(f"No question text found, skipping")
                    continue

                # Create standardized question object with snake_case keys
                question_obj = {
                    "question": question_text,
                    "user_answer": user_answer,
                    "is_correct": is_correct,
                    "explanation": explanation,
                }

                # Add correct answer if the user was wrong
                if not is_correct:
                    correct_answer = None

                    # Try to extract correct answer from question data
                    if isinstance(question_data, dict):
                        # Direct correct_answer field
                        if "correct_answer" in question_data:
                            correct_answer = question_data["correct_answer"]

                        # Look in answers array
                        if not correct_answer and "answers" in question_data:
                            for answer in question_data["answers"]:
                                if isinstance(answer, dict) and answer.get("is_correct", False):
                                    correct_answer = answer.get("text", "")
                                    break
                    else:
                        # Try attribute access
                        if hasattr(question_data, "correct_answer"):
                            correct_answer = question_data.correct_answer

                        # Try answers attribute
                        if not correct_answer and hasattr(question_data, "answers"):
                            for answer in question_data.answers:
                                if getattr(answer, "is_correct", False):
                                    correct_answer = getattr(answer, "text", "")
                                    break

                    # Add correct answer to question object if found
                    if correct_answer:
                        question_obj["correct_answer"] = correct_answer
                        logger.info(f"Added correct answer: {correct_answer}")

                # Add the processed question to our list
                questions.append(question_obj)
                logger.info(f"Successfully extracted question from chapter {chapter.chapter_number}")

            except Exception as e:
                logger.error(f"Error processing chapter {getattr(chapter, 'chapter_number', 'unknown')}: {str(e)}")
                # Continue processing other chapters
                
        return len(questions) > 0
    
    @staticmethod
    def _extract_questions_from_metadata(state: AdventureState, 
                                        questions: List[Dict[str, Any]], 
                                        all_found_questions: List) -> bool:
        """Extract questions from state.metadata.simulation_metadata.lesson_questions.
        
        Returns:
            True if questions were found, False otherwise
        """
        if not (hasattr(state, "metadata") and isinstance(state.metadata, dict)):
            return False
            
        logger.info("Checking metadata for simulation_metadata.lesson_questions")

        simulation_metadata = state.metadata.get("simulation_metadata", {})
        if not (isinstance(simulation_metadata, dict) and "lesson_questions" in simulation_metadata):
            return False
            
        logger.info("Found lesson_questions in simulation_metadata")

        for i, question_data in enumerate(simulation_metadata["lesson_questions"]):
            try:
                if not isinstance(question_data, dict):
                    continue

                # Extract basic question data
                question_text = question_data.get("question", "")
                if not question_text:
                    continue

                is_correct = question_data.get("is_correct", False)
                user_answer = question_data.get("chosen_answer", "No answer recorded")
                explanation = question_data.get("explanation", "")

                # Create question object with snake_case keys
                question_obj = {
                    "question": question_text,
                    "user_answer": user_answer,
                    "is_correct": is_correct,
                    "explanation": explanation,
                }

                # Add correct answer if answer was incorrect
                if not is_correct:
                    correct_answer = question_data.get("correct_answer")
                    if correct_answer:
                        question_obj["correct_answer"] = correct_answer

                questions.append(question_obj)
                logger.info(f"Added question from simulation_metadata: {question_text[:50]}...")

            except Exception as e:
                logger.error(f"Error processing metadata question {i}: {str(e)}")
                
        return len(questions) > 0
    
    @staticmethod
    def _create_fallback_questions(state: AdventureState, 
                                  questions: List[Dict[str, Any]], 
                                  all_found_questions: List) -> None:
        """Create fallback questions when no questions are found."""
        # First check if we have LESSON chapters to determine whether we should have questions
        has_lesson_chapters = any(ChapterTypeHelper.is_lesson_chapter(chapter.chapter_type) 
                                  for chapter in state.chapters)

        if has_lesson_chapters or all_found_questions:
            logger.warning("Questions should exist (found LESSON chapters or raw question data), creating fallback question")
            fallback_question = {
                "question": "What did you learn from this adventure?",
                "user_answer": "I learned about important concepts through this interactive story",
                "is_correct": True,
                "explanation": "This adventure was designed to teach important concepts while telling an engaging story.",
            }
            questions.append(fallback_question)
            logger.info(f"Added educational fallback question: {fallback_question['question']}")
        else:
            logger.info("No LESSON chapters found, adding standard reflection question")
            standard_question = {
                "question": "Did you enjoy your adventure?",
                "user_answer": "Yes, the adventure was enjoyable and educational",
                "is_correct": True,
                "explanation": "We hope you had a great time on this adventure!",
            }
            questions.append(standard_question)
            logger.info(f"Added standard reflection question: {standard_question['question']}")
    
    @staticmethod
    def _normalize_questions(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize questions to ensure consistent format."""
        normalized_questions = []
        for q in questions:
            # Create a normalized question with required fields
            normalized_question = {
                "question": q.get("question", ""),
                "user_answer": q.get("user_answer", ""),
                "is_correct": bool(q.get("is_correct", False)),  # Ensure boolean type
                "explanation": q.get("explanation", ""),
            }

            # Only add correct_answer if the answer was incorrect
            if not q.get("is_correct", False) and "correct_answer" in q:
                normalized_question["correct_answer"] = q["correct_answer"]

            # Validate and ensure we have necessary fields
            if not normalized_question["question"]:
                logger.warning("Skipping question with empty question text")
                continue

            normalized_questions.append(normalized_question)

        # Log each question's structure for verification
        logger.info(f"Successfully extracted {len(normalized_questions)} educational questions")
        
        return normalized_questions
        
    @staticmethod
    async def process_stored_lesson_questions(state_data: Dict[str, Any]) -> None:
        """Process lesson questions if none exist in the state."""
        # Skip if lesson_questions already exists
        if state_data.get("lesson_questions"):
            return
            
        logger.info("Extracting lesson questions for state before storing")

        # Find all LESSON chapters
        lesson_chapters = []
        for chapter in state_data.get("chapters", []):
            chapter_number = chapter.get("chapter_number", 0)
            chapter_type = chapter.get("chapter_type", "")

            # Check if this is a LESSON chapter
            is_lesson = False
            if isinstance(chapter_type, str) and chapter_type.lower() == "lesson":
                is_lesson = True
            elif hasattr(chapter_type, "value") and chapter_type.value.lower() == "lesson":
                is_lesson = True

            if is_lesson:
                lesson_chapters.append(chapter_number)
                
        logger.info(f"Found {len(lesson_chapters)} LESSON chapters: {lesson_chapters}")

        # Extract questions from chapters
        lesson_questions = []
        
        # Process each LESSON chapter
        for chapter in state_data.get("chapters", []):
            # Skip non-LESSON chapters
            chapter_type = chapter.get("chapter_type", "")
            is_lesson = False
            if isinstance(chapter_type, str) and chapter_type.lower() == "lesson":
                is_lesson = True
            elif hasattr(chapter_type, "value") and chapter_type.value.lower() == "lesson":
                is_lesson = True
                
            if not is_lesson:
                continue
                
            chapter_number = chapter.get("chapter_number", 0)
            logger.info(f"Processing LESSON chapter {chapter_number} for questions")
            
            # Attempt to extract question data
            question_obj = QuestionProcessor._extract_question_from_chapter(chapter, chapter_number)
            if question_obj:
                lesson_questions.append(question_obj)
                logger.info(f"Added complete question from chapter {chapter_number}")
            
        # If no questions found from chapters, add fallback questions
        if not lesson_questions:
            lesson_questions = QuestionProcessor._create_stored_fallback_questions()
            logger.info("Added fallback questions since no questions were found")
            
        # Add to state data
        state_data["lesson_questions"] = lesson_questions
        logger.info(f"Added {len(lesson_questions)} questions to state data")
    
    @staticmethod
    def _extract_question_from_chapter(chapter, chapter_number):
        """Extract question data from a chapter."""
        # Look for question data
        question_data = None
        
        # Try direct question field first
        if chapter.get("question"):
            question_data = chapter.get("question")
        # Try chapter_content.question next
        elif chapter.get("chapter_content") and chapter.get("chapter_content").get("question"):
            question_data = chapter.get("chapter_content").get("question")
        # Try scanning content for question format as last resort
        elif chapter.get("content"):
            content = chapter.get("content", "")
            # Look for question patterns in content
            question_match = re.search(r"Question:?\s+([^\?]+\?)", content)
            if question_match:
                question_text = question_match.group(1).strip()
                question_data = {"question": question_text}
                
        if not question_data:
            logger.info(f"No question data found in chapter {chapter_number}")
            return None
            
        # Get response data
        is_correct = False
        chosen_answer = "No answer recorded"
        
        response = chapter.get("response")
        if response:
            # Extract user answer and correctness from response
            if hasattr(response, "chosen_answer"):
                chosen_answer = response.chosen_answer
            elif isinstance(response, dict) and "chosen_answer" in response:
                chosen_answer = response["chosen_answer"]
                
            if hasattr(response, "is_correct"):
                is_correct = response.is_correct
            elif isinstance(response, dict) and "is_correct" in response:
                is_correct = response["is_correct"]
                
        # Extract question text and explanation
        question_text = ""
        explanation = ""
        
        if isinstance(question_data, dict):
            question_text = question_data.get("question", "")
            explanation = question_data.get("explanation", "")
        elif hasattr(question_data, "question"):
            question_text = question_data.question
            if hasattr(question_data, "explanation"):
                explanation = question_data.explanation
        else:
            question_text = str(question_data)
            
        if not question_text:
            return None
            
        # Create question object
        question_obj = {
            "question": question_text,
            "userAnswer": chosen_answer,
            "isCorrect": is_correct,
            "explanation": explanation,
        }
        
        # Add correct answer if needed
        if not is_correct:
            correct_answer = None
            
            # Look for correct answer in different places
            if isinstance(question_data, dict) and "correct_answer" in question_data:
                correct_answer = question_data["correct_answer"]
            elif hasattr(question_data, "correct_answer"):
                correct_answer = question_data.correct_answer
            elif isinstance(question_data, dict) and "answers" in question_data:
                for answer in question_data["answers"]:
                    if isinstance(answer, dict) and answer.get("is_correct"):
                        correct_answer = answer.get("text", "")
                        break
                        
            if correct_answer:
                question_obj["correctAnswer"] = correct_answer
                
        return question_obj
    
    @staticmethod
    def _create_stored_fallback_questions():
        """Create standard fallback questions."""
        return [
            {
                "question": "What did you learn from this adventure?",
                "userAnswer": "I learned valuable lessons about teamwork and problem-solving",
                "isCorrect": True,
                "explanation": "This adventure was designed to teach important concepts through an engaging narrative.",
            },
            {
                "question": "What was your favorite part of the adventure?",
                "userAnswer": "I enjoyed exploring new places and meeting interesting characters",
                "isCorrect": True,
                "explanation": "Adventures are about discovery and new experiences.",
            },
            {
                "question": "Would you like to go on another adventure?",
                "userAnswer": "Yes! I can't wait for the next one",
                "isCorrect": True,
                "explanation": "Great! There are many more adventures waiting for you.",
            }
        ]