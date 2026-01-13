"""
Recipe API Client - Connects to RalphMode.com for hotties (past recipes)

Features:
- LOCAL recipe storage (~/.ralph/recipes/) - FREE, save your recipes!
- QR code generation for easy recall - FREE
- Whole recipe search (find similar projects)
- Granular task search (find popular task snippets)
- Upvote/popularity ranking system
- Model quality tiers for search ranking
- Cloud sync (future feature for cross-device access)
"""

import aiohttp
import json
import logging
import hashlib
import re
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

# Local recipe storage
RALPH_HOME = Path.home() / ".ralph"
RECIPES_DIR = RALPH_HOME / "recipes"
RECIPES_INDEX = RALPH_HOME / "recipes_index.json"


# ============ LOCAL RECIPE STORAGE ============

@dataclass
class Recipe:
    """A saved recipe with PRD and metadata"""
    id: str
    name: str
    description: str
    prd: Dict
    tags: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    cloud_synced: bool = False
    paid: bool = False  # future: cloud storage tier
    # Model tracking for quality ranking
    model: str = ""  # e.g., "llama3.1:8b", "gpt-4", "claude-3-opus"
    provider: str = ""  # e.g., "local", "groq", "openai"
    model_quality_tier: int = 1  # 1=basic, 2=mid, 3=advanced, 4=frontier

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at
        # Auto-calculate quality tier based on model
        if not self.model_quality_tier or self.model_quality_tier == 1:
            self.model_quality_tier = calculate_model_tier(self.model)


# Model quality tiers for ranking
MODEL_TIERS = {
    # Tier 4: Frontier models (best)
    "claude-3-opus": 4, "claude-opus": 4, "gpt-4-turbo": 4, "gpt-4o": 4,
    "claude-3.5-sonnet": 4, "claude-sonnet": 4,
    # Tier 3: Advanced models
    "gpt-4": 3, "claude-3-sonnet": 3, "llama-3.1-405b": 3,
    "llama3.1:70b": 3, "llama-3.3-70b": 3, "qwen2.5:72b": 3,
    "mixtral-8x22b": 3,
    # Tier 2: Mid-tier models
    "gpt-3.5-turbo": 2, "claude-3-haiku": 2,
    "llama3.1:8b": 2, "llama-3.1-8b": 2, "llama3:8b": 2,
    "mistral:7b": 2, "mixtral-8x7b": 2, "gemma2-9b": 2,
    "qwen2.5:14b": 2, "deepseek-coder": 2,
    # Tier 1: Basic models
    "llama3.2:3b": 1, "phi3:mini": 1, "gemma:2b": 1,
    "tinyllama": 1, "qwen2.5:3b": 1,
}


def calculate_model_tier(model: str) -> int:
    """Calculate quality tier for a model (1-4, higher is better)"""
    if not model:
        return 1
    model_lower = model.lower()
    for model_name, tier in MODEL_TIERS.items():
        if model_name in model_lower:
            return tier
    # Default to tier 2 for unknown models
    return 2


def ensure_recipes_dir():
    """Ensure recipes directory exists"""
    RALPH_HOME.mkdir(exist_ok=True)
    RECIPES_DIR.mkdir(exist_ok=True)
    if not RECIPES_INDEX.exists():
        RECIPES_INDEX.write_text("{}")


def generate_recipe_id() -> str:
    """Generate unique recipe ID"""
    return f"RALPH-{uuid.uuid4().hex[:8].upper()}"


def save_recipe(
    name: str,
    description: str,
    prd: Dict,
    tags: List[str] = None,
    recipe_id: str = None,
    model: str = "",
    provider: str = ""
) -> str:
    """
    Save a recipe locally with model tracking for quality ranking.
    Returns the recipe ID.
    """
    ensure_recipes_dir()

    if not recipe_id:
        recipe_id = generate_recipe_id()

    # Calculate model quality tier
    quality_tier = calculate_model_tier(model)

    recipe = Recipe(
        id=recipe_id,
        name=name,
        description=description,
        prd=sanitize_prd(prd),
        tags=tags or [],
        updated_at=datetime.now().isoformat(),
        model=model,
        provider=provider,
        model_quality_tier=quality_tier
    )

    # Save recipe file
    recipe_file = RECIPES_DIR / f"{recipe_id}.json"
    recipe_file.write_text(json.dumps(asdict(recipe), indent=2))

    # Update index with model info for ranking
    index = load_recipes_index()
    index[recipe_id] = {
        "name": name,
        "description": description[:100],
        "tags": tags or [],
        "created_at": recipe.created_at,
        "updated_at": recipe.updated_at,
        "cloud_synced": False,
        "paid": False,
        "model": model,
        "provider": provider,
        "model_quality_tier": quality_tier
    }
    save_recipes_index(index)

    logger.info(f"Recipe saved: {recipe_id} - {name} (model: {model}, tier: {quality_tier})")
    return recipe_id


