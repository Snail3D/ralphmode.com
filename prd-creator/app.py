"""
Ralph Mode PRD Creator - Main Flask Application

SEC-001: SECRET_KEY validation (via config.py)
SEC-002: OCR Configuration (via ocr_processor.py)
SEC-003: LLaMA Model Initialization (via prd_engine.py)
X-910/X-1000: Input Validation
X-911/X-1001: Rate Limiting
API-001: API endpoint for PRD creation
"""
import os
import json
import logging
from io import BytesIO
from functools import wraps
from typing import Dict, Any

from flask import (
    Flask, render_template, request, jsonify, Response,
    session, redirect, url_for, flash
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename

from config import (
    SECRET_KEY, DEBUG, ALLOWED_PROJECT_NAME_CHARS,
    MAX_PROJECT_NAME_LENGTH, MAX_DESCRIPTION_LENGTH,
    MAX_PROMPT_LENGTH, PRD_STORAGE_PATH, UPLOAD_FOLDER,
    OLLAMA_URL, OLLAMA_MODEL
)
from exceptions import (
    PRDCreatorError, ValidationError, OCRError,
    PRDGenerationError, RateLimitError, handle_error
)
from prd_engine import get_prd_engine
from prd_store import get_prd_store, PRD
from ocr_processor import get_ocr_processor
import ralph
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO if DEBUG else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)

# Initialize rate limiter (X-911/X-1001)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Initialize components
prd_engine = get_prd_engine()
prd_store = get_prd_store()


# ============================================================================
# DECORATORS
# ============================================================================

