import { useState } from 'react';
import { Sliders, AlertTriangle, Truck } from 'lucide-react';

function SettingsPage() {
  const [capacity, setCapacity] = useState(800);
  const [status, setStatus] = useState('');
  const [isSimulating, setIsSimulating] = useState(false);

  const handleSimulate = async (e) => {
    e.preventDefault();
    setIsSimulating(true);
    setStatus('Running CVRP Algorithm...');

    try {
      const response = await fetch('http://127.0.0.1:8000/api/settings/capacity', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_capacity: parseInt(capacity) })
      });

      if (response.ok) {
        const data = await response.json();
        setStatus(`✅ Simulation Complete! AI deployed ${data.total_trucks} trucks.`);
      } else {
        setStatus('❌ Error reaching AI engine.');
      }
    } catch {
      setStatus('❌ Network Error.');
    } finally {
      setIsSimulating(false);
    }
  };

  return (
    <div style={{ padding: '30px', maxWidth: '800px', margin: '0 auto', color: 'white' }}>
      <h2 style={{ color: '#A9D08E', borderBottom: '1px solid #444', paddingBottom: '10px', display: 'flex', alignItems: 'center', gap: '10px' }}>
        <Sliders /> AI Simulation Parameters
      </h2>
      <p style={{ color: '#aaa', marginBottom: '30px' }}>
        Adjust the physical constraints of the logistics network to stress-test the AI routing engine.
      </p>

      {/* Capacity Constraint Card */}
      <div style={{ backgroundColor: '#2a2a40', padding: '25px', borderRadius: '12px', border: '1px solid #444', marginBottom: '20px' }}>
        <h3 style={{ margin: '0 0 15px 0', color: '#fff', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Truck size={20} color="#3357FF"/> Fleet Capacity Limit
        </h3>
        <p style={{ fontSize: '13px', color: '#aaa', marginBottom: '20px' }}>
          By default, standard lorries carry 800 boxes. What happens if we switch to smaller vans (300 boxes) or heavy articulated trucks (2000 boxes)?
        </p>

        <form onSubmit={handleSimulate}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '20px', marginBottom: '20px' }}>
            <input 
              type="range" 
              min="100" 
              max="3000" 
              step="100"
              value={capacity} 
              onChange={(e) => setCapacity(e.target.value)}
              style={{ flex: 1, cursor: 'pointer' }}
            />
            <div style={{ fontSize: '24px', fontWeight: 'bold', width: '120px', textAlign: 'right', color: '#A9D08E' }}>
              {capacity} <span style={{ fontSize: '14px', color: '#aaa', fontWeight: 'normal' }}>boxes</span>
            </div>
          </div>

          <button 
            type="submit" 
            disabled={isSimulating}
            style={{ width: '100%', padding: '12px', backgroundColor: isSimulating ? '#444' : '#3357FF', color: 'white', border: 'none', borderRadius: '6px', cursor: isSimulating ? 'not-allowed' : 'pointer', fontWeight: 'bold', fontSize: '16px', transition: '0.2s' }}
          >
            {isSimulating ? 'Recalculating Routes...' : 'Run Simulation'}
          </button>
        </form>
        
        {status && <div style={{ marginTop: '15px', textAlign: 'center', color: status.includes('✅') ? '#33FF57' : '#FFB533', fontWeight: 'bold' }}>{status}</div>}
      </div>

      {/* Coming Soon Card (Great for FYP future work sections) */}
      <div style={{ backgroundColor: '#1e1e2f', padding: '20px', borderRadius: '12px', border: '1px dashed #555', opacity: 0.7 }}>
        <h4 style={{ margin: '0 0 10px 0', color: '#ccc', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <AlertTriangle size={18} color="#FF5733" /> Coming Soon: Disaster Scenarios
        </h4>
        <p style={{ fontSize: '13px', color: '#888', margin: 0 }}>
          Future iterations will include toggles for "Flood in Pahang" or "+50% Festive Demand Spikes" to test dynamic supply chain rerouting.
        </p>
      </div>

    </div>
  );
}

export default SettingsPage;