def load_recipe(recipe_id: str) -> Optional[Recipe]:
    """Load a recipe by ID"""
    ensure_recipes_dir()

    recipe_file = RECIPES_DIR / f"{recipe_id}.json"
    if not recipe_file.exists():
        logger.warning(f"Recipe not found: {recipe_id}")
        return None

    try:
        data = json.loads(recipe_file.read_text())
        return Recipe(**data)
    except Exception as e:
        logger.error(f"Error loading recipe {recipe_id}: {e}")
        return None


def delete_recipe(recipe_id: str) -> bool:
    """Delete a recipe"""
    ensure_recipes_dir()

    recipe_file = RECIPES_DIR / f"{recipe_id}.json"
    if recipe_file.exists():
        recipe_file.unlink()

    # Update index
    index = load_recipes_index()
    if recipe_id in index:
        del index[recipe_id]
        save_recipes_index(index)

    return True


def list_local_recipes() -> List[Dict]:
    """List all locally saved recipes"""
    ensure_recipes_dir()
    index = load_recipes_index()

    recipes = []
    for recipe_id, meta in index.items():
        recipes.append({
            "id": recipe_id,
            **meta
        })

    # Sort by updated_at descending
    return sorted(recipes, key=lambda x: x.get("updated_at", ""), reverse=True)


def load_recipes_index() -> Dict:
    """Load the recipes index"""
    ensure_recipes_dir()
    try:
        return json.loads(RECIPES_INDEX.read_text())
    except:
        return {}


def save_recipes_index(index: Dict):
    """Save the recipes index"""
    ensure_recipes_dir()
    RECIPES_INDEX.write_text(json.dumps(index, indent=2))


def search_local_recipes(query: str) -> List[Dict]:
    """Search locally saved recipes, ranked by relevance AND model quality"""
    recipes = list_local_recipes()
    query_lower = query.lower()

    results = []
    for recipe in recipes:
        score = 0
        if query_lower in recipe.get("name", "").lower():
            score += 20
        if query_lower in recipe.get("description", "").lower():
            score += 10
        for tag in recipe.get("tags", []):
            if query_lower in tag.lower():
                score += 15

        if score > 0:
            # Boost score by model quality tier (tier 4 = +40, tier 1 = +10)
            model_tier = recipe.get("model_quality_tier", 1)
            model_boost = model_tier * 10
            final_score = score + model_boost

            results.append({
                **recipe,
                "_score": final_score,
                "_relevance": score,
                "_model_boost": model_boost
            })

    return sorted(results, key=lambda x: x["_score"], reverse=True)


# ============ QR CODE RECIPE OPERATIONS ============

def get_recipe_qr_url(recipe_id: str) -> str:
    """Get the URL for a recipe (for QR code)"""
    return f"https://ralphmode.com/r/{recipe_id}"


