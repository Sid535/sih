from flask import Flask, render_template, jsonify
import random
import threading
import time
import datetime

app = Flask(__name__)

# Simulated bus data for Amritsar: list of buses with id, name, route_id, and location (latitude, longitude)
buses = [
    {"id": 1, "name": "Bus 101", "route_id": 1, "lat": 31.6330, "lng": 74.8720, "crowdedness": random.randint(0,100)},
    {"id": 2, "name": "Bus 102", "route_id": 1, "lat": 31.6350, "lng": 74.8740, "crowdedness": random.randint(0,100)},
    {"id": 3, "name": "Bus 103", "route_id": 2, "lat": 31.6200, "lng": 74.8765, "crowdedness": random.randint(0,100)},
    {"id": 4, "name": "Bus 104", "route_id": 2, "lat": 31.6220, "lng": 74.8780, "crowdedness": random.randint(0,100)},
    {"id": 5, "name": "Bus 105", "route_id": 3, "lat": 31.6150, "lng": 74.8800, "crowdedness": random.randint(0,100)},
    {"id": 6, "name": "Bus 106", "route_id": 3, "lat": 31.6170, "lng": 74.8820, "crowdedness": random.randint(0,100)},
    {"id": 7, "name": "Bus 107", "route_id": 1, "lat": 31.6300, "lng": 74.8700, "crowdedness": random.randint(0,100)},
    {"id": 8, "name": "Bus 108", "route_id": 2, "lat": 31.6250, "lng": 74.8750, "crowdedness": random.randint(0,100)},
    {"id": 9, "name": "Bus 109", "route_id": 3, "lat": 31.6120, "lng": 74.8830, "crowdedness": random.randint(0,100)},
    {"id": 10, "name": "Bus 110", "route_id": 1, "lat": 31.6280, "lng": 74.8680, "crowdedness": random.randint(0,100)},
]

# Routes data
routes = [
    {"id": 1, "name": "Railway Station to Golden Temple", "color": "#00FF00"},
    {"id": 2, "name": "Bus Stand to Jallianwala Bagh", "color": "#0000FF"},
    {"id": 3, "name": "Airport to City Center", "color": "#FF0000"},
]

# Stops data
stops = [
    {"id": 1, "name": "Amritsar Railway Station", "lat": 31.6330, "lng": 74.8720, "route_ids": [1]},
    {"id": 2, "name": "Golden Temple", "lat": 31.6200, "lng": 74.8765, "route_ids": [1, 2]},
    {"id": 3, "name": "Jallianwala Bagh", "lat": 31.6205, "lng": 74.8800, "route_ids": [2]},
    {"id": 4, "name": "Bus Stand", "lat": 31.6350, "lng": 74.8740, "route_ids": [2]},
    {"id": 5, "name": "Sri Guru Ram Das Ji International Airport", "lat": 31.7050, "lng": 74.8000, "route_ids": [3]},
    {"id": 6, "name": "City Center", "lat": 31.6150, "lng": 74.8800, "route_ids": [3]},
]

# Schedules data (simplified)
schedules = [
    {"route_id": 1, "times": ["06:00", "07:00", "08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00"]},
    {"route_id": 2, "times": ["06:30", "07:30", "08:30", "09:30", "10:30", "11:30", "12:30", "13:30", "14:30", "15:30", "16:30", "17:30", "18:30", "19:30", "20:30"]},
    {"route_id": 3, "times": ["05:00", "06:00", "07:00", "08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00"]},
]

# Fares data (simplified, per route)
fares = [
    {"route_id": 1, "fare": 20},  # INR
    {"route_id": 2, "fare": 25},
    {"route_id": 3, "fare": 30},
]

# Traffic data (simulated segments)
traffic = [
    {"route_id": 1, "start_lat": 31.6330, "start_lng": 74.8720, "end_lat": 31.6200, "end_lng": 74.8765, "delay_minutes": 5},
    {"route_id": 2, "start_lat": 31.6350, "start_lng": 74.8740, "end_lat": 31.6205, "end_lng": 74.8800, "delay_minutes": 10},
    {"route_id": 3, "start_lat": 31.7050, "start_lng": 74.8000, "end_lat": 31.6150, "end_lng": 74.8800, "delay_minutes": 15},
]

def update_bus_locations():
    while True:
        for bus in buses:
            # Randomly move bus location slightly to simulate movement
            bus["lat"] += random.uniform(-0.0005, 0.0005)
            bus["lng"] += random.uniform(-0.0005, 0.0005)
            # Update crowdedness randomly
            bus["crowdedness"] = random.randint(0, 100)
        time.sleep(5)  # update every 5 seconds

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/buses')
def get_buses():
    return jsonify(buses)

@app.route('/api/routes')
def get_routes():
    return jsonify(routes)

@app.route('/api/stops')
def get_stops():
    return jsonify(stops)

@app.route('/api/schedules')
def get_schedules():
    return jsonify(schedules)

# New API endpoint for fares
@app.route('/api/fares')
def get_fares():
    return jsonify(fares)

# New API endpoint for traffic
@app.route('/api/traffic')
def get_traffic():
    return jsonify(traffic)

# Helper function to parse time string to datetime.time
def parse_time(t_str):
    return datetime.datetime.strptime(t_str, "%H:%M").time()

# Helper function to calculate estimated arrival time in minutes from now
def estimate_arrival(route_id, current_time):
    # Find next scheduled time for the route after current_time
    schedule = next((s for s in schedules if s["route_id"] == route_id), None)
    if not schedule:
        return None
    now = current_time
    for t_str in schedule["times"]:
        sched_time = parse_time(t_str)
        if sched_time >= now:
            delta = datetime.datetime.combine(datetime.date.today(), sched_time) - datetime.datetime.combine(datetime.date.today(), now)
            return int(delta.total_seconds() / 60)
    # If no future time, return time to first schedule next day
    first_sched = parse_time(schedule["times"][0])
    delta = datetime.datetime.combine(datetime.date.today() + datetime.timedelta(days=1), first_sched) - datetime.datetime.combine(datetime.date.today(), now)
    return int(delta.total_seconds() / 60)

# New API endpoint for bus details
@app.route('/api/bus_details/<int:bus_id>')
def get_bus_details(bus_id):
    bus = next((b for b in buses if b["id"] == bus_id), None)
    if not bus:
        return jsonify({"error": "Bus not found"}), 404
    current_time = datetime.datetime.now().time()
    arrival_time = estimate_arrival(bus["route_id"], current_time)
    # Find final stop for the route
    route_stops = [stop for stop in stops if bus["route_id"] in stop["route_ids"]]
    final_stop = route_stops[-1]["name"] if route_stops else "Unknown"
    # Find closest stop (simplified as first stop for demo)
    closest_stop = route_stops[0]["name"] if route_stops else "Unknown"
    return jsonify({
        "id": bus["id"],
        "name": bus["name"],
        "current_location": {"lat": bus["lat"], "lng": bus["lng"]},
        "crowdedness": bus.get("crowdedness", 0),
        "estimated_arrival_minutes": arrival_time,
        "closest_stop": closest_stop,
        "final_stop": final_stop,
        "fare": next((f["fare"] for f in fares if f["route_id"] == bus["route_id"]), None)
    })

if __name__ == '__main__':
    # Start background thread to update bus locations
    thread = threading.Thread(target=update_bus_locations)
    thread.daemon = True
    thread.start()
    app.run(debug=True)
