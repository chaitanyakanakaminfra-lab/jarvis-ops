import { useState, useEffect, useRef } from "react";

interface AgentStatus {
  agent: string;
  status: string;
  state: "idle" | "checking" | "done";
}

const AGENT_ICONS: Record<string, string> = {
  "CI/CD Pipeline": "⚡",
  "Infrastructure": "☁️",
  "Cloud Costs": "💰",
  "Security": "🔒",
  "Compliance": "📋",
  "Observability": "👁️",
  "Incidents": "🚨",
  "Weekly Report": "📊",
};

function VoiceOrb({ state }: { state: "idle"|"listening"|"speaking"|"thinking" }) {
  const colors = {
    idle:      ["#1a1a3e", "#2a2a5e"],
    listening: ["#0ea5e9", "#38bdf8"],
    speaking:  ["#6366f1", "#818cf8"],
    thinking:  ["#f59e0b", "#fbbf24"],
  };
  const [c1, c2] = colors[state];
  return (
    <div style={{ position: "relative", width: 160, height: 160, margin: "0 auto" }}>
      {state !== "idle" && (
        <div style={{
          position: "absolute", inset: -20, borderRadius: "50%",
          border: `2px solid ${c1}`, opacity: 0.4,
          animation: "ping 1.5s cubic-bezier(0,0,0.2,1) infinite",
        }} />
      )}
      <div style={{
        width: "100%", height: "100%", borderRadius: "50%",
        background: `radial-gradient(circle at 35% 35%, ${c2}, ${c1})`,
        boxShadow: `0 0 40px ${c1}88, 0 0 80px ${c1}44`,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 48, transition: "all 0.3s ease",
      }}>🤖</div>
      <div style={{
        textAlign: "center", marginTop: 12, fontSize: 12, color: c2,
        fontFamily: "monospace", letterSpacing: "0.2em", textTransform: "uppercase",
      }}>
        {state === "idle" && "STANDBY"}
        {state === "listening" && "LISTENING"}
        {state === "speaking" && "SPEAKING"}
        {state === "thinking" && "PROCESSING"}
      </div>
    </div>
  );
}

