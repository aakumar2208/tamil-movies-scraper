import requests
from bs4 import BeautifulSoup
from datetime import datetime, date
from app.database import supabase
from app.schemas import MovieCreate
from typing import List
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Base URL for Tamil movies AJAX endpoint
BASE_URL = "https://letterboxd.com/films/ajax/popular/language/tamil/page/{page}/?esiAllowFilters=true"

def fetch_page(page: int) -> str:
    """
    Fetches the HTML content from the AJAX endpoint for a given page number.
    """
    url = BASE_URL.format(page=page)
    logger.info(f"Fetching URL: {url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.error(f"Failed to fetch page {page}: {str(e)}")
        return ""

def parse_movies(html: str) -> List[MovieCreate]:
    """
    Parses the HTML content from the AJAX response to extract movie details.
    """
    soup = BeautifulSoup(html, 'html.parser')
    movie_list = []

    # Find all movie containers
    movies = soup.find_all('li', class_='poster-container')
    # logger.info(f"Found {len(movies)} movies on the page")

    for movie in movies:
        try:
            # Extract basic details
            poster_div = movie.find('div', class_='film-poster')
            
            if not poster_div:
                continue

            # Extract title from the img alt attribute
            title = poster_div.find('img')['alt'] if poster_div.find('img') else None
            
            # Extract Letterboxd URL
            letterboxd_url = f"https://letterboxd.com{poster_div['data-target-link']}" if poster_div.get('data-target-link') else None
            
            # Extract average rating from the li element
            average_rating = float(movie['data-average-rating']) if movie.get('data-average-rating') else None

            # Create MovieCreate object
            movie_data = MovieCreate(
                title=title,
                genre=[],
                average_rating=average_rating,
                letterboxd_url=letterboxd_url,
                poster_url=None,
                release_date=None,
            )
            
            movie_list.append(movie_data)
            # logger.info(f"Parsed movie: {title}, {letterboxd_url}, {average_rating}")

        except Exception as e:
            logger.error(f"Error parsing movie: {str(e)}")
            continue

    return movie_list

def insert_movies(movies: List[MovieCreate]) -> None:
    """
    Insert movies into Supabase database.
    
    Args:
        movies: List of MovieCreate objects to insert
    """
    try:
        # Convert movies to list of dictionaries
        movies_data = [movie.dict() for movie in movies]
        
        # Insert movies into Supabase
        response = supabase.table("movies").upsert(
            movies_data, 
        ).execute()
        
    except Exception as e:
        logger.error(f"Error inserting movies into database: {str(e)}")
        raise

def scrape_tamil_movies(start_page: int = 1, total_pages: int = 1):
    """
    Scrapes Tamil movies from Letterboxd across the specified number of pages.
    
    Args:
        start_page (int): The page number to start scraping from (default: 1)
        total_pages (int): Number of pages to scrape (default: 1)
    """
    end_page = start_page + total_pages
    
    for page in range(start_page, end_page):
        html = fetch_page(page)
        if not html:
            logger.warning(f"No HTML content fetched for page {page}. Skipping...")
            continue

        movies = parse_movies(html)
        if movies:
            logger.info(f"Successfully parsed {len(movies)} movies from page {page}")
            try:
                insert_movies(movies)
                logger.info(f"Successfully inserted movies from page {page}")
            except Exception as e:
                logger.error(f"Failed to insert movies from page {page}: {str(e)}")
        else:
            logger.warning(f"No movies found on page {page}")

if __name__ == "__main__":
    scrape_tamil_movies(total_pages=2)  # Scrape first 2 pages as an example
