import React, { useState } from 'react';

export default function Header({ onQuickSearch, onDashboard }) {
    const [searchTerm, setSearchTerm] = useState('');

    const handleSearchSubmit = (e) => {
        e.preventDefault();
        if (searchTerm.trim() && onQuickSearch) {
            onQuickSearch(searchTerm.trim());
            setSearchTerm('');
        }
    };

    return (
        <header className="fixed top-0 left-0 right-0 z-50 bg-surface-container-lowest shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
            <div className="h-14 w-full px-margin flex items-center justify-between gap-space-lg">
                <div className="flex items-center gap-space-lg">
                    <div
                        className="flex items-center gap-space-sm cursor-pointer"
                        onClick={onDashboard}
                    >
                        <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-on-primary font-bold font-mono text-sm shadow-sm">
                            C4
                        </div>
                        <span className="font-headline-sm text-headline-sm text-on-surface">CUBE Track 04</span>
                        <span className="font-label-caps text-label-caps uppercase bg-surface-container px-space-xs py-0.5 rounded text-on-surface-variant">OPS HUB</span>
                    </div>

                    <div className="hidden md:flex items-center gap-space-xs px-space-sm py-1 rounded bg-surface-container-low text-on-surface">
                        <span className="material-symbols-outlined text-secondary text-[16px]">warehouse</span>
                        <div className="flex flex-col">
                            <span className="font-label-caps text-label-caps text-on-surface-variant uppercase">Facility Station</span>
                            <span className="font-data-mono-sm text-data-mono-sm font-semibold text-on-surface">Prep Hub West - DC 09</span>
                        </div>
                    </div>
                </div>

                <div className="flex-1 max-w-xl mx-auto">
                    <form onSubmit={handleSearchSubmit} className="relative flex items-center w-full">
                        <span className="material-symbols-outlined absolute left-space-sm text-outline text-[18px]">qr_code_scanner</span>
                        <input
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="w-full h-9 pl-9 pr-14 bg-surface-container-low text-on-surface font-data-mono-md text-data-mono-md uppercase rounded outline-none placeholder:text-outline focus:bg-surface-container-lowest border border-transparent focus:border-secondary transition-colors"
                            placeholder="SCAN / ENTER RETURN ID, LPN, OR RMA..."
                            type="text"
                        />
                        <button type="submit" className="absolute right-space-sm font-data-mono-sm text-data-mono-sm bg-surface-container px-1 py-0.5 rounded text-on-surface-variant hover:text-on-surface">
                            [ENTER]
                        </button>
                    </form>
                </div>

                <div className="flex items-center gap-space-md">
                    <div className="hidden lg:flex items-center gap-space-xs px-space-sm py-1 rounded bg-surface-container">
                        <span className="w-2 h-2 rounded-full bg-on-tertiary-container animate-pulse"></span>
                        <span className="font-data-mono-sm text-data-mono-sm uppercase text-on-tertiary-container font-semibold">MOCK ACTIVE</span>
                    </div>

                    <div className="flex items-center gap-space-sm pl-space-sm">
                        <div className="text-right hidden xl:block">
                            <span className="font-body-sm text-body-sm font-semibold block text-on-surface">E. Marcus (Supv)</span>
                            <span className="font-data-mono-sm text-data-mono-sm text-on-surface-variant">STA-W09-OPS</span>
                        </div>
                        <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                            <span className="material-symbols-outlined text-on-primary text-[18px]">person</span>
                        </div>
                    </div>
                </div>
            </div>

            <div className="h-10 w-full px-margin bg-surface-container-low flex items-center justify-between">
                <nav className="flex items-center gap-space-xs h-full py-1">
                    <button
                        onClick={onDashboard}
                        className="px-space-md py-1 rounded text-body-sm font-medium transition-colors text-on-surface font-semibold bg-surface-container-lowest shadow-sm"
                    >
                        Dashboard
                    </button>
                    <button
                        disabled
                        className="px-space-md py-1 rounded text-body-sm font-medium text-on-surface-variant opacity-50 cursor-default"
                    >
                        Inspection Detail
                    </button>
                    <button
                        disabled
                        className="px-space-md py-1 rounded text-body-sm font-medium text-on-surface-variant opacity-50 cursor-default"
                    >
                        Batch Queue
                    </button>
                    <button
                        disabled
                        className="px-space-md py-1 rounded text-body-sm font-medium text-on-surface-variant opacity-50 cursor-default"
                    >
                        Audit Log
                    </button>
                </nav>

                <div className="hidden sm:flex items-center gap-space-md">
                    <div className="flex items-center gap-space-xs">
                        <span className="font-label-caps text-label-caps text-on-surface-variant uppercase">STATION ID:</span>
                        <span className="font-data-mono-sm text-data-mono-sm font-bold text-on-surface">DC09-DOCK-R04</span>
                    </div>
                    <div className="flex items-center gap-space-xs">
                        <span className="font-label-caps text-label-caps text-on-surface-variant uppercase">SHIFT:</span>
                        <span className="font-data-mono-sm text-data-mono-sm text-on-surface">ALPHA-01</span>
                    </div>
                </div>
            </div>
        </header>
    );
}
