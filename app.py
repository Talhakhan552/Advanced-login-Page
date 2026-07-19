from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import jwt
import bcrypt
import hashlib
from datetime import datetime, timedelta
from functools import wraps
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration from .env file
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', 5432))
DB_NAME = os.getenv('DB_NAME', 'login_system')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')

ACCESS_TOKEN_SECRET = os.getenv('ACCESS_TOKEN_SECRET', 'access-secret')
REFRESH_TOKEN_SECRET = os.getenv('REFRESH_TOKEN_SECRET', 'refresh-secret')

print(f"🔌 Connecting to PostgreSQL...")
print(f"   Host: {DB_HOST}:{DB_PORT}")
print(f"   Database: {DB_NAME}")
print(f"   User: {DB_USER}")

# ============ DATABASE FUNCTIONS ============

def get_db_connection():
    """
    Connect to PostgreSQL database
    Returns connection object or None if failed
    """
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return None

def hash_token(token):
    """
    Hash token using SHA256 for secure storage
    Don't store raw tokens in database!
    """
    return hashlib.sha256(token.encode()).hexdigest()

# ============ MIDDLEWARE ============

def token_required(f):
    """
    Middleware to check if user has valid access token
    Extracts user data from JWT and adds to request object
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from Authorization header: "Bearer TOKEN"
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]  # Split "Bearer TOKEN"
            except IndexError:
                return {'message': 'Invalid token format'}, 401
        
        if not token:
            return {'message': 'Token is missing'}, 401
        
        try:
            # Decode JWT token
            data = jwt.decode(token, ACCESS_TOKEN_SECRET, algorithms=['HS256'])
            request.user_id = data['id']
            request.username = data['username']
            request.user_role = data['role']
        except jwt.ExpiredSignatureError:
            return {'message': 'Token has expired'}, 403
        except jwt.InvalidTokenError:
            return {'message': 'Invalid token'}, 403
        
        return f(*args, **kwargs)
    
    return decorated

def role_required(allowed_roles):
    """
    Middleware to check if user has required role
    Example: @role_required(['admin']) or @role_required(['admin', 'moderator'])
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if request.user_role not in allowed_roles:
                return {'message': f'Access denied. Required role: {allowed_roles}'}, 403
            return f(*args, **kwargs)
        return decorated
    return decorator

# ============ HEALTH CHECK ============

@app.route('/health', methods=['GET'])
def health():
    """Test if server is running"""
    return {'status': 'OK', 'message': 'Backend is healthy'}, 200

# ============ AUTHENTICATION ROUTES ============

@app.route('/auth/register', methods=['POST'])
def register():
    """
    Register a new user
    
    Expected JSON:
    {
        "username": "john_doe",
        "email": "john@example.com",
        "password": "secure_password"
    }
    """
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        # Validate input
        if not username or not email or not password:
            return {'message': 'Missing required fields: username, email, password'}, 400
        
        conn = get_db_connection()
        if not conn:
            return {'message': 'Database connection error'}, 500
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # SQL: Check if user already exists
        cur.execute('SELECT id FROM users WHERE username = %s OR email = %s', (username, email))
        if cur.fetchone():
            cur.close()
            conn.close()
            return {'message': 'Username or email already exists'}, 409
        
        # Hash password using bcrypt
        # bcrypt.gensalt(10) = 10 salt rounds (higher = slower but more secure)
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(10)).decode('utf-8')
        
        # SQL: Insert new user into database
        cur.execute(
            'INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, %s) RETURNING id, username, email, role',
            (username, email, password_hash, 'user')
        )
        new_user = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✅ New user registered: {username}")
        return {'message': 'User created successfully', 'user': dict(new_user)}, 201
    
    except Exception as e:
        print(f"❌ Register error: {e}")
        return {'message': 'Server error during registration'}, 500

