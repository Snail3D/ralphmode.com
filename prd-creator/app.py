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
    """Landing page."""
    return render_template('index.html')


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

    app.run(host='0.0.0.0', port=5000, debug=DEBUG)
