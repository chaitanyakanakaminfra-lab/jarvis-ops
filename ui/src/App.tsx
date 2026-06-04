import { useState, useEffect, useRef } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────
interface AgentStatus {
  agent: string;
  status: string;
  state: "idle" | "checking" | "done";
}

interface BriefingMessage {
  type: string;
  agent?: string;
  status?: string;
  message?: string;
  index?: number;
  total_agents?: number;
  results?: AgentStatus[];
}

// ── Agent icons ───────────────────────────────────────────────────────────────
const AGENT_ICONS: Record<string, string> = {
  "CI/CD Pipeline":   "⚡",
  "Infrastructure":   "☁️",
  "Cloud Costs":      "💰",
  "Security":         "🔒",
  "Compliance":       "📋",
  "Observability":    "👁️",
  "Incidents":        "🚨",
  "Weekly Report":    "📊",
};

// ── Voice Orb ─────────────────────────────────────────────────────────────────
function VoiceOrb({ state }: { state: "idle" | "listening" | "speaking" | "thinking" }) {
  const colors = {
    idle:      ["#1a1a3e", "#2a2a5e"],
    listening: ["#0ea5e9", "#38bdf8"],
    speaking:  ["#6366f1", "#818cf8"],
    thinking:  ["#f59e0b", "#fbbf24"],
  };

  const [c1, c2] = colors[state];

  return (
    <div style={{
      position: "relative",
      width: 160,
      height: 160,
      margin: "0 auto",
    }}>
      {/* Outer ring */}
      {state !== "idle" && (
        <div style={{
          position: "absolute",
          inset: -20,
          borderRadius: "50%",
          border: `2px solid ${c1}`,
          opacity: 0.4,
          animation: "ping 1.5s cubic-bezier(0,0,0.2,1) infinite",
        }} />
      )}
      {/* Inner orb */}
      <div style={{
        width: "100%",
        height: "100%",
        borderRadius: "50%",
        background: `radial-gradient(circle at 35% 35%, ${c2}, ${c1})`,
        boxShadow: `0 0 40px ${c1}88, 0 0 80px ${c1}44`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 48,
        transition: "all 0.3s ease",
      }}>
        🤖
      </div>
      {/* State label */}
      <div style={{
        textAlign: "center",
        marginTop: 12,
        fontSize: 12,
        color: c2,
        fontFamily: "monospace",
        letterSpacing: "0.2em",
        textTransform: "uppercase",
      }}>
        {state === "idle"      && "STANDBY"}
        {state === "listening" && "LISTENING"}
        {state === "speaking"  && "SPEAKING"}
        {state === "thinking"  && "PROCESSING"}
      </div>
    </div>
  );
}

