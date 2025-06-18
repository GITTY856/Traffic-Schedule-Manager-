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
  const [currentAlgorithm, setCurrentAlgorithm] = useState('FCFS');
  const [nextLane, setNextLane] = useState(null);
  const [showTaskbar, setShowTaskbar] = useState(true);
  const [queueCounts, setQueueCounts] = useState({
    north: 0, south: 0, east: 0, west: 0
  });

  const positionToViewport = (pos) => {
    const x = 50 + (pos.x / 2.5);
    const y = 50 - (pos.y / 2.5);
    return { x, y };
  };

  const getEmoji = (type) => {
    const emojiMap = {
      car: '🚗',
      bike: '🚲',
      ambulance: '🚑',
      bus: '🚌',
      truck: '🚚',
      fire: '🚒',
      police: '🚓',
      a: '🚑',
      f: '🚒',
      p: '🚓',
      b: '🚌',
      c: '🚗',
      t: '🚚',
      u: '🚎'
    };
    return emojiMap[type] || '🚗';
  };

  const fetchSimulationState = async () => {
    try {
      const response = await axios.get('http://localhost:5000/get_state');
      setLightStates(response.data.lights);
      setCurrentAlgorithm(response.data.algorithm);
      setNextLane(response.data.next_lane);

      const counts = {
        north: response.data.vehicles.queued.north.length,
        south: response.data.vehicles.queued.south.length,
        east: response.data.vehicles.queued.east.length,
        west: response.data.vehicles.queued.west.length
      };
      setQueueCounts(counts);

      const processedVehicles = Object.entries(response.data.vehicles.active).map(([id, vehicle]) => ({
        ...vehicle,
        id,
        position: vehicle.position,
        stopped: vehicle.stopped,
        priority: vehicle.priority
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

    for (const direction of ['north', 'south', 'east', 'west']) {
      const vehicles = inputValues[direction].replace(/\s/g, '').split(',').filter(Boolean);

      for (const char of vehicles) {
        if (!['a', 'f', 'p', 'b', 'c', 't', 'u'].includes(char.toLowerCase())) continue;

        try {
          await axios.post('http://localhost:5000/add_vehicle', {
            type: char.toLowerCase(),
            direction
          });
          await new Promise(resolve => setTimeout(resolve, 200));
        } catch (error) {
          console.error('Error adding vehicle:', error);
        }
      }
    }
  };

  const getTransition = () => ({
    type: "spring",
    damping: 20,
    stiffness: 100,
    mass: 0.8
  });

  const getVehicleStyle = (vehicle) => {
    const baseStyle = {
      position: 'absolute',
      zIndex: vehicle.priority >= 3 ? 25 : 15,
      transform: 'translate(-50%, -50%)',
      willChange: 'transform',
      fontSize: vehicle.type === 't' ? '32px' : '28px'
    };

    if (vehicle.priority >= 3) {
      baseStyle.filter = 'drop-shadow(0 0 8px rgba(255,0,255,0.8))';
    }

    return baseStyle;
  };

  return (
    <div className="app">
      {showTaskbar && (
        <div className="taskbar">
          <div className="taskbar-section">
            <h3>Traffic Control Panel</h3>
            <div className="algorithm-display">
              Current Algorithm: <strong>{currentAlgorithm}</strong>
            </div>
            <div className="lane-controls">
              {['north', 'south', 'east', 'west'].map(direction => (
                <div key={direction} className="lane-control">
                  <div className="lane-header">
                    <span className="lane-name">{direction.toUpperCase()}</span>
                    <span className={`light-indicator ${lightStates[direction]}`}></span>
                    <span className="queue-count">{queueCounts[direction]} vehicles</span>
                  </div>
                  <input
                    type="text"
                    value={inputValues[direction]}
                    onChange={(e) => handleInputChange(direction, e.target.value)}
                    placeholder="a,f,p,b,c,t,u"
                  />
                </div>
              ))}
            </div>
            <button
              className="start-button"
              onClick={startSimulation}
              disabled={isSimulating}
            >
              {isSimulating ? 'Simulation Running...' : 'Start Simulation'}
            </button>
          </div>
        </div>
      )}

      <div className="intersection">
        <div className="road horizontal"></div>
        <div className="road vertical"></div>
        <div className="lane-markings horizontal"></div>
        <div className="lane-markings vertical"></div>

        {['top', 'bottom', 'left', 'right'].map(pos => (
          <div key={pos} className={`zebra zebra-${pos}`}></div>
        ))}

        {['north', 'south', 'east', 'west'].map(direction => (
          <div key={direction} className={`traffic-light ${direction}`}>
            {['red', 'yellow', 'green'].map(color => (
              <div
                key={color}
                className={`light ${lightStates[direction] === color ? `${color} active` : 'off'}`}
              ></div>
            ))}
          </div>
        ))}

        <div className="decorations">
          <div className="tree deciduous nw1">🌳</div>
          <div className="tree coniferous nw2">🌲</div>
          <div className="building office nw">
            <div className="building-windows"></div>
            <div className="building-details"></div>
          </div>
          <div className="bush nw1"></div>

          <div className="tree palm ne1">🌴</div>
          <div className="tree coniferous ne2">🌲</div>
          <div className="building highrise ne">
            <div className="building-windows"></div>
            <div className="building-rooftop"></div>
          </div>

          <div className="tree deciduous sw1">🌳</div>
          <div className="construction sw">
            <div className="crane">🏗️</div>
            <div className="construction-materials"></div>
          </div>

          <div className="tree palm se1">🌴</div>
          <div className="tree deciduous se2">🌳</div>
          <div className="building apartment se">
            <div className="building-windows"></div>
            <div className="building-balconies"></div>
          </div>
        </div>

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
              style={getVehicleStyle(vehicle)}
            >
              {getEmoji(vehicle.type)}
              {['a', 'f', 'p'].includes(vehicle.type) && (
                <span className="siren">🚨</span>
              )}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

export default App;
