"""
Structured logging configuration for enterprise-grade observability.

This module provides centralized logging configuration with:
- Structured JSON logging for production
- Request/response logging with timings
- Correlation IDs for request tracing
- Different log levels for different environments
"""

import logging
import logging.config
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from contextvars import ContextVar
import os

# Context variables for request tracking
request_id_var: ContextVar[str] = ContextVar('request_id', default='')
user_id_var: ContextVar[str] = ContextVar('user_id', default='')
tenant_id_var: ContextVar[str] = ContextVar('tenant_id', default='')


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        # Base log entry
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add request context if available
        request_id = request_id_var.get('')
        if request_id:
            log_entry['request_id'] = request_id
            
        user_id = user_id_var.get('')
        if user_id:
            log_entry['user_id'] = user_id
            
        tenant_id = tenant_id_var.get('')
        if tenant_id:
            log_entry['tenant_id'] = tenant_id
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
            
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_entry.update(getattr(record, 'extra_fields', {}))
            
        return json.dumps(log_entry, default=str)


class RequestLogger:
    """
    Utility class for structured request/response logging.
    """
    
    @staticmethod
    def log_request(
        method: str,
        path: str,
        query_params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        body_size: Optional[int] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log incoming request details."""
        logger = logging.getLogger("api.request")
        
        log_data = {
            'event_type': 'request_started',
            'http_method': method,
            'path': path,
            'client_ip': client_ip,
            'user_agent': user_agent,
            'body_size_bytes': body_size
        }
        
        if query_params:
            log_data['query_params'] = query_params
            
        # Log selected headers (avoid sensitive data)
        if headers:
            safe_headers = {
                k: v for k, v in headers.items() 
                if k.lower() not in ['authorization', 'cookie', 'x-api-key']
            }
            if safe_headers:
                log_data['headers'] = safe_headers
        
        logger.info("HTTP request started", extra={'extra_fields': log_data})
    
    @staticmethod
    def log_response(
        status_code: int,
        response_time_ms: float,
        response_size: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        """Log response details with timing."""
        logger = logging.getLogger("api.response")
        
        log_data = {
            'event_type': 'request_completed',
            'status_code': status_code,
            'response_time_ms': round(response_time_ms, 2),
            'response_size_bytes': response_size
        }
        
        if error_message:
            log_data['error_message'] = error_message
            
        # Determine log level based on status code
        if status_code >= 500:
            logger.error("HTTP request completed with server error", extra={'extra_fields': log_data})
        elif status_code >= 400:
            logger.warning("HTTP request completed with client error", extra={'extra_fields': log_data})
        else:
            logger.info("HTTP request completed successfully", extra={'extra_fields': log_data})


def get_logging_config() -> Dict[str, Any]:
    """
    Get logging configuration based on environment.
    """
    environment = os.getenv('ENVIRONMENT', 'development').lower()
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    if environment == 'production':
        # Production: Structured JSON logging
        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'structured': {
                    '()': StructuredFormatter,
                },
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'structured',
                    'level': log_level,
                },
                'file': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'filename': 'logs/app.log',
                    'maxBytes': 10485760,  # 10MB
                    'backupCount': 5,
                    'formatter': 'structured',
                    'level': log_level,
                },
            },
            'loggers': {
                'api': {
                    'handlers': ['console', 'file'],
                    'level': log_level,
                    'propagate': False,
                },
                'auth': {
                    'handlers': ['console', 'file'],
                    'level': log_level,
                    'propagate': False,
                },
                'cache': {
                    'handlers': ['console', 'file'],
                    'level': log_level,
                    'propagate': False,
                },
                'database': {
                    'handlers': ['console', 'file'],
                    'level': log_level,
                    'propagate': False,
                },
            },
            'root': {
                'handlers': ['console'],
                'level': log_level,
            },
        }
    else:
        # Development: Human-readable logging
        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'detailed': {
                    'format': '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s',
                    'datefmt': '%Y-%m-%d %H:%M:%S',
                },
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'detailed',
                    'level': log_level,
                },
            },
            'loggers': {
                'api': {
                    'handlers': ['console'],
                    'level': log_level,
                    'propagate': False,
                },
                'auth': {
                    'handlers': ['console'],
                    'level': log_level,
                    'propagate': False,
                },
                'cache': {
                    'handlers': ['console'],
                    'level': log_level,
                    'propagate': False,
                },
                'database': {
                    'handlers': ['console'],
                    'level': log_level,
                    'propagate': False,
                },
            },
            'root': {
                'handlers': ['console'],
                'level': log_level,
            },
        }


def setup_logging():
    """
    Initialize logging for the application.
    """
    # Create logs directory if it doesn't exist
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Apply logging configuration
    config = get_logging_config()
    logging.config.dictConfig(config)
    
    # Set up third-party library logging levels
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    """
    return logging.getLogger(name)


def set_request_context(request_id: str, user_id: str = '', tenant_id: str = ''):
    """
    Set request context for logging.
    """
    request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)
    if tenant_id:
        tenant_id_var.set(tenant_id)


def clear_request_context():
    """
    Clear request context.
    """
    request_id_var.set('')
    user_id_var.set('')
    tenant_id_var.set('')


def generate_request_id() -> str:
    """
    Generate a unique request ID for correlation.
    """
    return str(uuid.uuid4())


# Security-related logging helpers
def log_auth_event(event_type: str, user_email: str = '', success: bool = True, details: Optional[Dict[str, Any]] = None):
    """Log authentication events for security monitoring."""
    logger = get_logger('auth.security')
    
    log_data = {
        'event_type': f'auth_{event_type}',
        'user_email': user_email,
        'success': success,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    if details:
        log_data.update(details)
    
    if success:
        logger.info(f"Auth event: {event_type}", extra={'extra_fields': log_data})
    else:
        logger.warning(f"Auth event failed: {event_type}", extra={'extra_fields': log_data})


def log_permission_check(resource: str, action: str, user_id: str, tenant_id: str, allowed: bool):
    """Log permission checks for audit trails."""
    logger = get_logger('auth.permissions')
    
    log_data = {
        'event_type': 'permission_check',
        'resource': resource,
        'action': action,
        'user_id': user_id,
        'tenant_id': tenant_id,
        'allowed': allowed
    }
    
    if allowed:
        logger.debug("Permission granted", extra={'extra_fields': log_data})
    else:
        logger.warning("Permission denied", extra={'extra_fields': log_data})


def log_database_operation(operation: str, table: str, duration_ms: float, record_count: int = 1):
    """Log database operations with performance metrics."""
    logger = get_logger('database.operations')
    
    log_data = {
        'event_type': 'database_operation',
        'operation': operation,
        'table': table,
        'duration_ms': round(duration_ms, 2),
        'record_count': record_count
    }
    
    if duration_ms > 1000:  # Log slow queries
        logger.warning("Slow database operation", extra={'extra_fields': log_data})
    else:
        logger.debug("Database operation completed", extra={'extra_fields': log_data})


def log_cache_operation(operation: str, key: str, hit: Optional[bool] = None, duration_ms: Optional[float] = None):
    """Log cache operations for monitoring."""
    logger = get_logger('cache.operations')
    
    log_data = {
        'event_type': 'cache_operation',
        'operation': operation,
        'cache_key': key[:100] if key else None  # Truncate long keys
    }
    
    if hit is not None:
        log_data['cache_hit'] = hit
    if duration_ms is not None:
        log_data['duration_ms'] = round(duration_ms, 2)
    
    logger.debug("Cache operation", extra={'extra_fields': log_data})