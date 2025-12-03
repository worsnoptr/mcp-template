"""
Input validation utilities for MCP tools.

Provides decorators and functions for validating tool inputs before processing.
"""

import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional, Type
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class ValidationException(Exception):
    """Exception raised for input validation errors."""
    
    def __init__(self, message: str, errors: Optional[Dict] = None):
        super().__init__(message)
        self.errors = errors or {}


def validate_with_schema(schema: Type[BaseModel]):
    """
    Decorator to validate tool inputs against a Pydantic schema.
    
    Args:
        schema: Pydantic BaseModel class defining the expected schema
    
    Returns:
        Decorated function with input validation
    
    Example:
        @validate_with_schema(MySchema)
        def my_tool(validated_input):
            # validated_input is guaranteed to match MySchema
            return validated_input.field_name
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # If first argument is dict, validate it
                if args and isinstance(args[0], dict):
                    validated = schema(**args[0])
                    return func(validated, *args[1:], **kwargs)
                # If keyword arguments, validate them
                elif kwargs:
                    validated = schema(**kwargs)
                    return func(validated)
                else:
                    return func(*args, **kwargs)
            
            except ValidationError as e:
                logger.error(f"Validation error in {func.__name__}: {e}")
                raise ValidationException(
                    f"Invalid input for {func.__name__}",
                    errors=e.errors()
                )
        
        return wrapper
    return decorator


def validate_required_fields(required_fields: list):
    """
    Decorator to check for required fields in input dict.
    
    Args:
        required_fields: List of required field names
    
    Returns:
        Decorated function with required field validation
    
    Example:
        @validate_required_fields(["name", "email"])
        def create_user(data: dict):
            return f"Created user: {data['name']}"
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check first argument if it's a dict
            input_data = None
            if args and isinstance(args[0], dict):
                input_data = args[0]
            elif kwargs:
                input_data = kwargs
            
            if input_data:
                missing_fields = [
                    field for field in required_fields 
                    if field not in input_data
                ]
                
                if missing_fields:
                    raise ValidationException(
                        f"Missing required fields: {', '.join(missing_fields)}",
                        errors={"missing_fields": missing_fields}
                    )
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def validate_type(field_types: Dict[str, type]):
    """
    Decorator to validate field types in input dict.
    
    Args:
        field_types: Dict mapping field names to expected types
    
    Returns:
        Decorated function with type validation
    
    Example:
        @validate_type({"age": int, "name": str})
        def process_user(data: dict):
            return data
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check first argument if it's a dict
            input_data = None
            if args and isinstance(args[0], dict):
                input_data = args[0]
            elif kwargs:
                input_data = kwargs
            
            if input_data:
                type_errors = {}
                for field, expected_type in field_types.items():
                    if field in input_data:
                        value = input_data[field]
                        if not isinstance(value, expected_type):
                            type_errors[field] = {
                                "expected": expected_type.__name__,
                                "actual": type(value).__name__
                            }
                
                if type_errors:
                    raise ValidationException(
                        f"Type validation failed for fields: {', '.join(type_errors.keys())}",
                        errors=type_errors
                    )
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def validate_range(field_ranges: Dict[str, tuple]):
    """
    Decorator to validate numeric field ranges.
    
    Args:
        field_ranges: Dict mapping field names to (min, max) tuples
    
    Returns:
        Decorated function with range validation
    
    Example:
        @validate_range({"age": (0, 120), "score": (0, 100)})
        def process_data(data: dict):
            return data
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check first argument if it's a dict
            input_data = None
            if args and isinstance(args[0], dict):
                input_data = args[0]
            elif kwargs:
                input_data = kwargs
            
            if input_data:
                range_errors = {}
                for field, (min_val, max_val) in field_ranges.items():
                    if field in input_data:
                        value = input_data[field]
                        if not (min_val <= value <= max_val):
                            range_errors[field] = {
                                "value": value,
                                "min": min_val,
                                "max": max_val
                            }
                
                if range_errors:
                    raise ValidationException(
                        f"Range validation failed for fields: {', '.join(range_errors.keys())}",
                        errors=range_errors
                    )
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def sanitize_string(value: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize string input by removing potentially dangerous characters.
    
    Args:
        value: Input string to sanitize
        max_length: Maximum allowed length (None = no limit)
    
    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        raise ValidationException("Value must be a string")
    
    # Strip whitespace
    sanitized = value.strip()
    
    # Truncate if needed
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized


def validate_email(email: str) -> bool:
    """
    Basic email validation.
    
    Args:
        email: Email address to validate
    
    Returns:
        True if email format is valid
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """
    Basic URL validation.
    
    Args:
        url: URL to validate
    
    Returns:
        True if URL format is valid
    """
    import re
    pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
    return bool(re.match(pattern, url))
