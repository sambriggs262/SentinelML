import { useState, useEffect } from "react";
import useSWR from "swr";

interface Alert {
  id: string;
  type: string;
  confidence: number;
  timestamp: number;
  presignedUrl: string;
}

interface AlertsResponse {
  alerts: Alert[];
}

const fetcher = async (url: string): Promise<AlertsResponse> => {
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to fetch alerts");
  return res.json();
};

export default function Dashboard() {
  const { data, error, isLoading, mutate } = useSWR<AlertsResponse>(
    "/api/alerts",
    fetcher,
    { refreshInterval: 3000 }
  );

  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);

  useEffect(() => {
    // Optional WS: only connect if provided (safe for open-source)
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL;
    if (!wsUrl) return;

    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const alert: Alert = JSON.parse(event.data);
        mutate((prev) => {
          const existing = prev?.alerts || [];
          return { alerts: [alert, ...existing].slice(0, 20) };
        }, false);
      } catch (err) {
        console.error("WebSocket message error:", err);
      }
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
    };

    return () => ws.close();
  }, [mutate]);

  return (
    <main className="p-8 bg-gray-900 min-h-screen text-white space-y-6">
      <h1 className="text-4xl font-bold mb-4">Detection Dashboard</h1>

      {/* Live Stream */}
      <section className="p-6 bg-gray-800 rounded-lg shadow-lg">
        <h2 className="text-2xl font-semibold mb-4">Live YOLO Stream</h2>

        {/* Option 1 (recommended): proxy via Next API route */}
        <img
          src="/api/video-feed"
          alt="Live YOLO Stream"
          className="w-auto h-auto max-w-full max-h-[500px] mx-auto rounded object-contain"
        />

        {/* Option 2 (if you prefer env var instead of proxy):
            const feedUrl = process.env.NEXT_PUBLIC_VIDEO_FEED_URL;
            and then <img src={feedUrl ?? ""} ... />
        */}
      </section>

      {/* Alerts */}
      <section className="p-6 bg-gray-800 rounded-lg shadow-lg">
        <h2 className="text-2xl font-semibold mb-4">Recent Alerts</h2>
        {error && <p className="text-red-500">Error loading alerts.</p>}
        {isLoading && <p>Loading alerts...</p>}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {data?.alerts?.length ? (
            data.alerts.map((alert) => (
              <div
                key={alert.id}
                className={`p-4 rounded border ${
                  selectedAlert?.id === alert.id
                    ? "border-blue-500 bg-gray-700"
                    : "border-gray-800 bg-gray-800"
                } hover:border-blue-300 hover:shadow-lg cursor-pointer transition`}
                onClick={() => setSelectedAlert(alert)}
              >
                <h2 className="text-xl font-semibold">{alert.type}</h2>
                <p className="text-sm text-gray-400">
                  Confidence: {(alert.confidence * 100).toFixed(1)}%
                </p>
                <p className="text-sm text-gray-400">
                  Time: {new Date(alert.timestamp).toLocaleString()}
                </p>
              </div>
            ))
          ) : (
            !isLoading && <p className="text-gray-400 italic">No alerts available.</p>
          )}
        </div>

        {selectedAlert && (
          <div className="mt-6">
            <h3 className="text-xl font-semibold mb-2">Alert Video</h3>
            <video
              src={selectedAlert.presignedUrl}
              controls
              className="w-full max-h-[400px] rounded"
            />
          </div>
        )}
      </section>
    </main>
  );
}
