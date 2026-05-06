import { useState, useEffect } from 'react'

function App() {
  // This creates a blank list to hold the data we get from Python
  const [orders, setOrders] = useState([])

  // This runs the moment the website loads
  useEffect(() => {
    // 1. Call the Python API
    fetch('http://127.0.0.1:8000/api/orders/pending')
      // 2. Turn the response into JSON
      .then(response => response.json())
      // 3. Save the data into our list
      .then(data => setOrders(data))
      .catch(error => console.error("Error fetching data:", error))
  }, [])

  return (
    <div style={{ padding: '40px', fontFamily: 'sans-serif', backgroundColor: '#1e1e2f', color: 'white', minHeight: '100vh' }}>
      <h1 style={{ color: '#A9D08E' }}>🥬 GreenLogistics AI Dispatch</h1>
      <h3>Live Orders from Database:</h3>
      
      <div style={{ display: 'flex', gap: '20px', marginTop: '20px' }}>
        {/* This loops through the data and creates a card for each order */}
        {orders.map(order => (
          <div key={order.order_id} style={{ border: '1px solid #444', padding: '20px', borderRadius: '10px', backgroundColor: '#2a2a40' }}>
            <h2>{order.sku}</h2>
            <p><strong>Region:</strong> {order.region}</p>
            <p><strong>Customer ID:</strong> {order.customer_id}</p>
            <p><strong>Quantity:</strong> {order.boxes} boxes</p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default App