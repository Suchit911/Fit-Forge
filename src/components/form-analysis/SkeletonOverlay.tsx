/**
 * Real-Time Canvas Skeleton Overlay Component (Phase 9B.6).
 *
 * Renders backend-derived pose landmarks over the live camera feed.
 *
 * Requirements:
 *   - Strictly uses backend landmarks (zero frontend MediaPipe or pose inference).
 *   - Uses standard MediaPipe 33-landmark connectivity.
 *   - Color-codes joint nodes and connection lines by confidence.
 *   - When no landmarks or insufficient data are present, does NOT render a fake skeleton;
 *     displays honest non-judgmental prompt ("Move into frame" / "Pose confidence low").
 *   - Synchronized with video element dimensions and devicePixelRatio.
 */

import React, { useRef, useEffect } from 'react'
import type { PoseLandmark } from '../../types/formStream'

export interface SkeletonOverlayProps {
  landmarks: PoseLandmark[]
  trackingStatus: string
  isAnalyzing: boolean
  mirrored?: boolean
}

// Canonical connections between MediaPipe 33 landmarks
const POSE_CONNECTIONS: [number, number][] = [
  // Face / Head
  [0, 11], // Nose to Left Shoulder
  [0, 12], // Nose to Right Shoulder

  // Shoulders & Torso
  [11, 12], // Left Shoulder to Right Shoulder
  [11, 23], // Left Shoulder to Left Hip
  [12, 24], // Right Shoulder to Right Hip
  [23, 24], // Left Hip to Right Hip

  // Left Arm
  [11, 13], // Left Shoulder to Left Elbow
  [13, 15], // Left Elbow to Left Wrist

  // Right Arm
  [12, 14], // Right Shoulder to Right Elbow
  [14, 16], // Right Elbow to Right Wrist

  // Left Leg
  [23, 25], // Left Hip to Left Knee
  [25, 27], // Left Knee to Left Ankle
  [27, 29], // Left Ankle to Left Heel
  [27, 31], // Left Ankle to Left Foot Index

  // Right Leg
  [24, 26], // Right Hip to Right Knee
  [26, 28], // Right Knee to Right Ankle
  [28, 30], // Right Ankle to Right Heel
  [28, 32], // Right Ankle to Right Foot Index
]

export const SkeletonOverlay: React.FC<SkeletonOverlayProps> = ({
  landmarks,
  trackingStatus,
  isAnalyzing,
  mirrored = true,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Match canvas coordinate resolution to display size and device pixel ratio
    const dpr = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()
    const width = rect.width
    const height = rect.height

    if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) {
      canvas.width = Math.round(width * dpr)
      canvas.height = Math.round(height * dpr)
    }

    ctx.save()
    ctx.scale(dpr, dpr)
    ctx.clearRect(0, 0, width, height)

    // Only render skeleton if analyzing and valid landmarks exist
    if (!isAnalyzing || !landmarks || landmarks.length === 0) {
      ctx.restore()
      return
    }

    // Map landmarks by ID for O(1) connection lookup
    const landmarkMap = new Map<number, PoseLandmark>()
    for (const lm of landmarks) {
      landmarkMap.set(lm.id, lm)
    }

    // Helper to compute canvas coordinates
    const getPoint = (lm: PoseLandmark): { x: number; y: number } => {
      // Normalized [0, 1] coordinates
      const normX = mirrored ? 1.0 - lm.x : lm.x
      const normY = lm.y
      return {
        x: normX * width,
        y: normY * height,
      }
    }

    // 1. Draw Connection Lines
    ctx.lineWidth = 3
    ctx.lineCap = 'round'

    for (const [idA, idB] of POSE_CONNECTIONS) {
      const lmA = landmarkMap.get(idA)
      const lmB = landmarkMap.get(idB)

      if (!lmA || !lmB) continue

      const minVis = Math.min(lmA.visibility, lmB.visibility)
      if (minVis < 0.25) continue // Skip occluded / unobservable segments

      const pA = getPoint(lmA)
      const pB = getPoint(lmB)

      ctx.beginPath()
      ctx.moveTo(pA.x, pA.y)
      ctx.lineTo(pB.x, pB.y)

      if (minVis >= 0.6) {
        ctx.strokeStyle = '#10b981' // Vibrant Emerald for high confidence
      } else if (minVis >= 0.4) {
        ctx.strokeStyle = '#f59e0b' // Amber for moderate confidence
      } else {
        ctx.strokeStyle = '#ef4444' // Red for borderline visibility
      }
      ctx.stroke()
    }

    // 2. Draw Landmark Joint Nodes
    for (const lm of landmarks) {
      if (lm.visibility < 0.25) continue

      const pt = getPoint(lm)
      const radius = lm.id === 0 ? 6 : 5

      ctx.beginPath()
      ctx.arc(pt.x, pt.y, radius, 0, Math.PI * 2)

      if (lm.visibility >= 0.6) {
        ctx.fillStyle = '#10b981'
      } else if (lm.visibility >= 0.4) {
        ctx.fillStyle = '#f59e0b'
      } else {
        ctx.fillStyle = '#ef4444'
      }

      ctx.fill()
      ctx.strokeStyle = '#0f172a'
      ctx.lineWidth = 2
      ctx.stroke()
    }

    ctx.restore()
  }, [landmarks, isAnalyzing, mirrored])

  // Honest Insufficient Data / Searching feedback badges
  const showSearchingBadge =
    isAnalyzing &&
    (landmarks.length === 0 ||
      trackingStatus === 'LOST' ||
      trackingStatus === 'SEARCHING' ||
      trackingStatus === 'INSUFFICIENT_DATA')

  return (
    <div className="absolute inset-0 pointer-events-none">
      <canvas
        ref={canvasRef}
        className="w-full h-full block"
        aria-hidden="true"
      />

      {/* Non-judgmental Uncertainty Badge */}
      {showSearchingBadge && (
        <div
          role="status"
          aria-live="polite"
          className="absolute top-4 left-1/2 -translate-x-1/2 rounded-full bg-slate-950/80 border border-amber-500/40 px-4 py-1.5 backdrop-blur-md text-center shadow-lg"
        >
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500" />
            </span>
            <span className="text-xs font-mono font-medium text-amber-300">
              {trackingStatus === 'LOST' || landmarks.length === 0
                ? 'Move into frame'
                : 'Pose confidence low'}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
