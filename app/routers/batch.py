from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app import schemas, models
from app.database import get_db

router = APIRouter(prefix="/batch", tags=["batch"])

@router.post("/titles")
def batch_insert_titles(titles: List[schemas.TitleCreate], db: Session = Depends(get_db)):
    """
    Батчевая загрузка тайтлов
    Пропуск дубликатов по (canonical_title, type)
    """
    inserted = 0
    skipped = 0
    
    for title_data in titles:
        existing = db.query(models.Title).filter(
            models.Title.canonical_title == title_data.canonical_title,
            models.Title.type == title_data.type
        ).first()
        
        if existing:
            skipped += 1
            continue  
        
        try:
            db_title = models.Title(**title_data.model_dump())
            db.add(db_title)
            inserted += 1
        except Exception as e:
            skipped += 1
    
    db.commit()
    
    return {
        "status": "success",
        "message": f"Добавлено {inserted} тайтлов, пропущено {skipped} (дубликаты/ошибки)",
        "inserted": inserted,
        "skipped": skipped
    }