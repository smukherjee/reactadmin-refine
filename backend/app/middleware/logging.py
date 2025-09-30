"""
Request/Response logging middleware with timing and structured logging.

This middleware provides comprehensive request/response logging with:
- Request correlation IDs
- Timing measurements
- Request/response body logging (configurable)
- Error tracking and stack traces
- User and tenant context
"""

import time
import json
from typing import Callable, Optional, Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
import logging

from backend.app.core.logging import (
    RequestLogger, generate_request_id, set_request_context, 
    clear_request_context, get_logger
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive request/response logging with timings.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        log_request_body: bool = False,
        log_response_body: bool = False,
        max_body_size: int = 1024,  # Maximum body size to log (bytes)
        skip_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.max_body_size = max_body_size
        self.skip_paths = skip_paths or ['/health', '/metrics', '/liveness', '/readiness']
        self.logger = get_logger('api.middleware')
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for certain paths (health checks, etc.)
        if request.url.path in self.skip_paths:
            return await call_next(request)
        
        # Generate request ID and set context
        request_id = generate_request_id()
        start_time = time.time()
        
        # Extract user context from request if available
        user_id = ''
        tenant_id = ''
        
        # Try to extract user info from JWT token or session
        try:
            if hasattr(request.state, 'user'):
                user_id = str(getattr(request.state.user, 'id', ''))
                tenant_id = str(getattr(request.state.user, 'tenant_id', ''))
            elif hasattr(request.state, 'current_user'):
                user_id = str(getattr(request.state.current_user, 'id', ''))
                tenant_id = str(getattr(request.state.current_user, 'tenant_id', ''))
        except Exception:
            pass  # Ignore errors in user extraction
        
        # Set request context for all subsequent logging
        set_request_context(request_id, user_id, tenant_id)
        
        # Add request ID to request state for access in endpoints
        request.state.request_id = request_id
        
        try:
            # Log request details
            await self._log_request(request)
            
            # Process request
            response = await call_next(request)
            
            # Calculate timing
            process_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Log response details
            await self._log_response(response, process_time)
            
            # Add timing header to response
            response.headers["X-Process-Time"] = str(round(process_time, 2))
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Log error
            process_time = (time.time() - start_time) * 1000
            await self._log_error(e, process_time)
            raise
            
        finally:
            # Clear request context
            clear_request_context()
    
    async def _log_request(self, request: Request):
        """Log incoming request details."""
        try:
            # Get client IP (handle proxy headers)
            client_ip = self._get_client_ip(request)
            
            # Get request size
            body_size = None
            request_body = None
            
            if self.log_request_body and request.method in ['POST', 'PUT', 'PATCH']:
                try:
                    body = await request.body()
                    body_size = len(body)
                    
                    if body_size > 0 and body_size <= self.max_body_size:
                        try:
                            # Try to parse as JSON for better logging
                            request_body = json.loads(body.decode('utf-8'))
                            # Remove sensitive fields
                            if isinstance(request_body, dict):
                                request_body = self._sanitize_data(request_body)
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            request_body = f"<binary data: {body_size} bytes>"
                            
                    # Re-create request body for downstream processing
                    async def receive():
                        return {"type": "http.request", "body": body}
                    request._receive = receive
                    
                except Exception as e:
                    self.logger.warning(f"Failed to read request body: {e}")
            
            # Prepare query parameters (sanitize)
            query_params = dict(request.query_params) if request.query_params else None
            if query_params:
                query_params = self._sanitize_data(query_params)
            
            # Log the request
            RequestLogger.log_request(
                method=request.method,
                path=request.url.path,
                query_params=query_params,
                headers=dict(request.headers),
                body_size=body_size,
                client_ip=client_ip,
                user_agent=request.headers.get('user-agent')
            )
            
            # Log request body if enabled
            if request_body is not None:
                self.logger.debug("Request body", extra={
                    'extra_fields': {
                        'event_type': 'request_body',
                        'body': request_body
                    }
                })
                
        except Exception as e:
            self.logger.error(f"Failed to log request: {e}")
    
    async def _log_response(self, response: Response, process_time: float):
        """Log response details with timing."""
        try:
            response_size = None
            response_body = None
            
            if self.log_response_body and hasattr(response, 'body'):
                try:
                    body = response.body
                    if body:
                        response_size = len(body)
                        
                        if response_size <= self.max_body_size:
                            try:
                                # Try to parse as JSON
                                if response.media_type == 'application/json':
                                    if isinstance(body, bytes):
                                        body_str = body.decode('utf-8')
                                    else:
                                        body_str = str(body)
                                    response_body = json.loads(body_str)
                                    response_body = self._sanitize_data(response_body)
                                else:
                                    response_body = f"<{response.media_type}: {response_size} bytes>"
                            except (json.JSONDecodeError, UnicodeDecodeError):
                                response_body = f"<binary data: {response_size} bytes>"
                                
                except Exception as e:
                    self.logger.warning(f"Failed to read response body: {e}")
            
            # Log the response
            RequestLogger.log_response(
                status_code=response.status_code,
                response_time_ms=process_time,
                response_size=response_size
            )
            
            # Log response body if enabled
            if response_body is not None:
                self.logger.debug("Response body", extra={
                    'extra_fields': {
                        'event_type': 'response_body',
                        'body': response_body
                    }
                })
                
        except Exception as e:
            self.logger.error(f"Failed to log response: {e}")
    
    async def _log_error(self, error: Exception, process_time: float):
        """Log error details."""
        try:
            import traceback
            
            error_details = {
                'event_type': 'request_error',
                'error_type': type(error).__name__,
                'error_message': str(error),
                'process_time_ms': round(process_time, 2),
                'stack_trace': traceback.format_exc()
            }
            
            self.logger.error("Request processing error", extra={'extra_fields': error_details})
            
        except Exception as e:
            self.logger.error(f"Failed to log error: {e}")
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, handling proxy headers."""
        # Check for proxy headers (in order of preference)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            # Take the first IP in case of multiple proxies
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        return request.client.host if request.client else 'unknown'
    
    def _sanitize_data(self, data: Any) -> Any:
        """
        Remove sensitive data from logs.
        """
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                key_lower = key.lower()
                if any(sensitive in key_lower for sensitive in [
                    'password', 'token', 'secret', 'key', 'authorization',
                    'cookie', 'session', 'csrf', 'api_key', 'auth',
                    'credential', 'private'
                ]):
                    sanitized[key] = '<redacted>'
                elif isinstance(value, (dict, list)):
                    sanitized[key] = self._sanitize_data(value)
                else:
                    sanitized[key] = value
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        else:
            return data


class PerformanceLoggingMiddleware(BaseHTTPMiddleware):
    """
    Lightweight middleware for performance monitoring.
    """
    
    def __init__(self, app: ASGIApp, slow_request_threshold: float = 1000.0):
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold  # milliseconds
        self.logger = get_logger('api.performance')
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Log slow requests
        if process_time > self.slow_request_threshold:
            self.logger.warning("Slow request detected", extra={
                'extra_fields': {
                    'event_type': 'slow_request',
                    'method': request.method,
                    'path': request.url.path,
                    'response_time_ms': round(process_time, 2),
                    'status_code': response.status_code,
                    'threshold_ms': self.slow_request_threshold
                }
            })
        
        return response