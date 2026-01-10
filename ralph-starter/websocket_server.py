#!/usr/bin/env python3
"""
WB-002: WebSocket Server for Live Build Stream

This server provides:
- Real-time terminal output streaming
- Build status updates
- Progress tracking
- Output sanitization (no secrets)

Usage:
    from websocket_server import BuildStreamServer

    server = BuildStreamServer()
    server.emit_build_output(feedback_id, output_line)
    server.emit_build_status(feedback_id, status)
"""

import os
import re
import logging
from typing import Optional, Set, Dict

# Try to import Flask and SocketIO dependencies
try:
    from flask import Flask, request
    from flask_socketio import SocketIO, emit, join_room, leave_room
    from flask_cors import CORS
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False
    Flask = None
    SocketIO = None
    CORS = None

logger = logging.getLogger(__name__)

# Patterns to sanitize from output (prevent secret leakage)
SECRET_PATTERNS = [
    # API keys and tokens with Bearer prefix
    r'Bearer\s+[A-Za-z0-9_\-]{10,}',
    # API keys and tokens
    r'(api[_-]?key|token)["\s:=]+[A-Za-z0-9_\-]{16,}',
    # Passwords
    r'(password|passwd|pwd)["\s:=]+[^\s"]+',
    # Environment variables with secrets
    r'(GROQ|TELEGRAM|API|SECRET|KEY)[_A-Z]*=[^\s]+',
    # SSH keys
    r'-----BEGIN [A-Z\s]+ PRIVATE KEY-----[\s\S]*?-----END [A-Z\s]+ PRIVATE KEY-----',
    # Database URLs with credentials
    r'(postgres|mysql|mongodb)://[^:]+:[^@]+@',
    # AWS credentials
    r'(aws_access_key_id|aws_secret_access_key)[\s:=]+[^\s]+',
]


class OutputSanitizer:
    """
    WB-002: Sanitize build output to prevent secret leakage.

    Removes sensitive information like API keys, passwords, tokens,
    and other credentials from terminal output.
    """

    def __init__(self):
        """Initialize sanitizer with compiled regex patterns."""
        self.patterns = [re.compile(pattern, re.IGNORECASE) for pattern in SECRET_PATTERNS]

    def sanitize(self, text: str) -> str:
        """
        Sanitize text by replacing sensitive patterns.

        Args:
            text: Input text to sanitize

        Returns:
            Sanitized text with secrets redacted
        """
        sanitized = text

        for pattern in self.patterns:
            # Replace sensitive data with ***REDACTED***
            sanitized = pattern.sub('***REDACTED***', sanitized)

        return sanitized


