import React, { useEffect, useState } from "react";
import axios from "axios";

const BACKEND_URL = "http://localhost:5000"; // Flask backend

function App() {
  const [logs, setLogs] = useState([]);
  const [analysis, setAnalysis] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  // ✅ Fetch logs via Flask (which proxies to Loki)
  const fetchLogs = async () => {
    try {
      const res = await axios.get(`${BACKEND_URL}/logs`);
      const results = res.data?.data?.result || [];

      if (results.length > 0) {
        const newLogs = results.flatMap((r) =>
          r.values.map((v) => ({
            timestamp: new Date(parseInt(v[0].slice(0, 13))).toLocaleTimeString(),
            message: v[1],
          }))
        );
        setLogs(newLogs);
      } else {
        setLogs([]);
      }

      setError(null);
    } catch (err) {
      setError("Error fetching logs: " + err.message);
    }
  };

  // ✅ Analyze logs using Flask + Gemini API
  const analyzeLogs = async () => {
    if (logs.length === 0) {
      setError("No logs to analyze!");
      return;
    }

    try {
      setLoading(true);
      setAnalysis("");
      const combinedLogs = logs.map((l) => l.message).join("\n");

      const res = await axios.post(`${BACKEND_URL}/analyze`, { logs: combinedLogs });
      const aiResponse =
        res.data?.candidates?.[0]?.content?.parts?.[0]?.text ||
        res.data?.output ||
        "No insights generated.";

      setAnalysis(aiResponse);
      setError(null);
    } catch (err) {
      setError("Error analyzing logs: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  // ✅ Poll logs every 3 seconds
  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>📜 Loki Logs Dashboard</h1>

      {error && <p style={styles.error}>{error}</p>}

      <button
        onClick={analyzeLogs}
        style={styles.button}
        disabled={loading || logs.length === 0}
      >
        {loading ? "Analyzing..." : "Analyze Logs"}
      </button>

      <div style={styles.logBox}>
        {logs.length > 0 ? (
          logs.map((log, index) => (
            <div key={index} style={styles.logLine}>
              <span style={styles.time}>[{log.timestamp}]</span> {log.message}
            </div>
          ))
        ) : (
          <p>No logs found...</p>
        )}
      </div>

      {analysis && (
        <div style={styles.analysisBox}>
          <h3>🧠 AI Insights</h3>
          <p>{analysis}</p>
        </div>
      )}
    </div>
  );
}

const styles = {
  container: {
    fontFamily: "monospace",
    padding: "20px",
    backgroundColor: "#121212",
    color: "#f1f1f1",
    minHeight: "100vh",
  },
  title: { color: "#00e676" },
  error: { color: "red", fontWeight: "bold" },
  button: {
    backgroundColor: "#00e676",
    color: "#121212",
    border: "none",
    padding: "10px 20px",
    borderRadius: "5px",
    cursor: "pointer",
    fontWeight: "bold",
    marginBottom: "15px",
  },
  logBox: {
    backgroundColor: "#1e1e1e",
    padding: "10px",
    borderRadius: "8px",
    height: "60vh",
    overflowY: "auto",
    border: "1px solid #333",
  },
  logLine: { marginBottom: "6px" },
  time: { color: "#888" },
  analysisBox: {
    backgroundColor: "#1e1e1e",
    padding: "15px",
    borderRadius: "8px",
    marginTop: "15px",
    border: "1px solid #333",
  },
};

export default App;