def validate_request(f):
    """
    X-910/X-1000: Validate user input decorator
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Validate JSON content type for POST/PUT
        if request.method in ['POST', 'PUT'] and request.is_json:
            data = request.get_json()

            # Check for potential injection patterns
            for key, value in data.items():
                if isinstance(value, str):
                    # Check for SQL injection patterns
                    sql_patterns = ['--', ';', '/*', '*/', 'xp_', 'sp_']
                    if any(pattern in value.lower() for pattern in sql_patterns):
                        logger.warning(f"Potential SQL injection in {key}")
                        return jsonify(handle_error(ValidationError(
                            "Invalid input detected",
                            field=key
                        ))), 400

                    # Check for XSS patterns
                    xss_patterns = ['<script', 'javascript:', 'onerror=', 'onload=']
                    if any(pattern in value.lower() for pattern in xss_patterns):
                        logger.warning(f"Potential XSS in {key}")
                        return jsonify(handle_error(ValidationError(
                            "Invalid input detected",
                            field=key
                        ))), 400

        return f(*args, **kwargs)
    return decorated_function


def validate_project_name(name: str) -> None:
    """Validate project name."""
    if not name or len(name) > MAX_PROJECT_NAME_LENGTH:
        raise ValidationError(
            f"Project name must be 1-{MAX_PROJECT_NAME_LENGTH} characters",
            field="project_name",
            value=name
        )

    # Check for allowed characters
    invalid_chars = set(name) - ALLOWED_PROJECT_NAME_CHARS
    if invalid_chars:
        raise ValidationError(
            f"Invalid characters in project name: {', '.join(invalid_chars)}",
            field="project_name",
            value=name
        )


def validate_tech_stack(tech_stack: str) -> Dict[str, Any]:
    """Convert tech stack preset to dict."""
    presets = {
        "python-flask": {"lang": "Python", "fw": "Flask", "db": "None", "oth": []},
        "python-fastapi": {"lang": "Python", "fw": "FastAPI", "db": "PostgreSQL", "oth": ["Redis"]},
        "javascript-node": {"lang": "JavaScript", "fw": "Node.js", "db": "MongoDB", "oth": []},
        "rust-axum": {"lang": "Rust", "fw": "Axum", "db": "PostgreSQL", "oth": ["Redis"]},
        "go-gin": {"lang": "Go", "fw": "Gin", "db": "PostgreSQL", "oth": []},
    }

    if tech_stack not in presets:
        raise ValidationError(
            f"Invalid tech stack preset: {tech_stack}",
            field="tech_stack",
            value=tech_stack
        )

    return presets[tech_stack]


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return render_template('base.html', content="<h1 style='color:#00ff00'>404 - NOT FOUND</h1>"), 404


@app.errorhandler(500)
def server_error(error):
    logger.exception("Server error")
    return render_template('base.html', content="<h1 style='color:#ff0000'>500 - SERVER ERROR</h1>"), 500


@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify(handle_error(RateLimitError(
        "Rate limit exceeded",
        limit=str(e.description)
    ))), 429


# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    """Landing page - redirect to chat."""
    return redirect(url_for('chat_new'))


@app.route('/create')
def create_prd():
    """PRD creation page."""
    return render_template('create.html')


@app.route('/prds')
def list_prds():
    """List all saved PRDs with pagination."""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    offset = (page - 1) * per_page
    prds = prd_store.list_all(limit=per_page, offset=offset)

    total = prd_store.count()
    total_pages = (total + per_page - 1) // per_page

    return render_template('list.html', prds=prds, page=page, total_pages=total_pages)


@app.route('/prd/<prd_id>')
def view_prd(prd_id: str):
    """View a single PRD."""
    try:
        prd = prd_store.load(prd_id)
        return render_template('view.html', prd=prd, prd_dict=prd.to_ralph_format())
    except Exception as e:
        flash(f'PRD not found: {prd_id}', 'error')
        return redirect(url_for('list_prds'))


# ============================================================================
# CHAT ROUTES (Ralph)
# ============================================================================

@app.route('/chat')
def chat_new():
    """Create a new chat session."""
    new_session_id = str(uuid.uuid4())
    return redirect(url_for('chat_session', session_id=new_session_id))


@app.route('/chat/<session_id>')
def chat_session(session_id: str):
    """Chat with Ralph - split view with live PRD editor."""
    chat = ralph.get_chat_session(session_id)
    messages = chat.conversation_state.get("messages", [])

    # Convert messages to format expected by template
    formatted_messages = []
    for msg in messages:
        formatted_messages.append({
            "role": msg["role"],
            "content": msg["content"],
            "actions": []  # Actions are generated dynamically
        })

    # Get initial PRD state for the editor
    initial_prd = None
    if chat.get_prd():
        initial_prd = ralph.compress_prd(chat.get_prd())

    # Get all sessions for sidebar
    all_sessions = ralph.list_chat_sessions()

    return render_template('split_chat.html',
                         session_id=session_id,
                         messages=formatted_messages,
                         chats=all_sessions,
                         current_chat_id=session_id,
                         initial_prd=initial_prd)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/status')
def api_status():
    """Get system status."""
    try:
        # Check Ollama availability
        import requests
        ollama_available = False
        try:
            response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=1)
            ollama_available = response.status_code == 200
        except:
            pass

        return jsonify({
            "status": "online",
            "model": OLLAMA_MODEL,
            "model_available": ollama_available,
            "prd_count": prd_store.count()
        })
    except Exception as e:
        return jsonify({
            "status": "online",
            "model": OLLAMA_MODEL,
            "model_available": False,
            "prd_count": prd_store.count(),
            "error": str(e)
        })


@app.route('/api/chat', methods=['POST'])
@limiter.limit("60 per minute")
def api_chat():
    """
    Chat with Ralph API endpoint.

    Handles conversational PRD building with Ralph.
    Returns PRD preview for live editor updates.
    Also handles: gender_toggle, suggestion_id, vote
    """
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        session_id = data.get('session_id', '')

        # Ralph-specific parameters
        action = data.get('action')
        suggestion_id = data.get('suggestion_id')
        vote = data.get('vote')
        gender_toggle = data.get('gender_toggle')

        if not message and not action and not suggestion_id and not gender_toggle:
            return jsonify({"error": "Message or action is required"}), 400

        # Get or create chat session
        if session_id:
            chat = ralph.get_chat_session(session_id)
        else:
            chat = ralph.get_chat_session(str(uuid.uuid4()))
            session_id = chat.session_id

        # Process message/action and get response
        # Ralph returns: (response, suggestions, prd_preview, backroom)
        result = chat.process_message(
            message=message,
            action=action,
            suggestion_id=suggestion_id,
            vote=vote,
            gender_toggle=gender_toggle
        )

        # Handle both old return format and new Ralph format
        if len(result) == 3:
            response_text, actions, prd_preview = result
            backroom = None
            suggestions = []
        elif len(result) == 4:
            response_text, suggestions, prd_preview, backroom = result
            actions = []
        else:
            response_text = result[0] if result else "Something went wrong"
            actions = []
            suggestions = []
            prd_preview = None
            backroom = None

        return jsonify({
            "success": True,
            "session_id": session_id,
            "is_new": len(chat.conversation_state.get("messages", [])) <= 2,
            "message": response_text,
            "actions": actions,
            "suggestions": suggestions,
            "prd_preview": prd_preview,
            "backroom": backroom,
            "has_prd": chat.get_prd() is not None
        })

    except Exception as e:
        logger.exception("Chat API error")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "*scratches head*\n\nWell slap my thigh! Something went wrong. Please try again."
        }), 500


@app.route('/api/chat/reset', methods=['POST'])
def api_reset_chat():
    """
    Reset/clear conversation and start fresh.
    Creates a new session and redirects to it.
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id', '')

        # Remove old session from memory
        if session_id and session_id in ralph._sessions:
            del ralph._sessions[session_id]

        # Create new session
        new_session_id = str(uuid.uuid4())

        return jsonify({
            "success": True,
            "new_session_id": new_session_id
        })

    except Exception as e:
        logger.exception("Reset error")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# OLLAMA MODEL MANAGEMENT API
