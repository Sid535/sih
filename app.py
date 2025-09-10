from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import time

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Replace with a secure key in production

# Database connection
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Initialize database
def init_db():
    conn = get_db_connection()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS buses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route TEXT NOT NULL,
            departure_time TEXT NOT NULL,
            seats_available INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            bus_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (bus_id) REFERENCES buses(id)
        );
        CREATE TABLE IF NOT EXISTS bus_locations (
            bus_id INTEGER,
            latitude REAL,
            longitude REAL,
            last_updated INTEGER,
            FOREIGN KEY (bus_id) REFERENCES buses(id)
        );
    ''')
    # Sample bus data
    conn.executescript('''
        INSERT OR IGNORE INTO buses (route, departure_time, seats_available)
        VALUES ('Bangalore-Chennai', '2025-09-11 08:00', 30),
               ('Chennai-Bangalore', '2025-09-11 10:00', 25);
    ''')
    conn.commit()
    conn.close()

init_db()

# Homepage with bus search
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        from_city = request.form['from_city']
        to_city = request.form['to_city']
        conn = get_db_connection()
        buses = conn.execute(
            'SELECT * FROM buses WHERE route LIKE ?', (f'{from_city}-{to_city}',)
        ).fetchall()
        conn.close()
        return render_template('index.html', buses=buses)
    return render_template('index.html', buses=[])

# User registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('register.html', error="Username already exists")
        finally:
            conn.close()
    return render_template('register.html', error=None)

# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE username = ? AND password = ?', (username, password)
        ).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            return redirect(url_for('index'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html', error=None)

# Book a ticket
@app.route('/book/<int:bus_id>', methods=['GET', 'POST'])
def book(bus_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        conn = get_db_connection()
        bus = conn.execute('SELECT * FROM buses WHERE id = ?', (bus_id,)).fetchone()
        if bus and bus['seats_available'] > 0:
            conn.execute(
                'INSERT INTO bookings (user_id, bus_id) VALUES (?, ?)', (session['user_id'], bus_id)
            )
            conn.execute(
                'UPDATE buses SET seats_available = seats_available - 1 WHERE id = ?', (bus_id,)
            )
            conn.commit()
            conn.close()
            return redirect(url_for('booking_confirmation', bus_id=bus_id))
        conn.close()
        return render_template('booking.html', error="No seats available", bus=bus)
    conn = get_db_connection()
    bus = conn.execute('SELECT * FROM buses WHERE id = ?', (bus_id,)).fetchone()
    conn.close()
    return render_template('booking.html', bus=bus, error=None)

# Booking confirmation
@app.route('/booking_confirmation/<int:bus_id>')
def booking_confirmation(bus_id):
    conn = get_db_connection()
    bus = conn.execute('SELECT * FROM buses WHERE id = ?', (bus_id,)).fetchone()
    conn.close()
    return render_template('booking.html', bus=bus, confirmation=True)

# Live tracking
@app.route('/track/<int:bus_id>')
def track(bus_id):
    conn = get_db_connection()
    bus = conn.execute('SELECT * FROM buses WHERE id = ?', (bus_id,)).fetchone()
    location = conn.execute('SELECT * FROM bus_locations WHERE bus_id = ?', (bus_id,)).fetchone()
    conn.close()
    return render_template('tracking.html', bus=bus, location=location)

# Simulate bus location updates (for demo)
@app.route('/update_location/<int:bus_id>')
def update_location(bus_id):
    import random
    latitude = 12.9716 + random.uniform(-0.1, 0.1)  # Around Bangalore
    longitude = 77.5946 + random.uniform(-0.1, 0.1)
    conn = get_db_connection()
    conn.execute(
        'INSERT OR REPLACE INTO bus_locations (bus_id, latitude, longitude, last_updated) VALUES (?, ?, ?, ?)',
        (bus_id, latitude, longitude, int(time.time()))
    )
    conn.commit()
    conn.close()
    return jsonify({'latitude': latitude, 'longitude': longitude})

# Admin panel
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        route = request.form['route']
        departure_time = request.form['departure_time']
        seats = request.form['seats']
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO buses (route, departure_time, seats_available) VALUES (?, ?, ?)',
            (route, departure_time, seats)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))
    conn = get_db_connection()
    buses = conn.execute('SELECT * FROM buses').fetchall()
    conn.close()
    return render_template('admin.html', buses=buses)

# Logout route
@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Remove user_id from session
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)