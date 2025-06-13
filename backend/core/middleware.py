import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from backend.core.logging import log_api_request, log_error


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all API requests with timing and unique request IDs"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Add request ID to request headers for downstream use
        request.headers.__dict__["_list"].append((b"x-request-id", request_id.encode()))
        
        # Record start time
        start_time = time.time()
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Extract user ID if available (you can modify this based on your auth implementation)
            user_id = getattr(request.state, 'user_id', None)
            
            # Log the request
            log_api_request(
                method=request.method,
                path=str(request.url.path),
                status_code=response.status_code,
                duration_ms=duration_ms,
                user_id=user_id,
                request_id=request_id
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as exc:
            # Calculate duration for failed requests
            duration_ms = (time.time() - start_time) * 1000
            
            # Log the error
            log_error(
                error=exc,
                context={
                    "method": request.method,
                    "path": str(request.url.path),
                    "duration_ms": duration_ms
                },
                request_id=request_id
            )
            
            # Log the failed request
            log_api_request(
                method=request.method,
                path=str(request.url.path),
                status_code=500,
                duration_ms=duration_ms,
                request_id=request_id
            )
            
            # Re-raise the exception to be handled by exception handlers
            raise exc


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware to handle uncaught exceptions gracefully"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            # Get request ID if available
            request_id = getattr(request.state, 'request_id', None)
            
            # Log the error with context and traceback
            import traceback
            full_traceback = traceback.format_exc()
            log_error(
                error=exc,
                context={
                    "method": request.method,
                    "path": str(request.url.path),
                    "query_params": str(request.query_params),
                    "client_ip": request.client.host if request.client else None,
                    "traceback": full_traceback # Add traceback to context
                },
                request_id=request_id
            )
            
            # Return a generic error response
            error_response = {
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Please try again later.",
                    "request_id": request_id
                }
            }
            
            response = JSONResponse(
                status_code=500,
                content=error_response
            )
            
            if request_id:
                response.headers["X-Request-ID"] = request_id
                
            return response 