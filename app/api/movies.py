from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from app.models.schemas import Movie, MovieCreate
from app.core.database import supabase
from app.services.ranker import rank_movies
from typing import List, Dict, Any
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[Movie])
async def get_movies():
    try:
        response = supabase.table("movies").select("*").execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching movies: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/rankings", response_model=List[Dict[str, Any]])
async def get_movie_rankings():
    """Get ranked list of movies based on review metrics."""
    try:
        rankings = rank_movies()
        return rankings
    except Exception as e:
        logger.error(f"Error getting movie rankings: {e}")
        raise HTTPException(status_code=500, detail=str(e))