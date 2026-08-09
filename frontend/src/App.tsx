import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppShell } from './presentation/components/navigation/AppShell';
import { DashboardPage } from './presentation/pages/DashboardPage';
import { ExtratoPage } from './presentation/pages/ExtratoPage';
import { AnalyticsPage } from './presentation/pages/AnalyticsPage';
import { DiviasPage } from './presentation/pages/DiviasPage';
import { LancarPage } from './presentation/pages/LancarPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 1000 * 60 * 5,
    },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<DashboardPage />} />
            <Route path="extrato"   element={<ExtratoPage />} />
            <Route path="analytics" element={<AnalyticsPage />} />
            <Route path="dividas"   element={<DiviasPage />} />
            <Route path="lancar"    element={<LancarPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
