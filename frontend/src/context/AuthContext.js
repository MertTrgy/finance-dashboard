import { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null);
  const [loading, setLoading] = useState(true); // true while we verify the stored token

  // On mount: if tokens are stored, fetch the current user to hydrate state
  useEffect(() => {
    const access = localStorage.getItem('access');
    if (access) {
      api.get('/auth/me/')
        .then(({ data }) => setUser(data))
        .catch(() => {
          localStorage.removeItem('access');
          localStorage.removeItem('refresh');
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (username, password) => {
    const { data } = await api.post('/auth/login/', { username, password });
    localStorage.setItem('access', data.access);
    localStorage.setItem('refresh', data.refresh);
    const me = await api.get('/auth/me/');
    setUser(me.data);
    return me.data;
  };

  const register = async (username, email, password) => {
    await api.post('/auth/register/', { username, email, password });
    return login(username, password); // auto-login after register
  };

  const logout = () => {
    localStorage.removeItem('access');
    localStorage.removeItem('refresh');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// Convenience hook — import useAuth anywhere instead of useContext(AuthContext)
export function useAuth() {
  return useContext(AuthContext);
}