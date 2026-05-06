import { useState, useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polyline, Tooltip } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

const DefaultIcon = L.icon({
  iconUrl: markerIcon, shadowUrl: markerShadow,
  iconAnchor: [12, 41], popupAnchor: [1, -34]
})
L.Marker.prototype.options.icon = DefaultIcon

const FarmIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
  iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34]
});

const routeColors = ['#FF5733', '#33FF57', '#3357FF', '#F333FF', '#FFB533'];

function App() {
  const [orders, setOrders] = useState([])
  const [routingData, setRoutingData] = useState(null)

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/orders/pending')
      .then(res => res.json())
      .then(data => setOrders(data))

    fetch('http://127.0.0.1:8000/api/routes/optimized')
      .then(res => res.json())
      .then(data => setRoutingData(data))
  }, [])

  let totalBoxes = 0;
  let totalStops = 0;
  let totalTrucks = 0;
  let estimatedCostRM = 0;

  if (routingData) {
    totalTrucks = routingData.milk_runs.length;
    routingData.milk_runs.forEach(route => {
      totalBoxes += route.total_load;
      totalStops += route.stops;
    });
    estimatedCostRM = totalTrucks * 350; 
  }

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', backgroundColor: '#1e1e2f', color: 'white', fontFamily: 'sans-serif' }}>
      
      {/* --- LEFT COLUMN: SHRUNK SIDEBAR --- */}
      {/* Reduced width from 350px to 260px, reduced padding */}
      <div style={{ width: '260px', padding: '15px', backgroundColor: '#2a2a40', borderRight: '1px solid #444', display: 'flex', flexDirection: 'column', gap: '12px', overflowY: 'auto' }}>
        
        <div>
          <h2 style={{ color: '#A9D08E', margin: '0 0 5px 0', fontSize: '18px' }}>🥬 GreenLogistics AI</h2>
          <p style={{ margin: 0, color: '#aaa', fontSize: '12px' }}>Daily Master Dispatch Plan</p>
        </div>
        
        <hr style={{ borderColor: '#444', width: '100%', margin: '5px 0' }} />

        {/* KPI Cards: Replaced <h1> with smaller, tighter custom fonts */}
        <div style={{ backgroundColor: '#1e1e2f', padding: '12px', borderRadius: '8px', borderLeft: '4px solid #3357FF' }}>
          <div style={{ color: '#aaa', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Total Fleet Needed</div>
          <div style={{ fontSize: '22px', fontWeight: 'bold', marginTop: '4px' }}>{totalTrucks} Trucks</div>
        </div>

        <div style={{ backgroundColor: '#1e1e2f', padding: '12px', borderRadius: '8px', borderLeft: '4px solid #33FF57' }}>
          <div style={{ color: '#aaa', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Total Cargo Volume</div>
          <div style={{ fontSize: '22px', fontWeight: 'bold', marginTop: '4px' }}>{totalBoxes} Boxes</div>
        </div>

        <div style={{ backgroundColor: '#1e1e2f', padding: '12px', borderRadius: '8px', borderLeft: '4px solid #FF5733' }}>
          <div style={{ color: '#aaa', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Est. Daily Cost</div>
          <div style={{ fontSize: '22px', fontWeight: 'bold', marginTop: '4px' }}>RM {estimatedCostRM}</div>
        </div>

        <div style={{ backgroundColor: '#1e1e2f', padding: '12px', borderRadius: '8px', borderLeft: '4px solid #F333FF' }}>
          <div style={{ color: '#aaa', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Customers Served</div>
          <div style={{ fontSize: '22px', fontWeight: 'bold', marginTop: '4px' }}>{totalStops} Stops</div>
        </div>
      </div>

      {/* --- RIGHT COLUMN: THE MAP --- */}
      {/* Reduced padding around the map */}
      <div style={{ flex: 1, padding: '15px', display: 'flex', flexDirection: 'column' }}>
        <h3 style={{ margin: '0 0 10px 0', fontSize: '16px', fontWeight: 'normal', color: '#ccc' }}>Live AI Fleet Routing Monitor</h3>
        
        <div style={{ flex: 1, borderRadius: '10px', overflow: 'hidden', border: '1px solid #444' }}>
          <MapContainer center={[3.8, 101.5]} zoom={8} style={{ height: '100%', width: '100%' }}>
            
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            {orders.map(order => (
              <Marker key={order.customer_id} position={[order.lat, order.lon]}>
                <Popup>
                  <div style={{ color: 'black', minWidth: '120px' }}>
                    <h4 style={{ margin: '0 0 5px 0', borderBottom: '1px solid #ccc', fontSize: '14px' }}>{order.customer_id} ({order.state})</h4>
                    <p style={{ margin: '0', fontSize: '13px' }}><strong>Demand:</strong> {order.total_boxes} boxes</p>
                  </div>
                </Popup>
              </Marker>
            ))}

            {routingData && (
              <>
                <Marker position={[routingData.farm.lat, routingData.farm.lon]} icon={FarmIcon}>
                  <Popup><b>🌾 Origin: {routingData.farm.name}</b></Popup>
                </Marker>

                {routingData.milk_runs.map((route, index) => (
                  <Polyline 
                    key={route.region} 
                    positions={route.path} 
                    pathOptions={{ 
                      color: routeColors[index % routeColors.length], 
                      weight: 4,  // slightly thinner line
                      opacity: 0.8,
                      dashArray: '8, 8'
                    }} 
                  >
                    <Tooltip sticky>
                      <div style={{ fontSize: '13px' }}>
                        <strong>Route: {route.region}</strong><br/>
                        🚚 Total Load: {route.total_load} boxes<br/>
                        📍 Customers: {route.stops}
                      </div>
                    </Tooltip>
                  </Polyline>
                ))}
              </>
            )}

          </MapContainer>
        </div>
      </div>
      
    </div>
  )
}

export default App