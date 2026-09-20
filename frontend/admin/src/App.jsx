import { NavLink, Route, Routes } from 'react-router-dom'

function Dashboard() {
  return (
    <div className="card">
      <h2>Dashboard</h2>
      <p>Placeholder — overview of sites, templates, and activity goes here.</p>
    </div>
  )
}

function Sites() {
  return (
    <div className="card">
      <h2>Sites</h2>
      <p>Placeholder — list of customer sites goes here.</p>
    </div>
  )
}

function Templates() {
  return (
    <div className="card">
      <h2>Templates</h2>
      <p>Placeholder — template overview goes here (upload happens in the Portal app).</p>
    </div>
  )
}

export default function App() {
  return (
    <div className="layout">
      <aside className="sidebar">
        <h1>Vicinic Admin</h1>
        <nav>
          <NavLink to="/" end>
            Dashboard
          </NavLink>
          <NavLink to="/sites">Sites</NavLink>
          <NavLink to="/templates">Templates</NavLink>
        </nav>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/sites" element={<Sites />} />
          <Route path="/templates" element={<Templates />} />
        </Routes>
      </main>
    </div>
  )
}
