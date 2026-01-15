import type { NextApiRequest, NextApiResponse } from 'next'

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  res.status(200).json({
    alerts: [
      {
        id: 'alert-1',
        type: 'Gun Detected',
        confidence: 0.91,
        timestamp: Date.now(),
        presignedUrl: 'https://your-kinesis-url.mp4', //TODO: Replace with real presigned url
      },

    ],
  })
}
