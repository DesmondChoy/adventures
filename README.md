# Interactive Educational Storytelling App

An AI-powered educational application that creates interactive, branching stories while seamlessly integrating learning objectives. The app uses GPT-4 to generate engaging narratives that adapt to user choices and educational requirements.

## Features

- Dynamic story generation with branching narratives
- Educational content integration
- Customizable story configurations (tone, vocabulary level, narrative elements)
- Real-time story streaming
- Progress tracking and state management

## Prerequisites

- Python 3.8+
- OpenAI API key

## Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

## Project Structure

- `app/`: Main application directory
  - `services/`: Core services including LLM integration
  - `models/`: Data models and state management
  - `templates/`: HTML templates
  - `data/`: Story configurations and educational content

## License

MIT License 