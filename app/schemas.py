# app/schemas.py
from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import date, datetime

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r"^\S+@\S+\.\S+$")

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserResponse(UserBase):
    id: int
    is_active: bool
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    status: str
    message: str
    user_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

class LibraryUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(planned|watching|completed|dropped|on_hold)$")
    progress: Optional[int] = Field(None, ge=0)
    user_score: Optional[int] = Field(None, ge=1, le=10)

class LibraryCreate(BaseModel):
    user_id: int
    title_id: int
    status: str = Field(..., pattern="^(planned|watching|completed|dropped|on_hold)$")
    progress: int = Field(0, ge=0)
    user_score: Optional[int] = Field(None, ge=1, le=10)

class LibraryResponse(LibraryCreate):
    id: int
    last_updated: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class ReviewCreate(BaseModel):
    user_id: int
    title_id: int
    content: str = Field(..., min_length=10, max_length=5000)

class ReviewResponse(ReviewCreate):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class GenreBase(BaseModel):
    name: str
    model_config = ConfigDict(from_attributes=True)

class TitleBase(BaseModel):
    canonical_title: str = Field(..., min_length=1, max_length=255)
    russian_title: Optional[str] = Field(None, max_length=255)
    type: str = Field(..., pattern="^(anime|manga)$")
    status: str = Field(..., pattern="^(announced|ongoing|released|discontinued)$")
    synopsis: Optional[str] = None
    poster_url: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    episodes_count: Optional[int] = Field(None, ge=0)
    volumes_count: Optional[int] = Field(None, ge=0)
    chapters_count: Optional[int] = Field(None, ge=0)

    @model_validator(mode="after")
    def check_dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("Дата окончания не может быть раньше даты начала")
        return self

class TitleCreate(TitleBase):
    pass

class TitleUpdate(BaseModel):
    canonical_title: Optional[str] = Field(None, min_length=1, max_length=255)
    russian_title: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(announced|ongoing|released|discontinued)$")
    synopsis: Optional[str] = None
    poster_url: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class TitleResponse(TitleBase):
    id: int
    average_rating: Optional[Decimal] = None
    vote_count: int
    genres: List[GenreBase] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)

class TopAnimeView(BaseModel):
    id: int
    title: str
    average_rating: Optional[Decimal]
    vote_count: int
    poster_url: Optional[str]
    model_config = ConfigDict(from_attributes=True)

class UserStatsResponse(BaseModel):
    id: int
    username: str
    total_titles: int
    completed_count: int
    avg_score: Optional[Decimal] = None
    last_active: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class GenrePopularityResponse(BaseModel):
    genre: str
    titles_count: int
    genre_avg_rating: Optional[Decimal] = None
    model_config = ConfigDict(from_attributes=True)

class AuditLogResponse(BaseModel):
    id: int
    event_timestamp: Optional[datetime] = None
    user_id: Optional[int] = None
    user_role: str
    action_type: str
    entity_type: str
    entity_id: int
    description: str
    changes: Optional[Dict[str, Any]] = None
    model_config = ConfigDict(from_attributes=True)

class BatchImportConfig(BaseModel):
    """Параметры батчевой загрузки"""
    skip_duplicates: bool = Field(True, description="Пропускать дубликаты (по canonical_title)")
    on_conflict: str = Field("skip", pattern="^(skip|update)$", description="Действие при конфликте: skip - пропустить, update - обновить")
    log_errors: bool = Field(True, description="Логировать ошибки в отдельную таблицу")
    batch_size: int = Field(100, ge=1, le=1000, description="Размер пакета для обработки")

class UserRankResponse(BaseModel):
    user_id: int
    rank: str
    completed_count: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)