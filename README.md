# CineMatch | Apriori Movie Recommendation System

CineMatch is a premium movie recommendation engine that combines classical association rule mining with modern real-time data classification. It uses the **Apriori Algorithm** to find deep connections between movies based on user ratings and integrates the **TMDB API** for identifying new, real-time releases.

## 🌟 Features

- **Apriori Recommendation Engine**: Analyzes over 100,000+ ratings to generate association rules (If you like X, you'll love Y).
- **TMDB Real-time Identification**: Search for *any* movie in existence. Even if it's not in our dataset, the system uses TMDB to classify its genre and provide matches.
- **Premium Dashboard**: A sleek, high-performing UI built with Glassmorphism, smooth animations, and responsive side-navigation.
- **User Authentication**: Secure login and signup system with encrypted passwords using Flask-Bcrypt.
- **Persistent History**: Track your discovery journey. Every recommendation you get is saved to your personal dashboard.
- **Visual Results**: Fetches official movie posters and metadata in real-time.

## 🛠️ Technology Stack

- **Backend**: Flask (Python)
- **Database**: SQLite (SQLAlchemy)
- **Algorithm**: Apriori (mlxtend)
- **Data**: Pandas
- **API**: The Movie Database (TMDB)
- **Frontend**: Vanilla HTML/CSS/JS (Modern Design System)

## 🚀 Getting Started

Follow these instructions to get a copy of the project up and running on your local machine.

### Prerequisites

- Python 3.8 or higher
- A TMDB API Key (Optional but recommended for real-time search)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/movie-recommendation-system.git
   cd movie-recommendation-system
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **TMDB Configuration**:
   Open `model.py` and replace `self.tmdb_api_key` with your actual API key:
   ```python
   self.tmdb_api_key = 'your_api_key_here'
   ```

5. **Run the application**:
   ```bash
   python app.py
   ```

6. **Access the App**:
   Navigate to `http://127.0.0.1:5000` in your browser.

## 📂 Project Structure

- `app.py`: Flask application routes and database models.
- `model.py`: Core logic for Apriori algorithm and TMDB API integration.
- `movies.csv` & `ratings.csv`: MovieLens dataset (Small).
- `static/`: CSS styles and frontend assets.
- `templates/`: HTML templates for Dashboard, Auth, and Landing page.


## ✨ Acknowledgments

- Dataset provided by [MovieLens](https://grouplens.org/datasets/movielens/).
- API services by [TMDB](https://www.themoviedb.org/).
