import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class MovieRecommender:
    def __init__(self, movies_path='movies.csv', ratings_path='ratings.csv'):
        self.movies_path = movies_path
        self.ratings_path = ratings_path
        self.tmdb_api_key = os.getenv('TMDB_API_KEY')
        self.rules = None
        self.movies_df = None
        self.load_data()
        self.train_model()

    def load_data(self):
        """Load and preprocess the dataset."""
        print("Loading data...")
        self.movies_df = pd.read_csv(self.movies_path)
        ratings_df = pd.read_csv(self.ratings_path)

        # 1. Filter ratings >= 4
        high_ratings = ratings_df[ratings_df['rating'] >= 4]

        # 2. Group by userId to create baskets (lists of movieIds)
        # Each user is treated as a transaction
        print("Creating transactions...")
        self.baskets = high_ratings.groupby('userId')['movieId'].apply(list).values.tolist()

    def train_model(self):
        """Apply Apriori algorithm and generate rules."""
        print("Training model (this might take a moment)...")
        
        # 3. Convert baskets into one-hot encoded dataframe
        te = TransactionEncoder()
        te_ary = te.fit(self.baskets).transform(self.baskets)
        df = pd.DataFrame(te_ary, columns=te.columns_)

        # 4. Apply Apriori algorithm
        # Minimum support: 0.01 (1%)
        # Max itemset length: 2
        frequent_itemsets = apriori(df, min_support=0.01, use_colnames=True, max_len=2)

        if frequent_itemsets.empty:
            print("WARNING: No frequent itemsets found with min_support=0.01. Trying 0.005 for demo purposes.")
            frequent_itemsets = apriori(df, min_support=0.005, use_colnames=True, max_len=2)

        # 5. Generate association rules
        # Metric: confidence, Threshold: 1.0 (100%) - Reduced to 0.7 for more variety
        if not frequent_itemsets.empty:
            self.rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=0.7)
            print(f"Generated {len(self.rules)} association rules.")
        else:
            self.rules = pd.DataFrame()
            print("No rules generated based on the specified constraints.")

    def get_recommendations(self, movie_id):
        """
        Input: movieId
        Output: top 5 recommended movieIds
        Logic: IF movieId in antecedents -> return consequents
        """
        if self.rules.empty:
            return []

        # Convert movie_id to int in case it's passed as string
        movie_id = int(movie_id)
        
        # Filter rules where the movie_id is in the antecedents
        # mlxtend antecedents are frozensets
        recommendations = []
        for _, rule in self.rules.iterrows():
            if movie_id in rule['antecedents']:
                # Get the items in the consequents
                for item in rule['consequents']:
                    recommendations.append({
                        'id': int(item),
                        'support': rule['support'],
                        'confidence': rule['confidence']
                    })
        
        # Sort by support (Bonus requirement)
        recommendations = sorted(recommendations, key=lambda x: x['support'], reverse=True)
        
        # Extract just the movie IDs and remove duplicates
        seen = set()
        unique_recs = []
        for rec in recommendations:
            if rec['id'] not in seen and rec['id'] != movie_id:
                unique_recs.append(rec['id'])
                seen.add(rec['id'])
        
        return unique_recs[:5]

    def get_movie_title(self, movie_id):
        """Map movieId -> movie title"""
        try:
            row = self.movies_df[self.movies_df['movieId'] == int(movie_id)]
            if not row.empty:
                return row.iloc[0]['title']
        except:
            pass
        return f"Unknown Movie ({movie_id})"

    def get_all_movies(self):
        """Return list of movies for dropdown"""
        return self.movies_df[['movieId', 'title']].to_dict(orient='records')

    def identify_realtime_movie(self, title):
        """
        Identify a movie from user input (real-time).
        1. Try to find a match in the existing dataset.
        2. If not found, use TMDB API to get real movie info.
        3. Map TMDB genres to local dataset movies and return recommendations.
        """
        title_lower = title.lower()
        
        # 1. Local Fuzzy/Substring match first
        match = self.movies_df[self.movies_df['title'].str.lower().str.contains(title_lower, na=False)]
        
        if not match.empty:
            match['len_diff'] = match['title'].apply(lambda x: abs(len(x) - len(title)))
            best_match = match.sort_values('len_diff').iloc[0]
            movie_id = best_match['movieId']
            rec_ids = self.get_recommendations(movie_id)
            
            recs = []
            for rid in rec_ids:
                recs.append({"id": rid, "title": self.get_movie_title(rid)})
                
            return {
                "matched_title": best_match['title'],
                "recommendations": recs,
                "classification": best_match['genres']
            }
        
        # 2. TMDB API Integration
        try:
            url = f"https://api.themoviedb.org/3/search/movie?api_key={self.tmdb_api_key}&query={title}"
            response = requests.get(url, timeout=5)
            data = response.json()
            
            if data['results']:
                movie = data['results'][0]
                tmdb_title = movie['title']
                poster_path = f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie['poster_path'] else None
                
                # Get genre names from TMDB genre IDs
                # TMDB genre map (Simplified for mapping to local genres)
                tmdb_genre_map = {
                    28: 'Action', 12: 'Adventure', 16: 'Animation', 35: 'Comedy', 
                    80: 'Crime', 99: 'Documentary', 18: 'Drama', 10751: 'Family', 
                    14: 'Fantasy', 36: 'History', 27: 'Horror', 10402: 'Music', 
                    9648: 'Mystery', 10749: 'Romance', 878: 'Sci-Fi', 10770: 'TV Movie', 
                    53: 'Thriller', 10752: 'War', 37: 'Western'
                }
                
                genres = [tmdb_genre_map.get(gid, 'General') for gid in movie['genre_ids']]
                found_genre = "|".join(genres) if genres else "General"
                
                # Find local recommendations based on these genres
                fallback_recs = []
                search_pattern = '|'.join(genres) if genres else "General"
                genre_matches = self.movies_df[self.movies_df['genres'].str.contains(search_pattern, na=False)].sample(min(5, len(self.movies_df)))
                
                for _, row in genre_matches.iterrows():
                    fallback_recs.append({"id": int(row['movieId']), "title": row['title']})
                    
                return {
                    "matched_title": tmdb_title,
                    "recommendations": fallback_recs,
                    "classification": found_genre,
                    "poster": poster_path,
                    "is_realtime": True,
                    "source": "TMDB"
                }
        except Exception as e:
            print(f"TMDB Error: {e}")
            pass

        # 3. Last Resort Fallback (Existing Keyword Logic)
        genre_keywords = {
            'Action': ['war', 'fight', 'kill', 'dark', 'knight', 'die', 'terminator', 'fast', 'furious'],
            'Comedy': ['funny', 'laugh', 'love', 'school', 'story', 'adventure', 'toy'],
            'Horror': ['dead', 'ghost', 'evil', 'blood', 'scary', 'night', 'scream'],
            'Sci-Fi': ['space', 'star', 'alien', 'future', 'robot', 'matrix'],
            'Romance': ['love', 'heart', 'kiss', 'wedding', 'date']
        }
        
        detected_genres = []
        for genre, words in genre_keywords.items():
            if any(word in title_lower for word in words):
                detected_genres.append(genre)
        found_genre = "|".join(detected_genres) if detected_genres else "General"
        
        fallback_recs = []
        sample_movies = self.movies_df.sample(5)
        for _, row in sample_movies.iterrows():
            fallback_recs.append({"id": int(row['movieId']), "title": row['title']})

        return {
            "classification": found_genre,
            "recommendations": fallback_recs,
            "is_realtime": True,
            "source": "Heuristic"
        }

if __name__ == "__main__":
    # Test block
    recommender = MovieRecommender()
    recs = recommender.get_recommendations(1) # Toy Story
    print(f"Recommendations for Toy Story: {recs}")
