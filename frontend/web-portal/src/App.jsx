import { Route, Routes } from 'react-router-dom'

function Login() {
  return (
    <div className="page">
      <div className="card">
        <h2>Sign in</h2>
        <p>Placeholder — customer login goes here once the backend API exists.</p>
      </div>
    </div>
  )
}

function SiteEditor() {
  return (
    <div className="page">
      <div className="card">
        <h2>Edit your site</h2>
        <p>Placeholder — a list of editable slots (text) for the customer's own site goes here.</p>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Login />} />
      <Route path="/edit" element={<SiteEditor />} />
    </Routes>
  )
}
