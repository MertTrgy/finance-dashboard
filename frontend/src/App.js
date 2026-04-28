import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import ErrorBoundary from './components/ErrorBoundary';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Categories from './pages/Categories';
import Recurring from './pages/Recurring';
import Insights from './pages/Insights';

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login"    element={<Login />} />
            <Route path="/register" element={<Register />} />

            <Route path="/" element={
              <ProtectedRoute><Dashboard /></ProtectedRoute>
            }/>

            <Route path="/categories" element={
              <ProtectedRoute><Categories /></ProtectedRoute>
            }/>

            <Route path="/recurring" element={
              <ProtectedRoute><Recurring /></ProtectedRoute>
            }/>

            <Route path="/insights" element={
              <ProtectedRoute><Insights /></ProtectedRoute>
            }/>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}