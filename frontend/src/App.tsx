import { Navigate, Route, Routes } from 'react-router-dom';
import Host from './pages/Host';
import Guest from './pages/Guest';

export default function App() {
  return (
    <Routes>
      <Route path="/host" element={<Host />} />
      <Route path="/w/:token" element={<Guest />} />
      <Route path="*" element={<Navigate to="/host" replace />} />
    </Routes>
  );
}
