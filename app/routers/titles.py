from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from sqlalchemy.exc import SQLAlchemyError
from app import schemas, models, crud
from app.database import get_db
from datetime import date

router = APIRouter(prefix="/titles", tags=["titles"])

def get_title_or_404(title_id: int, db: Session = Depends(get_db)) -> models.Title:
    title = crud.get_title(db, title_id)
    if not title:
        raise HTTPException(status_code=404, detail="Тайтл не найден")
    return title

@router.get("/", response_model=List[schemas.TitleResponse])
def read_titles(
    skip: int = Query(0, ge=0, description="Пропустить N записей"),
    limit: int = Query(100, ge=1, le=1000, description="Лимит записей"),
    db: Session = Depends(get_db)
):
    try:
        return crud.get_titles(db, skip, limit)
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Ошибка базы данных: {str(e)}")

@router.get("/{title_id}", response_model=schemas.TitleResponse)
def read_title(title: models.Title = Depends(get_title_or_404)):
    return title

@router.post("/", response_model=schemas.TitleResponse, status_code=201)
def create_title(title: schemas.TitleCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_title(db, title)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Ошибка базы данных: {str(e)}")
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка: {str(e)}")

@router.patch("/{title_id}", response_model=schemas.TitleResponse)
def patch_title(
    title: models.Title = Depends(get_title_or_404),
    title_update: schemas.TitleUpdate = None,
    db: Session = Depends(get_db)
):
    if not title_update:
        return title
    
    update_data = title_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")
    
    try:
        return crud.update_title_partial(db, title, update_data)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Ошибка базы данных: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{title_id}", status_code=204)
def delete_title(
    title: models.Title = Depends(get_title_or_404),
    db: Session = Depends(get_db)
):
    try:
        crud.delete_title(db, title)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка удаления: {str(e)}")

@router.get("/search/advanced", response_model=List[schemas.TitleResponse])
def search_titles_advanced(
    genre_name: Optional[str] = Query(None, description="Название жанра"),
    year_start: Optional[int] = Query(None, ge=1900, le=2100, description="Год начала"),
    year_end: Optional[int] = Query(None, ge=1900, le=2100, description="Год окончания"),
    status: Optional[str] = Query(None, description="Статус тайтла"),
    min_rating: float = Query(0.0, ge=0, le=10, description="Минимальный рейтинг"),
    skip: int = Query(0, ge=0, description="Пропустить N записей"),
    limit: int = Query(50, le=100, description="Лимит записей"),
    db: Session = Depends(get_db)
):
    try:
        if year_start and year_end and year_start > year_end:
            raise HTTPException(status_code=400, detail="Год начала не может быть больше года окончания")
        
        if status:
            valid_statuses = ['announced', 'ongoing', 'released', 'discontinued']
            if status not in valid_statuses:
                raise HTTPException(status_code=400, detail=f"Некорректный статус. Допустимые: {valid_statuses}")
        
        query = db.query(models.Title).options(joinedload(models.Title.genres))
        
        if genre_name:
            query = query.join(models.Title.genres)
            query = query.filter(models.Genre.name.ilike(f"%{genre_name.strip()}%"))
        
        if year_start:
            query = query.filter(models.Title.start_date >= date(year_start, 1, 1))
        if year_end:
            query = query.filter(models.Title.start_date <= date(year_end, 12, 31))
        if status:
            query = query.filter(models.Title.status == status)
        if min_rating and min_rating > 0:
            query = query.filter(models.Title.average_rating >= min_rating)
        
        query = query.order_by(
            models.Title.average_rating.desc().nullslast(),
            models.Title.vote_count.desc(),
            models.Title.start_date.desc()
        )
        
        return query.offset(skip).limit(limit).all()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка поиска: {str(e)}")

@router.get("/search/title", response_model=List[schemas.TitleResponse])
def search_titles_by_name(
    q: str = Query(..., min_length=1, description="Поисковый запрос по названию"),
    exact: bool = Query(False, description="Точный поиск (регистронезависимый)"),
    skip: int = Query(0, ge=0, description="Пропустить N записей"),
    limit: int = Query(100, ge=1, le=1000, description="Лимит записей"),
    db: Session = Depends(get_db)
):
    try:
        if len(q) > 100:
            raise HTTPException(status_code=400, detail="Слишком длинный запрос")
        
        return crud.get_titles_by_name(db, q.strip(), exact=exact, skip=skip, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка поиска: {str(e)}")