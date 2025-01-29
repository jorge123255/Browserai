# Operator Browser AI

A desktop application that uses a local LLM to interpret user instructions and control a live browser view. The agent can read page contents, reason about them, and perform actions like clicking buttons and filling forms.

## Features

- Local LLM integration using Ollama
- Modern PyQt6-based UI with live browser preview
- Intelligent browser automation agent
- Interruptible long-running tasks
- Clean and modular architecture

## Prerequisites

- Python 3.8+
- Ollama installed and running locally (https://ollama.ai)
- The llama2 model pulled in Ollama (`ollama pull llama2`)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/operator_browser_ai.git
cd operator_browser_ai
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Make sure Ollama is running with the llama2 model:
```bash
ollama serve
```

2. Run the application:
```bash
python main.py
```

3. Enter instructions in the text area and click "Submit". Example instructions:
- "Go to google.com and search for 'Python programming'"
- "Find the first search result and click it"
- "Fill out this form with my information"

4. Use the "Stop" button to interrupt the agent at any time.

## Project Structure

- `main.py`: Application entry point
- `ui.py`: PyQt UI implementation
- `agent.py`: Browser automation agent
- `browser_tools.py`: Browser interaction utilities
- `ollama_connection.py`: Local LLM integration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - see LICENSE file for details
