import React, { useState, useRef } from 'react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';
const DEMO_ORG = 'org_demo_alpha';
const DEMO_OPERATOR = 'E. Marcus (Station #04)';

export default function CaptureView({ onBack, onResult, qrVerification, initialScenario }) {
    const [recordId] = useState(() => `RTN-${Date.now().toString().slice(-6)}`);
    const [orderId, setOrderId] = useState('ORD-10482');
    const [sku, setSku] = useState('SKU-SPEAKER-500');
    const [asin, setAsin] = useState('B0DUMMY729');
    const [parts, setParts] = useState('cable;manual;adapter');
    const [scenario, setScenario] = useState(initialScenario || 'SCENARIO_1');
    const [capturedImages, setCapturedImages] = useState([]);
    const [processing, setProcessing] = useState(false);
    const [statusMsg, setStatusMsg] = useState('');

    const cameraRef = useRef(null);
    const fileRef = useRef(null);

    const addFile = (file) => {
        setCapturedImages((prev) => [...prev, { file, preview: URL.createObjectURL(file) }]);
    };

    const handleFileChange = (e) => {
        if (e.target.files) {
            Array.from(e.target.files).forEach(addFile);
            e.target.value = '';
        }
    };

    const removeImage = (idx) => {
        setCapturedImages((prev) => prev.filter((_, i) => i !== idx));
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
        ctx.fillText('CUBE MOCK INSPECTION PROOF', 40, 80);
        ctx.fillStyle = '#94a3b8';
        ctx.font = '16px monospace';
        ctx.fillText(`RECORD: ${recordId}`, 40, 130);
        ctx.fillText(`SKU: ${sku}`, 40, 160);
        ctx.fillText(`SCENARIO: ${scenario}`, 40, 190);
        ctx.fillText(`TIMESTAMP: ${new Date().toISOString()}`, 40, 220);

        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 3;
        ctx.strokeRect(50, 250, 150, 100);
        ctx.fillStyle = '#38bdf8';
        ctx.fillText('ITEM ROI', 60, 280);

        return new Promise((resolve) => {
            canvas.toBlob((blob) => {
                const file = new File([blob], `mock_${recordId}.jpg`, { type: 'image/jpeg' });
                resolve(file);
            }, 'image/jpeg');
        });
    };

    const handleSubmit = async () => {
        if (!sku.trim() || !orderId.trim()) return alert('Order ID and SKU are required.');

        setProcessing(true);
        setStatusMsg('Preparing photo evidence...');

        let imagesToSubmit = [...capturedImages];
        if (imagesToSubmit.length === 0) {
            const mockFile = await createMockBlob();
            imagesToSubmit = [{ file: mockFile, preview: URL.createObjectURL(mockFile) }];
        }

        const mediaRefs = [];

        try {
            for (const img of imagesToSubmit) {
                const form = new FormData();
                form.append('file', img.file);
                form.append('record_id', recordId);
                form.append('organization_id', DEMO_ORG);
                const { data } = await axios.post(`${API_BASE}/media`, form);
                mediaRefs.push(data.storage_ref);
            }

            setStatusMsg('Processing mock inspection pipeline & decision engine...');

            const payload = {
                record_id: recordId,
                unit_id: `UNIT-${recordId}`,
                org_id: DEMO_ORG,
                order_id: orderId.trim(),
                ordered_sku: sku.trim(),
                ordered_asin: asin.trim(),
                parts_list: parts.trim() || 'product',
                photo_refs: mediaRefs.join(';'),
                operator_id: DEMO_OPERATOR,
                captured_at: new Date().toISOString(),
                scenario: scenario,
                ...(qrVerification ?? {}),
            };

            const { data } = await axios.post(`${API_BASE}/inspect`, payload);
            onResult(data);
        } catch (err) {
            alert('Inspection failed: ' + (err.response?.data?.detail ?? err.message));
        } finally {
            setProcessing(false);
        }
    };

    return (
        <div className="w-full max-w-4xl mx-auto animate-fadeIn pb-12">
            <button
                onClick={onBack}
                className="mb-space-md font-data-mono-sm text-data-mono-sm text-secondary flex items-center gap-1 hover:underline"
            >
                <span className="material-symbols-outlined text-[16px]">arrow_back</span> Back
            </button>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-md">
                {/* Parcel Metadata Input */}
                <div className="lg:col-span-6 bg-surface-container-lowest p-space-md rounded shadow-md border border-surface-container">
                    <div className="flex items-center gap-space-xs mb-space-md pb-space-xs border-b border-surface-container">
                        <span className="material-symbols-outlined text-secondary text-[20px]">assignment</span>
                        <span className="font-headline-md text-headline-md text-on-surface">Return Parcel Metadata</span>
                    </div>

                    <div className="space-y-space-md font-data-mono-sm text-data-mono-sm">
                        <div>
                            <label className="font-label-caps text-label-caps text-outline uppercase block mb-1">Target AI Test Scenario</label>
                            <select
                                value={scenario}
                                onChange={(e) => setScenario(e.target.value)}
                                className="w-full h-10 px-3 bg-surface-container-low text-on-surface rounded font-bold border border-secondary outline-none focus:ring-2 focus:ring-secondary"
                            >
                                <option value="SCENARIO_1">1. Correct Product (Restock)</option>
                                <option value="SCENARIO_2">2. Wrong Product (Dispose)</option>
                                <option value="SCENARIO_3">3. Missing Accessory (Liquidate)</option>
                                <option value="SCENARIO_4">4. Uncertain Product (Pending Review)</option>
                                <option value="SCENARIO_5">5. Damaged Product (Liquidate)</option>
                            </select>
                        </div>

                        <div>
                            <label className="font-label-caps text-label-caps text-outline uppercase block mb-1">Generated Record ID</label>
                            <input value={recordId} readOnly className="w-full h-10 px-3 bg-surface-container-low text-on-surface rounded font-bold border border-outline-variant outline-none" />
                        </div>

                        <div>
                            <label className="font-label-caps text-label-caps text-outline uppercase block mb-1">Order ID *</label>
                            <input value={orderId} onChange={(e) => setOrderId(e.target.value)} placeholder="ORD-10482" className="w-full h-10 px-3 bg-surface-container-low text-on-surface rounded border border-outline-variant focus:border-secondary outline-none" required />
                        </div>

                        <div>
                            <label className="font-label-caps text-label-caps text-outline uppercase block mb-1">Expected SKU *</label>
                            <input value={sku} onChange={(e) => setSku(e.target.value)} placeholder="SKU-SPEAKER-500" className="w-full h-10 px-3 bg-surface-container-low text-on-surface rounded border border-outline-variant focus:border-secondary outline-none" required />
                        </div>

                        <div>
                            <label className="font-label-caps text-label-caps text-outline uppercase block mb-1">Expected ASIN *</label>
                            <input value={asin} onChange={(e) => setAsin(e.target.value)} placeholder="B0DUMMY729" className="w-full h-10 px-3 bg-surface-container-low text-on-surface rounded border border-outline-variant focus:border-secondary outline-none" required />
                        </div>

                        <div>
                            <label className="font-label-caps text-label-caps text-outline uppercase block mb-1">Expected Parts List (BOM)</label>
                            <input value={parts} onChange={(e) => setParts(e.target.value)} placeholder="cable;manual;adapter" className="w-full h-10 px-3 bg-surface-container-low text-on-surface rounded border border-outline-variant focus:border-secondary outline-none" />
                        </div>
                    </div>
                </div>

                {/* Photo Evidence Capture */}
                <div className="lg:col-span-6 bg-surface-container-lowest p-space-md rounded shadow-md border border-surface-container flex flex-col justify-between">
                    <div>
                        <div className="flex items-center justify-between mb-space-md pb-space-xs border-b border-surface-container">
                            <div className="flex items-center gap-space-xs">
                                <span className="material-symbols-outlined text-secondary text-[20px]">photo_camera</span>
                                <span className="font-headline-md text-headline-md text-on-surface">Photographic Evidence</span>
                            </div>
                            <span className="font-data-mono-sm text-data-mono-sm font-bold text-secondary">{capturedImages.length} CAPTURED</span>
                        </div>

                        {capturedImages.length > 0 && (
                            <div className="grid grid-cols-3 gap-space-xs mb-space-md">
                                {capturedImages.map((img, idx) => (
                                    <div key={idx} className="relative aspect-square rounded overflow-hidden border border-outline-variant bg-surface-container group">
                                        <img src={img.preview} alt="Evidence" className="w-full h-full object-cover" />
                                        <button
                                            onClick={() => removeImage(idx)}
                                            className="absolute top-1 right-1 w-6 h-6 rounded-full bg-error text-on-error font-bold flex items-center justify-center text-xs"
                                        >
                                            ×
                                        </button>
                                        <span className="absolute bottom-1 left-1 bg-primary/80 text-on-primary font-data-mono-sm text-[9px] px-1 rounded">
                                            VIEW 0{idx + 1}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        )}

                        <div className="grid grid-cols-2 gap-space-sm mb-space-md">
                            <button
                                type="button"
                                onClick={() => cameraRef.current?.click()}
                                className="h-24 bg-surface-container hover:bg-surface-container-high rounded border border-dashed border-outline flex flex-col items-center justify-center gap-1 text-on-surface transition-colors"
                            >
                                <span className="material-symbols-outlined text-[28px] text-secondary">photo_camera</span>
                                <span className="font-data-mono-sm text-data-mono-sm font-bold">Camera Capture</span>
                            </button>

                            <button
                                type="button"
                                onClick={() => fileRef.current?.click()}
                                className="h-24 bg-surface-container hover:bg-surface-container-high rounded border border-dashed border-outline flex flex-col items-center justify-center gap-1 text-on-surface transition-colors"
                            >
                                <span className="material-symbols-outlined text-[28px] text-secondary">upload_file</span>
                                <span className="font-data-mono-sm text-data-mono-sm font-bold">Upload Files</span>
                            </button>
                        </div>

                        <input ref={cameraRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={handleFileChange} />
                        <input ref={fileRef} type="file" accept="image/*" multiple className="hidden" onChange={handleFileChange} />
                    </div>

                    <button
                        onClick={handleSubmit}
                        disabled={processing}
                        className="w-full h-12 bg-primary hover:bg-surface-tint text-on-primary font-headline-sm text-headline-sm font-bold rounded flex items-center justify-center gap-space-xs transition-colors shadow-md"
                    >
                        {processing ? (
                            <span className="material-symbols-outlined animate-spin text-[20px]">autorenew</span>
                        ) : (
                            <span className="material-symbols-outlined text-[20px]">auto_detect_voice</span>
                        )}
                        <span>{processing ? statusMsg : 'Submit to Vision Inspection Engine'}</span>
                    </button>
                </div>
            </div>
        </div>
    );
}

