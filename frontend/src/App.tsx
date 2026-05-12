import { useState, useEffect, useRef, useCallback } from 'react'
import './App.css'

interface Violation {
  id: string
  person: string
  word: string
  amount: string
  timestamp: string
}

interface Offender {
  person: string
  total: number
  count: number
}

interface Stats {
  total: number
  count: number
  offenders: Offender[]
}

function GlitchText({ text }: { text: string }) {
  return (
    <span className="glitch" data-text={text}>
      {text}
    </span>
  )
}

function AnimatedCounter({ value, decimals = 0 }: { value: number; decimals?: number }) {
  const [displayed, setDisplayed] = useState(0)
  const prev = useRef(0)

  useEffect(() => {
    const start = prev.current
    const end = value
    const duration = 900
    const startTime = performance.now()
    const animate = (now: number) => {
      const p = Math.min((now - startTime) / duration, 1)
      const eased = 1 - Math.pow(1 - p, 4)
      const current = start + (end - start) * eased
      setDisplayed(current)
      if (p < 1) requestAnimationFrame(animate)
      else prev.current = end
    }
    requestAnimationFrame(animate)
  }, [value])

  return <>{displayed.toFixed(decimals)}</>
}

function ParticleCanvas() {
  const ref = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')!

    const resize = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
    }
    resize()
    window.addEventListener('resize', resize)

    type Particle = { x: number; y: number; vx: number; vy: number; size: number; color: string; alpha: number }
    const COLORS = ['#7c3aed', '#06b6d4', '#10b981', '#a855f7', '#f43f5e']
    const particles: Particle[] = Array.from({ length: 90 }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.25,
      vy: (Math.random() - 0.5) * 0.25,
      size: Math.random() * 1.8 + 0.3,
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
      alpha: Math.random() * 0.5 + 0.1,
    }))

    let raf: number
    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i]
        p.x = (p.x + p.vx + canvas.width) % canvas.width
        p.y = (p.y + p.vy + canvas.height) % canvas.height

        ctx.beginPath()
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
        ctx.fillStyle = p.color
        ctx.globalAlpha = p.alpha
        ctx.fill()

        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j]
          const dx = p.x - p2.x
          const dy = p.y - p2.y
          const d = Math.sqrt(dx * dx + dy * dy)
          if (d < 110) {
            ctx.beginPath()
            ctx.moveTo(p.x, p.y)
            ctx.lineTo(p2.x, p2.y)
            ctx.strokeStyle = '#7c3aed'
            ctx.globalAlpha = 0.08 * (1 - d / 110)
            ctx.lineWidth = 0.6
            ctx.stroke()
          }
        }
      }
      ctx.globalAlpha = 1
      raf = requestAnimationFrame(draw)
    }
    draw()

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', resize)
    }
  }, [])

  return <canvas ref={ref} className="particle-canvas" />
}

function Clock() {
  const [time, setTime] = useState(() => new Date().toLocaleTimeString('fr-FR'))
  useEffect(() => {
    const id = setInterval(() => setTime(new Date().toLocaleTimeString('fr-FR')), 1000)
    return () => clearInterval(id)
  }, [])
  return <span className="clock">{time}</span>
}

