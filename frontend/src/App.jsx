import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, PackageSearch, Truck, Settings } from 'lucide-react'

// --- PLACEHOLDER PAGES ---
// Later, we will move these into their own separate files!
import LiveMapDashboard from './LiveMapDashboard' // We will create this next!

function OrdersPage() {
  return <div style={{ padding: '20px' }}><h1>📦 Order Management</h1><p>Data table of all orders will go here...</p></div>
}

function FleetPage() {
  return <div style={{ padding: '20px' }}><h1>🚚 Fleet & Capacity</h1><p>Truck details and capacity limits will go here...</p></div>
}

function SettingsPage() {
  return <div style={{ padding: '20px' }}><h1>⚙️ Simulation Settings</h1><p>Disaster toggles and AI parameters will go here...</p></div>
}

// --- NAVIGATION COMPONENT ---
function Sidebar() {
  const location = useLocation();

  // A helper function to make the active button look highlighted
  const getLinkStyle = (path) => ({
    display: 'flex', alignItems: 'center', gap: '10px', padding: '12px 15px', 
    textDecoration: 'none', borderRadius: '8px', marginBottom: '8px',
    backgroundColor: location.pathname === path ? '#3357FF' : 'transparent',
    color: location.pathname === path ? 'white' : '#aaa',
    transition: '0.2s'
  });

  return (
    <div style={{ width: '250px', backgroundColor: '#2a2a40', borderRight: '1px solid #444', padding: '20px', display: 'flex', flexDirection: 'column' }}>
      <h2 style={{ color: '#A9D08E', margin: '0 0 30px 0', fontSize: '20px' }}>🥬 GreenLogistics</h2>
      
      <nav style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
        <Link to="/" style={getLinkStyle('/')}>
          <LayoutDashboard size={20} /> Live Dispatch
        </Link>
        <Link to="/orders" style={getLinkStyle('/orders')}>
          <PackageSearch size={20} /> Order Management
        </Link>
        <Link to="/fleet" style={getLinkStyle('/fleet')}>
          <Truck size={20} /> Fleet Network
        </Link>
        <Link to="/settings" style={getLinkStyle('/settings')}>
          <Settings size={20} /> AI Simulations
        </Link>
      </nav>

      <div style={{ color: '#666', fontSize: '12px', textAlign: 'center' }}>
        FYP Build v1.0
      </div>
    </div>
  )
}

// --- MAIN APP ROUTER ---
function App() {
  return (
    <Router>
      <div style={{ display: 'flex', height: '100vh', width: '100vw', backgroundColor: '#1e1e2f', color: 'white', fontFamily: 'sans-serif' }}>
        
        {/* The permanent Navigation Menu */}
        <Sidebar />

        {/* The dynamic window that changes based on the URL */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          <Routes>
            <Route path="/" element={<LiveMapDashboard />} />
            <Route path="/orders" element={<OrdersPage />} />
            <Route path="/fleet" element={<FleetPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </div>

      </div>
    </Router>
  )
}

export default App