# ============================================================================

@app.route('/api/ollama/models')
def api_ollama_models():
    """Get list of installed Ollama models."""
    try:
        import requests
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)

        if response.status_code == 200:
            data = response.json()
            models = []

            if 'models' in data:
                for model in data['models']:
                    models.append({
                        'name': model['name'],
                        'size': model.get('size', 0),
                        'modified': model.get('modified_at', '')
                    })

            return jsonify({
                "success": True,
                "models": models
            })
        else:
            return jsonify({
                "success": False,
                "error": "Ollama not responding"
            }), 503

    except Exception as e:
        logger.exception("Ollama models error")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/ollama/search')
def api_ollama_search():
    """Search for Ollama models in the library."""
    try:
        query = request.args.get('q', '')

        # Ollama library search - using a predefined list of popular models
        # In production, you'd scrape ollama.com/library or use their API
        popular_models = [
            {"name": "llama3.2", "description": "Meta's Llama 3.2 - 3B parameter model"},
            {"name": "llama3.2:1b", "description": "Meta's Llama 3.2 - 1B parameter model (lightweight)"},
            {"name": "llama3.1", "description": "Meta's Llama 3.1 - 8B parameter model"},
            {"name": "llama3", "description": "Meta's Llama 3 - 70B parameter model"},
            {"name": "mistral", "description": "Mistral 7B - high quality open source model"},
            {"name": "mixtral", "description": "Mixtral 8x7B - mixture of experts model"},
            {"name": "codellama", "description": "Code Llama - model fine-tuned for coding"},
            {"name": "deepseek-coder", "description": "DeepSeek Coder - specialized for code"},
            {"name": "phi3", "description": "Microsoft Phi-3 - 3.8B parameter model"},
            {"name": "gemma2", "description": "Google Gemma 2 - lightweight yet powerful"},
            {"name": "qwen2.5", "description": "Alibaba Qwen 2.5 - multilingual model"},
            {"name": "nomic-embed-text", "description": "Nomic embedding model for text"},
        ]

        # Filter by query
        if query:
            filtered = [m for m in popular_models if query.lower() in m['name'].lower()]
        else:
            filtered = popular_models[:10]

        return jsonify({
            "success": True,
            "models": filtered
        })

    except Exception as e:
        logger.exception("Ollama search error")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/ollama/pull', methods=['POST'])
