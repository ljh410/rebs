from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import mysql.connector
import os
import hashlib
from datetime import datetime
import secrets
from werkzeug.utils import secure_filename
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
socketio = SocketIO(app)

def get_db():
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='jlee48',
            password='OLE_miss2024',
            database='jlee48',
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci',
            autocommit=True
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
        return None

@app.route('/')
def index():
    conn = get_db()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT p.*, u.username, u.is_verified, u.display_name, u.profile_image,
                   (SELECT COUNT(*) FROM likes WHERE post_id = p.id) AS likes_count,
                   EXISTS(SELECT 1 FROM likes WHERE post_id = p.id AND user_id = %s) AS is_liked,
                   EXISTS(SELECT 1 FROM bookmarks WHERE post_id = p.id AND user_id = %s) AS is_bookmarked
            FROM posts p
            JOIN users u ON p.user_id = u.id
            ORDER BY p.created_at DESC
        ''', (session.get('user_id', 0), session.get('user_id', 0)))
        posts = cursor.fetchall()
        
        for post in posts:
            cursor.execute('''
                SELECT c.*, u.username, u.is_verified, u.display_name,
                       (SELECT COUNT(*) FROM replies WHERE comment_id = c.id) AS replies_count
                FROM comments c
                JOIN users u ON c.user_id = u.id
                WHERE c.post_id = %s
                ORDER BY c.created_at
            ''', (post['id'],))
            post['comments'] = cursor.fetchall()
        
        cursor.close()
        conn.close()
        return render_template('index.html', posts=posts)
    return "Database connection error", 500

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()
        email = request.form['email']
        
        conn = get_db()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute('INSERT INTO users (username, password, email) VALUES (%s, %s, %s)',
                             (username, password, email))
                conn.commit()
                flash('Registration successful!')
                return redirect(url_for('login'))
            except mysql.connector.IntegrityError:
                flash('Username or email already exists')
            finally:
                cursor.close()
                conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()
        
        conn = get_db()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s',
                         (username, password))
            user = cursor.fetchone()
            
            if user:
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['is_verified'] = user['is_verified']
                flash('Login successful!')
                cursor.close()
                conn.close()
                return redirect(url_for('index'))
            
            flash('Invalid credentials')
            cursor.close()
            conn.close()
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/post', methods=['POST'])
def create_post():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    content = request.form['content']
    media = request.files.get('media')
    media_path = None
    
    if media and media.filename:
        filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{media.filename}")
        media_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        media.save(media_path)
    
    conn = get_db()
    if conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO posts (user_id, content, media_path) VALUES (%s, %s, %s)',
                      (session['user_id'], content, media_path))
        conn.commit()
        
        if session.get('is_verified'):
            cursor.execute('''
                SELECT u.email FROM subscriptions s
                JOIN users u ON s.subscriber_id = u.id
                WHERE s.creator_id = %s
            ''', (session['user_id'],))
            subscribers = cursor.fetchall()
            
            for sub in subscribers:
                send_notification_email(sub[0], content)
        
        cursor.close()
        conn.close()
    return redirect(url_for('index'))

@app.route('/post/<int:post_id>', methods=['PUT', 'DELETE'])
def manage_post(post_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    conn = get_db()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM posts WHERE id = %s AND user_id = %s',
                      (post_id, session['user_id']))
        post = cursor.fetchone()
        
        if not post:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Not found'}), 404
            
        if request.method == 'DELETE':
            cursor.execute('DELETE FROM posts WHERE id = %s', (post_id,))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True})
            
        content = request.json.get('content')
        cursor.execute('UPDATE posts SET content = %s WHERE id = %s', (content, post_id))
        conn.commit()
        cursor.close()
        conn.close()
        
    return jsonify({'success': True})

@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)
    emit('status', {'msg': f"{session.get('username')} has joined the room."}, room=room)

@socketio.on('leave')
def on_leave(data):
    room = data['room']
    leave_room(room)
    emit('status', {'msg': f"{session.get('username')} has left the room."}, room=room)

@socketio.on('message')
def handle_message(data):
    room = data['room']
    message = data['message']
    
    conn = get_db()
    if conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO messages (room_name, user_id, content) VALUES (%s, %s, %s)',
                      (room, session['user_id'], message))
        conn.commit()
        cursor.close()
        conn.close()
        
        emit('message', {
            'user': session.get('username'),
            'message': message,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, room=room)

def send_notification_email(to_email, content):
    msg = MIMEText(f"New post from someone you follow:\n\n{content}")
    msg['Subject'] = 'New Post Notification'
    msg['From'] = 'notifications@rebs.com'
    msg['To'] = to_email
    
    with smtplib.SMTP('localhost', 1025) as server:
        server.send_message(msg)

if __name__ == "__main__":
    socketio.run(app, host='127.0.0.1', port=5001)