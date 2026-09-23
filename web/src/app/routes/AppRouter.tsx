import { lazy } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from '@/components/layout/AppShell';
import { useAppSelector } from '@/app/store/hooks';
import { personaHomePath } from '@/constants/nav';

const CommandCentrePage = lazy(() => import('@/pages/CommandCentrePage'));
const BriefPage = lazy(() => import('@/pages/BriefPage'));
const PatternsPage = lazy(() => import('@/pages/PatternsPage'));
const BookPage = lazy(() => import('@/pages/BookPage'));
const AnomaliesPage = lazy(() => import('@/pages/AnomaliesPage'));
const BriefingPage = lazy(() => import('@/pages/BriefingPage'));

function PersonaHome() {
  const persona = useAppSelector((s) => s.persona.current);
  return <Navigate to={personaHomePath(persona)} replace />;
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<PersonaHome />} />
          <Route path="/command-centre" element={<CommandCentrePage />} />
          <Route path="/brief" element={<BriefPage />} />
          <Route path="/patterns" element={<PatternsPage />} />
          <Route path="/book" element={<BookPage />} />
          <Route path="/anomalies" element={<AnomaliesPage />} />
          <Route path="/briefing" element={<BriefingPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