export default function App() {
  const [violations, setViolations] = useState<Violation[]>([])
  const [stats, setStats] = useState<Stats>({ total: 0, count: 0, offenders: [] })
  const [showModal, setShowModal] = useState(false)
  const [person, setPerson] = useState('')
  const [word, setWord] = useState('')
  const [amount, setAmount] = useState('1')
  const [loading, setLoading] = useState(false)
  const [flash, setFlash] = useState(false)
  const [newIds, setNewIds] = useState<Set<string>>(new Set())

  const fetchData = useCallback(async () => {
    try {
      const [vRes, sRes] = await Promise.all([fetch('/api/violations'), fetch('/api/stats')])
      const [vData, sData] = await Promise.all([vRes.json(), sRes.json()])
      setViolations(vData)
      setStats(sData)
    } catch {
      // silent — app still works offline
    }
  }, [])

  useEffect(() => {
    fetchData()
    const id = setInterval(fetchData, 5000)
    return () => clearInterval(id)
  }, [fetchData])

  const handleSubmit = async () => {
    if (!person.trim()) return
    setLoading(true)
    try {
      const res = await fetch('/api/violations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ person: person.trim(), word: word.trim() || '---', amount: parseFloat(amount) || 1 }),
      })
      const created = await res.json()
      await fetchData()
      setNewIds(s => new Set([...s, created.id]))
      setTimeout(() => setNewIds(s => { const n = new Set(s); n.delete(created.id); return n }), 2000)
      setFlash(true)
      setTimeout(() => setFlash(false), 600)
      setPerson('')
      setWord('')
      setAmount('1')
      setShowModal(false)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: string) => {
    await fetch(`/api/violations/${id}`, { method: 'DELETE' })
    await fetchData()
  }

  const topOffender = stats.offenders[0]

  return (
    <div className={`app${flash ? ' flash' : ''}`}>
      <ParticleCanvas />
      <div className="scanlines" />
      <div className="grid-bg" />

      <header className="header">
        <div className="header-top">
          <div className="header-badge">◈ SYSTÈME DE SURVEILLANCE VERBALE ◈</div>
          <Clock />
        </div>
        <h1 className="title">
          <GlitchText text="ZERO MOT" />
        </h1>
        <p className="subtitle">PROTOCOLE DE RÉGULATION VERBALE // BUREAU v2.0 // AMENDE : 1€/INFRACTION</p>
        <div className="header-line" />
      </header>

      <section className="hero">
        <div className="cagnotte-frame">
          <div className="cagnotte-corner tl" />
          <div className="cagnotte-corner tr" />
          <div className="cagnotte-corner bl" />
          <div className="cagnotte-corner br" />
          <div className="cagnotte-label">◤ CAGNOTTE TOTALE ◢</div>
          <div className="cagnotte-value">
            <AnimatedCounter value={stats.total} decimals={2} />
            <span className="cagnotte-unit"> €</span>
          </div>
          <div className="cagnotte-sub">
            <span className="stat-chip">
              <span className="stat-chip-dot cyan" />
              {stats.count} INFRACTIONS
            </span>
            {topOffender && (
              <span className="stat-chip">
                <span className="stat-chip-dot pink" />
                {topOffender.person.toUpperCase()} EN TÊTE
              </span>
            )}
          </div>
        </div>

        <button className="add-btn" onClick={() => setShowModal(true)}>
          <span className="add-btn-inner">
            <span className="add-btn-icon">⚠</span>
            DÉCLARER UNE INFRACTION
          </span>
          <span className="add-btn-scan" />
        </button>
      </section>

      <div className="grid-content">
        <section className="panel">
          <div className="panel-header">
            <span className="panel-indicator cyan" />
            <span>TOP CONTREVENANTS</span>
            <span className="panel-count">{stats.offenders.length}</span>
          </div>
          {stats.offenders.length === 0 ? (
            <div className="empty-state">
              <span className="empty-icon">◉</span>
              <span>AUCUNE INFRACTION DÉTECTÉE</span>
            </div>
          ) : (
            <div className="leaderboard">
              {stats.offenders.map((o, i) => (
                <div key={o.person} className="lb-row" style={{ '--i': i } as React.CSSProperties}>
                  <span className="lb-rank" data-rank={i}>{i === 0 ? '▲' : i === 1 ? '◆' : i === 2 ? '▼' : `#${i + 1}`}</span>
                  <span className="lb-name">{o.person.toUpperCase()}</span>
                  <div className="lb-bar-wrap">
                    <div
                      className="lb-bar"
                      style={{ width: `${(o.total / stats.offenders[0].total) * 100}%` }}
                    />
                  </div>
                  <span className="lb-amount">{o.total.toFixed(2)}€</span>
                  <span className="lb-badge">×{o.count}</span>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="panel">
          <div className="panel-header">
            <span className="panel-indicator pink" />
            <span>JOURNAL DES INFRACTIONS</span>
            <span className="panel-count">{violations.length}</span>
          </div>
          {violations.length === 0 ? (
            <div className="empty-state">
              <span className="empty-icon">◎</span>
              <span>AUCUNE ENTRÉE ENREGISTRÉE</span>
            </div>
          ) : (
            <div className="feed">
              {[...violations].reverse().map((v, i) => (
                <div
                  key={v.id}
                  className={`feed-item${newIds.has(v.id) ? ' feed-item--new' : ''}`}
                  style={{ '--i': i } as React.CSSProperties}
                >
                  <div className="feed-row-top">
                    <span className="feed-person">{v.person.toUpperCase()}</span>
                    <span className="feed-amount">+{parseFloat(v.amount).toFixed(2)}€</span>
                  </div>
                  <div className="feed-row-bot">
                    <span className="feed-word">"{v.word}"</span>
                    <span className="feed-time">{new Date(v.timestamp).toLocaleString('fr-FR')}</span>
                    <button className="feed-del" onClick={() => handleDelete(v.id)} title="Supprimer">✕</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      {showModal && (
        <div className="overlay" onClick={e => e.target === e.currentTarget && setShowModal(false)}>
          <div className="modal" role="dialog" aria-modal="true">
            <div className="modal-corner tl" />
            <div className="modal-corner tr" />
            <div className="modal-corner bl" />
            <div className="modal-corner br" />
            <div className="modal-header">
              <span className="modal-title"><GlitchText text="NOUVELLE INFRACTION" /></span>
              <button className="modal-close" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <label className="field-label">CONTREVENANT *</label>
              <input
                className="field-input"
                placeholder="Nom de la personne..."
                value={person}
                onChange={e => setPerson(e.target.value)}
                autoFocus
              />
              <label className="field-label">DESCRIPTION DU MOT (optionnel)</label>
              <input
                className="field-input"
                placeholder="Le mot / la phrase..."
                value={word}
                onChange={e => setWord(e.target.value)}
              />
              <label className="field-label">MONTANT (€)</label>
              <input
                className="field-input"
                type="number"
                min="0.5"
                step="0.5"
                value={amount}
                onChange={e => setAmount(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSubmit()}
              />
              <div className="fine-preview">
                <span className="fine-preview-label">AMENDE À INFLIGER</span>
                <span className="fine-preview-value">{parseFloat(amount || '1').toFixed(2)} €</span>
              </div>
              <button
                className="submit-btn"
                onClick={handleSubmit}
                disabled={loading || !person.trim()}
              >
                {loading ? (
                  <><span className="spinner" /> TRAITEMENT EN COURS...</>
                ) : (
                  <>⚡ CONFIRMER L'INFRACTION</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
