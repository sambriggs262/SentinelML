import { useState } from 'react'
import useSWR from 'swr'

interface Alert {
  id: string
  type: string
  confidence: number
  timestamp: number
  presignedUrl: string
}

interface AlertsResponse {
  alerts: Alert[]
}

const fetcher = (url: string): Promise<AlertsResponse> =>
  fetch(url).then(res => res.json())

export default function Dashboard() {
  const { data, error, isLoading } = useSWR<AlertsResponse>('/api/alerts', fetcher, {
    refreshInterval: 5000,
  })

  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null)

  return (
    <main className="p-8 bg-gray-900 min-h-screen text-white space-y-6">
      <h1 className="text-4xl font-bold mb-4">Detection Dashboard</h1>

      {error && <p className="text-red-500">Error loading alerts.</p>}
      {isLoading && <p>Loading alerts...</p>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {data?.alerts?.map(alert => (
          <div
            key={alert.id}
            className={`p-4 rounded border ${
              selectedAlert?.id === alert.id
                ? 'border-blue-500 bg-gray-800'
                : 'border-gray-700 bg-gray-800'
            } hover:border-blue-300 hover:shadow-xl cursor-pointer transition`}
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
        ))}
      </div>

      <section className="mt-8 p-6 bg-gray-800 rounded-lg shadow-lg">
        <h2 className="text-2xl font-semibold mb-4">Live Feed</h2>

        {selectedAlert ? (
          <>
            <p className="mb-2"><strong>Type:</strong> {selectedAlert.type}</p>
            <p className="mb-4"><strong>Detected At:</strong> {new Date(selectedAlert.timestamp).toLocaleString()}</p>

            <video className="w-full max-h-[500px] rounded" controls>
              <source src={selectedAlert.presignedUrl} type="video/mp4" />
              Your browser does not support the video tag.
            </video>
          </>
        ) : (
          <p className="text-gray-400 italic">Select an alert to view the feed.</p>
        )}
      </section>
    </main>
  )
}
