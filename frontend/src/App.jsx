import { useState, useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css' // This is required to make the map look right!

// --- Fix for Leaflet Icons in React ---
import L from 'leaflet'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

const DefaultIcon = L.icon({
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
  iconAnchor: [12, 41],
  popupAnchor: [1, -34]
})
L.Marker.prototype.options.icon = DefaultIcon
// --------------------------------------

function App() {
  const [orders, setOrders] = useState([])

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/orders/pending')
      .then(response => response.json())
      .then(data => setOrders(data))
      .catch(error => console.error("Error fetching data:", error))
  }, [])

  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif', backgroundColor: '#1e1e2f', color: 'white', minHeight: '100vh' }}>
      <h1 style={{ color: '#A9D08E' }}>🥬 GreenLogistics AI Map Dashboard</h1>
      <p>Live Pending Orders (Selangor Region)</p>
      
      {/* --- THE MAP CONTAINER --- */}
      <div style={{ height: '600px', width: '100%', borderRadius: '15px', overflow: 'hidden', border: '2px solid #444' }}>
        <MapContainer center={[3.09, 101.57]} zoom={11} style={{ height: '100%', width: '100%' }}>
          
          {/* This is the background map image from OpenStreetMap */}
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {/* This loops through your Python data and places a Pin for every order */}
          {orders.map(order => (
            <Marker key={order.order_id} position={[order.lat, order.lon]}>
              <Popup>
                <div style={{ color: 'black' }}>
                  <h3 style={{ margin: '0 0 5px 0' }}>{order.sku}</h3>
                  <p style={{ margin: '0' }}><strong>Boxes:</strong> {order.boxes}</p>
                  <p style={{ margin: '0' }}><strong>Customer ID:</strong> {order.customer_id}</p>
                </div>
              </Popup>
            </Marker>
          ))}

        </MapContainer>
      </div>
      
    </div>
  )
}

export default App