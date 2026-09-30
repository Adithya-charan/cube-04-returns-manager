import React, { useState, useRef, useCallback, useEffect } from 'react';
import axios from 'axios';
import {
  Camera, Upload, CheckCircle, XCircle, AlertCircle, RefreshCw,
  Eye, ArrowLeft, Loader2, FileImage, ShieldCheck, ClipboardList,
  UserCheck, ChevronRight, Info, Zap, QrCode
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';
const DEMO_ORG = 'org_demo_alpha';
const DEMO_OPERATOR = 'op_mobile_user';

// ─── Utility Components ───────────────────────────────────────────────────────

const VerdictIcon = ({ verdict }) => {
  if (verdict === 'PASS') return <CheckCircle className="text-emerald-400 w-5 h-5 shrink-0" />;
  if (verdict === 'FAIL') return <XCircle className="text-red-400 w-5 h-5 shrink-0" />;
  return <AlertCircle className="text-amber-400 w-5 h-5 shrink-0" />;
};

const VerdictPill = ({ verdict }) => {
  const cls = verdict === 'PASS' ? 'pill-pass' : verdict === 'FAIL' ? 'pill-fail' : 'pill-uncertain';
  return (
    <span className={`text-xs font-mono font-semibold px-2 py-0.5 rounded ${cls}`}>
      {verdict}
    </span>
  );
};

const DispositionBadge = ({ disposition }) => {
  const cls = `disposition-${disposition}`;
  return (
    <span className={`text-sm font-bold uppercase tracking-wider px-4 py-1.5 rounded-full ${cls}`}>
      {disposition?.replace('_', ' ')}
    </span>
  );
};

// ─── Views ────────────────────────────────────────────────────────────────────

function DashboardView({ onNewInspection, reviews, onReview, loading }) {
  const [lanUrl, setLanUrl] = useState(null);

  useEffect(() => {
    // Try to determine LAN IP for phone access
    // This is a hint - user needs to replace with actual PC LAN IP
    const hostname = window.location.hostname;
    if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
      setLanUrl(`http://${hostname}:5173`);
    }
  }, []);

  return (
    <div className="space-y-6">
      {/* Hero CTA */}
      <div className="glass rounded-2xl p-6 space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-500/20 flex items-center justify-center">
            <Zap className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <h2 className="font-bold text-white">New Inspection</h2>
            <p className="text-xs text-slate-400">Capture photos · Ollama AI analysis · Instant disposition</p>
          </div>
        </div>
        <button
          onClick={onNewInspection}
          className="w-full bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white font-semibold py-3 rounded-xl flex items-center justify-center gap-2 transition-colors"
        >
          <Camera className="w-5 h-5" /> Start Inspection (Visual Only)
        </button>
        <button
          onClick={() => onNewInspection('qr')}
          className="w-full bg-slate-800 hover:bg-slate-700 active:bg-slate-600 border border-slate-700 text-white font-semibold py-3 rounded-xl flex items-center justify-center gap-2 transition-colors"
        >
          <QrCode className="w-5 h-5 text-blue-400" /> Start QR + Visual Inspection
        </button>
        {lanUrl && (
          <div className="text-xs text-slate-500 bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
            <p className="font-semibold text-blue-400 mb-1">📱 Mobile Access</p>
            <p>Open this URL on your phone (same Wi-Fi):</p>
            <code className="text-blue-300 break-all">{lanUrl}</code>
            <p className="mt-1 text-xs text-slate-500">Backend API must be accessible at <code>http://{window.location.hostname}:8000</code></p>
          </div>
        )}
      </div>

      {/* Pending Reviews */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs font-bold text-slate-500 uppercase tracking-widest">Pending Review</h2>
          <button onClick={() => window.location.reload()} className="text-slate-500 hover:text-slate-300 transition-colors">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {loading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="animate-spin text-slate-600 w-8 h-8" />
          </div>
        ) : reviews.length === 0 ? (
          <div className="glass rounded-xl p-8 text-center space-y-2">
            <ShieldCheck className="w-10 h-10 mx-auto text-emerald-500/40" />
            <p className="text-slate-400 text-sm">No pending reviews</p>
          </div>
        ) : (
          <div className="space-y-2">
            {reviews.map(r => (
              <div key={r.record_id} className="glass rounded-xl p-4 flex justify-between items-center">
                <div className="space-y-1">
                  <p className="font-semibold text-slate-100 font-mono text-sm">{r.record_id}</p>
                  <span className="pill-pending text-xs px-2 py-0.5 rounded font-mono font-semibold">
                    PENDING REVIEW
                  </span>
                </div>
                <button
                  onClick={() => onReview(r.record_id)}
                  className="flex items-center gap-1 text-xs bg-white/5 hover:bg-white/10 border border-white/10 px-3 py-2 rounded-lg text-slate-300 transition-colors"
                >
                  <Eye className="w-4 h-4" /> Resolve
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function QRScanView({ onBack, onContinue }) {
  const [packageQR, setPackageQR] = useState('');
  const [productQR, setProductQR] = useState('');
  const [verifying, setVerifying] = useState(false);
  const [result, setResult] = useState(null);

  const verify = async (e) => {
    e.preventDefault();
    if (!packageQR || !productQR) return;
    setVerifying(true);
    setResult(null);
    try {
      const form = new FormData();
      form.append('package_qr', packageQR);
      form.append('product_qr', productQR);
      const { data } = await axios.post(`${API_BASE}/authentication/verify`, form);
      setResult(data);
    } catch (err) {
      setResult({ error: err.response?.data?.detail ?? err.message });
    }
    setVerifying(false);
  };

  return (
    <div className="space-y-5 animate-fadeIn">
      <button type="button" onClick={onBack} className="flex items-center gap-1.5 text-blue-400 text-sm font-medium mb-2">
        <ArrowLeft className="w-4 h-4" /> Cancel
      </button>

      <div className="glass rounded-2xl p-5 space-y-4">
        <h2 className="font-bold text-slate-200 border-b border-white/10 pb-3 flex items-center gap-2">
          <QrCode className="w-5 h-5 text-blue-400" /> Package & Product Authentication
        </h2>
        <p className="text-sm text-slate-400">Scan or enter the opaque QR identifiers.</p>

        <form onSubmit={verify} className="space-y-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Package QR ID</label>
            <input value={packageQR} onChange={e => setPackageQR(e.target.value)}
              placeholder="e.g. PKG-12345"
              className="w-full bg-white/5 border border-white/10 px-3 py-2.5 rounded-lg text-slate-100 placeholder-slate-600 focus:outline-none" required />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Product QR ID</label>
            <input value={productQR} onChange={e => setProductQR(e.target.value)}
              placeholder="e.g. PRD-98765"
              className="w-full bg-white/5 border border-white/10 px-3 py-2.5 rounded-lg text-slate-100 placeholder-slate-600 focus:outline-none" required />
          </div>
          <button type="submit" disabled={verifying || !packageQR || !productQR}
            className="w-full bg-blue-600/20 text-blue-400 hover:bg-blue-600/30 border border-blue-500/30 font-bold py-3 rounded-xl transition-all disabled:opacity-40">
            {verifying ? <Loader2 className="w-5 h-5 animate-spin mx-auto" /> : "Verify Binding"}
          </button>
        </form>

        {result && !result.error && (
          <div className={`mt-4 p-4 rounded-xl border ${result.qr_auth_result === 'AUTHENTICATED' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' : 'bg-amber-500/10 border-amber-500/30 text-amber-400'}`}>
            <p className="font-bold mb-1">{result.qr_auth_result}</p>
            <p className="text-sm opacity-90">{result.message}</p>
          </div>
        )}
        {result?.error && (
          <div className="mt-4 p-4 rounded-xl border bg-red-500/10 border-red-500/30 text-red-400">
            {result.error}
          </div>
        )}
      </div>

      <button
        onClick={() => onContinue(result?.qr_auth_result || null)}
        className="w-full bg-slate-100 hover:bg-white text-slate-900 font-bold py-4 rounded-xl flex items-center justify-center gap-2 transition-all shadow-lg"
      >
        Continue to Visual Inspection <ChevronRight className="w-5 h-5" />
      </button>
    </div>
  );
}

function ScannerView({ onBack, onResult, qrAuthResult }) {
  const [recordId] = useState(`RTN-${Date.now().toString().slice(-6)}`);
  const [sku, setSku] = useState('');
  const [parts, setParts] = useState('');
  const [capturedImages, setCapturedImages] = useState([]); // { file, preview }
  const [processing, setProcessing] = useState('idle'); // idle | uploading | inspecting | done | error
  const [statusMsg, setStatusMsg] = useState('');
  const fileRef = useRef();
  const cameraRef = useRef();

  const addFile = useCallback((file) => {
    const preview = URL.createObjectURL(file);
    setCapturedImages(prev => [...prev, { file, preview }]);
  }, []);

  const handleFileChange = (e) => {
    Array.from(e.target.files).forEach(addFile);
    e.target.value = '';
  };

  const handleCapture = (e) => {
    const file = e.target.files[0];
    if (file) addFile(file);
    e.target.value = '';
  };

  const removeImage = (idx) => {
    setCapturedImages(prev => prev.filter((_, i) => i !== idx));
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!capturedImages.length) return alert('Please capture or upload at least one photo.');
    if (!sku.trim()) return alert('Expected SKU is required.');

    setProcessing('uploading');

    // Step 1: Upload all images to /media
    const mediaRefs = [];
    try {
      for (const img of capturedImages) {
        setStatusMsg(`Uploading ${img.file.name}…`);
        const form = new FormData();
        form.append('file', img.file);
        form.append('record_id', recordId);
        form.append('organization_id', DEMO_ORG);
        const { data } = await axios.post(`${API_BASE}/media`, form);
        mediaRefs.push(data.storage_ref);
      }
    } catch (err) {
      setProcessing('error');
      setStatusMsg(`Upload failed: ${err.response?.data?.detail ?? err.message}`);
      return;
    }

    // Step 2: Trigger inspection pipeline with progressive status updates
    setProcessing('inspecting');
    let statusIndex = 0;
    const statusMessages = [
      'Sending to Ollama qwen3-vl:8b…',
      'Analyzing product identity…',
      'Checking included components…',
      'Evaluating visible condition…',
      'Preparing return decision…',
    ];
    const updateStatus = () => {
      if (statusIndex < statusMessages.length) {
        setStatusMsg(statusMessages[statusIndex]);
        statusIndex++;
      }
    };
    updateStatus();
    const statusInterval = setInterval(updateStatus, 15000); // Update every 15s

    const payload = {
      record_id: recordId,
      unit_id: `UNIT-${recordId}`,
      org_id: DEMO_ORG,
      order_id: `ORD-${recordId}`,
      ordered_sku: sku.trim(),
      ordered_asin: 'ASIN-DEMO',
      parts_list: parts.trim() || 'product',
      photo_refs: mediaRefs.join(';'),
      operator_id: DEMO_OPERATOR,
      captured_at: new Date().toISOString(),
      qr_auth_result: qrAuthResult
    };

    try {
      const { data } = await axios.post(`${API_BASE}/inspect`, payload);
      clearInterval(statusInterval);
      setProcessing('done');
      onResult(data);
    } catch (err) {
      clearInterval(statusInterval);
      setProcessing('error');
      setStatusMsg(`Inspection failed: ${err.response?.data?.detail ?? err.message}`);
    }
  };

  const busy = processing === 'uploading' || processing === 'inspecting';

  return (
    <form onSubmit={submit} className="space-y-5">
      <button type="button" onClick={onBack} className="flex items-center gap-1.5 text-blue-400 text-sm font-medium mb-2">
        <ArrowLeft className="w-4 h-4" /> Cancel
      </button>

      {/* Unit Details */}
      <div className="glass rounded-2xl p-5 space-y-4">
        <h2 className="font-bold text-slate-200 border-b border-white/10 pb-3">Unit Details</h2>

        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Record ID</label>
          <input value={recordId} readOnly
            className="w-full bg-white/5 border border-white/10 px-3 py-2.5 rounded-lg text-slate-300 font-mono text-sm focus:outline-none" />
        </div>

        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Expected SKU *</label>
          <input value={sku} onChange={e => setSku(e.target.value)}
            placeholder="e.g. SKU-SPEAKER-500"
            className="w-full bg-white/5 border border-white/10 px-3 py-2.5 rounded-lg text-slate-100 placeholder-slate-600 focus:outline-none focus:border-blue-500/50 transition-colors"
            required />
        </div>

        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Expected Parts (semicolon separated)</label>
          <input value={parts} onChange={e => setParts(e.target.value)}
            placeholder="e.g. cable;manual;adapter"
            className="w-full bg-white/5 border border-white/10 px-3 py-2.5 rounded-lg text-slate-100 placeholder-slate-600 focus:outline-none focus:border-blue-500/50 transition-colors" />
        </div>
      </div>

      {/* Image Capture */}
      <div className="glass rounded-2xl p-5 space-y-4">
        <h2 className="font-bold text-slate-200 border-b border-white/10 pb-3">
          Photos <span className="text-xs text-slate-500 font-normal ml-1">(sent directly to qwen3-vl:8b)</span>
        </h2>

        {capturedImages.length > 0 && (
          <div className="grid grid-cols-3 gap-2">
            {capturedImages.map((img, i) => (
              <div key={i} className="relative aspect-square rounded-lg overflow-hidden">
                <img src={img.preview} alt="" className="w-full h-full object-cover" />
                <button
                  type="button"
                  onClick={() => removeImage(i)}
                  className="absolute top-1 right-1 w-5 h-5 rounded-full bg-black/70 text-red-400 flex items-center justify-center text-xs leading-none"
                >×</button>
              </div>
            ))}
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          {/* Camera capture (mobile) */}
          <button type="button" onClick={() => cameraRef.current.click()}
            className="flex flex-col items-center gap-2 py-5 rounded-xl border-2 border-dashed border-white/20 hover:border-blue-500/40 text-slate-400 hover:text-blue-400 transition-all bg-white/[0.02]">
            <Camera className="w-7 h-7" />
            <span className="text-xs font-medium">Camera</span>
          </button>
          {/* File upload */}
          <button type="button" onClick={() => fileRef.current.click()}
            className="flex flex-col items-center gap-2 py-5 rounded-xl border-2 border-dashed border-white/20 hover:border-blue-500/40 text-slate-400 hover:text-blue-400 transition-all bg-white/[0.02]">
            <FileImage className="w-7 h-7" />
            <span className="text-xs font-medium">Upload</span>
          </button>
        </div>

        <input ref={cameraRef} type="file" accept="image/*" capture="environment"
          className="hidden" onChange={handleCapture} />
        <input ref={fileRef} type="file" accept="image/*" multiple
          className="hidden" onChange={handleFileChange} />
      </div>

      {/* Submit */}
      <button
        type="submit"
        disabled={busy}
        className="w-full bg-slate-100 hover:bg-white disabled:opacity-40 text-slate-900 font-bold py-4 rounded-xl flex items-center justify-center gap-2 transition-all shadow-lg"
      >
        {busy ? (
          <><Loader2 className="w-5 h-5 animate-spin" /> {statusMsg || 'Processing…'}</>
        ) : (
          <><Zap className="w-5 h-5" /> Inspect Return</>
        )}
      </button>

      {processing === 'error' && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm">
          {statusMsg}
        </div>
      )}
    </form>
  );
}

function CheckRow({ check }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border border-white/10 rounded-xl overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between p-4 text-left hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-3">
          <VerdictIcon verdict={check.verdict} />
          <span className="font-semibold capitalize text-slate-200">{check.check_key}</span>
        </div>
        <div className="flex items-center gap-2">
          <VerdictPill verdict={check.verdict} />
          <ChevronRight className={`w-4 h-4 text-slate-500 transition-transform ${open ? 'rotate-90' : ''}`} />
        </div>
      </button>
      {open && (
        <div className="px-4 pb-4 space-y-2 border-t border-white/5 pt-3">
          <p className="text-sm text-slate-400">{check.detail}</p>
          <div className="flex gap-4 text-xs text-slate-600">
            <span>Confidence: <span className="text-slate-400">{(check.confidence * 100).toFixed(0)}%</span></span>
            {check.latency_ms && <span>Latency: <span className="text-slate-400">{check.latency_ms}ms</span></span>}
          </div>
        </div>
      )}
    </div>
  );
}

function ResultView({ result, onBack, onResolve }) {
  const isComplete = result.status === 'completed';
  const needsReview = result.status === 'pending_review';

  return (
    <div className="space-y-5 animate-fadeIn">
      <button onClick={onBack} className="flex items-center gap-1.5 text-blue-400 text-sm font-medium">
        <ArrowLeft className="w-4 h-4" /> Dashboard
      </button>

      {/* Disposition header */}
      <div className={`glass rounded-2xl p-6 ${needsReview ? 'border-violet-500/30' : 'border-emerald-500/20'}`}>
        <p className="text-xs text-slate-500 font-semibold uppercase tracking-widest mb-3">System Decision</p>
        <DispositionBadge disposition={result.outcome} />
        <div className="flex items-center gap-3 mt-4 text-sm">
          <span className={`font-semibold ${isComplete ? 'text-emerald-400' : 'text-violet-400'}`}>
            {isComplete ? 'Completed' : 'Pending Review'}
          </span>
          <span className="text-slate-600">·</span>
          <span className="text-slate-500 font-mono text-xs">{result.record_id}</span>
        </div>
        {needsReview && (
          <div className="mt-4 flex items-start gap-2 text-sm text-violet-300 bg-violet-500/10 border border-violet-500/20 rounded-lg p-3">
            <Info className="w-4 h-4 shrink-0 mt-0.5" />
            AI confidence insufficient. Human override required.
          </div>
        )}
      </div>

      {/* AI Checks */}
      <div className="glass rounded-2xl p-5 space-y-3">
        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-3">Evidence Checks</h3>
        {result.checks.map((c, i) => <CheckRow key={i} check={c} />)}
      </div>

      {/* Overrides */}
      {result.overrides?.length > 0 && (
        <div className="glass rounded-2xl p-5 space-y-3">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest">Human Overrides</h3>
          {result.overrides.map((o, i) => (
            <div key={i} className="bg-white/5 rounded-xl p-4 space-y-1">
              <div className="flex items-center gap-2 text-sm">
                <UserCheck className="w-4 h-4 text-blue-400" />
                <span className="font-semibold text-slate-200">{o.operator_id}</span>
                <span className="text-slate-500">·</span>
                <span className="font-mono text-xs text-slate-400">{o.original_verdict} → {o.new_verdict}</span>
              </div>
              <p className="text-xs text-slate-500">{o.reason}</p>
            </div>
          ))}
        </div>
      )}

      {/* Human Override for pending */}
      {needsReview && (
        <div className="glass rounded-2xl p-5 space-y-3">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest">Override Disposition</h3>
          <div className="grid grid-cols-2 gap-2">
            {['restock', 'refurbish', 'liquidate', 'dispose'].map(d => (
              <button
                key={d}
                onClick={() => onResolve(result.record_id, d)}
                className={`py-3 rounded-xl text-sm font-bold capitalize border transition-colors
                  ${d === 'dispose'
                    ? 'bg-red-500/10 border-red-500/30 text-red-400 hover:bg-red-500/20'
                    : 'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10'}`}
              >
                {d}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ReviewView({ recordId, orgId, onBack, onResolved }) {
  const [resolving, setResolving] = useState(null);

  const resolve = async (disposition) => {
    setResolving(disposition);
    try {
      await axios.post(
        `${API_BASE}/reviews/${recordId}/resolve`,
        null,
        { params: { new_disposition: disposition, operator_id: DEMO_OPERATOR, org_id: orgId, reason: 'Mobile operator override' } }
      );
      onResolved();
    } catch (e) {
      alert('Override failed: ' + (e.response?.data?.detail ?? e.message));
      setResolving(null);
    }
  };

  return (
    <div className="space-y-5">
      <button onClick={onBack} className="flex items-center gap-1.5 text-blue-400 text-sm font-medium">
        <ArrowLeft className="w-4 h-4" /> Cancel
      </button>
      <div className="glass rounded-2xl p-6 space-y-4">
        <div>
          <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-1">Resolving Review</p>
          <p className="font-mono font-semibold text-slate-200">{recordId}</p>
        </div>
        <p className="text-sm text-slate-400">
          AI inspection was insufficient to determine an authoritative disposition.
          Select the correct outcome based on your physical inspection.
        </p>
        <div className="grid grid-cols-2 gap-3">
          {['restock', 'refurbish', 'liquidate', 'dispose'].map(d => (
            <button
              key={d}
              onClick={() => resolve(d)}
              disabled={resolving !== null}
              className={`py-4 rounded-xl font-bold capitalize border transition-colors
                ${d === 'dispose'
                  ? 'bg-red-500/10 border-red-500/30 text-red-400 hover:bg-red-500/20'
                  : 'bg-white/5 border-white/10 text-slate-200 hover:bg-white/10'}
                disabled:opacity-40`}
            >
              {resolving === d ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : d}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── App Root ─────────────────────────────────────────────────────────────────

import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';

function WebsiteDashboard() {
  const [reviews, setReviews] = useState([]);
  const [loadingReviews, setLoadingReviews] = useState(true);
  const navigate = useNavigate();

  const fetchReviews = useCallback(async () => {
    setLoadingReviews(true);
    try {
      const { data } = await axios.get(`${API_BASE}/reviews`, { params: { org_id: DEMO_ORG } });
      setReviews(data);
    } catch { setReviews([]); }
    setLoadingReviews(false);
  }, []);

  useEffect(() => { fetchReviews(); }, [fetchReviews]);

  return <DashboardView
    onNewInspection={(mode) => navigate(`/mobile${mode === 'qr' ? '?flow=qr' : ''}`)}
    reviews={reviews}
    onReview={(id) => navigate(`/website/review/${id}`)}
    loading={loadingReviews}
  />;
}

function WebsiteReview() {
  const location = useLocation();
  const navigate = useNavigate();
  // Extract ID from path
  const recordId = location.pathname.split('/').pop();

  return <ReviewView
    recordId={recordId}
    orgId={DEMO_ORG}
    onBack={() => navigate('/website')}
    onResolved={() => navigate('/website')}
  />;
}

function MobileCapture() {
  const navigate = useNavigate();
  const location = useLocation();
  const [qrAuthResult, setQrAuthResult] = useState(null);

  const queryParams = new URLSearchParams(location.search);
  const flow = queryParams.get('flow');
  const [step, setStep] = useState(flow === 'qr' ? 'qr' : 'vision'); // qr -> vision

  const handleResult = (result) => {
    navigate('/result', { state: { result } });
  };

  if (step === 'qr') {
    return (
      <QRScanView
        onBack={() => navigate('/')}
        onContinue={(res) => {
          setQrAuthResult(res);
          setStep('vision');
        }}
      />
    );
  }

  return (
    <ScannerView
      onBack={() => navigate('/')}
      onResult={handleResult}
      qrAuthResult={qrAuthResult}
    />
  );
}

function MobileResult() {
  const location = useLocation();
  const navigate = useNavigate();
  const result = location.state?.result;

  if (!result) return <Navigate to="/mobile" />;

  const handleResolve = async (recordId, disposition) => {
    try {
      await axios.post(
        `${API_BASE}/reviews/${recordId}/resolve`,
        null,
        { params: { new_disposition: disposition, operator_id: DEMO_OPERATOR, org_id: DEMO_ORG, reason: 'Mobile operator override from result view' } }
      );
      navigate('/mobile');
    } catch (e) {
      alert('Override failed: ' + (e.response?.data?.detail ?? e.message));
    }
  };

  return <ResultView result={result} onBack={() => navigate('/mobile')} onResolve={handleResolve} />;
}

function AppLayout() {
  return (
    <div className="min-h-screen bg-slate-950 pb-8">
      {/* Top bar */}
      <header className="sticky top-0 z-20 bg-slate-950/90 backdrop-blur-md border-b border-white/5">
        <div className="max-w-lg mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center">
              <ClipboardList className="w-4 h-4 text-blue-400" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-white leading-none">Returns Manager</h1>
              <p className="text-xs text-slate-500 leading-none mt-0.5">Ollama · Qwen3-VL + YOLO</p>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs text-slate-500">Local AI</span>
          </div>
        </div>
      </header>

      <main className="max-w-lg mx-auto px-4 pt-6">
        <Routes>
          <Route path="/" element={<MobileCapture />} />
          <Route path="/result" element={<MobileResult />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Router>
      <AppLayout />
    </Router>
  );
}
