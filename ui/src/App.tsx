import { useState, useEffect, useRef } from "react";

const AGENT_ICONS: Record<string, string> = {
  "Iron Man": "⚡", "Vision": "🔍",
  "War Machine": "🐳", "Nick Fury": "🏷️",
  "Thor": "🏗️", "Captain America": "☸️",
  "Black Widow": "☁️", "Hulk": "💾",
  "Ant-Man": "💰", "Giant-Man": "📈",
  "Black Panther": "🔒", "Captain Marvel": "📋",
  "Hawkeye": "👁️", "Spider-Man": "🚨", "Doctor Strange": "📊",
};

const MARVEL_NAMES: Record<string, string> = {
  "CI/CD Pipeline": "Iron Man",
  "Lint & Code Quality": "Vision",
  "Docker & Image": "War Machine",
  "Release & Versioning": "Nick Fury",
  "Infra Provisioning": "Thor",
  "Kubernetes Ops": "Captain America",
  "Cloud Config": "Black Widow",
  "DR & Backup": "Hulk",
  "Cost Optimization": "Ant-Man",
  "Auto-Scaling": "Giant-Man",
  "Security Scanning": "Black Panther",
  "Compliance": "Captain Marvel",
  "Observability": "Hawkeye",
  "Incident Response": "Spider-Man",
  "Reporting": "Doctor Strange",
};

const CATEGORY_COLORS: Record<string, string> = {
  "CI/CD": "#22d3ee", "Infrastructure": "#818cf8",
  "Cost": "#fb923c", "Security": "#f87171",
  "Observability": "#4ade80", "Intelligence": "#a78bfa",
};

const AGENT_CATEGORIES: Record<string, string> = {
  "CI/CD Pipeline": "CI/CD", "Lint & Code Quality": "CI/CD",
  "Docker & Image": "CI/CD", "Release & Versioning": "CI/CD",
  "Infra Provisioning": "Infrastructure", "Kubernetes Ops": "Infrastructure",
  "Cloud Config": "Infrastructure", "DR & Backup": "Infrastructure",
  "Cost Optimization": "Cost", "Auto-Scaling": "Cost",
  "Security Scanning": "Security", "Compliance": "Security",
  "Observability": "Observability", "Incident Response": "Observability",
  "Reporting": "Intelligence",
  "Iron Man": "CI/CD", "Vision": "CI/CD",
  "War Machine": "CI/CD", "Nick Fury": "CI/CD",
  "Thor": "Infrastructure", "Captain America": "Infrastructure",
  "Black Widow": "Infrastructure", "Hulk": "Infrastructure",
  "Ant-Man": "Cost", "Giant-Man": "Cost",
  "Black Panther": "Security", "Captain Marvel": "Security",
  "Hawkeye": "Observability", "Spider-Man": "Observability",
  "Doctor Strange": "Intelligence",
};

const ALL_AGENTS = [
  { agent: "CI/CD Pipeline", marvel: "Iron Man", cmd: "run the pipeline" },
  { agent: "Lint & Code Quality", marvel: "Vision", cmd: "run ruff" },
  { agent: "Docker & Image", marvel: "War Machine", cmd: "mirror the images" },
  { agent: "Release & Versioning", marvel: "Nick Fury", cmd: "what is the latest version" },
  { agent: "Infra Provisioning", marvel: "Thor", cmd: "plan the infra" },
  { agent: "Kubernetes Ops", marvel: "Captain America", cmd: "check the cluster" },
  { agent: "Cloud Config", marvel: "Black Widow", cmd: "audit cloud config" },
  { agent: "DR & Backup", marvel: "Hulk", cmd: "run a backup" },
  { agent: "Cost Optimization", marvel: "Ant-Man", cmd: "how are cloud costs" },
  { agent: "Auto-Scaling", marvel: "Giant-Man", cmd: "scaling status" },
  { agent: "Security Scanning", marvel: "Black Panther", cmd: "scan for vulnerabilities" },
  { agent: "Compliance", marvel: "Captain Marvel", cmd: "run compliance check" },
  { agent: "Observability", marvel: "Hawkeye", cmd: "hows the system" },
  { agent: "Incident Response", marvel: "Spider-Man", cmd: "any active incidents" },
  { agent: "Reporting", marvel: "Doctor Strange", cmd: "weekly summary" },
];

