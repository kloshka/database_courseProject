from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, and_
from sqlalchemy.exc import SQLAlchemyError
from app import models, schemas


def get_titles(db: Session, skip: int = 0, limit: int = 100) -> List[models.Title]:
    """Получить список тайтлов"""
    try:
        return db.query(models.Title)\
                 .options(joinedload(models.Title.genres))\
                 .order_by(models.Title.id)\
                 .offset(skip)\
                 .limit(limit)\
                 .all()
    except SQLAlchemyError as e:
        db.rollback()
        raise e


def get_title(db: Session, title_id: int) -> Optional[models.Title]:
    """Получить тайтл по ID"""
    try:
        return db.query(models.Title)\
                 .options(joinedload(models.Title.genres))\
                 .filter(models.Title.id == title_id)\
                 .first()
    except SQLAlchemyError as e:
        db.rollback()
        raise e


def create_title(db: Session, title_data: schemas.TitleCreate) -> models.Title:
    """Создать новый тайтл"""
    try:
        db_title = models.Title(**title_data.model_dump())
        db.add(db_title)
        db.commit()
        db.refresh(db_title)
        return db_title
    except SQLAlchemyError as e:
        db.rollback()
        raise e


def update_title_partial(db: Session, title: models.Title, update_data: dict) -> models.Title:
    """Частичное обновление тайтла"""
    try:
        for key, value in update_data.items():
            if hasattr(title, key) and value is not None:
                setattr(title, key, value)
        db.add(title)
        db.commit()
        db.refresh(title)
        return title
    except SQLAlchemyError as e:
        db.rollback()
        raise e


def delete_title(db: Session, title: models.Title) -> None:
    """Удалить тайтл"""
    try:
        db.delete(title)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise e


def add_to_library(db: Session, lib: schemas.LibraryCreate) -> models.UserLibrary:
    """Добавить тайтл в библиотеку пользователя"""
    try:
        existing = db.query(models.UserLibrary).filter(
            models.UserLibrary.user_id == lib.user_id,
            models.UserLibrary.title_id == lib.title_id
        ).first()
        
        if existing:
            raise ValueError("Тайтл уже в библиотеке пользователя")
        
        new_entry = models.UserLibrary(**lib.model_dump())
        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)
        return new_entry
    except SQLAlchemyError as e:
        db.rollback()
        raise e


def update_library_entry(db: Session, entry: models.UserLibrary, data: dict) -> models.UserLibrary:
    """Обновить запись в библиотеке"""
    try:
        for key, value in data.items():
            if hasattr(entry, key) and value is not None:
                setattr(entry, key, value)
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    except SQLAlchemyError as e:
        db.rollback()
        raise e


def get_reviews(db: Session, title_id: Optional[int] = None, 
                skip: int = 0, limit: int = 50) -> List[models.Review]:
    """Получить отзывы (с фильтром по тайтлу)"""
    try:
        q = db.query(models.Review)\
              .options(joinedload(models.Review.user), joinedload(models.Review.title))
        
        if title_id:
            q = q.filter(models.Review.title_id == title_id)
            
        return q.order_by(models.Review.created_at.desc())\
                .offset(skip)\
                .limit(limit)\
                .all()
    except SQLAlchemyError as e:
        db.rollback()
        raise e


def create_review(db: Session, review: schemas.ReviewCreate) -> models.Review:
    """Создать отзыв"""
    try:
        existing = db.query(models.Review).filter(
            models.Review.user_id == review.user_id,
            models.Review.title_id == review.title_id
        ).first()
        
        if existing:
            raise ValueError("Отзыв на этот тайтл уже существует")
        
        r = models.Review(**review.model_dump())
        db.add(r)
        db.commit()
        db.refresh(r)
        return r
    except SQLAlchemyError as e:
        db.rollback()
        raise e


def delete_review(db: Session, review_id: int) -> bool:
    """Удалить отзыв по ID"""
    try:
        review = db.query(models.Review).filter(models.Review.id == review_id).first()
        if not review:
            return False
            
        db.delete(review)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise e


def get_titles_by_name(db: Session, query: str, exact: bool = False, 
                       skip: int = 0, limit: int = 100) -> List[models.Title]:
    """Поиск тайтлов по названию"""
    try:
        q = db.query(models.Title)\
              .options(joinedload(models.Title.genres))
        
        if exact:
            q = q.filter(func.lower(models.Title.canonical_title) == query.lower())
        else:
            like_pattern = f"%{query}%"
            q = q.filter(
                or_(
                    models.Title.canonical_title.ilike(like_pattern),
                    models.Title.russian_title.ilike(like_pattern)
                )
            )
            
        return q.order_by(models.Title.id.desc())\
                .offset(skip)\
                .limit(limit)\
                .all()
    except SQLAlchemyError as e:
        db.rollback()
        raise e


def get_user_stats(db: Session, user_id: int) -> dict:
    """Получить статистику пользователя"""
    try:
        stats = db.query(
            models.UserLibrary.status,
            func.count(models.UserLibrary.id).label('count')
        ).filter(
            models.UserLibrary.user_id == user_id
        ).group_by(
            models.UserLibrary.status
        ).all()
        
        avg_score = db.query(
            func.avg(models.UserLibrary.user_score).label('avg_score')
        ).filter(
            models.UserLibrary.user_id == user_id,
            models.UserLibrary.user_score.isnot(None)
        ).scalar()
        
        last_active = db.query(
            func.max(models.UserLibrary.last_updated)
        ).filter(
            models.UserLibrary.user_id == user_id
        ).scalar()
        
        return {
            'stats_by_status': {status: count for status, count in stats},
            'avg_score': float(avg_score) if avg_score else None,
            'last_active': last_active
        }
    except SQLAlchemyError as e:
        db.rollback()
        raise e


def get_popular_titles(db: Session, title_type: str = 'anime', 
                       limit: int = 20) -> List[models.Title]:
    """Получить популярные тайтлы по рейтингу"""
    try:
        return db.query(models.Title)\
                 .options(joinedload(models.Title.genres))\
                 .filter(
                     models.Title.type == title_type,
                     models.Title.average_rating.isnot(None),
                     models.Title.vote_count > 10  
                 )\
                 .order_by(
                     models.Title.average_rating.desc(),
                     models.Title.vote_count.desc()
                 )\
                 .limit(limit)\
                 .all()
    except SQLAlchemyError as e:
        db.rollback()
        raise e