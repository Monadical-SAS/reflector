import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from reflector.db.jobs import JobStatus, JobType


@pytest.fixture(autouse=True)
def mock_auth():
    """Mock authentication for all tests"""
    from reflector.app import app
    from reflector.auth import current_user_optional
    
    app.dependency_overrides[current_user_optional] = lambda: {
        "sub": "test-user-123",
        "email": "test@example.com",
    }
    yield
    del app.dependency_overrides[current_user_optional]


@pytest.fixture(autouse=True)
def mock_url_validator():
    """Mock URL validator to allow test URLs"""
    with patch("reflector.worker.audio_tasks.validate_audio_url") as mock_validate:
        mock_validate.return_value = (True, None)
        yield mock_validate


@pytest.fixture(autouse=True)
def mock_ci_token():
    """Mock CI evaluation token verification"""
    from reflector.app import app
    from reflector.views.audio import verify_ci_evaluation_token
    
    app.dependency_overrides[verify_ci_evaluation_token] = lambda: True
    yield
    if verify_ci_evaluation_token in app.dependency_overrides:
        del app.dependency_overrides[verify_ci_evaluation_token]


@pytest.fixture
def client():
    """Create test client"""
    from reflector.app import app
    return TestClient(app)


@pytest.fixture
async def db_session():
    """Create database session for tests"""
    from reflector.db import database
    await database.connect()
    yield database
    await database.disconnect()


@pytest.fixture
def mock_celery_task():
    """Mock Celery task apply_async"""
    with patch("reflector.views.audio.process_audio_task") as mock_task:
        mock_apply = MagicMock()
        mock_task.apply_async = mock_apply
        yield mock_apply


@pytest.fixture
def mock_celery_diarization_task():
    """Mock Celery diarization task apply_async"""
    with patch("reflector.views.audio.process_audio_with_diarization_task") as mock_task:
        mock_apply = MagicMock()
        mock_task.apply_async = mock_apply
        yield mock_apply


