"""
Example: Calculator Tools

This example demonstrates the Direct Tool Definition mode.
Simple calculator tools showing proper input validation, error handling, and documentation.
"""

import logging
from typing import List

from utils.validation import validate_type, validate_required_fields
from utils.observability import trace_tool_execution, record_metric
from utils.error_handling import MCPError

logger = logging.getLogger(__name__)


def register_calculator_tools(mcp):
    """
    Register calculator tools with the MCP server.
    
    Args:
        mcp: FastMCP server instance
    """
    logger.info("Registering calculator tools...")
    
    @mcp.tool()
    @trace_tool_execution("add_numbers")
    def add_numbers(a: float, b: float) -> float:
        """
        Add two numbers together.
        
        Args:
            a: First number
            b: Second number
        
        Returns:
            Sum of a and b
        """
        record_metric("calculator.operations", 1, {"operation": "add"})
        result = a + b
        logger.debug(f"Addition: {a} + {b} = {result}")
        return result
    
    @mcp.tool()
    @trace_tool_execution("subtract_numbers")
    def subtract_numbers(a: float, b: float) -> float:
        """
        Subtract b from a.
        
        Args:
            a: Number to subtract from
            b: Number to subtract
        
        Returns:
            Difference of a and b
        """
        record_metric("calculator.operations", 1, {"operation": "subtract"})
        result = a - b
        logger.debug(f"Subtraction: {a} - {b} = {result}")
        return result
    
    @mcp.tool()
    @trace_tool_execution("multiply_numbers")
    def multiply_numbers(a: float, b: float) -> float:
        """
        Multiply two numbers together.
        
        Args:
            a: First number
            b: Second number
        
        Returns:
            Product of a and b
        """
        record_metric("calculator.operations", 1, {"operation": "multiply"})
        result = a * b
        logger.debug(f"Multiplication: {a} * {b} = {result}")
        return result
    
    @mcp.tool()
    @trace_tool_execution("divide_numbers")
    def divide_numbers(a: float, b: float) -> float:
        """
        Divide a by b.
        
        Args:
            a: Numerator
            b: Denominator (must not be zero)
        
        Returns:
            Quotient of a and b
        
        Raises:
            MCPError: If b is zero
        """
        record_metric("calculator.operations", 1, {"operation": "divide"})
        
        if b == 0:
            logger.error("Division by zero attempted")
            raise MCPError(
                "Cannot divide by zero",
                code="division_by_zero",
                details={"numerator": a, "denominator": b}
            )
        
        result = a / b
        logger.debug(f"Division: {a} / {b} = {result}")
        return result
    
    @mcp.tool()
    @trace_tool_execution("power")
    def power(base: float, exponent: float) -> float:
        """
        Calculate base raised to the power of exponent.
        
        Args:
            base: Base number
            exponent: Power to raise base to
        
        Returns:
            base^exponent
        """
        record_metric("calculator.operations", 1, {"operation": "power"})
        result = base ** exponent
        logger.debug(f"Power: {base}^{exponent} = {result}")
        return result
    
    @mcp.tool()
    @trace_tool_execution("calculate_average")
    def calculate_average(numbers: List[float]) -> float:
        """
        Calculate the average of a list of numbers.
        
        Args:
            numbers: List of numbers to average
        
        Returns:
            Average value
        
        Raises:
            MCPError: If numbers list is empty
        """
        record_metric("calculator.operations", 1, {"operation": "average"})
        
        if not numbers:
            raise MCPError(
                "Cannot calculate average of empty list",
                code="empty_list",
                details={"numbers": numbers}
            )
        
        result = sum(numbers) / len(numbers)
        logger.debug(f"Average of {len(numbers)} numbers: {result}")
        return result
    
    @mcp.tool()
    @trace_tool_execution("calculate_statistics")
    def calculate_statistics(numbers: List[float]) -> dict:
        """
        Calculate comprehensive statistics for a list of numbers.
        
        Args:
            numbers: List of numbers to analyze
        
        Returns:
            Dictionary with min, max, average, sum, count, and median
        
        Raises:
            MCPError: If numbers list is empty
        """
        record_metric("calculator.operations", 1, {"operation": "statistics"})
        
        if not numbers:
            raise MCPError(
                "Cannot calculate statistics of empty list",
                code="empty_list"
            )
        
        sorted_numbers = sorted(numbers)
        n = len(sorted_numbers)
        
        # Calculate median
        if n % 2 == 0:
            median = (sorted_numbers[n//2 - 1] + sorted_numbers[n//2]) / 2
        else:
            median = sorted_numbers[n//2]
        
        result = {
            "count": n,
            "sum": sum(numbers),
            "average": sum(numbers) / n,
            "min": min(numbers),
            "max": max(numbers),
            "median": median
        }
        
        logger.debug(f"Statistics calculated for {n} numbers")
        return result
    
    logger.info(f"✓ Registered {7} calculator tools")
