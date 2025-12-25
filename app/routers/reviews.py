from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app import schemas, crud, models
from app.database import get_db

router = APIRouter(prefix="/reviews", tags=["reviews"])

@router.get("/", response_model=List[schemas.ReviewResponse])
def get_reviews(title_id: Optional[int] = None, skip: int = Query(0, ge=0), limit: int = Query(50, le=100), db: Session = Depends(get_db)):
    return crud.get_reviews(db, title_id=title_id, skip=skip, limit=limit)

@router.post("/", response_model=schemas.ReviewResponse, status_code=201)
def create_review(review: schemas.ReviewCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == review.user_id).first()
    title = db.query(models.Title).filter(models.Title.id == review.title_id).first()
    if not user or not title:
        raise HTTPException(status_code=404, detail="Пользователь или тайтл не найден")
    try:
        return crud.create_review(db, review)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ошибка создания отзыва: нарушение целостности данных")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{review_id}", status_code=204)
def delete_review(review_id: int, db: Session = Depends(get_db)):
    review = db.query(models.Review).filter(models.Review.id == review_id).first()

    if not review:
        raise HTTPException(status_code=404, detail="Отзыв не найден")

    try:
        db.delete(review)
        db.commit()
        return None
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ошибка удаления: нарушение целостности данных")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
