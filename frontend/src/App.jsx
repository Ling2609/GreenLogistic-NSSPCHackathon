import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, PackageSearch, Truck, Settings, Menu } from 'lucide-react'

// --- PLACEHOLDER PAGES ---
import LiveMapDashboard from './LiveMapDashboard' 
import OrdersPage from './OrdersPage'
import SettingsPage from './SettingsPage'

function FleetPage() {
  return <div style={{ padding: '20px' }}><h1>🚚 Fleet & Capacity</h1><p>Truck details and capacity limits will go here...</p></div>
}

// --- NAVIGATION COMPONENT ---
function Sidebar() {
  const location = useLocation();
  // State to track if the sidebar is expanded or collapsed
  const [isExpanded, setIsExpanded] = useState(true);

  // Dynamic styling based on expansion state
  const getLinkStyle = (path) => ({
    display: 'flex', 
    alignItems: 'center', 
    gap: isExpanded ? '15px' : '0px', 
    padding: '12px 15px', 
    justifyContent: isExpanded ? 'flex-start' : 'center',
    textDecoration: 'none', 
    borderRadius: '8px', 
    marginBottom: '8px',
    backgroundColor: location.pathname === path ? '#3357FF' : 'transparent',
    color: location.pathname === path ? 'white' : '#aaa',
    transition: 'all 0.2s ease',
    whiteSpace: 'nowrap' // Prevents text from dropping to the next line during animation
  });

  return (
    <div style={{ 
      width: isExpanded ? '250px' : '80px', // The magic toggle!
      transition: 'width 0.3s ease', // Smooth sliding animation
      backgroundColor: '#2a2a40', 
      borderRight: '1px solid #444', 
      padding: isExpanded ? '20px' : '20px 10px', 
      display: 'flex', 
      flexDirection: 'column',
      overflowX: 'hidden' // Hides text when collapsed
    }}>
      
      {/* Top Header & Toggle Button */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: isExpanded ? 'space-between' : 'center', marginBottom: '30px' }}>
        {isExpanded && <h2 style={{ color: '#A9D08E', margin: 0, fontSize: '20px' }}>🥬 GreenLogistics</h2>}
        
        <button 
          onClick={() => setIsExpanded(!isExpanded)}
          style={{ background: 'transparent', border: 'none', color: '#A9D08E', cursor: 'pointer', padding: '5px', display: 'flex', alignItems: 'center' }}
          title="Toggle Menu"
        >
          <Menu size={24} />
        </button>
      </div>
      
      {/* Navigation Links */}
      <nav style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
        <Link to="/" style={getLinkStyle('/')}>
          <div style={{ minWidth: '20px', display: 'flex', justifyContent: 'center' }}><LayoutDashboard size={20} /></div>
          {isExpanded && <span>Live Dispatch</span>}
        </Link>
        <Link to="/orders" style={getLinkStyle('/orders')}>
          <div style={{ minWidth: '20px', display: 'flex', justifyContent: 'center' }}><PackageSearch size={20} /></div>
          {isExpanded && <span>Order Management</span>}
        </Link>
        <Link to="/fleet" style={getLinkStyle('/fleet')}>
          <div style={{ minWidth: '20px', display: 'flex', justifyContent: 'center' }}><Truck size={20} /></div>
          {isExpanded && <span>Fleet Network</span>}
        </Link>
        <Link to="/settings" style={getLinkStyle('/settings')}>
          <div style={{ minWidth: '20px', display: 'flex', justifyContent: 'center' }}><Settings size={20} /></div>
          {isExpanded && <span>AI Simulations</span>}
        </Link>
      </nav>

      {/* Footer Version */}
      <div style={{ color: '#666', fontSize: '11px', textAlign: 'center', whiteSpace: 'nowrap' }}>
        {isExpanded ? 'FYP Build v1.0' : 'v1.0'}
      </div>
    </div>
  )
}

// --- MAIN APP ROUTER ---
function App() {
  return (
    <Router>
      <div style={{ display: 'flex', height: '100vh', width: '100vw', backgroundColor: '#1e1e2f', color: 'white', fontFamily: 'sans-serif', overflow: 'hidden' }}>
        <Sidebar />
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