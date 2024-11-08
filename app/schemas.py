from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date

class MovieBase(BaseModel):
    title: str
    genre: List[str]
    release_date: date = None
    average_rating: Optional[float] = None
    poster_url: Optional[str] = None
    letterboxd_url: Optional[str] = None

class MovieCreate(MovieBase):
    pass

class Movie(MovieBase):
    id: str

    class Config:
        orm_mode = True

class ReviewBase(BaseModel):
    user: str
    review: str
    rating: float

class ReviewCreate(ReviewBase):
    movie_id: str

class Review(ReviewBase):
    id: str
    created_at: Optional[str] = None

    class Config:
        orm_mode = True
