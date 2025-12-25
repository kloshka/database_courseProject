from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app import schemas, models
from app.database import get_db
from app.auth_utils import get_password_hash, verify_password

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    exists = db.query(models.User).filter(
        (models.User.username == user.username) | (models.User.email == user.email)
    ).first()
    
    if exists:
        raise HTTPException(status_code=409, detail="Пользователь с таким username или email уже существует")
    
    hashed = get_password_hash(user.password)
    new_user = models.User(username=user.username, email=user.email, password_hash=hashed, avatar_url="/default-avatar.png")
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ошибка создания пользователя (возможно дубликат)")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login", response_model=schemas.LoginResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")
    return schemas.LoginResponse(
        status="success", 
        message=f"Добро пожаловать, {user.username}!", 
        user_id=user.id
    )

@router.delete("/{user_id}/with-reviews", status_code=204)
def delete_user_with_reviews(user_id: int, db: Session = Depends(get_db)):
    """
    Транзакция: удалить пользователя и все его отзывы.
    Демонстрация работы с несколькими таблицами в одной транзакции.
    """
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        reviews = db.query(models.Review).filter(models.Review.user_id == user_id).all()
        review_ids = [r.id for r in reviews]
        review_count = len(review_ids)
        
        db.delete(user)
        
        audit_log = models.AuditLog(
            user_id=None, 
            user_role="system",
            action_type="user_delete",
            entity_type="user",
            entity_id=user_id,
            description=f"Удален пользователь {user.username} с {review_count} отзывами",
            changes={
                "deleted_review_ids": review_ids,
                "username": user.username,
                "email": user.email,
                "total_reviews_deleted": review_count
            }
        )
        db.add(audit_log)
        db.commit()
        
        
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка базы данных: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка: {str(e)}")
    

