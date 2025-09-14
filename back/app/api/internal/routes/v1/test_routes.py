"""
Test endpoints for all services in the application.
These endpoints help verify that all components are working correctly.
"""

# Standard library imports
from datetime import datetime

# Third-party imports
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel
import redis.asyncio as redis
from sqlalchemy import text

# Optional imports - will be enabled after container rebuild
try:
    # Third-party imports
    from minio import Minio

    HAS_MINIO = True
except ImportError:
    HAS_MINIO = False

try:
    # Third-party imports
    import aiosmtplib

    HAS_SMTP = True
except ImportError:
    HAS_SMTP = False

try:
    # Local application imports
    from app.tasks.celery_app import celery_app, test_celery

    HAS_CELERY = True
except ImportError:
    HAS_CELERY = False
    celery_app = None
    test_celery = None

# Standard library imports
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Local application imports
from app.core.db import get_async_session
from app.settings import settings

router = APIRouter(prefix="/test", tags=["Service Tests"])


class CeleryTestRequest(BaseModel):
    message: str = "Hello from API"
    delay: int = 0  # Delay in seconds


class EmailTestRequest(BaseModel):
    to_email: str
    subject: str = "Test Email from FastAPI"
    body: str = "This is a test email sent from the FastAPI application."


# ============= Database Test =============
@router.get("/database")
async def test_database():
    """Test PostgreSQL database connection and basic operations."""
    try:
        db_session_generator = get_async_session()
        async for db in db_session_generator:
            # Test connection
            result = await db.execute(text("SELECT version()"))
            version = result.scalar()

            # Test table count
            tables_result = await db.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                """
                )
            )
            table_count = tables_result.scalar()

            return {
                "status": "success",
                "service": "PostgreSQL",
                "connection": "established",
                "version": version,
                "tables_count": table_count,
                "database": settings.POSTGRES_DB,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# ============= Redis Test =============
@router.get("/redis")
async def test_redis():
    """Test Redis connection and basic operations."""
    try:
        # Connect to Redis
        redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

        # Test ping
        await redis_client.ping()

        # Test set/get
        test_key = f"test_key_{datetime.now().isoformat()}"
        test_value = "FastAPI Redis Test"

        await redis_client.setex(test_key, 60, test_value)
        retrieved_value = await redis_client.get(test_key)

        # Get info
        info = await redis_client.info()

        # Clean up
        await redis_client.delete(test_key)
        await redis_client.close()

        return {
            "status": "success",
            "service": "Redis",
            "connection": "established",
            "test_write": "success",
            "test_read": retrieved_value == test_value,
            "version": info.get("redis_version", "unknown"),
            "used_memory": info.get("used_memory_human", "unknown"),
            "connected_clients": info.get("connected_clients", 0),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis error: {str(e)}")


# ============= Celery Worker Test =============
@router.post("/celery/worker")
async def test_celery_worker(request: CeleryTestRequest):
    """Test Celery worker by sending a task."""
    if not HAS_CELERY:
        return {
            "status": "warning",
            "service": "Celery Worker",
            "error": "celery package not installed. Rebuild container to enable.",
            "flower_url": "http://localhost:5555",
            "note": "Celery tasks require celery package to be installed",
        }
    try:
        # Send task to Celery
        if request.delay > 0:
            # Test with delay
            result = test_celery.apply_async(args=[request.message], countdown=request.delay)
        else:
            # Test immediate execution
            result = test_celery.delay(request.message)

        # Wait for result (with timeout)
        try:
            task_result = result.get(timeout=10)
        except Exception as timeout_err:
            task_result = f"Task queued but timed out: {timeout_err}"

        return {
            "status": "success",
            "service": "Celery Worker",
            "task_id": result.id,
            "task_status": result.status,
            "task_result": task_result,
            "message_sent": request.message,
            "delay_seconds": request.delay,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Celery worker error: {str(e)}")


# ============= Celery Beat Test =============
@router.get("/celery/beat")
async def test_celery_beat():
    """Check Celery Beat scheduler status."""
    if not HAS_CELERY:
        return {
            "status": "warning",
            "service": "Celery Beat",
            "error": "celery package not installed. Rebuild container to enable.",
            "flower_url": "http://localhost:5555",
            "note": "Celery Beat scheduler requires celery package to be installed",
        }
    try:
        # Get scheduled tasks from Celery
        inspect = celery_app.control.inspect()
        scheduled = inspect.scheduled()
        active = inspect.active()
        stats = inspect.stats()

        return {
            "status": "success",
            "service": "Celery Beat",
            "scheduled_tasks": scheduled or {},
            "active_tasks": active or {},
            "worker_stats": stats or {},
            "beat_schedule": dict(celery_app.conf.beat_schedule) if hasattr(celery_app.conf, "beat_schedule") else {},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Celery beat error: {str(e)}")


# ============= Flower Test =============
@router.get("/flower")
async def test_flower():
    """Check Flower monitoring status."""
    try:
        # Third-party imports
        import httpx

        async with httpx.AsyncClient() as client:
            # Check Flower API
            response = await client.get("http://flower:5555/api/workers")
            workers = response.json() if response.status_code == 200 else {}

            # Get tasks
            tasks_response = await client.get("http://flower:5555/api/tasks")
            tasks = tasks_response.json() if tasks_response.status_code == 200 else {}

            return {
                "status": "success",
                "service": "Flower",
                "monitoring_url": "http://localhost:5555",
                "workers_count": len(workers),
                "workers": list(workers.keys()) if workers else [],
                "total_tasks": len(tasks),
                "flower_accessible": response.status_code == 200,
            }
    except Exception as e:
        return {
            "status": "warning",
            "service": "Flower",
            "monitoring_url": "http://localhost:5555",
            "note": "Access Flower directly at http://localhost:5555",
            "error": str(e),
        }


# ============= MinIO Test =============
@router.post("/minio/upload")
async def test_minio_upload(file: UploadFile = File(...)):
    """Test MinIO S3 storage by uploading a file."""
    if not HAS_MINIO:
        return {
            "status": "warning",
            "service": "MinIO",
            "error": "minio package not installed. Rebuild container to enable.",
            "console_url": "http://localhost:9001",
            "credentials": {"username": "minioadmin", "password": "minioadmin"},
        }
    try:
        # Initialize MinIO client
        client = Minio(
            settings.S3_URL.replace("http://", "").replace("https://", ""),
            access_key=settings.S3_ACCESS_KEY_ID,
            secret_key=settings.S3_SECRET_ACCESS_KEY,
            secure=False,
        )

        # Check if bucket exists, create if not
        bucket_name = settings.S3_PUBLIC_BUCKET_NAME
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)

        # Upload file
        file_name = f"test/{datetime.now().isoformat()}_{file.filename}"
        file_data = await file.read()

        # Standard library imports
        from io import BytesIO

        client.put_object(
            bucket_name,
            file_name,
            BytesIO(file_data),
            len(file_data),
            content_type=file.content_type,
        )

        # Generate presigned URL
        url = client.presigned_get_object(bucket_name, file_name)

        return {
            "status": "success",
            "service": "MinIO",
            "bucket": bucket_name,
            "file_name": file_name,
            "file_size": len(file_data),
            "presigned_url": url,
            "console_url": "http://localhost:9001",
            "credentials": {"username": "minioadmin", "password": "minioadmin"},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MinIO error: {str(e)}")


@router.get("/minio/buckets")
async def test_minio_list_buckets():
    """List all MinIO buckets."""
    if not HAS_MINIO:
        return {
            "status": "warning",
            "service": "MinIO",
            "error": "minio package not installed. Rebuild container to enable.",
            "console_url": "http://localhost:9001",
            "credentials": {"username": "minioadmin", "password": "minioadmin"},
        }
    try:
        # Initialize MinIO client
        client = Minio(
            settings.S3_URL.replace("http://", "").replace("https://", ""),
            access_key=settings.S3_ACCESS_KEY_ID,
            secret_key=settings.S3_SECRET_ACCESS_KEY,
            secure=False,
        )

        # List buckets
        buckets = client.list_buckets()

        bucket_info = []
        for bucket in buckets:
            # Try to get object count for each bucket
            try:
                objects = list(client.list_objects(bucket.name, recursive=True))
                bucket_info.append(
                    {
                        "name": bucket.name,
                        "creation_date": bucket.creation_date.isoformat(),
                        "object_count": len(objects),
                    }
                )
            except Exception:
                bucket_info.append(
                    {
                        "name": bucket.name,
                        "creation_date": bucket.creation_date.isoformat(),
                        "object_count": "N/A",
                    }
                )

        return {
            "status": "success",
            "service": "MinIO",
            "total_buckets": len(buckets),
            "buckets": bucket_info,
            "console_url": "http://localhost:9001",
            "credentials": {"username": "minioadmin", "password": "minioadmin"},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MinIO error: {str(e)}")


# ============= Mailpit Test =============
@router.post("/mailpit/send")
async def test_mailpit_send(request: EmailTestRequest):
    """Test Mailpit email service by sending a test email."""
    if not HAS_SMTP:
        return {
            "status": "warning",
            "service": "Mailpit",
            "error": "aiosmtplib package not installed. Rebuild container to enable.",
            "web_ui_url": "http://localhost:8025",
            "note": "You can still access Mailpit UI directly",
        }
    try:
        # Create message
        message = MIMEMultipart()
        message["From"] = settings.ADMIN_EMAIL
        message["To"] = request.to_email
        message["Subject"] = request.subject

        # Add body
        message.attach(MIMEText(request.body, "plain"))

        # Send email via Mailpit SMTP
        await aiosmtplib.send(
            message,
            hostname="mailpit",
            port=1025,
            start_tls=False,
            use_tls=False,
        )

        return {
            "status": "success",
            "service": "Mailpit",
            "email_sent": True,
            "to": request.to_email,
            "subject": request.subject,
            "web_ui_url": "http://localhost:8025",
            "note": "Check Mailpit UI to see the sent email",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mailpit error: {str(e)}")


@router.get("/mailpit/status")
async def test_mailpit_status():
    """Check Mailpit service status."""
    try:
        # Third-party imports
        import httpx

        async with httpx.AsyncClient() as client:
            # Check Mailpit API
            response = await client.get("http://mailpit:8025/api/v1/messages")

            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "service": "Mailpit",
                    "web_ui_url": "http://localhost:8025",
                    "api_accessible": True,
                    "total_messages": data.get("total", 0),
                    "messages_count": data.get("count", 0),
                }
            else:
                return {
                    "status": "warning",
                    "service": "Mailpit",
                    "web_ui_url": "http://localhost:8025",
                    "api_accessible": False,
                    "note": "Mailpit might be running but API not accessible from container",
                }
    except Exception as e:
        return {
            "status": "warning",
            "service": "Mailpit",
            "web_ui_url": "http://localhost:8025",
            "note": "Access Mailpit directly at http://localhost:8025",
            "error": str(e),
        }


# ============= RabbitMQ Test =============
@router.get("/rabbitmq")
async def test_rabbitmq():
    """Check RabbitMQ service status."""
    try:
        # Standard library imports
        from base64 import b64encode

        # Third-party imports
        import httpx

        # Create auth header
        credentials = f"{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASSWORD}"
        auth_header = b64encode(credentials.encode()).decode()

        async with httpx.AsyncClient() as client:
            # Check RabbitMQ Management API
            response = await client.get(
                "http://rabbitmq:15672/api/overview",
                headers={"Authorization": f"Basic {auth_header}"},
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "service": "RabbitMQ",
                    "management_url": "http://localhost:15672",
                    "credentials": {
                        "username": settings.RABBITMQ_USER,
                        "password": settings.RABBITMQ_PASSWORD,
                    },
                    "version": data.get("rabbitmq_version", "unknown"),
                    "erlang_version": data.get("erlang_version", "unknown"),
                    "message_stats": data.get("message_stats", {}),
                    "queue_totals": data.get("queue_totals", {}),
                }
            else:
                return {
                    "status": "warning",
                    "service": "RabbitMQ",
                    "management_url": "http://localhost:15672",
                    "credentials": {
                        "username": settings.RABBITMQ_USER,
                        "password": settings.RABBITMQ_PASSWORD,
                    },
                    "api_response_code": response.status_code,
                }
    except Exception as e:
        return {
            "status": "warning",
            "service": "RabbitMQ",
            "management_url": "http://localhost:15672",
            "credentials": {"username": "devuser", "password": "devpass"},
            "note": "Access RabbitMQ Management at http://localhost:15672",
            "error": str(e),
        }


# ============= Health Check All Services =============
@router.get("/all")
async def test_all_services():
    """Run health checks on all services."""
    results = {}

    # Test Database
    try:
        db_result = await test_database()
        results["postgresql"] = {"status": "healthy", "details": db_result}
    except Exception as e:
        results["postgresql"] = {"status": "unhealthy", "error": str(e)}

    # Test Redis
    try:
        redis_result = await test_redis()
        results["redis"] = {"status": "healthy", "details": redis_result}
    except Exception as e:
        results["redis"] = {"status": "unhealthy", "error": str(e)}

    # Test Celery Beat
    try:
        beat_result = await test_celery_beat()
        # Check if it's a warning (celery not available) vs actual error
        if beat_result.get("status") == "warning":
            results["celery_beat"] = {"status": "unavailable", "details": beat_result}
        else:
            results["celery_beat"] = {"status": "healthy", "details": beat_result}
    except Exception as e:
        results["celery_beat"] = {"status": "unhealthy", "error": str(e)}

    # Test Flower
    try:
        flower_result = await test_flower()
        results["flower"] = {"status": "healthy", "details": flower_result}
    except Exception as e:
        results["flower"] = {"status": "unhealthy", "error": str(e)}

    # Test Mailpit
    try:
        mailpit_result = await test_mailpit_status()
        # Check if it's a warning (service unavailable) vs actual error
        if mailpit_result.get("status") == "warning":
            results["mailpit"] = {"status": "unavailable", "details": mailpit_result}
        else:
            results["mailpit"] = {"status": "healthy", "details": mailpit_result}
    except Exception as e:
        results["mailpit"] = {"status": "unhealthy", "error": str(e)}

    # Test RabbitMQ
    try:
        rabbitmq_result = await test_rabbitmq()
        # Check if it's a warning (service unavailable) vs actual error
        if rabbitmq_result.get("status") == "warning":
            results["rabbitmq"] = {"status": "unavailable", "details": rabbitmq_result}
        else:
            results["rabbitmq"] = {"status": "healthy", "details": rabbitmq_result}
    except Exception as e:
        results["rabbitmq"] = {"status": "unhealthy", "error": str(e)}

    # Summary
    healthy_count = sum(1 for s in results.values() if s["status"] == "healthy")
    unavailable_count = sum(1 for s in results.values() if s["status"] == "unavailable")
    unhealthy_count = sum(1 for s in results.values() if s["status"] == "unhealthy")
    total_count = len(results)

    # Consider unavailable services as not affecting overall health
    overall_status = "healthy" if unhealthy_count == 0 else "degraded"

    return {
        "overall_status": overall_status,
        "healthy_services": healthy_count,
        "unavailable_services": unavailable_count,
        "unhealthy_services": unhealthy_count,
        "total_services": total_count,
        "services": results,
        "access_urls": {
            "api_docs": "http://localhost:8000/api/v1/docs",
            "flower": "http://localhost:5555",
            "mailpit": "http://localhost:8025",
            "minio": "http://localhost:9001",
            "rabbitmq": "http://localhost:15672",
        },
    }
