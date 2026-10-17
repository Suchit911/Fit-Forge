/**
 * Real-Time Form Analysis Streaming & Camera Coordinator Hook (Phase 9B.6).
 *
 * Coordinates:
 *   Browser Camera (getUserMedia) -> Offscreen Canvas (JPEG) -> 32-Byte Packet Encoder ->
 *   WebSocket (Phase 9B.5) -> Pose + FSM + Heuristics + Scoring -> UI & Canvas Skeleton.
 *
 * Enforces:
 *   - 25 FPS maximum frame rate (40ms inter-frame interval).
 *   - Bounded latest-frame-wins backpressure (at most 1 frame in-flight; no unbounded queue).
 *   - Hardware release and track stoppage on pause, stop, or component unmount.
 *   - Authoritative backend rep counting and scoring (zero frontend score calculation).
 */

import { useState, useRef, useEffect, useCallback } from 'react'
import type {
  SupportedExerciseId,
  StreamLifecycleState,
  ConnectionStatus,
  PoseLandmark,
  HeuristicItem,
  CompletedRepItem,
  WSAnalysisMessage,
  WSRepCompletedMessage,
  WSErrorMessage,
  WSStoppedMessage,
} from '../types/formStream'
import { packFramePacket } from '../services/formPacketEncoder'
import { FormAnalysisWebSocket } from '../services/formAnalysisWebSocket'
import {
  resolveCVExerciseId,
  getCVUnsupportedExplanation,
} from '../utils/formAnalysisCapability.ts'

export interface UseFormAnalysisStreamOptions {
  initialExerciseId?: SupportedExerciseId
  onRepCompleted?: (rep: CompletedRepItem) => void
  onError?: (error: WSErrorMessage) => void
  onStopped?: (msg: WSStoppedMessage) => void
}

export interface UseFormAnalysisStreamReturn {
  videoRef: React.RefObject<HTMLVideoElement | null>
  streamState: StreamLifecycleState
  connectionStatus: ConnectionStatus
  exerciseId: SupportedExerciseId
  sessionId: string | null
  repCount: number
  fsmState: string
  trackingStatus: string
  latestScore: number | null
  scoreStatus: string | null
  landmarks: PoseLandmark[]
  jointAngles: Record<string, number>
  heuristics: HeuristicItem[]
  feedback: string[]
  completedReps: CompletedRepItem[]
  fps: number
  droppedFrames: number
  latencyMs: number | null
  error: string | null
  startCamera: () => Promise<void>
  startAnalysis: () => Promise<void>
  pauseAnalysis: () => void
  resumeAnalysis: () => void
  stopAnalysis: () => void
  selectExercise: (id: SupportedExerciseId) => void
}

const TARGET_FPS = 25
const FRAME_INTERVAL_MS = 1000 / TARGET_FPS // 40ms
const MAX_WIDTH = 1280
const MAX_HEIGHT = 720
const JPEG_QUALITY = 0.8

