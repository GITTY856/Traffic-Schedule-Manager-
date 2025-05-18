import React, { useState, useEffect } from 'react';
import './App.css';
import { motion } from 'framer-motion';
import axios from 'axios';

function App() {
  const [vehicles, setVehicles] = useState([]);
  const [inputValues, setInputValues] = useState({
    north: '', south: '', east: '', west: ''
  });
  const [isSimulating, setIsSimulating] = useState(false);
  const [lightStates, setLightStates] = useState({
    north: 'red', south: 'red', east: 'green', west: 'green'
  });

  // Corrected position mapping
  const positionToViewport = (pos) => {
    // Map backend coordinates (-100 to 100) to viewport percentages (0-100%)
    const x = 50 + (pos.x / 2);
    const y = 50 - (pos.y / 2);
    return { x, y };
  };

  const getEmoji = (type) => ({
    car: '🚗', bike: '🚲', ambulance: '🚑', bus: '🚌'
  }[type] || '❓');

  const fetchSimulationState = async () => {
    try {
      const response = await axios.get('http://localhost:5000/get_state');
      setLightStates(response.data.lights);

      const processedVehicles = Object.entries(response.data.vehicles.active).map(([id, vehicle]) => ({
        ...vehicle,
        id,
        position: vehicle.position,
        stopped: vehicle.stopped
      }));

      setVehicles(processedVehicles);
    } catch (error) {
      console.error('Error fetching simulation state:', error);
    }
  };

  useEffect(() => {
    if (!isSimulating) return;
    const interval = setInterval(fetchSimulationState, 50);
    return () => clearInterval(interval);
  }, [isSimulating]);

  const handleInputChange = (direction, value) => {
    setInputValues(prev => ({ ...prev, [direction]: value }));
  };

  const startSimulation = async () => {
    setIsSimulating(true);
    setVehicles([]);

    const vehicleTypes = { c: 'car', b: 'bike', t: 'bus', a: 'ambulance' };

    for (const direction of ['north', 'south', 'east', 'west']) {
      const vehicles = inputValues[direction].replace(/\s/g, '').split(',').filter(Boolean);

      for (const char of vehicles) {
        const type = vehicleTypes[char.toLowerCase()];
        if (!type) continue;

        try {
          await axios.post('http://localhost:5000/add_vehicle', { type, direction });
          await new Promise(resolve => setTimeout(resolve, 200));
        } catch (error) {
          console.error('Error adding vehicle:', error);
        }
      }
    }
  };

  // Smoother animation config
  const getTransition = () => ({
    type: "spring",
    damping: 20,
    stiffness: 100,
    mass: 0.8
  });

  return (
    <div className="app">
      <div className="intersection">
        {/* Road Elements */}
        <div className="road horizontal"></div>
        <div className="road vertical"></div>
        <div className="lane-markings horizontal"></div>
        <div className="lane-markings vertical"></div>

        {/* Zebra Crossings */}
        {['top', 'bottom', 'left', 'right'].map(pos => (
          <div key={pos} className={`zebra zebra-${pos}`}></div>
        ))}

        {/* Traffic Lights */}
        {['north', 'south', 'east', 'west'].map(direction => (
          <div key={direction} className={`traffic-light ${direction}`}>
            {['red', 'yellow', 'green'].map(color => (
              <div key={color} className={`light ${lightStates[direction] === color ? `${color} active` : 'off'}`}></div>
            ))}
          </div>
        ))}

        {/* Input Controls */}
        {[
          { dir: 'north', label: 'North (↓)' },
          { dir: 'south', label: 'South (↑)' },
          { dir: 'east', label: 'East (←)' },
          { dir: 'west', label: 'West (→)' }
        ].map(({ dir, label }) => (
          <div key={dir} className={`direction-input ${dir}`}>
            <label>{label}</label>
            <input
              type="text"
              value={inputValues[dir]}
              onChange={(e) => handleInputChange(dir, e.target.value)}
              placeholder="c,b,t,a"
              disabled={isSimulating}
            />
          </div>
        ))}

        <button className="start-button" onClick={startSimulation} disabled={isSimulating}>
          {isSimulating ? 'Simulating...' : 'Start Simulation'}
        </button>

        {/* Vehicles */}
        {vehicles.map(vehicle => {
          const viewportPos = positionToViewport(vehicle.position);
          
          return (
            <motion.div
              key={vehicle.id}
              className={`vehicle ${vehicle.type} ${vehicle.stopped ? 'stopped' : ''}`}
              initial={false}
              animate={{
                left: `${viewportPos.x}%`,
                top: `${viewportPos.y}%`,
                transition: getTransition()
              }}
              style={{
                position: 'absolute',
                zIndex: vehicle.type === 'ambulance' ? 20 : 15,
                transform: 'translate(-50%, -50%)',
                willChange: 'transform'
              }}
            >
              {getEmoji(vehicle.type)}
              {vehicle.type === 'ambulance' && <span className="siren">🚨</span>}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

export default App;