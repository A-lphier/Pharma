"""
Endpoint API per health check e status del sistema.
Incluso: status Celery workers, database, Redis.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
import logging

from app.db.session import engine
from app.core.config import settings
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


class HealthResponse(BaseModel):
    """Schema risposta health check."""
    status: str
    version: str
    database: str
    redis: str
    celery_workers: str
    celery_beat: Optional[str] = None


class WorkerInfo(BaseModel):
    """Info singolo worker."""
    name: str
    status: str
    last_seen: Optional[str] = None
    active_tasks: int = 0
    pool_status: Optional[str] = None


class WorkersResponse(BaseModel):
    """Schema risposta status workers."""
    status: str
    workers_online: int
    workers_total: int
    workers: list[WorkerInfo]
    beat_schedule: dict


@router.get("", response_model=HealthResponse)
async def health_check():
    """
    Health check completo del sistema.
    Verifica: database, Redis, Celery workers.
    """
    # Check database
    db_status = "healthy"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)[:50]}"
        logger.error(f"Health: Database check failed: {e}")
    
    # Check Redis
    redis_status = "healthy"
    try:
        from redis import Redis
        r = Redis.from_url(settings.REDIS_URL)
        r.ping()
        r.close()
    except Exception as e:
        redis_status = f"unhealthy: {str(e)[:50]}"
        logger.error(f"Health: Redis check failed: {e}")
    
    # Check Celery workers
    celery_status = await _check_celery_workers()
    
    # Check Celery Beat
    beat_status = None
    try:
        beat_schedule = celery_app.conf.beat_schedule
        beat_status = f"active ({len(beat_schedule)} tasks scheduled)"
    except Exception as e:
        beat_status = f"error: {str(e)[:50]}"
    
    # Determina status generale
    overall = "healthy"
    if "unhealthy" in db_status or "unhealthy" in redis_status:
        overall = "degraded"
    if "unhealthy" in celery_status:
        overall = "degraded"
    
    return HealthResponse(
        status=overall,
        version=settings.APP_VERSION,
        database=db_status,
        redis=redis_status,
        celery_workers=celery_status,
        celery_beat=beat_status
    )


@router.get("/workers", response_model=WorkersResponse)
async def get_workers_status():
    """
    Status dettagliato dei Celery workers.
    Endpoint: GET /api/v1/health/workers
    """
    workers = []
    workers_online = 0
    workers_total = 0
    
    try:
        # Inspect workers from Celery
        inspect = celery_app.control.inspect()
        
        # Get active workers
        active_workers = inspect.active() or {}
        registered = inspect.registered() or {}
        stats = inspect.stats() or {}
        
        for worker_name, worker_stats in stats.items():
            workers_total += 1
            active_tasks = len(active_workers.get(worker_name, []))
            
            workers.append(WorkerInfo(
                name=worker_name,
                status="online",
                active_tasks=active_tasks,
                pool_status=worker_stats.get("pool", {}).get("max-concurrency", "unknown") if isinstance(worker_stats, dict) else "unknown"
            ))
            workers_online += 1
        
        # Trova worker registered ma non in stats (offline)
        all_registered = set()
        for task_list in registered.values():
            if isinstance(task_list, list):
                all_registered.update(task_list)
        
        celery_status = "online" if workers_online > 0 else "offline"
        
    except Exception as e:
        logger.error(f"Health: Error checking workers: {e}")
        celery_status = f"error: {str(e)[:50]}"
    
    # Beat schedule info
    beat_schedule = {}
    try:
        schedule = celery_app.conf.beat_schedule
        for task_name, task_config in schedule.items():
            beat_schedule[task_name] = {
                "task": task_config.get("task", "unknown"),
                "schedule": str(task_config.get("schedule", "unknown"))
            }
    except Exception as e:
        logger.warning(f"Health: Could not get beat schedule: {e}")
    
    return WorkersResponse(
        status=celery_status,
        workers_online=workers_online,
        workers_total=workers_total,
        workers=workers,
        beat_schedule=beat_schedule
    )


@router.post("/workers/ping")
async def ping_workers():
    """
    Ping tutti i workers Celery.
    Risponde con latenza per ogni worker.
    """
    try:
        inspect = celery_app.control.inspect()
        
        # Ping a tutti i worker
        result = inspect.ping()
        
        if result:
            return {
                "success": True,
                "workers_responded": len(result),
                "latencies": result
            }
        else:
            return {
                "success": False,
                "error": "Nessun worker ha risposto"
            }
    except Exception as e:
        logger.error(f"Health: Ping workers failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def _check_celery_workers() -> str:
    """Verifica se i worker Celery sono online."""
    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        
        if not stats:
            return "no workers online"
        
        worker_count = len(stats)
        return f"online ({worker_count} workers)"
        
    except Exception as e:
        return f"error: {str(e)[:50]}"
