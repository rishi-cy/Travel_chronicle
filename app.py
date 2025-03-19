from flask import Flask, render_template, request, redirect, session, jsonify, url_for
from flask_session import Session
import os
import json
import requests
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from datetime import timedelta, datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Set a strong secret key from environment variable
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))

# Session configuration
app.config.update(
    SESSION_TYPE='filesystem',
    SESSION_FILE_DIR='flask_session',
    SESSION_FILE_THRESHOLD=100,
    SESSION_FILE_MODE=0o600,
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=False,  # Set to False for local development
    SESSION_COOKIE_SAMESITE='Lax',
    MAX_CONTENT_LENGTH=int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB max file size
)

# Create session directory if it doesn't exist
os.makedirs('flask_session', exist_ok=True)

# Initialize Flask-Session
Session(app)

# Upload folder for images
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'static/uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Database file for storing locations
DATABASE_FILE = 'locations.json'
if not os.path.exists(DATABASE_FILE):
    with open(DATABASE_FILE, 'w') as db:
        json.dump([], db)

# User credentials stored in a file
USERS_FILE = 'users.json'
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w') as users_file:
        json.dump({}, users_file)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_password(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not any(char.isdigit() for char in password):
        return False, "Password must contain at least one number"
    if not any(char.isupper() for char in password):
        return False, "Password must contain at least one uppercase letter"
    return True, "Password is valid"

# OpenStreetMap Nominatim API URL
GEOCODING_API_URL = "https://nominatim.openstreetmap.org/search"

@app.route('/')
def home():
    return "Hello, Render!"

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration."""
    if request.method == 'GET':
        return render_template('register.html')
    elif request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            confirm_password = request.form.get('confirm_password', '').strip()

            print(f"Registration attempt for username: {username}")  # Debug log

            # Basic validation
            if not username or not password or not confirm_password:
                print("Registration failed: Empty fields")  # Debug log
                return render_template('register.html', error="Please fill in all fields")

            if password != confirm_password:
                print("Registration failed: Passwords don't match")  # Debug log
                return render_template('register.html', error="Passwords do not match")

            # Validate password
            is_valid, message = validate_password(password)
            if not is_valid:
                print(f"Registration failed: {message}")  # Debug log
                return render_template('register.html', error=message)

            # Load existing users
            try:
                if os.path.exists(USERS_FILE):
                    with open(USERS_FILE, 'r') as users_file:
                        users = json.load(users_file)
                        print(f"Loaded existing users: {list(users.keys())}")  # Debug log
                else:
                    print("Users file does not exist, creating new one")  # Debug log
                    users = {}
            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"Error loading users file: {str(e)}")  # Debug log
                users = {}

            if username in users:
                print(f"Registration failed: Username {username} already exists")  # Debug log
                return render_template('register.html', error="Username already exists. Please choose another.")

            # Hash password before storing
            try:
                hashed_password = generate_password_hash(password)
                users[username] = hashed_password
                
                # Save updated users
                with open(USERS_FILE, 'w') as users_file:
                    json.dump(users, users_file, indent=4)
                print(f"Successfully registered user: {username}")  # Debug log
            except Exception as e:
                print(f"Error saving user data: {str(e)}")  # Debug log
                return render_template('register.html', error="Error saving user data. Please try again.")

            # Auto-login after successful registration
            try:
                session.clear()  # Clear any existing session data
                session['username'] = username
                session.permanent = True
                print(f"Session created for user: {username}")  # Debug log
                return redirect('/map')
            except Exception as e:
                print(f"Error creating session: {str(e)}")  # Debug log
                return render_template('register.html', error="Registration successful but login failed. Please try logging in manually.")

        except Exception as e:
            print(f"Registration error: {str(e)}")  # Debug log
            return render_template('register.html', error="An error occurred during registration. Please try again.")

@app.route('/login', methods=['POST'])
def login_user():
    """Authenticate the user."""
    try:
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        print(f"Login attempt for username: {username}")  # Debug log

        if not username or not password:
            print("Login failed: Empty username or password")  # Debug log
            return render_template('login.html', error="Please fill in all fields")

        # Load existing users
        try:
            if not os.path.exists(USERS_FILE):
                print("Users file not found")  # Debug log
                return render_template('login.html', error="System error. Please try again later.")

            with open(USERS_FILE, 'r') as users_file:
                users = json.load(users_file)
                print(f"Loaded users: {list(users.keys())}")  # Debug log

        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading users file: {str(e)}")  # Debug log
            return render_template('login.html', error="System error. Please try again later.")

        if username not in users:
            print(f"Login failed: Username {username} not found")  # Debug log
            return render_template('login.html', error="Invalid username or password")

        stored_password = users[username]
        if check_password_hash(stored_password, password):
            print(f"Login successful for user: {username}")  # Debug log
            session.clear()
            session['username'] = username
            session.permanent = True
            print(f"Session created: {session.get('username')}")  # Debug log
            return redirect('/map')  # Redirect to the map page
        else:
            print(f"Login failed: Invalid password for user {username}")  # Debug log
            return render_template('login.html', error="Invalid username or password")

    except Exception as e:
        print(f"Login error: {str(e)}")  # Debug log
        return render_template('login.html', error="An error occurred. Please try again.")

@app.route('/logout')
def logout():
    """Log out the current user."""
    session.clear()
    return redirect('/')

@app.route('/map')
def map_page():
    """Load the map page with existing locations."""
    if 'username' not in session:
        print("No username in session, redirecting to login")  # Debug log
        return redirect('/')
    
    print(f"User {session['username']} accessing map page")  # Debug log
    try:
        with open(DATABASE_FILE, 'r') as db:
            locations = json.load(db)
            print(f"Loaded {len(locations)} locations")  # Debug log
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading locations: {str(e)}")  # Debug log
        locations = []

    user_locations = [loc for loc in locations if loc.get('user') == session['username']]
    print(f"Found {len(user_locations)} locations for user {session['username']}")  # Debug log
    return render_template('map.html', locations=user_locations)

@app.route('/upload_location', methods=['POST'])
def upload_location():
    """Save user input (name, description, experience, coordinates, and images)."""
    if 'username' not in session:
        return jsonify({"error": "User not logged in"}), 401

    try:
        name = request.form.get('name')
        description = request.form.get('description')
        experience = request.form.get('experience')
        latitude = float(request.form.get('latitude', 0))
        longitude = float(request.form.get('longitude', 0))

        if not all([name, description, experience]):
            return jsonify({"error": "Missing required fields"}), 400

        # Save uploaded images with validation
        pictures = []
        for file in request.files.getlist('pictures'):
            if file and allowed_file(file.filename):
                try:
                    # Create a unique filename using timestamp and original name
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    original_filename = secure_filename(file.filename)
                    filename = f"{timestamp}_{original_filename}"
                    
                    filepath = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(filepath)
                    
                    # Store the relative URL path
                    picture_url = url_for('static', filename=f'uploads/{filename}')
                    pictures.append(picture_url)
                except Exception as e:
                    print(f"Error saving file {filename}: {e}")
                    continue

        # Store location data
        location_data = {
            "user": session['username'],
            "name": name,
            "description": description,
            "experience": experience,
            "latitude": latitude,
            "longitude": longitude,
            "pictures": pictures
        }

        with open(DATABASE_FILE, 'r+') as db:
            locations = json.load(db)
            locations.append(location_data)
            db.seek(0)
            db.truncate()
            json.dump(locations, db, indent=4)

        # Return success response with the saved picture URLs
        return jsonify({
            "success": True,
            "message": "Location saved successfully",
            "pictures": pictures
        })

    except Exception as e:
        print(f"Error saving location: {e}")
        return jsonify({"error": "Failed to save location"}), 500

@app.route('/get_coordinates', methods=['GET', 'POST'])
def get_coordinates():
    """Return coordinates for a given place name using the OpenStreetMap Nominatim API."""
    if request.method == 'GET':
        place_name = request.args.get('place_name')
    else:
        place_name = request.json.get('place_name')

    if not place_name:
        return jsonify({"error": "Place name is required"}), 400

    try:
        params = {
            "q": place_name,
            "format": "json",
            "limit": 1,
            "addressdetails": 1
        }

        headers = {
            "User-Agent": "TravelChronicle/1.0",
            "Accept-Language": "en-US,en;q=0.9"
        }

        print(f"Searching for location: {place_name}")  # Debug log
        response = requests.get(GEOCODING_API_URL, params=params, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"API Error: Status {response.status_code}")  # Debug log
            return jsonify({"error": "Failed to contact geocoding service"}), response.status_code

        results = response.json()
        print(f"API Response: {results}")  # Debug log

        if not results:
            return jsonify({"error": f"No results found for '{place_name}'"}), 404

        # Extract the first result's coordinates and address
        data = results[0]
        result = {
            "latitude": float(data["lat"]),
            "longitude": float(data["lon"]),
            "address": data.get("display_name", "Unknown location")
        }
        print(f"Found coordinates: {result}")  # Debug log
        return jsonify(result)

    except requests.exceptions.Timeout:
        print("API Timeout")  # Debug log
        return jsonify({"error": "Search request timed out. Please try again."}), 504
    except requests.exceptions.RequestException as e:
        print(f"Request error: {str(e)}")  # Debug log
        return jsonify({"error": "Failed to search location. Please try again."}), 500
    except Exception as e:
        print(f"Unexpected error: {str(e)}")  # Debug log
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500

@app.route('/remove_marker', methods=['POST'])
def remove_marker():
    if 'username' not in session:
        return jsonify({"error": "User not logged in"}), 401

    try:
        data = request.json
        latitude = data.get('latitude')
        longitude = data.get('longitude')

        if latitude is None or longitude is None:
            return jsonify({"error": "Latitude and longitude are required"}), 400

        with open(DATABASE_FILE, 'r+') as db:
            locations = json.load(db)
            original_length = len(locations)
            locations = [loc for loc in locations if not (
                loc['latitude'] == latitude and 
                loc['longitude'] == longitude and 
                loc['user'] == session['username']
            )]
            
            if len(locations) == original_length:
                return jsonify({"error": "Marker not found"}), 404

            db.seek(0)
            db.truncate()
            json.dump(locations, db, indent=4)

        return jsonify({"success": True, "message": "Marker removed successfully"})
    except Exception as e:
        print(f"Error removing marker: {e}")
        return jsonify({"error": "Failed to remove marker"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)  # Ensure debug=False for production
