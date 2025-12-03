"""
Direct tool definitions using FastMCP decorators.

This module demonstrates how to define MCP tools directly as Python functions.
Add your custom tools here following the same pattern.
"""

import logging
from typing import Dict, Any

from utils.validation import validate_required_fields, validate_type, sanitize_string
from utils.observability import trace_tool_execution, record_metric

logger = logging.getLogger(__name__)


def register_direct_tools(mcp):
    """
    Register direct tools with the MCP server.
    
    This function is called from server.py to register all tools.
    Add your tool registration here.
    
    Args:
        mcp: FastMCP server instance
    """
    logger.info("Registering direct tools...")
    
    # Example: String manipulation tool
    @mcp.tool()
    @trace_tool_execution("process_text")
    @validate_required_fields(["text"])
    def process_text(text: str, operation: str = "uppercase") -> str:
        """
        Process text with various operations.
        
        Args:
            text: The text to process
            operation: Operation to perform (uppercase, lowercase, title, reverse)
        
        Returns:
            Processed text
        """
        record_metric("tool.invocations", 1, {"tool": "process_text", "operation": operation})
        
        # Sanitize input
        clean_text = sanitize_string(text, max_length=10000)
        
        # Perform operation
        operations = {
            "uppercase": lambda t: t.upper(),
            "lowercase": lambda t: t.lower(),
            "title": lambda t: t.title(),
            "reverse": lambda t: t[::-1],
            "length": lambda t: str(len(t))
        }
        
        if operation not in operations:
            return f"Unknown operation: {operation}. Available: {', '.join(operations.keys())}"
        
        result = operations[operation](clean_text)
        logger.info(f"Processed text with operation '{operation}'")
        
        return result
    
    # Example: Data validation tool
    @mcp.tool()
    @trace_tool_execution("validate_data")
    def validate_data(data: Dict[str, Any], rules: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate data against specified rules.
        
        Args:
            data: Data to validate
            rules: Validation rules (e.g., {"age": {"type": "int", "min": 0, "max": 120}})
        
        Returns:
            Validation result with status and errors
        """
        record_metric("tool.invocations", 1, {"tool": "validate_data"})
        
        errors = []
        
        for field, rule in rules.items():
            if field not in data:
                if rule.get("required", False):
                    errors.append(f"Missing required field: {field}")
                continue
            
            value = data[field]
            
            # Type validation
            if "type" in rule:
                expected_type = {
                    "int": int,
                    "str": str,
                    "float": float,
                    "bool": bool
                }.get(rule["type"])
                
                if expected_type and not isinstance(value, expected_type):
                    errors.append(f"Field '{field}' must be {rule['type']}, got {type(value).__name__}")
            
            # Range validation for numbers
            if isinstance(value, (int, float)):
                if "min" in rule and value < rule["min"]:
                    errors.append(f"Field '{field}' must be >= {rule['min']}")
                if "max" in rule and value > rule["max"]:
                    errors.append(f"Field '{field}' must be <= {rule['max']}")
        
        result = {
            "valid": len(errors) == 0,
            "errors": errors,
            "validated_fields": len(data)
        }
        
        logger.info(f"Validated data: {'valid' if result['valid'] else 'invalid'}")
        
        return result
    
    # Example: JSON transformation tool
    @mcp.tool()
    @trace_tool_execution("transform_json")
    def transform_json(data: Dict[str, Any], transformations: Dict[str, str]) -> Dict[str, Any]:
        """
        Transform JSON data by applying field mappings.
        
        Args:
            data: Input JSON data
            transformations: Field mappings (e.g., {"old_name": "new_name"})
        
        Returns:
            Transformed JSON data
        """
        record_metric("tool.invocations", 1, {"tool": "transform_json"})
        
        result = {}
        
        for old_key, new_key in transformations.items():
            if old_key in data:
                result[new_key] = data[old_key]
        
        # Include fields not in transformation map
        for key, value in data.items():
            if key not in transformations:
                result[key] = value
        
        logger.info(f"Transformed JSON with {len(transformations)} mappings")
        
        return result
    
    logger.info(f"✓ Registered {3} direct tools")


# ==============================================================================
# TEMPLATE FOR YOUR CUSTOM TOOLS
# ==============================================================================

def template_for_your_tool(mcp):
    """
    Template showing how to add your own tools.
    
    Copy this template and customize it for your needs.
    """
    
    @mcp.tool()
    @trace_tool_execution("my_custom_tool")
    @validate_required_fields(["required_param"])
    def my_custom_tool(required_param: str, optional_param: int = 0) -> Dict[str, Any]:
        """
        Brief description of what your tool does.
        
        This docstring is important - it helps AI agents understand
        when and how to use your tool.
        
        Args:
            required_param: Description of this parameter
            optional_param: Description of optional parameter
        
        Returns:
            Description of return value
        """
        # Record metric for monitoring
        record_metric("tool.invocations", 1, {"tool": "my_custom_tool"})
        
        # Your business logic here
        result = {
            "success": True,
            "data": f"Processed: {required_param}",
            "metadata": {
                "optional_param": optional_param
            }
        }
        
        logger.info("Custom tool executed successfully")
        
        return result
