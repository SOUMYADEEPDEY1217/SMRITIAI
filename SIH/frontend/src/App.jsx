import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Navbar from './components/common/Navbar';
import Background3D from './components/common/Background3D';
import LandingPage from './pages/landing/LandingPage';
import LoginPage from './pages/login/LoginPage';
import PatientDashboard from './pages/patient/PatientDashboard';
import ResultScreen from './pages/patient/ResultScreen';
import DoctorDashboard from './pages/doctor/DoctorDashboard';
import PatientProfile from './pages/doctor/PatientProfile';
import AdminDashboard from './pages/admin/AdminDashboard';

// New Feature Pages
import MemoriesPage from './pages/patient/MemoriesPage';
import FamilyMembersPage from './pages/patient/FamilyMembersPage';
import RemindersPage from './pages/patient/RemindersPage';
import QuizPage from './pages/patient/QuizPage';

// 10 Patient Activities
import MemoryGarden from './activities/MemoryGarden';
import FamiliarFace from './activities/FamiliarFace';
import LifeStory from './activities/LifeStory';
import MemoryRadio from './activities/MemoryRadio';
import DailyCompanion from './activities/DailyCompanion';
import MemoryWalk from './activities/MemoryWalk';
import CultureQuest from './activities/CultureQuest';
import RecallLoop from './activities/RecallLoop';
import FamilyPuzzle from './activities/FamilyPuzzle';
import CognitiveFingerprint from './activities/CognitiveFingerprint';

// Layout wrapper: displays portal Navbar on authenticated screens
function AppLayout({ children }) {
  const location = useLocation();
  const hideNavbar = location.pathname === '/' || location.pathname === '/login';

  return (
    <div className="cognitive-care-shell" style={{ position: 'relative', zIndex: 1 }}>
      <Background3D />
      {!hideNavbar && <Navbar />}
      <main className="app-main-content">{children}</main>
    </div>
  );
}

// Protected Route Wrapper
import { getCurrentUser } from './data/storage';

function ProtectedRoute({ children, allowedRoles }) {
  const user = getCurrentUser();
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout>
        <Routes>
          {/* Public Landing Page */}
          <Route path="/" element={<LandingPage />} />

          {/* Authentication & Role Selection */}
          <Route path="/login" element={<LoginPage />} />

          {/* Patient Portal */}
          <Route path="/patient" element={<ProtectedRoute allowedRoles={['patient']}><PatientDashboard /></ProtectedRoute>} />
          <Route path="/patient/result" element={<ProtectedRoute allowedRoles={['patient']}><ResultScreen /></ProtectedRoute>} />
          <Route path="/patient/fingerprint" element={<ProtectedRoute allowedRoles={['patient']}><CognitiveFingerprint /></ProtectedRoute>} />
          <Route path="/patient/memories" element={<ProtectedRoute allowedRoles={['patient']}><MemoriesPage /></ProtectedRoute>} />
          <Route path="/patient/family" element={<ProtectedRoute allowedRoles={['patient']}><FamilyMembersPage /></ProtectedRoute>} />
          <Route path="/patient/reminders" element={<ProtectedRoute allowedRoles={['patient']}><RemindersPage /></ProtectedRoute>} />
          <Route path="/patient/quiz" element={<ProtectedRoute allowedRoles={['patient']}><QuizPage /></ProtectedRoute>} />

          {/* The 10 Cognitive Activities */}
          <Route path="/patient/activity/memory-garden" element={<ProtectedRoute allowedRoles={['patient']}><MemoryGarden /></ProtectedRoute>} />
          <Route path="/patient/activity/familiar-face" element={<ProtectedRoute allowedRoles={['patient']}><FamiliarFace /></ProtectedRoute>} />
          <Route path="/patient/activity/lifestory" element={<ProtectedRoute allowedRoles={['patient']}><LifeStory /></ProtectedRoute>} />
          <Route path="/patient/activity/memory-radio" element={<ProtectedRoute allowedRoles={['patient']}><MemoryRadio /></ProtectedRoute>} />
          <Route path="/patient/activity/daily-companion" element={<ProtectedRoute allowedRoles={['patient']}><DailyCompanion /></ProtectedRoute>} />
          <Route path="/patient/activity/memory-walk" element={<ProtectedRoute allowedRoles={['patient']}><MemoryWalk /></ProtectedRoute>} />
          <Route path="/patient/activity/culture-quest" element={<ProtectedRoute allowedRoles={['patient']}><CultureQuest /></ProtectedRoute>} />
          <Route path="/patient/activity/recall-loop" element={<ProtectedRoute allowedRoles={['patient']}><RecallLoop /></ProtectedRoute>} />
          <Route path="/patient/activity/family-puzzle" element={<ProtectedRoute allowedRoles={['patient']}><FamilyPuzzle /></ProtectedRoute>} />

          {/* Doctor / Nurse Portal */}
          <Route path="/doctor" element={<ProtectedRoute allowedRoles={['doctor']}><DoctorDashboard /></ProtectedRoute>} />
          <Route path="/doctor/patient/:id" element={<ProtectedRoute allowedRoles={['doctor']}><PatientProfile /></ProtectedRoute>} />

          {/* Admin Portal */}
          <Route path="/admin" element={<ProtectedRoute allowedRoles={['admin']}><AdminDashboard /></ProtectedRoute>} />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppLayout>
    </BrowserRouter>
  );
}
