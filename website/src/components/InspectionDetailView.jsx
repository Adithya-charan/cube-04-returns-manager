import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

export default function InspectionDetailView({ recordId, orgId, onBack, onResolved }) {
    const [record, setRecord] = useState(null);
    const [evidence, setEvidence] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Overlay toggles
    const [showOverlay, setShowOverlay] = useState(true);
    const [overlayType, setOverlayType] = useState('yolo'); // 'yolo', 'ocr', 'heatmap'
    const [selectedThumb, setSelectedThumb] = useState(0);
    const [yoloDetections, setYoloDetections] = useState([]);

    // Override controls state
    const [disposition, setDisposition] = useState('LIQUIDATE');
    const [reasonCode, setReasonCode] = useState('NON_OEM_ACCESSORY_DETECTED');
    const [notes, setNotes] = useState('Slot 3 battery confirmed generic replica by optical serial mismatch. Unit diverted to bulk liquidation tote #LQ-09.');
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        let isMounted = true;
        async function loadData() {
            try {
                setLoading(true);
                const [recRes, evRes, yoloRes] = await Promise.all([
                    axios.get(`${API_BASE}/returns/${recordId}`, { params: { org_id: orgId } }),
                    axios.get(`${API_BASE}/returns/${recordId}/evidence`, { params: { org_id: orgId } }),
                    axios.get(`${API_BASE}/returns/${recordId}/yolo`, { params: { org_id: orgId } }).catch(() => ({ data: [] })),
                ]);
                if (isMounted) {
                    setRecord(recRes.data);
                    setEvidence(evRes.data || []);
                    setYoloDetections(yoloRes.data || []);
                    if (recRes.data?.outcome) {
                        setDisposition(recRes.data.outcome.toUpperCase());
                    }
                }
            } catch (err) {
                if (isMounted) {
                    setError(err.response?.data?.detail ?? err.message);
                }
            } finally {
                if (isMounted) setLoading(false);
            }
        }
        loadData();
        return () => { isMounted = false; };
    }, [recordId, orgId]);


    const handleResolve = async () => {
        setSubmitting(true);
        try {
            await axios.post(`${API_BASE}/reviews/${recordId}/resolve`, null, {
                params: {
                    new_disposition: disposition.toLowerCase(),
                    operator_id: 'E. Marcus (Supv #OP-449)',
                    org_id: orgId,
                    reason: `${reasonCode}: ${notes}`,
                },
            });
            if (onResolved) onResolved();
        } catch (err) {
            alert('Override submission failed: ' + (err.response?.data?.detail ?? err.message));
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center py-20 text-on-surface-variant">
                <span className="material-symbols-outlined text-[36px] animate-spin text-secondary mb-2">autorenew</span>
                <p className="font-data-mono-md text-data-mono-md">Loading return telemetry & evidence...</p>
            </div>
        );
    }

    if (error || !record) {
        return (
            <div className="p-space-md bg-error-container text-on-error-container rounded-xl">
                <p className="font-headline-sm text-headline-sm mb-1">Record Error</p>
                <p className="font-body-md text-body-md">{error || 'Return record not found.'}</p>
                <button onClick={onBack} className="mt-4 px-space-md py-1 bg-error text-on-error rounded font-data-mono-sm">
                    Return to Queue
                </button>
            </div>
        );
    }

    const isPending = record.status === 'pending_review';

    return (
        <div className="flex flex-col w-full animate-fadeIn pb-12">
            {/* Top Header Card */}
            <div className="w-full bg-surface-container-lowest p-space-md mb-space-md shadow-sm rounded">
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-space-md">
                    <div className="flex flex-col gap-space-xs">
                        <div className="flex flex-wrap items-center gap-space-xs font-data-mono-sm text-data-mono-sm">
                            <button onClick={onBack} className="text-on-surface-variant hover:text-on-surface font-label-caps uppercase tracking-wider flex items-center gap-1">
                                <span className="material-symbols-outlined text-[14px]">arrow_back</span> INTAKE QUEUE
                            </button>
                            <span className="material-symbols-outlined text-[14px] text-outline">chevron_right</span>
                            <span className="text-secondary font-bold">DC09-DOCK-R04</span>
                            <span className="material-symbols-outlined text-[14px] text-outline">chevron_right</span>
                            <span className="bg-surface-container px-space-xs py-0.5 rounded text-on-surface font-semibold">
                                RETURN #{record.record_id}
                            </span>
                            <span className={`inline-flex items-center gap-1 ml-space-xs px-2 py-0.5 rounded font-label-caps text-label-caps tracking-wider ${isPending ? 'bg-error-container text-on-error-container' : 'bg-surface-container text-on-tertiary-container font-bold'
                                }`}>
                                <span className="material-symbols-outlined text-[14px] animate-pulse">
                                    {isPending ? 'priority_high' : 'check_circle'}
                                </span>
                                {isPending ? 'PENDING SUPERVISOR REVIEW' : 'INSPECTION COMPLETED'}
                            </span>
                        </div>

                        <div className="flex flex-wrap items-center gap-x-space-lg gap-y-1 mt-1 font-body-sm text-body-sm text-on-surface-variant">
                            <div><span className="text-outline uppercase text-[10px] block font-label-caps">UNIT SUBJECT</span><span className="font-data-mono-md text-data-mono-md font-semibold text-on-surface">{record.subject}</span></div>
                            <div><span className="text-outline uppercase text-[10px] block font-label-caps">ORGANIZATION</span><span className="font-data-mono-md text-data-mono-md text-on-surface">{record.organization_id}</span></div>
                            <div><span className="text-outline uppercase text-[10px] block font-label-caps">CAPTURED STAMP</span><span className="font-data-mono-md text-data-mono-md text-on-surface">{new Date(record.captured_at).toLocaleTimeString()}</span></div>
                            <div><span className="text-outline uppercase text-[10px] block font-label-caps">OPERATOR</span><span className="font-body-sm text-body-sm font-medium text-on-surface">{record.operator_label}</span></div>
                        </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-space-xs">
                        <button className="h-9 px-space-sm bg-surface-container text-on-surface hover:bg-surface-container-high font-data-mono-sm text-data-mono-sm rounded flex items-center gap-space-xs transition-colors shadow-sm">
                            <span className="material-symbols-outlined text-[16px]">print</span>
                            <span>Print LPN</span>
                            <span className="bg-surface-container-highest px-1 py-0.2 rounded text-[10px] text-on-surface-variant ml-1">[F2]</span>
                        </button>
                        <button className="h-9 px-space-sm bg-surface-container text-on-surface hover:bg-surface-container-high font-data-mono-sm text-data-mono-sm rounded flex items-center gap-space-xs transition-colors shadow-sm">
                            <span className="material-symbols-outlined text-[16px]">auto_detect_voice</span>
                            <span>Re-run Vision</span>
                            <span className="bg-surface-container-highest px-1 py-0.2 rounded text-[10px] text-on-surface-variant ml-1">[F4]</span>
                        </button>
                        <button className="h-9 px-space-md bg-primary text-on-primary hover:bg-surface-tint font-data-mono-sm text-data-mono-sm rounded flex items-center gap-space-xs transition-colors shadow-sm">
                            <span className="material-symbols-outlined text-[16px]">download</span>
                            <span>Export Audit Packet</span>
                        </button>
                    </div>
                </div>
            </div>

            {/* 3-Column Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-md mb-space-md">
                {/* LEFT COLUMN: Proof Viewer & CV Telemetry */}
                <div className="lg:col-span-4 flex flex-col gap-space-md">
                    <div className="bg-surface-container-lowest p-space-md rounded shadow-sm flex flex-col">
                        <div className="flex items-center justify-between mb-space-sm">
                            <div className="flex items-center gap-space-xs">
                                <span className="material-symbols-outlined text-secondary text-[18px]">photo_camera</span>
                                <span className="font-headline-sm text-headline-sm text-on-surface">Inspection Proofs</span>
                            </div>
                            <span className="font-data-mono-sm text-data-mono-sm text-on-tertiary-container bg-surface-container px-space-xs py-0.5 rounded font-bold">
                                {evidence.length || record.images.length} SYNCED
                            </span>
                        </div>

                        <div className="relative w-full aspect-[4/3] bg-surface-container-highest rounded overflow-hidden shadow-inner group">
                            {evidence.length > 0 && evidence[selectedThumb]?.media_id ? (
                                <img
                                    src={`${API_BASE}/media/${encodeURIComponent(evidence[selectedThumb].media_id)}?organization_id=${encodeURIComponent(orgId)}`}
                                    alt="Evidence Proof"
                                    className="w-full h-full object-contain"
                                />
                            ) : (
                                <img
                                    src="https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?auto=format&fit=crop&w=800&q=80"
                                    alt="Sample Inspection Proof"
                                    className="w-full h-full object-cover"
                                />
                            )}

                            {/* Dynamic YOLO / Vision Overlay */}
                            {showOverlay && (
                                <div className="absolute inset-0 pointer-events-none p-2">
                                    {overlayType === 'yolo' && yoloDetections.map((det, i) => {
                                        const bbox = det.bbox || [50, 60, 450, 400];
                                        const [x1, y1, x2, y2] = bbox;
                                        const left = `${(x1 / 800) * 100}%`;
                                        const top = `${(y1 / 600) * 100}%`;
                                        const width = `${((x2 - x1) / 800) * 100}%`;
                                        const height = `${((y2 - y1) / 600) * 100}%`;
                                        const colors = [
                                            'border-secondary text-secondary bg-secondary/15',
                                            'border-tertiary-fixed-dim text-tertiary-fixed bg-tertiary-container/20',
                                            'border-primary text-primary bg-primary/15',
                                            'border-error text-error bg-error-container/20'
                                        ];
                                        const styleClass = colors[i % colors.length];

                                        return (
                                            <div
                                                key={i}
                                                className={`absolute border-2 rounded shadow-sm ${styleClass}`}
                                                style={{ left, top, width, height }}
                                            >
                                                <span className="absolute -top-5 left-0 bg-surface-container-highest text-on-surface font-data-mono-sm font-bold text-[9px] px-1 rounded border border-outline-variant shadow">
                                                    {det.label} {Math.round((det.confidence || 0.9) * 100)}%
                                                </span>
                                            </div>
                                        );
                                    })}

                                    {overlayType === 'ocr' && (
                                        <div className="absolute top-4 left-4 border-2 border-dashed border-tertiary-fixed bg-tertiary-container/40 p-1.5 rounded">
                                            <span className="font-data-mono-sm text-[9px] bg-primary text-on-primary px-1 rounded block">OCR DETECTED 99.4%</span>
                                            <span className="font-data-mono-sm text-[11px] text-tertiary-fixed font-bold">{record.ordered_sku}</span>
                                        </div>
                                    )}

                                    {overlayType === 'heatmap' && (
                                        <div className="absolute inset-0 bg-gradient-to-tr from-error/20 via-transparent to-secondary/20 pointer-events-none rounded flex items-center justify-center">
                                            <span className="font-data-mono-sm text-[10px] bg-error text-on-error px-2 py-0.5 rounded font-bold animate-pulse">
                                                ANOMALY HEATMAP OVERLAY ACTIVE
                                            </span>
                                        </div>
                                    )}
                                </div>
                            )}

                            <div className="absolute bottom-2 left-2 bg-surface-container-lowest/90 px-space-xs py-0.5 rounded font-data-mono-sm text-[10px] text-on-surface shadow-sm">
                                FOV: CAM-DOCK-04A • MOCK VISION + YOLO ACTIVE
                            </div>
                        </div>

                        {/* Overlay Controls */}
                        <div className="mt-space-sm pt-space-xs flex items-center justify-between gap-space-xs bg-surface-container-low p-space-xs rounded">
                            <span className="font-label-caps text-label-caps text-on-surface-variant uppercase pl-1">Vision Overlay:</span>
                            <div className="flex items-center gap-space-xs">
                                <button
                                    onClick={() => { setShowOverlay(true); setOverlayType('yolo'); }}
                                    className={`px-space-xs py-1 rounded font-data-mono-sm text-[10px] ${overlayType === 'yolo' && showOverlay ? 'bg-primary text-on-primary font-bold' : 'bg-surface-container text-on-surface'}`}
                                >
                                    YOLO BBoxes ({yoloDetections.length})
                                </button>
                                <button
                                    onClick={() => { setShowOverlay(true); setOverlayType('ocr'); }}
                                    className={`px-space-xs py-1 rounded font-data-mono-sm text-[10px] ${overlayType === 'ocr' && showOverlay ? 'bg-primary text-on-primary font-bold' : 'bg-surface-container text-on-surface'}`}
                                >
                                    OCR BBox
                                </button>
                                <button
                                    onClick={() => { setShowOverlay(true); setOverlayType('heatmap'); }}
                                    className={`px-space-xs py-1 rounded font-data-mono-sm text-[10px] ${overlayType === 'heatmap' && showOverlay ? 'bg-primary text-on-primary font-bold' : 'bg-surface-container text-on-surface'}`}
                                >
                                    Heatmap
                                </button>
                                <button
                                    onClick={() => setShowOverlay(!showOverlay)}
                                    className="px-space-xs py-1 rounded font-data-mono-sm text-[10px] bg-surface-container-high text-on-surface"
                                >
                                    {showOverlay ? 'Hide' : 'Show'}
                                </button>
                            </div>
                        </div>

                        {/* Thumbnail Reel */}
                        <div className="grid grid-cols-3 gap-space-xs mt-space-sm">
                            {[0, 1, 2].map((idx) => (
                                <button
                                    key={idx}
                                    onClick={() => setSelectedThumb(idx)}
                                    className={`relative rounded overflow-hidden aspect-[4/3] ${selectedThumb === idx ? 'ring-2 ring-secondary' : 'bg-surface-container'}`}
                                >
                                    <div className="w-full h-full bg-surface-container flex items-center justify-center font-data-mono-sm text-[10px] text-on-surface-variant">
                                        VIEW 0{idx + 1}
                                    </div>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Validation Scorecard */}
                    <div className="bg-surface-container-lowest p-space-md rounded shadow-sm">
                        <div className="flex items-center justify-between mb-space-sm">
                            <span className="font-headline-sm text-headline-sm text-on-surface">Capture Validation</span>
                            <span className="font-data-mono-sm text-data-mono-sm text-on-tertiary-container font-bold">ALL SENSORS OK</span>
                        </div>
                        <div className="grid grid-cols-2 gap-space-xs font-data-mono-sm text-data-mono-sm">
                            <div className="bg-surface-container-low p-space-xs rounded">
                                <div className="text-outline text-[10px]">BLUR SCORE</div>
                                <div className="font-bold text-on-surface text-base">98/100</div>
                                <div className="text-on-tertiary-container font-semibold text-[9px]">PASS</div>
                            </div>
                            <div className="bg-surface-container-low p-space-xs rounded">
                                <div className="text-outline text-[10px]">GLARE INDEX</div>
                                <div className="font-bold text-on-surface text-base">1.2%</div>
                                <div className="text-on-tertiary-container font-semibold text-[9px]">PASS</div>
                            </div>
                            <div className="bg-surface-container-low p-space-xs rounded">
                                <div className="text-outline text-[10px]">EXPOSURE</div>
                                <div className="font-bold text-on-surface text-base">EV 12.4</div>
                                <div className="text-on-tertiary-container font-semibold text-[9px]">PASS</div>
                            </div>
                            <div className="bg-surface-container-low p-space-xs rounded">
                                <div className="text-outline text-[10px]">FRAMING</div>
                                <div className="font-bold text-on-surface text-base">92%</div>
                                <div className="text-on-tertiary-container font-semibold text-[9px]">PASS</div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* CENTER COLUMN: Inspection Verification Stack */}
                <div className="lg:col-span-5 flex flex-col gap-space-md">
                    {/* Pipeline Workflow Banner */}
                    <div className="bg-surface-container-lowest p-space-sm rounded shadow-sm flex flex-col gap-1 font-data-mono-sm text-data-mono-sm border-l-4 border-l-secondary">
                        <span className="font-bold text-on-surface flex items-center gap-1">
                            <span className="material-symbols-outlined text-[16px] text-secondary">account_tree</span>
                            Pipeline Workflow Execution Trace
                        </span>
                        <div className="flex items-center gap-1 text-[10px] flex-wrap mt-0.5">
                            <span className="px-1.5 py-0.5 rounded bg-surface-container text-on-surface font-semibold">1. DETECT</span>
                            <span className="text-outline">→</span>
                            <span className="px-1.5 py-0.5 rounded bg-surface-container text-on-surface font-semibold">2. REASON</span>
                            <span className="text-outline">→</span>
                            <span className="px-1.5 py-0.5 rounded bg-surface-container text-on-surface font-semibold">3. VERIFY</span>
                            <span className="text-outline">→</span>
                            <span className="px-1.5 py-0.5 rounded bg-secondary text-on-secondary font-bold">4. DECIDE</span>
                            <span className="text-outline">→</span>
                            <span className={`px-1.5 py-0.5 rounded font-bold ${isPending ? 'bg-error-container text-error' : 'bg-surface-container text-on-tertiary-container'}`}>
                                5. {isPending ? 'REVIEW' : 'COMPLETED'}
                            </span>
                        </div>
                    </div>

                    <div className="bg-surface-container-lowest p-space-md rounded shadow-sm flex items-center justify-between">
                        <div>
                            <span className="font-label-caps text-label-caps text-outline uppercase tracking-wider block">INSPECTION PROTOCOL</span>
                            <span className="font-headline-md text-headline-md text-on-surface">Rule Matrix v2026.04-Core</span>
                        </div>
                        <span className="px-2 py-1 rounded bg-surface-container font-data-mono-sm font-semibold text-on-surface">
                            {record.checks?.length || 3} CHECKS
                        </span>
                    </div>

                    {record.checks?.map((check, idx) => (
                        <div
                            key={check.check_key || idx}
                            className={`bg-surface-container-lowest p-space-md rounded shadow-sm border-l-4 ${check.verdict === 'PASS' ? 'border-l-on-tertiary-container' : check.verdict === 'FAIL' ? 'border-l-error' : 'border-l-secondary'
                                }`}
                        >
                            <div className="flex items-center justify-between mb-space-sm">
                                <div className="flex items-center gap-space-xs">
                                    <span className="w-6 h-6 rounded-full bg-surface-container flex items-center justify-center font-data-mono-sm font-bold">
                                        {idx + 1}
                                    </span>
                                    <span className="font-headline-sm text-headline-sm capitalize text-on-surface">
                                        {check.check_key} Check
                                    </span>
                                </div>
                                <span className={`px-2 py-0.5 rounded font-data-mono-sm text-data-mono-sm font-bold ${check.verdict === 'PASS' ? 'bg-surface-container text-on-tertiary-container' : check.verdict === 'FAIL' ? 'bg-error-container text-error' : 'bg-secondary-fixed text-on-secondary-fixed-variant'
                                    }`}>
                                    {check.verdict} ({Math.round((check.confidence || 0.85) * 100)}%)
                                </span>
                            </div>
                            <div className="bg-surface-container-low p-space-sm rounded text-body-sm font-data-mono-sm text-on-surface leading-relaxed">
                                {check.detail}
                            </div>
                        </div>
                    ))}
                </div>

                {/* RIGHT COLUMN: Supervisor Override Workspace */}
                <div className="lg:col-span-3 flex flex-col gap-space-md">
                    <div className="bg-surface-container-lowest p-space-md rounded shadow-sm">
                        <span className="font-label-caps text-label-caps text-outline uppercase block mb-1">SYSTEM DISPOSITION</span>
                        <div className="p-space-sm bg-surface-container-low rounded flex items-center justify-between">
                            <div>
                                <span className="font-headline-sm text-headline-sm font-bold text-on-surface uppercase block">
                                    {record.outcome}
                                </span>
                                <span className="font-data-mono-sm text-[10px] text-on-surface-variant">Deterministic Engine</span>
                            </div>
                            <span className="px-2 py-1 rounded bg-error-container text-on-error-container font-data-mono-sm text-data-mono-sm font-bold">
                                {isPending ? 'NEEDS OVERRIDE' : 'FINALIZED'}
                            </span>
                        </div>
                    </div>

                    <div className="bg-surface-container-lowest p-space-md rounded shadow-md flex-1 flex flex-col justify-between">
                        <div>
                            <div className="flex items-center justify-between mb-space-sm">
                                <span className="font-headline-sm text-headline-sm text-on-surface">Supervisor Override</span>
                                <span className="font-data-mono-sm text-[10px] bg-surface-container px-2 py-0.5 rounded">OP-449</span>
                            </div>

                            <div className="mb-space-md">
                                <label className="font-label-caps text-label-caps text-on-surface-variant uppercase block mb-1">Operational Disposition</label>
                                <div className="grid grid-cols-2 gap-space-xs">
                                    {['RESTOCK', 'REFURBISH', 'LIQUIDATE', 'DISPOSE'].map((item) => (
                                        <button
                                            key={item}
                                            type="button"
                                            onClick={() => setDisposition(item)}
                                            className={`py-2 px-space-xs rounded font-data-mono-sm text-data-mono-sm font-bold transition-all ${disposition === item ? 'bg-primary text-on-primary shadow-sm' : 'bg-surface-container-low text-on-surface hover:bg-surface-container'
                                                }`}
                                        >
                                            {item}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div className="mb-space-md">
                                <label className="font-label-caps text-label-caps text-on-surface-variant uppercase block mb-1">Justification Code</label>
                                <select
                                    value={reasonCode}
                                    onChange={(e) => setReasonCode(e.target.value)}
                                    className="w-full h-9 px-2 bg-surface-container-low text-on-surface font-data-mono-sm text-data-mono-sm rounded outline-none"
                                >
                                    <option value="NON_OEM_ACCESSORY_DETECTED">NON_OEM_ACCESSORY_DETECTED (Code 402)</option>
                                    <option value="COSMETIC_DAMAGE_OVERRIDE">COSMETIC_DAMAGE_OVERRIDE (Code 209)</option>
                                    <option value="PARTS_SALVAGE_PRIORITY">PARTS_SALVAGE_PRIORITY (Code 512)</option>
                                    <option value="CUSTOMER_FRAUD_INVESTIGATION">CUSTOMER_FRAUD_INVESTIGATION (Code 991)</option>
                                </select>
                            </div>

                            <div className="mb-space-md">
                                <label className="font-label-caps text-label-caps text-on-surface-variant uppercase block mb-1">Operational Notes</label>
                                <textarea
                                    value={notes}
                                    onChange={(e) => setNotes(e.target.value)}
                                    rows={3}
                                    className="w-full p-2 bg-surface-container-low text-on-surface font-data-mono-sm text-data-mono-sm rounded outline-none resize-none"
                                />
                            </div>
                        </div>

                        <button
                            onClick={handleResolve}
                            disabled={submitting}
                            className="w-full h-11 bg-primary hover:bg-surface-tint text-on-primary font-headline-sm text-headline-sm rounded flex items-center justify-center gap-space-xs transition-colors shadow-md disabled:opacity-50"
                        >
                            {submitting ? (
                                <span className="material-symbols-outlined animate-spin text-[18px]">autorenew</span>
                            ) : (
                                <span className="material-symbols-outlined text-[18px]">task_alt</span>
                            )}
                            <span>Confirm & Route Disposition</span>
                        </button>
                    </div>
                </div>
            </div>

            {/* Cryptographic Traceability Footer */}
            <div className="w-full bg-surface-container-lowest p-space-md rounded shadow-sm flex flex-col md:flex-row justify-between gap-space-md font-data-mono-sm text-data-mono-sm">
                <div>
                    <span className="text-outline block uppercase text-[10px]">SHA-256 PROOF HASH</span>
                    <span className="text-on-surface font-bold truncate block max-w-md">{record.content_hash || '4a8f902c2e0bfa9398ec71d02c81d3f9e20a01947b1e847cc021'}</span>
                </div>
                <div className="flex items-center gap-space-lg">
                    <div><span className="text-outline block uppercase text-[10px]">STATUS</span><span className="text-on-tertiary-container font-bold">{record.status}</span></div>
                    <div><span className="text-outline block uppercase text-[10px]">LEDGER</span><span className="text-secondary font-bold">BLOCK #8,941,202</span></div>
                </div>
            </div>
        </div>
    );
}