// ── Agent Card ────────────────────────────────────────────────────────────────
function AgentCard({ agent }: { agent: AgentStatus }) {
  const stateColors = {
    idle:     { border: "#1e293b", text: "#475569", bg: "transparent" },
    checking: { border: "#f59e0b", text: "#fbbf24", bg: "#7c3aed11" },
    done:     { border: "#6366f1", text: "#a5b4fc", bg: "#6366f111" },
  };
  const { border, text, bg } = stateColors[agent.state];

  return (
    <div style={{
      border: `1px solid ${border}`,
      borderRadius: 8,
      padding: "10px 14px",
      background: bg,
      transition: "all 0.3s ease",
      marginBottom: 6,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ fontSize: 18 }}>
          {AGENT_ICONS[agent.agent] || "🤖"}
        </span>
        <div style={{ flex: 1 }}>
          <div style={{
            fontSize: 12,
            fontWeight: 700,
            color: text,
            fontFamily: "monospace",
            letterSpacing: "0.05em",
          }}>
            {agent.agent.toUpperCase()}
          </div>
          {agent.state === "checking" && (
            <div style={{ fontSize: 11, color: "#f59e0b", marginTop: 2 }}>
              ⟳ Checking...
            </div>
          )}
          {agent.state === "done" && agent.status && (
            <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>
              {agent.status.length > 80
                ? agent.status.slice(0, 80) + "..."
                : agent.status}
            </div>
          )}
        </div>
        <div style={{
          fontSize: 10,
          padding: "2px 6px",
          borderRadius: 3,
          background: agent.state === "done"
            ? "#6366f122" : agent.state === "checking"
            ? "#f59e0b22" : "#1e293b",
          color: agent.state === "done"
            ? "#6366f1" : agent.state === "checking"
            ? "#f59e0b" : "#334155",
          fontFamily: "monospace",
        }}>
          {agent.state === "done"      ? "DONE"
           : agent.state === "checking" ? "ACTIVE"
           : "IDLE"}
        </div>
      </div>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const JARVIS_WS  = "ws://localhost:8080/voice/stream";
  const JARVIS_API = "http://localhost:8000";

  const [orbState,   setOrbState]   = useState<"idle"|"listening"|"speaking"|"thinking">("idle");
  const [agents,     setAgents]     = useState<AgentStatus[]>([
    { agent: "CI/CD Pipeline",  status: "", state: "idle" },
    { agent: "Infrastructure",  status: "", state: "idle" },
    { agent: "Cloud Costs",     status: "", state: "idle" },
    { agent: "Security",        status: "", state: "idle" },
    { agent: "Compliance",      status: "", state: "idle" },
    { agent: "Observability",   status: "", state: "idle" },
    { agent: "Incidents",       status: "", state: "idle" },
    { agent: "Weekly Report",   status: "", state: "idle" },
  ]);
  const [transcript, setTranscript] = useState<string[]>([]);
  const [isConnected,setIsConnected]= useState(false);
  const [isBriefing, setIsBriefing] = useState(false);
  const wsRef       = useRef<WebSocket | null>(null);
  const transcriptRef = useRef<HTMLDivElement>(null);

  // Auto-scroll transcript
  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
    }
  }, [transcript]);

  // WebSocket connection
  useEffect(() => {
    connectWS();
    return () => wsRef.current?.close();
  }, []);

  function connectWS() {
    try {
      const ws = new WebSocket(JARVIS_WS);
      ws.onopen    = () => { setIsConnected(true); addTranscript("system", "Connected to Jarvis"); };
      ws.onclose   = () => { setIsConnected(false); setTimeout(connectWS, 3000); };
      ws.onerror   = () => setIsConnected(false);
      ws.onmessage = (e) => handleMessage(JSON.parse(e.data));
      wsRef.current = ws;
    } catch {
      setTimeout(connectWS, 3000);
    }
  }

  function handleMessage(msg: BriefingMessage) {
    switch (msg.type) {
      case "briefing_start":
        setIsBriefing(true);
        setOrbState("speaking");
        addTranscript("jarvis", msg.message || "");
        break;

      case "agent_checking":
        setOrbState("thinking");
        updateAgent(msg.agent!, "checking", "");
        break;

      case "agent_done":
        setOrbState("speaking");
        updateAgent(msg.agent!, "done", msg.status || "");
        addTranscript("jarvis", `${msg.agent}: ${msg.status}`);
        break;

      case "briefing_complete":
        setIsBriefing(false);
        setOrbState("idle");
        addTranscript("jarvis", msg.message || "Briefing complete.");
        break;

      case "response":
        setOrbState("speaking");
        addTranscript("jarvis", msg.message || "");
        setTimeout(() => setOrbState("idle"), 2000);
        break;

      case "status":
        if (msg.message === "processing") setOrbState("thinking");
        break;
    }
  }

  function updateAgent(name: string, state: AgentStatus["state"], status: string) {
    setAgents(prev => prev.map(a =>
      a.agent === name ? { ...a, state, status } : a
    ));
  }

  function addTranscript(role: string, text: string) {
    setTranscript(prev => [...prev.slice(-50), `[${role.toUpperCase()}]: ${text}`]);
  }

  async function triggerBriefing() {
    setIsBriefing(true);
    setOrbState("thinking");
    addTranscript("you", "Jarvis, wake up");

    // Reset all agents
    setAgents(prev => prev.map(a => ({ ...a, state: "idle", status: "" })));

    try {
      const res  = await fetch(`${JARVIS_API}/agents/run`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ command: "morning briefing" }),
      });
      const data = await res.json();
      setOrbState("speaking");
      addTranscript("jarvis", data.response);
      setTimeout(() => setOrbState("idle"), 3000);
    } catch {
      addTranscript("system", "Could not connect to Jarvis API");
      setOrbState("idle");
    }
    setIsBriefing(false);
  }

  async function sendCommand(command: string) {
    if (!command.trim()) return;
    addTranscript("you", command);
    setOrbState("thinking");
    try {
      const res  = await fetch(`${JARVIS_API}/agents/run`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ command }),
      });
      const data = await res.json();
      setOrbState("speaking");
      addTranscript("jarvis", data.response);
      setTimeout(() => setOrbState("idle"), 2000);
    } catch {
      addTranscript("system", "Error connecting to Jarvis");
      setOrbState("idle");
    }
  }

  const [inputCmd, setInputCmd] = useState("");

  return (
    <div style={{
      background: "#050510",
      minHeight: "100vh",
      color: "#e2e0ff",
      fontFamily: "'JetBrains Mono', monospace",
      padding: 20,
    }}>
      <style>{`
        @keyframes ping {
          75%, 100% { transform: scale(2); opacity: 0; }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>

      {/* Header */}
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        marginBottom: 24,
        borderBottom: "1px solid #1e293b",
        paddingBottom: 16,
      }}>
        <div>
          <div style={{ fontSize: 24, fontWeight: 700, color: "#6366f1" }}>
            J.A.R.V.I.S
          </div>
          <div style={{ fontSize: 11, color: "#475569", letterSpacing: "0.2em" }}>
            JUST A RATHER VERY INTELLIGENT SYSTEM
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{
            width: 8, height: 8, borderRadius: "50%",
            background: isConnected ? "#4ade80" : "#ef4444",
            animation: isConnected ? "pulse 2s infinite" : "none",
          }} />
          <span style={{ fontSize: 11, color: isConnected ? "#4ade80" : "#ef4444" }}>
            {isConnected ? "ONLINE" : "OFFLINE"}
          </span>
        </div>
      </div>

      {/* Main grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 20 }}>

        {/* Left — Orb + controls */}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 24 }}>
          <VoiceOrb state={orbState} />

          {/* Wake up button */}
          <button
            onClick={triggerBriefing}
            disabled={isBriefing}
            style={{
              background: isBriefing
                ? "#1e293b"
                : "linear-gradient(135deg, #6366f1, #4f46e5)",
              border: "none",
              borderRadius: 8,
              padding: "12px 24px",
              color: isBriefing ? "#475569" : "#fff",
              fontSize: 13,
              fontFamily: "monospace",
              fontWeight: 700,
              cursor: isBriefing ? "not-allowed" : "pointer",
              letterSpacing: "0.1em",
              width: "100%",
              transition: "all 0.2s",
            }}
          >
            {isBriefing ? "⟳ BRIEFING..." : "🌅 JARVIS WAKE UP"}
          </button>

          {/* Quick commands */}
          <div style={{ width: "100%" }}>
            <div style={{ fontSize: 10, color: "#475569", marginBottom: 8, letterSpacing: "0.1em" }}>
              QUICK COMMANDS
            </div>
            {[
              "how are cloud costs",
              "check the cluster",
              "scan for vulnerabilities",
              "weekly summary",
            ].map(cmd => (
              <button
                key={cmd}
                onClick={() => sendCommand(cmd)}
                style={{
                  display: "block",
                  width: "100%",
                  background: "transparent",
                  border: "1px solid #1e293b",
                  borderRadius: 6,
                  padding: "8px 12px",
                  color: "#64748b",
                  fontSize: 11,
                  fontFamily: "monospace",
                  cursor: "pointer",
                  textAlign: "left",
                  marginBottom: 4,
                  transition: "all 0.15s",
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.borderColor = "#6366f1";
                  e.currentTarget.style.color = "#a5b4fc";
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.borderColor = "#1e293b";
                  e.currentTarget.style.color = "#64748b";
                }}
              >
                ▸ {cmd}
              </button>
            ))}
          </div>
        </div>

        {/* Middle — Agent status cards */}
        <div>
          <div style={{ fontSize: 10, color: "#475569", marginBottom: 12, letterSpacing: "0.1em" }}>
            AGENT STATUS — {agents.filter(a => a.state === "done").length}/{agents.length} CHECKED
          </div>
          {/* Progress bar */}
          <div style={{
            height: 3,
            background: "#1e293b",
            borderRadius: 2,
            marginBottom: 16,
          }}>
            <div style={{
              height: "100%",
              width: `${(agents.filter(a => a.state === "done").length / agents.length) * 100}%`,
              background: "linear-gradient(90deg, #6366f1, #a78bfa)",
              borderRadius: 2,
              transition: "width 0.5s ease",
            }} />
          </div>
          {agents.map(agent => (
            <AgentCard key={agent.agent} agent={agent} />
          ))}
        </div>

        {/* Right — Live transcript */}
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ fontSize: 10, color: "#475569", marginBottom: 12, letterSpacing: "0.1em" }}>
            LIVE TRANSCRIPT
          </div>

          {/* Transcript feed */}
          <div
            ref={transcriptRef}
            style={{
              flex: 1,
              height: 400,
              overflowY: "auto",
              background: "#080814",
              border: "1px solid #1e293b",
              borderRadius: 8,
              padding: 12,
              marginBottom: 12,
            }}
          >
            {transcript.length === 0 && (
              <div style={{ color: "#334155", fontSize: 11, fontStyle: "italic" }}>
                Say "Jarvis wake up" or click the button to start...
              </div>
            )}
            {transcript.map((line, i) => (
              <div key={i} style={{
                fontSize: 11,
                marginBottom: 6,
                color: line.startsWith("[JARVIS]")
                  ? "#a5b4fc"
                  : line.startsWith("[YOU]")
                  ? "#4ade80"
                  : "#475569",
                lineHeight: 1.5,
              }}>
                {line}
              </div>
            ))}
          </div>

          {/* Manual command input */}
          <div style={{ display: "flex", gap: 8 }}>
            <input
              value={inputCmd}
              onChange={e => setInputCmd(e.target.value)}
              onKeyDown={e => {
                if (e.key === "Enter" && inputCmd.trim()) {
                  sendCommand(inputCmd);
                  setInputCmd("");
                }
              }}
              placeholder="Type a command..."
              style={{
                flex: 1,
                background: "#0f0f1a",
                border: "1px solid #1e293b",
                borderRadius: 6,
                padding: "8px 12px",
                color: "#e2e0ff",
                fontSize: 12,
                fontFamily: "monospace",
                outline: "none",
              }}
            />
            <button
              onClick={() => {
                if (inputCmd.trim()) {
                  sendCommand(inputCmd);
                  setInputCmd("");
                }
              }}
              style={{
                background: "#6366f1",
                border: "none",
                borderRadius: 6,
                padding: "8px 16px",
                color: "#fff",
                fontSize: 12,
                fontFamily: "monospace",
                cursor: "pointer",
              }}
            >
              SEND
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