export function useFormAnalysisStream(
  options: UseFormAnalysisStreamOptions = {}
): UseFormAnalysisStreamReturn {
  const initialResolved = resolveCVExerciseId(options.initialExerciseId) || 'squat'
  const isInitialUnsupported = !!options.initialExerciseId && !resolveCVExerciseId(options.initialExerciseId)

  const [exerciseId, setExerciseId] = useState<SupportedExerciseId>(initialResolved)
  const [streamState, setStreamState] = useState<StreamLifecycleState>(
    isInitialUnsupported ? 'ERROR' : 'INITIAL'
  )
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('DISCONNECTED')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [repCount, setRepCount] = useState<number>(0)
  const [fsmState, setFsmState] = useState<string>('IDLE')
  const [trackingStatus, setTrackingStatus] = useState<string>('SEARCHING')
  const [latestScore, setLatestScore] = useState<number | null>(null)
  const [scoreStatus, setScoreStatus] = useState<string | null>(null)
  const [landmarks, setLandmarks] = useState<PoseLandmark[]>([])
  const [jointAngles, setJointAngles] = useState<Record<string, number>>({})
  const [heuristics, setHeuristics] = useState<HeuristicItem[]>([])
  const [feedback, setFeedback] = useState<string[]>([])
  const [completedReps, setCompletedReps] = useState<CompletedRepItem[]>([])
  const [fps, setFps] = useState<number>(0)
  const [droppedFrames, setDroppedFrames] = useState<number>(0)
  const [latencyMs, setLatencyMs] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(
    isInitialUnsupported ? getCVUnsupportedExplanation(options.initialExerciseId) : null
  )

  const videoRef = useRef<HTMLVideoElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const wsClientRef = useRef<FormAnalysisWebSocket | null>(null)
  const offscreenCanvasRef = useRef<HTMLCanvasElement | null>(null)

  // Transport and loop refs (mutable for 25 FPS high frequency)
  const sequenceIdRef = useRef<number>(1)
  const isTransmittingRef = useRef<boolean>(false)
  const isFrameInFlightRef = useRef<boolean>(false)
  const lastFrameTimeRef = useRef<number>(0)
  const loopTimerRef = useRef<any>(null)
  const fpsFrameCountRef = useRef<number>(0)
  const fpsLastSampleTimeRef = useRef<number>(Date.now())
  const activeSessionIdRef = useRef<string | null>(null)

  // Helper to stop all camera tracks
  const stopCameraTracks = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => {
        try {
          track.stop()
        } catch {
          // Ignore track stop errors
        }
      })
      streamRef.current = null
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
  }, [])

  // Helper to stop frame loop
  const stopFrameLoop = useCallback(() => {
    isTransmittingRef.current = false
    if (loopTimerRef.current) {
      clearInterval(loopTimerRef.current)
      loopTimerRef.current = null
    }
  }, [])

  // Complete cleanup
  const cleanupAll = useCallback(() => {
    stopFrameLoop()
    stopCameraTracks()
    if (wsClientRef.current) {
      wsClientRef.current.disconnect()
      wsClientRef.current = null
    }
    activeSessionIdRef.current = null
    isFrameInFlightRef.current = false
  }, [stopFrameLoop, stopCameraTracks])

  // Step 1: Request Camera Permission & Start Preview
  const startCamera = useCallback(async () => {
    try {
      setStreamState('CAMERA_PERMISSION')
      setError(null)

      if (
        typeof navigator === 'undefined' ||
        !navigator.mediaDevices ||
        typeof navigator.mediaDevices.getUserMedia !== 'function'
      ) {
        cleanupAll()
        setStreamState('ERROR')
        setError('Browser camera API (getUserMedia) is not supported in this browser or environment.')
        return
      }

      // Only video, never audio
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: MAX_WIDTH },
          height: { ideal: MAX_HEIGHT },
          frameRate: { ideal: TARGET_FPS, max: TARGET_FPS },
          facingMode: 'user',
        },
        audio: false,
      })

      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }

      setStreamState('CAMERA_READY')
    } catch (err: any) {
      cleanupAll()
      setStreamState('ERROR')
      if (err?.name === 'NotAllowedError' || err?.name === 'PermissionDeniedError') {
        setError('Camera permission was denied. Please allow camera access in your browser to analyze form.')
      } else if (err?.name === 'NotFoundError' || err?.name === 'DevicesNotFoundError') {
        setError('No camera detected. Please connect a webcam.')
      } else if (err?.name === 'NotReadableError' || err?.name === 'TrackStartError') {
        setError('Camera hardware is currently unavailable or in use by another application.')
      } else {
        setError('Failed to start camera. ' + (err?.message || ''))
      }
    }
  }, [cleanupAll])

  // Frame Capture & Transmit Step (Executed at 25 FPS)
  const captureAndSendFrame = useCallback(async () => {
    if (!isTransmittingRef.current) return
    const video = videoRef.current
    const ws = wsClientRef.current
    const currentSessionId = activeSessionIdRef.current

    if (
      !video ||
      !ws ||
      !currentSessionId ||
      video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA ||
      ws.getStatus() !== 'CONNECTED'
    ) {
      return
    }

    // Enforce 25 FPS pacing
    const now = performance.now()
    if (now - lastFrameTimeRef.current < FRAME_INTERVAL_MS) {
      return
    }

    // Latest-frame-wins bounded backpressure:
    // If previous frame is still encoding/transmitting, drop this tick
    if (isFrameInFlightRef.current) {
      setDroppedFrames((prev) => prev + 1)
      return
    }

    isFrameInFlightRef.current = true
    lastFrameTimeRef.current = now

    try {
      if (!offscreenCanvasRef.current) {
        offscreenCanvasRef.current = document.createElement('canvas')
      }
      const canvas = offscreenCanvasRef.current

      // Scale to video dimensions within max bounds
      const vw = video.videoWidth || MAX_WIDTH
      const vh = video.videoHeight || MAX_HEIGHT
      const scale = Math.min(1, MAX_WIDTH / vw, MAX_HEIGHT / vh)
      const targetW = Math.round(vw * scale)
      const targetH = Math.round(vh * scale)

      if (canvas.width !== targetW || canvas.height !== targetH) {
        canvas.width = targetW
        canvas.height = targetH
      }

      const ctx = canvas.getContext('2d')
      if (!ctx) {
        isFrameInFlightRef.current = false
        return
      }

      ctx.drawImage(video, 0, 0, targetW, targetH)

      // Convert canvas to JPEG blob
      canvas.toBlob(
        async (blob) => {
          if (!blob || !isTransmittingRef.current) {
            isFrameInFlightRef.current = false
            return
          }

          try {
            const arrayBuffer = await blob.arrayBuffer()
            const seq = sequenceIdRef.current
            const captureTimestamp = Date.now()

            // Pack binary packet (32-byte header + JPEG payload)
            const packet = packFramePacket(currentSessionId, seq, captureTimestamp, arrayBuffer)

            const sent = ws.sendPacket(packet)
            if (sent) {
              // Increment sequence ID only when successfully transmitted
              sequenceIdRef.current = seq + 1
              fpsFrameCountRef.current++
            }

            // Update FPS telemetry every second
            const nowTime = Date.now()
            if (nowTime - fpsLastSampleTimeRef.current >= 1000) {
              setFps(fpsFrameCountRef.current)
              fpsFrameCountRef.current = 0
              fpsLastSampleTimeRef.current = nowTime
            }
          } catch {
            // Drop on packing error
          } finally {
            isFrameInFlightRef.current = false
          }
        },
        'image/jpeg',
        JPEG_QUALITY
      )
    } catch {
      isFrameInFlightRef.current = false
    }
  }, [])

  // Step 2: Start Analysis (Connects WebSocket & begins 25 FPS stream)
  const startAnalysis = useCallback(async () => {
    // Capability gate: verified CV support required
    const resolved = resolveCVExerciseId(exerciseId)
    if (!resolved) {
      cleanupAll()
      setStreamState('ERROR')
      setError(getCVUnsupportedExplanation(exerciseId))
      return
    }

    // If camera not started yet, start it first
    if (!streamRef.current) {
      await startCamera()
    }

    setStreamState('CONNECTING')
    setError(null)
    sequenceIdRef.current = 1
    fpsFrameCountRef.current = 0
    fpsLastSampleTimeRef.current = Date.now()
    setDroppedFrames(0)

    // Disconnect old socket if present
    if (wsClientRef.current) {
      wsClientRef.current.disconnect()
    }

    const ws = new FormAnalysisWebSocket({
      exerciseId,
      callbacks: {
        onStatusChange: (status) => {
          setConnectionStatus(status)
          if (status === 'CONNECTED') {
            setStreamState('ANALYZING')
            isTransmittingRef.current = true
            // Start 25 FPS loop
            if (!loopTimerRef.current) {
              loopTimerRef.current = setInterval(captureAndSendFrame, FRAME_INTERVAL_MS)
            }
          } else if (status === 'STOPPED') {
            setStreamState('STOPPED')
            stopFrameLoop()
          } else if (status === 'ERROR') {
            setStreamState('ERROR')
            stopFrameLoop()
          }
        },
        onAck: (ack) => {
          if (ack.session_id) {
            setSessionId(ack.session_id)
            activeSessionIdRef.current = ack.session_id
          }
        },
        onAnalysis: (analysis: WSAnalysisMessage) => {
          setRepCount(analysis.rep_count)
          setFsmState(analysis.fsm_state)
          setTrackingStatus(analysis.tracking_status)
          setObservabilityRatioSafe(analysis.observability_ratio)
          setLandmarks(analysis.landmarks || [])
          setJointAngles(analysis.joint_angles || {})
          setHeuristics(analysis.heuristics || [])
          if (analysis.feedback && analysis.feedback.length > 0) {
            setFeedback(analysis.feedback)
          }
          if (analysis.latest_score !== null && analysis.latest_score !== undefined) {
            setLatestScore(analysis.latest_score)
          }
          setScoreStatus(analysis.score_status || null)
          setLatencyMs(analysis.processing_ms || null)
        },
        onRepCompleted: (repMsg: WSRepCompletedMessage) => {
          const item: CompletedRepItem = {
            repNumber: repMsg.rep_number,
            outcome: repMsg.fsm_outcome,
            romDegrees: repMsg.rom_degrees,
            durationMs: repMsg.duration_ms,
            score: repMsg.score,
            scoreStatus: repMsg.score_status,
            feedback: repMsg.feedback || [],
          }
          setCompletedReps((prev) => [...prev, item])
          setRepCount(repMsg.rep_number)
          if (repMsg.score !== null && repMsg.score !== undefined) {
            setLatestScore(repMsg.score)
          }
          setScoreStatus(repMsg.score_status)
          options.onRepCompleted?.(item)
        },
        onError: (err: WSErrorMessage) => {
          setError(err.error || 'Stream error occurred.')
          options.onError?.(err)
        },
        onStopped: (msg: WSStoppedMessage) => {
          options.onStopped?.(msg)
        },
      },
    })

    wsClientRef.current = ws
    await ws.connect()
  }, [exerciseId, startCamera, captureAndSendFrame, stopFrameLoop, options])

  // Helper for safe ratio
  const setObservabilityRatioSafe = (_ratio: number) => {
    // Kept in analysis state
  }

  // Step 3: Pause
  const pauseAnalysis = useCallback(() => {
    isTransmittingRef.current = false
    setStreamState('PAUSED')
    wsClientRef.current?.pause(sequenceIdRef.current)
  }, [])

  // Step 4: Resume
  const resumeAnalysis = useCallback(() => {
    isTransmittingRef.current = true
    setStreamState('ANALYZING')
    wsClientRef.current?.resume(sequenceIdRef.current)
  }, [])

  // Step 5: Stop Analysis (clean release of hardware and transport)
  const stopAnalysis = useCallback(() => {
    wsClientRef.current?.stop()
    cleanupAll()
    setStreamState('STOPPED')
  }, [cleanupAll])

  // Step 6: Select Exercise (strictly gated by verified CV capability)
  const selectExercise = useCallback(
    (newExerciseId: string) => {
      const resolved = resolveCVExerciseId(newExerciseId)
      if (!resolved) {
        if (streamState === 'ANALYZING' || streamState === 'PAUSED') {
          stopAnalysis()
        }
        setError(getCVUnsupportedExplanation(newExerciseId))
        setStreamState('ERROR')
        return
      }

      if (resolved === exerciseId && streamState !== 'ERROR') return
      if (streamState === 'ANALYZING' || streamState === 'PAUSED') {
        stopAnalysis()
      }
      setExerciseId(resolved)
      setRepCount(0)
      setLatestScore(null)
      setScoreStatus(null)
      setCompletedReps([])
      setLandmarks([])
      setJointAngles({})
      setHeuristics([])
      setFeedback([])
      setError(null)
      setStreamState('INITIAL')
    },
    [exerciseId, streamState, stopAnalysis]
  )

  // Ensure hardware and transport are released on component unmount
  useEffect(() => {
    return () => {
      cleanupAll()
    }
  }, [cleanupAll])

  return {
    videoRef,
    streamState,
    connectionStatus,
    exerciseId,
    sessionId,
    repCount,
    fsmState,
    trackingStatus,
    latestScore,
    scoreStatus,
    landmarks,
    jointAngles,
    heuristics,
    feedback,
    completedReps,
    fps,
    droppedFrames,
    latencyMs,
    error,
    startCamera,
    startAnalysis,
    pauseAnalysis,
    resumeAnalysis,
    stopAnalysis,
    selectExercise,
  }
}
