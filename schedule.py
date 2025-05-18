from flask import Flask, jsonify, request
from flask_cors import CORS
from collections import defaultdict, deque
import time
import threading
import random
import math

app = Flask(__name__)
CORS(app)

# Constants
LANE_LENGTH = 100
VEHICLE_SPEED = 15
INTERSECTION_SIZE = 20

simulation_state = {
    'lights': {
        'north': 'red',
        'south': 'red',
        'east': 'green',
        'west': 'green'
    },
    'vehicles': {
        'queued': defaultdict(deque),
        'active': {}
    },
    'next_id': 1,
    'stop_distance': INTERSECTION_SIZE
}

class Vehicle:
    def __init__(self, vid, vtype, origin, destination):
        self.id = vid
        self.type = vtype
        self.origin = origin
        self.destination = destination
        self.position = self.get_spawn_position()
        self.target_position = self.get_approach_point()
        self.speed = VEHICLE_SPEED
        self.stopped = False
        self.has_entered = False
        self.has_exited = False

    def get_spawn_position(self):
        return {
            'north': (0, LANE_LENGTH),
            'south': (0, -LANE_LENGTH),
            'east': (LANE_LENGTH, 0),
            'west': (-LANE_LENGTH, 0)
        }.get(self.origin, (0, 0))

    def get_approach_point(self):
        return {
            'north': (0, INTERSECTION_SIZE),
            'south': (0, -INTERSECTION_SIZE),
            'east': (INTERSECTION_SIZE, 0),
            'west': (-INTERSECTION_SIZE, 0)
        }.get(self.origin, (0, 0))

    def get_exit_point(self):
        return {
            'north': (0, INTERSECTION_SIZE),
            'south': (0, -INTERSECTION_SIZE),
            'east': (INTERSECTION_SIZE, 0),
            'west': (-INTERSECTION_SIZE, 0)
        }.get(self.destination, (0, 0))

    def get_destination_position(self):
        return {
            'north': (0, LANE_LENGTH),
            'south': (0, -LANE_LENGTH),
            'east': (LANE_LENGTH, 0),
            'west': (-LANE_LENGTH, 0)
        }.get(self.destination, (0, 0))

    def distance(self, p1, p2):
        return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

    def should_stop(self):
        if self.has_entered:
            return False
            
        dist_to_intersection = self.distance(self.position, (0, 0))
        return (dist_to_intersection < INTERSECTION_SIZE * 1.5 and 
                simulation_state['lights'][self.origin] != 'green' and
                self.type != 'ambulance')

    def update(self, dt):
        self.stopped = self.should_stop()
        
        if self.type == 'ambulance' and self.stopped:
            self.stopped = False
            self.speed = VEHICLE_SPEED * 1.5
        
        if self.stopped:
            return False
            
        # Determine current target
        if not self.has_entered:
            target = self.get_approach_point()
            if self.distance(self.position, target) < 1:
                self.has_entered = True
                target = self.get_exit_point()
        elif not self.has_exited:
            target = self.get_exit_point()
            if self.distance(self.position, target) < 1:
                self.has_exited = True
                target = self.get_destination_position()
        else:
            target = self.get_destination_position()
            if self.distance(self.position, target) < 1:
                return True  # Reached destination
        
        # Move toward target
        direction = (
            target[0] - self.position[0],
            target[1] - self.position[1]
        )
        distance = self.distance(self.position, target)
        direction = (
            direction[0]/distance if distance > 0 else 0,
            direction[1]/distance if distance > 0 else 0
        )
        
        self.position = (
            self.position[0] + direction[0] * self.speed * dt,
            self.position[1] + direction[1] * self.speed * dt
        )
        
        return False

def traffic_light_controller():
    while True:
        # North-South green
        simulation_state['lights'] = {
            'north': 'green',
            'south': 'green',
            'east': 'red',
            'west': 'red'
        }
        time.sleep(10)
        
        # North-South yellow
        simulation_state['lights'] = {
            'north': 'yellow',
            'south': 'yellow',
            'east': 'red',
            'west': 'red'
        }
        time.sleep(2)
        
        # East-West green
        simulation_state['lights'] = {
            'north': 'red',
            'south': 'red',
            'east': 'green',
            'west': 'green'
        }
        time.sleep(10)
        
        # East-West yellow
        simulation_state['lights'] = {
            'north': 'red',
            'south': 'red',
            'east': 'yellow',
            'west': 'yellow'
        }
        time.sleep(2)

def vehicle_controller():
    last_time = time.time()
    while True:
        current_time = time.time()
        dt = min(current_time - last_time, 0.1)
        last_time = current_time
        
        # Update vehicles
        for vid, vehicle in list(simulation_state['vehicles']['active'].items()):
            try:
                if vehicle.update(dt):
                    del simulation_state['vehicles']['active'][vid]
            except Exception as e:
                print(f"Error updating vehicle {vid}: {e}")
                continue
        
        # Spawn new vehicles
        for direction in ['north', 'south', 'east', 'west']:
            queue = simulation_state['vehicles']['queued'][direction]
            if queue and simulation_state['lights'][direction] == 'green':
                vehicle_data = queue.popleft()
                destinations = ['north', 'south', 'east', 'west']
                destinations.remove(direction)
                destination = random.choice(destinations)
                
                try:
                    vehicle = Vehicle(
                        vehicle_data['id'],
                        vehicle_data['type'],
                        direction,
                        destination
                    )
                    simulation_state['vehicles']['active'][vehicle.id] = vehicle
                except Exception as e:
                    print(f"Error creating vehicle: {e}")
                    continue
        
        time.sleep(0.05)

@app.route('/add_vehicle', methods=['POST'])
def add_vehicle():
    data = request.json
    vehicle = {
        'id': simulation_state['next_id'],
        'type': data['type'],
        'direction': data['direction']
    }
    simulation_state['next_id'] += 1
    simulation_state['vehicles']['queued'][data['direction']].append(vehicle)
    return jsonify({'success': True, 'vehicle_id': vehicle['id']})

@app.route('/get_state', methods=['GET'])
def get_state():
    active_vehicles = {}
    for vid, vehicle in simulation_state['vehicles']['active'].items():
        active_vehicles[vid] = {
            'type': vehicle.type,
            'origin': vehicle.origin,
            'destination': vehicle.destination,
            'position': {'x': vehicle.position[0], 'y': vehicle.position[1]},
            'stopped': vehicle.stopped
        }
    
    return jsonify({
        'lights': simulation_state['lights'],
        'vehicles': {
            'queued': {k: list(v) for k, v in simulation_state['vehicles']['queued'].items()},
            'active': active_vehicles
        }
    })

if __name__ == '__main__':
    threading.Thread(target=traffic_light_controller, daemon=True).start()
    threading.Thread(target=vehicle_controller, daemon=True).start()
    app.run(port=5000, debug=True)