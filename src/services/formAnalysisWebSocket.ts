/**
 * WebSocket Streaming Client for Real-Time Form Analysis (Phase 9B.6).
 * Connects browser clients to Phase 9B.5 backend streaming endpoint.
 */

import { getIdToken } from '../lib/firebase.ts'
import type {
  SupportedExerciseId,
  ConnectionStatus,
  WSServerMessage,
  WSAckMessage,
  WSAnalysisMessage,
  WSRepCompletedMessage,
  WSErrorMessage,
  WSPongMessage,
  WSStoppedMessage,
  WSClientControlMessage,
} from '../types/formStream.ts'

export interface FormAnalysisWebSocketCallbacks {
  onAck?: (msg: WSAckMessage) => void
  onAnalysis?: (msg: WSAnalysisMessage) => void
  onRepCompleted?: (msg: WSRepCompletedMessage) => void
  onError?: (msg: WSErrorMessage) => void
  onPong?: (msg: WSPongMessage) => void
  onStopped?: (msg: WSStoppedMessage) => void
  onStatusChange?: (status: ConnectionStatus) => void
}

export interface FormAnalysisWebSocketConfig {
  exerciseId: SupportedExerciseId
  sessionId?: string | null
  tokenProvider?: () => Promise<string | null>
  maxReconnectAttempts?: number
  heartbeatIntervalMs?: number
  callbacks?: FormAnalysisWebSocketCallbacks
}

export class FormAnalysisWebSocket {
  private ws: WebSocket | null = null
  private exerciseId: SupportedExerciseId
  private sessionId: string | null = null
  private tokenProvider?: () => Promise<string | null>
  private status: ConnectionStatus = 'DISCONNECTED'
  private callbacks: FormAnalysisWebSocketCallbacks = {}
  private maxReconnectAttempts: number
  private reconnectAttempts = 0
  private reconnectTimeoutId: any = null
  private heartbeatIntervalMs: number
  private heartbeatTimerId: any = null
  private isIntentionallyClosed = false
  private lastCompletedRepEmitted = -1

  constructor(config: FormAnalysisWebSocketConfig) {
    this.exerciseId = config.exerciseId
    this.sessionId = config.sessionId || null
    this.tokenProvider = config.tokenProvider
    this.maxReconnectAttempts = config.maxReconnectAttempts ?? 3
    this.heartbeatIntervalMs = config.heartbeatIntervalMs ?? 15000
    if (config.callbacks) {
      this.callbacks = config.callbacks
    }
  }

  public getStatus(): ConnectionStatus {
    return this.status
  }

  public getSessionId(): string | null {
    return this.sessionId
  }

  public setCallbacks(callbacks: FormAnalysisWebSocketCallbacks): void {
    this.callbacks = { ...this.callbacks, ...callbacks }
  }

  private setStatus(status: ConnectionStatus): void {
    if (this.status !== status) {
      this.status = status
      this.callbacks.onStatusChange?.(status)
    }
  }

  /**
   * Constructs the authenticated WebSocket URL.
   */
  public static buildWebSocketUrl(
    exerciseId: string,
    token: string,
    sessionId?: string | null
  ): string {
    const explicitWs = typeof import.meta !== 'undefined' ? import.meta.env?.VITE_WS_URL : null
    let baseWs: string

    if (explicitWs) {
      baseWs = explicitWs.replace(/\/$/, '')
    } else {
      const apiBase = (typeof import.meta !== 'undefined' ? import.meta.env?.VITE_API_BASE_URL : null) || 'http://localhost:8000/api/v1'
      baseWs = apiBase.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:').replace(/\/$/, '')
    }

    const endpoint = `${baseWs}/form-analysis/ws`
    const params = new URLSearchParams()
    params.set('token', token)
    params.set('exercise_id', exerciseId)
    if (sessionId) {
      params.set('session_id', sessionId)
    }

    return `${endpoint}?${params.toString()}`
  }

  /**
   * Connects to the backend WebSocket stream using Firebase auth token.
   */
  public async connect(): Promise<void> {
    // Prevent duplicate sockets
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      this.disconnect()
    }

    this.isIntentionallyClosed = false
    this.setStatus('CONNECTING')

