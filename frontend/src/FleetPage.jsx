import { useState } from 'react';
import { Truck, CheckCircle, Wrench, AlertCircle } from 'lucide-react';

function FleetPage() {
  // Mock data for the FYP presentation to make it look like a real active fleet
  const [fleet] = useState([
    { id: 'T-1001', type: 'Heavy Lorry', capacity: 2000, region: 'Johor', status: 'Active', health: '98%' },
    { id: 'T-1002', type: 'Standard Truck', capacity: 800, region: 'Selangor', status: 'Active', health: '95%' },
    { id: 'T-1003', type: 'Standard Truck', capacity: 800, region: 'Selangor', status: 'Maintenance', health: '45%' },
    { id: 'T-1004', type: 'Light Van', capacity: 300, region: 'Perak', status: 'Active', health: '88%' },
    { id: 'T-1005', type: 'Heavy Lorry', capacity: 2000, region: 'Pahang', status: 'Off-Duty', health: '92%' },
    { id: 'T-1006', type: 'Standard Truck', capacity: 800, region: 'Penang', status: 'Active', health: '99%' },
  ]);

  const getStatusIcon = (status) => {
    switch(status) {
      case 'Active': return <CheckCircle size={16} color="#33FF57" />;
      case 'Maintenance': return <Wrench size={16} color="#FF5733" />;
      case 'Off-Duty': return <AlertCircle size={16} color="#FFB533" />;
      default: return null;
    }
  };

  const getStatusColor = (status) => {
    switch(status) {
      case 'Active': return '#1a4025';
      case 'Maintenance': return '#4a2520';
      case 'Off-Duty': return '#4a3f20';
      default: return '#2a2a40';
    }
  };

  return (
    <div style={{ padding: '30px', maxWidth: '1000px', margin: '0 auto', color: 'white' }}>
      <h2 style={{ color: '#A9D08E', borderBottom: '1px solid #444', paddingBottom: '10px', display: 'flex', alignItems: 'center', gap: '10px' }}>
        <Truck /> Fleet Management Network
      </h2>
      <p style={{ color: '#aaa', marginBottom: '30px' }}>
        Real-time status of all physical logistic assets currently registered to the AI routing engine.
      </p>

      {/* Fleet Data Table */}
      <div style={{ backgroundColor: '#2a2a40', borderRadius: '12px', border: '1px solid #444', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ backgroundColor: '#1e1e2f', borderBottom: '2px solid #444', color: '#ccc' }}>
              <th style={{ padding: '15px 20px', fontWeight: 'normal' }}>Vehicle ID</th>
              <th style={{ padding: '15px 20px', fontWeight: 'normal' }}>Asset Type</th>
              <th style={{ padding: '15px 20px', fontWeight: 'normal' }}>Max Capacity</th>
              <th style={{ padding: '15px 20px', fontWeight: 'normal' }}>Current Region</th>
              <th style={{ padding: '15px 20px', fontWeight: 'normal' }}>Operational Status</th>
              <th style={{ padding: '15px 20px', fontWeight: 'normal' }}>Engine Health</th>
            </tr>
          </thead>
          <tbody>
            {fleet.map((vehicle, index) => (
              <tr key={vehicle.id} style={{ borderBottom: index === fleet.length - 1 ? 'none' : '1px solid #333' }}>
                <td style={{ padding: '15px 20px', fontWeight: 'bold' }}>{vehicle.id}</td>
                <td style={{ padding: '15px 20px', color: '#aaa' }}>{vehicle.type}</td>
                <td style={{ padding: '15px 20px' }}>{vehicle.capacity} boxes</td>
                <td style={{ padding: '15px 20px', color: '#aaa' }}>{vehicle.region}</td>
                <td style={{ padding: '15px 20px' }}>
                  <span style={{ 
                    display: 'inline-flex', alignItems: 'center', gap: '8px', 
                    backgroundColor: getStatusColor(vehicle.status), 
                    padding: '5px 12px', borderRadius: '20px', fontSize: '13px' 
                  }}>
                    {getStatusIcon(vehicle.status)} {vehicle.status}
                  </span>
                </td>
                <td style={{ padding: '15px 20px', color: parseInt(vehicle.health) < 50 ? '#FF5733' : '#A9D08E' }}>
                  {vehicle.health}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default FleetPage;