class TestAudioProcessEndpoint:
    """Test /api/v1/audio/process endpoint"""
    
    @pytest.mark.asyncio
    async def test_process_audio_success(self, client: TestClient, mock_celery_task):
        """Test successful audio processing job creation"""
        request_data = {
            "audio_url": "https://example.com/audio.wav",
            "options": {
                "source_language": "en",
                "target_language": "es",
                "only_transcript": False,
                "enable_topics": True,
                "timeout_ms": 300000
            }
        }
        
        response = client.post("/api/v1/audio/process", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "job_id" in data
        assert data["status"] == "pending"
        assert "created_at" in data
        assert "estimated_completion" in data
        
        # Verify Celery task was called
        mock_celery_task.assert_called_once()
        call_args = mock_celery_task.call_args
        # apply_async is called with args=list and kwargs
        assert call_args.kwargs["args"][1] == request_data["audio_url"]
        assert call_args.kwargs["args"][2] == "en"
        assert call_args.kwargs["args"][3] == "es"
        assert call_args.kwargs["args"][4] == False  # only_transcript
        assert call_args.kwargs["args"][5] == True   # enable_topics
        assert call_args.kwargs["time_limit"] == 300  # 300000ms / 1000
    
    @pytest.mark.asyncio
    async def test_process_audio_default_options(self, client: TestClient, mock_celery_task):
        """Test audio processing with default options"""
        request_data = {
            "audio_url": "https://example.com/audio.wav"
        }
        
        response = client.post("/api/v1/audio/process", json=request_data)
        
        assert response.status_code == 200
        
        # Verify defaults were used
        call_args = mock_celery_task.call_args
        assert call_args.kwargs["args"][2] == "en"  # default source_language
        assert call_args.kwargs["args"][3] == "en"  # default target_language
        assert call_args.kwargs["args"][4] == True   # default only_transcript
        assert call_args.kwargs["args"][5] == False  # default enable_topics
    
    @pytest.mark.asyncio
    async def test_process_audio_invalid_url(self, client: TestClient):
        """Test with invalid audio URL"""
        request_data = {
            "audio_url": "not-a-valid-url"
        }
        
        response = client.post("/api/v1/audio/process", json=request_data)
        
        assert response.status_code == 422  # Validation error


class TestAudioProcessWithDiarizationEndpoint:
    """Test /api/v1/audio/process-with-diarization endpoint"""
    
    @pytest.mark.asyncio
    async def test_process_with_diarization_success(
        self, client: TestClient, mock_celery_diarization_task
    ):
        """Test successful audio processing with diarization"""
        request_data = {
            "audio_url": "https://example.com/audio.wav",
            "options": {
                "source_language": "en",
                "target_language": "en",
                "only_transcript": False,
                "diarization_backend": "modal",
                "timeout_ms": 600000
            }
        }
        
        response = client.post("/api/v1/audio/process-with-diarization", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "job_id" in data
        assert data["status"] == "pending"
        
        # Verify Celery task was called
        mock_celery_diarization_task.assert_called_once()
        call_args = mock_celery_diarization_task.call_args
        assert call_args.kwargs["args"][1] == request_data["audio_url"]
        assert call_args.kwargs["args"][5] == "modal"  # diarization_backend
        assert call_args.kwargs["time_limit"] == 600  # 600000ms / 1000


class TestJobStatusEndpoint:
    """Test /api/v1/jobs/{job_id}/status endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_job_status_pending(self, client: TestClient, db_session):
        """Test getting status of pending job"""
        # Create a test job
        job_id = uuid.uuid4()
        await db_session.execute(
            "INSERT INTO jobs (id, type, status, created_at, updated_at, request_data, metadata, user_id) "
            "VALUES (:id, :type, :status, :created_at, :updated_at, :request_data, :metadata, :user_id)",
            {
                "id": str(job_id),
                "type": JobType.AUDIO_PROCESS,
                "status": JobStatus.PENDING,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "request_data": json.dumps({}),  # Serialize for SQLite
                "metadata": json.dumps({}),  # Serialize for SQLite
                "user_id": "test-user-123",
            }
        )
        
        response = client.get(f"/api/v1/jobs/{job_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["job_id"] == str(job_id)
        assert data["status"] == "pending"
        assert data["progress"]["current_step"] is None
        assert data["error"] is None
    
    @pytest.mark.asyncio
    async def test_get_job_status_processing(self, client: TestClient, db_session):
        """Test getting status of processing job"""
        job_id = uuid.uuid4()
        await db_session.execute(
            "INSERT INTO jobs (id, type, status, current_step, progress_percentage, "
            "created_at, updated_at, request_data, metadata, user_id) "
            "VALUES (:id, :type, :status, :current_step, :progress_percentage, "
            ":created_at, :updated_at, :request_data, :metadata, :user_id)",
            {
                "id": str(job_id),
                "type": JobType.AUDIO_PROCESS,
                "status": JobStatus.PROCESSING,
                "current_step": "transcription",
                "progress_percentage": 30,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "request_data": json.dumps({}),  # Serialize for SQLite
                "metadata": json.dumps({}),  # Serialize for SQLite
                "user_id": "test-user-123",
            }
        )
        
        response = client.get(f"/api/v1/jobs/{job_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "processing"
        assert data["progress"]["current_step"] == "transcription"
        assert data["progress"]["percentage"] == 30
    
    @pytest.mark.asyncio
    async def test_get_job_status_failed(self, client: TestClient, db_session):
        """Test getting status of failed job"""
        job_id = uuid.uuid4()
        await db_session.execute(
            "INSERT INTO jobs (id, type, status, error_code, error_message, "
            "error_details, created_at, updated_at, request_data, metadata, user_id) "
            "VALUES (:id, :type, :status, :error_code, :error_message, "
            ":error_details, :created_at, :updated_at, :request_data, :metadata, :user_id)",
            {
                "id": str(job_id),
                "type": JobType.AUDIO_PROCESS,
                "status": JobStatus.FAILED,
                "error_code": "PROCESSING_ERROR",
                "error_message": "Failed to process audio",
                "error_details": json.dumps({"exception": "ValueError"}),  # Serialize for SQLite
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "request_data": json.dumps({}),  # Serialize for SQLite
                "metadata": json.dumps({}),  # Serialize for SQLite
                "user_id": "test-user-123",
            }
        )
        
        response = client.get(f"/api/v1/jobs/{job_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "failed"
        assert data["error"]["code"] == "PROCESSING_ERROR"
        assert data["error"]["message"] == "Failed to process audio"
        assert data["error"]["details"]["exception"] == "ValueError"
    
    @pytest.mark.asyncio
    async def test_get_job_status_not_found(self, client: TestClient):
        """Test getting status of non-existent job"""
        fake_id = uuid.uuid4()
        response = client.get(f"/api/v1/jobs/{fake_id}/status")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"]["code"] == "JOB_NOT_FOUND"


class TestJobResultsEndpoint:
    """Test /api/v1/jobs/{job_id}/results endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_job_results_success(self, client: TestClient, db_session):
        """Test getting results of completed job"""
        job_id = uuid.uuid4()
        result_data = [
            {
                "processor": "AudioTranscriptAutoProcessor",
                "uid": "abc123",
                "data": {
                    "words": [
                        {"text": "Hello", "start": 0.0, "end": 0.5},
                        {"text": "world", "start": 0.6, "end": 1.0}
                    ]
                }
            },
            {
                "processor": "TranscriptTranslatorProcessor",
                "uid": "def456",
                "data": {
                    "translation": {
                        "text": "Hola mundo",
                        "language": "es"
                    }
                }
            }
        ]
        
        await db_session.execute(
            "INSERT INTO jobs (id, type, status, result_data, completed_at, "
            "created_at, updated_at, request_data, metadata, user_id) "
            "VALUES (:id, :type, :status, :result_data, :completed_at, "
            ":created_at, :updated_at, :request_data, :metadata, :user_id)",
            {
                "id": str(job_id),
                "type": JobType.AUDIO_PROCESS,
                "status": JobStatus.COMPLETED,
                "result_data": json.dumps(result_data),  # Serialize for SQLite
                "completed_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "request_data": json.dumps({}),  # Serialize for SQLite
                "metadata": json.dumps({}),  # Serialize for SQLite
                "user_id": "test-user-123",
            }
        )
        
        response = client.get(f"/api/v1/jobs/{job_id}/results")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["job_id"] == str(job_id)
        assert len(data["results"]) == 2
        assert data["results"][0]["processor"] == "AudioTranscriptAutoProcessor"
        assert data["results"][1]["processor"] == "TranscriptTranslatorProcessor"
        assert data["metadata"]["processors_used"] == [
            "AudioTranscriptAutoProcessor",
            "TranscriptTranslatorProcessor"
        ]
    
    @pytest.mark.asyncio
    async def test_get_job_results_jsonl_format(self, client: TestClient, db_session):
        """Test getting results in JSONL format"""
        job_id = uuid.uuid4()
        result_data = [
            {
                "processor": "AudioTranscriptAutoProcessor",
                "uid": "abc123",
                "data": {"words": [{"text": "Test", "start": 0.0, "end": 0.5}]}
            }
        ]
        
        await db_session.execute(
            "INSERT INTO jobs (id, type, status, result_data, completed_at, "
            "created_at, updated_at, request_data, metadata, user_id) "
            "VALUES (:id, :type, :status, :result_data, :completed_at, "
            ":created_at, :updated_at, :request_data, :metadata, :user_id)",
            {
                "id": str(job_id),
                "type": JobType.AUDIO_PROCESS,
                "status": JobStatus.COMPLETED,
                "result_data": json.dumps(result_data),  # Serialize for SQLite
                "completed_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "request_data": json.dumps({}),  # Serialize for SQLite
                "metadata": json.dumps({}),  # Serialize for SQLite
                "user_id": "test-user-123",
            }
        )
        
        response = client.get(f"/api/v1/jobs/{job_id}/results?format=jsonl")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-ndjson"
        
        # Parse JSONL
        lines = response.text.strip().split("\n")
        assert len(lines) == 1
        
        import json as json_module
        first_line = json_module.loads(lines[0])
        assert first_line["processor"] == "AudioTranscriptAutoProcessor"
    
    @pytest.mark.asyncio
    async def test_get_job_results_not_completed(self, client: TestClient, db_session):
        """Test getting results of non-completed job"""
        job_id = uuid.uuid4()
        await db_session.execute(
            "INSERT INTO jobs (id, type, status, created_at, updated_at, request_data, metadata, user_id) "
            "VALUES (:id, :type, :status, :created_at, :updated_at, :request_data, :metadata, :user_id)",
            {
                "id": str(job_id),
                "type": JobType.AUDIO_PROCESS,
                "status": JobStatus.PROCESSING,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "request_data": json.dumps({}),  # Serialize for SQLite
                "metadata": json.dumps({}),  # Serialize for SQLite
                "user_id": "test-user-123",
            }
        )
        
        response = client.get(f"/api/v1/jobs/{job_id}/results")
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"]["code"] == "JOB_NOT_COMPLETED"


class TestHealthCheckEndpoint:
    """Test /api/v1/health endpoint"""
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, client: TestClient):
        """Test successful health check"""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert data["version"] == "1.0.0"
        assert "services" in data
        assert "database" in data["services"]
        assert "transcription" in data["services"]
        assert "diarization" in data["services"]
        assert "translation" in data["services"]
    
    @pytest.mark.asyncio
    async def test_health_check_db_failure(self, client: TestClient):
        """Test health check when database is down"""
        with patch("reflector.db.database.execute", side_effect=Exception("DB Error")):
            response = client.get("/api/v1/health")
            
            # Should still return a response, but with degraded/unhealthy status
            assert response.status_code in [200, 503]
            data = response.json()
            
            if response.status_code == 200:
                # Normal health check response
                assert data["status"] in ["degraded", "unhealthy"]
                assert data["services"]["database"] == "unavailable"
            else:
                # Error response when service is completely down
                assert response.status_code == 503
                # Error response format will have error field, not services