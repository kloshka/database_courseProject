from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app import schemas, models, crud
from app.database import get_db

router = APIRouter(prefix="/library", tags=["library"])

@router.post("/", response_model=schemas.LibraryResponse)
def add_to_library(item: schemas.LibraryCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == item.user_id).first()
    title = db.query(models.Title).filter(models.Title.id == item.title_id).first()
    
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    if not title:
        raise HTTPException(404, "Тайтл не найден")
    
    try:
        return crud.add_to_library(db, item)
    except IntegrityError as e:
        db.rollback()
        if "unique constraint" in str(e).lower() or "duplicate key" in str(e).lower():
            raise HTTPException(409, "Этот тайтл уже есть в библиотеке пользователя")
        else:
            raise HTTPException(400, "Ошибка сохранения в БД")
    except Exception as e:
        db.rollback()
        raise HTTPException(500, "Внутренняя ошибка сервера")

@router.patch("/{user_id}/{title_id}", response_model=schemas.LibraryResponse)
def update_library_entry(user_id: int, title_id: int, update_data: schemas.LibraryUpdate, db: Session = Depends(get_db)):
    entry = db.query(models.UserLibrary).filter(models.UserLibrary.user_id == user_id, models.UserLibrary.title_id == title_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Запись в библиотеке не найдена")
    update_payload = update_data.model_dump(exclude_unset=True)
    try:
        return crud.update_library_entry(db, entry, update_payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ошибка валидации данных БД")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
