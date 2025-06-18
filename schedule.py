from flask import Flask, jsonify, request
from flask_cors import CORS
from collections import defaultdict, deque
import time
import threading
import random
import math

app = Flask(__name__)
CORS(app)

LANE_LENGTH = 100
VEHICLE_SPEED = 15
INTERSECTION_SIZE = 20

VEHICLE_PRIORITIES = {
    'ambulance': 4,
    'fire': 3,
    'police': 2,
    'bus': 1,
    'car': 0,
    'truck': 0
}

VEHICLE_PROCESSING_TIMES = {
    'ambulance': 2,
    'fire': 3,
    'police': 3,
    'bus': 5,
    'car': 4,
    'truck': 6
}

class TrafficScheduler:
    def __init__(self):
        self.lanes = {
            'north': deque(),
            'south': deque(),
            'east': deque(),
            'west': deque()
        }
        self.current_lane = None
        self.time_quantum = 3
        self.algorithm = None
        self.cycle_count = 0
        self.total_processed = 0
        
    def add_vehicle(self, vehicle_type, direction):
        if direction in self.lanes:
            self.lanes[direction].append({
                'type': vehicle_type,
                'priority': VEHICLE_PRIORITIES.get(vehicle_type, 0),
                'processing_time': VEHICLE_PROCESSING_TIMES.get(vehicle_type, 4)
            })
            return True
        return False
    
    def select_algorithm(self):
        total_vehicles = sum(len(q) for q in self.lanes.values())
        emergency_count = sum(1 for q in self.lanes.values() 
                            for v in q if v['priority'] >= 3)
        
        if emergency_count > 0:
            return "PRIORITY"
        elif total_vehicles < 5:
            return "FCFS"
        elif all(len(q) < 3 for q in self.lanes.values()):
            return "SJF"
        else:
            return "RR"
    
    def run_cycle(self):
        self.algorithm = self.select_algorithm()
        open_lane = None
        
        if self.algorithm == "FCFS":
            open_lane = self._run_fcfs()
        elif self.algorithm == "SJF":
            open_lane = self._run_sjf()
        elif self.algorithm == "PRIORITY":
            open_lane = self._run_priority()
        else:
            open_lane = self._run_rr()
            
        self.cycle_count += 1
        return open_lane
    
    def _run_fcfs(self):
        return max(self.lanes.keys(), key=lambda x: len(self.lanes[x]))
    
    def _run_sjf(self):
        shortest = None
        for lane, vehicles in self.lanes.items():
            if vehicles:
                vehicle = vehicles[0]
                if shortest is None or vehicle['processing_time'] < shortest[1]['processing_time']:
                    shortest = (lane, vehicle)
        return shortest[0] if shortest else None
    
    def _run_priority(self):
        highest = None
        for lane, vehicles in self.lanes.items():
            if vehicles:
                vehicle = vehicles[0]
                if highest is None or vehicle['priority'] > highest[1]['priority']:
                    highest = (lane, vehicle)
        return highest[0] if highest else None
    
    def _run_rr(self):
        lanes_order = ['north', 'south', 'east', 'west']
        if self.current_lane:
            start_idx = (lanes_order.index(self.current_lane) + 1)
        else:
          start_idx = 0
            
        for i in range(4):
            lane = lanes_order[(start_idx + i) % 4]
            if self.lanes[lane]:
                self.current_lane = lane
                return lane
                
        return None

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
    'stop_distance': INTERSECTION_SIZE,
    'scheduler': TrafficScheduler()
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
                return True 
        
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
        open_lane = simulation_state['scheduler'].run_cycle()
        
        if open_lane:
            if open_lane in ['north', 'south']:
                simulation_state['lights'] = {
                    'north': 'green',
                    'south': 'green',
                    'east': 'red',
                    'west': 'red'
                }
            else:
                simulation_state['lights'] = {
                    'north': 'red',
                    'south': 'red',
                    'east': 'green',
                    'west': 'green'
                }
            
            time.sleep(5 + len(simulation_state['scheduler'].lanes[open_lane]))
            
            if open_lane in ['north', 'south']:
                simulation_state['lights'] = {
                    'north': 'yellow',
                    'south': 'yellow',
                    'east': 'red',
                    'west': 'red'
                }
            else:
                simulation_state['lights'] = {
                    'north': 'red',
                    'south': 'red',
                    'east': 'yellow',
                    'west': 'yellow'
                }
            time.sleep(2)
        else:
            simulation_state['lights'] = {
                'north': 'red',
                'south': 'red',
                'east': 'red',
                'west': 'red'
            }
            time.sleep(1)

def vehicle_controller():
    last_time = time.time()
    while True:
        current_time = time.time()
        dt = min(current_time - last_time, 0.1)
        last_time = current_time
        
        for vid, vehicle in list(simulation_state['vehicles']['active'].items()):
            try:
                if vehicle.update(dt):
                    del simulation_state['vehicles']['active'][vid]
            except Exception as e:
                print(f"Error updating vehicle {vid}: {e}")
                continue
        
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
    simulation_state['scheduler'].add_vehicle(data['type'], data['direction'])
    
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
        },
        'algorithm': simulation_state['scheduler'].algorithm
    })

if __name__ == '__main__':
    threading.Thread(target=traffic_light_controller, daemon=True).start()
    threading.Thread(target=vehicle_controller, daemon=True).start()
    app.run(port=5000, debug=True)
