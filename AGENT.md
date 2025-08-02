# AGENT.md

## One-Word Commands
Quick shortcuts for common tasks:

- `$update`: Update memory-bank to reflect session changes. No opinionated remarks - ask for clarification when unsure.
- `$craft`: Create git commit message for session changes using conventional commit types (feat, docs, chore, etc). Do not commit - user reviews first.
- `$review`: Use Oracle and remind it of the original objective, then review all changes made using all tools available. Check for opinionated changes, over-engineering, and opportunities for simplification or efficiency improvements. Present findings to user for decision.
- `$parallel-x`: Run x sub-agents in parallel (not sequentially) where x is the number specified.
- `$playwright`: Start server and use Playwright MCP for browser automation/visual verification to iterative develop/test your code implementations. Steps: 1) `start cmd /k ".venv\Scripts\activate && python -m app.main"` 2) `mcp__playwright__browser_wait_for` (3 sec) 3) `mcp__playwright__browser_navigate` to `http://localhost:8000` 4) Use snapshot/screenshot/evaluate as needed. 

## Commands
- **Virtual Environment**: ALWAYS activate `.venv` before running Python commands

## Code Style & Patterns
- **Imports**: Use absolute imports (`from app.services.summary import SummaryService`)
- **Type hints**: Required for all functions, use Pydantic models extensively
- **Error handling**: Use custom exceptions (`StateNotFoundError`, `SummaryError`)
- **Async**: Use `async`/`await` for all I/O operations, services are async
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **State management**: `AdventureState` is single source of truth, never hardcode chapter data
- **Logging**: Use structured logging with context (`logger.info("message", extra={"state_id": id})`)
- **Code reuse**: Review existing codebase before creating new functions, prioritize modular design

## Critical Implementation Rules

### State Management
- `AdventureState` MUST be single source of truth
- NEVER hardcode chapter numbers (use `state.story_length` and `planned_chapter_types`)
- Agency choice MUST be stored in `state.metadata["agency"]`
- Always convert chapter types to lowercase when storing/retrieving
- Complete state serialization required with proper type hints
- State changes must be logged with context

### Chapter Requirements
- First chapter MUST be STORY type with agency choice
- Last chapter MUST be CONCLUSION type
- 50% of remaining chapters MUST be LESSON type
- REFLECT chapters MUST only follow LESSON chapters
- No consecutive LESSON chapters allowed
- No question repetition in session

### Agency Implementation
- Agency MUST be referenced in all subsequent chapters
- Agency MUST evolve in REFLECT chapters
- Agency MUST have meaningful resolution in conclusion
- Use `update_agency_references()` for tracking

### Dynamic Content Handling (CRITICAL)
- **NEVER hardcode narrative strings, character names, or plot points** - content is AI-generated
- **Rely on state structure**: Base logic on `AdventureState` fields, `ChapterType`, metadata
- **Abstract testing**: Focus on state transitions, not specific LLM-generated text
- **Use metadata**: Store extracted information in structured fields, avoid parsing free-form text

## Code Implementation Guidelines (CRITICAL)

### NEVER Make Assumptions - Always Verify First
**Before writing ANY code that calls functions, imports, or references existing code:**

1. **ALWAYS use search tools to verify function names and signatures BEFORE using them**
   - Use `Grep` to find exact function definitions: `def function_name`
   - Use `codebase_search_agent` to understand how functions are used elsewhere
   - Use `Read` to examine the actual implementation and parameters

2. **NEVER assume function names, even if they seem logical**
   - Wrong: Assuming `get_previous_lessons()` exists 
   - Right: Search for "previous_lessons" or "lesson" functions first
   - Always verify import paths and module structure

3. **ALWAYS check existing import patterns before adding new imports**
   - Look at other files in the same directory for import examples
   - Verify module structure with `list_directory` if needed
   - Check that the function/class you're importing actually exists

4. **ALWAYS verify parameter types and return values**
   - Read function signatures and docstrings
   - Check how the function is called elsewhere in the codebase
   - Understand the expected data structures

### Implementation Order (MANDATORY)
1. **Search** → Find existing implementations
2. **Read** → Understand the actual code structure  
3. **Verify** → Check function signatures and usage patterns
4. **Implement** → Write code based on verified information
5. **Test** → Run diagnostics to catch errors early

### Red Flags That Require Verification
- Using any function name that "makes sense" but you haven't verified
- Importing from modules without checking they exist
- Assuming parameter types or return values
- Copy-pasting patterns without understanding the context
- Making changes that "should work" without verification

### Common Debugging Patterns
- **Method Missing at Runtime**: Check indentation - methods inside functions won't be accessible on class instances
- **AttributeError on Service Methods**: Verify method is properly indented within the class definition
- **Telemetry/Duration Issues**: Connection restarts cause chapter start times to be lost, resulting in null duration values. Check metadata keys and consider timestamp-based backfilling for historical data
- **Data Flow Tracing**: When debugging UI display issues, trace the complete data flow from storage → calculation → display rather than assuming the problem is at the UI layer

**Remember: Assumptions lead to bugs. Verification prevents them.**