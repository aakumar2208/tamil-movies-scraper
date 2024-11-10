from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from app.models.schemas import Review, ReviewCreate
from app.core.database import supabase
from typing import List
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[Review])
async def get_reviews():
    try:
        response = supabase.table("reviews").select("*").execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching reviews: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")