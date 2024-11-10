from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.services.scraper import scrape_tamil_movies, process_all_movies_metadata, process_all_movies_reviews
from app.services.analyzer import process_all_reviews
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/movies", response_model=Dict[str, str])
async def scrape_movies(start_page: int = 1, total_pages: int = 1):
    try:
        scrape_tamil_movies(start_page=start_page, total_pages=total_pages)
        return {"message": f"Successfully scraped {total_pages} pages starting from page {start_page}"}
    except Exception as e:
        logger.error(f"Error scraping movies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/metadata", response_model=Dict[str, Any])
async def update_metadata():
    try:
        result = process_all_movies_metadata()
        return result
    except Exception as e:
        logger.error(f"Error updating metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reviews", response_model=Dict[str, int])
async def scrape_all_reviews():
    try:
        result = process_all_movies_reviews()
        return result
    except Exception as e:
        logger.error(f"Error scraping all reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/analyze", response_model=Dict[str, int])
async def analyze_reviews():
    try:
        processed_count = process_all_reviews()
        return {"processed_reviews": processed_count}
    except Exception as e:
        logger.error(f"Error analyzing reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))
