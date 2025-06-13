import pytest
from unittest.mock import MagicMock
from backend.core.config import Settings
from sqlalchemy.orm import Session # Add this import

@pytest.fixture(scope="session")
def mock_settings():
    """
    Fixture to provide a mock Settings object for tests.
    """
    settings = MagicMock(spec=Settings)
    settings.openai_api_key = "mock_openai_key"
    settings.anthropic_api_key = "mock_anthropic_key"
    settings.google_api_key = "mock_google_key"
    settings.redis_url = "redis://localhost:6379/0"
    settings.celery_broker_url = "redis://localhost:6379/1"
    settings.celery_result_backend = "redis://localhost:6379/2"
    settings.minio_endpoint = "http://localhost:9000"
    settings.minio_access_key = "minioadmin"
    settings.minio_secret_key = "minioadmin"
    settings.minio_bucket_name = "smartchat-documents"
    settings.environment = "test"
    settings.log_level = "INFO"
    settings.embedding_api_timeout = 60 # Add this line
    return settings

# Mock SQLAlchemy Session
@pytest.fixture
def mock_db_session():
    def _create_mock_query_chain():
        mock_chain = MagicMock()
        mock_chain.filter.return_value = mock_chain
        mock_chain.order_by.return_value = mock_chain
        mock_chain.offset.return_value = mock_chain
        mock_chain.limit.return_value = mock_chain
        mock_chain.first.return_value = None
        mock_chain.count.return_value = 0
        mock_chain.all.return_value = []
        mock_chain.with_entities.return_value = mock_chain # Added for stats query
        return mock_chain

    mock_session = MagicMock(spec=Session)
    mock_session.query.return_value = _create_mock_query_chain()
    return mock_session

@pytest.fixture(autouse=True)
def override_settings_for_tests(mock_settings):
    """
    Fixture to override settings globally for tests, including backend.config.
    """
    # Patch backend.core.config.get_settings
    from backend.core import config as core_config
    original_core_get_settings = core_config.get_settings
    core_config.get_settings = lambda: mock_settings

    # Patch backend.config.settings (used by embedding_service)
    from backend import config as backend_config
    original_backend_settings = backend_config.settings
    backend_config.settings = mock_settings

    # Patch services.embedding_service.settings (if it imports directly from config)
    from backend.services import embedding_service
    original_embedding_service_settings = embedding_service.embedding_service.settings
    embedding_service.embedding_service.settings = mock_settings

    yield

    # Restore original settings after tests
    core_config.get_settings = original_core_get_settings
    backend_config.settings = original_backend_settings
    embedding_service.embedding_service.settings = original_embedding_service_settings