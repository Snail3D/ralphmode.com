#!/usr/bin/env python3
"""
OB-027: Project Template Selector
Manages project templates for Ralph Mode onboarding.
"""

import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class ProjectTemplate:
    """Represents a project template"""
    id: str
    name: str
    description: str
    category: str
    files: Dict[str, str]  # filename -> content
    prd_tasks: List[Dict[str, Any]]
    customization_options: List[Dict[str, Any]]
    tags: List[str]


class TemplateManager:
    """Manages project templates for quick-start scaffolding"""

    def __init__(self):
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, ProjectTemplate]:
        """Load all available templates"""
        return {
            "ralph-starter": self._get_ralph_starter_template(),
            "telegram-bot": self._get_telegram_bot_template(),
            "web-app": self._get_web_app_template(),
            "rest-api": self._get_rest_api_template(),
            "cli-tool": self._get_cli_tool_template(),
            "fullstack": self._get_fullstack_template(),
        }

    def get_all_templates(self) -> List[Dict[str, Any]]:
        """Get list of all templates with metadata"""
        return [
            {
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "category": template.category,
                "tags": template.tags,
            }
            for template in self.templates.values()
        ]

    def get_template(self, template_id: str) -> Optional[ProjectTemplate]:
        """Get specific template by ID"""
        return self.templates.get(template_id)

    def get_templates_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get templates filtered by category"""
        return [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "tags": t.tags,
            }
            for t in self.templates.values()
            if t.category == category
        ]

    def scaffold_project(self, template_id: str, project_path: str, customizations: Optional[Dict[str, Any]] = None) -> bool:
        """
        Create project structure from template

        Args:
            template_id: ID of template to use
            project_path: Where to create the project
            customizations: Optional customization options

        Returns:
            True if successful, False otherwise
        """
        template = self.get_template(template_id)
        if not template:
            return False

        try:
            # Create project directory
            os.makedirs(project_path, exist_ok=True)

            # Create files from template
            for filename, content in template.files.items():
                # Apply customizations to content if provided
                if customizations:
                    content = self._apply_customizations(content, customizations)

                file_path = os.path.join(project_path, filename)

                # Create subdirectories if needed
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                # Write file
                with open(file_path, 'w') as f:
                    f.write(content)

            # Generate PRD from template tasks
            prd_path = os.path.join(project_path, "scripts/ralph/prd.json")
            self._generate_prd(template, prd_path, customizations)

            return True
        except Exception as e:
            print(f"Error scaffolding project: {e}")
            return False

    def _apply_customizations(self, content: str, customizations: Dict[str, Any]) -> str:
        """Apply customization options to template content"""
        for key, value in customizations.items():
            placeholder = f"{{{{{key}}}}}"
            content = content.replace(placeholder, str(value))
        return content

    def _generate_prd(self, template: ProjectTemplate, prd_path: str, customizations: Optional[Dict[str, Any]]):
        """Generate PRD file from template tasks"""
        os.makedirs(os.path.dirname(prd_path), exist_ok=True)

        prd_data = {
            "project_name": customizations.get("project_name", "New Project") if customizations else "New Project",
            "tasks": template.prd_tasks,
            "priority_order": [f"{task['id']} - {task['title']}" for task in template.prd_tasks]
        }

        with open(prd_path, 'w') as f:
            json.dump(prd_data, f, indent=2)

    # Template definitions

    def _get_ralph_starter_template(self) -> ProjectTemplate:
        """Ralph Mode autonomous coding pattern template"""
        return ProjectTemplate(
            id="ralph-starter",
            name="Ralph Pattern Starter",
            description="The original Ralph autonomous coding loop. Perfect for letting AI build features while you sleep.",
            category="AI-Powered",
            tags=["ralph", "autonomous", "claude-code", "automation"],
            files={
                "scripts/ralph/ralph.sh": self._get_ralph_sh_content(),
                "scripts/ralph/prompt.md": self._get_prompt_md_content(),
                "scripts/ralph/progress.txt": "# Ralph Progress Log\n\n",
                "AGENTS.md": "# Agent Memory\n\nLong-term learnings and patterns go here.\n",
                "README.md": self._get_ralph_readme_content(),
                ".gitignore": self._get_gitignore_content(),
            },
            prd_tasks=[
                {
                    "id": "SETUP-001",
                    "category": "Setup",
                    "title": "Initialize Project Structure",
                    "description": "Set up basic project structure and dependencies",
                    "acceptance_criteria": [
                        "Project structure created",
                        "Dependencies installed",
                        "Git initialized",
                    ],
                    "passes": False
                }
            ],
            customization_options=[
                {
                    "id": "project_name",
                    "label": "Project Name",
                    "type": "text",
                    "default": "my-ralph-project"
                },
            ]
        )

    def _get_telegram_bot_template(self) -> ProjectTemplate:
        """Telegram bot template"""
        return ProjectTemplate(
            id="telegram-bot",
            name="Telegram Bot",
            description="Full-featured Telegram bot with character personalities and AI integration.",
            category="Bot",
            tags=["telegram", "bot", "ai", "python"],
            files={
                "bot.py": self._get_telegram_bot_content(),
                "config.py": self._get_config_content(),
                "requirements.txt": self._get_telegram_requirements_content(),
                ".env.example": "TELEGRAM_BOT_TOKEN=your_token_here\nGROQ_API_KEY=your_key_here\n",
                ".gitignore": self._get_gitignore_content(),
                "README.md": "# Telegram Bot\n\nYour awesome Telegram bot.\n",
            },
            prd_tasks=[
                {
                    "id": "BOT-001",
                    "category": "Core",
                    "title": "Basic Bot Commands",
                    "description": "Implement /start, /help commands",
                    "acceptance_criteria": [
                        "/start command works",
                        "/help shows available commands",
                    ],
                    "passes": False
                }
            ],
            customization_options=[
                {
                    "id": "bot_name",
                    "label": "Bot Name",
                    "type": "text",
                    "default": "MyBot"
                },
            ]
        )

    def _get_web_app_template(self) -> ProjectTemplate:
        """Modern web app template"""
        return ProjectTemplate(
            id="web-app",
            name="Web App (React + FastAPI)",
            description="Modern full-stack web app with React frontend and FastAPI backend.",
            category="Web",
            tags=["react", "fastapi", "web", "fullstack"],
            files={
                "frontend/package.json": self._get_package_json_content(),
                "frontend/src/App.tsx": self._get_react_app_content(),
                "backend/main.py": self._get_fastapi_main_content(),
                "backend/requirements.txt": "fastapi\nuvicorn\npydantic\n",
                "README.md": "# Web App\n\nModern web application.\n",
                ".gitignore": self._get_gitignore_content(),
            },
            prd_tasks=[
                {
                    "id": "WEB-001",
                    "category": "Setup",
                    "title": "Setup Frontend and Backend",
                    "description": "Initialize React and FastAPI",
                    "acceptance_criteria": [
                        "Frontend runs on localhost:3000",
                        "Backend runs on localhost:8000",
                    ],
                    "passes": False
                }
            ],
            customization_options=[
                {
                    "id": "app_name",
                    "label": "App Name",
                    "type": "text",
                    "default": "MyWebApp"
                },
            ]
        )

    def _get_rest_api_template(self) -> ProjectTemplate:
        """REST API template"""
        return ProjectTemplate(
            id="rest-api",
            name="REST API (FastAPI)",
            description="Production-ready REST API with authentication, database, and documentation.",
            category="Backend",
            tags=["api", "fastapi", "rest", "backend"],
            files={
                "main.py": self._get_api_main_content(),
                "models.py": "from pydantic import BaseModel\n\n# Your models here\n",
                "database.py": "# Database connection\n",
                "requirements.txt": "fastapi\nuvicorn\nsqlalchemy\npydantic\n",
                "README.md": "# REST API\n\nFastAPI REST API.\n",
                ".gitignore": self._get_gitignore_content(),
            },
            prd_tasks=[
                {
                    "id": "API-001",
                    "category": "Core",
                    "title": "Basic CRUD Endpoints",
                    "description": "Implement Create, Read, Update, Delete",
                    "acceptance_criteria": [
                        "GET /items works",
                        "POST /items works",
                        "PUT /items/{id} works",
                        "DELETE /items/{id} works",
                    ],
                    "passes": False
                }
            ],
            customization_options=[
                {
                    "id": "api_name",
                    "label": "API Name",
                    "type": "text",
                    "default": "MyAPI"
                },
            ]
        )

    def _get_cli_tool_template(self) -> ProjectTemplate:
        """CLI tool template"""
        return ProjectTemplate(
            id="cli-tool",
            name="CLI Tool (Python)",
            description="Command-line tool with argument parsing and rich output.",
            category="Tool",
            tags=["cli", "tool", "python", "automation"],
            files={
                "cli.py": self._get_cli_content(),
                "requirements.txt": "click\nrich\n",
                "README.md": "# CLI Tool\n\nYour command-line tool.\n",
                ".gitignore": self._get_gitignore_content(),
            },
            prd_tasks=[
                {
                    "id": "CLI-001",
                    "category": "Core",
                    "title": "Basic Commands",
                    "description": "Implement main CLI commands",
                    "acceptance_criteria": [
                        "Help command shows usage",
                        "Version command works",
                    ],
                    "passes": False
                }
            ],
            customization_options=[
                {
                    "id": "tool_name",
                    "label": "Tool Name",
                    "type": "text",
                    "default": "mytool"
                },
            ]
        )

    def _get_fullstack_template(self) -> ProjectTemplate:
        """Full-stack application template"""
        return ProjectTemplate(
            id="fullstack",
            name="Full-Stack App",
            description="Complete full-stack application with authentication, database, and deployment config.",
            category="Fullstack",
            tags=["fullstack", "react", "fastapi", "postgres", "docker"],
            files={
                "docker-compose.yml": self._get_docker_compose_content(),
                "frontend/package.json": self._get_package_json_content(),
                "backend/main.py": self._get_fastapi_main_content(),
                "README.md": "# Full-Stack App\n\nComplete full-stack application.\n",
                ".gitignore": self._get_gitignore_content(),
            },
            prd_tasks=[
                {
                    "id": "FS-001",
                    "category": "Setup",
                    "title": "Docker Setup",
                    "description": "Configure Docker containers",
                    "acceptance_criteria": [
                        "docker-compose up works",
                        "All services start correctly",
                    ],
                    "passes": False
                }
            ],
            customization_options=[
                {
                    "id": "project_name",
                    "label": "Project Name",
                    "type": "text",
                    "default": "my-fullstack-app"
                },
            ]
        )

    # File content generators

    def _get_ralph_sh_content(self) -> str:
        return """#!/bin/bash
