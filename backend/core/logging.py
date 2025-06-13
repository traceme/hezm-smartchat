import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import json
from logging.handlers import RotatingFileHandler
from backend.core.config import get_settings

class SmartChatLogger:
    """Centralized logging configuration for SmartChat application"""
    
    def __init__(self):
        self.settings = get_settings()
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # Create different loggers for different components
        self.app_logger = self._setup_logger("smartchat.app", "app.log")
        self.api_logger = self._setup_logger("smartchat.api", "api.log")
        self.error_logger = self._setup_logger("smartchat.error", "error.log", level=logging.ERROR)
        self.debug_logger = self._setup_logger("smartchat.debug", "debug.log", level=logging.DEBUG)
        
        # Setup a logger for the entire 'backend' module to capture all internal logs
        self.backend_logger = self._setup_logger("backend", "backend.log", level=logging.DEBUG)
    
    def _setup_logger(self, name: str, filename: str, level: int = logging.INFO) -> logging.Logger:
        """Setup a logger with file rotation and console output"""
        logger = logging.getLogger(name)
        
        # Avoid duplicate handlers if logger already exists
        if logger.handlers:
            return logger
            
        logger.setLevel(logging.DEBUG if self.settings.debug else level)
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            fmt='%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # File handler with rotation (10MB per file, keep 5 backup files)
        file_handler = RotatingFileHandler(
            self.log_dir / filename,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(detailed_formatter)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG) # Set to DEBUG to capture all levels
        console_handler.setFormatter(detailed_formatter) # Use detailed formatter for console
        logger.addHandler(console_handler)
        
        logger.addHandler(file_handler)
        
        # Prevent propagation to root logger
        logger.propagate = False
        
        return logger
    
    def log_api_request(self, method: str, path: str, status_code: int, 
                       duration_ms: float, user_id: Optional[int] = None,
                       request_id: Optional[str] = None):
        """Log API request details"""
        log_data = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "user_id": user_id,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if status_code >= 400:
            self.api_logger.warning(f"API Request: {json.dumps(log_data)}")
        else:
            self.api_logger.info(f"API Request: {json.dumps(log_data)}")
    
    def log_error(self, error: Exception, context: Optional[dict] = None,
                  request_id: Optional[str] = None):
        """Log error with context information"""
        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {},
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.error_logger.error(f"Error: {json.dumps(error_data)}", exc_info=True)
    
    def log_document_processing(self, document_id: int, filename: str, 
                              status: str, processing_time: Optional[float] = None,
                              error: Optional[str] = None):
        """Log document processing events"""
        log_data = {
            "document_id": document_id,
            "filename": filename,
            "status": status,
            "processing_time_ms": round(processing_time, 2) if processing_time else None,
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if error:
            self.app_logger.error(f"Document Processing: {json.dumps(log_data)}")
        else:
            self.app_logger.info(f"Document Processing: {json.dumps(log_data)}")
    
    def log_search_query(self, query: str, document_id: Optional[int] = None,
                        results_count: int = 0, duration_ms: float = 0,
                        user_id: Optional[int] = None):
        """Log search query events"""
        log_data = {
            "query": query[:100] + "..." if len(query) > 100 else query,  # Truncate long queries
            "document_id": document_id,
            "results_count": results_count,
            "duration_ms": round(duration_ms, 2),
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.app_logger.info(f"Search Query: {json.dumps(log_data)}")
    
    def log_ai_interaction(self, model: str, prompt_tokens: int, 
                          completion_tokens: int, duration_ms: float,
                          user_id: Optional[int] = None, error: Optional[str] = None):
        """Log AI model interactions"""
        log_data = {
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "duration_ms": round(duration_ms, 2),
            "user_id": user_id,
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if error:
            self.app_logger.error(f"AI Interaction: {json.dumps(log_data)}")
        else:
            self.app_logger.info(f"AI Interaction: {json.dumps(log_data)}")


# Global logger instance
smartchat_logger = SmartChatLogger()

# Convenience functions for easy access
def get_app_logger() -> logging.Logger:
    return smartchat_logger.app_logger

def get_api_logger() -> logging.Logger:
    return smartchat_logger.api_logger

def get_error_logger() -> logging.Logger:
    return smartchat_logger.error_logger

def get_debug_logger() -> logging.Logger:
    return smartchat_logger.debug_logger

def log_api_request(*args, **kwargs):
    return smartchat_logger.log_api_request(*args, **kwargs)

def log_error(*args, **kwargs):
    return smartchat_logger.log_error(*args, **kwargs)

def log_document_processing(*args, **kwargs):
    return smartchat_logger.log_document_processing(*args, **kwargs)

def log_search_query(*args, **kwargs):
    return smartchat_logger.log_search_query(*args, **kwargs)

def log_ai_interaction(*args, **kwargs):
    return smartchat_logger.log_ai_interaction(*args, **kwargs) 