type Screen = "landing" | "awake" | "agent" | "done";

interface ActiveAgent {
  name: string;
  status: string;
  category: string;
  index: number;
}

export default function App() {
  const JARVIS_API = `${window.location.protocol}//${window.location.hostname}/api`;
  const VOICE_WS = `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.hostname}/voice-ws`;

  const [screen, setScreen] = useState<Screen>("landing");
  const [activeAgent, setActiveAgent] = useState<ActiveAgent | null>(null);
  const [orbState, setOrbState] = useState<"idle"|"listening"|"speaking"|"thinking">("idle");
  const [isRecording, setIsRecording] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [transcript, setTranscript] = useState<string[]>([]);
  const [completedAgents, setCompletedAgents] = useState<string[]>([]);
  const [statusText, setStatusText] = useState("");
  const [isBriefing, setIsBriefing] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const autoListenRef = useRef(false);

  useEffect(() => { connectWS(); return () => { wsRef.current?.close(); }; }, []);

  function connectWS() {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    try {
      const ws = new WebSocket(VOICE_WS);
      ws.onopen = () => setWsConnected(true);
      ws.onclose = () => { setWsConnected(false); setTimeout(connectWS, 3000); };
      ws.onerror = () => setWsConnected(false);
      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === "transcript") addLog("you", msg.text);
        else if (msg.type === "response") {
          addLog("jarvis", msg.text);
          setScreen("awake");
          setOrbState("speaking");
        } else if (msg.type === "audio") {
          playAudio(msg.audio, () => {
            setOrbState("idle");
            setTimeout(() => startListening(), 500);
          });
        } else if (msg.type === "briefing_trigger") {
          runBriefing();
        } else if (msg.type === "status") {
          if (msg.message === "transcribing" || msg.message === "processing") setOrbState("thinking");
          else if (msg.message === "speaking") setOrbState("speaking");
          else if (msg.message === "idle") setOrbState("idle");
        }
      };
      wsRef.current = ws;
    } catch { setTimeout(connectWS, 3000); }
  }

  function playAudio(base64Audio: string, onEnd?: () => void) {
    try {
      const bytes = atob(base64Audio);
      const buf = new ArrayBuffer(bytes.length);
      const view = new Uint8Array(buf);
      for (let i = 0; i < bytes.length; i++) view[i] = bytes.charCodeAt(i);
      const blob = new Blob([buf], { type: "audio/mpeg" });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.onended = () => { URL.revokeObjectURL(url); onEnd?.(); };
      audio.play();
    } catch {}
  }

  async function speakTTS(text: string): Promise<void> {
    return new Promise((resolve) => {
      if (wsRef.current?.readyState !== WebSocket.OPEN) {
        setTimeout(resolve, text.length * 80);
        return;
      }
      const timeout = setTimeout(resolve, 15000);
      const orig = wsRef.current.onmessage;
      wsRef.current.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === "audio") {
          clearTimeout(timeout);
          wsRef.current!.onmessage = orig;
          playAudio(msg.audio, resolve);
        } else if (orig) orig(e);
      };
      wsRef.current.send(JSON.stringify({ type: "tts", text }));
    });
  }

  async function startListening() {
    if (!autoListenRef.current || isBriefing) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const ctx = new AudioContext();
      const analyser = ctx.createAnalyser();
      ctx.createMediaStreamSource(stream).connect(analyser);
      analyser.fftSize = 512;
      const data = new Uint8Array(analyser.frequencyBinCount);
      setOrbState("listening");
      let speechDetected = false, silenceCount = 0, recording = false;
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      audioChunksRef.current = [];
      recorder.ondataavailable = (e) => audioChunksRef.current.push(e.data);
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        ctx.close();
        setIsRecording(false);
        if (speechDetected && audioChunksRef.current.length > 0) {
          const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
          const ab = await blob.arrayBuffer();
          const b64 = btoa(String.fromCharCode(...new Uint8Array(ab)));
          wsRef.current?.send(JSON.stringify({ type: "audio", audio: b64 }));
        } else {
          setTimeout(() => startListening(), 300);
        }
      };
      const interval = setInterval(() => {
        analyser.getByteFrequencyData(data);
        const avg = data.reduce((a, b) => a + b, 0) / data.length;
        if (avg > 15 && !recording) {
          speechDetected = true; recording = true;
          recorder.start(); setIsRecording(true);
        } else if (recording && avg < 8) {
          if (++silenceCount > 15) { clearInterval(interval); recorder.stop(); }
        } else if (recording) silenceCount = 0;
      }, 100);
      setTimeout(() => {
        clearInterval(interval);
        if (recording && recorder.state === "recording") recorder.stop();
        else if (!recording) {
          stream.getTracks().forEach(t => t.stop()); ctx.close();
          setIsRecording(false); setTimeout(() => startListening(), 300);
        }
      }, 10000);
      mediaRecorderRef.current = recorder;
    } catch { autoListenRef.current = false; }
  }

  async function toggleRecording() {
    if (isRecording) { mediaRecorderRef.current?.stop(); setIsRecording(false); return; }
    autoListenRef.current = true;
    startListening();
  }

  function addLog(role: string, text: string) {
    const t = new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
    setTranscript(prev => [...prev.slice(-50), `${t} [${role.toUpperCase()}]: ${text}`]);
  }

  async function runBriefing() {
    setIsBriefing(true);
    autoListenRef.current = false;
    setCompletedAgents([]);
    setScreen("awake");

    const hour = new Date().getHours();
    const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
    const wakeText = `${greeting} Chaitanya. All systems online. Activating 15 agents.`;
    addLog("jarvis", wakeText);
    setStatusText(wakeText);
    await speakTTS(wakeText);
    await new Promise(r => setTimeout(r, 500));

    for (let i = 0; i < ALL_AGENTS.length; i++) {
      const { agent, marvel, cmd } = ALL_AGENTS[i];
      const category = AGENT_CATEGORIES[agent] || "CI/CD";

      // Show cinematic agent screen
      setScreen("agent");
      setActiveAgent({ name: agent, status: "Initializing...", category, index: i });
      setOrbState("thinking");

      try {
        const res = await fetch(`${JARVIS_API}/agents/run`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ command: cmd }),
        });
        const data = await res.json();
        const status = data.response || "Systems nominal.";

        setActiveAgent({ name: agent, status, category, index: i });
        setOrbState("speaking");
        const speech = `${marvel} reporting. ${status}`;
        addLog("agent", speech);
        await speakTTS(speech);

      } catch {
        const status = "All systems nominal.";
        setActiveAgent({ name: agent, status, category, index: i });
        setOrbState("speaking");
        await speakTTS(`${marvel} reporting. All systems nominal.`);
      }

      setCompletedAgents(prev => [...prev, agent]);
      await new Promise(r => setTimeout(r, 300));
    }

    // All done
    setScreen("done");
    setOrbState("speaking");
    const closeText = "All 15 agents online. Jarvis is ready, Chaitanya.";
    addLog("jarvis", closeText);
    await speakTTS(closeText);
    await new Promise(r => setTimeout(r, 2000));
    setScreen("awake");
    setOrbState("idle");
    setIsBriefing(false);
    autoListenRef.current = true;
    setTimeout(() => startListening(), 500);
  }

  const catColor = activeAgent ? CATEGORY_COLORS[activeAgent.category] || "#6366f1" : "#6366f1";
  const orbColor = isRecording ? ["#991b1b","#ef4444"] : orbState === "listening" ? ["#0ea5e9","#38bdf8"] : orbState === "speaking" ? ["#6366f1","#818cf8"] : orbState === "thinking" ? ["#f59e0b","#fbbf24"] : ["#1a1a3e","#2a2a5e"];

  return (
    <div style={{ background: "#020208", minHeight: "100vh", color: "#e2e0ff", fontFamily: "JetBrains Mono, monospace", overflow: "hidden" }}>
      <style>{`
        @keyframes ping { 75%, 100% { transform: scale(2.5); opacity: 0; } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes glow { 0%, 100% { text-shadow: 0 0 20px currentColor; } 50% { text-shadow: 0 0 40px currentColor, 0 0 80px currentColor; } }
        @keyframes scanline { 0% { transform: translateY(-100%); } 100% { transform: translateY(100vh); } }
        @keyframes bars { 0%, 100% { height: 8px; } 50% { height: 32px; } }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #020208; }
      `}</style>

      {/* ── LANDING SCREEN ─────────────────────────────────────────── */}
      {screen === "landing" && (
        <div style={{ height: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 40 }}>
          {/* Scanline effect */}
          <div style={{ position: "fixed", inset: 0, background: "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(99,102,241,0.02) 2px, rgba(99,102,241,0.02) 4px)", pointerEvents: "none" }} />

          {/* Logo */}
          <div style={{ textAlign: "center", animation: "fadeIn 1s ease" }}>
            <div style={{ fontSize: 48, fontWeight: 700, color: "#6366f1", letterSpacing: "0.5em", animation: "glow 3s infinite" }}>J.A.R.V.I.S</div>
            <div style={{ fontSize: 10, color: "#334155", letterSpacing: "0.3em", marginTop: 8 }}>JUST A RATHER VERY INTELLIGENT SYSTEM</div>
          </div>

          {/* Orb */}
          <div style={{ position: "relative", width: 220, height: 220, cursor: "pointer" }} onClick={toggleRecording}>
            <div style={{ position: "absolute", inset: -30, borderRadius: "50%", border: "1px solid #6366f133", animation: "ping 3s ease infinite" }} />
            <div style={{ position: "absolute", inset: -15, borderRadius: "50%", border: "1px solid #6366f155", animation: "ping 2s ease infinite" }} />
            <div style={{
              width: "100%", height: "100%", borderRadius: "50%",
              background: isRecording ? "radial-gradient(circle at 35% 35%, #ef4444, #7f1d1d)" : "radial-gradient(circle at 35% 35%, #4f46e5, #020208)",
              boxShadow: isRecording ? "0 0 80px #ef444466, 0 0 160px #ef444433" : "0 0 80px #6366f166, 0 0 160px #6366f133",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 72, transition: "all 0.5s ease",
            }}>
              {isRecording ? "🔴" : "🤖"}
            </div>
          </div>

          {/* Instructions */}
          <div style={{ textAlign: "center", animation: "fadeIn 1.5s ease" }}>
            <div style={{ fontSize: 11, color: isRecording ? "#ef4444" : "#6366f1", letterSpacing: "0.3em", animation: "pulse 2s infinite", marginBottom: 16 }}>
              {isRecording ? "● LISTENING" : "● TAP TO ACTIVATE"}
            </div>
            <div style={{ fontSize: 22, color: "#e2e0ff", fontWeight: 300, marginBottom: 8 }}>Say "Hey Jarvis"</div>
            <div style={{ fontSize: 11, color: "#334155" }}>to initialize all systems</div>
          </div>

          {/* Status */}
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: wsConnected ? "#4ade80" : "#ef4444", animation: "pulse 2s infinite" }} />
            <span style={{ fontSize: 9, color: wsConnected ? "#4ade80" : "#ef4444", letterSpacing: "0.2em" }}>
              {wsConnected ? "SYSTEMS ONLINE" : "CONNECTING..."}
            </span>
          </div>
        </div>
      )}

      {/* ── AWAKE SCREEN ───────────────────────────────────────────── */}
      {screen === "awake" && (
        <div style={{ height: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 32, padding: 40 }}>
          <div style={{ position: "fixed", inset: 0, background: "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(99,102,241,0.02) 2px, rgba(99,102,241,0.02) 4px)", pointerEvents: "none" }} />

          {/* Small orb */}
          <div style={{ position: "relative", width: 120, height: 120, cursor: "pointer" }} onClick={toggleRecording}>
            {orbState !== "idle" && <div style={{ position: "absolute", inset: -12, borderRadius: "50%", border: `2px solid ${orbColor[0]}`, opacity: 0.5, animation: "ping 1.5s ease infinite" }} />}
            <div style={{ width: "100%", height: "100%", borderRadius: "50%", background: `radial-gradient(circle at 35% 35%, ${orbColor[1]}, ${orbColor[0]})`, boxShadow: `0 0 40px ${orbColor[0]}88`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 40, transition: "all 0.3s ease" }}>
              {isRecording ? "🔴" : "🤖"}
            </div>
          </div>

          <div style={{ fontSize: 9, color: orbColor[1], letterSpacing: "0.3em", animation: "pulse 2s infinite" }}>
            {isRecording ? "● RECORDING" : orbState === "listening" ? "● LISTENING" : orbState === "speaking" ? "● SPEAKING" : orbState === "thinking" ? "● PROCESSING" : "● STANDBY"}
          </div>

          {/* Recent transcript */}
          <div style={{ maxWidth: 600, textAlign: "center" }}>
            {transcript.slice(-3).map((line, i) => (
              <div key={i} style={{ fontSize: 12, color: line.includes("[JARVIS]") ? "#a5b4fc" : line.includes("[YOU]") ? "#4ade80" : "#475569", marginBottom: 8, opacity: 0.5 + i * 0.25, animation: "fadeIn 0.5s ease" }}>
                {line}
              </div>
            ))}
          </div>

          {/* Wake up agents button */}
          <button onClick={runBriefing} disabled={isBriefing} style={{ background: "transparent", border: "1px solid #6366f166", borderRadius: 4, padding: "12px 32px", color: "#6366f1", fontSize: 11, fontFamily: "monospace", cursor: isBriefing ? "not-allowed" : "pointer", letterSpacing: "0.2em", transition: "all 0.3s" }}
          onMouseEnter={e => { e.currentTarget.style.background="#6366f122"; e.currentTarget.style.borderColor="#6366f1"; }}
          onMouseLeave={e => { e.currentTarget.style.background="transparent"; e.currentTarget.style.borderColor="#6366f166"; }}>
            {isBriefing ? "INITIALIZING..." : "WAKE UP ALL AGENTS"}
          </button>

          {/* Completed agents pills */}
          {completedAgents.length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, justifyContent: "center", maxWidth: 500 }}>
              {completedAgents.map(a => (
                <div key={a} style={{ fontSize: 9, padding: "3px 8px", borderRadius: 3, background: (CATEGORY_COLORS[AGENT_CATEGORIES[a]] || "#6366f1") + "22", color: CATEGORY_COLORS[AGENT_CATEGORIES[a]] || "#6366f1", fontFamily: "monospace", border: `1px solid ${CATEGORY_COLORS[AGENT_CATEGORIES[a]] || "#6366f1"}44` }}>
                  {AGENT_ICONS[MARVEL_NAMES[a] || a]} {MARVEL_NAMES[a] || a}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── AGENT CINEMATIC SCREEN ─────────────────────────────────── */}
      {screen === "agent" && activeAgent && (
        <div style={{ height: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", position: "relative", overflow: "hidden" }}>

          {/* Background glow */}
          <div style={{ position: "absolute", inset: 0, background: `radial-gradient(circle at 50% 50%, ${catColor}11, transparent 70%)`, pointerEvents: "none" }} />

          {/* Scanlines */}
          <div style={{ position: "absolute", inset: 0, background: "repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(0,0,0,0.1) 3px, rgba(0,0,0,0.1) 4px)", pointerEvents: "none" }} />

          {/* Top bar */}
          <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, background: `linear-gradient(90deg, transparent, ${catColor}, transparent)`, animation: "pulse 1s infinite" }} />
          <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: 1, background: `linear-gradient(90deg, transparent, ${catColor}66, transparent)` }} />

          {/* Agent number */}
          <div style={{ position: "absolute", top: 24, left: 24, fontSize: 10, color: "#334155", fontFamily: "monospace", letterSpacing: "0.2em" }}>
            AGENT {String(activeAgent.index + 1).padStart(2, "0")} / 15
          </div>

          {/* Category */}
          <div style={{ position: "absolute", top: 24, right: 24, fontSize: 10, color: catColor, fontFamily: "monospace", letterSpacing: "0.2em", animation: "pulse 2s infinite" }}>
            {activeAgent.category.toUpperCase()}
          </div>

          {/* Progress bar */}
          <div style={{ position: "absolute", top: 0, left: 0, height: 2, width: `${((activeAgent.index + 1) / 15) * 100}%`, background: catColor, transition: "width 0.5s ease" }} />

          {/* Main content */}
          <div style={{ textAlign: "center", animation: "fadeIn 0.5s ease", padding: "0 40px", maxWidth: 700 }}>

            {/* Icon */}
            <div style={{ fontSize: 80, marginBottom: 24, filter: `drop-shadow(0 0 30px ${catColor})` }}>
              {AGENT_ICONS[activeAgent.name] || "🤖"}
            </div>

            {/* Marvel name */}
            <div style={{ fontSize: 32, fontWeight: 700, color: catColor, letterSpacing: "0.2em", textTransform: "uppercase", marginBottom: 4, animation: "glow 2s infinite" }}>
              {MARVEL_NAMES[activeAgent.name] || activeAgent.name}
            </div>

            {/* Real agent name */}
            <div style={{ fontSize: 11, color: "#475569", letterSpacing: "0.2em", marginBottom: 32 }}>
              {activeAgent.name.toUpperCase()}
            </div>

            {/* Status */}
            <div style={{ fontSize: 14, color: activeAgent.status === "Initializing..." ? "#475569" : "#e2e0ff", lineHeight: 1.8, padding: "20px 32px", border: `1px solid ${catColor}33`, borderRadius: 8, background: `${catColor}08`, minHeight: 80, display: "flex", alignItems: "center", justifyContent: "center" }}>
              {activeAgent.status}
            </div>

            {/* Sound bars */}
            {orbState === "speaking" && (
              <div style={{ display: "flex", gap: 4, justifyContent: "center", marginTop: 24 }}>
                {[1,2,3,4,5,6,7].map(i => (
                  <div key={i} style={{ width: 3, borderRadius: 2, background: catColor, animation: `bars ${0.3 + i * 0.1}s ease infinite alternate`, height: 8 }} />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── ALL DONE SCREEN ────────────────────────────────────────── */}
      {screen === "done" && (
        <div style={{ height: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 24, animation: "fadeIn 0.5s ease" }}>
          <div style={{ fontSize: 48, fontWeight: 700, color: "#4ade80", letterSpacing: "0.3em", animation: "glow 2s infinite" }}>ALL ONLINE</div>
          <div style={{ fontSize: 12, color: "#334155", letterSpacing: "0.2em" }}>15 / 15 AGENTS OPERATIONAL</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, justifyContent: "center", maxWidth: 600, marginTop: 16 }}>
            {ALL_AGENTS.map(({ agent, marvel }) => (
              <div key={agent} style={{ fontSize: 9, padding: "3px 8px", borderRadius: 3, background: (CATEGORY_COLORS[AGENT_CATEGORIES[agent]] || "#6366f1") + "22", color: CATEGORY_COLORS[AGENT_CATEGORIES[agent]] || "#6366f1", fontFamily: "monospace" }}>
                {AGENT_ICONS[marvel]} {marvel}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
