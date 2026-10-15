export type ShowcasePhase = 'idle' | 'story' | 'qa'

export interface ShowcaseState {
  phase: ShowcasePhase
  /** 当前这句的下标。闲置时为 -1。 */
  turnIndex: number
}

export type ShowcaseEvent =
  | { type: 'start' }
  | { type: 'segment-finished' }
  | { type: 'skip-to-qa' }
  | { type: 'restart' }

export const initialShowcaseState: ShowcaseState = { phase: 'idle', turnIndex: -1 }

/** 讲解者回答里的 mp3。空字符串或不是 mp3 时不播放。 */
export function mp3BytesFromBase64(encoded: string): Uint8Array | null {
  const trimmed = encoded.trim()
  if (!trimmed) return null
  try {
    const binary = atob(trimmed)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i)
    const header = String.fromCharCode(bytes[0] ?? 0, bytes[1] ?? 0, bytes[2] ?? 0)
    if (header !== 'ID3') return null
    return bytes
  } catch {
    return null
  }
}

/** Vite 对缺失的 mp3 会回 200 的 index.html，不能交给 audio 元素。 */
export function canPlayAudioResponse(ok: boolean, contentType: string | null): boolean {
  return ok && (contentType ?? '').toLowerCase().startsWith('audio/')
}

export function showcaseReducer(
  state: ShowcaseState,
  event: ShowcaseEvent,
  totalTurns: number,
): ShowcaseState {
  switch (event.type) {
    case 'start':
      return { phase: 'story', turnIndex: 0 }
    case 'segment-finished':
      if (state.phase !== 'story') return state
      if (state.turnIndex >= totalTurns - 1) return { phase: 'qa', turnIndex: totalTurns - 1 }
      return { phase: 'story', turnIndex: state.turnIndex + 1 }
    case 'skip-to-qa':
      if (state.phase === 'idle') return state
      return { phase: 'qa', turnIndex: Math.max(state.turnIndex, 0) }
    case 'restart':
      return initialShowcaseState
    default:
      return state
  }
}
