"""
Observability utilities for MCP server.

Integrates with AWS Distro for OpenTelemetry (ADOT) for traces, spans, and metrics.
"""

import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Try to import OpenTelemetry dependencies
try:
    from opentelemetry import trace, metrics, baggage, context
    from opentelemetry.trace import Status, StatusCode
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    logger.warning("OpenTelemetry not available. Install aws-opentelemetry-distro for observability.")


def setup_observability(service_name: str):
    """
    Setup observability with ADOT.
    
    This function is called when the server starts with observability enabled.
    The actual instrumentation is handled by running with:
    opentelemetry-instrument python src/server.py
    
    Args:
        service_name: Name of the service for traces and metrics
    """
    if not OTEL_AVAILABLE:
        logger.warning("Observability setup skipped - OpenTelemetry not available")
        return
    
    logger.info(f"Observability configured for service: {service_name}")
    logger.info("Run with: opentelemetry-instrument python src/server.py")


def trace_tool_execution(tool_name: str):
    """
    Decorator to trace tool execution with OpenTelemetry.
    
    Creates a span for each tool execution with timing and metadata.
    
    Args:
        tool_name: Name of the tool being traced
    
    Returns:
        Decorated function with tracing
    
    Example:
        @trace_tool_execution("my_tool")
        def my_tool(input_data: str) -> str:
            return process(input_data)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not OTEL_AVAILABLE:
                return await func(*args, **kwargs)
            
            tracer = trace.get_tracer(__name__)
            
            with tracer.start_as_current_span(
                f"tool.{tool_name}",
                attributes={
                    "tool.name": tool_name,
                    "tool.function": func.__name__
                }
            ) as span:
                try:
                    start_time = time.time()
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    span.set_attribute("tool.duration_ms", duration * 1000)
                    span.set_status(Status(StatusCode.OK))
                    
                    return result
                
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not OTEL_AVAILABLE:
                return func(*args, **kwargs)
            
            tracer = trace.get_tracer(__name__)
            
            with tracer.start_as_current_span(
                f"tool.{tool_name}",
                attributes={
                    "tool.name": tool_name,
                    "tool.function": func.__name__
                }
            ) as span:
                try:
                    start_time = time.time()
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    span.set_attribute("tool.duration_ms", duration * 1000)
                    span.set_status(Status(StatusCode.OK))
                    
                    return result
                
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def record_metric(
    metric_name: str,
    value: float,
    attributes: Optional[Dict[str, Any]] = None
):
    """
    Record a custom metric.
    
    Args:
        metric_name: Name of the metric
        value: Metric value
        attributes: Additional attributes/dimensions for the metric
    
    Example:
        record_metric("tool.invocations", 1, {"tool_name": "calculator"})
    """
    if not OTEL_AVAILABLE:
        return
    
    try:
        meter = metrics.get_meter(__name__)
        counter = meter.create_counter(
            name=metric_name,
            description=f"Custom metric: {metric_name}"
        )
        
        counter.add(value, attributes=attributes or {})
    
    except Exception as e:
        logger.warning(f"Failed to record metric {metric_name}: {e}")


def set_session_id(session_id: str):
    """
    Set session ID in OpenTelemetry baggage for propagation.
    
    This enables session tracking across traces.
    
    Args:
        session_id: Session identifier to propagate
    
    Example:
        set_session_id("my-session-123")
    """
    if not OTEL_AVAILABLE:
        return
    
    try:
        ctx = baggage.set_baggage("session.id", session_id)
        context.attach(ctx)
    except Exception as e:
        logger.warning(f"Failed to set session ID in baggage: {e}")


def get_session_id() -> Optional[str]:
    """
    Get session ID from OpenTelemetry baggage.
    
    Returns:
        Session ID if available, None otherwise
    """
    if not OTEL_AVAILABLE:
        return None
    
    try:
        return baggage.get_baggage("session.id")
    except Exception as e:
        logger.warning(f"Failed to get session ID from baggage: {e}")
        return None


def add_span_attribute(key: str, value: Any):
    """
    Add an attribute to the current span.
    
    Args:
        key: Attribute key
        value: Attribute value
    """
    if not OTEL_AVAILABLE:
        return
    
    try:
        span = trace.get_current_span()
        if span:
            span.set_attribute(key, value)
    except Exception as e:
        logger.warning(f"Failed to add span attribute {key}: {e}")


def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Add an event to the current span.
    
    Args:
        name: Event name
        attributes: Event attributes
    """
    if not OTEL_AVAILABLE:
        return
    
    try:
        span = trace.get_current_span()
        if span:
            span.add_event(name, attributes=attributes or {})
    except Exception as e:
        logger.warning(f"Failed to add span event {name}: {e}")


class ToolMetrics:
    """Helper class for tracking tool-specific metrics."""
    
    def __init__(self, tool_name: str):
        """
        Initialize tool metrics tracker.
        
        Args:
            tool_name: Name of the tool to track
        """
        self.tool_name = tool_name
        self.invocations = 0
        self.errors = 0
        self.total_duration = 0.0
    
    def record_invocation(self):
        """Record a tool invocation."""
        self.invocations += 1
        record_metric(
            "mcp.tool.invocations",
            1,
            {"tool_name": self.tool_name}
        )
    
    def record_error(self):
        """Record a tool error."""
        self.errors += 1
        record_metric(
            "mcp.tool.errors",
            1,
            {"tool_name": self.tool_name}
        )
    
    def record_duration(self, duration_ms: float):
        """
        Record tool execution duration.
        
        Args:
            duration_ms: Duration in milliseconds
        """
        self.total_duration += duration_ms
        record_metric(
            "mcp.tool.duration_ms",
            duration_ms,
            {"tool_name": self.tool_name}
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get tool statistics.
        
        Returns:
            Dictionary with tool metrics
        """
        avg_duration = (
            self.total_duration / self.invocations 
            if self.invocations > 0 
            else 0
        )
        
        return {
            "tool_name": self.tool_name,
            "invocations": self.invocations,
            "errors": self.errors,
            "error_rate": self.errors / self.invocations if self.invocations > 0 else 0,
            "avg_duration_ms": avg_duration
        }
