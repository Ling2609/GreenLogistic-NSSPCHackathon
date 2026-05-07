import { useState } from 'react';
import { Send, MapPin } from 'lucide-react';

function OrdersPage() {
  const [formData, setFormData] = useState({
    customer_id: '',
    state: 'Selangor',
    total_boxes: '',
    lat: '',
    lon: ''
  });
  const [status, setStatus] = useState('');

  // Helper to instantly fill in dummy GPS coordinates for testing
  const autofillGPS = () => {
    setFormData({ ...formData, lat: '2.9213', lon: '101.6559', state: 'Selangor' }); // Cyberjaya
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setStatus('Sending to AI...');

    try {
      const response = await fetch('http://127.0.0.1:8000/api/orders/new', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_id: formData.customer_id,
          state: formData.state,
          total_boxes: parseInt(formData.total_boxes),
          lat: parseFloat(formData.lat),
          lon: parseFloat(formData.lon)
        })
      });

      if (response.ok) {
        setStatus('✅ Order Added & Routes Recalculated!');
        setFormData({ customer_id: '', state: 'Selangor', total_boxes: '', lat: '', lon: '' });
      } else {
        setStatus('❌ Error: Could not reach backend.');
      }
    } catch {
      setStatus('❌ Network Error.');
    }
  };

  return (
    <div style={{ padding: '30px', maxWidth: '800px', margin: '0 auto', color: 'white' }}>
      <h2 style={{ color: '#A9D08E', borderBottom: '1px solid #444', paddingBottom: '10px' }}>📦 Manual Order Entry</h2>
      <p style={{ color: '#aaa', marginBottom: '30px' }}>
        Input ad-hoc orders here. The AI will instantly recalculate the master dispatch plan.
      </p>

      <div style={{ backgroundColor: '#2a2a40', padding: '25px', borderRadius: '12px', border: '1px solid #444' }}>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
          
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontSize: '14px', color: '#ccc' }}>Customer ID</label>
            <input required type="text" placeholder="e.g., C999" value={formData.customer_id} onChange={e => setFormData({...formData, customer_id: e.target.value})} style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #555', backgroundColor: '#1e1e2f', color: 'white' }} />
          </div>

          <div style={{ display: 'flex', gap: '15px' }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', marginBottom: '5px', fontSize: '14px', color: '#ccc' }}>Region / State</label>
              <select value={formData.state} onChange={e => setFormData({...formData, state: e.target.value})} style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #555', backgroundColor: '#1e1e2f', color: 'white' }}>
                <option value="Selangor">Selangor</option>
                <option value="Perak">Perak</option>
                <option value="Johor">Johor</option>
                <option value="Pahang">Pahang</option>
              </select>
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', marginBottom: '5px', fontSize: '14px', color: '#ccc' }}>Total Boxes (Demand)</label>
              <input required type="number" placeholder="e.g., 500" value={formData.total_boxes} onChange={e => setFormData({...formData, total_boxes: e.target.value})} style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #555', backgroundColor: '#1e1e2f', color: 'white' }} />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '15px', alignItems: 'flex-end' }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', marginBottom: '5px', fontSize: '14px', color: '#ccc' }}>Latitude</label>
              <input required type="number" step="any" placeholder="3.1415" value={formData.lat} onChange={e => setFormData({...formData, lat: e.target.value})} style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #555', backgroundColor: '#1e1e2f', color: 'white' }} />
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', marginBottom: '5px', fontSize: '14px', color: '#ccc' }}>Longitude</label>
              <input required type="number" step="any" placeholder="101.686" value={formData.lon} onChange={e => setFormData({...formData, lon: e.target.value})} style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #555', backgroundColor: '#1e1e2f', color: 'white' }} />
            </div>
            <button type="button" onClick={autofillGPS} style={{ padding: '10px 15px', backgroundColor: '#444', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', display: 'flex', gap: '5px', alignItems: 'center' }}>
              <MapPin size={16} /> Autofill Test GPS
            </button>
          </div>

          <button type="submit" style={{ marginTop: '15px', padding: '12px', backgroundColor: '#3357FF', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold', fontSize: '16px', display: 'flex', justifyContent: 'center', gap: '10px', alignItems: 'center' }}>
            <Send size={18} /> Inject Order into AI System
          </button>
          
          {status && <div style={{ marginTop: '10px', textAlign: 'center', color: status.includes('✅') ? '#33FF57' : '#FF5733' }}>{status}</div>}
        </form>
      </div>
    </div>
  );
}

export default OrdersPage;