class BuildStreamServer:
    """
    WB-002: WebSocket server for real-time build streaming.

    Provides:
    - Live terminal output streaming
    - Build status updates
    - Current task display
    - Progress tracking
    - Output sanitization
    """

    def __init__(self, app: Optional['Flask'] = None):
        """
        Initialize the build stream server.

        Args:
            app: Flask application instance (optional, will create if None)
        """
        if not DEPENDENCIES_AVAILABLE:
            raise ImportError(
                "Flask-SocketIO dependencies not available. "
                "Install with: pip install flask flask-socketio flask-cors"
            )

        # Create Flask app if not provided
        if app is None:
            self.app = Flask(__name__)
            # Configure CORS for WebSocket
            CORS(self.app, origins=['http://localhost:3000', 'https://ralphmode.com'])
        else:
            self.app = app

        # Configure SocketIO
        self.socketio = SocketIO(
            self.app,
            cors_allowed_origins=['http://localhost:3000', 'https://ralphmode.com'],
            async_mode='threading'
        )

        # Initialize sanitizer
        self.sanitizer = OutputSanitizer()

        # Track connected clients per build
        self.build_rooms: Dict[int, Set[str]] = {}

        # Register event handlers
        self._register_handlers()

        logger.info("BuildStreamServer initialized")

    def _register_handlers(self):
        """Register WebSocket event handlers."""

        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection."""
            logger.info(f"Client connected: {request.sid}")
            emit('connected', {'status': 'Connected to build stream'})

        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            logger.info(f"Client disconnected: {request.sid}")

        @self.socketio.on('subscribe_build')
        def handle_subscribe(data):
            """
            Subscribe to a specific build's output.

            Args:
                data: Dict with 'feedback_id' key
            """
            try:
                feedback_id = data.get('feedback_id')
                if not feedback_id:
                    emit('error', {'message': 'feedback_id required'})
                    return

                # Join room for this build
                room = f'build_{feedback_id}'
                join_room(room)

                # Track client
                if feedback_id not in self.build_rooms:
                    self.build_rooms[feedback_id] = set()
                self.build_rooms[feedback_id].add(request.sid)

                logger.info(f"Client {request.sid} subscribed to build {feedback_id}")
                emit('subscribed', {
                    'feedback_id': feedback_id,
                    'message': f'Subscribed to build {feedback_id}'
                })

            except Exception as e:
                logger.error(f"Error subscribing: {e}")
                emit('error', {'message': str(e)})

        @self.socketio.on('unsubscribe_build')
        def handle_unsubscribe(data):
            """
            Unsubscribe from a build's output.

            Args:
                data: Dict with 'feedback_id' key
            """
            try:
                feedback_id = data.get('feedback_id')
                if not feedback_id:
                    return

                # Leave room
                room = f'build_{feedback_id}'
                leave_room(room)

                # Remove from tracking
                if feedback_id in self.build_rooms:
                    self.build_rooms[feedback_id].discard(request.sid)

                logger.info(f"Client {request.sid} unsubscribed from build {feedback_id}")
                emit('unsubscribed', {'feedback_id': feedback_id})

            except Exception as e:
                logger.error(f"Error unsubscribing: {e}")

    def emit_build_output(self, feedback_id: int, output: str):
        """
        Emit build output to all subscribed clients.

        Args:
            feedback_id: Feedback ID being built
            output: Terminal output line
        """
        try:
            # Sanitize output to remove secrets
            sanitized_output = self.sanitizer.sanitize(output)

            # Emit to room
            room = f'build_{feedback_id}'
            self.socketio.emit(
                'build_output',
                {
                    'feedback_id': feedback_id,
                    'output': sanitized_output,
                    'timestamp': self._get_timestamp()
                },
                room=room
            )

        except Exception as e:
            logger.error(f"Error emitting build output: {e}")

    def emit_build_status(self, feedback_id: int, status: str, message: Optional[str] = None):
        """
        Emit build status update.

        Args:
            feedback_id: Feedback ID being built
            status: Build status (pending, in_progress, testing, deploying, complete, failed)
            message: Optional status message
        """
        try:
            room = f'build_{feedback_id}'
            self.socketio.emit(
                'build_status',
                {
                    'feedback_id': feedback_id,
                    'status': status,
                    'message': message,
                    'timestamp': self._get_timestamp()
                },
                room=room
            )

            logger.info(f"Build {feedback_id} status: {status}")

        except Exception as e:
            logger.error(f"Error emitting build status: {e}")

    def emit_build_progress(self, feedback_id: int, current_task: str, progress: float):
        """
        Emit build progress update.

        Args:
            feedback_id: Feedback ID being built
            current_task: Description of current task
            progress: Progress percentage (0-100)
        """
        try:
            room = f'build_{feedback_id}'
            self.socketio.emit(
                'build_progress',
                {
                    'feedback_id': feedback_id,
                    'current_task': current_task,
                    'progress': progress,
                    'timestamp': self._get_timestamp()
                },
                room=room
            )

        except Exception as e:
            logger.error(f"Error emitting build progress: {e}")

    def emit_test_output(self, feedback_id: int, test_name: str, result: str, output: Optional[str] = None):
        """
        Emit test execution output.

        Args:
            feedback_id: Feedback ID being built
            test_name: Name of test being run
            result: Test result (pass, fail, skip)
            output: Optional test output
        """
        try:
            # Sanitize output
            sanitized_output = self.sanitizer.sanitize(output) if output else None

            room = f'build_{feedback_id}'
            self.socketio.emit(
                'test_output',
                {
                    'feedback_id': feedback_id,
                    'test_name': test_name,
                    'result': result,
                    'output': sanitized_output,
                    'timestamp': self._get_timestamp()
                },
                room=room
            )

        except Exception as e:
            logger.error(f"Error emitting test output: {e}")

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat()

    def run(self, host: str = '0.0.0.0', port: int = 5001, debug: bool = False):
        """
        Run the WebSocket server.

        Args:
            host: Host to bind to
            port: Port to listen on
            debug: Enable debug mode
        """
        logger.info(f"Starting BuildStreamServer on {host}:{port}")
        self.socketio.run(self.app, host=host, port=port, debug=debug)


# Global server instance
_server_instance: Optional[BuildStreamServer] = None


def get_build_stream_server(app: Optional[Flask] = None) -> BuildStreamServer:
    """
    Get the global BuildStreamServer instance.

    Args:
        app: Flask application instance (optional)

    Returns:
        BuildStreamServer instance
    """
    global _server_instance

    if _server_instance is None:
        _server_instance = BuildStreamServer(app)

    return _server_instance


if __name__ == '__main__':
    # Run standalone server for testing
    server = BuildStreamServer()
    server.run(debug=True)
