import os
import time
import json
from typing import List, Dict, Any
import google.generativeai as genai
from dotenv import load_dotenv
from app.database import supabase
from app.schemas import Review
import logging

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# Constants
BATCH_SIZE = 1000
FETCH_SIZE = 10000

def get_sentiment_prompt(reviews: List[Dict[str, Any]]) -> str:
    """Generate the prompt for sentiment analysis."""
    reviews_text = "\n\n".join([f"Review {i}: {r['content']}" for i, r in enumerate(reviews)])
    
    return f"""You are an expert Tamil cinema critic and sentiment analyst. You deeply understand Tamil cinema culture, narratives, and audience expectations. Analyze the following movie reviews considering:

1. Cultural context and Tamil cinema sensibilities
2. Local audience expectations and preferences
3. Technical aspects (direction, acting, music, etc.)
4. Emotional impact and cultural resonance
5. Commercial and artistic merit

For each review, provide a sentiment score between -1 and 1, where:
- -1 represents extremely negative/disappointing
- -0.5 represents moderately negative
- 0 represents neutral/mixed feelings
- 0.5 represents moderately positive
- 1 represents extremely positive/exceptional

Reviews to analyze:
{reviews_text}

Return ONLY an array of numbers representing the sentiment scores in the same order as the reviews."""

def analyze_sentiments(reviews: List[Dict[str, Any]], retry_count: int = 0, max_retries: int = 3) -> List[float]:
    """Analyze sentiments of reviews using Gemini."""
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        prompt = get_sentiment_prompt(reviews)
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                top_p=0.8,
                top_k=40,
                max_output_tokens=8192,
            )
        )
        
        # Parse the response text as JSON array
        sentiments = json.loads(response.text)
        return sentiments
        
    except Exception as e:
        if retry_count >= max_retries:
            raise Exception(f"Max retry attempts ({max_retries}) reached")
            
        # Simple exponential backoff
        wait_time = 60 * (2 ** retry_count)
        print(f"Error occurred: {str(e)}. Retrying in {wait_time} seconds...")
        time.sleep(wait_time)
        
        return analyze_sentiments(reviews, retry_count + 1, max_retries)

def chunk_array(array: List[Any], size: int) -> List[List[Any]]:
    """Split array into chunks of specified size."""
    return [array[i:i + size] for i in range(0, len(array), size)]

def process_reviews_batch(reviews: List[Dict[str, Any]], batch_number: int) -> int:
    """Process a batch of reviews."""
    try:
        print(f"Processing batch {batch_number} with {len(reviews)} reviews...")
        sentiments = analyze_sentiments(reviews)
        
        # Prepare updates
        updates = [
            {
                "id": review["id"],
                "sentiment_score": sentiment
            }
            for review, sentiment in zip(reviews, sentiments)
        ]
        
        # Update reviews in database
        response = supabase.table("reviews").upsert(updates).execute()
        
        print(f"Completed batch {batch_number}")
        return len(sentiments)
        
    except Exception as e:
        print(f"Error processing batch {batch_number}: {str(e)}")
        raise

def process_all_reviews():
    """Process all reviews in the database."""
    try:
        processed_count = 0
        last_id = None
        has_more = True
        
        print("Starting review processing...")
        
        while has_more:
            # Fetch reviews
            query = supabase.table("reviews").select("*").order("id")
            if last_id:
                query = query.gt("id", last_id)
            query = query.limit(FETCH_SIZE)
            
            response = query.execute()
            reviews = response.data
            
            if not reviews or len(reviews) == 0:
                print("No more reviews to process")
                break
                
            print(f"Fetched {len(reviews)} reviews")
            last_id = reviews[-1]["id"]
            
            # Process reviews in batches
            batches = chunk_array(reviews, BATCH_SIZE)
            print(f"Processing {len(batches)} batches sequentially...")
            
            for i, batch in enumerate(batches, 1):
                try:
                    batch_count = process_reviews_batch(batch, i)
                    processed_count += batch_count
                    print(f"Total processed so far: {processed_count}")
                    
                    # Small delay between batches
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"Failed to process batch {i}: {str(e)}")
                    continue
            
            if len(reviews) < FETCH_SIZE:
                has_more = False
                
        print(f"Completed! Total reviews processed: {processed_count}")
        return processed_count
        
    except Exception as e:
        print(f"Error in main process: {str(e)}")
        raise

logger = logging.getLogger(__name__)