from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from model import MovieRecommender
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-key-for-dev')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///cine_match.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Initialize the recommender
recommender = MovieRecommender(movies_path='movies.csv', ratings_path='ratings.csv')

# --- Database Models ---

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    history = db.relationship('RecommendationHistory', backref='user', lazy=True)

class RecommendationHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    movie_title = db.Column(db.String(200), nullable=False)
    recommendations = db.Column(db.Text, nullable=False) # Stored as comma-separated string
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Routes ---

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        user_exists = User.query.filter((User.username == username) | (User.email == email)).first()
        if user_exists:
            flash('Username or Email already exists!', 'danger')
            return redirect(url_for('signup'))
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Login unsuccessful. Please check email and password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    movies = recommender.get_all_movies()
    return render_template('dashboard.html', movies=movies, user=current_user)

@app.route('/recommend')
@login_required
def recommend():
    movie_id = request.args.get('movie_id')
    movie_title_input = request.args.get('title')
    
    if not movie_id and not movie_title_input:
        return jsonify({"error": "No movie provided"}), 400
    
    try:
        recommendations = []
        root_title = ""

        if movie_id:
            movie_id = int(movie_id)
            rec_ids = recommender.get_recommendations(movie_id)
            root_title = recommender.get_movie_title(movie_id)
            for rid in rec_ids:
                recommendations.append({
                    "id": rid,
                    "title": recommender.get_movie_title(rid)
                })
        elif movie_title_input:
            # Real-time data classification/identification fallback
            root_title = movie_title_input
            res = recommender.identify_realtime_movie(movie_title_input)
            recommendations = res['recommendations']
            # If we found a real movie match, use its title
            if 'matched_title' in res:
                root_title = res['matched_title']

        # Save to history
        if recommendations:
            rec_titles = ", ".join([r['title'] for r in recommendations])
            history_entry = RecommendationHistory(
                user_id=current_user.id,
                movie_title=root_title,
                recommendations=rec_titles
            )
            db.session.add(history_entry)
            db.session.commit()
            
        return jsonify({
            "root_movie": root_title,
            "recommendations": recommendations,
            "classification": res.get('classification', 'General') if movie_title_input else 'Dataset'
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/history')
@login_required
def get_history():
    history = RecommendationHistory.query.filter_by(user_id=current_user.id).order_by(RecommendationHistory.timestamp.desc()).all()
    return jsonify([{
        "id": h.id,
        "movie_title": h.movie_title,
        "recommendations": h.recommendations,
        "timestamp": h.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    } for h in history])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