@app.route('/auth/login', methods=['POST'])
def login():
    """
    Login a user and return JWT tokens
    
    Expected JSON:
    {
        "username": "john_doe",
        "password": "secure_password"
    }
    
    Returns:
    {
        "accessToken": "JWT_TOKEN",
        "refreshToken": "JWT_TOKEN",
        "user": { "id": 1, "username": "john_doe", "email": "...", "role": "user" }
    }
    """
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return {'message': 'Missing username or password'}, 400
        
        conn = get_db_connection()
        if not conn:
            return {'message': 'Database connection error'}, 500
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # SQL: Get user from database
        cur.execute(
            'SELECT id, username, email, password_hash, role FROM users WHERE username = %s',
            (username,)
        )
        user = cur.fetchone()
        
        if not user:
            cur.close()
            conn.close()
            return {'message': 'Invalid credentials'}, 401
        
        # Verify password using bcrypt
        if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            cur.close()
            conn.close()
            return {'message': 'Invalid credentials'}, 401
        
        # Generate ACCESS TOKEN (short-lived: 15 minutes)
        # This token is sent with each request to prove authentication
        access_token = jwt.encode(
            {
                'id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'exp': datetime.utcnow() + timedelta(minutes=15)  # Expires in 15 min
            },
            ACCESS_TOKEN_SECRET,
            algorithm='HS256'
        )
        
        # Generate REFRESH TOKEN (long-lived: 7 days)
        # This token is used to get a new access token when it expires
        refresh_token = jwt.encode(
            {
                'id': user['id'],
                'exp': datetime.utcnow() + timedelta(days=7)  # Expires in 7 days
            },
            REFRESH_TOKEN_SECRET,
            algorithm='HS256'
        )
        
        # SQL: Store refresh token hash in database
        # We store the HASH, not the raw token (for security)
        token_hash = hash_token(refresh_token)
        expires_at = datetime.utcnow() + timedelta(days=7)
        
        cur.execute(
            'INSERT INTO refresh_tokens (user_id, token_hash, expires_at) VALUES (%s, %s, %s)',
            (user['id'], token_hash, expires_at)
        )
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✅ User logged in: {username}")
        return {
            'accessToken': access_token,
            'refreshToken': refresh_token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'role': user['role']
            }
        }, 200
    
    except Exception as e:
        print(f"❌ Login error: {e}")
        return {'message': 'Server error during login'}, 500

@app.route('/auth/refresh', methods=['POST'])
def refresh():
    """
    Get new access token using refresh token
    Called when access token expires (403 response)
    
    Expected JSON:
    {
        "refreshToken": "JWT_TOKEN"
    }
    
    Returns:
    {
        "accessToken": "NEW_JWT_TOKEN"
    }
    """
    try:
        data = request.get_json()
        refresh_token = data.get('refreshToken')
        
        if not refresh_token:
            return {'message': 'Refresh token required'}, 400
        
        # Verify refresh token JWT
        try:
            payload = jwt.decode(refresh_token, REFRESH_TOKEN_SECRET, algorithms=['HS256'])
        except jwt.InvalidTokenError:
            return {'message': 'Invalid refresh token'}, 403
        
        conn = get_db_connection()
        if not conn:
            return {'message': 'Database connection error'}, 500
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # SQL: Check if token is stored and not revoked (logout)
        # We also check that it hasn't expired
        token_hash = hash_token(refresh_token)
        cur.execute(
            'SELECT id FROM refresh_tokens WHERE token_hash = %s AND revoked = FALSE AND expires_at > NOW()',
            (token_hash,)
        )
        
        if not cur.fetchone():
            cur.close()
            conn.close()
            return {'message': 'Invalid or expired refresh token'}, 403
        
        # SQL: Get updated user info
        cur.execute(
            'SELECT id, username, email, role FROM users WHERE id = %s',
            (payload['id'],)
        )
        user = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if not user:
            return {'message': 'User not found'}, 404
        
        # Generate new access token
        new_access_token = jwt.encode(
            {
                'id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'exp': datetime.utcnow() + timedelta(minutes=15)
            },
            ACCESS_TOKEN_SECRET,
            algorithm='HS256'
        )
        
        print(f"✅ Token refreshed for user ID: {user['id']}")
        return {'accessToken': new_access_token}, 200
    
    except Exception as e:
        print(f"❌ Refresh error: {e}")
        return {'message': 'Server error during token refresh'}, 500

