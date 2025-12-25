from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import text
from app import schemas, models 
from app.database import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/top-anime", response_model=List[schemas.TopAnimeView])
def get_top_anime(
    skip: int = Query(0, ge=0, description="Количество записей для пропуска"),
    limit: int = Query(10, ge=1, le=100, description="Количество записей для возврата"),
    db: Session = Depends(get_db)
):
    """
    Получить топ аниме.
    """
    try:
        q = text("""
            SELECT id, title, average_rating, vote_count, poster_url 
            FROM view_top_anime 
            LIMIT :lim OFFSET :off
        """)
        rows = db.execute(q, {"lim": limit, "off": skip}).mappings().all()
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")

@router.get("/user-stats", response_model=List[schemas.UserStatsResponse])
def get_user_stats(
    skip: int = Query(0, ge=0, description="Количество записей для пропуска"),
    limit: int = Query(100, ge=1, le=500, description="Количество записей для возврата"),
    db: Session = Depends(get_db)
):
    """
    Сортировка по количеству завершенных тайтлов.
    """
    try:
        q = text("""
            SELECT id, username, total_titles, completed_count, avg_score, last_active 
            FROM view_user_stats 
            ORDER BY completed_count DESC 
            LIMIT :lim OFFSET :off
        """)
        rows = db.execute(q, {"lim": limit, "off": skip}).mappings().all()
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")

@router.get("/genre-popularity", response_model=List[schemas.GenrePopularityResponse])
def get_genre_popularity(
    min_titles: int = Query(10, ge=1, description="Минимальное количество тайтлов в жанре"),
    skip: int = Query(0, ge=0, description="Количество записей для пропуска"),
    limit: int = Query(100, ge=1, le=500, description="Количество записей для возврата"),
    db: Session = Depends(get_db)
):
    """
    Получить популярность жанров.
    """
    try:
        q = text("""
            SELECT genre, titles_count, genre_avg_rating 
            FROM view_genre_popularity 
            WHERE titles_count >= :min_titles 
            ORDER BY titles_count DESC
            LIMIT :lim OFFSET :off
        """)
        rows = db.execute(q, {"min_titles": min_titles, "lim": limit, "off": skip}).mappings().all()
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")

@router.get("/audit-log", response_model=List[schemas.AuditLogResponse])
def get_audit_log(
    skip: int = Query(0, ge=0, description="Количество записей для пропуска"),
    limit: int = Query(100, ge=1, le=500, description="Количество записей для возврата"),
    db: Session = Depends(get_db)
):
    """
    Получить журнал аудита.
    Сортировка по времени события (новые сначала).
    """
    try:
        return db.query(models.AuditLog) \
                 .order_by(models.AuditLog.event_timestamp.desc()) \
                 .offset(skip) \
                 .limit(limit) \
                 .all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")
    
@router.get("/user/{user_id}/rank", response_model=schemas.UserRankResponse)
def get_user_rank(
    user_id: int,
    include_stats: bool = Query(False, description="Включить количество завершённых тайтлов"),
    db: Session = Depends(get_db)
):
    """
    Получить ранг пользователя по количеству завершённых тайтлов.
    """
    try:
        q = text("SELECT get_user_rank(:user_id)")
        rank = db.execute(q, {"user_id": user_id}).scalar()
        
        if rank == "Пользователь не найден":
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        response_data = {
            "user_id": user_id,
            "rank": rank
        }
        
        if include_stats:
            stats_q = text("""
                SELECT COUNT(*) 
                FROM user_library 
                WHERE user_id = :user_id AND status = 'completed'
            """)
            completed_count = db.execute(stats_q, {"user_id": user_id}).scalar()
            response_data["completed_count"] = completed_count
        
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка базы данных: {str(e)}")