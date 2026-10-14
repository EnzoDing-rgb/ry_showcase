import { useCallback, useEffect, useRef, useState } from 'react'
import './App.css'
import './Showcase.css'
import { RoleCard } from './components/RoleCard'
import lexFace from './assets/faces/lex.png'
import wuweiFace from './assets/faces/wuwei.png'
import {
  canPlayAudioResponse,
  initialShowcaseState,
  showcaseReducer,
  type ShowcaseState,
} from './showcase/playback'

type SpeakerId = 'developer' | 'guide'

interface StoryTurn {
  index: number
  speaker: SpeakerId
  text: string
  audio: string
}

interface StoryPayload {
  title: string
  subtitle: string
  turns: StoryTurn[]
}

interface QaItem {
  question: string
  reply: string
}

const CAST = {
  developer: {
    name: '开发者',
    school: '手里有一块新板子',
    avatarSrc: wuweiFace,
    accent: '#0f766e',
  },
  guide: {
    name: '讲解者',
    school: '如意 SDK',
    avatarSrc: lexFace,
    accent: '#1d4ed8',
  },
} as const

function App() {
  const [story, setStory] = useState<StoryPayload | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [stage, setStage] = useState<ShowcaseState>(initialShowcaseState)
  const [audioMissing, setAudioMissing] = useState(false)
  const [draft, setDraft] = useState('')
  const [qa, setQa] = useState<QaItem[]>([])
  const [asking, setAsking] = useState(false)
  const [askError, setAskError] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement>(null)
  const total = story?.turns.length ?? 0

  useEffect(() => {
    let cancelled = false
    fetch('/api/showcase/script')
      .then(async (res) => {
        if (!res.ok) throw new Error(`脚本接口 ${res.status}`)
        return res.json() as Promise<StoryPayload>
      })
      .then((payload) => {
        if (!cancelled) setStory(payload)
      })
      .catch((err: unknown) => {
        if (!cancelled) setLoadError(err instanceof Error ? err.message : '无法读取故事')
      })
    return () => {
      cancelled = true
    }
  }, [])

  const dispatch = useCallback(
    (event: Parameters<typeof showcaseReducer>[1]) => {
      if (!total) return
      setStage((current) => showcaseReducer(current, event, total))
    },
    [total],
  )

  useEffect(() => {
    if (stage.phase !== 'story' || !story) return
    const turn = story.turns[stage.turnIndex]
    const el = audioRef.current
    if (!turn || !el) return
    let cancelled = false
    setAudioMissing(false)
    const onEnded = () => dispatch({ type: 'segment-finished' })
    const onError = () => setAudioMissing(true)

    void (async () => {
      try {
        const probe = await fetch(turn.audio, { method: 'HEAD' })
        if (cancelled) return
        if (!canPlayAudioResponse(probe.ok, probe.headers.get('content-type'))) {
          setAudioMissing(true)
          return
        }
      } catch {
        if (!cancelled) setAudioMissing(true)
        return
      }
      if (cancelled) return
      el.src = turn.audio
      el.addEventListener('ended', onEnded)
      el.addEventListener('error', onError)
      void el.play().catch(() => setAudioMissing(true))
    })()

    return () => {
      cancelled = true
      el.pause()
      el.removeEventListener('ended', onEnded)
      el.removeEventListener('error', onError)
    }
  }, [dispatch, stage.phase, stage.turnIndex, story])

  const restart = () => {
    audioRef.current?.pause()
    setQa([])
    setDraft('')
    setAskError(null)
    setAudioMissing(false)
    setStage(initialShowcaseState)
  }

  const submitQuestion = async () => {
    const message = draft.trim()
    if (!message || asking) return
    setAsking(true)
    setAskError(null)
    try {
      const res = await fetch('/api/showcase/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
      })
      if (!res.ok) throw new Error(`提问接口 ${res.status}`)
      const body = (await res.json()) as { reply: string }
      setQa((items) => [...items, { question: message, reply: body.reply }])
      setDraft('')
    } catch (err: unknown) {
      setAskError(err instanceof Error ? err.message : '提问失败')
    } finally {
      setAsking(false)
    }
  }

  const revealed =
    story && stage.phase !== 'idle' ? story.turns.slice(0, stage.turnIndex + 1) : []

  return (
    <div className="app-root">
      <div className="app-container showcase">
        <header className="app-header">
          <h1>{story?.title ?? '如意 SDK'}</h1>
          <p className="topic">{story?.subtitle ?? '同一套工具，许多块 RISC-V 开发板'}</p>
        </header>

        <div className="showcase-cast">
          <RoleCard {...CAST.developer} isLeft />
          <RoleCard {...CAST.guide} isLeft={false} />
        </div>

        {loadError && <p className="showcase-note">{loadError}</p>}

        <div className="showcase-log" aria-live="polite">
          {revealed.map((turn) => {
            const person = CAST[turn.speaker]
            const active = stage.phase === 'story' && turn.index - 1 === stage.turnIndex
            return (
              <article
                key={turn.index}
                className={`showcase-line${active ? ' is-active' : ''}${turn.speaker === 'guide' ? ' is-guide' : ''}`}
              >
                <img src={person.avatarSrc} alt="" />
                <div>
                  <div className="showcase-who">{person.name}</div>
                  <p>{turn.text}</p>
                </div>
              </article>
            )
          })}
        </div>

        <audio ref={audioRef} preload="none" />

        <div className="controls-container">
          {stage.phase === 'idle' && (
            <button className="start-button" type="button" disabled={!story} onClick={() => dispatch({ type: 'start' })}>
              开始演示
            </button>
          )}
          {stage.phase === 'story' && audioMissing && (
            <button className="start-button" type="button" onClick={() => dispatch({ type: 'segment-finished' })}>
              语音还没合成，继续下一段
            </button>
          )}
          {stage.phase === 'story' && (
            <button className="download-button" type="button" onClick={() => dispatch({ type: 'skip-to-qa' })}>
              跳到提问
            </button>
          )}
          {stage.phase !== 'idle' && (
            <button className="download-button" type="button" onClick={restart}>
              重开这场
            </button>
          )}
        </div>

        {stage.phase === 'qa' && (
          <section className="showcase-qa">
            <h2>现场提问</h2>
            <p className="showcase-note">问题交给讲解者。模型额度还没到位，现在只会返回本地说明，不会请求大模型。</p>
            <div className="showcase-qa-row">
              <input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') void submitQuestion()
                }}
                placeholder="问问如意怎么对待不同的板子"
                aria-label="观众提问"
              />
              <button className="start-button" type="button" disabled={asking || !draft.trim()} onClick={() => void submitQuestion()}>
                发送
              </button>
            </div>
            {askError && <p className="showcase-note">{askError}</p>}
            {qa.map((item, i) => (
              <div key={i} className="showcase-qa-item">
                <p className="showcase-q">观众：{item.question}</p>
                <p className="showcase-a">讲解者：{item.reply}</p>
              </div>
            ))}
          </section>
        )}
      </div>
    </div>
  )
}

export default App