@limiter.limit("10 per hour")
def api_ollama_pull():
    """Pull/download an Ollama model."""
    try:
        data = request.get_json()
        model = data.get('model', '')

        if not model:
            return jsonify({"error": "Model name is required"}), 400

        import requests
        # Pull model (this is async, will take time)
        response = requests.post(
            f"{OLLAMA_URL}/api/pull",
            json={"name": model},
            timeout=300  # 5 minute timeout
        )

        if response.status_code == 200:
            return jsonify({
                "success": True,
                "message": f"Model {model} pulled successfully"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to pull model"
            }), 500

    except Exception as e:
        logger.exception("Ollama pull error")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================================
# BACKROOM DEBATE API
# ============================================================================

@app.route('/api/backroom/debate', methods=['POST'])
@limiter.limit("20 per hour")
def api_backroom_debate():
    """
    Generate a backroom debate between Stool (skeptic) and Gomer (optimist).
    Returns 10 exchanges (5 each) with typing effect for display.
    """
    try:
        data = request.get_json()
        context = data.get('context', 'Building a web application')

        # Import for LLM calls
        import requests

        # Define analyst personas
        ANALYST_A = {"name": "Stool", "role": "The Skeptic", "emoji": "🤔"}
        ANALYST_B = {"name": "Gomer", "role": "The Optimist", "emoji": "💡"}

        # Build the debate
        exchanges = []

        # First message - Stool starts
        prompt_1 = f"""Stool (skeptic) analyzing project. 1-2 sentences MAX.
CTX: {context}
Question ONE thing: need, problem, or gap. Direct, punchy."""

        response_1 = query_llm(prompt_1)
        if response_1:
            exchanges.append({"analyst": "Stool", "message": response_1})

        # Generate 9 more exchanges (alternating)
        for i in range(9):
            last_msg = exchanges[-1]["message"]

            if i % 2 == 0:  # Gomer's turn
                prompt = f"""Gomer (optimist) responds. 1-2 sentences MAX.
CTX: {context}
STOOL: {last_msg}
Counter with ONE use case or opportunity. Punchy."""
                analyst = "Gomer"
            else:  # Stool's turn
                prompt = f"""Stool (skeptic) responds. 1-2 sentences MAX.
CTX: {context}
GOMER: {last_msg}
ONE concern or edge case. Acknowledge good points briefly."""
                analyst = "Stool"

            response = query_llm(prompt)
            if response:
                exchanges.append({"analyst": analyst, "message": response})

        return jsonify({
            "success": True,
            "debate": exchanges
        })

    except Exception as e:
        logger.exception("Backroom debate error")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def query_llm(prompt: str) -> str:
    """Query the LLM (Ollama or Grok) with a prompt."""
    try:
        import requests

        # Check if Grok API key is configured
        grok_api_key = os.environ.get("GROK_API_KEY") or os.environ.get("GROQ_API_KEY")

        if grok_api_key:
            # Use Grok/Groq
            try:
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {grok_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.8,
                        "max_tokens": 150
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"].strip()
            except:
                pass  # Fall through to Ollama

        # Use Ollama
        ollama_model = os.environ.get("OLLAMA_MODEL", "llama3.2")
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.8, "num_predict": 150}
            },
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            return data.get("response", "").strip()

        return ""

    except Exception as e:
        logger.error(f"LLM query error: {e}")
        return ""