# Ralph autonomous coding loop

while true; do
    echo "Ralph starting iteration..."
    claude --dangerously-skip-permissions --prompt scripts/ralph/prompt.md
    sleep 10
done
"""

    def _get_prompt_md_content(self) -> str:
        return """# Ralph Agent Instructions

You are Ralph, an autonomous coding agent. Your job is to:

1. Read the PRD at scripts/ralph/prd.json
2. Find the first incomplete task
3. Implement it following acceptance criteria
4. Test your work
5. Commit with format: feat(ralph): [task title]
6. Update prd.json to mark task complete
7. Append learnings to progress.txt

Work autonomously. Ship quality code.
"""

    def _get_ralph_readme_content(self) -> str:
        return """# Ralph Pattern Project

Ship features while you sleep using the Ralph autonomous coding pattern.

## How It Works

1. Define tasks in `scripts/ralph/prd.json`
2. Run `./scripts/ralph/ralph.sh`
3. Ralph picks tasks and implements them
4. Wake up to shipped features

## Setup

1. Install Claude Code: `npm install -g @anthropic-ai/claude-code`
2. Set ANTHROPIC_API_KEY in your environment
3. Run `./scripts/ralph/ralph.sh`

That's it. Ralph handles the rest.
"""

    def _get_gitignore_content(self) -> str:
        return """.env
