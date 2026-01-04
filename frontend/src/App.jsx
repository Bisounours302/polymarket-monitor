import { useState, useEffect } from "react";
import useSWR from "swr";
import {
    Activity,
    Settings,
    ExternalLink,
    ShieldAlert,
    Zap,
    BarChart3,
    Search
} from "lucide-react";
import clsx from "clsx";

const API_URL = import.meta.env.VITE_API_URL || "/api";


console.log("Using API_URL:", API_URL);

const fetcher = (url) => fetch(url).then((res) => {
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
});

function App() {
    const { data: alerts } = useSWR(`${API_URL}/alerts?limit=50`, fetcher, { refreshInterval: 5000 });
    const { data: stats } = useSWR(`${API_URL}/stats`, fetcher, { refreshInterval: 10000 });

    // UI State
    const [filterMode, setFilterMode] = useState("ALL"); // ALL | SUSPICIOUS
    const [showSettings, setShowSettings] = useState(false);
    const [showDebug, setShowDebug] = useState(false);

    // Settings State
    const [settings, setSettings] = useState({
        notify_whales: true,
        notify_suspicious: true,
        system_active: true
    });

    // Debug State
    const [debugData, setDebugData] = useState(null);
    const [debugLoading, setDebugLoading] = useState(false);
    const [debugViewMode, setDebugViewMode] = useState("SMART");

    // Auto-fetch debug data when modal opens
    useEffect(() => {
        if (showDebug) {
            fetchDebugMarkets();
        }
    }, [showDebug]);

    // Load Settings
    useEffect(() => {
        fetch(`${API_URL}/settings`)
            .then(res => res.json())
            .then(setSettings)
            .catch(err => console.error("Failed to load settings", err));
    }, []);

    // Save Settings
    const saveSettings = async (newSettingsOverride) => {
        const toSave = newSettingsOverride || settings;
        try {
            await fetch(`${API_URL}/settings`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(toSave)
            });
            setSettings(toSave);
            if (!newSettingsOverride) setShowSettings(false);
        } catch (err) {
            console.error("Failed to save settings", err);
        }
    }

    const toggleSystem = () => {
        const newSettings = { ...settings, system_active: !settings.system_active };
        saveSettings(newSettings);
    };

    const fetchDebugMarkets = async () => {
        setDebugLoading(true);
        try {
            const res = await fetch(`${API_URL}/debug/markets`);
            const data = await res.json();
            setDebugData({ type: "markets", content: data });
        } catch (e) {
            setDebugData({ type: "error", content: String(e) });
        }
        setDebugLoading(false);
    };

    const fetchDebugTrades = async () => {
        setDebugLoading(true);
        try {
            // Fetch top market first to get ID
            const mRes = await fetch(`${API_URL}/debug/markets`);
            const mData = await mRes.json();
            if (mData.data && mData.data.length > 0) {
                const clobId = mData.data[0].clobTokenIds[0];
                const tRes = await fetch(`${API_URL}/debug/trades?market_id=${clobId}`);
                const tData = await tRes.json();
                setDebugData({ type: "trades", content: tData });
            } else {
                setDebugData({ type: "error", content: "No active markets found to test trades." });
            }
        } catch (e) {
            setDebugData({ type: "error", content: String(e) });
        }
        setDebugLoading(false);
    };

    const filteredAlerts = alerts?.filter(a => {
        if (filterMode === "SUSPICIOUS") return a.nonce < 10;
        return true;
    }) || [];

    return (
        <div className="min-h-screen p-8 bg-background relative overflow-hidden">
            {/* Background Glow */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-primary/10 rounded-full blur-[120px] pointer-events-none" />

            <main className="max-w-7xl mx-auto relative z-10 space-y-8">

                {/* Header */}
                <header className="flex justify-between items-center glass-panel p-6">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-primary/20 rounded-lg">
                            <Activity className="text-primary w-8 h-8" />
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-400">
                                Polymarket Monitor
                            </h1>
                            <div className="flex items-center gap-2 text-sm text-gray-400">
                                <span className={clsx("w-2 h-2 rounded-full animate-pulse", settings.system_active ? "bg-green-500" : "bg-red-500")} />
                                {settings.system_active ? "System Operational" : "System Paused"}
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        {/* Stats Chips */}
                        <div className="hidden md:flex gap-6 pr-8 border-r border-white/10">
                            <div className="text-right">
                                <p className="text-xs text-gray-500 uppercase">Volume Today</p>
                                <p className="font-mono text-lg font-bold text-white">${stats?.total_volume?.toLocaleString() || "..."}</p>
                            </div>
                            <div className="text-right">
                                <p className="text-xs text-gray-500 uppercase">Total Alerts</p>
                                <p className="font-mono text-lg font-bold text-accent">{stats?.total_alerts || "..."}</p>
                            </div>
                        </div>

                        {/* System Toggle */}
                        <button
                            onClick={toggleSystem}
                            className={clsx(
                                "px-4 py-2 rounded-lg font-bold text-sm transition-all border",
                                settings.system_active
                                    ? "bg-green-500/10 text-green-400 border-green-500/20 hover:bg-green-500/20"
                                    : "bg-red-500/10 text-red-400 border-red-500/20 hover:bg-red-500/20"
                            )}
                        >
                            {settings.system_active ? "ON" : "OFF"}
                        </button>

                        <button
                            onClick={() => setShowDebug(true)}
                            className="p-3 hover:bg-white/5 rounded-lg transition-colors text-gray-400 hover:text-white"
                            title="API Inspector"
                        >
                            <Search className="w-6 h-6" />
                        </button>

                        <button
                            onClick={() => setShowSettings(true)}
                            className="p-3 hover:bg-white/5 rounded-lg transition-colors text-gray-400 hover:text-white"
                        >
                            <Settings className="w-6 h-6" />
                        </button>
                    </div>
                </header>

                {/* Content Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">

                    {/* Sidebar Controls */}
                    <div className="lg:col-span-1 space-y-4">
                        <div className="glass-panel p-4 space-y-2">
                            <h3 className="text-sm font-semibold text-gray-400 mb-4 px-2 uppercase tracking-wider">Feed Filter</h3>

                            <button
                                onClick={() => setFilterMode("ALL")}
                                className={clsx(
                                    "w-full text-left p-3 rounded-lg flex items-center gap-3 transition-all",
                                    filterMode === "ALL" ? "bg-primary/20 text-blue-300 border border-primary/30" : "hover:bg-white/5 text-gray-400"
                                )}
                            >
                                <BarChart3 className="w-5 h-5" />
                                <span className="font-medium">All Whales</span>
                            </button>

                            <button
                                onClick={() => setFilterMode("SUSPICIOUS")}
                                className={clsx(
                                    "w-full text-left p-3 rounded-lg flex items-center gap-3 transition-all",
                                    filterMode === "SUSPICIOUS" ? "bg-danger/20 text-red-300 border border-danger/30" : "hover:bg-white/5 text-gray-400"
                                )}
                            >
                                <ShieldAlert className="w-5 h-5" />
                                <span className="font-medium">Suspicious Only</span>
                            </button>
                        </div>

                        <div className="glass-panel p-6 text-center">
                            <p className="text-xs text-gray-500 mb-2">SCANNING</p>
                            <div className={clsx("text-3xl font-mono", settings.system_active ? "animate-pulse text-primary" : "text-gray-600")}>
                                {settings.system_active ? "LIVE" : "PAUSED"}
                            </div>
                        </div>
                    </div>

                    {/* Main Feed */}
                    <div className="lg:col-span-3 glass-panel overflow-hidden min-h-[600px]">
                        <div className="p-6 border-b border-white/5 flex justify-between items-center">
                            <h2 className="font-semibold text-lg flex items-center gap-2">
                                {filterMode === "SUSPICIOUS" ? "🚨 Suspicious Activity" : "🌊 Large Trades Feed"}
                                <span className="text-xs bg-white/10 px-2 py-1 rounded-full text-gray-400">
                                    {filteredAlerts.length}
                                </span>
                            </h2>
                        </div>

                        <div className="overflow-x-auto">
                            <table className="w-full text-left text-sm text-gray-400">
                                <thead className="bg-white/5 text-gray-200">
                                    <tr>
                                        <th className="p-4 font-medium uppercase text-xs tracking-wider">Time</th>
                                        <th className="p-4 font-medium uppercase text-xs tracking-wider">Amount (USD)</th>
                                        <th className="p-4 font-medium uppercase text-xs tracking-wider">Type</th>
                                        <th className="p-4 font-medium uppercase text-xs tracking-wider">Market</th>
                                        <th className="p-4 font-medium uppercase text-xs tracking-wider">Wallet / Nonce</th>
                                        <th className="p-4 text-right">Link</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-white/5">
                                    {filteredAlerts.length === 0 ? (
                                        <tr>
                                            <td colSpan={6} className="p-12 text-center text-gray-600">
                                                No alerts found in this category.
                                            </td>
                                        </tr>
                                    ) : filteredAlerts.map((alert) => (
                                        <tr key={alert.id} className="table-row hover:bg-white/[0.02]">
                                            <td className="p-4 font-mono text-gray-500 whitespace-nowrap">
                                                {new Date(alert.timestamp).toLocaleTimeString()}
                                            </td>
                                            <td className="p-4 font-mono font-bold text-white">
                                                ${alert.amount_usd.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                                            </td>
                                            <td className="p-4">
                                                {alert.nonce < 10 ? (
                                                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-danger/20 text-danger text-xs font-bold border border-danger/20">
                                                        <ShieldAlert className="w-3 h-3" /> SUSPICIOUS
                                                    </span>
                                                ) : (
                                                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-primary/20 text-primary text-xs font-bold border border-primary/20">
                                                        <Zap className="w-3 h-3" /> WHALE
                                                    </span>
                                                )}
                                            </td>
                                            <td className="p-4 max-w-[250px] truncate text-gray-300" title={alert.market_name}>
                                                {alert.market_name}
                                            </td>
                                            <td className="p-4 font-mono text-xs">
                                                <div className="text-gray-300">{alert.wallet_address.substring(0, 6)}...{alert.wallet_address.substring(38)}</div>
                                                <div className="text-gray-600">Nonce: {alert.nonce}</div>
                                            </td>
                                            <td className="p-4 text-right">
                                                <a
                                                    href={alert.polymarket_url}
                                                    target="_blank"
                                                    className="inline-flex p-2 hover:bg-white/10 rounded-md transition-colors text-primary"
                                                >
                                                    <ExternalLink className="w-4 h-4" />
                                                </a>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>

                </div>
            </main>

            {/* Settings Modal */}
            {showSettings && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
                    <div className="glass-panel w-full max-w-md p-6 space-y-6 animate-in zoom-in-95 duration-200">
                        <h2 className="text-xl font-bold text-white flex items-center gap-2">
                            <Settings className="w-5 h-5 text-gray-400" /> Settings
                        </h2>

                        <div className="space-y-4">
                            <label className="flex items-center justify-between p-4 bg-white/5 rounded-lg cursor-pointer hover:bg-white/10 transition">
                                <div>
                                    <span className="block font-medium text-white">Notify on Whales</span>
                                    <span className="text-xs text-gray-500">Alerts {'>'} $5k from active wallets</span>
                                </div>
                                <input
                                    type="checkbox"
                                    checked={settings.notify_whales}
                                    onChange={(e) => setSettings({ ...settings, notify_whales: e.target.checked })}
                                    className="w-5 h-5 rounded border-gray-600 bg-gray-700 text-primary focus:ring-primary"
                                />
                            </label>

                            <label className="flex items-center justify-between p-4 bg-white/5 rounded-lg cursor-pointer hover:bg-white/10 transition">
                                <div>
                                    <span className="block font-medium text-white">Notify on Suspicious</span>
                                    <span className="text-xs text-gray-500">Alerts from fresh wallets (Nonce &lt; 10)</span>
                                </div>
                                <input
                                    type="checkbox"
                                    checked={settings.notify_suspicious}
                                    onChange={(e) => setSettings({ ...settings, notify_suspicious: e.target.checked })}
                                    className="w-5 h-5 rounded border-gray-600 bg-gray-700 text-primary focus:ring-primary"
                                />
                            </label>
                        </div>

                        <div className="flex justify-end gap-3 pt-4 border-t border-white/10">
                            <button
                                onClick={() => setShowSettings(false)}
                                className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={() => saveSettings()}
                                className="px-4 py-2 text-sm bg-primary hover:bg-blue-600 text-white rounded-lg font-medium transition-colors shadow-lg shadow-blue-500/20"
                            >
                                Save Configuration
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Auto-Refresh Logic for Debug Inspector */}
            const [refreshTimer, setRefreshTimer] = useState(5);

            useEffect(() => {
                if (!showDebug) return; // Only run when debug modal is open

                const fetchData = async () => {
                    try {
                        if (debugViewMode === "SMART" || debugViewMode === "RAW") {
                            const res = await fetch(`${API_URL}/debug/markets`);
            const data = await res.json();
            setDebugData({type: "markets", content: data });
                        } else if (debugViewMode === "SCANNER") {
                            const res = await fetch(`${API_URL}/debug/feed`);
            const data = await res.json();
            setDebugData({type: "scanner", content: data });
                        }
                    } catch (e) {
                console.error("Auto-fetch error:", e);
                    }
                };

            // Initial Fetch when modal opens or mode changes
            fetchData();

                const interval = setInterval(() => {
                setRefreshTimer((prev) => {
                    if (prev <= 1) { // When timer hits 0 or 1, fetch and reset
                        fetchData();
                        return 5; // Reset to 5 seconds
                    }
                    return prev - 1;
                });
                }, 1000); // Update every second

                return () => clearInterval(interval); // Cleanup on unmount or dependency change
            }, [showDebug, debugViewMode]); // Dependencies: re-run effect if these change

            {/* API Inspector Modal */}
            {showDebug && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
                    <div className="glass-panel w-full max-w-5xl p-6 space-y-4 animate-in zoom-in-95 duration-200 h-[85vh] flex flex-col">

                        <div className="flex justify-between items-center pb-4 border-b border-white/10">
                            <div className="flex items-center gap-4">
                                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                                    <Search className="w-5 h-5 text-gray-400" /> Live Inspector
                                </h2>
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => setDebugViewMode("SMART")}
                                        className={clsx("px-3 py-1 text-xs rounded-lg transition-colors", debugViewMode === "SMART" || debugViewMode === "RAW" ? "bg-primary text-white" : "hover:bg-white/10 text-gray-400")}
                                    >
                                        Markets Cache
                                    </button>
                                    <button
                                        onClick={() => {
                                            setDebugViewMode("SCANNER");
                                        }}
                                        className={clsx("px-3 py-1 text-xs rounded-lg transition-colors", debugViewMode === "SCANNER" ? "bg-primary text-white" : "hover:bg-white/10 text-gray-400")}
                                    >
                                        Live Scanner ({debugData?.type === "scanner" ? debugData?.content?.count : 0})
                                    </button>
                                </div>

                                {/* Timer Badge */}
                                <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/5 text-xs font-mono text-gray-400">
                                    <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                                    Auto-refresh: {refreshTimer}s
                                </div>
                            </div>

                            <button onClick={() => setShowDebug(false)} className="bg-white/5 hover:bg-white/10 p-2 rounded-lg text-gray-400 transition-colors">✕</button>
                        </div>

                        {/* Content Area */}
                        <div className="flex-1 bg-black/30 rounded-lg overflow-hidden border border-white/5 relative">
                            {debugLoading && (
                                <div className="absolute inset-0 bg-black/60 flex items-center justify-center z-10 backdrop-blur-sm">
                                    <div className="flex items-center gap-2 text-primary">
                                        <span className="w-5 h-5 rounded-full border-2 border-current border-t-transparent animate-spin" />
                                        Syncing with Worker...
                                    </div>
                                </div>
                            )}

                            <div className="h-full overflow-auto p-4 custom-scrollbar">

                                {debugViewMode === "SCANNER" ? (
                                    <table className="w-full text-left text-xs text-gray-400 font-mono">
                                        <thead className="bg-white/5 sticky top-0 text-white">
                                            <tr>
                                                <th className="p-2">Time</th>
                                                <th className="p-2">Status</th>
                                                <th className="p-2">Amount</th>
                                                <th className="p-2">Market</th>
                                                <th className="p-2">Wallet</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-white/5">
                                            {debugData?.content?.data?.map((item, i) => (
                                                <tr key={i} className="hover:bg-white/5">
                                                    <td className="p-2 text-gray-500">{item.time}</td>
                                                    <td className={clsx("p-2 font-bold", (item.status || "").includes("Ignored") ? "text-gray-600" : "text-green-400")}>
                                                        {item.status || "Unknown"}
                                                    </td>
                                                    <td className="p-2">${item.amount}</td>
                                                    <td className="p-2 truncate max-w-[200px]" title={item.market}>{item.market}</td>
                                                    <td className="p-2 truncate max-w-[100px]">{item.wallet}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                ) : (
                                    // Existing Market Grid Logic
                                    debugViewMode === "RAW" ? (
                                        <pre className="font-mono text-xs text-green-400 whitespace-pre-wrap">
                                            {JSON.stringify(debugData, null, 2)}
                                        </pre>
                                    ) : (
                                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                            {/* Smart Cards */}
                                            {debugData?.content?.data?.map((market, idx) => (
                                                <div key={idx} className="bg-white/5 hover:bg-white/10 p-4 rounded-lg border border-white/5 transition-all text-sm space-y-2">
                                                    <div className="flex justify-between items-start gap-2">
                                                        <h4 className="font-medium text-white line-clamp-2">{market.question}</h4>
                                                        <span className="text-xs bg-black/40 px-2 py-1 rounded text-gray-400 font-mono">#{idx + 1}</span>
                                                    </div>

                                                    <div className="grid grid-cols-2 gap-2 text-xs py-2">
                                                        <div>
                                                            <p className="text-gray-500">Volume</p>
                                                            <p className="text-gray-300 font-mono">${parseInt(market.volume || 0).toLocaleString()}</p>
                                                        </div>
                                                        <div>
                                                            <p className="text-gray-500">Active</p>
                                                            <p className={clsx("font-bold", market.active ? "text-green-400" : "text-red-400")}>
                                                                {market.active ? "YES" : "NO"}
                                                            </p>
                                                        </div>
                                                    </div>

                                                    <div className="space-y-1 bg-black/20 p-2 rounded text-xs font-mono break-all">
                                                        <div className="flex gap-2">
                                                            <span className="text-gray-500 w-8">CID:</span>
                                                            <span className="text-blue-300 truncate">{market.conditionId}</span>
                                                        </div>
                                                        <div className="flex gap-2">
                                                            <span className="text-gray-500 w-8">TOK:</span>
                                                            <span className="text-purple-300 truncate">{market.clobTokenIds?.[0]}</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            ))}
                                            {!debugData?.content?.data && <div className="text-gray-500 p-4 col-span-full text-center">No cached data found. Worker might be starting...</div>}
                                        </div>
                                    )
                                )}
                            </div>
                        </div>

                        {/* Footer Info */}
                        <div className="flex justify-between text-xs text-gray-500 px-2">
                            <p>Data Source: {debugData?.content?.source === "cache" ? "Worker File System (data/debug_markets.json)" : "Live API Fallback"}</p>
                            <p>Items: {debugData?.content?.count || 0}</p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

export default App