@app.route('/api/chat/backroom-add', methods=['POST'])
def api_backroom_add():
    """Add an approved backroom message to the PRD."""
    try:
        data = request.get_json()
        session_id = data.get('session_id', '')
        analyst = data.get('analyst', '')
        message = data.get('message', '')

        chat = ralph.get_chat_session(session_id)
        prd = chat.get_prd()

        if not prd:
            return jsonify({"success": False, "error": "No PRD yet"}), 400

        # Add as a task based on the analyst's perspective
        task_id = f"BACK-{len(prd.get('p', {}).get('02_core', {}).get('t', [])) + 1}"

        if analyst == 'Stool':
            # Skeptic concerns → Security/Validation tasks
            prd['p']['00_security']['t'].append({
                "id": task_id,
                "ti": f"Address: {message[:50]}",
                "d": f"Security concern from backroom: {message}",
                "f": "security.py",
                "pr": "high"
            })
        else:
            # Optimist suggestions → Feature tasks
            prd['p']['02_core']['t'].append({
                "id": task_id,
                "ti": f"Feature: {message[:50]}",
                "d": f"Feature suggestion from backroom: {message}",
                "f": "features.py",
                "pr": "medium"
            })

        # Update PRD display
        prd_preview = ralph.compress_prd(prd)

        return jsonify({
            "success": True,
            "prd_preview": prd_preview,
            "message": f"*nods* Added {analyst}'s point to your PRD!"
        })

    except Exception as e:
        logger.exception("Backroom add error")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/chat/summarize', methods=['POST'])
def api_summarize_prd():
    """Generate a summary and update the PRD."""
    try:
        data = request.get_json()
        session_id = data.get('session_id', '')

        chat = ralph.get_chat_session(session_id)
        prd = chat.get_prd()

        if not prd:
            return jsonify({"success": False, "error": "No PRD yet"}), 400

        # Add summary task
        total_tasks = sum(len(cat.get("t", [])) for cat in prd.get("p", {}).values())

        prd_preview = ralph.compress_prd(prd)

        return jsonify({
            "success": True,
            "prd_preview": prd_preview,
            "total_tasks": total_tasks,
            "message": f"*beams proudly* Your PRD now has {total_tasks} tasks!"
        })

    except Exception as e:
        logger.exception("Summarize error")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/chat/<session_id>/export/<format>')
def api_export_chat_prd(session_id: str, format: str):
    """Export PRD from chat session."""
    try:
        chat = ralph.get_chat_session(session_id)
        prd = chat.get_prd()

        if not prd:
            return jsonify({"error": "No PRD generated yet"}), 404

        if format == 'json':
            response = Response(
                json.dumps(prd, indent=2),
                mimetype='application/json',
                headers={
                    'Content-Disposition': f'attachment; filename="prd-{prd.get("pn", "project")}.json"'
                }
            )
            return response

        elif format == 'markdown':
            md = f"# {prd.get('pn', 'Project')}\n\n"
            md += f"**Description:** {prd.get('pd', 'N/A')}\n\n"
            md += f"## Tech Stack\n\n"
            ts = prd.get('ts', {})
            md += f"- Language: {ts.get('lang', 'N/A')}\n"
            md += f"- Framework: {ts.get('fw', 'N/A')}\n"
            md += f"- Database: {ts.get('db', 'N/A')}\n"
            if ts.get('oth'):
                md += f"- Other: {', '.join(ts['oth'])}\n"
            md += f"\n## File Structure\n\n"
            for f in prd.get('fs', []):
                md += f"- `{f}`\n"
            md += f"\n## Tasks\n\n"
            for cat_id, cat in prd.get('p', {}).items():
                md += f"### {cat['n']} [{cat_id}]\n\n"
                for task in cat['t']:
                    md += f"#### {task['id']} [{task['pr']}]\n\n"
                    md += f"**{task['ti']}**\n\n"
                    md += f"- {task['d']}\n"
                    md += f"- File: `{task['f']}`\n\n"

            response = Response(
                md,
                mimetype='text/markdown',
                headers={
                    'Content-Disposition': f'attachment; filename="prd-{prd.get("pn", "project")}.md"'
                }
            )
            return response

        elif format == 'compressed':
            # Return compressed format (like Telegram) - includes full legend
            compressed = ralph.compress_prd(prd)
            response = Response(
                compressed,
                mimetype='text/plain',
                headers={
                    'Content-Disposition': f'attachment; filename="prd-{prd.get("pn", "project")}.txt"'
                }
            )
            return response

        else:
            return jsonify({"error": "Invalid format. Use: json, markdown, or compressed"}), 400

    except Exception as e:
        logger.exception("Export error")
        return jsonify({"error": str(e)}), 500


