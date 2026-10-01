import React, { useState, useEffect, useId } from 'react';
import axios from 'axios';
import { Html5QrcodeScanner } from 'html5-qrcode';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

export default function QRScanView({ onBack, onContinue }) {
    const [packageQR, setPackageQR] = useState('');
    const [productQR, setProductQR] = useState('');
    const [verifying, setVerifying] = useState(false);
    const [result, setResult] = useState(null);
    const [scanState, setScanState] = useState('idle'); // 'idle', 'product', 'package'
    const readerId = `qr-reader-${useId().replaceAll(':', '')}`;

    useEffect(() => {
        if (scanState === 'idle') return undefined;

        const scanner = new Html5QrcodeScanner(
            readerId,
            { fps: 10, qrbox: { width: 250, height: 250 }, rememberLastUsedCamera: true },
            false
        );

        scanner.render(
            (decodedText) => {
                const val = decodedText.trim();
                if (!val) return;
                if (scanState === 'product') setProductQR(val);
                else if (scanState === 'package') setPackageQR(val);
                setScanState('idle');
                scanner.clear().catch(() => { });
            },
            () => { }
        );

        return () => {
            scanner.clear().catch(() => { });
        };
    }, [readerId, scanState]);

    const verifyBinding = async (e) => {
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
        } finally {
            setVerifying(false);
        }
    };

    return (
        <div className="w-full max-w-2xl mx-auto animate-fadeIn pb-12">
            <button
                onClick={onBack}
                className="mb-space-md font-data-mono-sm text-data-mono-sm text-secondary flex items-center gap-1 hover:underline"
            >
                <span className="material-symbols-outlined text-[16px]">arrow_back</span> Back to Dashboard
            </button>

            <div className="bg-surface-container-lowest p-space-md rounded shadow-md border border-surface-container">
                <div className="flex items-center gap-space-sm mb-space-md pb-space-sm border-b border-surface-container">
                    <div className="w-10 h-10 rounded-lg bg-secondary text-on-secondary flex items-center justify-center">
                        <span className="material-symbols-outlined text-[24px]">qr_code_scanner</span>
                    </div>
                    <div>
                        <span className="font-headline-md text-headline-md text-on-surface block">QR Binding & Authentication</span>
                        <span className="font-data-mono-sm text-data-mono-sm text-on-surface-variant">Verify product and parcel identity before visual inspection</span>
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-space-sm mb-space-md">
                    <button
                        type="button"
                        onClick={() => setScanState('product')}
                        className="h-11 bg-surface-container hover:bg-surface-container-high text-on-surface font-data-mono-sm text-data-mono-sm font-bold rounded flex items-center justify-center gap-space-xs transition-colors border border-outline-variant"
                    >
                        <span className="material-symbols-outlined text-[18px]">photo_camera</span>
                        <span>Scan Product QR</span>
                    </button>
                    <button
                        type="button"
                        onClick={() => setScanState('package')}
                        className="h-11 bg-surface-container hover:bg-surface-container-high text-on-surface font-data-mono-sm text-data-mono-sm font-bold rounded flex items-center justify-center gap-space-xs transition-colors border border-outline-variant"
                    >
                        <span className="material-symbols-outlined text-[18px]">inventory_2</span>
                        <span>Scan Package QR</span>
                    </button>
                </div>

                {scanState !== 'idle' && (
                    <div className="mb-space-md p-space-sm bg-surface-container-low rounded border border-secondary">
                        <div id={readerId} className="w-full min-h-[260px]" />
                        <p className="font-data-mono-sm text-data-mono-sm text-on-surface-variant text-center mt-2">
                            Scanning active for: <strong className="uppercase text-secondary">{scanState}</strong>
                        </p>
                    </div>
                )}

                <form onSubmit={verifyBinding} className="space-y-space-md">
                    <div>
                        <label className="font-label-caps text-label-caps text-on-surface-variant uppercase block mb-1">Package QR Identifier</label>
                        <input
                            value={packageQR}
                            onChange={(e) => setPackageQR(e.target.value)}
                            placeholder="e.g. PKG-12345"
                            className="w-full h-11 px-space-md bg-surface-container-low text-on-surface font-data-mono-md text-data-mono-md rounded outline-none border border-outline-variant focus:border-secondary"
                            required
                        />
                    </div>

                    <div>
                        <label className="font-label-caps text-label-caps text-on-surface-variant uppercase block mb-1">Product QR Identifier</label>
                        <input
                            value={productQR}
                            onChange={(e) => setProductQR(e.target.value)}
                            placeholder="e.g. PRD-98765"
                            className="w-full h-11 px-space-md bg-surface-container-low text-on-surface font-data-mono-md text-data-mono-md rounded outline-none border border-outline-variant focus:border-secondary"
                            required
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={verifying || !packageQR || !productQR}
                        className="w-full h-11 bg-primary hover:bg-surface-tint text-on-primary font-headline-sm text-headline-sm rounded flex items-center justify-center gap-space-xs transition-colors shadow-md disabled:opacity-40"
                    >
                        {verifying ? (
                            <span className="material-symbols-outlined animate-spin text-[18px]">autorenew</span>
                        ) : (
                            <span className="material-symbols-outlined text-[18px]">verified_user</span>
                        )}
                        <span>Verify Server-Side Binding</span>
                    </button>
                </form>

                {result && !result.error && (
                    <div className={`mt-space-md p-space-md rounded font-data-mono-sm text-data-mono-sm ${result.qr_auth_result === 'AUTHENTICATED' ? 'bg-surface-container text-on-tertiary-container border border-on-tertiary-container' : 'bg-secondary-fixed text-on-secondary-fixed-variant'
                        }`}>
                        <div className="font-bold text-sm mb-1 uppercase tracking-wider">{result.qr_auth_result}</div>
                        <div>{result.message}</div>
                    </div>
                )}

                {result?.error && (
                    <div className="mt-space-md p-space-md bg-error-container text-on-error-container rounded font-data-mono-sm text-data-mono-sm">
                        {result.error}
                    </div>
                )}

                <button
                    onClick={() => onContinue({ product_qr: productQR, package_qr: packageQR, auth_event_id: result?.auth_event_id })}
                    disabled={!result || Boolean(result.error)}
                    className="mt-space-md w-full h-12 bg-secondary hover:bg-secondary/90 text-on-secondary font-headline-sm text-headline-sm font-bold rounded flex items-center justify-center gap-space-xs transition-colors shadow-md disabled:opacity-40"
                >
                    <span>Continue to Visual Inspection Intake</span>
                    <span className="material-symbols-outlined text-[18px]">chevron_right</span>
                </button>
            </div>
        </div>
    );
}
