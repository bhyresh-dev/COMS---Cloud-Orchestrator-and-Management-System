import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ChatProvider } from './contexts/ChatContext';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';
import Login          from './pages/Login';
import Dashboard      from './pages/Dashboard';
import AdminDashboard from './pages/AdminDashboard';
import Security       from './pages/Security';
import AuditLog       from './pages/AuditLog';
import Approvals      from './pages/Approvals';
import Profile        from './pages/Profile';
import ResourcesPage  from './pages/ResourcesPage';

export default function App() {
  return (
    <AuthProvider>
      <ChatProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />

          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Layout><Dashboard /></Layout>
              </ProtectedRoute>
            }
          />

          <Route
            path="/security"
            element={
              <ProtectedRoute>
                <Layout><Security /></Layout>
              </ProtectedRoute>
            }
          />

          <Route
            path="/admin"
            element={
              <ProtectedRoute requireAdmin>
                <Layout><AdminDashboard /></Layout>
              </ProtectedRoute>
            }
          />

          <Route
            path="/audit"
            element={
              <ProtectedRoute>
                <Layout><AuditLog /></Layout>
              </ProtectedRoute>
            }
          />

          <Route
            path="/approvals"
            element={
              <ProtectedRoute>
                <Layout><Approvals /></Layout>
              </ProtectedRoute>
            }
          />

          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <Layout><Profile /></Layout>
              </ProtectedRoute>
            }
          />

          <Route
            path="/resources/:type"
            element={
              <ProtectedRoute>
                <Layout><ResourcesPage /></Layout>
              </ProtectedRoute>
            }
          />

          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
      </ChatProvider>
    </AuthProvider>
  );
}
