from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from backend.core.logging import log_error


class SmartChatException(Exception):
    """Base exception class for SmartChat application"""
    def __init__(self, message: str, code: str = "SMARTCHAT_ERROR", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class DocumentNotFoundException(SmartChatException):
    """Raised when a document is not found"""
    def __init__(self, document_id: int):
        super().__init__(
            message=f"Document with ID {document_id} not found",
            code="DOCUMENT_NOT_FOUND",
            details={"document_id": document_id}
        )


class DocumentProcessingException(SmartChatException):
    """Raised when document processing fails"""
    def __init__(self, filename: str, error: str):
        super().__init__(
            message=f"Failed to process document '{filename}': {error}",
            code="DOCUMENT_PROCESSING_ERROR",
            details={"filename": filename, "error": error}
        )


class SearchException(SmartChatException):
    """Raised when search operations fail"""
    def __init__(self, query: str, error: str):
        super().__init__(
            message=f"Search failed for query '{query}': {error}",
            code="SEARCH_ERROR",
            details={"query": query, "error": error}
        )


class AIServiceException(SmartChatException):
    """Raised when AI service operations fail"""
    def __init__(self, model: str, error: str):
        super().__init__(
            message=f"AI service error with model '{model}': {error}",
            code="AI_SERVICE_ERROR",
            details={"model": model, "error": error}
        )


class UploadException(SmartChatException):
    """Raised when file upload operations fail"""
    def __init__(self, filename: str, error: str):
        super().__init__(
            message=f"Upload failed for file '{filename}': {error}",
            code="UPLOAD_ERROR",
            details={"filename": filename, "error": error}
        )


class ValidationException(SmartChatException):
    """Raised when validation fails"""
    def __init__(self, field: str, value: str, error: str):
        super().__init__(
            message=f"Validation failed for field '{field}': {error}",
            code="VALIDATION_ERROR",
            details={"field": field, "value": value, "error": error}
        )


class ConfigurationException(SmartChatException):
    """Raised when configuration is invalid"""
    def __init__(self, setting: str, error: str):
        super().__init__(
            message=f"Configuration error for '{setting}': {error}",
            code="CONFIGURATION_ERROR",
            details={"setting": setting, "error": error}
        )


def create_error_response(
    request: Request,
    code: str,
    message: str,
    status_code: int = 500,
    details: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """Create a standardized error response"""
    request_id = getattr(request.state, 'request_id', None)
    
    error_response = {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id
        }
    }
    
    if details:
        error_response["error"]["details"] = details
    
    response = JSONResponse(
        status_code=status_code,
        content=error_response
    )
    
    if request_id:
        response.headers["X-Request-ID"] = request_id
    
    return response


# Exception handlers
async def smartchat_exception_handler(request: Request, exc: SmartChatException) -> JSONResponse:
    """Handle SmartChat custom exceptions"""
    # Determine status code based on exception type
    status_code = 500
    if isinstance(exc, DocumentNotFoundException):
        status_code = 404
    elif isinstance(exc, ValidationException):
        status_code = 422
    elif isinstance(exc, (UploadException, DocumentProcessingException)):
        status_code = 400
    elif isinstance(exc, (SearchException, AIServiceException)):
        status_code = 503
    elif isinstance(exc, ConfigurationException):
        status_code = 500
    
    # Log the error
    log_error(
        error=exc,
        context={
            "exception_type": type(exc).__name__,
            "error_code": exc.code,
            "details": exc.details
        },
        request_id=getattr(request.state, 'request_id', None)
    )
    
    return create_error_response(
        request=request,
        code=exc.code,
        message=exc.message,
        status_code=status_code,
        details=exc.details
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions"""
    # Log the error
    log_error(
        error=exc,
        context={
            "status_code": exc.status_code,
            "detail": exc.detail
        },
        request_id=getattr(request.state, 'request_id', None)
    )
    
    # Map common HTTP status codes to user-friendly messages
    message_mapping = {
        400: "Bad request. Please check your input.",
        401: "Authentication required.",
        403: "Access denied.",
        404: "The requested resource was not found.",
        405: "Method not allowed.",
        409: "Conflict with current state of the resource.",
        422: "Invalid input data.",
        429: "Too many requests. Please try again later.",
        500: "Internal server error. Please try again later.",
        502: "Service temporarily unavailable.",
        503: "Service temporarily unavailable.",
        504: "Request timeout. Please try again."
    }
    
    message = message_mapping.get(exc.status_code, str(exc.detail))
    code = f"HTTP_{exc.status_code}"
    
    return create_error_response(
        request=request,
        code=code,
        message=message,
        status_code=exc.status_code,
        details={"original_detail": exc.detail} if exc.detail != message else None
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors"""
    # Log the error
    log_error(
        error=exc,
        context={
            "validation_errors": exc.errors()
        },
        request_id=getattr(request.state, 'request_id', None)
    )
    
    # Format validation errors for user
    formatted_errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        formatted_errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"]
        })
    
    return create_error_response(
        request=request,
        code="VALIDATION_ERROR",
        message="Invalid input data provided.",
        status_code=422,
        details={"validation_errors": formatted_errors}
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other unhandled exceptions"""
    # Log the error with full traceback
    log_error(
        error=exc,
        context={
            "exception_type": type(exc).__name__,
            "method": request.method,
            "path": str(request.url.path),
            "query_params": str(request.query_params)
        },
        request_id=getattr(request.state, 'request_id', None)
    )
    
    return create_error_response(
        request=request,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred. Please try again later.",
        status_code=500
    ) 