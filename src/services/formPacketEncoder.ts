/**
 * Binary Frame Packet Encoder & Decoder for Phase 9B.5/9B.6 Real-Time Form Analysis.
 *
 * Wire Protocol (Fixed 32-byte Header):
 *   [0..15]   UUID session_id (16 raw bytes)
 *   [16..23]  uint64 sequence_id (8 bytes, big-endian)
 *   [24..31]  uint64 timestamp_ms (8 bytes, big-endian)
 *   [32..End] Encoded image payload (JPEG / WebP / PNG)
 *
 * Struct equivalent: >16sQQ
 */

export const HEADER_SIZE_BYTES = 32
export const MAX_FRAME_PAYLOAD_BYTES = 5 * 1024 * 1024 // 5 MB

export class PacketEncodingError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'PacketEncodingError'
  }
}

/**
 * Converts a standard UUID string (with or without hyphens) into 16 raw binary bytes.
 */
export function uuidToBytes(uuidStr: string): Uint8Array {
  if (typeof uuidStr !== 'string') {
    throw new PacketEncodingError('UUID must be a string')
  }
  const clean = uuidStr.replace(/-/g, '').toLowerCase()
  if (clean.length !== 32 || !/^[0-9a-f]{32}$/.test(clean)) {
    throw new PacketEncodingError(`Invalid UUID format: "${uuidStr}". Expected 32 hex characters.`)
  }

  const bytes = new Uint8Array(16)
  for (let i = 0; i < 16; i++) {
    bytes[i] = parseInt(clean.substring(i * 2, i * 2 + 2), 16)
  }
  return bytes
}

/**
 * Converts 16 raw binary bytes into a canonical lowercase UUID string with hyphens.
 */
export function bytesToUuid(bytes: Uint8Array): string {
  if (!(bytes instanceof Uint8Array) || bytes.length < 16) {
    throw new PacketEncodingError('Expected at least 16 bytes for UUID conversion')
  }

  let hex = ''
  for (let i = 0; i < 16; i++) {
    const b = bytes[i].toString(16).padStart(2, '0')
    hex += b
  }

  return `${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20, 32)}`
}

export interface UnpackedHeader {
  sessionId: string
  sequenceId: number
  timestampMs: number
  payload: Uint8Array
}

/**
 * Packs a frame into the approved binary packet format with a 32-byte header.
 *
 * @param sessionId - Canonical session UUID string
 * @param sequenceId - Monotonically increasing non-negative integer
 * @param timestampMs - Client capture timestamp in milliseconds
 * @param imageBytes - Encoded image payload (ArrayBuffer or Uint8Array)
 * @returns Complete binary packet buffer
 */
export function packFramePacket(
  sessionId: string,
  sequenceId: number,
  timestampMs: number,
  imageBytes: ArrayBuffer | Uint8Array
): Uint8Array {
  // 1. Validate session UUID
  const sessionBytes = uuidToBytes(sessionId)

  // 2. Validate sequence ID
  if (
    typeof sequenceId !== 'number' ||
    !Number.isFinite(sequenceId) ||
    sequenceId < 0 ||
    !Number.isInteger(sequenceId)
  ) {
    throw new PacketEncodingError(`Invalid sequenceId: ${sequenceId}. Must be a non-negative integer.`)
  }

  // 3. Validate timestamp
  if (
    typeof timestampMs !== 'number' ||
    !Number.isFinite(timestampMs) ||
    timestampMs < 0
  ) {
    throw new PacketEncodingError(`Invalid timestampMs: ${timestampMs}. Must be a non-negative number.`)
  }

  // 4. Validate payload size
  const payloadArray = imageBytes instanceof Uint8Array ? imageBytes : new Uint8Array(imageBytes)
  if (payloadArray.byteLength > MAX_FRAME_PAYLOAD_BYTES) {
    throw new PacketEncodingError(
      `Payload size (${payloadArray.byteLength} bytes) exceeds maximum allowable limit of ${MAX_FRAME_PAYLOAD_BYTES} bytes (5 MB).`
    )
  }

  // 5. Construct 32-byte header
  const headerBuffer = new Uint8Array(HEADER_SIZE_BYTES)
  headerBuffer.set(sessionBytes, 0)

  const view = new DataView(headerBuffer.buffer, headerBuffer.byteOffset, headerBuffer.byteLength)
  // uint64 big-endian sequence_id at offset 16
  view.setBigUint64(16, BigInt(sequenceId), false)
  // uint64 big-endian timestamp_ms at offset 24
  view.setBigUint64(24, BigInt(Math.round(timestampMs)), false)

  // 6. Assemble complete packet
  const packet = new Uint8Array(HEADER_SIZE_BYTES + payloadArray.byteLength)
  packet.set(headerBuffer, 0)
  packet.set(payloadArray, HEADER_SIZE_BYTES)

  return packet
}

/**
 * Unpacks the 32-byte header from a binary frame packet.
 *
 * @param packet - Complete binary packet
 * @returns Unpacked metadata and image payload
 */
export function unpackFrameHeader(packet: ArrayBuffer | Uint8Array): UnpackedHeader {
  const packetBytes = packet instanceof Uint8Array ? packet : new Uint8Array(packet)
  if (packetBytes.byteLength < HEADER_SIZE_BYTES) {
    throw new PacketEncodingError(
      `Packet size (${packetBytes.byteLength} bytes) is smaller than the required 32-byte header.`
    )
  }

  const sessionBytes = packetBytes.subarray(0, 16)
  const sessionId = bytesToUuid(sessionBytes)

  const view = new DataView(packetBytes.buffer, packetBytes.byteOffset, packetBytes.byteLength)
  const sequenceId = Number(view.getBigUint64(16, false))
  const timestampMs = Number(view.getBigUint64(24, false))

  const payload = packetBytes.subarray(HEADER_SIZE_BYTES)

  return {
    sessionId,
    sequenceId,
    timestampMs,
    payload,
  }
}
