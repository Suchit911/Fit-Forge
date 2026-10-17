/**
 * Real-Time Camera Viewport with Integrated Skeleton Overlay & Live HUD (Phase 9B.6).
 *
 * Preserves the approved dark aesthetic and glassmorphic card language of the existing viewport.
 */

import React, { useState } from 'react'
import {
  Play,
  Pause,
  Square,
  Camera,
  RefreshCw,
  AlertCircle,
  Activity,
  Zap,
} from 'lucide-react'
import type {
  StreamLifecycleState,
  ConnectionStatus,
  PoseLandmark,
} from '../../types/formStream'
import { SkeletonOverlay } from './SkeletonOverlay'

export interface CameraLiveViewportProps {
  videoRef: React.RefObject<HTMLVideoElement | null>
  streamState: StreamLifecycleState
  connectionStatus: ConnectionStatus
  repCount: number
  fsmState: string
  trackingStatus: string
  latestScore: number | null
  scoreStatus: string | null
  landmarks: PoseLandmark[]
  jointAngles: Record<string, number>
  fps: number
  latencyMs: number | null
  error: string | null
  onStart: () => void
  onPause: () => void
  onResume: () => void
  onStop: () => void
}

export const CameraLiveViewport: React.FC<CameraLiveViewportProps> = ({
  videoRef,
  streamState,
  connectionStatus,
  repCount,
  fsmState,
  trackingStatus,
  latestScore,
  scoreStatus,
  landmarks,
  jointAngles,
  fps,
  latencyMs,
  error,
  onStart,
  onPause,
  onResume,
  onStop,
}) => {
  const [isMirrored, setIsMirrored] = useState(true)

  const isAnalyzing = streamState === 'ANALYZING'
  const isPaused = streamState === 'PAUSED'
  const isConnecting = streamState === 'CONNECTING' || streamState === 'CAMERA_PERMISSION'
  const hasError = streamState === 'ERROR' || !!error

  // Extract primary angle if available
  const primaryAngleKey = Object.keys(jointAngles)[0]
  const primaryAngleVal = primaryAngleKey ? jointAngles[primaryAngleKey] : null

  return (
    <div className="relative aspect-[16/9] w-full rounded-3xl overflow-hidden bg-slate-950 border border-slate-800 shadow-2xl group text-left">
      {/* 1. Live Video Stream Element */}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className={`w-full h-full object-cover ${isMirrored ? 'transform -scale-x-100' : ''}`}
        aria-label="Live Camera Feed for Form Analysis"
      />

      {/* Subtle overlay gradient */}
      <div className="absolute inset-0 bg-gradient-to-t from-slate-950/90 via-transparent to-slate-950/40 pointer-events-none" />

      {/* 2. Skeleton Canvas Overlay */}
      <SkeletonOverlay
        landmarks={landmarks}
        trackingStatus={trackingStatus}
        isAnalyzing={isAnalyzing || isPaused}
        mirrored={isMirrored}
      />

      {/* 3. Top Header Badges Overlay */}
      <div className="absolute top-3 left-3 right-3 flex items-center justify-between pointer-events-none">
        {/* Connection & FSM Status */}
        <div className="flex items-center gap-2">
          {/* Connection Pill */}
          <div className="flex items-center gap-1.5 rounded-full bg-slate-950/80 border border-slate-800 px-3 py-1 backdrop-blur-md">
            <span
              className={`h-2 w-2 rounded-full ${
                connectionStatus === 'CONNECTED'
                  ? 'bg-emerald-500 animate-pulse'
                  : connectionStatus === 'CONNECTING' || connectionStatus === 'RECONNECTING'
                  ? 'bg-amber-500 animate-ping'
                  : 'bg-slate-500'
              }`}
            />
            <span className="text-[11px] font-mono uppercase text-slate-300">
              {connectionStatus}
            </span>
          </div>

          {/* FSM Phase Pill */}
          {(isAnalyzing || isPaused) && (
            <div className="hidden sm:flex items-center gap-1.5 rounded-full bg-slate-950/80 border border-slate-800 px-3 py-1 backdrop-blur-md">
              <Activity className="h-3 w-3 text-emerald-400" />
              <span className="text-[11px] font-mono text-slate-300">
                Phase: <span className="font-bold text-emerald-400">{fsmState}</span>
              </span>
            </div>
          )}
        </div>

        {/* Telemetry (FPS & Latency) */}
        <div className="flex items-center gap-2">
          {(isAnalyzing || isPaused) && (
            <>
              {latencyMs !== null && (
                <div className="hidden md:flex items-center gap-1 rounded-full bg-slate-950/80 border border-slate-800 px-2.5 py-1 backdrop-blur-md text-[11px] font-mono text-slate-400">
                  <Zap className="h-3 w-3 text-amber-400" />
                  <span>{latencyMs}ms</span>
                </div>
              )}
              <div className="rounded-full bg-slate-950/80 border border-slate-800 px-2.5 py-1 backdrop-blur-md text-[11px] font-mono text-slate-400">
                {fps} FPS
              </div>
            </>
          )}

          {/* Mirror Toggle Button */}
          <button
            type="button"
            onClick={() => setIsMirrored(!isMirrored)}
            className="pointer-events-auto flex h-7 w-7 items-center justify-center rounded-full bg-slate-900/80 border border-slate-700 text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
            title={isMirrored ? 'Disable Mirror Preview' : 'Enable Mirror Preview'}
            aria-label="Toggle camera mirror mode"
          >
            <Camera className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* 4. Floating HUD Metrics (Rep Counter & Score Pill) */}
      {(isAnalyzing || isPaused) && (
        <div className="absolute top-14 left-4 flex flex-col gap-2 pointer-events-none">
          {/* Rep Counter Box */}
          <div className="rounded-2xl bg-slate-950/85 border border-emerald-500/30 p-3 backdrop-blur-md text-left shadow-xl min-w-[90px]">
            <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">
              Completed Reps
            </span>
            <span className="text-3xl font-extrabold font-mono text-emerald-400 leading-none">
              {repCount}
            </span>
          </div>

          {/* Form Score Box */}
          <div className="rounded-2xl bg-slate-950/85 border border-slate-800 p-2.5 backdrop-blur-md text-left shadow-xl">
            <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">
              Latest Score
            </span>
            <div className="flex items-baseline gap-1 mt-0.5">
              <span className="text-xl font-bold font-mono text-white">
                {latestScore !== null ? Math.round(latestScore) : '--'}
              </span>
              {scoreStatus && (
                <span className="text-[10px] font-mono text-slate-400">
                  ({scoreStatus})
                </span>
              )}
            </div>
          </div>

          {/* Primary Joint Angle Box */}
          {primaryAngleVal !== null && (
            <div className="rounded-2xl bg-slate-950/85 border border-slate-800 p-2 backdrop-blur-md text-left shadow-xl">
              <span className="text-[9px] font-mono text-slate-400 uppercase tracking-wider block">
                {primaryAngleKey?.replace(/_/g, ' ')}
              </span>
              <span className="text-sm font-bold font-mono text-emerald-400">
                {Math.round(primaryAngleVal)}°
              </span>
            </div>
          )}
        </div>
      )}

      {/* 5. Initial / Connecting / Error State Overlay (When not streaming) */}
      {!isAnalyzing && !isPaused && (
        <div className="absolute inset-0 flex flex-col items-center justify-center p-6 bg-slate-950/70 backdrop-blur-sm">
          {hasError ? (
            <div className="max-w-md text-center space-y-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-rose-500/20 text-rose-400 mx-auto">
                <AlertCircle className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Camera or Stream Error</h3>
                <p className="text-sm text-slate-400 mt-1">{error}</p>
              </div>
              <button
                type="button"
                onClick={onStart}
                className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-5 py-2.5 text-sm font-bold text-slate-950 hover:bg-emerald-400 transition-colors shadow-lg cursor-pointer"
              >
                <RefreshCw className="h-4 w-4" />
                Retry Connection
              </button>
            </div>
          ) : isConnecting ? (
            <div className="text-center space-y-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 mx-auto animate-spin">
                <RefreshCw className="h-6 w-6" />
              </div>
              <h3 className="text-base font-bold text-white">Connecting Form Stream...</h3>
              <p className="text-xs font-mono text-slate-400">
                {streamState === 'CAMERA_PERMISSION'
                  ? 'Please allow camera access in your browser'
                  : 'Establishing secure streaming session'}
              </p>
            </div>
          ) : (
            <div className="text-center space-y-4 max-w-sm">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 mx-auto">
                <Camera className="h-7 w-7" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Live Form Analysis</h3>
                <p className="text-xs text-slate-400 mt-1">
                  Start your camera to analyze exercise technique, count reps, and receive deterministic form feedback in real time.
                </p>
              </div>
              <button
                type="button"
                onClick={onStart}
                className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-6 py-3 text-sm font-bold text-slate-950 hover:bg-emerald-400 transition-colors shadow-lg cursor-pointer"
              >
                <Play className="h-4 w-4 fill-slate-950" />
                Start Live Analysis
              </button>
            </div>
          )}
        </div>
      )}

      {/* 6. Bottom Stream Control Bar */}
      <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between gap-4 rounded-2xl bg-slate-950/85 border border-slate-800 p-3 backdrop-blur-md">
        {/* Controls (Play/Pause/Resume/Stop) */}
        <div className="flex items-center gap-3">
          {isAnalyzing ? (
            <button
              type="button"
              onClick={onPause}
              className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-800 text-slate-200 hover:bg-slate-700 hover:text-white transition-colors cursor-pointer"
              title="Pause Analysis"
              aria-label="Pause Analysis"
            >
              <Pause className="h-4 w-4" />
            </button>
          ) : isPaused ? (
            <button
              type="button"
              onClick={onResume}
              className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition-colors cursor-pointer"
              title="Resume Analysis"
              aria-label="Resume Analysis"
            >
              <Play className="h-4 w-4 fill-slate-950 ml-0.5" />
            </button>
          ) : (
            <button
              type="button"
              onClick={onStart}
              className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition-colors cursor-pointer"
              title="Start Analysis"
              aria-label="Start Analysis"
            >
              <Play className="h-4 w-4 fill-slate-950 ml-0.5" />
            </button>
          )}

          {(isAnalyzing || isPaused) && (
            <button
              type="button"
              onClick={onStop}
              className="flex h-9 w-9 items-center justify-center rounded-full bg-rose-500/20 text-rose-400 hover:bg-rose-500 hover:text-slate-950 transition-colors cursor-pointer border border-rose-500/30"
              title="Stop Analysis & Release Camera"
              aria-label="Stop Analysis"
            >
              <Square className="h-3.5 w-3.5 fill-current" />
            </button>
          )}

          <div className="text-xs font-mono text-slate-300">
            {isAnalyzing
              ? 'Analyzing live frame stream'
              : isPaused
              ? 'Analysis paused'
              : 'Camera ready'}
          </div>
        </div>

        {/* Rep completion feedback or hint */}
        <div className="hidden sm:block text-right">
          <span className="text-xs font-mono text-slate-400">
            {trackingStatus === 'TRACKING' ? (
              <span className="text-emerald-400">✓ Pose Locked</span>
            ) : (
              <span className="text-slate-400">Target: 25 FPS</span>
            )}
          </span>
        </div>
      </div>

      {/* Hidden Live Region for Screen Reader Announcements */}
      <div role="status" aria-live="polite" className="sr-only">
        {isAnalyzing && `Live analysis active for ${fsmState}. Reps: ${repCount}`}
        {isPaused && 'Live analysis paused'}
        {streamState === 'STOPPED' && `Analysis stopped. Final reps: ${repCount}`}
        {error && `Error: ${error}`}
      </div>
    </div>
  )
}
