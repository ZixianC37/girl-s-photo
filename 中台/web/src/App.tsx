import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './theme/ThemeContext';
import AppLayout from './components/AppLayout';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';

import { lazy, Suspense } from 'react';
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Projects = lazy(() => import('./pages/Projects'));
const ProjectCreate = lazy(() => import('./pages/ProjectCreate'));
const ProjectDetail = lazy(() => import('./pages/ProjectDetail'));
const Anomalies = lazy(() => import('./pages/Anomalies'));
const RoutesPage = lazy(() => import('./pages/Routes'));
const UserMapping = lazy(() => import('./pages/UserMapping'));
const TaskMonitor = lazy(() => import('./pages/TaskMonitor'));

function Loading() {
  return <div style={{ color: 'rgba(255,255,255,0.5)', textAlign: 'center', padding: 40 }}>加载中...</div>;
}

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <Suspense fallback={<Loading />}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/projects" element={<Projects />} />
              <Route path="/projects/new" element={<ProjectCreate />} />
              <Route path="/projects/:id" element={<ProjectDetail />} />
              <Route path="/anomalies" element={<Anomalies />} />
              <Route path="/routes" element={<RoutesPage />} />
              <Route path="/users" element={<UserMapping />} />
              <Route path="/tasks" element={<TaskMonitor />} />
            </Route>
          </Routes>
        </Suspense>
      </ThemeProvider>
    </BrowserRouter>
  );
}
