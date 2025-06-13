from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Base error detail model"""
    field: str = Field(..., description="The field that caused the error")
    message: str = Field(..., description="Error message for the field")
    type: str = Field(..., description="Type of validation error")


class ValidationErrorDetail(BaseModel):
    """Validation error details"""
    validation_errors: List[ErrorDetail] = Field(..., description="List of validation errors")


class DocumentErrorDetail(BaseModel):
    """Document-specific error details"""
    document_id: Optional[int] = Field(None, description="Document ID if applicable")
    filename: Optional[str] = Field(None, description="Filename if applicable")
    error: Optional[str] = Field(None, description="Specific error message")


class SearchErrorDetail(BaseModel):
    """Search-specific error details"""
    query: str = Field(..., description="The search query that failed")
    error: str = Field(..., description="Specific search error")


class AIServiceErrorDetail(BaseModel):
    """AI service error details"""
    model: str = Field(..., description="AI model that encountered the error")
    error: str = Field(..., description="Specific AI service error")


class UploadErrorDetail(BaseModel):
    """Upload-specific error details"""
    filename: str = Field(..., description="File that failed to upload")
    error: str = Field(..., description="Specific upload error")


class ConfigurationErrorDetail(BaseModel):
    """Configuration error details"""
    setting: str = Field(..., description="Configuration setting that is invalid")
    error: str = Field(..., description="Specific configuration error")


class BaseErrorResponse(BaseModel):
    """Base error response model"""
    code: str = Field(..., description="Error code identifying the type of error")
    message: str = Field(..., description="Human-readable error message")
    request_id: Optional[str] = Field(None, description="Unique request identifier for debugging")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class ErrorResponse(BaseModel):
    """Standard error response wrapper"""
    error: BaseErrorResponse = Field(..., description="Error information")

    class Config:
        json_schema_extra = {
            "example": {
                "error": {
                    "code": "DOCUMENT_NOT_FOUND",
                    "message": "Document with ID 123 not found",
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                    "details": {
                        "document_id": 123
                    }
                }
            }
        }


# Specific error response models for different scenarios
class DocumentNotFoundResponse(BaseModel):
    """Response for document not found errors"""
    error: BaseErrorResponse = Field(
        ...,
        description="Document not found error",
        example={
            "code": "DOCUMENT_NOT_FOUND",
            "message": "Document with ID 123 not found",
            "request_id": "550e8400-e29b-41d4-a716-446655440000",
            "details": {"document_id": 123}
        }
    )


class ValidationErrorResponse(BaseModel):
    """Response for validation errors"""
    error: BaseErrorResponse = Field(
        ...,
        description="Validation error",
        example={
            "code": "VALIDATION_ERROR",
            "message": "Invalid input data provided.",
            "request_id": "550e8400-e29b-41d4-a716-446655440000",
            "details": {
                "validation_errors": [
                    {
                        "field": "email",
                        "message": "field required",
                        "type": "value_error.missing"
                    }
                ]
            }
        }
    )


class DocumentProcessingErrorResponse(BaseModel):
    """Response for document processing errors"""
    error: BaseErrorResponse = Field(
        ...,
        description="Document processing error",
        example={
            "code": "DOCUMENT_PROCESSING_ERROR",
            "message": "Failed to process document 'example.pdf': Invalid PDF format",
            "request_id": "550e8400-e29b-41d4-a716-446655440000",
            "details": {
                "filename": "example.pdf",
                "error": "Invalid PDF format"
            }
        }
    )


class SearchErrorResponse(BaseModel):
    """Response for search errors"""
    error: BaseErrorResponse = Field(
        ...,
        description="Search error",
        example={
            "code": "SEARCH_ERROR",
            "message": "Search failed for query 'machine learning': Vector database connection failed",
            "request_id": "550e8400-e29b-41d4-a716-446655440000",
            "details": {
                "query": "machine learning",
                "error": "Vector database connection failed"
            }
        }
    )


class AIServiceErrorResponse(BaseModel):
    """Response for AI service errors"""
    error: BaseErrorResponse = Field(
        ...,
        description="AI service error",
        example={
            "code": "AI_SERVICE_ERROR",
            "message": "AI service error with model 'gpt-4o': Rate limit exceeded",
            "request_id": "550e8400-e29b-41d4-a716-446655440000",
            "details": {
                "model": "gpt-4o",
                "error": "Rate limit exceeded"
            }
        }
    )


class UploadErrorResponse(BaseModel):
    """Response for upload errors"""
    error: BaseErrorResponse = Field(
        ...,
        description="Upload error",
        example={
            "code": "UPLOAD_ERROR",
            "message": "Upload failed for file 'document.pdf': File size exceeds maximum limit",
            "request_id": "550e8400-e29b-41d4-a716-446655440000",
            "details": {
                "filename": "document.pdf",
                "error": "File size exceeds maximum limit"
            }
        }
    )


class InternalServerErrorResponse(BaseModel):
    """Response for internal server errors"""
    error: BaseErrorResponse = Field(
        ...,
        description="Internal server error",
        example={
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred. Please try again later.",
            "request_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    )


class BadRequestErrorResponse(BaseModel):
    """Response for bad request errors"""
    error: BaseErrorResponse = Field(
        ...,
        description="Bad request error",
        example={
            "code": "HTTP_400",
            "message": "Bad request. Please check your input.",
            "request_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    )


class UnauthorizedErrorResponse(BaseModel):
    """Response for unauthorized errors"""
    error: BaseErrorResponse = Field(
        ...,
        description="Unauthorized error",
        example={
            "code": "HTTP_401",
            "message": "Authentication required.",
            "request_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    )


class ForbiddenErrorResponse(BaseModel):
    """Response for forbidden errors"""
    error: BaseErrorResponse = Field(
        ...,
        description="Forbidden error",
        example={
            "code": "HTTP_403",
            "message": "Access denied.",
            "request_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    )


class ServiceUnavailableErrorResponse(BaseModel):
    """Response for service unavailable errors"""
    error: BaseErrorResponse = Field(
        ...,
        description="Service unavailable error",
        example={
            "code": "HTTP_503",
            "message": "Service temporarily unavailable.",
            "request_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    )


# Common HTTP error status responses for OpenAPI documentation
ERROR_RESPONSES = {
    400: {"model": BadRequestErrorResponse, "description": "Bad Request"},
    401: {"model": UnauthorizedErrorResponse, "description": "Unauthorized"},
    403: {"model": ForbiddenErrorResponse, "description": "Forbidden"},
    404: {"model": DocumentNotFoundResponse, "description": "Not Found"},
    422: {"model": ValidationErrorResponse, "description": "Validation Error"},
    500: {"model": InternalServerErrorResponse, "description": "Internal Server Error"},
    503: {"model": ServiceUnavailableErrorResponse, "description": "Service Unavailable"},
}


# Convenience function to add error responses to endpoint documentation
def add_error_responses(*status_codes: int) -> Dict[int, Dict[str, Any]]:
    """Add error responses to FastAPI endpoint documentation"""
    return {code: ERROR_RESPONSES[code] for code in status_codes if code in ERROR_RESPONSES} 