    try {
      const token = this.tokenProvider ? await this.tokenProvider() : await getIdToken()
      if (!token) {
        throw new Error('Authentication required. Could not retrieve Firebase ID token.')
      }

      const wsUrl = FormAnalysisWebSocket.buildWebSocketUrl(this.exerciseId, token, this.sessionId)
      this.ws = new WebSocket(wsUrl)
      this.ws.binaryType = 'arraybuffer'

      this.ws.onopen = this.handleOpen.bind(this)
      this.ws.onmessage = this.handleMessage.bind(this)
      this.ws.onerror = this.handleError.bind(this)
      this.ws.onclose = this.handleClose.bind(this)
    } catch (err: any) {
      this.setStatus('ERROR')
      this.callbacks.onError?.({
        type: 'error',
        code: 'AUTH_FAILURE',
        error: 'Failed to authenticate WebSocket connection.',
        detail: err?.message || 'Authentication error',
      })
    }
  }

  private handleOpen(): void {
    this.reconnectAttempts = 0
    this.setStatus('CONNECTED')
    this.startHeartbeat()
  }

  private handleMessage(event: MessageEvent): void {
    if (typeof event.data !== 'string') {
      // Binary messages from server are not expected in Phase 9B.5 (server sends JSON telemetry)
      return
    }

    try {
      const data: WSServerMessage = JSON.parse(event.data)

      switch (data.type) {
        case 'ack':
          if (data.session_id && !this.sessionId) {
            this.sessionId = data.session_id
          }
          this.callbacks.onAck?.(data)
          break

        case 'analysis':
          if (data.session_id && !this.sessionId) {
            this.sessionId = data.session_id
          }
          this.callbacks.onAnalysis?.(data)
          break

        case 'rep_completed':
          // Protect against duplicate rep completed events
          if (data.rep_number > this.lastCompletedRepEmitted) {
            this.lastCompletedRepEmitted = data.rep_number
            this.callbacks.onRepCompleted?.(data)
          }
          break

        case 'error':
          this.callbacks.onError?.(data)
          break

        case 'pong':
          this.callbacks.onPong?.(data)
          break

        case 'stopped':
          this.setStatus('STOPPED')
          this.callbacks.onStopped?.(data)
          break

        default:
          break
      }
    } catch {
      this.callbacks.onError?.({
        type: 'error',
        code: 'MALFORMED_SERVER_MESSAGE',
        error: 'Received non-JSON message from server.',
      })
    }
  }

  private handleError(): void {
    if (this.status !== 'STOPPED' && !this.isIntentionallyClosed) {
      this.callbacks.onError?.({
        type: 'error',
        code: 'WEBSOCKET_ERROR',
        error: 'WebSocket encountered a transport error.',
      })
    }
  }

  private handleClose(event: CloseEvent): void {
    this.stopHeartbeat()

    if (this.isIntentionallyClosed || event.code === 1000) {
      this.setStatus('STOPPED')
      return
    }

    // Auth failure (1008 Policy Violation) or client limit reached: do NOT retry
    if (event.code === 1008) {
      this.setStatus('ERROR')
      this.callbacks.onError?.({
        type: 'error',
        code: 'AUTH_REJECTED',
        error: 'Connection rejected by server authentication policy.',
      })
      return
    }

    // Bounded reconnect for unexpected dropouts
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      this.setStatus('RECONNECTING')
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), 5000)
      this.reconnectTimeoutId = setTimeout(() => {
        this.connect()
      }, delay)
    } else {
      this.setStatus('DISCONNECTED')
    }
  }

  /**
   * Sends an encoded 32-byte binary frame packet to the backend.
   */
  public sendPacket(packet: Uint8Array): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return false
    }
    try {
      this.ws.send(packet as unknown as BufferSource)
      return true
    } catch {
      return false
    }
  }

  /**
   * Sends a structured JSON control message to the backend.
   */
  public sendControl(control: WSClientControlMessage): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return false
    }
    try {
      this.ws.send(JSON.stringify(control))
      return true
    } catch {
      return false
    }
  }

  public pause(sequenceId?: number): boolean {
    return this.sendControl({ type: 'pause', sequence_id: sequenceId })
  }

  public resume(sequenceId?: number): boolean {
    return this.sendControl({ type: 'resume', sequence_id: sequenceId })
  }

  public stop(): boolean {
    const res = this.sendControl({ type: 'stop' })
    this.isIntentionallyClosed = true
    this.setStatus('STOPPED')
    return res
  }

  public ping(sequenceId?: number): boolean {
    return this.sendControl({ type: 'ping', sequence_id: sequenceId, timestamp_ms: Date.now() })
  }

  private startHeartbeat(): void {
    this.stopHeartbeat()
    this.heartbeatTimerId = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ping()
      }
    }, this.heartbeatIntervalMs)
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimerId) {
      clearInterval(this.heartbeatTimerId)
      this.heartbeatTimerId = null
    }
  }

  /**
   * Closes the connection and releases all timers and event listeners.
   */
  public disconnect(): void {
    this.isIntentionallyClosed = true
    this.stopHeartbeat()

    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId)
      this.reconnectTimeoutId = null
    }

    if (this.ws) {
      this.ws.onopen = null
      this.ws.onmessage = null
      this.ws.onerror = null
      this.ws.onclose = null

      if (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING) {
        try {
          this.ws.close(1000, 'Normal closure')
        } catch {
          // Ignore close errors during disconnect
        }
      }
      this.ws = null
    }

    this.setStatus('DISCONNECTED')
  }
}
