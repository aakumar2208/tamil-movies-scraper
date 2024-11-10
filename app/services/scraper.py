import requests
from bs4 import BeautifulSoup
from datetime import datetime, date
from app.core.database import supabase
from app.models.schemas import MovieCreate, ReviewCreate
from typing import List, Dict, Any
import logging
import re
import time
from uuid import UUID

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Base URL for Tamil movies AJAX endpoint
BASE_URL = "https://letterboxd.com/films/ajax/popular/language/tamil/page/{page}/?esiAllowFilters=true"

def fetch_page(page: int) -> str:
    """Fetches the HTML content from the AJAX endpoint for a given page number."""
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
    """Parses the HTML content to extract movie details with updated schema."""
    soup = BeautifulSoup(html, 'html.parser')
    movie_list = []

    for movie in soup.find_all('li', class_='poster-container'):
        try:
            poster_div = movie.find('div', class_='film-poster')
            if not poster_div:
                continue

            movie_data = {
                'title': poster_div.find('img')['alt'] if poster_div.find('img') else None,
                'letterboxd_url': f"https://letterboxd.com{poster_div['data-target-link']}" if poster_div.get('data-target-link') else None,
                'average_rating': float(movie['data-average-rating']) if movie.get('data-average-rating') else None,
                'genre': [],
                'release_date': None,
                'original_title': None,
                'synopsis': None,
                'runtime': None,
                'actors': [],
                'studio': [],
                'tmdb_id': None,
                'imdb_id': None,
                'tmdb_url': None,
                'imdb_url': None
            }

            if all(v is not None for v in [movie_data['title'], movie_data['letterboxd_url']]):
                movie_list.append(MovieCreate(**movie_data))

        except Exception as e:
            logger.error(f"Error parsing movie: {str(e)}")
            continue

    return movie_list

def extract_ids(imdb_url: str = None, tmdb_url: str = None) -> Dict[str, str]:
    """Extract IMDb and TMDb IDs from their respective URLs."""
    imdb_id = re.search(r'tt\d+', imdb_url) if imdb_url else None
    tmdb_id = re.search(r'movie/(\d+)', tmdb_url) if tmdb_url else None
    
    return {
        'imdb_id': imdb_id.group(0) if imdb_id else None,
        'tmdb_id': tmdb_id.group(1) if tmdb_id else None
    }

