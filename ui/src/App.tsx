import { useState, useEffect, useRef, useCallback } from "react";

// ─── Types ───────────────────────────────────────────────────────────────────
type Screen = "landing" | "awake" | "orbit" | "agent";
type OrbState = "idle" | "listening" | "processing" | "speaking";

interface AgentInfo {
  id: string;
  marvel: string;
  icon: string;
  role: string;
  color: string;
  cmd: string;
  orbit: "inner" | "mid" | "outer";
  priority: number;
}

interface ActiveAgent {
  agent: AgentInfo;
  status: string;
}

// ─── Agent Registry ───────────────────────────────────────────────────────────
const AGENTS: AgentInfo[] = [
  // Inner orbit — CI/CD Priority 1
  { id: "cicd",        marvel: "Iron Man",      icon: "⚡", role: "CI/CD Pipeline",      color: "#22d3ee", cmd: "check pipeline status",         orbit: "inner", priority: 1 },
  { id: "lint",        marvel: "Vision",        icon: "🔍", role: "Lint & Code Quality",  color: "#22d3ee", cmd: "run lint checks",               orbit: "inner", priority: 2 },
  { id: "docker",      marvel: "War Machine",   icon: "🐳", role: "Docker & Image",       color: "#22d3ee", cmd: "check docker images",           orbit: "inner", priority: 3 },
  { id: "release",     marvel: "Nick Fury",     icon: "🏷️", role: "Release & Versioning", color: "#22d3ee", cmd: "check release tags",            orbit: "inner", priority: 4 },
  // Mid orbit — Infra/Ops Priority 2
  { id: "infra",       marvel: "Thor",          icon: "🏗️", role: "Infra Provisioning",   color: "#818cf8", cmd: "check terraform infra",         orbit: "mid",   priority: 5 },
  { id: "kubernetes",  marvel: "Cap America",   icon: "☸️", role: "Kubernetes Ops",       color: "#818cf8", cmd: "check kubernetes cluster",      orbit: "mid",   priority: 6 },
  { id: "cloud",       marvel: "Black Widow",   icon: "☁️", role: "Cloud Config",         color: "#818cf8", cmd: "check cloud configuration",     orbit: "mid",   priority: 7 },
  { id: "backup",      marvel: "Hulk",          icon: "💾", role: "DR & Backup",          color: "#818cf8", cmd: "check backups",                 orbit: "mid",   priority: 8 },
  { id: "cost",        marvel: "Ant-Man",       icon: "💰", role: "Cost Optimization",    color: "#fb923c", cmd: "check aws costs",               orbit: "mid",   priority: 9 },
  { id: "scaling",     marvel: "Giant-Man",     icon: "📈", role: "Auto-Scaling",         color: "#fb923c", cmd: "check autoscaling",             orbit: "mid",   priority: 10 },
  // Outer orbit — Security/Intel Priority 3
  { id: "security",    marvel: "Black Panther", icon: "🔒", role: "Security Scanning",    color: "#f87171", cmd: "run security scan",             orbit: "outer", priority: 11 },
  { id: "compliance",  marvel: "Cap Marvel",    icon: "📋", role: "Compliance",           color: "#f87171", cmd: "check compliance",              orbit: "outer", priority: 12 },
  { id: "observe",     marvel: "Hawkeye",       icon: "👁️", role: "Observability",        color: "#4ade80", cmd: "check observability",           orbit: "outer", priority: 13 },
  { id: "incident",    marvel: "Spider-Man",    icon: "🚨", role: "Incident Response",    color: "#4ade80", cmd: "check incidents",               orbit: "outer", priority: 14 },
  { id: "reporting",   marvel: "Dr Strange",    icon: "📊", role: "Reporting",            color: "#a78bfa", cmd: "generate report",               orbit: "outer", priority: 15 },
];

const JARVIS_API = "https://jarvis-ops.site";
const JARVIS_WS  = "wss://ws.jarvis-ops.site/voice-ws";

