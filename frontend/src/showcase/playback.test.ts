import { describe, expect, it } from 'vitest'
import { canPlayAudioResponse, initialShowcaseState, showcaseReducer } from './playback'

const total = 6

describe('showcaseReducer', () => {
  it('starts at the first line', () => {
    const next = showcaseReducer(initialShowcaseState, { type: 'start' }, total)
    expect(next).toEqual({ phase: 'story', turnIndex: 0 })
  })

  it('advances one line at a time and opens questions after the last', () => {
    let state = showcaseReducer(initialShowcaseState, { type: 'start' }, total)
    for (let i = 0; i < total - 1; i++) {
      state = showcaseReducer(state, { type: 'segment-finished' }, total)
      expect(state).toEqual({ phase: 'story', turnIndex: i + 1 })
    }
    state = showcaseReducer(state, { type: 'segment-finished' }, total)
    expect(state).toEqual({ phase: 'qa', turnIndex: total - 1 })
  })

  it('skips to questions only after the show has started', () => {
    expect(showcaseReducer(initialShowcaseState, { type: 'skip-to-qa' }, total)).toEqual(
      initialShowcaseState,
    )
    const started = showcaseReducer(initialShowcaseState, { type: 'start' }, total)
    const skipped = showcaseReducer(started, { type: 'skip-to-qa' }, total)
    expect(skipped.phase).toBe('qa')
  })

  it('treats the SPA html fallback as missing audio', () => {
    expect(canPlayAudioResponse(true, 'text/html')).toBe(false)
    expect(canPlayAudioResponse(false, 'audio/mpeg')).toBe(false)
    expect(canPlayAudioResponse(true, 'audio/mpeg')).toBe(true)
  })

  it('restarts to the idle stage', () => {
    const started = showcaseReducer(initialShowcaseState, { type: 'start' }, total)
    expect(showcaseReducer(started, { type: 'restart' }, total)).toEqual(initialShowcaseState)
  })
})
