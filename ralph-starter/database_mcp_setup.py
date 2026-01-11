#!/usr/bin/env python3
"""
Database MCP Server Setup

Guides users through connecting database MCP servers (PostgreSQL, MySQL, MongoDB, SQLite).
Handles connection string setup, credential management, and testing.
"""

import subprocess
import logging
import os
import json
from typing import Dict, Any, Optional, Tuple, List


class DatabaseMCPSetup:
    """Handles database MCP server setup and configuration."""

    def __init__(self):
        """Initialize the database MCP setup handler."""
        self.logger = logging.getLogger(__name__)

        # Database types and their MCP server packages
        self.db_types = {
            "postgresql": {
                "name": "PostgreSQL",
                "package": "@modelcontextprotocol/server-postgres",
                "default_port": 5432,
                "requires_auth": True
            },
            "mysql": {
                "name": "MySQL",
                "package": "@modelcontextprotocol/server-mysql",
                "default_port": 3306,
                "requires_auth": True
            },
            "mongodb": {
                "name": "MongoDB",
                "package": "@modelcontextprotocol/server-mongodb",
                "default_port": 27017,
                "requires_auth": True
            },
            "sqlite": {
                "name": "SQLite",
                "package": "@modelcontextprotocol/server-sqlite",
                "default_port": None,
                "requires_auth": False
            }
        }

    def get_database_types(self) -> List[Dict[str, Any]]:
        """Get list of supported database types with details.

        Returns:
            List of database type dictionaries
        """
        return [
            {
                "id": db_id,
                "name": db_info["name"],
                "description": self._get_db_description(db_id),
                "difficulty": self._get_difficulty(db_id),
                "use_cases": self._get_use_cases(db_id)
            }
            for db_id, db_info in self.db_types.items()
        ]

    def _get_db_description(self, db_type: str) -> str:
        """Get description for database type."""
        descriptions = {
            "postgresql": "Powerful open-source relational database. Best for complex queries and ACID compliance.",
            "mysql": "Popular relational database. Great for web applications and read-heavy workloads.",
            "mongodb": "NoSQL document database. Perfect for flexible schemas and JSON-like data.",
            "sqlite": "Lightweight file-based database. Ideal for local dev, testing, and small apps."
        }
        return descriptions.get(db_type, "Database server")

    def _get_difficulty(self, db_type: str) -> str:
        """Get setup difficulty level."""
        if db_type == "sqlite":
            return "Easy"
        elif db_type in ["mysql", "postgresql"]:
            return "Medium"
        else:
            return "Advanced"

    def _get_use_cases(self, db_type: str) -> List[str]:
        """Get common use cases for database type."""
        use_cases = {
            "postgresql": ["Web applications", "Analytics", "GIS data", "JSON storage"],
            "mysql": ["WordPress sites", "E-commerce", "Content management", "Web apps"],
            "mongodb": ["Real-time analytics", "Content management", "IoT data", "Mobile apps"],
            "sqlite": ["Local development", "Testing", "Mobile apps", "Desktop apps"]
        }
        return use_cases.get(db_type, [])

    def get_connection_string_format(self, db_type: str) -> Dict[str, Any]:
        """Get connection string format and examples for database type.

        Args:
            db_type: Database type (postgresql, mysql, mongodb, sqlite)

        Returns:
            Dictionary with format info and examples
        """
        db_info = self.db_types.get(db_type)
        if not db_info:
            return {"error": f"Unsupported database type: {db_type}"}

        formats = {
            "postgresql": {
                "format": "postgresql://[user[:password]@][host][:port][/database]",
                "examples": [
                    {
                        "scenario": "Local development",
                        "string": "postgresql://postgres:password@localhost:5432/mydb",
                        "explanation": "Connect to local PostgreSQL with username 'postgres'"
                    },
                    {
                        "scenario": "Remote server",
                        "string": "postgresql://user:pass@db.example.com:5432/production",
                        "explanation": "Connect to remote PostgreSQL server"
                    },
                    {
                        "scenario": "No password (trusted)",
                        "string": "postgresql://localhost/mydb",
                        "explanation": "Local connection using peer authentication"
                    }
                ],
                "parameters": {
                    "user": "Database username (default: postgres)",
                    "password": "Database password (optional if using peer auth)",
                    "host": "Database host (default: localhost)",
                    "port": f"Port number (default: {db_info['default_port']})",
                    "database": "Database name"
                }
            },
            "mysql": {
                "format": "mysql://[user[:password]@][host][:port][/database]",
                "examples": [
                    {
                        "scenario": "Local development",
                        "string": "mysql://root:password@localhost:3306/mydb",
                        "explanation": "Connect to local MySQL with root user"
                    },
                    {
                        "scenario": "Remote server",
                        "string": "mysql://user:pass@mysql.example.com:3306/production",
                        "explanation": "Connect to remote MySQL server"
                    }
                ],
                "parameters": {
                    "user": "Database username (default: root)",
                    "password": "Database password",
                    "host": "Database host (default: localhost)",
                    "port": f"Port number (default: {db_info['default_port']})",
                    "database": "Database name"
                }
            },
            "mongodb": {
                "format": "mongodb://[user:password@]host[:port][/database][?options]",
                "examples": [
                    {
                        "scenario": "Local MongoDB",
                        "string": "mongodb://localhost:27017/mydb",
                        "explanation": "Connect to local MongoDB without auth"
                    },
                    {
                        "scenario": "Authenticated connection",
                        "string": "mongodb://user:password@localhost:27017/mydb?authSource=admin",
                        "explanation": "Connect with authentication"
                    },
                    {
                        "scenario": "MongoDB Atlas (cloud)",
                        "string": "mongodb+srv://user:password@cluster.mongodb.net/mydb",
                        "explanation": "Connect to MongoDB Atlas cloud database"
                    }
                ],
                "parameters": {
                    "user": "Database username (optional)",
                    "password": "Database password (optional)",
                    "host": "Database host (default: localhost)",
                    "port": f"Port number (default: {db_info['default_port']})",
                    "database": "Database name",
                    "options": "Additional options (e.g., authSource=admin)"
                }
            },
            "sqlite": {
                "format": "sqlite:///[path/to/database.db]",
                "examples": [
                    {
                        "scenario": "Relative path",
                        "string": "sqlite:///data/myapp.db",
                        "explanation": "Database file in ./data/ directory"
                    },
                    {
                        "scenario": "Absolute path",
                        "string": "sqlite:////absolute/path/to/database.db",
                        "explanation": "Database at absolute path (note: 4 slashes for absolute)"
                    },
                    {
                        "scenario": "In-memory database",
                        "string": "sqlite://:memory:",
                        "explanation": "Temporary in-memory database (lost on close)"
                    }
                ],
                "parameters": {
                    "path": "Path to SQLite database file (created if doesn't exist)"
                }
            }
        }

        return {
            "db_type": db_type,
            "db_name": db_info["name"],
            **formats.get(db_type, {})
        }

    def build_connection_string(self, db_type: str, config: Dict[str, str]) -> Tuple[bool, str]:
        """Build connection string from configuration.

        Args:
            db_type: Database type
            config: Configuration dictionary with host, user, password, etc.

        Returns:
            Tuple of (success, connection_string_or_error)
        """
        try:
            if db_type == "sqlite":
                path = config.get("path", "database.db")
                return True, f"sqlite:///{path}"

            elif db_type in ["postgresql", "mysql"]:
                user = config.get("user", "")
                password = config.get("password", "")
                host = config.get("host", "localhost")
                port = config.get("port", str(self.db_types[db_type]["default_port"]))
                database = config.get("database", "")

                # Build connection string
                auth_part = ""
                if user:
                    auth_part = user
                    if password:
                        auth_part += f":{password}"
                    auth_part += "@"

                conn_str = f"{db_type}://{auth_part}{host}:{port}"
                if database:
                    conn_str += f"/{database}"

                return True, conn_str

            elif db_type == "mongodb":
                user = config.get("user", "")
                password = config.get("password", "")
                host = config.get("host", "localhost")
                port = config.get("port", str(self.db_types[db_type]["default_port"]))
                database = config.get("database", "")
                auth_source = config.get("auth_source", "admin")
                is_srv = config.get("is_srv", False)

                # Build connection string
                protocol = "mongodb+srv" if is_srv else "mongodb"
                auth_part = ""
                if user and password:
                    auth_part = f"{user}:{password}@"

                port_part = "" if is_srv else f":{port}"
                conn_str = f"{protocol}://{auth_part}{host}{port_part}"

                if database:
                    conn_str += f"/{database}"

                if user and not is_srv:
                    conn_str += f"?authSource={auth_source}"

                return True, conn_str

            else:
                return False, f"Unsupported database type: {db_type}"

        except Exception as e:
            self.logger.error(f"Error building connection string: {e}")
            return False, f"Error: {str(e)}"

    def test_connection(self, db_type: str, connection_string: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Test database connection.

        Args:
            db_type: Database type
            connection_string: Connection string to test

        Returns:
            Tuple of (success, message, metadata)
        """
        try:
            if db_type == "sqlite":
                return self._test_sqlite_connection(connection_string)
            elif db_type == "postgresql":
                return self._test_postgresql_connection(connection_string)
            elif db_type == "mysql":
                return self._test_mysql_connection(connection_string)
            elif db_type == "mongodb":
                return self._test_mongodb_connection(connection_string)
            else:
                return False, f"Testing not implemented for {db_type}", None

        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False, f"Test failed: {str(e)}", None

    def _test_sqlite_connection(self, connection_string: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Test SQLite connection."""
        try:
            import sqlite3

            # Extract path from connection string
            path = connection_string.replace("sqlite:///", "")

            # Check if it's in-memory
            if path == ":memory:":
                conn = sqlite3.connect(":memory:")
                cursor = conn.cursor()
                cursor.execute("SELECT sqlite_version()")
                version = cursor.fetchone()[0]
                conn.close()

                return True, "Connected to in-memory SQLite database", {
                    "version": version,
                    "type": "in-memory"
                }

            # Check if file exists or can be created
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                return False, f"Directory does not exist: {directory}", None

            # Try to connect
            conn = sqlite3.connect(path)
            cursor = conn.cursor()
            cursor.execute("SELECT sqlite_version()")
            version = cursor.fetchone()[0]

            # Get database info
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            conn.close()

            return True, f"Connected successfully to {path}", {
                "version": version,
                "path": path,
                "file_exists": os.path.exists(path),
                "tables": tables,
                "table_count": len(tables)
            }

        except ImportError:
            return False, "sqlite3 module not available", None
        except Exception as e:
            return False, f"SQLite connection failed: {str(e)}", None

    def _test_postgresql_connection(self, connection_string: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Test PostgreSQL connection."""
        try:
            import psycopg2

            conn = psycopg2.connect(connection_string)
            cursor = conn.cursor()

            # Get version
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0].split(',')[0]

            # Get database name
            cursor.execute("SELECT current_database()")
            database = cursor.fetchone()[0]

            # Get table count
            cursor.execute("""
                SELECT count(*)
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """)
            table_count = cursor.fetchone()[0]

            conn.close()

            return True, "Connected successfully to PostgreSQL", {
                "version": version,
                "database": database,
                "table_count": table_count
            }

        except ImportError:
            return False, "psycopg2 module not installed. Install with: pip install psycopg2-binary", None
        except Exception as e:
            return False, f"PostgreSQL connection failed: {str(e)}", None

    def _test_mysql_connection(self, connection_string: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Test MySQL connection."""
        try:
            import mysql.connector
            from urllib.parse import urlparse

            # Parse connection string
            parsed = urlparse(connection_string)

            conn = mysql.connector.connect(
                host=parsed.hostname,
                port=parsed.port or 3306,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path.lstrip('/') if parsed.path else None
            )

            cursor = conn.cursor()

            # Get version
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]

            # Get database name
            cursor.execute("SELECT DATABASE()")
            database = cursor.fetchone()[0]

            # Get table count
            if database:
                cursor.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema = %s", (database,))
                table_count = cursor.fetchone()[0]
            else:
                table_count = 0

            conn.close()

            return True, "Connected successfully to MySQL", {
                "version": version,
                "database": database,
                "table_count": table_count
            }

        except ImportError:
            return False, "mysql-connector-python not installed. Install with: pip install mysql-connector-python", None
        except Exception as e:
            return False, f"MySQL connection failed: {str(e)}", None

    def _test_mongodb_connection(self, connection_string: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Test MongoDB connection."""
        try:
            from pymongo import MongoClient
            from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

            # Create client with short timeout
            client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)

            # Force connection
            client.admin.command('ping')

            # Get server info
            server_info = client.server_info()
            version = server_info.get('version', 'unknown')

            # Get database name from connection string
            from urllib.parse import urlparse
            parsed = urlparse(connection_string)
            db_name = parsed.path.lstrip('/').split('?')[0] if parsed.path else 'test'

            # Get collection count
            if db_name:
                db = client[db_name]
                collection_count = len(db.list_collection_names())
            else:
                collection_count = 0

            client.close()

            return True, "Connected successfully to MongoDB", {
                "version": version,
                "database": db_name,
                "collection_count": collection_count
            }

        except ImportError:
            return False, "pymongo not installed. Install with: pip install pymongo", None
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            return False, f"MongoDB connection failed: Cannot reach server", None
        except Exception as e:
            return False, f"MongoDB connection failed: {str(e)}", None

    def get_example_queries(self, db_type: str) -> List[Dict[str, str]]:
        """Get example queries for database type.

        Args:
            db_type: Database type

        Returns:
            List of example queries with descriptions
        """
        examples = {
            "postgresql": [
                {
                    "name": "List all tables",
                    "query": "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';",
                    "description": "Show all tables in the public schema"
                },
                {
                    "name": "Create a table",
                    "query": "CREATE TABLE users (id SERIAL PRIMARY KEY, name VARCHAR(100), email VARCHAR(100) UNIQUE);",
                    "description": "Create a simple users table"
                },
                {
                    "name": "Insert data",
                    "query": "INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com');",
                    "description": "Add a new user"
                },
                {
                    "name": "Query data",
                    "query": "SELECT * FROM users WHERE name LIKE 'A%';",
                    "description": "Find all users whose names start with 'A'"
                }
            ],
            "mysql": [
                {
                    "name": "Show databases",
                    "query": "SHOW DATABASES;",
                    "description": "List all databases"
                },
                {
                    "name": "Show tables",
                    "query": "SHOW TABLES;",
                    "description": "List all tables in current database"
                },
                {
                    "name": "Create a table",
                    "query": "CREATE TABLE products (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100), price DECIMAL(10,2));",
                    "description": "Create a products table"
                },
                {
                    "name": "Query data",
                    "query": "SELECT * FROM products WHERE price > 10.00;",
                    "description": "Find products over $10"
                }
            ],
            "mongodb": [
                {
                    "name": "List collections",
                    "query": "db.getCollectionNames()",
                    "description": "Show all collections in database"
                },
                {
                    "name": "Insert document",
                    "query": 'db.users.insertOne({name: "Alice", email: "alice@example.com", age: 30})',
                    "description": "Add a new user document"
                },
                {
                    "name": "Find documents",
                    "query": 'db.users.find({age: {$gte: 18}})',
                    "description": "Find all users age 18 or older"
                },
                {
                    "name": "Update document",
                    "query": 'db.users.updateOne({name: "Alice"}, {$set: {age: 31}})',
                    "description": "Update Alice's age"
                }
            ],
            "sqlite": [
                {
                    "name": "List tables",
                    "query": "SELECT name FROM sqlite_master WHERE type='table';",
                    "description": "Show all tables in database"
                },
                {
                    "name": "Create a table",
                    "query": "CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT, completed INTEGER DEFAULT 0);",
                    "description": "Create a tasks table"
                },
                {
                    "name": "Insert data",
                    "query": "INSERT INTO tasks (title) VALUES ('Learn SQLite');",
                    "description": "Add a new task"
                },
                {
                    "name": "Query data",
                    "query": "SELECT * FROM tasks WHERE completed = 0;",
                    "description": "Find incomplete tasks"
                }
            ]
        }

        return examples.get(db_type, [])

    def get_mcp_config_template(self, db_type: str, connection_string: str) -> Dict[str, Any]:
        """Generate MCP configuration template for Claude Code.

        Args:
            db_type: Database type
            connection_string: Database connection string

        Returns:
            MCP configuration dictionary
        """
        db_info = self.db_types.get(db_type)
        if not db_info:
            return {}

        # Base configuration
        config = {
            "mcpServers": {
                f"{db_type}-database": {
                    "command": "npx",
                    "args": ["-y", db_info["package"]],
                    "env": {
                        f"{db_type.upper()}_CONNECTION_STRING": connection_string
                    }
                }
            }
        }

        return config

    def save_connection_to_env(self, db_type: str, connection_string: str, env_var_name: Optional[str] = None) -> Tuple[bool, str]:
        """Save connection string to .env file.

        Args:
            db_type: Database type
            connection_string: Connection string to save
            env_var_name: Optional custom environment variable name

        Returns:
            Tuple of (success, message)
        """
        try:
            env_path = ".env"
            var_name = env_var_name or f"{db_type.upper()}_CONNECTION_STRING"

            # Read existing .env file
            existing_lines = []
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    existing_lines = f.readlines()

            # Remove existing entry for this variable
            filtered_lines = [line for line in existing_lines if not line.startswith(f"{var_name}=")]

            # Add new entry
            filtered_lines.append(f"{var_name}={connection_string}\n")

            # Write back to file
            with open(env_path, 'w') as f:
                f.writelines(filtered_lines)

            return True, f"Saved to .env as {var_name}"

        except Exception as e:
            self.logger.error(f"Error saving to .env: {e}")
            return False, f"Error: {str(e)}"


# Singleton instance
_database_mcp_setup = None


def get_database_mcp_setup() -> DatabaseMCPSetup:
    """Get the singleton DatabaseMCPSetup instance.

    Returns:
        DatabaseMCPSetup instance
    """
    global _database_mcp_setup
    if _database_mcp_setup is None:
        _database_mcp_setup = DatabaseMCPSetup()
    return _database_mcp_setup
