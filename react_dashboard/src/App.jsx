import React, { useEffect, useState } from "react";
import axios from "axios";

const BACKEND_URL = "http://localhost:5000";

function App() {
  const [logs, setLogs] = useState([]);
  const [messages, setMessages] = useState([]);
  const [userInput, setUserInput] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({ chromadb_count: 0, logs_added: 0 });

  // Fetch logs from Flask (called every 15s)
  const fetchLogs = async () => {
    try {
      const res = await axios.get(`${BACKEND_URL}/logs?limit=100`);
      const results = res.data?.data?.result || [];

      if (results.length > 0) {
        const newLogs = results.flatMap((r) =>
          r.values.map((v) => ({
            timestamp: new Date(parseInt(v[0]) / 1000000).toLocaleString(),
            message: v[1],
            level: getLogLevel(v[1]),
            job: r.stream?.job || "unknown",
          }))
        );
        // Sort by timestamp descending (newest first)
        newLogs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        setLogs(newLogs);
      } else {
        setLogs([]); // clear if none
      }
      setError(null);
    } catch (err) {
      setError("Error fetching logs: " + err.message);
      console.error(err);
    }
  };

  // Fetch stats from Flask
  const fetchStats = async () => {
    try {
      const res = await axios.get(`${BACKEND_URL}/health`);
      setStats({
        chromadb_count: res.data.chromadb_count || 0,
        logs_added: res.data.logs_added || 0,
        logs_processed: res.data.logs_processed || 0,
      });
    } catch (err) {
      console.error("Error fetching stats:", err);
    }
  };

  // Determine log level from message
  const getLogLevel = (message) => {
    const upper = message.toUpperCase();
    if (upper.includes("ERROR") || upper.includes("[ERROR]")) return "error";
    if (upper.includes("WARNING") || upper.includes("[WARNING]")) return "warning";
    if (upper.includes("INFO") || upper.includes("[INFO]")) return "info";
    return "default";
  };

  // Send chat message
  const sendChat = async () => {
    if (!userInput.trim()) return;

    const query = userInput.trim();
    setUserInput("");
    setMessages((prev) => [...prev, { sender: "user", text: query }]);

    try {
      setLoading(true);
      const res = await axios.post(`${BACKEND_URL}/chat`, { message: query });

      const aiResponse = res.data?.answer || "No AI response.";
      const logsFound = res.data?.logs_found || 0;
      const totalInDb = res.data?.total_in_db || 0;

      setMessages((prev) => [
        ...prev,
        {
          sender: "ai",
          text: aiResponse,
          meta: `📊 Found ${logsFound} relevant logs out of ${totalInDb} total in ChromaDB`,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { sender: "ai", text: "❌ Error: " + err.message },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Poll logs and stats
  useEffect(() => {
    // initial fetch
    fetchLogs();
    fetchStats();

    const logsInterval = setInterval(fetchLogs, 15000); // every 15 seconds
    const statsInterval = setInterval(fetchStats, 5000);

    return () => {
      clearInterval(logsInterval);
      clearInterval(statsInterval);
    };
  }, []);

  return (
    <div style={styles.container}>
      {/* Header Stats Bar */}
      <div style={styles.statsBar}>
        <div style={styles.statItem}>
          <span style={styles.statLabel}>📊 ChromaDB:</span>
          <span style={styles.statValue}>{stats.chromadb_count}</span>
        </div>
        <div style={styles.statItem}>
          <span style={styles.statLabel}>✅ Added:</span>
          <span style={styles.statValue}>{stats.logs_added}</span>
        </div>
        <div style={styles.statItem}>
          <span style={styles.statLabel}>📝 Displayed:</span>
          <span style={styles.statValue}>{logs.length}</span>
        </div>
        <div style={styles.statItem}>
          <span style={styles.statLabel}>⏱️ Polling:</span>
          <span style={styles.statValue}>15s</span>
        </div>
        <button
          style={styles.refreshButton}
          onClick={() => {
            fetchLogs();
            fetchStats();
          }}
        >
          🔄 Refresh Now
        </button>
      </div>

      <div style={styles.mainContent}>
        {/* LEFT: Logs Panel */}
        <div style={styles.logsPanel}>
          <div style={styles.panelHeader}>
            <h2 style={styles.panelTitle}>📜 Real-Time Logs</h2>
          </div>

          {error && <p style={styles.error}>{error}</p>}

          <div style={styles.logBox}>
            {logs.length > 0 ? (
              logs.map((log, index) => (
                <div
                  key={index}
                  style={{
                    ...styles.logLine,
                    ...styles[
                      `log${log.level.charAt(0).toUpperCase() + log.level.slice(1)}`
                    ],
                  }}
                >
                  <span style={styles.logTimestamp}>{log.timestamp}</span>
                  <span style={styles.logJob}>[{log.job}]</span>
                  <span style={styles.logLevel}>[{log.level.toUpperCase()}]</span>
                  <span style={styles.logMessage}>{log.message}</span>
                </div>
              ))
            ) : (
              <p style={styles.emptyMessage}>⏳ Waiting for logs...</p>
            )}
          </div>
        </div>

        {/* RIGHT: Chat Panel */}
        <div style={styles.chatPanel}>
          <h2 style={styles.panelTitle}>🤖 AI Observability Assistant</h2>

          <div style={styles.chatBox}>
            {messages.length === 0 && (
              <div style={styles.chatWelcome}>
                <p>👋 Hi! Ask me about your system logs and performance.</p>
                <p style={styles.chatHint}>Try: "Show me all errors" or "What's causing high CPU?"</p>
              </div>
            )}

            {messages.map((m, i) => (
              <div key={i} style={styles.messageWrapper}>
                <div
                  style={{
                    ...styles.message,
                    alignSelf: m.sender === "user" ? "flex-end" : "flex-start",
                    backgroundColor: m.sender === "user" ? "#00e676" : "#1e1e1e",
                    color: m.sender === "user" ? "#121212" : "#f1f1f1",
                  }}
                >
                  <strong style={styles.messageSender}>
                    {m.sender === "user" ? "You" : "🤖 AI"}:
                  </strong>
                  <div style={styles.messageText}>{m.text}</div>
                  {m.meta && <div style={styles.messageMeta}>{m.meta}</div>}
                </div>
              </div>
            ))}

            {loading && (
              <div style={styles.loadingMessage}>
                <span style={styles.loadingDots}>●</span>
                <span style={styles.loadingDots}>●</span>
                <span style={styles.loadingDots}>●</span>
                <span style={styles.loadingText}>Analyzing logs with AI...</span>
              </div>
            )}
          </div>

          <div style={styles.inputContainer}>
            <input
              style={styles.input}
              placeholder="Ask about system performance, errors, or patterns..."
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendChat()}
              disabled={loading}
            />
            <button
              style={{
                ...styles.sendButton,
                opacity: loading || !userInput.trim() ? 0.5 : 1,
                cursor: loading || !userInput.trim() ? "not-allowed" : "pointer",
              }}
              onClick={sendChat}
              disabled={loading || !userInput.trim()}
            >
              {loading ? "⏳" : "📤"} Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Styles are the same as your previous file (kept for brevity)
const styles = {
  container: {
    display: "flex",
    flexDirection: "column",
    backgroundColor: "#0a0a0a",
    color: "#f1f1f1",
    minHeight: "100vh",
    fontFamily: "'Consolas', 'Monaco', 'Courier New', monospace",
  },
  statsBar: {
    display: "flex",
    alignItems: "center",
    gap: "20px",
    padding: "15px 20px",
    backgroundColor: "#1a1a1a",
    borderBottom: "2px solid #00e676",
    flexWrap: "wrap",
  },
  statItem: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  statLabel: {
    color: "#888",
    fontSize: "14px",
  },
  statValue: {
    color: "#00e676",
    fontSize: "18px",
    fontWeight: "bold",
  },
  refreshButton: {
    backgroundColor: "#007acc",
    color: "white",
    border: "none",
    padding: "8px 15px",
    borderRadius: "5px",
    cursor: "pointer",
    fontWeight: "bold",
    fontSize: "14px",
  },
  mainContent: {
    display: "flex",
    flex: 1,
    overflow: "hidden",
  },
  panelHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "10px",
  },
  panelTitle: {
    color: "#00e676",
    margin: 0,
    fontSize: "20px",
  },
  logsPanel: {
    flex: 1,
    borderRight: "2px solid #222",
    padding: "20px",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },
  chatPanel: {
    flex: 1,
    padding: "20px",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },
  logBox: {
    flex: 1,
    backgroundColor: "#0f0f0f",
    padding: "15px",
    borderRadius: "8px",
    overflowY: "auto",
    border: "1px solid #222",
  },
  logLine: {
    padding: "8px",
    marginBottom: "4px",
    borderRadius: "4px",
    display: "flex",
    gap: "10px",
    fontSize: "13px",
    lineHeight: "1.6",
    borderLeft: "3px solid transparent",
    transition: "background 0.2s",
  },
  logTimestamp: {
    color: "#666",
    minWidth: "160px",
  },
  logJob: {
    color: "#00e676",
    minWidth: "80px",
  },
  logLevel: {
    minWidth: "80px",
    fontWeight: "bold",
  },
  logMessage: {
    flex: 1,
    wordBreak: "break-word",
  },
  logError: {
    backgroundColor: "rgba(255, 0, 0, 0.1)",
    borderLeftColor: "#ff4444",
  },
  logWarning: {
    backgroundColor: "rgba(255, 165, 0, 0.1)",
    borderLeftColor: "#ff9800",
  },
  logInfo: {
    backgroundColor: "rgba(33, 150, 243, 0.1)",
    borderLeftColor: "#2196f3",
  },
  logDefault: {
    borderLeftColor: "#333",
  },
  emptyMessage: {
    textAlign: "center",
    color: "#666",
    padding: "40px",
    fontSize: "16px",
  },
  chatBox: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    backgroundColor: "#0f0f0f",
    padding: "15px",
    borderRadius: "8px",
    overflowY: "auto",
    border: "1px solid #222",
    marginBottom: "15px",
  },
  chatWelcome: {
    textAlign: "center",
    padding: "40px 20px",
    color: "#888",
  },
  chatHint: {
    fontSize: "14px",
    color: "#555",
    marginTop: "10px",
  },
  messageWrapper: {
    display: "flex",
    flexDirection: "column",
    marginBottom: "10px",
  },
  message: {
    maxWidth: "75%",
    padding: "12px 16px",
    borderRadius: "12px",
    wordBreak: "break-word",
    boxShadow: "0 2px 5px rgba(0,0,0,0.3)",
  },
  messageSender: {
    display: "block",
    marginBottom: "5px",
    fontSize: "12px",
  },
  messageText: {
    whiteSpace: "pre-wrap",
    lineHeight: "1.5",
  },
  messageMeta: {
    fontSize: "11px",
    marginTop: "8px",
    opacity: 0.7,
    borderTop: "1px solid rgba(255,255,255,0.1)",
    paddingTop: "8px",
  },
  loadingMessage: {
    alignSelf: "flex-start",
    backgroundColor: "#1e1e1e",
    padding: "12px 16px",
    borderRadius: "12px",
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  loadingDots: {
    fontSize: "20px",
    animation: "pulse 1.4s infinite",
    color: "#00e676",
  },
  loadingText: {
    color: "#888",
    fontSize: "14px",
  },
  inputContainer: {
    display: "flex",
    gap: "10px",
  },
  input: {
    flex: 1,
    padding: "12px 16px",
    borderRadius: "8px",
    border: "1px solid #333",
    backgroundColor: "#1e1e1e",
    color: "#f1f1f1",
    fontSize: "14px",
    outline: "none",
    transition: "border 0.2s",
  },
  sendButton: {
    backgroundColor: "#00e676",
    color: "#121212",
    border: "none",
    padding: "12px 24px",
    borderRadius: "8px",
    cursor: "pointer",
    fontWeight: "bold",
    fontSize: "14px",
    transition: "all 0.2s",
  },
  error: {
    color: "#ff4444",
    fontWeight: "bold",
    padding: "10px",
    backgroundColor: "rgba(255, 68, 68, 0.1)",
    borderRadius: "4px",
    marginBottom: "10px",
    border: "1px solid #ff4444",
  },
};

export default App;
