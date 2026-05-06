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

  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif', backgroundColor: '#1e1e2f', color: 'white', minHeight: '100vh' }}>
      <h1 style={{ color: '#A9D08E' }}>🚚 AI Fleet Dispatch & Milk Run Planner</h1>
      <p>Optimized Routes from {routingData ? routingData.farm.name : 'Loading...'} to Regional Supermarkets</p>
      
      <div style={{ height: '700px', width: '100%', borderRadius: '15px', overflow: 'hidden', border: '2px solid #444' }}>
        <MapContainer center={[3.8, 101.5]} zoom={8} style={{ height: '100%', width: '100%' }}>
          
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {/* UPGRADED: Rich Customer Popups */}
          {orders.map(order => (
            <Marker key={order.customer_id} position={[order.lat, order.lon]}>
              <Popup>
                <div style={{ color: 'black', minWidth: '150px' }}>
                  <h3 style={{ margin: '0 0 5px 0', borderBottom: '1px solid #ccc' }}>
                    {order.customer_id} ({order.state})
                  </h3>
                  <p style={{ margin: '5px 0' }}><strong>Demand:</strong> {order.total_boxes} boxes</p>
                  <p style={{ margin: '5px 0', fontSize: '11px', color: '#555' }}>
                    <strong>Items:</strong> {order.items_ordered}
                  </p>
                </div>
              </Popup>
            </Marker>
          ))}

          {routingData && (
            <>
              <Marker position={[routingData.farm.lat, routingData.farm.lon]} icon={FarmIcon}>
                <Popup><b>🌾 Origin: {routingData.farm.name}</b></Popup>
              </Marker>

              {/* UPGRADED: Interactive Hover Tooltips on the Routes */}
              {routingData.milk_runs.map((route, index) => (
                <Polyline 
                  key={route.region} 
                  positions={route.path} 
                  pathOptions={{ 
                    color: routeColors[index % routeColors.length], 
                    weight: 5, 
                    opacity: 0.8,
                    dashArray: '10, 10'
                  }} 
                >
                  <Tooltip sticky>
                    <div style={{ fontSize: '14px' }}>
                      <strong>Route: {route.region} Milk Run</strong><br/>
                      🚚 Total Load: {route.total_load} boxes<br/>
                      📍 Customers Served: {route.stops}
                    </div>
                  </Tooltip>
                </Polyline>
              ))}
            </>
          )}

        </MapContainer>
      </div>
    </div>
  )
}

export default App