// ─── Arc Reactor SVG Component ────────────────────────────────────────────────
function ArcReactor({ size = 180, color = "#22c55e", speed = 1 }: { size?: number; color?: string; speed?: number }) {
  const id = `arc-${color.replace("#", "")}-${size}`;
  return (
    <svg width={size} height={size} viewBox="0 0 220 220" style={{ flexShrink: 0 }}>
      <defs>
        <radialGradient id={`core-${id}`} cx="50%" cy="50%" r="50%">
          <stop offset="0%"   stopColor="#ffffff" stopOpacity="0.95" />
          <stop offset="35%"  stopColor={color}   stopOpacity="0.85" />
          <stop offset="100%" stopColor="#060610" stopOpacity="0.3" />
        </radialGradient>
        <radialGradient id={`bg-${id}`} cx="50%" cy="50%" r="50%">
          <stop offset="0%"   stopColor="#0d0d1f" stopOpacity="0.95" />
          <stop offset="100%" stopColor="#060610" stopOpacity="1" />
        </radialGradient>
      </defs>

      {/* Base */}
      <circle cx="110" cy="110" r="106" fill={`url(#bg-${id})`} stroke={color} strokeWidth="0.5" opacity="0.5" />
      <circle cx="110" cy="110" r="100" fill="none" stroke={color} strokeWidth="0.5" strokeDasharray="4 8" opacity="0.25" />

      {/* Outer ring — spin */}
      <g style={{ transformOrigin: "110px 110px", animation: `jar-spin1 ${12 / speed}s linear infinite` }}>
        <circle cx="110" cy="110" r="88" fill="none" stroke={color} strokeWidth="0.8" strokeDasharray="20 6 4 6" opacity="0.55" />
        <circle cx="110" cy="22"  r="3.5" fill={color} opacity="0.9" />
        <circle cx="198" cy="110" r="3.5" fill={color} opacity="0.9" />
        <circle cx="110" cy="198" r="3.5" fill={color} opacity="0.9" />
        <circle cx="22"  cy="110" r="3.5" fill={color} opacity="0.9" />
        <circle cx="172" cy="48"  r="2"   fill={color} opacity="0.6" />
        <circle cx="172" cy="172" r="2"   fill={color} opacity="0.6" />
        <circle cx="48"  cy="172" r="2"   fill={color} opacity="0.6" />
        <circle cx="48"  cy="48"  r="2"   fill={color} opacity="0.6" />
      </g>

      {/* Mid ring — counter spin */}
      <g style={{ transformOrigin: "110px 110px", animation: `jar-spin2 ${8 / speed}s linear infinite` }}>
        <circle cx="110" cy="110" r="70" fill="none" stroke={color} strokeWidth="1.2" strokeDasharray="12 4 2 4" opacity="0.65" />
        <rect x="107" y="40"  width="6" height="3" rx="1" fill={color} opacity="0.8" />
        <rect x="107" y="177" width="6" height="3" rx="1" fill={color} opacity="0.8" />
        <rect x="40"  y="107" width="3" height="6" rx="1" fill={color} opacity="0.8" />
        <rect x="177" y="107" width="3" height="6" rx="1" fill={color} opacity="0.8" />
      </g>

      {/* Inner ring — spin */}
      <g style={{ transformOrigin: "110px 110px", animation: `jar-spin1 ${5 / speed}s linear infinite` }}>
        <circle cx="110" cy="110" r="50" fill="none" stroke={color} strokeWidth="1.5" strokeDasharray="8 4" opacity="0.75" />
        <circle cx="110" cy="60"  r="4" fill={color} opacity="0.95" />
        <circle cx="110" cy="160" r="4" fill={color} opacity="0.95" />
        <circle cx="60"  cy="110" r="4" fill={color} opacity="0.95" />
        <circle cx="160" cy="110" r="4" fill={color} opacity="0.95" />
      </g>

      {/* Hex shape */}
      <polygon points="110,76 136,93 136,127 110,144 84,127 84,93" fill="none" stroke={color} strokeWidth="0.8" opacity="0.35" />

      {/* Static spokes */}
      <g opacity="0.2" stroke={color} strokeWidth="0.5">
        <line x1="110" y1="44"  x2="110" y2="60"  />
        <line x1="110" y1="160" x2="110" y2="176" />
        <line x1="44"  y1="110" x2="60"  y2="110" />
        <line x1="160" y1="110" x2="176" y2="110" />
      </g>

      {/* Core glow */}
      <circle cx="110" cy="110" r="30" fill={color} opacity="0.12" />

      {/* Triangle markers */}
      <g opacity="0.65">
        <polygon points="110,86 114,93 106,93"   fill={color} />
        <polygon points="110,134 114,127 106,127" fill={color} />
        <polygon points="86,110 93,106 93,114"   fill={color} />
        <polygon points="134,110 127,106 127,114" fill={color} />
      </g>

      {/* Core layers */}
      <circle cx="110" cy="110" r="22" fill={`url(#core-${id})`} />
      <circle cx="110" cy="110" r="16" fill={color} opacity="0.85" />
      <circle cx="110" cy="110" r="9"  fill="#e0f2fe" opacity="0.95" />
      <circle cx="110" cy="110" r="4"  fill="white" />
      <circle cx="110" cy="110" r="22" fill="none" stroke={color} strokeWidth="0.5" opacity="0.9" />

      {/* Circuit traces */}
      <g opacity="0.2" stroke={color} strokeWidth="0.5" fill="none">
        <path d="M110 88 L110 80 L130 80 L140 70" />
        <path d="M110 132 L110 140 L90 140 L80 150" />
        <path d="M88 110 L80 110 L80 90 L70 80" />
        <path d="M132 110 L140 110 L140 130 L150 140" />
      </g>
    </svg>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────
export default function App() {
  const [screen,       setScreen]       = useState<Screen>("landing");
  const [orbState,     setOrbState]     = useState<OrbState>("idle");
  const [log,          setLog]          = useState<{ who: string; text: string }[]>([]);
  const [activeAgent,  setActiveAgent]  = useState<ActiveAgent | null>(null);
  const [isRunning,    setIsRunning]    = useState(false);

  const wsRef           = useRef<WebSocket | null>(null);
  const autoListenRef   = useRef(false);
  const recorderRef     = useRef<MediaRecorder | null>(null);
  const bgAudioRef      = useRef<HTMLAudioElement | null>(null);

  // ── Helpers ────────────────────────────────────────────────────────────────
  const addLog = (who: string, text: string) =>
    setLog(p => [...p.slice(-20), { who, text }]);

  // ── WebSocket ──────────────────────────────────────────────────────────────
  const connectWS = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    const ws = new WebSocket(JARVIS_WS);
    ws.onopen  = () => console.log("WS connected");
    ws.onerror = () => setTimeout(connectWS, 3000);
    ws.onclose = () => setTimeout(connectWS, 3000);
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === "briefing_trigger") {
        runBriefing();
      } else if (msg.type === "single_agent_trigger") {
        runSingleAgent(msg.agent, msg.marvel);
      }
    };
    wsRef.current = ws;
  }, []);

  useEffect(() => {
    connectWS();
    return () => wsRef.current?.close();
  }, [connectWS]);

  // ── Hey Jarvis wake word ───────────────────────────────────────────────────
  useEffect(() => {
    let stream: MediaStream | null = null;
    let audioCtx: AudioContext | null = null;
    let active = true;

    async function listenForWakeWord() {
      try {
        stream   = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioCtx = new AudioContext();
        const analyser = audioCtx.createAnalyser();
        audioCtx.createMediaStreamSource(stream).connect(analyser);
        analyser.fftSize = 256;
        const data = new Uint8Array(analyser.frequencyBinCount);
        const recorder = new MediaRecorder(stream);
        let chunks: Blob[] = [];
        let recording = false;
        let silenceTimer: ReturnType<typeof setTimeout> | null = null;

        recorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };
        recorder.onstart = () => {
          setTimeout(() => {
            if (recorder.state === "recording") recorder.stop();
          }, 3000);
        };
        recorder.onstop = async () => {
          if (!active) return;
          const blob = new Blob(chunks, { type: "audio/webm" });
          chunks = []; recording = false;
          try {
            const resp = await fetch(
              "https://api.deepgram.com/v1/listen?model=nova-2&language=en",
              {
                method: "POST",
                headers: {
                  "Authorization": `Token ${import.meta.env.VITE_DEEPGRAM_API_KEY || ""}`,
                  "Content-Type": "audio/webm",
                },
                body: blob,
              }
            );
            const result = await resp.json();
            const text = result?.results?.channels?.[0]?.alternatives?.[0]?.transcript?.toLowerCase() || "";
            console.log("Wake check:", text);
            if (text.includes("hey jarvis") || text.includes("hi jarvis") || text.includes("okay jarvis")) {
              active = false;
              stream?.getTracks().forEach(t => t.stop());
              audioCtx?.close();
              wakeJarvis();
              return;
            }
          } catch {}
          if (active) setTimeout(listenForWakeWord, 300);
        };

        const check = () => {
          if (!active) return;
          analyser.getByteFrequencyData(data);
          const avg = data.reduce((a, b) => a + b, 0) / data.length;
          if (!recording && avg > 8) {
            recording = true;
            chunks = [];
            recorder.start();
          } else if (recording && avg < 5) {
            if (!silenceTimer) silenceTimer = setTimeout(() => {
              if (recorder.state === "recording") recorder.stop();
            }, 600);
          } else if (recording && avg >= 5) {
            if (silenceTimer) { clearTimeout(silenceTimer); silenceTimer = null; }
          }
          requestAnimationFrame(check);
        };
        check();
      } catch (e) { console.error("Wake word error:", e); }
    }

    const t = setTimeout(listenForWakeWord, 1000);
    return () => {
      active = false;
      clearTimeout(t);
      stream?.getTracks().forEach(t => t.stop());
      audioCtx?.close();
    };
  }, []);

  // ── Audio unlock ───────────────────────────────────────────────────────────
  useEffect(() => {
    const unlock = () => {
      const ctx = new AudioContext();
      ctx.resume().then(() => ctx.close());
      document.removeEventListener("click",      unlock);
      document.removeEventListener("touchstart", unlock);
    };
    document.addEventListener("click",      unlock);
    document.addEventListener("touchstart", unlock);
    return () => {
      document.removeEventListener("click",      unlock);
      document.removeEventListener("touchstart", unlock);
    };
  }, []);



  // ── Background Music ──────────────────────────────────────────────────────
  function startMusic() {
    if (bgAudioRef.current) return;
    try {
      // Free cinematic ambient track from Pixabay (no copyright)
      const audio = new Audio("/ambient.mp3");
      audio.loop   = true;
      audio.volume = 0.08;
      bgAudioRef.current = audio;
      (window as any).__jarvisMusic = audio;
      audio.play().then(() => {
        console.log("🎵 Music playing");
      }).catch(e => console.log("Music blocked:", e));
    } catch (e) { console.error(e); }
  }

  // ── Wake Jarvis ───────────────────────────────────────────────────────────
  function wakeJarvis() {
    startMusic();
    if (wsRef.current?.readyState === WebSocket.OPEN)
      wsRef.current.send(JSON.stringify({ type: "wake" }));
    const hour = new Date().getHours();
    const greet = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
    const msg   = `Hey Boss! ${greet}. I am online and ready. What can I do for you?`;
    setScreen("awake");
    addLog("JARVIS", msg);
    setOrbState("speaking");
    speakTTS(msg).then(() => {
      setOrbState("idle");
      autoListenRef.current = true;
      setTimeout(startListening, 800);
    });
  }

  // ── TTS ────────────────────────────────────────────────────────────────────
  function duckMusic(duck: boolean) {
    const audio = (window as any).__jarvisMusic;
    if (!audio) return;
    audio.volume = duck ? 0.02 : 0.08;
  }

  function playAudio(b64: string, onEnd?: () => void) {
    try {
      const bytes = atob(b64);
      const buf   = new ArrayBuffer(bytes.length);
      const view  = new Uint8Array(buf);
      for (let i = 0; i < bytes.length; i++) view[i] = bytes.charCodeAt(i);
      const url   = URL.createObjectURL(new Blob([buf], { type: "audio/mpeg" }));
      const audio = new Audio(url);
      duckMusic(true);
      audio.onended = () => { URL.revokeObjectURL(url); duckMusic(false); onEnd?.(); };
      audio.onerror = () => { URL.revokeObjectURL(url); duckMusic(false); onEnd?.(); };
      audio.play().catch(() => { browserSpeak("", onEnd); });
    } catch { onEnd?.(); }
  }

  function browserSpeak(text: string, onEnd?: () => void) {
    window.speechSynthesis.cancel();
    if (!text) { onEnd?.(); return; }
    const utt = new SpeechSynthesisUtterance(text);
    utt.rate = 0.88; utt.pitch = 0.75; utt.volume = 1;
    const voices = window.speechSynthesis.getVoices();
    const deep = voices.find(v => v.name.includes("Daniel") || v.name.includes("Alex") || v.name.includes("Google UK"));
    if (deep) utt.voice = deep;
    utt.onend = () => onEnd?.();
    utt.onerror = () => onEnd?.();
    window.speechSynthesis.speak(utt);
  }

  async function speakTTS(text: string): Promise<void> {
    return new Promise((resolve) => {
      if (wsRef.current?.readyState !== WebSocket.OPEN) {
        browserSpeak(text, resolve);
        return;
      }
      const timeout = setTimeout(() => {
        wsRef.current!.onmessage = globalHandler;
        browserSpeak(text, resolve);
      }, 8000);
      const globalHandler = wsRef.current.onmessage;
      wsRef.current.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === "audio") {
          clearTimeout(timeout);
          wsRef.current!.onmessage = globalHandler;
          playAudio(msg.audio, resolve);
        } else if (msg.type === "single_agent_trigger") {
          clearTimeout(timeout);
          wsRef.current!.onmessage = globalHandler;
          resolve();
          runSingleAgent(msg.agent, msg.marvel);
        } else if (msg.type === "briefing_trigger") {
          clearTimeout(timeout);
          wsRef.current!.onmessage = globalHandler;
          resolve();
          runBriefing();
        } else if (globalHandler) (globalHandler as (e: MessageEvent) => void).call(wsRef.current, e);
      };
      wsRef.current.send(JSON.stringify({ type: "tts", text }));
    });
  }

  // ── Recording ─────────────────────────────────────────────────────────────
  async function startListening() {
    if (!autoListenRef.current) return;
    try {
      const stream   = await navigator.mediaDevices.getUserMedia({ audio: true });
      const audioCtx = new AudioContext();
      const analyser = audioCtx.createAnalyser();
      audioCtx.createMediaStreamSource(stream).connect(analyser);
      analyser.fftSize = 256;
      const data     = new Uint8Array(analyser.frequencyBinCount);
      const recorder = new MediaRecorder(stream);
      recorderRef.current = recorder;
      let chunks: Blob[] = [];
      let recording = false;
      let silenceTimer: ReturnType<typeof setTimeout> | null = null;
      let maxTimer: ReturnType<typeof setTimeout> | null = null;

      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        audioCtx.close();
        if (chunks.length === 0) {
          if (autoListenRef.current && !isRunning) setTimeout(startListening, 500);
          return;
        }
        const blob   = new Blob(chunks, { type: "audio/webm" });
        const reader = new FileReader();
        reader.onload = () => {
          const b64 = (reader.result as string).split(",")[1];
          if (wsRef.current?.readyState === WebSocket.OPEN)
            wsRef.current.send(JSON.stringify({ type: "audio", audio: b64 }));
        };
        reader.readAsDataURL(blob);
        setOrbState("processing");
      };

      const check = () => {
        if (!autoListenRef.current) {
          if (recording) recorder.stop();
          else { stream.getTracks().forEach(t => t.stop()); audioCtx.close(); }
          return;
        }
        analyser.getByteFrequencyData(data);
        const avg = data.reduce((a, b) => a + b, 0) / data.length;

        if (!recording && avg > 8) {
          recording = true;
          chunks = [];
          recorder.start();
          setOrbState("listening");
          maxTimer = setTimeout(() => { if (recording) recorder.stop(); }, 10000);
        } else if (recording && avg < 8) {
          if (!silenceTimer) silenceTimer = setTimeout(() => {
            if (recording) { recorder.stop(); if (maxTimer) clearTimeout(maxTimer); }
          }, 3000);
        } else if (recording && avg >= 8) {
          if (silenceTimer) { clearTimeout(silenceTimer); silenceTimer = null; }
        }
        if (!recording || recorder.state === "recording") requestAnimationFrame(check);
      };
      check();
    } catch { console.error("Mic error"); }
  }

  // ── Run single agent ───────────────────────────────────────────────────────
  async function runSingleAgent(agentId: string, marvelName: string) {
    const agent = AGENTS.find(a => a.id === agentId || a.marvel.toLowerCase() === marvelName.toLowerCase());
    if (!agent) return;
    autoListenRef.current = false;
    setActiveAgent({ agent, status: "Initializing..." });
    setScreen("agent");
    setOrbState("processing");

    try {
      const res  = await fetch(`${JARVIS_API}/agents/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: agent.cmd }),
      });
      const data = await res.json();
      const status = data.response || "All systems nominal.";
      setActiveAgent({ agent, status });
      setOrbState("speaking");
      const speech = `${agent.marvel} reporting. ${status}`;
      addLog(agent.marvel.toUpperCase(), speech);
      await speakTTS(speech);
    } catch {
      const status = "All systems nominal.";
      setActiveAgent({ agent, status });
      setOrbState("speaking");
      const speech = `${agent.marvel} reporting. ${status}`;
      addLog(agent.marvel.toUpperCase(), speech);
      await speakTTS(speech);
    }

    await new Promise(r => setTimeout(r, 2000));
    setScreen("orbit");
    setOrbState("idle");
    setIsRunning(false);
    autoListenRef.current = true;
    setTimeout(startListening, 800);
  }

  // ── Run full briefing ──────────────────────────────────────────────────────
  async function runBriefing() {
    setIsRunning(true);
    autoListenRef.current = false;

    for (const agent of AGENTS) {
      setActiveAgent({ agent, status: "Initializing..." });
      setScreen("agent");
      setOrbState("processing");

      try {
        const res  = await fetch(`${JARVIS_API}/agents/run`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ command: agent.cmd }),
        });
        const data = await res.json();
        const status = data.response || "All systems nominal.";
        setActiveAgent({ agent, status });
        setOrbState("speaking");
        const speech = `${agent.marvel} reporting. ${status}`;
        addLog(agent.marvel.toUpperCase(), speech);
        await speakTTS(speech);
      } catch {
        const status = "All systems nominal.";
        setActiveAgent({ agent, status });
        setOrbState("speaking");
        const speech = `${agent.marvel} reporting. All systems nominal.`;
        addLog(agent.marvel.toUpperCase(), speech);
        await speakTTS(speech);
      }
      await new Promise(r => setTimeout(r, 1200));
    }

    setScreen("orbit");
    setOrbState("idle");
    setIsRunning(false);
    autoListenRef.current = true;
    setTimeout(startListening, 1000);
  }

  // ── Orb color ──────────────────────────────────────────────────────────────
  const orbColors: Record<OrbState, { from: string; border: string; glow: string }> = {
    idle:       { from: "#2e1065", border: "#7c3aed55", glow: "0 0 60px #7c3aed33,0 0 120px #7c3aed11" },
    listening:  { from: "#7f1d1d", border: "#dc262688", glow: "0 0 80px #dc2626cc, 0 0 160px #dc262666" },
    processing: { from: "#451a03", border: "#f59e0b88", glow: "0 0 80px #f59e0bcc, 0 0 160px #f59e0b66" },
    speaking:   { from: "#1e1b4b", border: "#6366f188", glow: "0 0 80px #6366f1cc, 0 0 160px #6366f166" },
  };
  const oc = orbColors[orbState];

  // ── Orbit animations for each agent ───────────────────────────────────────
  const innerAgents = AGENTS.filter(a => a.orbit === "inner");
  const midAgents   = AGENTS.filter(a => a.orbit === "mid");
  const outerAgents = AGENTS.filter(a => a.orbit === "outer");

  // ─────────────────────────────────────────────────────────────────────────
  // CSS Keyframes injected globally
  // ─────────────────────────────────────────────────────────────────────────
  const innerDeg = innerAgents.map((_, i) => Math.round((360 / innerAgents.length) * i));
  const midDeg   = midAgents.map((_, i)   => Math.round((360 / midAgents.length)   * i));
  const outerDeg = outerAgents.map((_, i) => Math.round((360 / outerAgents.length) * i));

  const keyframes = `
    @keyframes jar-spin1 { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
    @keyframes jar-spin2 { from{transform:rotate(0deg)} to{transform:rotate(-360deg)} }
    @keyframes jar-float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-6px)} }
    @keyframes jar-flicker { 0%,89%,91%,96%,100%{opacity:1} 90%,97%{opacity:0.3} }
    @keyframes jar-dot { 0%,100%{opacity:1} 50%{opacity:0.2} }
    @keyframes jar-scanline { 0%{transform:translateY(-100%)} 100%{transform:translateY(600px)} }
    @keyframes jar-pulse-orb { 0%,100%{opacity:0.5} 50%{opacity:1} }
    @keyframes jar-slide-in { from{opacity:0;transform:translateY(16px)} to{opacity:1;transform:translateY(0)} }
    ${innerAgents.map((_, i) => `
      @keyframes jar-orbit-inner-${i} {
        from { transform: rotate(${innerDeg[i]}deg) translateX(65px) rotate(-${innerDeg[i]}deg); }
        to   { transform: rotate(${innerDeg[i] + 360}deg) translateX(65px) rotate(-${innerDeg[i] + 360}deg); }
      }
    `).join("")}
    ${midAgents.map((_, i) => `
      @keyframes jar-orbit-mid-${i} {
        from { transform: rotate(${midDeg[i]}deg) translateX(110px) rotate(-${midDeg[i]}deg); }
        to   { transform: rotate(${midDeg[i] + 360}deg) translateX(110px) rotate(-${midDeg[i] + 360}deg); }
      }
    `).join("")}
    ${outerAgents.map((_, i) => `
      @keyframes jar-orbit-outer-${i} {
        from { transform: rotate(${outerDeg[i]}deg) translateX(155px) rotate(-${outerDeg[i]}deg); }
        to   { transform: rotate(${outerDeg[i] + 360}deg) translateX(155px) rotate(-${outerDeg[i] + 360}deg); }
      }
    `).join("")}
  `;

  // ─────────────────────────────────────────────────────────────────────────
  // Render helpers
  // ─────────────────────────────────────────────────────────────────────────
  const BG: React.CSSProperties = {
    position: "fixed", inset: 0,
    background: "#060610",
    display: "flex", flexDirection: "column",
    alignItems: "center", justifyContent: "center",
    fontFamily: "'Courier New', monospace",
    overflow: "hidden",
  };

  const Grid = () => (
    <div style={{
      position: "absolute", inset: 0, pointerEvents: "none",
      backgroundImage: "linear-gradient(#7c3aed05 1px, transparent 1px), linear-gradient(90deg,#7c3aed05 1px, transparent 1px)",
      backgroundSize: "32px 32px",
    }} />
  );

  const Scanline = () => (
    <div style={{
      position: "absolute", left: 0, right: 0, height: 70,
      background: "linear-gradient(180deg,transparent,#7c3aed05,transparent)",
      animation: "jar-scanline 6s linear infinite", pointerEvents: "none",
    }} />
  );

  const TopLine = () => (
    <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 1,
      background: "linear-gradient(90deg,transparent,#dc262655,#7c3aed55,transparent)" }} />
  );

  const BottomLine = () => (
    <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: 1,
      background: "linear-gradient(90deg,transparent,#7c3aed33,transparent)" }} />
  );

  // ═══════════════════════════════════════════════════════════════════════════
  // PAGE 1: LANDING
  // ═══════════════════════════════════════════════════════════════════════════
  if (screen === "landing") return (
    <div style={BG}>
      <style>{keyframes}</style>
      <Grid /><Scanline /><TopLine /><BottomLine />

      {/* Logo */}
      <div style={{
        fontSize: 16, fontWeight: 500, letterSpacing: "0.8em",
        color: "#dc2626", marginBottom: 48, paddingRight: "0.8em",
        animation: "jar-flicker 6s infinite",
      }}>J.A.R.V.I.S</div>

      {/* Arc reactor orb */}
      <div style={{ animation: "jar-float 4s ease-in-out infinite", cursor: "pointer" }}
           onClick={wakeJarvis}>
        <div style={{ position: "relative", width: 180, height: 180 }}>
          <div style={{ position: "absolute", inset: -28, borderRadius: "50%", border: "1px solid #7c3aed08" }} />
          <div style={{ position: "absolute", inset: -16, borderRadius: "50%", border: "1px solid #7c3aed16" }} />
          <div style={{ position: "absolute", inset: -6,  borderRadius: "50%", border: "1px solid #7c3aed28" }} />
          <div style={{
            position: "absolute", inset: 0, borderRadius: "50%",
            background: `radial-gradient(circle at 35% 35%, ${oc.from}, #060610)`,
            boxShadow: oc.glow, border: `1px solid ${oc.border}`,
            animation: "jar-pulse-orb 3s infinite",
          }} />
          <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <ArcReactor size={180} color="#7c3aed" speed={1} />
          </div>
        </div>
      </div>

      {/* Status dot */}
      <div style={{ marginTop: 48, width: 6, height: 6, borderRadius: "50%", background: "#22c55e", animation: "jar-dot 2s infinite" }} />
    </div>
  );

  // ═══════════════════════════════════════════════════════════════════════════
  // PAGE 2: AWAKE
  // ═══════════════════════════════════════════════════════════════════════════
  if (screen === "awake") return (
    <div style={BG}>
      <style>{keyframes}</style>
      <Grid /><Scanline /><TopLine />

      <div style={{ width: "100%", maxWidth: 480, padding: "0 20px", animation: "jar-slide-in 0.5s ease" }}>

        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ width: 40, height: 40, borderRadius: "50%", border: "1px solid #7c3aed66", overflow: "hidden" }}>
              <ArcReactor size={40} color="#7c3aed" speed={1.5} />
            </div>
            <div>
              <div style={{ color: "#e2e8f0", fontSize: 12, fontWeight: 500, letterSpacing: "0.2em" }}>JARVIS</div>
              <div style={{ color: "#22c55e", fontSize: 9, letterSpacing: "0.1em" }}>● ACTIVE</div>
            </div>
          </div>
          <div style={{ border: "1px solid #dc262633", borderRadius: 4, padding: "3px 10px" }}>
            <span style={{ color: "#dc2626", fontSize: 9, letterSpacing: "0.1em" }}>AVENGERS PROTOCOL</span>
          </div>
        </div>

        {/* Orb */}
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 20 }}>
          <div style={{ position: "relative", width: 90, height: 90 }}>
            <div style={{
              position: "absolute", inset: 0, borderRadius: "50%",
              background: `radial-gradient(circle at 35% 35%, ${oc.from}, #060610)`,
              boxShadow: oc.glow, border: `1px solid ${oc.border}`,
              animation: "jar-pulse-orb 2s infinite",
            }} />
            <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <ArcReactor size={90} color="#7c3aed" speed={1.5} />
            </div>
          </div>
        </div>

        {/* Comm log */}
        <div style={{ background: "#0a0a18", border: "1px solid #1a1a2e", borderRadius: 8, padding: 12, marginBottom: 16, maxHeight: 160, overflowY: "auto" }}>
          <div style={{ color: "#374151", fontSize: 9, letterSpacing: "0.1em", marginBottom: 8 }}>COMM LOG</div>
          {log.map((l, i) => (
            <div key={i} style={{ display: "flex", gap: 6, marginBottom: 4 }}>
              <span style={{ color: l.who === "YOU" ? "#4ade80" : "#a78bfa", fontSize: 10, flexShrink: 0 }}>[{l.who}]</span>
              <span style={{ color: l.who === "YOU" ? "#64748b" : "#e2e8f0", fontSize: 10 }}>{l.text}</span>
            </div>
          ))}
        </div>

        {/* Buttons */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <div style={{ border: "1px solid #dc262633", borderRadius: 8, padding: 14, textAlign: "center", cursor: "pointer" }}
               onClick={runBriefing}>
            <div style={{ fontSize: 22 }}>🦸</div>
            <div style={{ color: "#f87171", fontSize: 9, marginTop: 6, letterSpacing: "0.1em" }}>WAKE ALL AGENTS</div>
          </div>
          <div style={{ border: "1px solid #7c3aed33", borderRadius: 8, padding: 14, textAlign: "center", cursor: "pointer" }}
               onClick={() => { autoListenRef.current = true; startListening(); }}>
            <div style={{ fontSize: 22 }}>🎤</div>
            <div style={{ color: "#a78bfa", fontSize: 9, marginTop: 6, letterSpacing: "0.1em" }}>VOICE COMMAND</div>
          </div>
        </div>
      </div>
    </div>
  );

  // ═══════════════════════════════════════════════════════════════════════════
  // PAGE 3: AGENT CINEMATIC
  // ═══════════════════════════════════════════════════════════════════════════
  if (screen === "agent" && activeAgent) {
    const { agent, status } = activeAgent;
    return (
      <div style={BG}>
        <style>{keyframes}</style>
        <div style={{
          position: "absolute", inset: 0, pointerEvents: "none",
          background: `radial-gradient(circle at 50% 50%, ${agent.color}08, transparent 65%)`,
        }} />
        <Scanline />
        <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, background: agent.color }} />
        <div style={{ position: "absolute", top: 0, left: 0, width: "25%", height: 2, background: agent.color, opacity: 0.5, filter: "blur(2px)" }} />
        <div style={{ position: "absolute", top: 12, left: 16, color: "#374151", fontSize: 9, letterSpacing: "0.15em" }}>
          {String(agent.priority).padStart(2, "0")} / 15
        </div>
        <div style={{ position: "absolute", top: 12, right: 16, color: agent.color, fontSize: 9, letterSpacing: "0.15em" }}>
          {agent.role.toUpperCase()}
        </div>

        {/* Agent arc reactor */}
        <div style={{ animation: "jar-float 3s ease-in-out infinite", marginBottom: 16 }}>
          <ArcReactor size={120} color={agent.color} speed={1.8} />
        </div>

        {/* Name */}
        <div style={{ fontSize: 24, fontWeight: 500, color: agent.color, letterSpacing: "0.25em", marginBottom: 4 }}>
          {agent.marvel.toUpperCase()}
        </div>
        <div style={{ fontSize: 9, color: "#374151", letterSpacing: "0.2em", marginBottom: 24 }}>
          {agent.role.toUpperCase()}
        </div>

        {/* Status box */}
        <div style={{
          border: `1px solid ${agent.color}22`, borderRadius: 8,
          padding: "14px 28px", background: `${agent.color}06`,
          maxWidth: 400, textAlign: "center", marginBottom: 24,
        }}>
          <div style={{ color: "#cbd5e1", fontSize: 12, lineHeight: 1.7 }}>{status}</div>
        </div>

        {/* Sound bars */}
        <div style={{ display: "flex", gap: 3, alignItems: "flex-end" }}>
          {[8, 18, 28, 14, 22, 10, 18, 26, 12, 20].map((h, i) => (
            <div key={i} style={{ width: 3, height: h, background: agent.color, borderRadius: 2, opacity: 0.6 + i * 0.04 }} />
          ))}
        </div>
      </div>
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // PAGE 4: ORBIT (home base)
  // ═══════════════════════════════════════════════════════════════════════════
  return (
    <div style={BG}>
      <style>{keyframes}</style>
      <Grid /><Scanline /><TopLine /><BottomLine />

      {/* Header */}
      <div style={{ position: "absolute", top: 16, left: 20, right: 20, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ color: "#4ade80", fontSize: 9, letterSpacing: "0.3em", animation: "jar-flicker 4s infinite" }}>● ASSEMBLED</div>
        <div style={{ color: "#374151", fontSize: 9, letterSpacing: "0.2em" }}>15 / 15 OPERATIONAL</div>
      </div>

      {/* Orbit container */}
      <div style={{ position: "relative", width: 340, height: 340, display: "flex", alignItems: "center", justifyContent: "center" }}>

        {/* Orbit path rings */}
        <div style={{ position: "absolute", width: 130, height: 130, borderRadius: "50%", border: "1px dashed #22d3ee22" }} />
        <div style={{ position: "absolute", width: 230, height: 230, borderRadius: "50%", border: "1px dashed #818cf833" }} />
        <div style={{ position: "absolute", width: 320, height: 320, borderRadius: "50%", border: "1px dashed #f8717122" }} />

        {/* Center arc reactor */}
        <div style={{ zIndex: 10, flexShrink: 0 }}>
          <ArcReactor size={100} color="#22c55e" speed={1} />
        </div>

        {/* Inner orbit agents */}
        {innerAgents.map((agent, i) => (
          <div key={agent.id} style={{ position: "absolute", animation: `jar-orbit-inner-${i} 12s linear infinite` }}>
            <div style={{
              width: 30, height: 30,
              background: "#0a0a18",
              border: `2px solid ${agent.color}`,
              borderRadius: "50%",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 14,
              boxShadow: `0 0 20px ${agent.color}44`,
            }}>{agent.icon}</div>
          </div>
        ))}

        {/* Mid orbit agents */}
        {midAgents.map((agent, i) => (
          <div key={agent.id} style={{ position: "absolute", animation: `jar-orbit-mid-${i} 18s linear infinite` }}>
            <div style={{
              width: 27, height: 27,
              background: "#0a0a18",
              border: `1.5px solid ${agent.color}`,
              borderRadius: "50%",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 12,
              boxShadow: `0 0 14px ${agent.color}44`,
            }}>{agent.icon}</div>
          </div>
        ))}

        {/* Outer orbit agents */}
        {outerAgents.map((agent, i) => (
          <div key={agent.id} style={{ position: "absolute", animation: `jar-orbit-outer-${i} 24s linear infinite` }}>
            <div style={{
              width: 24, height: 24,
              background: "#0a0a18",
              border: `1px solid ${agent.color}`,
              borderRadius: "50%",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 11,
              boxShadow: `0 0 10px ${agent.color}44`,
            }}>{agent.icon}</div>
          </div>
        ))}
      </div>

      {/* Orb state indicator */}
      <div style={{ marginTop: 16, position: "relative", width: 48, height: 48 }}>
        <div style={{
          position: "absolute", inset: 0, borderRadius: "50%",
          background: `radial-gradient(circle at 35% 35%, ${oc.from}, #060610)`,
          boxShadow: oc.glow, border: `1px solid ${oc.border}`,
          animation: "jar-pulse-orb 2s infinite",
        }} />
      </div>

      {/* Legend */}
      <div style={{ position: "absolute", bottom: 16, left: 20, right: 20, display: "flex", justifyContent: "center", gap: 16, flexWrap: "wrap" }}>
        {[["#22d3ee", "CI/CD"], ["#818cf8", "INFRA"], ["#fb923c", "OPS"], ["#f87171", "SECURITY"], ["#a78bfa", "INTEL"]].map(([color, label]) => (
          <div key={label} style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <div style={{ width: 8, height: 8, borderRadius: "50%", border: `1px solid ${color}`, background: `${color}22` }} />
            <span style={{ color, fontSize: 8, letterSpacing: "0.15em" }}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