def scrape_movie_metadata(letterboxd_url: str, retry_count: int = 0) -> Dict[str, Any]:
    """Scrape detailed metadata for a movie from its Letterboxd page."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(letterboxd_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract IMDb and TMDb URLs
        imdb_url = soup.select_one('.text-footer a[data-track-action="IMDb"]')
        tmdb_url = soup.select_one('.text-footer a[data-track-action="TMDb"]')
        
        # Extract IDs
        ids = extract_ids(
            imdb_url.get('href') if imdb_url else None,
            tmdb_url.get('href') if tmdb_url else None
        )
        
        # Extract release year and convert to date
        release_year = None
        title_meta = soup.select_one('meta[property="og:title"]')
        if title_meta:
            year_match = re.search(r'\((\d{4})\)', title_meta['content'])
            if year_match:
                release_year = year_match.group(1)

        # Extract runtime
        runtime = None
        runtime_text = soup.select_one('.text-footer')
        if runtime_text:
            runtime_match = re.search(r'(\d+)\s*mins', runtime_text.text)
            if runtime_match:
                runtime = int(runtime_match.group(1))
        
        return {
            'original_title': soup.select_one('h2.originalname').text.strip() if soup.select_one('h2.originalname') else None,
            'synopsis': soup.select_one('.review.body-text.-prose.-hero p').text.strip() if soup.select_one('.review.body-text.-prose.-hero p') else None,
            'runtime': runtime,
            'actors': [a.text.strip() for a in soup.select('.cast-list.text-sluglist a')],
            'genre': [g.text.strip() for g in soup.select('#tab-genres .text-sluglist a')],
            'studio': [s.text.strip() for s in soup.select('#tab-details .text-sluglist a[href*="/studio/"]')],
            'release_date': release_year,
            **ids,
            'tmdb_url': tmdb_url.get('href') if tmdb_url else None,
            'imdb_url': imdb_url.get('href') if imdb_url else None
        }
        
    except requests.exceptions.RequestException as e:
        if retry_count < 3 and hasattr(e.response, 'status_code') and e.response.status_code == 429:
            retry_after = int(e.response.headers.get('retry-after', 60))
            logger.info(f"Rate limited. Waiting {retry_after} seconds before retry...")
            time.sleep(retry_after)
            return scrape_movie_metadata(letterboxd_url, retry_count + 1)
        raise

def insert_movies(movies: List[MovieCreate]) -> None:
    """Insert movies into Supabase database."""
    try:
        movies_data = [movie.model_dump(exclude_unset=True) for movie in movies]
        response = supabase.table("movies").upsert(movies_data).execute()
        logger.info(f"Inserted {len(movies)} movies")
    except Exception as e:
        logger.error(f"Error inserting movies: {str(e)}")
        raise

def scrape_tamil_movies(start_page: int = 1, total_pages: int = 1) -> None:
    """Scrapes Tamil movies from Letterboxd across specified pages."""
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
        time.sleep(2)  # Rate limiting

def process_all_movies_metadata() -> Dict[str, int]:
    """Process and update metadata for all movies in the database."""
    try:
        response = supabase.table("movies").select("*").execute()
        movies = response.data
        
        if not movies:
            logger.info("No movies to process")
            return {'total': 0, 'completed': 0, 'failed': 0}
            
        total = len(movies)
        completed = 0
        failed = 0
        
        logger.info(f"Found {total} movies to process")
        
        for movie in movies:
            try:
                if not movie.get('letterboxd_url'):
                    logger.warning(f"No Letterboxd URL for movie: {movie['title']}")
                    continue
                    
                logger.info(f"Processing: {movie['title']}")
                metadata = scrape_movie_metadata(movie['letterboxd_url'])
                
                update_data = {
                    'original_title': metadata['original_title'],
                    'synopsis': metadata['synopsis'],
                    'runtime': metadata['runtime'],
                    'actors': metadata['actors'],
                    'genre': metadata['genre'],
                    'studio': metadata['studio'],
                    'tmdb_id': metadata['tmdb_id'],
                    'imdb_id': metadata['imdb_id'],
                    'tmdb_url': metadata['tmdb_url'],
                    'imdb_url': metadata['imdb_url'],
                    'release_date': f"{metadata['release_date']}-01-01" if metadata['release_date'] else None
                }
                
                supabase.table("movies").update(update_data).eq('id', movie['id']).execute()
                logger.info(f"✓ Updated: {movie['title']}")
                completed += 1
                
            except Exception as e:
                logger.error(f"✗ Error processing {movie['title']}: {str(e)}")
                failed += 1
                continue
                
            time.sleep(2)  # Rate limiting
            
        return {
            'total': total,
            'completed': completed,
            'failed': failed
        }
        
    except Exception as e:
        logger.error(f"Error processing movies: {str(e)}")
        raise

def parse_review_date(date_str: str) -> date:
    """Convert Letterboxd date string to date object."""
    try:
        return datetime.strptime(date_str.strip(), '%Y-%m-%d').date()
    except ValueError:
        try:
            # Handle relative dates like "2 days ago"
            if 'days ago' in date_str:
                days = int(re.search(r'(\d+)', date_str).group(1))
                return date.today() - timedelta(days=days)
            return date.today()
        except:
            return date.today()

def scrape_movie_reviews(letterboxd_url: str, movie_id: UUID, page: int = 1) -> List[ReviewCreate]:
    """Scrapes reviews for a given movie from Letterboxd."""
    reviews_url = f"{letterboxd_url}reviews/by/activity/page/{page}/"
    logger.info(f"Scraping reviews from: {reviews_url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(reviews_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        reviews = []
        review_items = soup.select('li.film-detail')
        
        for item in review_items:
            try:
                # Extract author
                author = item.select_one('strong.name').text if item.select_one('strong.name') else None
                
                # Extract date
                date_elem = item.select_one('span._nobr')
                review_date = parse_review_date(date_elem.text) if date_elem else date.today()
                
                # Extract rating
                rating = None
                rating_elem = item.select_one('span.rating')
                if rating_elem:
                    rated_class = next((cls for cls in rating_elem['class'] if cls.startswith('rated-')), None)
                    if rated_class:
                        rating = float(rated_class.replace('rated-', '')) / 2
                
                # Extract content
                content = item.select_one('.body-text').text.strip() if item.select_one('.body-text') else ""
                
                # Extract likes count - with better error handling
                likes = 0
                likes_elem = item.select_one('[data-count]')
                if likes_elem and likes_elem.get('data-count'):
                    try:
                        likes_str = likes_elem['data-count'].strip()
                        likes = int(likes_str) if likes_str else 0
                    except (ValueError, TypeError):
                        likes = 0
                
                # Extract comments count - with better error handling
                comments = 0
                comments_elem = item.select_one('a.comment-count')
                if comments_elem and comments_elem.text:
                    try:
                        comments_str = comments_elem.text.strip()
                        comments = int(comments_str) if comments_str else 0
                    except (ValueError, TypeError):
                        comments = 0
                
                # Create review object
                review = ReviewCreate(
                    movie_id=movie_id,
                    author=author,
                    content=content,
                    rating=rating,
                    date=review_date,
                    likes=likes,
                    comments=comments,
                    letterboxd_url=reviews_url,
                    sentiment_score=None
                )
                reviews.append(review)
                
            except Exception as e:
                logger.error(f"Error parsing review: {str(e)}")
                continue
        
        return reviews
        
    except Exception as e:
        logger.error(f"Error scraping reviews: {str(e)}")
        return []

def process_movie_reviews(movie_id: UUID, letterboxd_url: str) -> Dict[str, int]:
    """Process and store all reviews for a single movie."""
    try:
        total_reviews = 0
        page = 1
        
        while True:
            reviews = scrape_movie_reviews(letterboxd_url, movie_id, page)
            if not reviews:
                break
                
            # Convert reviews to dict and format date and UUID
            reviews_data = []
            for review in reviews:
                review_dict = review.model_dump(exclude_unset=True)
                # Convert date to ISO format string
                review_dict['date'] = review_dict['date'].isoformat()
                # Convert UUID to string
                review_dict['movie_id'] = str(review_dict['movie_id'])
                reviews_data.append(review_dict)
            
            # Insert reviews into database
            supabase.table("reviews").upsert(reviews_data).execute()
            
            total_reviews += len(reviews)
            logger.info(f"Processed {len(reviews)} reviews from page {page}")
            
            page += 1
            time.sleep(2)  # Rate limiting
            
        return {"processed_reviews": total_reviews}
        
    except Exception as e:
        logger.error(f"Error processing reviews: {str(e)}")
        raise

def process_all_movies_reviews() -> Dict[str, int]:
    """Process and store reviews for all movies in the database."""
    try:
        # Fetch all movies
        response = supabase.table("movies").select("id, title, letterboxd_url").execute()
        movies = response.data
        
        if not movies:
            logger.info("No movies to process")
            return {"total_movies": 0, "total_reviews": 0, "failed_movies": 0}
            
        total_movies = len(movies)
        total_reviews = 0
        failed_movies = 0
        
        logger.info(f"Found {total_movies} movies to process reviews")
        
        for movie in movies:
            try:
                if not movie.get('letterboxd_url'):
                    logger.warning(f"No Letterboxd URL for movie: {movie['title']}")
                    continue
                    
                logger.info(f"Processing reviews for: {movie['title']}")
                result = process_movie_reviews(movie['id'], movie['letterboxd_url'])
                total_reviews += result["processed_reviews"]
                logger.info(f"✓ Processed {result['processed_reviews']} reviews for: {movie['title']}")
                
            except Exception as e:
                logger.error(f"✗ Error processing reviews for {movie['title']}: {str(e)}")
                failed_movies += 1
                continue
                
            time.sleep(2)  # Rate limiting
            
        return {
            "total_movies": total_movies,
            "total_reviews": total_reviews,
            "failed_movies": failed_movies
        }
        
    except Exception as e:
        logger.error(f"Error processing all movies reviews: {str(e)}")
        raise