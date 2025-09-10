from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import random
import sqlite3
import time

app = Flask(__name__)
app.secret_key = 'your-secret-key'

# --- START: NEW - In-memory state for bus simulation ---
# This dictionary will store the current progress of each bus.
# Format: { bus_id: {'segment_index': 0, 'fraction': 0.0} }
bus_simulation_state = {}
# --- END: NEW ---

# Database connection
def get_db_connection():
    conn = sqlite3.connect('database.db', check_same_thread=False) # Added check_same_thread for state management
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
        CREATE TABLE IF NOT EXISTS route_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_name TEXT NOT NULL,
            point_order INTEGER NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL
        );
    ''')
    # Sample bus data
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM buses")
    if cur.fetchone()[0] == 0:
        conn.executescript('''
            INSERT INTO buses (id, route, departure_time, seats_available)
            VALUES (1, 'Bangalore-Chennai', '2025-09-11 08:00', 30),
                   (2, 'Chennai-Bangalore', '2025-09-11 10:00', 25);
            
            -- START: SAMPLE ROUTE DATA --
            -- Points for Bangalore to Chennai
            INSERT INTO route_points (route_name, point_order, latitude, longitude) VALUES
            ('Bangalore-Chennai', 1, 12.9716, 77.5946), -- Bangalore
            ('Bangalore-Chennai', 2, 12.9141, 77.9944), -- Hosur
            ('Bangalore-Chennai', 3, 12.6935, 78.4839), -- Vellore
            ('Bangalore-Chennai', 4, 13.0827, 80.2707); -- Chennai

            -- Points for Chennai to Bangalore (reverse)
            INSERT INTO route_points (route_name, point_order, latitude, longitude) VALUES
            ('Chennai-Bangalore', 1, 13.0827, 80.2707), -- Chennai
            ('Chennai-Bangalore', 2, 12.6935, 78.4839), -- Vellore
            ('Chennai-Bangalore', 3, 12.9141, 77.9944), -- Hosur
            ('Chennai-Bangalore', 4, 12.9716, 77.5946); -- Bangalore
            -- END: SAMPLE ROUTE DATA --
        ''')
    conn.commit()
    conn.close()

init_db()

# Homepage with bus search
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        from_city = request.form['from_city'].strip()
        to_city = request.form['to_city'].strip()
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
    
    # Fetch the location row
    location_row = conn.execute('SELECT * FROM bus_locations WHERE bus_id = ?', (bus_id,)).fetchone()
    
    # Convert the sqlite3.Row object to a dictionary, or None if no location exists
    location = dict(location_row) if location_row else None
    
    # Fetch all points for the bus's route
    route_points_raw = conn.execute(
        'SELECT latitude, longitude FROM route_points WHERE route_name = ? ORDER BY point_order',
        (bus['route'],)
    ).fetchall()
    
    # Convert the raw points into a list of [lat, lng] lists for JavaScript
    route_points = [[point['latitude'], point['longitude']] for point in route_points_raw]
    
    conn.close()
    
    # Pass the bus, its location, and the route path to the template
    return render_template('tracking.html', bus=bus, location=location, route_points=route_points)

# Bus location simulation with progressive movement
@app.route('/update_location/<int:bus_id>')
def update_location(bus_id):
    global bus_simulation_state
    
    # Initialize state for the bus if it's not already being tracked
    if bus_id not in bus_simulation_state:
        bus_simulation_state[bus_id] = {
            "segment_index": 0,
            "fraction": 0.0
        }

    state = bus_simulation_state[bus_id]
    
    conn = get_db_connection()
    bus = conn.execute('SELECT * FROM buses WHERE id = ?', (bus_id,)).fetchone()
    
    points_raw = conn.execute(
        'SELECT latitude, longitude FROM route_points WHERE route_name = ? ORDER BY point_order', 
        (bus['route'],)
    ).fetchall()
    points = [[p['latitude'], p['longitude']] for p in points_raw]

    if len(points) > 1:
        # --- SPEED CONTROL ---
        # Increase for a faster bus, decrease for a slower bus.
        # This is the percentage of a route segment to travel per update.
        step = 0.1  # (i.e., 10% of the segment)
        #To make the bus move slower (cover less distance at once), make the step value smaller (e.g., step = 0.05).
        #To make it move faster, make the step value larger (e.g., step = 0.2).
        
        # Move the bus forward by the step amount
        state['fraction'] += step
        
        # If bus completes a segment, move to the next one
        if state['fraction'] >= 1.0:
            state['fraction'] = 0.0
            state['segment_index'] += 1
            
            # If bus completes the whole route, loop back to the start (for demo)
            if state['segment_index'] >= len(points) - 1:
                state['segment_index'] = 0

        # Get the current segment's start and end points
        current_segment = state['segment_index']
        start_point = points[current_segment]
        end_point = points[current_segment + 1]

        # Calculate the new position based on progress (fraction)
        fraction = state['fraction']
        lat = start_point[0] + (end_point[0] - start_point[0]) * fraction
        lng = start_point[1] + (end_point[1] - start_point[1]) * fraction

    else: # Fallback for routes with less than 2 points
        lat = points[0][0] if points else 12.9716
        lng = points[0][1] if points else 77.5946

    # Update the database with the new location
    conn.execute(
        'INSERT OR REPLACE INTO bus_locations (bus_id, latitude, longitude, last_updated) VALUES (?, ?, ?, ?)',
        (bus_id, lat, lng, int(time.time()))
    )
    conn.commit()
    conn.close()
    
    return jsonify({'latitude': lat, 'longitude': lng})

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
    session.pop('user_id', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)