__pycache__/
*.pyc
.DS_Store
node_modules/
dist/
build/
*.log
.venv/
venv/
"""

    def _get_telegram_bot_content(self) -> str:
        return """#!/usr/bin/env python3
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hello! I am {{bot_name}}.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Available commands: /start, /help')

if __name__ == '__main__':
    app = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.run_polling()
"""

    def _get_config_content(self) -> str:
        return """import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
"""

    def _get_telegram_requirements_content(self) -> str:
        return """python-telegram-bot==22.0.0
python-dotenv
groq
"""

    def _get_package_json_content(self) -> str:
        return """{
  "name": "{{app_name}}",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "vite build"
  },
  "dependencies": {
    "react": "^18.0.0",
    "react-dom": "^18.0.0"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "@vitejs/plugin-react": "^4.0.0"
  }
}
"""

    def _get_react_app_content(self) -> str:
        return """import React from 'react';

function App() {
  return (
    <div>
      <h1>{{app_name}}</h1>
      <p>Welcome to your new web app!</p>
    </div>
  );
}

export default App;
"""

    def _get_fastapi_main_content(self) -> str:
        return """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="{{api_name}}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hello from {{api_name}}"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
"""

    def _get_api_main_content(self) -> str:
        return """from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="{{api_name}}")

class Item(BaseModel):
    name: str
    description: str = None

items = []

@app.get("/items")
async def get_items():
    return items

@app.post("/items")
async def create_item(item: Item):
    items.append(item)
    return item

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    if item_id >= len(items):
        raise HTTPException(status_code=404, detail="Item not found")
    return items[item_id]
"""

    def _get_cli_content(self) -> str:
        return """#!/usr/bin/env python3
import click
from rich.console import Console

console = Console()

@click.group()
@click.version_option()
def cli():
    '''{{tool_name}} - Your CLI tool'''
    pass

@cli.command()
def hello():
    '''Say hello'''
    console.print("[green]Hello from {{tool_name}}![/green]")

if __name__ == '__main__':
    cli()
"""

    def _get_docker_compose_content(self) -> str:
        return """version: '3.8'

services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
    environment:
      - NODE_ENV=development

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/{{project_name}}

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB={{project_name}}
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
"""


# Export singleton instance
template_manager = TemplateManager()
