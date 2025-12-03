"""
Configuration management for MCP server.

Loads configuration from config.yaml and environment variables,
with environment variables taking precedence.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from dotenv import load_dotenv


class Config:
    """Configuration manager for MCP server."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to config.yaml file. If None, uses default location.
        """
        # Load environment variables from .env file if present
        load_dotenv()
        
        # Determine config file path
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        
        # Load configuration from YAML
        self._config = self._load_yaml(config_path)
        
        # Apply environment-specific overrides
        self._apply_environment_overrides()
        
        # Override with environment variables
        self._apply_env_vars()
    
    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            print(f"Warning: Config file not found at {path}, using defaults")
            return self._get_defaults()
        except yaml.YAMLError as e:
            print(f"Error parsing config file: {e}, using defaults")
            return self._get_defaults()
    
    def _get_defaults(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "server": {
                "host": "0.0.0.0",
                "port": 8000,
                "mcp_path": "/mcp",
                "stateless_http": True
            },
            "mcp": {
                "protocol_version": "2024-11-05",
                "server_name": "mcp-server",
                "server_version": "1.0.0"
            },
            "tools": {
                "mode": "direct"
            },
            "observability": {
                "enabled": True,
                "service_name": "mcp-server"
            },
            "logging": {
                "level": "INFO"
            },
            "security": {
                "validate_inputs": True
            }
        }
    
    def _apply_environment_overrides(self):
        """Apply environment-specific configuration overrides."""
        env = os.getenv("ENVIRONMENT", "development").lower()
        
        if "environments" in self._config and env in self._config["environments"]:
            overrides = self._config["environments"][env]
            self._deep_merge(self._config, overrides)
    
    def _apply_env_vars(self):
        """Override configuration with environment variables."""
        # Server configuration
        if host := os.getenv("MCP_SERVER_HOST"):
            self._config["server"]["host"] = host
        if port := os.getenv("MCP_SERVER_PORT"):
            self._config["server"]["port"] = int(port)
        
        # Observability
        if os.getenv("MCP_OBSERVABILITY_ENABLED"):
            self._config["observability"]["enabled"] = (
                os.getenv("MCP_OBSERVABILITY_ENABLED", "true").lower() == "true"
            )
        if service_name := os.getenv("MCP_SERVICE_NAME"):
            self._config["observability"]["service_name"] = service_name
        
        # Logging
        if log_level := os.getenv("MCP_LOG_LEVEL"):
            self._config["logging"]["level"] = log_level.upper()
        
        # AWS Configuration
        self._config["aws"] = {
            "region": os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-west-2")),
            "account_id": os.getenv("AWS_ACCOUNT_ID")
        }
    
    def _deep_merge(self, base: Dict, override: Dict):
        """Deep merge override dict into base dict."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def get(self, path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            path: Configuration path (e.g., "server.host")
            default: Default value if path not found
        
        Returns:
            Configuration value or default
        """
        keys = path.split(".")
        value = self._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section.
        
        Args:
            section: Section name (e.g., "server", "mcp")
        
        Returns:
            Configuration section as dict
        """
        return self._config.get(section, {})
    
    @property
    def server_host(self) -> str:
        """Get server host."""
        return self.get("server.host", "0.0.0.0")
    
    @property
    def server_port(self) -> int:
        """Get server port."""
        return self.get("server.port", 8000)
    
    @property
    def mcp_path(self) -> str:
        """Get MCP endpoint path."""
        return self.get("server.mcp_path", "/mcp")
    
    @property
    def stateless_http(self) -> bool:
        """Check if stateless HTTP is enabled."""
        return self.get("server.stateless_http", True)
    
    @property
    def observability_enabled(self) -> bool:
        """Check if observability is enabled."""
        return self.get("observability.enabled", True)
    
    @property
    def service_name(self) -> str:
        """Get service name for observability."""
        return self.get("observability.service_name", "mcp-server")
    
    @property
    def log_level(self) -> str:
        """Get log level."""
        return self.get("logging.level", "INFO")


# Global configuration instance
config = Config()
