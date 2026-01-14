# Ralph Mode PRD Creator - Implementation Plan

## Project Overview

**Project Name:** Ralph Mode PRD Creator
**Description:** A web-based interface for creating Ralph Mode loops and PRDs
**Tech Stack:** Python + Flask (no database required - JSON file storage)

---

## Phase 0: Project Initialization

### Directory Structure
```
prd-creator/
├── app.py                    # Main Flask application
├── config.py                 # Security configuration
├── requirements.txt          # Python dependencies
├── .env                      # Environment secrets (gitignored)
├── .env.example             # Environment template
├── .gitignore               # Git ignore rules
├── README.md                # Project documentation
├── prd_engine.py            # PRD generation engine (LLaMA/Grok)
├── ocr_processor.py         # OCR text extraction
├── prd_store.py             # JSON file storage for PRDs
├── static/
│   ├── css/
│   │   └── terminal.css     # Terminal theme styling
│   └── js/
│       └── app.js           # Frontend logic
└── templates/
    ├── base.html            # Base template
    ├── index.html           # Landing page
    ├── create.html          # PRD creation interface
    └── view.html            # View generated PRD
```

---

## Phase 1: Security Foundation (SEC-001 to SEC-003)

### SEC-001: Set up secret key
**File:** `config.py`
- Generate secure SECRET_KEY using `secrets.token_urlsafe(32)`
- Validate SECRET_KEY exists on startup (fail fast)
- Configure secure session cookies (HTTPS, HttpOnly, SameSite)
- Development vs Production configuration

### SEC-002: Configure OCR
**File:** `ocr_processor.py`
- Set up Tesseract OCR path configuration
- Handle missing Tesseract gracefully
- Add image preprocessing (resize, grayscale, noise reduction)
- Support multiple image formats (PNG, JPG, PDF)

### SEC-003: Initialize LLaMA model
**File:** `prd_engine.py`
- Set up Ollama API client for local LLaMA
- Configure fallback to Grok API
- Model selection (llama3.2, grok-2, etc.)
- Timeout and retry logic

### X-910/X-1000: Validate user input
**File:** `app.py` (validation decorator)
- Sanitize all user inputs (strip tags, escape HTML)
- Validate PRD name (alphanumeric, spaces, hyphens only)
- Validate prompt length (max 10,000 chars)
- Prevent command injection in OCR file paths

### X-911/X-1001: Implement rate limiting
**File:** `app.py`
- Use Flask-Limiter for API rate limiting
- Limit: 10 PRD creations per minute per IP
- Limit: 100 OCR requests per hour per IP
- Redis-backed or in-memory storage

---

## Phase 2: Core Setup (SET-001 to SET-002)

### SET-001: Create new PRD structure
**File:** `prd_store.py`
- Define PRD data model (Python class/TypedDict)
- PRD structure matches Ralph Mode format:
  - pn (project_name)
  - pd (project_description)
  - sp (starter_prompt)
  - ts (tech_stack)
  - fs (file_structure)
  - p (prds with tasks)
- JSON serialization/deserialization
- UUID generation for PRD IDs

### SET-002: Set up interface
**Files:** `templates/base.html`, `templates/index.html`, `static/css/terminal.css`
- Terminal/hacker aesthetic (reusing existing terminal.css)
- Clean, minimal interface
- Settings menu with dropdowns:
  - Model selection (LLaMA 3.2, Grok-2, GPT-4)
  - Task count (10, 20, 34, custom)
  - Tech stack presets (Python, JS, Rust, Go)
  - Output format (JSON, Markdown, Plain text)
- Form fields:
  - Project name
  - Project description
  - Starter prompt/idea
  - Upload image (OCR)
  - Generate button

---

## Phase 3: Core Processing (CORE-001 to CORE-002)

