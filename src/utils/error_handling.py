"""
Error handling utilities for MCP server.

Provides centralized error handling, logging, and response formatting.
"""

import logging
import traceback
from typing import Any, Dict
from functools import wraps

from starlette.responses import JSONResponse
from starlette.requests import Request

logger = logging.getLogger(__name__)


class MCPError(Exception):
    """Base exception for MCP server errors."""
    
    def __init__(self, message: str, code: str = "internal_error", details: Dict = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class ToolNotFoundError(MCPError):
    """Exception raised when a requested tool is not found."""
    
    def __init__(self, tool_name: str):
        super().__init__(
            message=f"Tool '{tool_name}' not found",
            code="tool_not_found",
            details={"tool_name": tool_name}
        )


class ValidationError(MCPError):
    """Exception raised for input validation errors."""
    
    def __init__(self, message: str, details: Dict = None):
        super().__init__(
            message=message,
            code="validation_error",
            details=details
        )


class ToolExecutionError(MCPError):
    """Exception raised when tool execution fails."""
    
    def __init__(self, tool_name: str, error: str):
        super().__init__(
            message=f"Tool '{tool_name}' execution failed: {error}",
            code="tool_execution_error",
            details={"tool_name": tool_name, "error": error}
        )


def handle_tool_errors(func):
    """
    Decorator to handle errors in tool execution.
    
    Catches exceptions and converts them to standardized error responses.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except MCPError as e:
            logger.error(f"MCP Error in {func.__name__}: {e.message}")
            return create_error_response(e.message, e.code, e.details)
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            return create_error_response(
                "An unexpected error occurred",
                "internal_error",
                {"error": str(e)}
            )
    
    return wrapper


def create_error_response(
    message: str,
    code: str = "error",
    details: Dict = None,
    status_code: int = 400,
    include_stack_trace: bool = False
) -> JSONResponse:
    """
    Create a standardized error response.
    
    Args:
        message: Human-readable error message
        code: Error code identifier
        details: Additional error details
        status_code: HTTP status code
        include_stack_trace: Whether to include stack trace in response
    
    Returns:
        JSONResponse with error information
    """
    error_data = {
        "error": {
            "code": code,
            "message": message
        }
    }
    
    if details:
        error_data["error"]["details"] = details
    
    if include_stack_trace:
        error_data["error"]["stack_trace"] = traceback.format_exc()
    
    return JSONResponse(
        content=error_data,
        status_code=status_code
    )


async def handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle validation errors.
    
    Args:
        request: Starlette Request object
        exc: Exception that was raised
    
    Returns:
        JSONResponse with validation error details
    """
    logger.warning(f"Validation error on {request.url.path}: {exc}")
    
    return create_error_response(
        message="Invalid input parameters",
        code="validation_error",
        details={"error": str(exc)},
        status_code=422
    )


async def handle_not_found_error(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle not found errors.
    
    Args:
        request: Starlette Request object
        exc: Exception that was raised
    
    Returns:
        JSONResponse with not found error details
    """
    logger.warning(f"Resource not found on {request.url.path}: {exc}")
    
    return create_error_response(
        message="Requested resource not found",
        code="not_found",
        details={"path": request.url.path},
        status_code=404
    )


async def handle_internal_error(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle internal server errors.
    
    Args:
        request: Starlette Request object
        exc: Exception that was raised
    
    Returns:
        JSONResponse with internal error details
    """
    logger.error(f"Internal error on {request.url.path}: {exc}", exc_info=True)
    
    return create_error_response(
        message="An internal error occurred",
        code="internal_error",
        details={"error": str(exc)},
        status_code=500,
        include_stack_trace=False  # Never expose stack traces in production
    )


def setup_error_handlers(mcp_server):
    """
    Setup error handlers for the MCP server.
    
    Args:
        mcp_server: FastMCP server instance
    """
    # Note: FastMCP may have its own error handling mechanisms
    # This function is a placeholder for additional custom error handling
    logger.info("Error handlers configured")


def log_error(error: Exception, context: Dict[str, Any] = None):
    """
    Log an error with context.
    
    Args:
        error: Exception that occurred
        context: Additional context information
    """
    context_str = ""
    if context:
        context_str = " | Context: " + ", ".join(f"{k}={v}" for k, v in context.items())
    
    logger.error(f"Error: {type(error).__name__}: {error}{context_str}", exc_info=True)


def safe_execute(func, *args, **kwargs):
    """
    Safely execute a function with error handling.
    
    Args:
        func: Function to execute
        *args: Positional arguments
        **kwargs: Keyword arguments
    
    Returns:
        Tuple of (result, error) where one will be None
    """
    try:
        result = func(*args, **kwargs)
        return result, None
    except Exception as e:
        log_error(e, {"function": func.__name__})
        return None, e
