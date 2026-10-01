import React, { useState, useRef, useEffect, useId } from 'react';
import axios from 'axios';
import { Html5QrcodeScanner } from 'html5-qrcode';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';
const DEMO_ORG = 'org_demo_alpha';
const DEMO_OPERATOR = 'op_mobile_user';

export default function App() {
  const [viewState, setViewState] = useState('dashboard'); // 'dashboard', 'qr_scan', 'capture', 'detail'
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRecordId, setSelectedRecordId] = useState(null);
  const [qrAuthData, setQrAuthData] = useState(null);

  const fetchReviews = async () => {
    setLoading(true);
    try {
      const { data } = await axios.get(`${API_BASE}/reviews`, { params: { org_id: DEMO_ORG } });
      setReviews(data || []);
    } catch {
      setReviews([]);
    } fontFinally: {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReviews();
  }, []);

  return (
    <div className="min-h-screen bg-surface font-body-md text-on-surface antialiased flex flex-col pb-safe">
      {/* Mobile Top App Bar */}
      <header className="sticky top-0 z-50 bg-surface-container-lowest shadow-sm border-b border-surface-container px-4 h-14 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {viewState !== 'dashboard' && (
            <button
              onClick={() => setViewState('dashboard')}
              className="w-8 h-8 rounded-full bg-surface-container flex items-center justify-center text-on-surface"
            >
              <span className="material-symbols-outlined text-[20px]">arrow_back</span>
            </button>
          )}
          <div className="flex flex-col">
            <span className="font-headline-sm text-headline-sm font-bold text-on-surface">CUBE Track 04</span>
            <span className="font-data-mono-sm text-[10px] text-secondary">STN-04 / MOBILE INTAKE</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-on-tertiary-container animate-pulse"></span>
          <span className="font-data-mono-sm text-[10px] bg-surface-container px-2 py-0.5 rounded text-on-surface font-semibold">
            ONLINE
          </span>
        </div>
      </header>

      {/* Main Screen Views */}
      <main className="flex-1 p-4 max-w-md mx-auto w-full">
        {viewState === 'dashboard' && (
          <MobileDashboard
            reviews={reviews}
            loading={loading}
            onStartScan={() => setViewState('qr_scan')}
            onStartCapture={() => setViewState('capture')}
            onSelectRecord={(id) => {
              setSelectedRecordId(id);
              setViewState('detail');
            }}
            onRefresh={fetchReviews}
          />
        )}

        {viewState === 'qr_scan' && (
          <MobileQRScanner
            onBack={() => setViewState('dashboard')}
            onContinue={(authData) => {
              setQrAuthData(authData);
              setViewState('capture');
            }}
          />
        )}

        {viewState === 'capture' && (
          <MobileCaptureView
            qrAuthData={qrAuthData}
            onBack={() => setViewState('dashboard')}
            onSuccess={(result) => {
              setSelectedRecordId(result.record_id);
              setViewState('detail');
              fetchReviews();
            }}
          />
        )}

        {viewState === 'detail' && selectedRecordId && (
          <MobileDetailView
            recordId={selectedRecordId}
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

function MobileDashboard({ reviews, loading, onStartScan, onStartCapture, onSelectRecord, onRefresh }) {
  return (
    <div className="space-y-4 animate-fadeIn">
      {/* Quick Launch Card */}
      <div className="bg-surface-container-lowest p-4 rounded-xl shadow-sm border border-surface-container">
        <div className="flex items-center gap-2 mb-3">
          <span className="material-symbols-outlined text-secondary text-[22px]">qr_code_scanner</span>
          <div>
            <span className="font-headline-sm text-headline-sm block">Station 04 Intake</span>
            <span className="font-data-mono-sm text-[10px] text-on-surface-variant">Handheld scanner mode</span>
          </div>
        </div>

        <div className="space-y-2">
          <button
            onClick={onStartScan}
            className="w-full h-12 bg-secondary hover:bg-secondary/90 text-on-secondary font-headline-sm font-bold rounded-lg flex items-center justify-center gap-2 shadow-sm"
          >
            <span className="material-symbols-outlined text-[20px]">qr_code_scanner</span>
            <span>Scan QR Codes</span>
          </button>
          <button
            onClick={onStartCapture}
            className="w-full h-12 bg-surface-container hover:bg-surface-container-high text-on-surface font-headline-sm font-semibold rounded-lg flex items-center justify-center gap-2 border border-outline-variant"
          >
            <span className="material-symbols-outlined text-[20px]">photo_camera</span>
            <span>Direct Photo Intake</span>
          </button>
        </div>
      </div>

      {/* Queue Section */}
      <div className="bg-surface-container-lowest p-4 rounded-xl shadow-sm border border-surface-container">
        <div className="flex items-center justify-between mb-3 pb-2 border-b border-surface-container">
          <span className="font-headline-sm text-headline-sm">Pending Reviews ({reviews.length})</span>
          <button onClick={onRefresh} className="p-1 rounded bg-surface-container text-on-surface">
            <span className="material-symbols-outlined text-[18px]">refresh</span>
          </button>
        </div>

        {loading ? (
          <div className="py-8 text-center text-on-surface-variant font-data-mono-sm text-xs">
            Loading queue...
          </div>
        ) : reviews.length === 0 ? (
          <div className="py-8 text-center bg-surface-container-low rounded border border-dashed border-outline-variant text-on-surface-variant font-data-mono-sm text-xs">
            No pending return reviews.
          </div>
        ) : (
          <div className="space-y-2">
            {reviews.map((rev) => (
              <div
                key={rev.record_id}
                onClick={() => onSelectRecord(rev.record_id)}
                className="p-3 bg-surface-container-low rounded-lg border border-outline-variant flex items-center justify-between active:bg-surface-container cursor-pointer"
              >
                <div>
                  <span className="font-data-mono-md font-bold text-on-surface block">#{rev.record_id}</span>
                  <span className="font-data-mono-sm text-[10px] text-error font-semibold">NEEDS OVERRIDE</span>
                </div>
                <span className="material-symbols-outlined text-secondary text-[20px]">chevron_right</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function MobileQRScanner({ onBack, onContinue }) {
  const [packageQR, setPackageQR] = useState('');
  const [productQR, setProductQR] = useState('');
  const [verifying, setVerifying] = useState(false);
  const [result, setResult] = useState(null);

  const verify = async (e) => {
    e.preventDefault();
    setVerifying(true);
    try {
      const form = new FormData();
      form.append('package_qr', packageQR);
      form.append('product_qr', productQR);
      const { data } = await axios.post(`${API_BASE}/authentication/verify`, form);
      setResult(data);
    } catch (err) {
      setResult({ error: err.response?.data?.detail ?? err.message });
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="space-y-4 animate-fadeIn">
      <div className="bg-surface-container-lowest p-4 rounded-xl shadow-sm border border-surface-container">
        <span className="font-headline-sm text-headline-sm block mb-1">Package & Product QR</span>
        <span className="font-data-mono-sm text-xs text-on-surface-variant block mb-4">Enter or scan bar identifiers</span>

        <form onSubmit={verify} className="space-y-3 font-data-mono-sm">
          <div>
            <label className="text-[10px] uppercase font-bold text-on-surface-variant block mb-1">Package QR</label>
            <input value={packageQR} onChange={(e) => setPackageQR(e.target.value)} placeholder="PKG-12345" className="w-full h-10 px-3 bg-surface-container-low text-on-surface rounded border border-outline-variant outline-none" required />
          </div>
          <div>
            <label className="text-[10px] uppercase font-bold text-on-surface-variant block mb-1">Product QR</label>
            <input value={productQR} onChange={(e) => setProductQR(e.target.value)} placeholder="PRD-98765" className="w-full h-10 px-3 bg-surface-container-low text-on-surface rounded border border-outline-variant outline-none" required />
          </div>

          <button type="submit" disabled={verifying} className="w-full h-11 bg-primary text-on-primary font-bold rounded-lg flex items-center justify-center gap-1 shadow-sm">
            {verifying ? 'Verifying...' : 'Verify Binding'}
          </button>
        </form>

        {result && !result.error && (
          <div className="mt-3 p-3 bg-surface-container text-on-tertiary-container font-data-mono-sm text-xs rounded border border-on-tertiary-container font-bold">
            {result.qr_auth_result}: {result.message}
          </div>
        )}

        <button
          onClick={() => onContinue({ product_qr: productQR, package_qr: packageQR })}
          disabled={!result || Boolean(result.error)}
          className="mt-4 w-full h-12 bg-secondary text-on-secondary font-bold rounded-lg flex items-center justify-center gap-1 shadow-sm disabled:opacity-40"
        >
          <span>Continue to Photo Intake</span>
          <span className="material-symbols-outlined text-[18px]">chevron_right</span>
        </button>
      </div>
    </div>
  );
}

function MobileCaptureView({ qrAuthData, onBack, onSuccess }) {
  const [images, setImages] = useState([]);
  const [sku, setSku] = useState('SKU-SPEAKER-500');
  const [orderId, setOrderId] = useState('ORD-10482');
  const [submitting, setSubmitting] = useState(false);
  const [showOverrideModal, setShowOverrideModal] = useState(false);
  const cameraRef = useRef(null);

  const handleCapture = (e) => {
    if (e.target.files?.[0]) {
      const file = e.target.files[0];
      setImages((prev) => [...prev, { file, preview: URL.createObjectURL(file) }]);
    }
  };

  const createMockBlob = () => {
    const canvas = document.createElement('canvas');
    canvas.width = 600;
    canvas.height = 400;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#1e293b';
    ctx.fillRect(0, 0, 600, 400);
    ctx.fillStyle = '#38bdf8';
    ctx.font = 'bold 24px monospace';
    ctx.fillText('CUBE HANDHELD MOCK PROOF', 40, 80);
    ctx.fillStyle = '#94a3b8';
    ctx.font = '16px monospace';
    ctx.fillText(`SKU: ${sku}`, 40, 140);
    ctx.fillText(`ORDER: ${orderId}`, 40, 180);
    return new Promise((resolve) => {
      canvas.toBlob((blob) => {
        const file = new File([blob], `mock_mobile.jpg`, { type: 'image/jpeg' });
        resolve(file);
      }, 'image/jpeg');
    });
  };

  const submit = async () => {
    setSubmitting(true);
    try {
      const recordId = `RTN-${Date.now().toString().slice(-6)}`;
      let imagesToSubmit = [...images];
      if (imagesToSubmit.length === 0) {
        const mockFile = await createMockBlob();
        imagesToSubmit = [{ file: mockFile, preview: URL.createObjectURL(mockFile) }];
      }

      const mediaRefs = [];

      for (const img of imagesToSubmit) {
        const form = new FormData();
        form.append('file', img.file);
        form.append('record_id', recordId);
        form.append('organization_id', DEMO_ORG);
        const { data } = await axios.post(`${API_BASE}/media`, form);
        mediaRefs.push(data.storage_ref);
      }

      const payload = {
        record_id: recordId,
        unit_id: `UNIT-${recordId}`,
        org_id: DEMO_ORG,
        order_id: orderId,
        ordered_sku: sku,
        ordered_asin: 'B0DUMMY729',
        parts_list: 'cable;manual;adapter',
        photo_refs: mediaRefs.join(';'),
        operator_id: DEMO_OPERATOR,
        captured_at: new Date().toISOString(),
        ...(qrAuthData ?? {}),
      };

      const { data } = await axios.post(`${API_BASE}/inspect`, payload);
      onSuccess(data);
    } catch (err) {
      alert('Inspection failed: ' + (err.response?.data?.detail ?? err.message));
    } finally {
      setSubmitting(false);
    }
  };


  return (
    <div className="space-y-4 animate-fadeIn pb-8">
      {/* Photo Quality & Live View Card */}
      <div className="bg-surface-container-lowest p-4 rounded-xl shadow-sm border border-surface-container">
        <div className="flex items-center justify-between mb-3">
          <span className="font-headline-sm text-headline-sm">Capture QA Pre-Check</span>
          <span className="font-data-mono-sm text-[10px] text-on-tertiary-container font-bold">3/4 PASSED</span>
        </div>

        <div className="relative aspect-[4/3] rounded-lg overflow-hidden bg-inverse-surface mb-3 flex items-center justify-center">
          {images.length > 0 ? (
            <img src={images[images.length - 1].preview} alt="Captured" className="w-full h-full object-cover" />
          ) : (
            <div className="text-center text-on-surface-variant font-data-mono-sm text-xs p-4">
              <span className="material-symbols-outlined text-[32px] text-outline block mb-1">photo_camera</span>
              Tap Retake to capture return parcel photo
            </div>
          )}
          <div className="absolute top-2 left-2 bg-primary/80 text-on-primary font-data-mono-sm text-[9px] px-1.5 py-0.5 rounded">
            ROI-PRIMARY :: 88%
          </div>
        </div>

        {/* 2x2 Core Metrics Grid */}
        <div className="grid grid-cols-2 gap-2 font-data-mono-sm text-xs mb-3">
          <div className="p-2 bg-surface-container-low rounded">
            <span className="text-outline text-[9px] block">BLUR</span>
            <span className="font-bold text-on-surface">94 / 100</span>
          </div>
          <div className="p-2 bg-error-container text-on-error-container rounded">
            <span className="text-error text-[9px] font-bold block">GLARE</span>
            <span className="font-bold">TAG UNREADABLE</span>
          </div>
        </div>

        <div className="space-y-2">
          <button
            onClick={() => cameraRef.current?.click()}
            className="w-full h-11 bg-primary text-on-primary font-bold rounded-lg flex items-center justify-between px-3 shadow-sm"
          >
            <span className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px]">photo_camera</span>
              <span>Retake Photo</span>
            </span>
            <span className="bg-primary-container text-on-primary text-[10px] px-1.5 py-0.5 rounded font-mono">[SPACE]</span>
          </button>

          <button
            onClick={() => setShowOverrideModal(true)}
            className="w-full h-10 bg-surface-container text-on-surface font-medium rounded-lg flex items-center justify-between px-3 text-xs border border-outline-variant"
          >
            <span>Override QA Gate</span>
            <span className="font-mono text-[10px] text-on-surface-variant">[F4]</span>
          </button>
        </div>

        <input ref={cameraRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={handleCapture} />
      </div>

      <button
        onClick={submit}
        disabled={submitting || images.length === 0}
        className="w-full h-12 bg-secondary text-on-secondary font-bold rounded-lg flex items-center justify-center gap-1 shadow-sm disabled:opacity-40"
      >
        {submitting ? 'Inspecting...' : 'Submit Return Intake'}
      </button>

      {/* Supervisor Override Sheet */}
      {showOverrideModal && (
        <div className="fixed inset-0 z-50 bg-primary/60 backdrop-blur-sm flex flex-col justify-end">
          <div className="bg-surface-container-lowest p-4 rounded-t-xl space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-surface-container">
              <span className="font-headline-sm font-bold text-on-surface">Supervisor Override Authorization</span>
              <button onClick={() => setShowOverrideModal(false)} className="text-on-surface-variant">
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>
            <p className="font-body-sm text-xs text-on-surface-variant">Scan Lead Badge ID to authorize glare bypass exception.</p>
            <input type="password" value="••••••••" readOnly className="w-full h-10 px-3 bg-surface-container-low font-mono text-sm rounded border border-outline-variant" />
            <div className="flex gap-2">
              <button onClick={() => setShowOverrideModal(false)} className="flex-1 h-10 bg-surface-container font-semibold text-xs rounded">Cancel</button>
              <button onClick={() => { setShowOverrideModal(false); alert('Bypass Authorized!'); }} className="flex-1 h-10 bg-error text-on-error font-bold text-xs rounded">Authorize [F4]</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function MobileDetailView({ recordId, onBack, onResolved }) {
  const [record, setRecord] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const { data } = await axios.get(`${API_BASE}/returns/${recordId}`, { params: { org_id: DEMO_ORG } });
        setRecord(data);
      } catch (err) {
        setRecord({ error: err.message });
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [recordId]);

  if (loading) return <div className="py-12 text-center font-data-mono-sm text-xs">Loading detail...</div>;
  if (!record || record.error) return <div className="p-4 bg-error-container text-on-error-container text-xs rounded">Failed to load record.</div>;

  return (
    <div className="space-y-4 animate-fadeIn pb-8">
      <div className="bg-surface-container-lowest p-4 rounded-xl shadow-sm border border-surface-container">
        <span className="font-label-caps text-[10px] text-outline uppercase block mb-1">RECORD #{record.record_id}</span>
        <span className="font-headline-md font-bold text-on-surface block mb-2">{record.subject}</span>
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 bg-surface-container font-data-mono-sm text-xs font-bold rounded">{record.outcome}</span>
          <span className="px-2 py-0.5 bg-error-container text-error font-data-mono-sm text-xs font-bold rounded">{record.status}</span>
        </div>
      </div>

      <div className="bg-surface-container-lowest p-4 rounded-xl shadow-sm border border-surface-container space-y-2">
        <span className="font-headline-sm font-semibold text-on-surface block mb-2">Checks Traceability</span>
        {record.checks?.map((c, i) => (
          <div key={i} className="p-2 bg-surface-container-low rounded font-data-mono-sm text-xs">
            <div className="font-bold uppercase text-on-surface">{c.check_key}: {c.verdict}</div>
            <div className="text-on-surface-variant text-[11px] mt-0.5">{c.detail}</div>
          </div>
        ))}
      </div>
    </div>
  );
}