from fastapi import FastAPI
from app.core.config import settings
from app.api import movies, reviews, scraping

app = FastAPI(
    title="Tamil Movies Scraper API",
    description="API for scraping and ranking Tamil movies from Letterboxd.",
    version="1.0.0"
)

# Include routers
app.include_router(movies.router, prefix="/movies", tags=["movies"])
app.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
app.include_router(scraping.router, prefix="/scraping", tags=["scraping"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Tamil Movies Scraper API!"}