async def sync_recipe_to_cloud(recipe_id: str, payment_token: str = None) -> bool:
    """
    Sync a local recipe to the cloud ($2 feature).
    Returns True if successful.
    """
    recipe = load_recipe(recipe_id)
    if not recipe:
        return False

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{RECIPE_API_BASE}/recipes/sync",
                json={
                    "recipe_id": recipe_id,
                    "name": recipe.name,
                    "description": recipe.description,
                    "prd": recipe.prd,
                    "tags": recipe.tags,
                    "payment_token": payment_token
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status in [200, 201]:
                    # Update local recipe as synced
                    index = load_recipes_index()
                    if recipe_id in index:
                        index[recipe_id]["cloud_synced"] = True
                        index[recipe_id]["paid"] = bool(payment_token)
                        save_recipes_index(index)
                    return True
    except Exception as e:
        logger.error(f"Cloud sync failed: {e}")

    return False


async def fetch_recipe_from_cloud(recipe_id: str) -> Optional[Recipe]:
    """
    Fetch a recipe from the cloud (by QR code scan).
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{RECIPE_API_BASE}/recipes/{recipe_id}",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Save locally
                    recipe_id = save_recipe(
                        name=data.get("name", "Imported Recipe"),
                        description=data.get("description", ""),
                        prd=data.get("prd", {}),
                        tags=data.get("tags", []),
                        recipe_id=data.get("id")
                    )
                    return load_recipe(recipe_id)
    except Exception as e:
        logger.error(f"Cloud fetch failed: {e}")

    return None

# Recipe Book API endpoint
RECIPE_API_BASE = "https://api.ralphmode.com"  # TODO: Set up actual endpoint
DONATION_URL = "https://buymeacoffee.com/snail3d"


@dataclass
class RecipeRanking:
    """Ranking data for a recipe or task"""
    upvotes: int = 0
    downloads: int = 0
    completions: int = 0  # How many people finished building with this

    @property
    def popularity_score(self) -> float:
        """Weighted popularity score"""
        # Completions worth most (people actually used it)
        # Downloads next (people tried it)
        # Upvotes last (people liked seeing it)
        return (self.completions * 10) + (self.downloads * 3) + (self.upvotes * 1)


# Mock data with popularity rankings
MOCK_RECIPES = [
    {
        "id": "telegram-bot-001",
        "name": "Telegram Bot Starter",
        "description": "A basic Telegram bot with command handlers and async support",
        "tags": ["telegram", "bot", "python", "async"],
        "upvotes": 156,
        "downloads": 423,
        "completions": 89,
        "tasks_count": 12,
        "prds": {
            "01_setup": {
                "tasks": [
                    {"id": "SETUP-001", "title": "Create bot token config", "upvotes": 45},
                    {"id": "SETUP-002", "title": "Set up python-telegram-bot", "upvotes": 38},
                ]
            },
            "02_handlers": {
                "tasks": [
                    {"id": "HAND-001", "title": "Create /start command handler", "upvotes": 67},
                    {"id": "HAND-002", "title": "Add message handler with filters", "upvotes": 52},
                ]
            }
        }
    },
    {
        "id": "discord-bot-001",
        "name": "Discord Bot Template",
        "description": "Discord bot with slash commands and embeds",
        "tags": ["discord", "bot", "python", "slash-commands"],
        "upvotes": 203,
        "downloads": 567,
        "completions": 134,
        "tasks_count": 15
    },
    {
        "id": "fastapi-crud-001",
        "name": "FastAPI CRUD API",
        "description": "REST API with FastAPI, SQLAlchemy, and Pydantic",
        "tags": ["fastapi", "api", "database", "crud", "rest"],
        "upvotes": 312,
        "downloads": 891,
        "completions": 245,
        "tasks_count": 18,
        "prds": {
            "01_setup": {
                "tasks": [
                    {"id": "SETUP-001", "title": "Initialize FastAPI app", "upvotes": 89},
                    {"id": "SETUP-002", "title": "Configure SQLAlchemy", "upvotes": 76},
                ]
            },
            "02_models": {
                "tasks": [
                    {"id": "MODEL-001", "title": "Create base SQLAlchemy model", "upvotes": 94},
                    {"id": "MODEL-002", "title": "Add Pydantic schemas", "upvotes": 81},
                ]
            }
        }
    },
    {
        "id": "cli-tool-001",
        "name": "Python CLI Tool",
        "description": "Command-line tool with Click and rich output",
        "tags": ["cli", "python", "click", "terminal"],
        "upvotes": 98,
        "downloads": 234,
        "completions": 67,
        "tasks_count": 10
    },
    {
        "id": "web-scraper-001",
        "name": "Web Scraper Template",
        "description": "Async web scraper with BeautifulSoup and aiohttp",
        "tags": ["scraper", "web", "python", "async", "beautifulsoup"],
        "upvotes": 178,
        "downloads": 445,
        "completions": 112,
        "tasks_count": 14
    }
]

# Popular task snippets that can be reused across projects
MOCK_TASK_SNIPPETS = [
    {
        "id": "snippet-env-001",
        "title": "Load environment variables with python-dotenv",
        "description": "Set up .env file loading with validation",
        "category": "setup",
        "upvotes": 234,
        "usage_count": 567,
        "code_hint": "from dotenv import load_dotenv"
    },
    {
        "id": "snippet-logging-001",
        "title": "Configure structured logging",
        "description": "Set up logging with proper formatting and levels",
        "category": "setup",
        "upvotes": 198,
        "usage_count": 445
    },
    {
        "id": "snippet-db-001",
        "title": "Async database connection pool",
        "description": "Create connection pool for PostgreSQL/SQLite",
        "category": "database",
        "upvotes": 287,
        "usage_count": 623
    },
    {
        "id": "snippet-auth-001",
        "title": "JWT authentication middleware",
        "description": "Add JWT token validation to API routes",
        "category": "auth",
        "upvotes": 356,
        "usage_count": 789
    },
    {
        "id": "snippet-cache-001",
        "title": "Redis caching layer",
        "description": "Add Redis caching for expensive operations",
        "category": "performance",
        "upvotes": 167,
        "usage_count": 334
    }
]


def calculate_popularity(item: Dict) -> float:
    """Calculate popularity score for ranking"""
    completions = item.get("completions", 0)
    downloads = item.get("downloads", item.get("usage_count", 0))
    upvotes = item.get("upvotes", 0)

    return (completions * 10) + (downloads * 3) + (upvotes * 1)


# ============ WHOLE RECIPE SEARCH ============

async def search_recipes(query: str, limit: int = 5) -> List[Dict]:
    """
    Search for complete recipes matching the query.
    Returns ranked by popularity.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{RECIPE_API_BASE}/recipes/search",
                params={"q": query, "limit": limit},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    results = await resp.json()
                    # Sort by popularity
                    return sorted(results, key=calculate_popularity, reverse=True)
    except Exception as e:
        logger.warning(f"Recipe API unavailable, using mock data: {e}")

    # Fallback to mock data
    return _search_mock_recipes(query, limit)


def _search_mock_recipes(query: str, limit: int) -> List[Dict]:
    """Search mock recipes with scoring"""
    query_lower = query.lower()
    query_words = set(query_lower.split())
    results = []

    for recipe in MOCK_RECIPES:
        relevance_score = 0

        # Tag matching (highest weight)
        for tag in recipe.get("tags", []):
            if tag in query_lower or any(word in tag for word in query_words):
                relevance_score += 20

        # Name matching
        name_lower = recipe["name"].lower()
        if any(word in name_lower for word in query_words):
            relevance_score += 15

        # Description matching
        desc_lower = recipe["description"].lower()
        for word in query_words:
            if word in desc_lower:
                relevance_score += 5

        if relevance_score > 0:
            # Combine relevance with popularity
            popularity = calculate_popularity(recipe)
            final_score = (relevance_score * 100) + popularity

            results.append({
                **recipe,
                "_relevance": relevance_score,
                "_popularity": popularity,
                "_score": final_score
            })

    # Sort by combined score
    return sorted(results, key=lambda x: x["_score"], reverse=True)[:limit]


# ============ GRANULAR TASK SEARCH ============

async def search_tasks(query: str, category: str = None, limit: int = 10) -> List[Dict]:
    """
    Search for individual task snippets.
    Great for finding popular ways to do specific things.
    """
    try:
        async with aiohttp.ClientSession() as session:
            params = {"q": query, "limit": limit}
            if category:
                params["category"] = category

            async with session.get(
                f"{RECIPE_API_BASE}/tasks/search",
                params=params,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    results = await resp.json()
                    return sorted(results, key=lambda x: x.get("usage_count", 0), reverse=True)
    except Exception as e:
        logger.warning(f"Task API unavailable, using mock data: {e}")

    # Fallback to mock snippets
    return _search_mock_tasks(query, category, limit)


def _search_mock_tasks(query: str, category: str, limit: int) -> List[Dict]:
    """Search mock task snippets"""
    query_lower = query.lower()
    results = []

    for snippet in MOCK_TASK_SNIPPETS:
        # Filter by category if specified
        if category and snippet.get("category") != category:
            continue

        score = 0
        if query_lower in snippet["title"].lower():
            score += 20
        if query_lower in snippet["description"].lower():
            score += 10
        if snippet.get("category") and query_lower in snippet["category"]:
            score += 15

        if score > 0:
            results.append({
                **snippet,
                "_score": score + snippet.get("usage_count", 0)
            })

    return sorted(results, key=lambda x: x["_score"], reverse=True)[:limit]


async def get_popular_tasks_for_category(category: str, limit: int = 5) -> List[Dict]:
    """Get the most popular tasks for a category (setup, database, auth, etc.)"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{RECIPE_API_BASE}/tasks/popular",
                params={"category": category, "limit": limit},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
    except:
        pass

    # Fallback
    return [s for s in MOCK_TASK_SNIPPETS if s.get("category") == category][:limit]


# ============ UPVOTING ============

async def upvote_recipe(recipe_id: str) -> bool:
    """Upvote a recipe"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{RECIPE_API_BASE}/recipes/{recipe_id}/upvote",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                return resp.status == 200
    except:
        return False


async def upvote_task(task_id: str) -> bool:
    """Upvote a task snippet"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{RECIPE_API_BASE}/tasks/{task_id}/upvote",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                return resp.status == 200
    except:
        return False


async def downvote_recipe(recipe_id: str) -> bool:
    """Downvote a recipe (user hated it - garbage sinks!)"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{RECIPE_API_BASE}/recipes/{recipe_id}/downvote",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                return resp.status == 200
    except:
        return False


async def downvote_task(task_id: str) -> bool:
    """Downvote a task snippet (user hated it)"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{RECIPE_API_BASE}/tasks/{task_id}/downvote",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                return resp.status == 200
    except:
        return False


async def record_recipe_used(recipe_id: str, completed: bool = False) -> bool:
    """Record that a recipe was downloaded/used (for popularity tracking)"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{RECIPE_API_BASE}/recipes/{recipe_id}/used",
                json={"completed": completed},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                return resp.status == 200
    except:
        return False


# ============ RECIPE DETAILS ============

async def get_recipe_details(recipe_id: str) -> Optional[Dict]:
    """Get full PRD details for a recipe"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{RECIPE_API_BASE}/recipes/{recipe_id}",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception as e:
        logger.warning(f"Could not fetch recipe details: {e}")

    # Check mock data
    for recipe in MOCK_RECIPES:
        if recipe["id"] == recipe_id:
            return recipe

    return None


# ============ RECIPE SUBMISSION ============

async def submit_recipe(prd: Dict, anonymous: bool = True) -> bool:
    """Submit a completed recipe to the Recipe Book"""
    sanitized = sanitize_prd(prd)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{RECIPE_API_BASE}/recipes/submit",
                json={
                    "prd": sanitized,
                    "anonymous": anonymous
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status in [200, 201]:
                    logger.info("Recipe submitted successfully!")
                    return True
    except Exception as e:
        logger.warning(f"Could not submit recipe: {e}")

    return False


# ============ SANITIZATION ============

def sanitize_prd(prd: Dict) -> Dict:
    """Remove sensitive information from PRD before sharing"""
    sanitized = json.loads(json.dumps(prd))

    sensitive_patterns = [
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # Email
        r'sk-[a-zA-Z0-9]{20,}',  # API keys
        r'ghp_[a-zA-Z0-9]{36}',  # GitHub tokens
        r'xox[baprs]-[a-zA-Z0-9-]+',  # Slack tokens
        r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',  # IP addresses
        r'password\s*[=:]\s*["\']?[^"\'\s]+',
        r'secret\s*[=:]\s*["\']?[^"\'\s]+',
        r'token\s*[=:]\s*["\']?[^"\'\s]+',
        r'/users/[a-zA-Z0-9_-]+/',
    ]

    def clean_string(s: str) -> str:
        if not isinstance(s, str):
            return s
        for pattern in sensitive_patterns:
            s = re.sub(pattern, '[REDACTED]', s, flags=re.IGNORECASE)
        return s

    def clean_dict(d):
        if isinstance(d, dict):
            return {k: clean_dict(v) for k, v in d.items()}
        elif isinstance(d, list):
            return [clean_dict(item) for item in d]
        elif isinstance(d, str):
            return clean_string(d)
        return d

    return clean_dict(sanitized)


# ============ DISPLAY HELPERS ============

def format_recipes_for_display(recipes: List[Dict]) -> str:
    """Format recipe list for terminal display"""
    if not recipes:
        return "No matching recipes found in the Recipe Book."

    lines = ["Found some similar recipes:\n"]
    for i, recipe in enumerate(recipes, 1):
        popularity = calculate_popularity(recipe)
        upvotes = recipe.get("upvotes", 0)

        lines.append(f"  {i}. {recipe['name']} ({upvotes} upvotes)")
        lines.append(f"     {recipe['description']}")
        lines.append(f"     Tags: {', '.join(recipe.get('tags', []))}")
        lines.append("")

    return "\n".join(lines)


def format_tasks_for_display(tasks: List[Dict]) -> str:
    """Format task snippets for display"""
    if not tasks:
        return "No matching tasks found."

    lines = ["Popular task snippets:\n"]
    for i, task in enumerate(tasks, 1):
        usage = task.get("usage_count", 0)
        upvotes = task.get("upvotes", 0)

        lines.append(f"  {i}. {task['title']} ({usage} uses, {upvotes} upvotes)")
        lines.append(f"     {task['description']}")
        lines.append("")

    return "\n".join(lines)


def get_donation_message() -> str:
    """Get the donation prompt message"""
    return f"""
Hey boss... *shuffles feet nervously*

My creator Snail has been working real hard on me...
I'm free to use, but if I helped you today, maybe buy him a coffee?

    {DONATION_URL}

No pressure! I still love you either way.
*I been working real hard mister...*
"""
