from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date
from uuid import UUID

class MovieBase(BaseModel):
    title: str
    genre: Optional[List[str]] = None
    release_date: Optional[date] = None
    average_rating: Optional[float] = None
    letterboxd_url: Optional[str] = None
    original_title: Optional[str] = None
    synopsis: Optional[str] = None
    runtime: Optional[int] = None
    actors: Optional[List[str]] = None
    studio: Optional[List[str]] = None
    tmdb_id: Optional[str] = None
    imdb_id: Optional[str] = None
    tmdb_url: Optional[str] = None
    imdb_url: Optional[str] = None

class MovieCreate(MovieBase):
    pass

class Movie(MovieBase):
    id: UUID

    class Config:
        from_attributes = True

class ReviewBase(BaseModel):
    author: str
    content: str
    rating: Optional[float] = None
    date: date
    likes: int = 0
    comments: int = 0
    letterboxd_url: str
    sentiment_score: Optional[float] = None

class ReviewCreate(ReviewBase):
    movie_id: UUID

class Review(ReviewBase):
    id: UUID
    movie_id: UUID

    class Config:
        from_attributes = True