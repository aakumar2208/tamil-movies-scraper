
# Tamil Movies Scraper API

A FastAPI-based service that scrapes, analyzes, and ranks Tamil movies from Letterboxd.

## Features

- 🎬 **Movie Scraping**: Automated scraping of Tamil movies from Letterboxd
- 📊 **Metadata Collection**: Detailed movie information including cast, runtime, and external IDs
- 📝 **Review Analysis**: Sentiment analysis of movie reviews using OpenAI's GPT-3.5
- 🏆 **Movie Ranking**: Advanced ranking system considering:
  - Sentiment scores
  - Like counts
  - Comment engagement

## Tech Stack

- **Backend Framework**: FastAPI
- **Database**: Supabase (SQL Based)
- **AI/ML**: OpenAI GPT-3.5
- **Web Scraping**: BeautifulSoup4
- **Environment**: Python 3.x

## Installation

- Clone the repository:
```
git clone <repository-url>
cd tamil-movies-scraper
```

- Create and activate virtual environment:
```
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate
```

- Install dependencies:
```
pip install -r requirements.txt
```

- Create `.env` file with required credentials:
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
OPENAI_API_KEY=your_openai_key
```




## Usage

- Create a Supabase Project
- Populate the .env as described in Installation Steps
- Run the following query in Supabase SQL Editor to generate movies table as per the schema:
```
create table
  public.movies (
    id uuid not null default gen_random_uuid (),
    title text null,
    genre json null,
    release_date date null,
    average_rating real null,
    letterboxd_url text null,
    original_title text null,
    synopsis text null,
    runtime integer null,
    actors text[] null,
    studio text[] null,
    tmdb_id text null,
    imdb_id text null,
    tmdb_url text null,
    imdb_url text null,
    constraint movies_pkey primary key (id)
  ) tablespace pg_default;
```
- Run the following query in Supabase SQL Editor to generate reviews table as per the schema:
```
create table
  public.reviews (
    id uuid not null default gen_random_uuid (),
    movie_id uuid null default gen_random_uuid (),
    author text null,
    content text null,
    rating real null,
    date date null,
    likes integer null,
    comments integer null,
    letterboxd_url text null,
    sentiment_score real null,
    constraint reviews_pkey primary key (id),
    constraint reviews_movie_id_fkey foreign key (movie_id) references movies (id)
  ) tablespace pg_default;
```
- Start the local server:
```
uvicorn app.main:app --reload
```
- Open ```http://localhost:8000/docs``` to access the Swagger Interface to use the API Endpoints

## API Endpoints

### Movies
- `GET /movies/` - Get all movies
- `GET /movies/rankings` - Get ranked movie list

### Reviews
- `GET /reviews/` - Get all reviews

### Scraping
- `POST /scraping/movies` - Scrape new movies
- `POST /scraping/metadata` - Update movie metadata
- `POST /scraping/reviews` - Scrape movie reviews
- `POST /scraping/analyze` - Analyze review sentiments

## Database Schema

### Movies Table
- id (UUID)
- title (string)
- original_title (string)
- letterboxd_url (string)
- genre (string[])
- release_date (date)
- synopsis (text)
- runtime (integer)
- actors (string[])
- studio (string[])
- external IDs (TMDB, IMDB)

### Reviews Table
- id (UUID)
- movie_id (UUID)
- author (string)
- content (text)
- rating (float)
- date (date)
- likes (integer)
- comments (integer)
- sentiment_score (float)

## Acknowledgments

- Letterboxd for movie data
- OpenAI for sentiment analysis
- Supabase for database services