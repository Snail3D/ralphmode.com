# Ralph Mode PRD Creator

A web-based interface for creating Ralph Mode loops and Product Requirements Documents (PRDs) using AI.

## Features

- **AI-Powered PRD Generation**: Uses local LLaMA models (via Ollama) or Grok API
- **OCR Support**: Extract ideas from screenshots and documents
- **Terminal Aesthetic**: Hacker-themed interface for the authentic Ralph Mode experience
- **Ralph Mode Format**: Generates structured PRDs with 5-phase task breakdown
- **JSON/Markdown Export**: Export your PRDs in multiple formats
- **Rate Limiting**: Built-in protection against abuse
- **Input Validation**: Protection against SQL injection and XSS attacks

## Quick Start

### Prerequisites

1. **Python 3.8+**
2. **Ollama** (for local LLaMA models) - Download from [ollama.com](https://ollama.com)
3. **Tesseract OCR** (optional, for image text extraction)

### Installation

```bash
# Navigate to the PRD Creator directory
cd prd-creator

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Generate a secret key
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

### Configuration

```bash
# Copy the environment template
cp .env.example .env

# Edit .env and add your SECRET_KEY
# You can also configure Ollama URL, Grok API key, etc.
```

### Pull Ollama Model

```bash
# Pull the LLaMA 3.2 model
ollama pull llama3.2
```

### Run the Application

```bash
python app.py
```

Visit `http://localhost:5000` in your browser.

## Project Structure

```
prd-creator/
├── app.py                    # Main Flask application
├── config.py                 # Security configuration
├── prd_engine.py             # PRD generation engine (LLaMA/Grok)
├── ocr_processor.py          # OCR text extraction
├── prd_store.py              # JSON file storage for PRDs
├── exceptions.py             # Custom error handling
├── requirements.txt          # Python dependencies
├── .env.example             # Environment template
├── .gitignore               # Git ignore rules
├── static/
│   └── css/
│       └── terminal.css     # Terminal theme styling
├── templates/
│   ├── base.html            # Base template
│   ├── index.html           # Landing page
│   ├── create.html          # PRD creation interface
│   ├── list.html            # List all PRDs
│   └── view.html            # View single PRD
└── tests/
    ├── test_prd_engine.py   # Unit tests for PRD engine
    ├── test_integration.py  # Integration tests
    └── test_load.py         # Load tests
```

## Usage

### Creating a PRD

1. Click **[CREATE NEW PRD]** on the home page
2. Fill in the project details:
   - **Project Name**: Name of your project
   - **Description**: Brief project description
   - **Starter Idea**: Detailed description of your project idea
3. Configure settings:
   - **AI Model**: Choose LLaMA (local) or Grok (API)
   - **Task Count**: Number of tasks to generate (10-100)
   - **Tech Stack**: Preset technology stack
4. Optionally upload an image for OCR extraction
5. Click **[GENERATE PRD]**

### Exporting PRDs

- **View PRD**: See the full PRD in the browser
- **Download JSON**: Export as JSON file
- **Download Markdown**: Export as readable Markdown

## API Endpoints

### Status

```
GET /api/status
```

Returns system status and statistics.

### Generate PRD

```
POST /api/prd/generate
Content-Type: application/json

{
  "project_name": "My Project",
  "description": "A brief description",
  "starter_prompt": "Detailed project idea...",
  "model": "llama3.2",
  "task_count": 34,
  "tech_stack": "python-flask"
}
```

### Get PRD

```
GET /api/prd/{prd_id}
```

Retrieve a saved PRD by ID.

### List PRDs

```
GET /api/prds?page=1&per_page=20
```

List all PRDs with pagination.

### Delete PRD

```
DELETE /api/prd/{prd_id}
```

Delete a PRD by ID.

### OCR Processing

```
POST /api/ocr
Content-Type: multipart/form-data

file: <image file>
```

Extract text from an uploaded image.

## Security Features

- **SECRET_KEY Validation**: Fails fast if secret key not configured
- **Input Validation**: Sanitizes all user inputs
- **SQL Injection Protection**: Detects and blocks SQL injection patterns
- **XSS Protection**: Detects and blocks XSS patterns
- **Rate Limiting**: Prevents abuse with configurable limits
- **Secure Sessions**: HTTPOnly, SameSite, HTTPS-only cookies

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run load tests (may take longer)
pytest tests/test_load.py -v

# Run specific test file
pytest tests/test_prd_engine.py -v
```

## Configuration Options

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `SECRET_KEY` | Flask secret key (required) | - |
| `FLASK_ENV` | Environment (development/production) | production |
| `OLLAMA_URL` | Ollama API URL | http://localhost:11434 |
| `OLLAMA_MODEL` | Default model name | llama3.2 |
| `GROK_API_KEY` | Grok API key (optional) | - |
| `TESSERACT_PATH` | Tesseract OCR path | /usr/bin/tesseract |
| `PRD_STORAGE_PATH` | PRD storage directory | ./prd_data |
| `RATE_LIMIT_PRD` | PRD generation rate limit | 10 per minute |
| `RATE_LIMIT_OCR` | OCR rate limit | 100 per hour |

## Troubleshooting

### Ollama Not Responding

```bash
# Check Ollama is running
ollama list

# Restart Ollama
# macOS: Click the Ollama menu bar icon -> Restart
# Linux: systemctl restart ollama
```

### Tesseract Not Found

```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

### Import Errors

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## Ralph Mode PRD Format

Generated PRDs follow the Ralph Mode structure:

```
{
  "pn": "project_name",           // Project name
  "pd": "project_description",    // Project description
  "sp": "starter_prompt",         // Complete build instructions
  "ts": {                         // Tech stack
    "lang": "Python",
    "fw": "Flask",
    "db": "PostgreSQL",
    "oth": ["Redis", "Celery"]
  },
  "fs": ["file1.py", ...],        // File structure
  "p": {                          // Tasks by phase
    "00_security": {
      "n": "Security",
      "t": [
        {
          "id": "SEC-001",
          "ti": "task_title",
          "d": "task_description",
          "f": "file.py",
          "pr": "critical"
        }
      ]
    },
    "01_setup": { ... },
    "02_core": { ... },
    "03_api": { ... },
    "04_test": { ... }
  }
}
```

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please read the contributing guidelines first.

## Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation
- Review troubleshooting section above
