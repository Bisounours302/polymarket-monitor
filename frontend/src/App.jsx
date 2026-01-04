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


const fetcher = (url) => fetch(url).then((res) => res.json());

function App() {
    const { data: alerts, mutate: refreshAlerts } = useSWR(`${API_URL}/alerts?limit=50`, fetcher, { refreshInterval: 5000 });
    const { data: stats } = useSWR(`${API_URL}/stats`, fetcher, { refreshInterval: 10000 });
    const [filterMode, setFilterMode] = useState("ALL"); // ALL | SUSPICIOUS
    const [showSettings, setShowSettings] = useState(false);

    // Settings State
    const [settings, setSettings] = useState({ notify_whales: true, notify_suspicious: true });

    // Load Settings
    useEffect(() => {
        fetch(`${API_URL}/settings`)
            .then(res => res.json())
            .then(setSettings)
            .catch(err => console.error("Failed to load settings", err));
    }, []);

    const saveSettings = async () => {
        try {
            await fetch(`${API_URL}/settings`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(settings)
            });
            setShowSettings(false);
        } catch (err) {
            console.error("Failed to save settings", err);
        }
    }

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
                                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                                System Operational
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
                            <div className="text-3xl font-mono animate-pulse text-primary">
                                LIVE
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
                                onClick={saveSettings}
                                className="px-4 py-2 text-sm bg-primary hover:bg-blue-600 text-white rounded-lg font-medium transition-colors shadow-lg shadow-blue-500/20"
                            >
                                Save Configuration
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

export default App