### CORE-001: Implement LLaMA model processing
**File:** `prd_engine.py`
```python
class PRDEngine:
    def __init__(self, model="llama3.2"):
        self.model = model
        self.client = Ollama(base_url=config.OLLAMA_URL)

    def generate_prd(self, project_name, description, starter_prompt, tech_stack, task_count=34):
        """Generate a complete Ralph Mode PRD using LLaMA"""
        prompt = self._build_prd_prompt(...)
        response = self.client.chat(model=self.model, messages=[...])
        return self._parse_prd_response(response)
```
- Build structured prompt for PRD generation
- Parse LLaMA response into PRD format
- Generate tasks across 5 categories (Security, Setup, Core, API, Test)
- Assign priorities and acceptance criteria

### CORE-002: Integrate Grok API
**File:** `prd_engine.py`
- Add Grok API client as fallback
- API key from environment variable
- Same prompt structure as LLaMA
- Graceful fallback if Ollama unavailable

### X-931/X-1005: Implement caching
**File:** `prd_engine.py`
- Cache generated PRDs by prompt hash
- TTL: 24 hours
- In-memory or Redis-backed
- Cache invalidation on model config change

### X-932: Enhanced error handling
**File:** `exceptions.py`
- Custom exceptions: PRDGenerationError, OCRError, ModelUnavailableError
- User-friendly error messages
- Logging with structured format
- Retry with exponential backoff for API calls

---

## Phase 4: API & Handlers (API-001)

### API-001: Create API endpoint for PRD creation
**File:** `app.py`
```python
@app.route('/api/prd/generate', methods=['POST'])
@limiter.limit("10/minute")
def generate_prd():
    data = request.get_json()
    # Validate input
    # Process OCR if image provided
    # Generate PRD using engine
    # Return JSON PRD
    return jsonify({"prd": prd_dict, "id": prd_id})
```

**Additional endpoints:**
- `GET /api/prd/<prd_id>` - Retrieve saved PRD
- `GET /api/prds` - List all PRDs
- `POST /api/prd/<prd_id>/export` - Export to file (JSON/MD)
- `DELETE /api/prd/<prd_id>` - Delete PRD

### X-941/X-1007: Implement API pagination
**File:** `app.py`
- Pagination for `/api/prds` endpoint
- Default: 20 per page, max 100
- Cursor-based or offset-based

---

## Phase 5: Testing (TEST-001)

### TEST-001: Write unit tests for LLaMA model processing
**File:** `tests/test_prd_engine.py`
- Mock Ollama API responses
- Test PRD parsing logic
- Test error handling
- Test prompt building

### X-951: Implement integration testing
**File:** `tests/test_integration.py`
- Test full PRD generation flow
- Test OCR integration
- Test API endpoints
- Test file storage

### X-1010: Load testing
**File:** `tests/test_load.py`
- Simulate concurrent PRD generation
- Test rate limiting
- Test cache performance
- Use pytest-xdist for parallel testing

---

## Implementation Order

1. **Phase 0** - Create directory structure, virtualenv, .gitignore
2. **Phase 1** - Security setup (config.py, requirements.txt)
3. **Phase 2** - Basic interface and PRD data model
4. **Phase 3** - Core LLaMA/Grok integration
5. **Phase 4** - API endpoints
6. **Phase 5** - Testing suite

---

## Dependencies

```
Flask==3.0.0
Flask-Limiter==3.5.0
python-dotenv==1.0.0
requests==2.31.0
ollama==0.1.0
pytesseract==0.3.10
Pillow==10.1.0
pytest==7.4.3
pytest-cov==4.1.0
pytest-xdist==3.5.0
```

---

## Environment Variables (.env.example)

```
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
OLLAMA_URL=http://localhost:11434
GROK_API_KEY=your-grok-api-key
TESSERACT_PATH=/usr/bin/tesseract
MAX_CONTENT_LENGTH=10485760
```

---

## Success Criteria

- [ ] User can create a PRD via web interface
- [ ] OCR extracts text from uploaded images
- [ ] LLaMA generates valid Ralph Mode PRD format
- [ ] Grok API works as fallback
- [ ] PRDs are saved and retrievable
- [ ] Rate limiting prevents abuse
- [ ] All tests pass with >80% coverage
- [ ] Terminal UI is responsive and clean
