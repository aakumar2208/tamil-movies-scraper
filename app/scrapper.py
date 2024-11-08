import requests
from bs4 import BeautifulSoup
from datetime import datetime, date
from app.database import supabase
from app.schemas import MovieCreate, ReviewBase
from typing import List
import logging
from datetime import datetime, date, timedelta

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

def parse_review_date(date_str: str) -> date:
    """
    Parse date string from Letterboxd format to date object.
    Example formats: "12 Jul 2024", "Yesterday", "Today", ""
    """
    try:
        # Handle empty or None date strings
        if not date_str or date_str.strip() == '':
            return date.today()
            
        date_str = date_str.strip().lower()
        if date_str == 'today':
            return date.today()
        elif date_str == 'yesterday':
            return date.today() - timedelta(days=1)
        else:
            return datetime.strptime(date_str, '%d %b %Y').date()
    except Exception as e:
        logger.error(f"Error parsing date {date_str!r}: {e}")
        return date.today()  # Fallback to today's date


def scrape_movie_reviews(letterboxd_url: str, page: int = 1) -> List[ReviewBase]:
    """
    Scrapes reviews for a given movie from Letterboxd.
    
    Args:
        letterboxd_url: The Letterboxd URL of the movie (e.g., 'https://letterboxd.com/film/maharaja-2024/')
        page: Page number to scrape (default: 1)
    
    Returns:
        List of ReviewBase objects containing review data
    """
    # Build the reviews URL by appending the reviews path
    print("Letterboxd URL: ", letterboxd_url)
    reviews_url = f"{letterboxd_url}reviews/by/activity/page/{page}/"
    print("Reviews URL: ", reviews_url)
    
    try:
        response = requests.get(reviews_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        reviews = []
        review_items = soup.select('li.film-detail')
        
        for item in review_items:
            # Extract author
            author_elem = item.select_one('strong.name')
            author = author_elem.text if author_elem else None
            
            # Extract date
            date_elem = item.select_one('span._nobr')
            review_date = parse_review_date(date_elem.text) if date_elem else date.today()
            
            # Extract rating
            rating_elem = item.select_one('span.rating')
            rating = None
            if rating_elem:
                # Find the class that starts with 'rated-'
                rated_class = next((cls for cls in rating_elem['class'] if cls.startswith('rated-')), None)
                if rated_class:
                    try:
                        # Extract the numeric value after 'rated-' and convert to float
                        rating_str = rated_class.replace('rated-', '')
                        if rating_str.isdigit():
                            rating = float(rating_str) / 2  # Convert to 5-star scale
                    except ValueError:
                        logger.debug(f"Skipping invalid rating value: {rating_str}")
                        rating = None
            
            # Extract review content
            content_elem = item.select_one('div.body-text')
            content = content_elem.text.strip() if content_elem else None
            
            # Extract likes count
            likes_elem = item.select_one('[data-count]')
            likes = likes_elem['data-count'] if likes_elem else '0'
            
            # Extract comments count
            comments_elem = item.select_one('a.comment-count')
            comments = comments_elem.text if comments_elem else '0'
            
            review_data = ReviewBase(
                author=author,
                content=content or "",  # Ensure content is not None since it's required
                rating=rating,
                date=review_date,
                likes=int(likes),
                comments=int(comments) if comments != '0' else 0,
                letterboxd_url=letterboxd_url
            )
            
            print("Author: ", author)
            print("Date: ", review_date)
            print("Rating: ", rating)
            print("Content: ", content)
            print("Likes: ", likes)
            print("Comments: ", comments)
            print("Letterboxd URL: ", letterboxd_url)
            # Print a separator
            print("-" * 50)
            reviews.append(review_data)

        return reviews
    
    except Exception as e:
        logger.error(f"Error scraping reviews for URL {letterboxd_url}, page {page}: {str(e)}")
        return []

def scrape_all_movie_reviews(letterboxd_url: str) -> List[ReviewBase]:
    """
    Scrapes all reviews for a movie by iterating through pages until no more reviews are found.
    
    Args:
        letterboxd_url: The Letterboxd URL of the movie
    
    Returns:
        List of all reviews
    """
    all_reviews = []
    page = 1
    
    while True:
        reviews = scrape_movie_reviews(letterboxd_url, page)
        if not reviews:
            break
            
        all_reviews.extend(reviews)
        page += 1
        logger.info(f"Scraped {len(reviews)} reviews from page {page} for {letterboxd_url}")
        
    return all_reviews