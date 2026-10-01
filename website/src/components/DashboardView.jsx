import React from 'react';

export default function DashboardView({ reviews, loading, onNewInspection, onReview, onRefresh }) {
    return (
        <div className="flex flex-col w-full gap-space-md animate-fadeIn pb-12">
            {/* Telemetry Metrics Row */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-space-md">
                <div className="bg-surface-container-lowest p-space-md rounded shadow-sm flex flex-col justify-between h-28">
                    <div className="flex items-center justify-between">
                        <span className="font-label-caps text-label-caps text-outline uppercase">Total Inspections Today</span>
                        <span className="material-symbols-outlined text-secondary text-[20px]">assignment</span>
                    </div>
                    <div className="font-headline-xl text-headline-xl text-on-surface font-bold">148</div>
                    <div className="font-data-mono-sm text-data-mono-sm text-on-tertiary-container font-semibold">+14.2% vs target</div>
                </div>

                <div className="bg-surface-container-lowest p-space-md rounded shadow-sm flex flex-col justify-between h-28">
                    <div className="flex items-center justify-between">
                        <span className="font-label-caps text-label-caps text-outline uppercase">Pending Supervisor Reviews</span>
                        <span className="material-symbols-outlined text-error text-[20px]">pending_actions</span>
                    </div>
                    <div className="font-headline-xl text-headline-xl text-error font-bold">{reviews.length}</div>
                    <div className="font-data-mono-sm text-data-mono-sm text-error font-semibold">Requires human resolution</div>
                </div>

                <div className="bg-surface-container-lowest p-space-md rounded shadow-sm flex flex-col justify-between h-28">
                    <div className="flex items-center justify-between">
                        <span className="font-label-caps text-label-caps text-outline uppercase">AI Model Accuracy</span>
                        <span className="material-symbols-outlined text-on-tertiary-container text-[20px]">verified</span>
                    </div>
                    <div className="font-headline-xl text-headline-xl text-on-surface font-bold">98.4%</div>
                    <div className="font-data-mono-sm text-data-mono-sm text-on-tertiary-container font-semibold">Zero critical false pass</div>
                </div>

                <div className="bg-surface-container-lowest p-space-md rounded shadow-sm flex flex-col justify-between h-28">
                    <div className="flex items-center justify-between">
                        <span className="font-label-caps text-label-caps text-outline uppercase">Avg Pipeline Latency</span>
                        <span className="material-symbols-outlined text-secondary text-[20px]">speed</span>
                    </div>
                    <div className="font-headline-xl text-headline-xl text-on-surface font-bold">3.2s</div>
                    <div className="font-data-mono-sm text-data-mono-sm text-on-surface-variant font-semibold">Ollama + YOLO GPU</div>
                </div>
            </div>

            {/* Main Action + Queue Split */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-md">
                {/* Left: Quick Launch Panel */}
                <div className="lg:col-span-4 bg-surface-container-lowest p-space-md rounded shadow-sm flex flex-col justify-between gap-space-md">
                    <div>
                        <div className="flex items-center gap-space-xs mb-space-sm">
                            <span className="material-symbols-outlined text-secondary text-[20px]">play_circle</span>
                            <span className="font-headline-md text-headline-md text-on-surface">Intake Station Controls</span>
                        </div>
                        <p className="font-body-sm text-body-sm text-on-surface-variant mb-space-md leading-relaxed">
                            Launch a new return parcel inspection workflow. Verify package binding QR codes or submit visual evidence directly to the deterministic engine.
                        </p>

                        <div className="space-y-space-sm mb-space-md">
                            <button
                                onClick={() => onNewInspection('qr')}
                                className="w-full h-11 bg-primary hover:bg-surface-tint text-on-primary font-headline-sm text-headline-sm rounded flex items-center justify-center gap-space-sm shadow-md transition-colors"
                            >
                                <span className="material-symbols-outlined text-[20px]">qr_code_scanner</span>
                                <span>Start QR + Visual Inspection</span>
                            </button>

                            <button
                                onClick={() => onNewInspection('vision')}
                                className="w-full h-11 bg-surface-container hover:bg-surface-container-high text-on-surface font-headline-sm text-headline-sm rounded flex items-center justify-center gap-space-sm transition-colors border border-outline-variant"
                            >
                                <span className="material-symbols-outlined text-[20px]">photo_camera</span>
                                <span>Start Direct Visual Intake</span>
                            </button>
                        </div>

                        {/* Instant Scenario Quick Tests */}
                        <div className="p-space-sm bg-surface-container-low rounded border border-outline-variant mb-space-md">
                            <span className="font-label-caps text-label-caps text-secondary uppercase block mb-2 font-bold flex items-center gap-1">
                                <span className="material-symbols-outlined text-[16px]">science</span>
                                Instant Mock Scenarios (Test Suite)
                            </span>
                            <div className="grid grid-cols-1 gap-1.5 font-data-mono-sm text-data-mono-sm">
                                <button
                                    onClick={() => onNewInspection('vision', 'SCENARIO_1')}
                                    className="px-2 py-1.5 bg-surface-container-lowest hover:bg-surface-container text-left text-on-surface rounded border border-outline-variant flex items-center justify-between"
                                >
                                    <span>1. Correct Product</span>
                                    <span className="text-on-tertiary-container font-bold text-[10px] bg-surface-container px-1.5 py-0.5 rounded">RESTOCK</span>
                                </button>
                                <button
                                    onClick={() => onNewInspection('vision', 'SCENARIO_2')}
                                    className="px-2 py-1.5 bg-surface-container-lowest hover:bg-surface-container text-left text-on-surface rounded border border-outline-variant flex items-center justify-between"
                                >
                                    <span>2. Wrong Product</span>
                                    <span className="text-error font-bold text-[10px] bg-error-container px-1.5 py-0.5 rounded">DISPOSE</span>
                                </button>
                                <button
                                    onClick={() => onNewInspection('vision', 'SCENARIO_3')}
                                    className="px-2 py-1.5 bg-surface-container-lowest hover:bg-surface-container text-left text-on-surface rounded border border-outline-variant flex items-center justify-between"
                                >
                                    <span>3. Missing Accessory</span>
                                    <span className="text-secondary font-bold text-[10px] bg-surface-container px-1.5 py-0.5 rounded">LIQUIDATE</span>
                                </button>
                                <button
                                    onClick={() => onNewInspection('vision', 'SCENARIO_4')}
                                    className="px-2 py-1.5 bg-surface-container-lowest hover:bg-surface-container text-left text-on-surface rounded border border-outline-variant flex items-center justify-between"
                                >
                                    <span>4. Uncertain Product</span>
                                    <span className="text-on-secondary-fixed-variant font-bold text-[10px] bg-secondary-fixed px-1.5 py-0.5 rounded">PENDING REVIEW</span>
                                </button>
                                <button
                                    onClick={() => onNewInspection('vision', 'SCENARIO_5')}
                                    className="px-2 py-1.5 bg-surface-container-lowest hover:bg-surface-container text-left text-on-surface rounded border border-outline-variant flex items-center justify-between"
                                >
                                    <span>5. Damaged Product</span>
                                    <span className="text-error font-bold text-[10px] bg-error-container px-1.5 py-0.5 rounded">LIQUIDATE</span>
                                </button>
                            </div>
                        </div>
                    </div>

                    <div className="p-space-sm bg-surface-container-low rounded border border-outline-variant">
                        <span className="font-label-caps text-label-caps text-outline uppercase block mb-1">Station Config</span>
                        <div className="font-data-mono-sm text-data-mono-sm text-on-surface">
                            <div>ORG: <strong className="text-secondary">org_demo_alpha</strong></div>
                            <div>SCANNER: <strong className="text-on-surface">Honeywell Xenon Ultra</strong></div>
                            <div>MODE: <strong className="text-on-tertiary-container font-mono uppercase">MOCK FIRST ARCHITECTURE</strong></div>
                        </div>
                    </div>

                </div>

                {/* Right: Pending Return Review Queue */}
                <div className="lg:col-span-8 bg-surface-container-lowest p-space-md rounded shadow-sm">
                    <div className="flex items-center justify-between mb-space-md pb-space-xs border-b border-surface-container">
                        <div>
                            <span className="font-headline-md text-headline-md text-on-surface">Pending Return Queue</span>
                            <span className="font-data-mono-sm text-data-mono-sm text-on-surface-variant block">Parcels awaiting operator review or supervisor override</span>
                        </div>
                        <button
                            onClick={onRefresh}
                            className="h-8 px-space-sm bg-surface-container hover:bg-surface-container-high rounded text-on-surface font-data-mono-sm text-data-mono-sm flex items-center gap-1"
                        >
                            <span className="material-symbols-outlined text-[16px]">refresh</span>
                            <span>Refresh</span>
                        </button>
                    </div>

                    {loading ? (
                        <div className="py-12 flex flex-col items-center justify-center text-on-surface-variant">
                            <span className="material-symbols-outlined animate-spin text-[28px] text-secondary mb-2">autorenew</span>
                            <span className="font-data-mono-sm text-data-mono-sm">Loading review records...</span>
                        </div>
                    ) : reviews.length === 0 ? (
                        <div className="py-12 text-center bg-surface-container-low rounded border border-dashed border-outline-variant p-space-md">
                            <span className="material-symbols-outlined text-[36px] text-outline mb-2">task_alt</span>
                            <p className="font-headline-sm text-headline-sm text-on-surface">Queue Cleared</p>
                            <p className="font-body-sm text-body-sm text-on-surface-variant">All returns have been evaluated and finalized.</p>
                        </div>
                    ) : (
                        <div className="space-y-space-sm">
                            {reviews.map((rev) => (
                                <div key={rev.record_id} className="p-space-md bg-surface-container-low rounded border border-outline-variant flex flex-col sm:flex-row sm:items-center justify-between gap-space-md hover:border-secondary transition-colors">
                                    <div className="flex flex-col gap-1 font-data-mono-sm text-data-mono-sm">
                                        <div className="flex items-center gap-space-sm">
                                            <span className="font-bold text-on-surface text-base">#{rev.record_id}</span>
                                            <span className="px-2 py-0.5 rounded font-label-caps text-label-caps bg-error-container text-on-error-container font-bold">
                                                {rev.status === 'pending_review' ? 'NEEDS OVERRIDE' : rev.status}
                                            </span>
                                        </div>
                                        <div className="text-on-surface-variant">
                                            Subject: <strong className="text-on-surface">{rev.subject || 'UNIT-RETURN'}</strong> • Outcome: <strong className="text-secondary">{rev.outcome || 'PENDING'}</strong>
                                        </div>
                                    </div>

                                    <button
                                        onClick={() => onReview(rev.record_id)}
                                        className="h-9 px-space-md bg-secondary hover:bg-secondary/90 text-on-secondary font-data-mono-sm text-data-mono-sm font-bold rounded flex items-center justify-center gap-space-xs transition-colors shadow-sm self-start sm:self-center"
                                    >
                                        <span>Inspect Return</span>
                                        <span className="material-symbols-outlined text-[16px]">chevron_right</span>
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
