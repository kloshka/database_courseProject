from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import text
import uuid
from datetime import datetime
import json
from app import schemas, models
from app.database import get_db
from pydantic import BaseModel, ConfigDict

router = APIRouter(prefix="/api", tags=["batch"])

class BatchImportResponse(BaseModel):
    batch_id: str
    status: str
    total_records: int
    successful_records: int
    skipped_records: int = 0
    failed_records: int
    successful_ids: List[int] = []
    skipped_titles: List[dict] = []
    errors: List[dict] = []
    import_duration: Optional[float] = None
    model_config = ConfigDict(from_attributes=True)

def log_error(db: Session, batch_id: str, entity_type: str, entity_data: dict, error_type: str, error_message: str):
    """Вспомогательная функция для логирования ошибок"""
    try:
        log_query = text("""
            INSERT INTO import_errors (import_batch_id, entity_type, entity_data, error_type, error_message)
            VALUES (:batch_id, :entity_type, CAST(:entity_data AS JSONB), :error_type, :error_message)
        """)
        db.execute(log_query, {
            "batch_id": batch_id,
            "entity_type": entity_type,
            "entity_data": json.dumps(entity_data),
            "error_type": error_type,
            "error_message": error_message[:500]
        })
        db.commit()
    except Exception:
        db.rollback()

@router.post("/batch-import/titles", response_model=BatchImportResponse, status_code=status.HTTP_201_CREATED)
def batch_import_titles(
    titles: List[schemas.TitleCreate],
    skip_duplicates: bool = Query(True, description="Пропускать дубликаты"),
    on_conflict: str = Query("skip", description="Действие при конфликте: skip или update"),
    log_errors: bool = Query(True, description="Логировать ошибки"),
    db: Session = Depends(get_db)
):
    """
    Батчевая загрузка тайтлов с параметрами и логированием ошибок.
    """
    start_time = datetime.now()
    batch_id = str(uuid.uuid4())
    
    successful_records = 0
    skipped_records = 0
    failed_records = 0
    successful_ids = []
    skipped_titles = []
    errors = []
    
    if on_conflict not in ["skip", "update"]:
        raise HTTPException(status_code=400, detail="Параметр on_conflict должен быть 'skip' или 'update'")
    
    if log_errors:
        try:
            batch_record = text("""
                INSERT INTO import_batches (id, entity_type, total_records, config, status, skipped_records)
                VALUES (:id, 'title', :total, CAST(:config AS JSONB), 'processing', 0)
            """)
            db.execute(batch_record, {
                "id": batch_id,
                "total": len(titles),
                "config": json.dumps({
                    "skip_duplicates": skip_duplicates,
                    "on_conflict": on_conflict,
                    "log_errors": log_errors
                })
            })
            db.commit()
        except Exception:
            db.rollback()
            log_errors = False
    
    for index, title_data in enumerate(titles, 1):
        try:
            if skip_duplicates or on_conflict == "update":
                existing = db.query(models.Title).filter(
                    models.Title.canonical_title == title_data.canonical_title,
                    models.Title.type == title_data.type
                ).first()
                
                if existing:
                    if on_conflict == "skip":
                        skipped_records += 1
                        skipped_titles.append({
                            "title": title_data.canonical_title,
                            "reason": "duplicate",
                            "existing_id": existing.id
                        })
                        continue
                    elif on_conflict == "update":
                        for key, value in title_data.model_dump().items():
                            if hasattr(existing, key) and value is not None:
                                setattr(existing, key, value)
                        db.add(existing)
                        db.commit()
                        db.refresh(existing)
                        successful_ids.append(existing.id)
                        successful_records += 1
                        continue
            
            db_title = models.Title(**title_data.model_dump())
            db.add(db_title)
            db.commit()
            db.refresh(db_title)
            
            successful_ids.append(db_title.id)
            successful_records += 1
            
        except IntegrityError as e:
            db.rollback()
            error_msg = str(e.orig).split('\n')[0] if e.orig else "Нарушение целостности данных"
            error_type = "integrity_error"
            failed_records += 1
            
            if log_errors:
                log_error(db, batch_id, "title", title_data.model_dump(), error_type, error_msg)
            
            errors.append({
                "record_index": index,
                "canonical_title": title_data.canonical_title,
                "error_type": error_type,
                "message": error_msg
            })
            
        except Exception as e:
            db.rollback()
            error_msg = str(e)
            error_type = "unknown_error"
            failed_records += 1
            
            if log_errors:
                log_error(db, batch_id, "title", title_data.model_dump(), error_type, error_msg)
            
            errors.append({
                "record_index": index,
                "canonical_title": title_data.canonical_title,
                "error_type": error_type,
                "message": error_msg
            })
    
    if log_errors:
        try:
            if failed_records == 0 and skipped_records == 0 and successful_records > 0:
                status_val = "completed"
            elif failed_records == 0 and skipped_records > 0:
                status_val = "completed_with_skipped"
            elif successful_records > 0 and failed_records > 0:
                status_val = "partial_success"
            else:
                status_val = "failed"
            
            update_batch = text("""
                UPDATE import_batches 
                SET successful_records = :success, 
                    skipped_records = :skipped,
                    failed_records = :failed,
                    completed_at = CURRENT_TIMESTAMP,
                    status = :status
                WHERE id = :batch_id
            """)
            db.execute(update_batch, {
                "success": successful_records,
                "skipped": skipped_records,
                "failed": failed_records,
                "status": status_val,
                "batch_id": batch_id
            })
            db.commit()
        except Exception:
            db.rollback()
    
    import_duration = (datetime.now() - start_time).total_seconds()
    
    if successful_records > 0 and failed_records == 0 and skipped_records == 0:
        final_status = "success"
    elif successful_records > 0 and (failed_records > 0 or skipped_records > 0):
        final_status = "partial_success"
    elif skipped_records > 0 and failed_records == 0 and successful_records == 0:
        final_status = "skipped"
    else:
        final_status = "failed"
    
    return BatchImportResponse(
        batch_id=batch_id,
        status=final_status,
        total_records=len(titles),
        successful_records=successful_records,
        skipped_records=skipped_records,
        failed_records=failed_records,
        successful_ids=successful_ids,
        skipped_titles=skipped_titles,
        errors=errors if errors else [],
        import_duration=import_duration
    )

@router.get("/batch-import/errors/{batch_id}")
def get_import_errors(batch_id: str, db: Session = Depends(get_db)):
    """Получить ошибки по идентификатору"""
    try:
        query = text("""
            SELECT id, entity_type, error_type, error_message, created_at
            FROM import_errors 
            WHERE import_batch_id = :batch_id
            ORDER BY created_at DESC
        """)
        result = db.execute(query, {"batch_id": batch_id}).mappings().all()
        return [dict(row) for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения логов: {str(e)}")

@router.get("/batch-import/history")
def get_import_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db)
):
    """Получить историю импортов"""
    try:
        query = text("""
            SELECT id, entity_type, total_records, successful_records, 
                skipped_records, failed_records, status, started_at, completed_at
            FROM import_batches
            ORDER BY started_at DESC
            LIMIT :limit OFFSET :skip
        """)
        result = db.execute(query, {"limit": limit, "skip": skip}).mappings().all()
        return [dict(row) for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения истории: {str(e)}")