function AgentCard({ agent }: { agent: AgentStatus }) {
  const stateColors = {
    idle:     { border: "#1e293b", text: "#475569", bg: "transparent" },
    checking: { border: "#f59e0b", text: "#fbbf24", bg: "#7c3aed11" },
    done:     { border: "#6366f1", text: "#a5b4fc", bg: "#6366f111" },
  };
  const { border, text, bg } = stateColors[agent.state];
  return (
    <div style={{
      border: `1px solid ${border}`, borderRadius: 8,
      padding: "10px 14px", background: bg,
      transition: "all 0.3s ease", marginBottom: 6,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ fontSize: 18 }}>{AGENT_ICONS[agent.agent] || "🤖"}</span>
        <div style={{ flex: 1 }}>
          <div style={{
            fontSize: 12, fontWeight: 700, color: text,
            fontFamily: "monospace", letterSpacing: "0.05em",
          }}>
            {agent.agent.toUpperCase()}
          </div>
          {agent.state === "checking" && (
            <div style={{ fontSize: 11, color: "#f59e0b", marginTop: 2 }}>⟳ Checking...</div>
          )}
          {agent.state === "done" && agent.status && (
            <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>
              {agent.status.length > 80 ? agent.status.slice(0, 80) + "..." : agent.status}
            </div>
          )}
        </div>
        <div style={{
          fontSize: 10, padding: "2px 6px", borderRadius: 3,
          background: agent.state === "done" ? "#6366f122" : agent.state === "checking" ? "#f59e0b22" : "#1e293b",
          color: agent.state === "done" ? "#6366f1" : agent.state === "checking" ? "#f59e0b" : "#334155",
          fontFamily: "monospace",
        }}>
          {agent.state === "done" ? "DONE" : agent.state === "checking" ? "ACTIVE" : "IDLE"}
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const JARVIS_API = `http://${window.location.hostname}:8000`;
  const [orbState, setOrbState] = useState<"idle"|"listening"|"speaking"|"thinking">("idle");
  const [agents, setAgents] = useState<AgentStatus[]>([
    { agent: "CI/CD Pipeline", status: "", state: "idle" },
    { agent: "Infrastructure",  status: "", state: "idle" },
    { agent: "Cloud Costs",     status: "", state: "idle" },
    { agent: "Security",        status: "", state: "idle" },
    { agent: "Compliance",      status: "", state: "idle" },
    { agent: "Observability",   status: "", state: "idle" },
    { agent: "Incidents",       status: "", state: "idle" },
    { agent: "Weekly Report",   status: "", state: "idle" },
  ]);
  const [transcript, setTranscript] = useState<string[]>([]);
  const [isBriefing, setIsBriefing] = useState(false);
  const [inputCmd, setInputCmd]     = useState("");
  const transcriptRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (transcriptRef.current)
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
  }, [transcript]);

  function addTranscript(role: string, text: string) {
    const time = new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
    setTranscript(prev => [...prev.slice(-50), `${time} [${role.toUpperCase()}]: ${text}`]);
  }

  function updateAgent(name: string, state: AgentStatus["state"], status: string) {
    setAgents(prev => prev.map(a => a.agent === name ? { ...a, state, status } : a));
  }

  async function runBriefing() {
    setIsBriefing(true);
    setOrbState("thinking");
    addTranscript("you", "Jarvis, wake up");
    setAgents(prev => prev.map(a => ({ ...a, state: "idle", status: "" })));

    const commands = [
      { agent: "CI/CD Pipeline", cmd: "pipeline status" },
      { agent: "Infrastructure",  cmd: "check the cluster" },
      { agent: "Cloud Costs",     cmd: "how are cloud costs" },
      { agent: "Security",        cmd: "scan for vulnerabilities" },
      { agent: "Compliance",      cmd: "run compliance check" },
      { agent: "Observability",   cmd: "hows the system" },
      { agent: "Incidents",       cmd: "any active incidents" },
      { agent: "Weekly Report",   cmd: "weekly summary" },
    ];

    const hour = new Date().getHours();
    const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
    addTranscript("jarvis", `${greeting} Chaitanya. All systems online. Running morning briefing...`);
    setOrbState("speaking");
    await new Promise(r => setTimeout(r, 1000));

    for (const { agent, cmd } of commands) {
      setOrbState("thinking");
      updateAgent(agent, "checking", "");
      addTranscript("jarvis", `Checking ${agent}...`);
      try {
        const res  = await fetch(`${JARVIS_API}/agents/run`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ command: cmd }),
        });
        const data = await res.json();
        const status = data.response || "Status unavailable";
        updateAgent(agent, "done", status);
        setOrbState("speaking");
        addTranscript("jarvis", `${agent}: ${status}`);
        await new Promise(r => setTimeout(r, 600));
      } catch {
        updateAgent(agent, "done", "Unavailable");
        addTranscript("system", `${agent}: Could not reach agent`);
      }
    }

    setOrbState("speaking");
    addTranscript("jarvis", "Morning briefing complete. All systems checked. Ready for your commands, Chaitanya.");
    await new Promise(r => setTimeout(r, 2000));
    setOrbState("idle");
    setIsBriefing(false);
  }

  async function sendCommand(command: string) {
    if (!command.trim()) return;
    addTranscript("you", command);
    setOrbState("thinking");
    try {
      const res  = await fetch(`${JARVIS_API}/agents/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command }),
      });
      const data = await res.json();
      setOrbState("speaking");
      addTranscript("jarvis", data.response);
      setTimeout(() => setOrbState("idle"), 2000);
    } catch {
      addTranscript("system", "Error connecting to Jarvis API");
      setOrbState("idle");
    }
  }

  const doneCount = agents.filter(a => a.state === "done").length;

  return (
    <div style={{
      background: "#050510", minHeight: "100vh", color: "#e2e0ff",
      fontFamily: "'JetBrains Mono', monospace", padding: 20,
    }}>
      <style>{`
        @keyframes ping { 75%, 100% { transform: scale(2); opacity: 0; } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        * { box-sizing: border-box; }
        body { margin: 0; background: #050510; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: #0f0f1a; }
        ::-webkit-scrollbar-thumb { background: #6366f1; border-radius: 2px; }
      `}</style>

      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        marginBottom: 24, borderBottom: "1px solid #1e293b", paddingBottom: 16,
      }}>
        <div>
          <div style={{ fontSize: 28, fontWeight: 700, color: "#6366f1", letterSpacing: "0.4em" }}>
            J.A.R.V.I.S
          </div>
          <div style={{ fontSize: 10, color: "#334155", letterSpacing: "0.15em", marginTop: 2 }}>
            JUST A RATHER VERY INTELLIGENT SYSTEM · 15 AGENTS · AWS EKS
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 20, color: "#6366f1", fontWeight: 700 }}>
            {doneCount}/{agents.length}
          </div>
          <div style={{ fontSize: 10, color: "#475569", letterSpacing: "0.1em" }}>
            AGENTS CHECKED
          </div>
          <div style={{ fontSize: 11, color: "#4ade80", marginTop: 6, animation: "pulse 2s infinite" }}>
            ● ONLINE
          </div>
        </div>
      </div>

      {/* Main grid */}
      <div style={{ display: "grid", gridTemplateColumns: "220px 1fr 1fr", gap: 20 }}>

        {/* Left — Orb + controls */}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
          <VoiceOrb state={orbState} />

          <button onClick={runBriefing} disabled={isBriefing} style={{
            background: isBriefing ? "#1e293b" : "linear-gradient(135deg, #6366f1, #4f46e5)",
            border: "none", borderRadius: 8, padding: "12px 16px",
            color: isBriefing ? "#475569" : "#fff", fontSize: 12,
            fontFamily: "monospace", fontWeight: 700,
            cursor: isBriefing ? "not-allowed" : "pointer",
            letterSpacing: "0.08em", width: "100%",
          }}>
            {isBriefing ? "⟳ RUNNING..." : "🌅 JARVIS WAKE UP"}
          </button>

          <div style={{ width: "100%", borderTop: "1px solid #1e293b", paddingTop: 12 }}>
            <div style={{ fontSize: 10, color: "#334155", marginBottom: 8, letterSpacing: "0.1em" }}>
              QUICK COMMANDS
            </div>
            {[
              ["💰", "how are cloud costs"],
              ["☁️", "check the cluster"],
              ["🔒", "scan for vulnerabilities"],
              ["📊", "weekly summary"],
              ["🚨", "we have an incident"],
            ].map(([icon, cmd]) => (
              <button key={cmd} onClick={() => sendCommand(cmd)} style={{
                display: "block", width: "100%", background: "transparent",
                border: "1px solid #1e293b", borderRadius: 6,
                padding: "7px 10px", color: "#64748b", fontSize: 10,
                fontFamily: "monospace", cursor: "pointer",
                textAlign: "left", marginBottom: 4,
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor="#6366f1"; e.currentTarget.style.color="#a5b4fc"; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor="#1e293b"; e.currentTarget.style.color="#64748b"; }}
              >
                {icon} {cmd}
              </button>
            ))}
          </div>
        </div>

        {/* Middle — Agent cards */}
        <div>
          <div style={{ fontSize: 10, color: "#475569", marginBottom: 8, letterSpacing: "0.1em" }}>
            AGENT STATUS
          </div>
          <div style={{ height: 4, background: "#1e293b", borderRadius: 2, marginBottom: 14 }}>
            <div style={{
              height: "100%",
              width: `${(doneCount / agents.length) * 100}%`,
              background: "linear-gradient(90deg, #6366f1, #a78bfa)",
              borderRadius: 2, transition: "width 0.5s ease",
            }} />
          </div>
          {agents.map(agent => <AgentCard key={agent.agent} agent={agent} />)}
        </div>

        {/* Right — Transcript */}
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ fontSize: 10, color: "#475569", marginBottom: 8, letterSpacing: "0.1em" }}>
            LIVE TRANSCRIPT
          </div>
          <div ref={transcriptRef} style={{
            flex: 1, height: 420, overflowY: "auto",
            background: "#080814", border: "1px solid #1e293b",
            borderRadius: 8, padding: 12, marginBottom: 10,
          }}>
            {transcript.length === 0 && (
              <div style={{ color: "#334155", fontSize: 11, fontStyle: "italic" }}>
                Click "JARVIS WAKE UP" to start morning briefing...
              </div>
            )}
            {transcript.map((line, i) => (
              <div key={i} style={{
                fontSize: 11, marginBottom: 5, lineHeight: 1.5,
                color: line.includes("[JARVIS]") ? "#a5b4fc"
                     : line.includes("[YOU]")    ? "#4ade80"
                     : "#475569",
              }}>
                {line}
              </div>
            ))}
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <input
              value={inputCmd}
              onChange={e => setInputCmd(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && inputCmd.trim()) { sendCommand(inputCmd); setInputCmd(""); }}}
              placeholder="Type a command to Jarvis..."
              style={{
                flex: 1, background: "#0f0f1a", border: "1px solid #1e293b",
                borderRadius: 6, padding: "8px 12px", color: "#e2e0ff",
                fontSize: 11, fontFamily: "monospace", outline: "none",
              }}
            />
            <button onClick={() => { if (inputCmd.trim()) { sendCommand(inputCmd); setInputCmd(""); }}} style={{
              background: "#6366f1", border: "none", borderRadius: 6,
              padding: "8px 14px", color: "#fff", fontSize: 11,
              fontFamily: "monospace", cursor: "pointer", fontWeight: 700,
            }}>
              ▶
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
