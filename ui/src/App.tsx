import { useState, useEffect, useRef } from "react";

interface AgentStatus {
  agent: string;
  status: string;
  state: "idle" | "checking" | "done";
  category: string;
}

const AGENT_ICONS: Record<string, string> = {
  "CI/CD Pipeline": "⚡",
  "Lint & Code Quality": "🔍",
  "Docker & Image": "🐳",
  "Release & Versioning": "🏷️",
  "Infra Provisioning": "🏗️",
  "Kubernetes Ops": "☸️",
  "Cloud Config": "☁️",
  "DR & Backup": "💾",
  "Cost Optimization": "💰",
  "Auto-Scaling": "📈",
  "Security Scanning": "🔒",
  "Compliance": "📋",
  "Observability": "👁️",
  "Incident Response": "🚨",
  "Reporting": "📊",
};

const CATEGORY_COLORS: Record<string, string> = {
  "CI/CD": "#22d3ee",
  "Infrastructure": "#818cf8",
  "Cost": "#fb923c",
  "Security": "#f87171",
  "Observability": "#4ade80",
  "Intelligence": "#a78bfa",
};

const ALL_AGENTS = [
  { agent: "CI/CD Pipeline", cmd: "run the pipeline", category: "CI/CD" },
  { agent: "Lint & Code Quality", cmd: "run ruff", category: "CI/CD" },
  { agent: "Docker & Image", cmd: "mirror the images", category: "CI/CD" },
  { agent: "Release & Versioning", cmd: "what is the latest version", category: "CI/CD" },
  { agent: "Infra Provisioning", cmd: "plan the infra", category: "Infrastructure" },
  { agent: "Kubernetes Ops", cmd: "check the cluster", category: "Infrastructure" },
  { agent: "Cloud Config", cmd: "audit cloud config", category: "Infrastructure" },
  { agent: "DR & Backup", cmd: "run a backup", category: "Infrastructure" },
  { agent: "Cost Optimization", cmd: "how are cloud costs", category: "Cost" },
  { agent: "Auto-Scaling", cmd: "scaling status", category: "Cost" },
  { agent: "Security Scanning", cmd: "scan for vulnerabilities", category: "Security" },
  { agent: "Compliance", cmd: "run compliance check", category: "Security" },
  { agent: "Observability", cmd: "hows the system", category: "Observability" },
  { agent: "Incident Response", cmd: "any active incidents", category: "Observability" },
  { agent: "Reporting", cmd: "weekly summary", category: "Intelligence" },
];

