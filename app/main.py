from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from app.database import supabase
from app.schemas import Movie, MovieCreate, Review, ReviewCreate
from typing import List, Dict
import logging
from app.scrapper import scrape_tamil_movies  # Import the scraping function

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Tamil Movies Scraper API",
    description="API for scraping and ranking Tamil movies from Letterboxd.",
    version="1.0.0"
)

@app.get("/", response_model=dict)
def read_root():
    return {"message": "Welcome to the Tamil Movies Scraper API!"}

# Movies Endpoints

@app.post("/movies/", response_model=Movie)
def create_movie(movie: MovieCreate):
    try:
        data = jsonable_encoder(movie)
        response = supabase.table("movies").insert(data).execute()

        logger.info(f"Response: {response}")

        return response.data[0]
    except Exception as e:
        logger.error(f"Error creating movie: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/movies/", response_model=List[Movie])
def get_movies():
    try:
        response = supabase.table("movies").select("*").execute()
        return response.data
    except Exception as e:
        logger.error(f"Error retrieving movies: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Reviews Endpoints

@app.post("/reviews/", response_model=Review)
def create_review(review: ReviewCreate):
    try:
        data = review.dict()
        response = supabase.table("reviews").insert(data).execute()
        return response.data[0]
    except Exception as e:
        logger.error(f"Error creating review: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/reviews/{movie_id}", response_model=List[Review])
def get_reviews(movie_id: str):
    try:
        response = supabase.table("reviews").select("*").eq("movie_id", movie_id).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error retrieving reviews for movie_id {movie_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Scraping Endpoint

@app.post("/scrape-tamil-movies/", response_model=Dict[str, str])
def scrape_tamil_movies_endpoint(start_page: int = 1, total_pages: int = 1):
    """
    Endpoint to trigger the scraping of Tamil movies from Letterboxd.

    - **start_page**: Page number to start scraping from (default is 1)
    - **total_pages**: Number of pages to scrape (default is 1)
    """
    try:
        logger.info(f"Starting scraping from page {start_page} for {total_pages} page(s).")
        scrape_tamil_movies(start_page=start_page, total_pages=total_pages)
        logger.info(f"Completed scraping {total_pages} page(s) starting from page {start_page}.")
        return {
            "message": f"Successfully scraped {total_pages} page(s) starting from page {start_page}."
        }
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

