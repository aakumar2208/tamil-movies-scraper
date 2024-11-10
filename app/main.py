from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from app.database import supabase
from app.schemas import Movie, MovieCreate, Review, ReviewCreate
from typing import List, Dict, Any
import logging
from app.scrapper import scrape_tamil_movies, scrape_all_movie_reviews, process_all_movies_metadata  # Import the scraping function
from app.analyze_sentiments import process_all_reviews
import time
from app.ranker import rank_movies

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

@app.post("/scrape-movie-reviews/{movie_id}", response_model=Dict[str, str])
def scrape_movie_reviews_endpoint(movie_id: str):
    """
    Endpoint to scrape all reviews for a given movie.
    
    Args:
        movie_id: The ID of the movie in our database
    """
    try:
        # First fetch the movie details from database
        movie_response = supabase.table("movies").select("*").eq("id", movie_id).execute()
        
        if not movie_response.data:
            raise HTTPException(status_code=404, detail="Movie not found")
            
        movie = movie_response.data[0]
        letterboxd_url = movie.get('letterboxd_url')
        
        if not letterboxd_url:
            raise HTTPException(
                status_code=400, 
                detail="Movie does not have a Letterboxd URL"
            )
        
        logger.info(f"Starting review scraping for movie {movie['title']} ({letterboxd_url})")
        reviews = scrape_all_movie_reviews(letterboxd_url)
        
        # Store all reviews in database with movie_id in a single batch
        reviews_to_insert = [
            ReviewCreate(
                **{
                    **review_base.model_dump(mode='json'),  # Convert to JSON-serializable format
                    'movie_id': movie_id
                }
            ).model_dump(mode='json')
            for review_base in reviews
        ]
        
        if reviews_to_insert:
            response = supabase.table("reviews").insert(reviews_to_insert).execute()
            stored_count = len(response.data)
            
        logger.info(f"Successfully scraped and stored {stored_count} reviews for {movie['title']}")
        return {
            "message": f"Successfully scraped and stored {stored_count} reviews for {movie['title']}"
        }
    except Exception as e:
        logger.error(f"Error during review scraping: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/scrape-all-movie-reviews/", response_model=Dict[str, str])
async def scrape_all_movie_reviews_endpoint():
    """
    Endpoint to scrape reviews for all movies in the database.
    This will iterate through each movie and scrape their reviews.
    """
    try:
        # Fetch all movies from database
        movies_response = supabase.table("movies").select("*").execute()
        
        if not movies_response.data:
            raise HTTPException(status_code=404, detail="No movies found in database")
            
        total_movies = len(movies_response.data)
        processed_movies = 0
        total_reviews = 0
        
        logger.info(f"Starting review scraping for {total_movies} movies")
        
        for movie in movies_response.data:
            movie_id = movie['id']
            letterboxd_url = movie.get('letterboxd_url')
            
            if not letterboxd_url:
                logger.warning(f"Skipping movie {movie['title']} - No Letterboxd URL")
                continue
                
            try:
                logger.info(f"Scraping reviews for movie: {movie['title']} ({letterboxd_url})")
                reviews = scrape_all_movie_reviews(letterboxd_url)
                
                # Prepare reviews for insertion
                reviews_to_insert = [
                    ReviewCreate(
                        **{
                            **review_base.model_dump(mode='json'),
                            'movie_id': movie_id
                        }
                    ).model_dump(mode='json')
                    for review_base in reviews
                ]
                
                if reviews_to_insert:
                    response = supabase.table("reviews").insert(reviews_to_insert).execute()
                    stored_count = len(response.data)
                    total_reviews += stored_count
                    logger.info(f"Stored {stored_count} reviews for {movie['title']}")
                
                processed_movies += 1
                logger.info(f"Progress: {processed_movies}/{total_movies} movies processed")
                
            except Exception as e:
                logger.error(f"Error processing movie {movie['title']}: {e}")
                continue
        
        success_message = (
            f"Successfully scraped {total_reviews} reviews "
            f"from {processed_movies} out of {total_movies} movies"
        )
        logger.info(success_message)
        return {"message": success_message}
        
    except Exception as e:
        logger.error(f"Error during bulk review scraping: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/analyze-reviews/", response_model=Dict[str, Any])
async def analyze_reviews_endpoint():
    """
    Endpoint to analyze all reviews using Gemini AI and calculate sentiment scores.
    """
    try:
        logger.info("Starting sentiment analysis for all reviews...")
        start_time = time.time()
        processed_count = process_all_reviews()
        end_time = time.time()
        
        return {
            "status": "success",
            "processed_reviews": processed_count,
            "processing_time_seconds": round(end_time - start_time, 2),
            "message": f"Successfully analyzed {processed_count} reviews"
        }
        
    except Exception as e:
        logger.error(f"Error during sentiment analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/rank-movies/", response_model=List[Dict[str, Any]])
async def rank_movies_endpoint():
    """
    Get ranked list of movies based on review sentiment scores, likes, and comments.
    Returns movies sorted by their ranking score.
    """
    try:
        logger.info("Starting movie ranking calculation...")
        ranked_movies = rank_movies()
        logger.info(f"Successfully ranked {len(ranked_movies)} movies")
        return ranked_movies
        
    except Exception as e:
        logger.error(f"Error during movie ranking: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update-movies-metadata/", response_model=Dict[str, Any])
async def update_movies_metadata_endpoint():
    """
    Endpoint to update metadata for all movies in the database.
    """
    try:
        logger.info("Starting movie metadata update...")
        start_time = time.time()
        results = process_all_movies_metadata()
        end_time = time.time()
        
        return {
            "status": "success",
            "total_movies": results['total'],
            "completed": results['completed'],
            "failed": results['failed'],
            "processing_time_seconds": round(end_time - start_time, 2),
            "message": f"Successfully processed {results['completed']} out of {results['total']} movies"
        }
        
    except Exception as e:
        logger.error(f"Error during metadata update: {e}")
        raise HTTPException(status_code=500, detail=str(e))