@app.route('/api/ocr', methods=['POST'])
@limiter.limit("100 per hour")
def api_ocr():
    """
    Extract text from uploaded image using OCR.

    X-911/X-1001: Rate limited to 100 requests per hour
    """
    if 'file' not in request.files:
        return jsonify(handle_error(ValidationError("No file uploaded"))), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify(handle_error(ValidationError("No file selected"))), 400

    try:
        # Read file data
        data = file.read()
        text = get_ocr_processor().extract_from_bytes(data, file.filename)

        return jsonify({
            "success": True,
            "text": text
        })
    except OCRError as e:
        return jsonify(handle_error(e)), 400
    except Exception as e:
        return jsonify(handle_error(e)), 500


@app.route('/api/prd/generate', methods=['POST'])
@limiter.limit("10 per minute")  # X-911/X-1001: Rate limiting
@validate_request  # X-910/X-1000: Input validation
def api_generate_prd():
    """
    API-001: API endpoint for PRD creation

    Generates a Ralph Mode PRD based on user input.
    """
    try:
        data = request.get_json()

        # Extract fields
        project_name = data.get('project_name', '').strip()
        description = data.get('description', '').strip()
        starter_prompt = data.get('starter_prompt', '').strip()
        model = data.get('model', OLLAMA_MODEL)
        task_count = data.get('task_count', 34)
        tech_stack_preset = data.get('tech_stack', 'python-flask')

        # Validate inputs
        validate_project_name(project_name)

        if not description or len(description) > MAX_DESCRIPTION_LENGTH:
            raise ValidationError(
                f"Description must be 1-{MAX_DESCRIPTION_LENGTH} characters",
                field="description"
            )

        if not starter_prompt or len(starter_prompt) > MAX_PROMPT_LENGTH:
            raise ValidationError(
                f"Starter prompt must be 1-{MAX_PROMPT_LENGTH} characters",
                field="starter_prompt"
            )

        if task_count < 5 or task_count > 100:
            raise ValidationError(
                "Task count must be between 5 and 100",
                field="task_count",
                value=task_count
            )

        tech_stack = validate_tech_stack(tech_stack_preset)

        # Generate PRD
        logger.info(f"Generating PRD: {project_name} with {model}, {task_count} tasks")
        prd_data = prd_engine.generate_prd(
            project_name=project_name,
            description=description,
            starter_prompt=starter_prompt,
            tech_stack=tech_stack,
            task_count=task_count
        )

        # Create PRD object and save
        prd = PRD.from_ralph_format(prd_data)
        prd_id = prd_store.save(prd)

        logger.info(f"PRD generated and saved: {prd_id}")

        return jsonify({
            "success": True,
            "id": prd_id,
            "project_name": prd.project_name,
            "prd": prd_data
        })

    except ValidationError as e:
        return jsonify(handle_error(e)), 400
    except PRDGenerationError as e:
        return jsonify(handle_error(e)), 500
    except Exception as e:
        logger.exception("Unexpected error in PRD generation")
        return jsonify(handle_error(e)), 500


@app.route('/api/prd/<prd_id>', methods=['GET'])
def api_get_prd(prd_id: str):
    """Get a PRD by ID."""
    try:
        prd = prd_store.load(prd_id)
        return jsonify({
            "success": True,
            "prd": prd.to_dict()
        })
    except Exception as e:
        return jsonify(handle_error(e)), 404