function VoiceOrb({ state }: { state: "idle"|"listening"|"speaking"|"thinking" }) {
  const colors = {
    idle: ["#1a1a3e", "#2a2a5e"],
    listening: ["#0ea5e9", "#38bdf8"],
    speaking: ["#6366f1", "#818cf8"],
    thinking: ["#f59e0b", "#fbbf24"],
  };
  const [c1, c2] = colors[state];
  return (
    <div style={{ position: "relative", width: 140, height: 140, margin: "0 auto" }}>
      {state !== "idle" && (
        <div style={{
          position: "absolute", inset: -16, borderRadius: "50%",
          border: `2px solid ${c1}`, opacity: 0.4,
          animation: "ping 1.5s cubic-bezier(0,0,0.2,1) infinite",
        }} />
      )}
      <div style={{
        width: "100%", height: "100%", borderRadius: "50%",
        background: `radial-gradient(circle at 35% 35%, ${c2}, ${c1})`,
        boxShadow: `0 0 40px ${c1}88, 0 0 80px ${c1}44`,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 44, transition: "all 0.3s ease",
      }}>🤖</div>
      <div style={{
        textAlign: "center", marginTop: 10, fontSize: 11, color: c2,
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
  const catColor = CATEGORY_COLORS[agent.category] || "#6366f1";
  const stateColors = {
    idle: { border: "#1e293b", text: "#475569", bg: "transparent" },
    checking: { border: "#f59e0b", text: "#fbbf24", bg: "#f59e0b08" },
    done: { border: catColor + "66", text: catColor, bg: catColor + "08" },
  };
  const { border, text, bg } = stateColors[agent.state];
  return (
    <div style={{
      border: `1px solid ${border}`, borderRadius: 6,
      padding: "8px 10px", background: bg,
      transition: "all 0.3s ease", marginBottom: 4,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ fontSize: 14, flexShrink: 0 }}>{AGENT_ICONS[agent.agent] || "🤖"}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontSize: 10, fontWeight: 700, color: text,
            fontFamily: "monospace", letterSpacing: "0.04em",
            whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
          }}>
            {agent.agent.toUpperCase()}
          </div>
          {agent.state === "checking" && (
            <div style={{ fontSize: 10, color: "#f59e0b", marginTop: 1 }}>Checking...</div>
          )}
          {agent.state === "done" && agent.status && (
            <div style={{ fontSize: 10, color: "#64748b", marginTop: 1, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {agent.status.length > 55 ? agent.status.slice(0, 55) + "..." : agent.status}
            </div>
          )}
        </div>
        <div style={{
          fontSize: 9, padding: "2px 5px", borderRadius: 3, flexShrink: 0,
          background: agent.state === "done" ? catColor + "22" : agent.state === "checking" ? "#f59e0b22" : "#1e293b",
          color: agent.state === "done" ? catColor : agent.state === "checking" ? "#f59e0b" : "#334155",
          fontFamily: "monospace",
        }}>
          {agent.state === "done" ? "✓" : agent.state === "checking" ? "..." : "—"}
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const JARVIS_API = `http://${window.location.hostname}:8000`;
  const [orbState, setOrbState] = useState<"idle"|"listening"|"speaking"|"thinking">("idle");
  const [agents, setAgents] = useState<AgentStatus[]>(
    ALL_AGENTS.map(a => ({ ...a, status: "", state: "idle" as const }))
  );
  const [transcript, setTranscript] = useState<string[]>([]);
  const [isBriefing, setIsBriefing] = useState(false);
  const [inputCmd, setInputCmd] = useState("");
  const transcriptRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (transcriptRef.current)
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
  }, [transcript]);

  function addTranscript(role: string, text: string) {
    const time = new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
    setTranscript(prev => [...prev.slice(-100), `${time} [${role.toUpperCase()}]: ${text}`]);
  }

  function updateAgent(name: string, state: AgentStatus["state"], status: string) {
    setAgents(prev => prev.map(a => a.agent === name ? { ...a, state, status } : a));
  }

  async function runBriefing() {
    setIsBriefing(true);
    setOrbState("thinking");
    addTranscript("you", "Jarvis, wake up");
    setAgents(prev => prev.map(a => ({ ...a, state: "idle", status: "" })));
    const hour = new Date().getHours();
    const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
    addTranscript("jarvis", `${greeting} Chaitanya. All 15 systems online. Running full briefing...`);
    setOrbState("speaking");
    await new Promise(r => setTimeout(r, 800));
    for (const { agent, cmd } of ALL_AGENTS) {
      setOrbState("thinking");
      updateAgent(agent, "checking", "");
      addTranscript("jarvis", `Checking ${agent}...`);
      try {
        const res = await fetch(`${JARVIS_API}/agents/run`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ command: cmd }),
        });
        const data = await res.json();
        const status = data.response || "Status unavailable";
        updateAgent(agent, "done", status);
        setOrbState("speaking");
        addTranscript("jarvis", `${agent}: ${status}`);
        await new Promise(r => setTimeout(r, 500));
      } catch {
        updateAgent(agent, "done", "Unavailable");
        addTranscript("system", `${agent}: Could not reach agent`);
      }
    }
    setOrbState("speaking");
    addTranscript("jarvis", "Full briefing complete. All 15 agents checked. Ready for your commands, Chaitanya.");
    await new Promise(r => setTimeout(r, 2000));
    setOrbState("idle");
    setIsBriefing(false);
  }

  async function sendCommand(command: string) {
    if (!command.trim()) return;
    addTranscript("you", command);
    setOrbState("thinking");
    try {
      const res = await fetch(`${JARVIS_API}/agents/run`, {
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
      fontFamily: "JetBrains Mono, monospace", padding: "16px 20px",
    }}>
      <style>{`
        @keyframes ping { 75%, 100% { transform: scale(2); opacity: 0; } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        * { box-sizing: border-box; }
        body { margin: 0; background: #050510; }
        ::-webkit-scrollbar { width: 3px; }
        ::-webkit-scrollbar-thumb { background: #6366f1; border-radius: 2px; }
      `}</style>

      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        marginBottom: 16, borderBottom: "1px solid #1e293b", paddingBottom: 12,
      }}>
        <div>
          <div style={{ fontSize: 24, fontWeight: 700, color: "#6366f1", letterSpacing: "0.4em" }}>J.A.R.V.I.S</div>
          <div style={{ fontSize: 9, color: "#334155", letterSpacing: "0.12em", marginTop: 2 }}>
            JUST A RATHER VERY INTELLIGENT SYSTEM · 15 AGENTS · AWS EKS
          </div>
        </div>
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 22, color: "#6366f1", fontWeight: 700 }}>{doneCount}</div>
            <div style={{ fontSize: 9, color: "#334155" }}>/ 15 CHECKED</div>
          </div>
          <div style={{ fontSize: 11, color: "#4ade80", animation: "pulse 2s infinite" }}>● ONLINE</div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "180px 1fr 1fr 260px", gap: 16 }}>

        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
          <VoiceOrb state={orbState} />
          <button onClick={runBriefing} disabled={isBriefing} style={{
            background: isBriefing ? "#1e293b" : "linear-gradient(135deg, #6366f1, #4f46e5)",
            border: "none", borderRadius: 8, padding: "10px 12px",
            color: isBriefing ? "#475569" : "#fff", fontSize: 11,
            fontFamily: "monospace", fontWeight: 700,
            cursor: isBriefing ? "not-allowed" : "pointer",
            letterSpacing: "0.08em", width: "100%",
          }}>
            {isBriefing ? "BRIEFING..." : "JARVIS WAKE UP"}
          </button>
          <div style={{ width: "100%", borderTop: "1px solid #1e293b", paddingTop: 10 }}>
            <div style={{ fontSize: 9, color: "#334155", marginBottom: 6, letterSpacing: "0.1em" }}>QUICK COMMANDS</div>
            {[
              ["how are cloud costs"],
              ["check the cluster"],
              ["scan for vulnerabilities"],
              ["weekly summary"],
              ["we have an incident"],
              ["plan the infra"],
              ["mirror the images"],
              ["cut a release"],
            ].map(([cmd]) => (
              <button key={cmd} onClick={() => sendCommand(cmd)} style={{
                display: "block", width: "100%", background: "transparent",
                border: "1px solid #1e293b", borderRadius: 4,
                padding: "5px 8px", color: "#475569", fontSize: 9,
                fontFamily: "monospace", cursor: "pointer",
                textAlign: "left", marginBottom: 3,
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor="#6366f1"; e.currentTarget.style.color="#a5b4fc"; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor="#1e293b"; e.currentTarget.style.color="#475569"; }}
              >
                {cmd}
              </button>
            ))}
          </div>
        </div>

        <div>
          {["CI/CD", "Infrastructure"].map(cat => (
            <div key={cat} style={{ marginBottom: 12 }}>
              <div style={{
                fontSize: 9, fontWeight: 700, color: CATEGORY_COLORS[cat],
                letterSpacing: "0.1em", marginBottom: 6,
                borderBottom: `1px solid ${CATEGORY_COLORS[cat]}22`, paddingBottom: 3,
              }}>
                {cat.toUpperCase()}
              </div>
              {agents.filter(a => a.category === cat).map(a => <AgentCard key={a.agent} agent={a} />)}
            </div>
          ))}
        </div>

        <div>
          {["Cost", "Security", "Observability", "Intelligence"].map(cat => (
            <div key={cat} style={{ marginBottom: 12 }}>
              <div style={{
                fontSize: 9, fontWeight: 700, color: CATEGORY_COLORS[cat],
                letterSpacing: "0.1em", marginBottom: 6,
                borderBottom: `1px solid ${CATEGORY_COLORS[cat]}22`, paddingBottom: 3,
              }}>
                {cat.toUpperCase()}
              </div>
              {agents.filter(a => a.category === cat).map(a => <AgentCard key={a.agent} agent={a} />)}
            </div>
          ))}
        </div>

        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ fontSize: 9, color: "#334155", marginBottom: 6, letterSpacing: "0.1em" }}>LIVE TRANSCRIPT</div>
          <div style={{ height: 2, background: "#1e293b", borderRadius: 1, marginBottom: 8 }}>
            <div style={{
              height: "100%", width: `${(doneCount / 15) * 100}%`,
              background: "linear-gradient(90deg, #6366f1, #a78bfa)",
              borderRadius: 1, transition: "width 0.5s ease",
            }} />
          </div>
          <div ref={transcriptRef} style={{
            flex: 1, height: 440, overflowY: "auto",
            background: "#080814", border: "1px solid #1e293b",
            borderRadius: 8, padding: 10, marginBottom: 8,
          }}>
            {transcript.length === 0 && (
              <div style={{ color: "#1e293b", fontSize: 10, fontStyle: "italic" }}>
                Click JARVIS WAKE UP to start full briefing...
              </div>
            )}
            {transcript.map((line, i) => (
              <div key={i} style={{
                fontSize: 10, marginBottom: 4, lineHeight: 1.4,
                color: line.includes("[JARVIS]") ? "#a5b4fc" : line.includes("[YOU]") ? "#4ade80" : "#334155",
              }}>
                {line}
              </div>
            ))}
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            <input
              value={inputCmd}
              onChange={e => setInputCmd(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && inputCmd.trim()) { sendCommand(inputCmd); setInputCmd(""); }}}
              placeholder="Ask Jarvis anything..."
              style={{
                flex: 1, background: "#080814", border: "1px solid #1e293b",
                borderRadius: 6, padding: "7px 10px", color: "#e2e0ff",
                fontSize: 10, fontFamily: "monospace", outline: "none",
              }}
            />
            <button onClick={() => { if (inputCmd.trim()) { sendCommand(inputCmd); setInputCmd(""); }}} style={{
              background: "#6366f1", border: "none", borderRadius: 6,
              padding: "7px 12px", color: "#fff", fontSize: 10,
              fontFamily: "monospace", cursor: "pointer", fontWeight: 700,
            }}>GO</button>
          </div>
        </div>
      </div>
    </div>
  );
}
