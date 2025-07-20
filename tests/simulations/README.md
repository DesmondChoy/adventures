# Adventure Testing Suite

Automated testing framework for the Learning Odyssey adventure system. This suite simulates complete adventure playthroughs and analyzes logs to detect errors and anomalies.

**🚧 Work in Progress** - The testing framework is implemented but still under development. Some functionality may not be fully stable yet.

**✨ Automated** - Includes automatic server startup/shutdown for zero-configuration testing!

## Overview

The testing suite consists of three main components:

1. **`adventure_test_runner.py`** - Simulates complete adventure experiences via WebSocket
2. **`log_analyzer.py`** - Analyzes test logs to extract errors and anomalies  
3. **`run_test_analysis.py`** - Combined runner with automatic server management

## Quick Start

### Zero-Configuration Testing

⚠️ **Note**: This testing framework is still a work in progress. While the core functionality is implemented, some features may not be fully stable.

Just run the test suite - it handles everything automatically:

```bash
python tests/simulations/run_test_analysis.py
```

This will:
- Automatically start the uvicorn server in the background
- Run 1 complete adventure simulation (default)
- Analyze the generated logs
- Provide a summary report with any issues found
- Automatically shut down the server when done

**No manual server setup required!**

For multiple test runs:
```bash
python tests/simulations/run_test_analysis.py --runs 5
```

## Components

### Adventure Test Runner

Simulates real user interactions:
- Connects to WebSocket endpoint
- Makes random story choices
- Processes all chapters (1-10)
- Generates adventure summary
- Captures comprehensive logs

```bash
# Run 10 tests with random categories/topics
python tests/simulations/adventure_test_runner.py --runs 10

# Test specific category and topic
python tests/simulations/adventure_test_runner.py --category "enchanted_forest_tales" --topic "Singapore History"

# Test against different server
python tests/simulations/adventure_test_runner.py --host production.server.com --port 443
```

### Enhanced Log Analyzer

Uses **app-specific patterns** from the actual Learning Odyssey codebase to detect:

**Critical Issues (High Severity):**
- **State Corruption**: `[STATE CORRUPTION]` messages, invalid chapter data
- **LLM Failures**: Generation timeouts, prompt failures, serialization errors
- **WebSocket Errors**: Connection failures, message processing errors
- **Performance Issues**: `[PERFORMANCE]` failures, operations >5 seconds

**Adventure Flow Issues:**
- **Incomplete Stories**: Adventures stopping before 10 chapters
- **Chapter Processing**: Missing/invalid chapter types or numbers
- **Summary Generation**: Failed adventure summary creation
- **Lesson Validation**: Invalid questions or answers

**Structured Logging Integration:**
- **JSON Log Parsing**: Handles StructuredLogger format from the app
- **Category Prefixes**: Recognizes `[PERFORMANCE]`, `[STATE STORAGE]`, `[REVEAL SUMMARY]`
- **Context Extraction**: Provides relevant log context around issues

```bash
# Analyze specific log file
python tests/simulations/log_analyzer.py logs/simulations/adventure_test_2025-01-20_14-30-15_a1b2c3d4.log

# Save analysis to file
python tests/simulations/log_analyzer.py logs/test.log --output analysis_report.txt
```

### Combined Test & Analysis

The easiest way to run comprehensive testing with full automation:

```bash
# Run 3 tests with automatic server management
python tests/simulations/run_test_analysis.py --runs 3

# Only analyze existing logs (no new tests)
python tests/simulations/run_test_analysis.py --analyze-only

# Test specific content with automatic server
python tests/simulations/run_test_analysis.py --runs 5 --category "circus_and_carnival_capers" --topic "Human Body"

# Use existing server (no automatic startup/shutdown)
python tests/simulations/run_test_analysis.py --runs 3 --no-server
```

## Output Files

### Log Files
- Location: `logs/simulations/`
- Format: `adventure_test_{timestamp}_{run_id}.log`
- Contains: All server and client logs during testing

### Analysis Reports  
- Location: `logs/simulations/`
- Format: `analysis_report_{timestamp}.txt`
- Contains: Summary of anomalies, errors, and performance issues

## Test Flow

Each adventure test follows this path:

1. **Connection**: WebSocket to `/ws/story/{category}/{topic}`
2. **Initialization**: Send `"start"` choice
3. **Chapter Loop**: 
   - Receive chapter content
   - Make random choice from available options
   - Repeat for 10 chapters
4. **Completion**: Process CONCLUSION chapter
5. **Summary**: Generate adventure summary
6. **Cleanup**: Close connection and log results

## Common Issues

### Server Not Running
```
Error: Failed to establish WebSocket connection
```
**Solution**: Ensure the server is running on the specified host/port

### Timeout Errors
```
Timeout waiting for response in chapter X
```
**Solution**: Check server performance, LLM service availability

### Authentication Issues
```
WebSocket connection closed during chapter X
```
**Solution**: Verify server configuration and JWT setup

## Advanced Usage

### Custom Categories/Topics

Available story categories:
- `circus_and_carnival_capers`
- `enchanted_forest_tales`
- `festival_of_lights_and_colors`
- `jade_mountain`
- `living_inside_your_own_drawing`

Available lesson topics:
- `Farm Animals`
- `Human Body`
- `Singapore History`

### Performance Testing

For load testing, run multiple instances:
```bash
# Terminal 1
python tests/simulations/adventure_test_runner.py --runs 10 &

# Terminal 2  
python tests/simulations/adventure_test_runner.py --runs 10 &

# Terminal 3
python tests/simulations/adventure_test_runner.py --runs 10 &
```

### Continuous Integration

For CI/CD pipelines:
```bash
# Run minimal test suite
python tests/simulations/run_test_analysis.py --runs 2

# Check exit code
if [ $? -eq 0 ]; then
    echo "Tests passed!"
else
    echo "Tests failed - check logs"
    exit 1
fi
```

## Architecture Integration

This testing suite leverages the existing Learning Odyssey architecture:

- **Data Loading**: Uses `StoryLoader` and `LessonLoader` for valid test data
- **WebSocket Protocol**: Follows exact message formats used by frontend
- **State Management**: Respects `AdventureState` structure and transitions  
- **Error Handling**: Captures all application errors and edge cases
- **Logging**: Uses existing logging infrastructure for comprehensive coverage

The tests simulate real user interactions without reimplementing business logic, ensuring accurate representation of production behavior.
