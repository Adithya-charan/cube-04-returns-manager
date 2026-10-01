import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Header from './components/Header';
import DashboardView from './components/DashboardView';
import InspectionDetailView from './components/InspectionDetailView';
import QRScanView from './components/QRScanView';
import CaptureView from './components/CaptureView';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';
const DEMO_ORG = 'org_demo_alpha';

export default function App() {
  const [viewState, setViewState] = useState('dashboard'); // 'dashboard', 'qr_scan', 'capture', 'detail'
  const [selectedRecordId, setSelectedRecordId] = useState(null);
  const [qrVerification, setQrVerification] = useState(null);

  const [reviews, setReviews] = useState([]);
  const [loadingReviews, setLoadingReviews] = useState(true);

  const fetchReviews = async () => {
    setLoadingReviews(true);
    try {
      const { data } = await axios.get(`${API_BASE}/reviews`, { params: { org_id: DEMO_ORG } });
      setReviews(data || []);
    } catch {
      setReviews([]);
    } finally {
      setLoadingReviews(false);
    }
  };

  useEffect(() => {
    fetchReviews();
  }, []);

  const [selectedScenario, setSelectedScenario] = useState(null);

  const handleQuickSearch = (term) => {
    setSelectedRecordId(term);
    setViewState('detail');
  };

  const handleStartInspection = (mode, scenario = null) => {
    if (scenario) setSelectedScenario(scenario);
    else setSelectedScenario(null);
    if (mode === 'qr') setViewState('qr_scan');
    else setViewState('capture');
  };

  const handleReview = (recordId) => {
    setSelectedRecordId(recordId);
    setViewState('detail');
  };

  const handleInspectionDone = (result) => {
    setSelectedRecordId(result.record_id);
    setViewState('detail');
    fetchReviews();
  };

  return (
    <div className="min-h-screen bg-surface font-body-md text-on-surface antialiased flex flex-col">
      <Header onQuickSearch={handleQuickSearch} onDashboard={() => setViewState('dashboard')} />


      <main className="flex-1 w-full pt-28 px-margin max-w-[1600px] mx-auto">
        {viewState === 'dashboard' && (
          <DashboardView
            reviews={reviews}
            loading={loadingReviews}
            onNewInspection={handleStartInspection}
            onReview={handleReview}
            onRefresh={fetchReviews}
          />
        )}

        {viewState === 'qr_scan' && (
          <QRScanView
            onBack={() => setViewState('dashboard')}
            onContinue={(verifyData) => {
              setQrVerification(verifyData);
              setViewState('capture');
            }}
          />
        )}

        {viewState === 'capture' && (
          <CaptureView
            onBack={() => setViewState('dashboard')}
            onResult={handleInspectionDone}
            qrVerification={qrVerification}
            initialScenario={selectedScenario}
          />
        )}


        {viewState === 'detail' && selectedRecordId && (
          <InspectionDetailView
            recordId={selectedRecordId}
            orgId={DEMO_ORG}
            onBack={() => setViewState('dashboard')}
            onResolved={() => {
              fetchReviews();
              setViewState('dashboard');
            }}
          />
        )}
      </main>
    </div>
  );
}