@app.route('/auth/logout', methods=['POST'])
@token_required
def logout():
    """
    Logout by revoking refresh token
    Requires valid access token
    
    Expected JSON:
    {
        "refreshToken": "JWT_TOKEN"
    }
    """
    try:
        data = request.get_json()
        refresh_token = data.get('refreshToken')
        
        if not refresh_token:
            return {'message': 'Refresh token required'}, 400
        
        conn = get_db_connection()
        if not conn:
            return {'message': 'Database connection error'}, 500
        
        cur = conn.cursor()
        token_hash = hash_token(refresh_token)
        
        # SQL: Mark token as revoked in database
        # This prevents it from being used to get new access tokens
        cur.execute(
            'UPDATE refresh_tokens SET revoked = TRUE WHERE token_hash = %s',
            (token_hash,)
        )
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✅ User logged out: {request.username}")
        return {'message': 'Logged out successfully'}, 200
    
    except Exception as e:
        print(f"❌ Logout error: {e}")
        return {'message': 'Server error during logout'}, 500

# ============ USER ROUTES ============

@app.route('/auth/me', methods=['GET'])
@token_required
def get_current_user():
    """
    Get current user info
    Requires valid access token in Authorization header
    """
    try:
        conn = get_db_connection()
        if not conn:
            return {'message': 'Database connection error'}, 500
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # SQL: Get user from database by ID (from JWT token)
        cur.execute(
            'SELECT id, username, email, role, created_at FROM users WHERE id = %s',
            (request.user_id,)
        )
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if not user:
            return {'message': 'User not found'}, 404
        
        return dict(user), 200
    
    except Exception as e:
        print(f"❌ Get user error: {e}")
        return {'message': 'Server error'}, 500

@app.route('/users', methods=['GET'])
@token_required
@role_required(['admin'])
def get_all_users():
    """
    Get all users (admin only)
    Requires admin role
    """
    try:
        conn = get_db_connection()
        if not conn:
            return {'message': 'Database connection error'}, 500
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # SQL: Get all users ordered by creation date
        cur.execute('SELECT id, username, email, role, created_at FROM users ORDER BY created_at DESC')
        users = cur.fetchall()
        cur.close()
        conn.close()
        
        return [dict(user) for user in users], 200
    
    except Exception as e:
        print(f"❌ Get users error: {e}")
        return {'message': 'Server error'}, 500

@app.route('/users/<int:user_id>/role', methods=['PUT'])
@token_required
@role_required(['admin'])
def update_user_role(user_id):
    """
    Update a user's role (admin only)
    
    Expected JSON:
    {
        "role": "admin"  # Must be: "user", "admin", or "moderator"
    }
    """
    try:
        data = request.get_json()
        new_role = data.get('role')
        
        # Validate role value
        if new_role not in ['user', 'admin', 'moderator']:
            return {'message': 'Invalid role. Must be: user, admin, or moderator'}, 400
        
        conn = get_db_connection()
        if not conn:
            return {'message': 'Database connection error'}, 500
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # SQL: Update user role in database
        cur.execute(
            'UPDATE users SET role = %s, updated_at = NOW() WHERE id = %s RETURNING id, username, role',
            (new_role, user_id)
        )
        updated_user = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        if not updated_user:
            return {'message': 'User not found'}, 404
        
        print(f"✅ User {user_id} role updated to: {new_role}")
        return dict(updated_user), 200
    
    except Exception as e:
        print(f"❌ Update role error: {e}")
        return {'message': 'Server error'}, 500

# ============ ERROR HANDLERS ============

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return {'message': 'Route not found'}, 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return {'message': 'Internal server error'}, 500

# ============ RUN THE APP ============

if __name__ == '__main__':
    print("🚀 Starting Flask application...")
    print("📖 API running on http://127.0.0.1:5000")
    print("🧪 Test it: curl http://127.0.0.1:5000/health")
    print("⏹️  Press Ctrl+C to stop the server")
    print()
    
    app.run(debug=True, port=5000, host='127.0.0.1')