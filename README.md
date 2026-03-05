# Ira - Local AI Assistant

A fully offline, multimodal AI assistant with text, voice, and image capabilities.

## Features

- 💬 **Chat** - Natural conversation with memory
- 🎤 **Voice** - Speech-to-text and text-to-speech
- 🖼️ **Vision** - Image understanding and analysis
- 📄 **Documents** - Q&A over your documents (RAG)
- 💻 **Coding** - Code assistance and execution
- 🏠 **Home Automation** - Control smart home devices

## Quick Start

### Prerequisites

1. **Ollama** - Install from [ollama.com](https://ollama.com)
2. **Python 3.11+** - Install from [python.org](https://python.org)
3. **Node.js 20+** - Install from [nodejs.org](https://nodejs.org)

### Installation

```powershell
# Run the installation script
.\scripts\install.ps1
```

### Start the Assistant

```powershell
# Start Ira
.\scripts\start.ps1
```

## Project Structure

```
Ira/
├── backend/          # Python FastAPI backend
├── frontend/         # Electron + React desktop app
├── models/           # Downloaded model files
├── data/             # Documents and databases
└── scripts/          # Setup and launch scripts
```

## Configuration

Edit `backend/app/config.py` to customize:

- Model selection
- Voice settings
- Home Assistant connection
- File paths

## License

MIT License - Feel free to modify and use as you wish!