@app.route('/api/prd/<prd_id>', methods=['DELETE'])
def api_delete_prd(prd_id: str):
    """Delete a PRD by ID."""
    try:
        if prd_store.delete(prd_id):
            return jsonify({"success": True})
        else:
            return jsonify(handle_error(ValidationError("PRD not found", prd_id=prd_id))), 404
    except Exception as e:
        return jsonify(handle_error(e)), 500


@app.route('/api/prds', methods=['GET'])
def api_list_prds():
    """
    X-941/X-1007: API pagination
    List all PRDs with pagination support.
    """
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    offset = (page - 1) * per_page
    prds = prd_store.list_all(limit=per_page, offset=offset)

    total = prd_store.count()
    total_pages = (total + per_page - 1) // per_page

    return jsonify({
        "success": True,
        "prds": prds,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages
        }
    })


# ============================================================================
# EXPORT ENDPOINTS
# ============================================================================

@app.route('/prd/<prd_id>/export/json')
def export_json(prd_id: str):
    """Export PRD as JSON file."""
    try:
        prd = prd_store.load(prd_id)
        import json
        response = Response(
            json.dumps(prd.to_ralph_format(), indent=2),
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename=prd-{prd.project_name}.json'
            }
        )
        return response
    except Exception as e:
        flash(f'Failed to export: {e}', 'error')
        return redirect(url_for('view_prd', prd_id=prd_id))


@app.route('/prd/<prd_id>/export/markdown')
def export_markdown(prd_id: str):
    """Export PRD as Markdown file."""
    try:
        prd = prd_store.load(prd_id)
        rd = prd.to_ralph_format()

        md = f"# {rd['pn']}\n\n"
        md += f"**Description:** {rd['pd']}\n\n"
        md += f"## Starter Prompt\n\n{rd['sp']}\n\n"
        md += f"## Tech Stack\n\n"
        md += f"- Language: {rd['ts'].get('lang', 'N/A')}\n"
        md += f"- Framework: {rd['ts'].get('fw', 'N/A')}\n"
        md += f"- Database: {rd['ts'].get('db', 'N/A')}\n"
        if rd['ts'].get('oth'):
            md += f"- Other: {', '.join(rd['ts']['oth'])}\n"
        md += f"\n## File Structure\n\n"
        for f in rd['fs']:
            md += f"- `{f}`\n"
        md += f"\n## Tasks\n\n"

        for cat_id, cat in rd['p'].items():
            md += f"### {cat['n']} [{cat_id}]\n\n"
            for task in cat['t']:
                md += f"#### {task['id']} [{task['pr']}]\n\n"
                md += f"**{task['ti']}**\n\n"
                md += f"- Description: {task['d']}\n"
                md += f"- File: `{task['f']}`\n\n"

        response = Response(
            md,
            mimetype='text/markdown',
            headers={
                'Content-Disposition': f'attachment; filename=prd-{prd.project_name}.md'
            }
        )
        return response
    except Exception as e:
        flash(f'Failed to export: {e}', 'error')
        return redirect(url_for('view_prd', prd_id=prd_id))


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║              ███████╗██╗   ██╗██████╗ ████████╗                   ║
║              ██╔════╝██║   ██║██╔══██╗╚══██╔══╝                   ║
║              ███████╗██║   ██║██████╔╝   ██║                      ║
║              ╚════██║██║   ██║██╔══██╗   ██║                      ║
║              ███████║╚██████╔╝██████╔╝   ██║                      ║
║              ╚══════╝ ╚═════╝ ╚═════╝    ╚═╝                      ║
║                                                                   ║
║                    P R D   C R E A T O R                          ║
║                                                                   ║
║                   [Starting Flask Server...]                      ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """)

    print(f"> Model: {OLLAMA_MODEL}")
    print(f"> Ollama URL: {OLLAMA_URL}")
    print(f"> Storage: {PRD_STORAGE_PATH}")
    print(f"> Debug: {DEBUG}")
    print()

    app.run(host='0.0.0.0', port=8000, debug=DEBUG)
