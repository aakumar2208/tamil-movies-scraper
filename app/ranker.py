import logging
from typing import List, Dict, Any
from app.database import supabase

logger = logging.getLogger(__name__)

def rank_movies() -> List[Dict[str, Any]]:
    """
    Rank all movies based on their reviews' sentiment scores, likes, and comments using SQL.
    Returns a list of movies with their ranking scores.
    """
    try:
        # First get all movies
        movies_response = supabase.table("movies").select("*").execute()
        movies = {m['id']: m for m in movies_response.data}
        
        # Then get all reviews
        reviews_response = supabase.table("reviews").select("*").execute()
        reviews = reviews_response.data
        
        # Group reviews by movie
        movie_reviews = {}
        for review in reviews:
            movie_id = review['movie_id']
            if movie_id not in movie_reviews:
                movie_reviews[movie_id] = []
            movie_reviews[movie_id].append(review)
        
        # Calculate rankings
        rankings = []
        for movie_id, movie_data in movies.items():
            movie_review_list = movie_reviews.get(movie_id, [])
            
            # Calculate metrics
            sentiment_scores = [r['sentiment_score'] for r in movie_review_list if r.get('sentiment_score') is not None]
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
            total_likes = sum(r.get('likes', 0) for r in movie_review_list)
            total_comments = sum(r.get('comments', 0) for r in movie_review_list)
            
            rankings.append({
                'id': movie_id,
                'title': movie_data['title'],
                'review_count': len(movie_review_list),
                'average_sentiment': round(avg_sentiment, 3),
                'total_likes': total_likes,
                'total_comments': total_comments,
                'ranking_score': round(
                    (avg_sentiment * 0.6) +
                    (total_likes / (max(1, sum(r.get('likes', 0) for r in reviews))) * 0.25) +
                    (total_comments / (max(1, sum(r.get('comments', 0) for r in reviews))) * 0.15),
                    3
                )
            })
        
        # Sort by ranking score
        rankings.sort(key=lambda x: x['ranking_score'], reverse=True)
        
        # Add ranks
        for i, movie in enumerate(rankings, 1):
            movie['rank'] = i
        
        # Print rankings
        print("\n=== TAMIL MOVIES RANKING ===\n")
        print(f"{'Rank':<6}{'Title':<50}{'Score':<10}{'Reviews':<10}{'Avg Sentiment':<15}{'Likes':<10}{'Comments':<10}")
        print("-" * 100)
        
        for movie in rankings:
            print(
                f"{movie['rank']:<6}"
                f"{movie['title'][:47] + '...' if len(movie['title']) > 47 else movie['title']:<50}"
                f"{movie['ranking_score']:<10}"
                f"{movie['review_count']:<10}"
                f"{movie['average_sentiment']:<15}"
                f"{movie['total_likes']:<10}"
                f"{movie['total_comments']:<10}"
            )
        
        print("\n" + "=" * 100 + "\n")
        return rankings
        
    except Exception as e:
        logger.error(f"Error ranking movies: {e}")
        raise