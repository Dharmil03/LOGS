export default function LogsViewer({ logs }) {
  const entries = logs?.data?.result || [];
  return (
    <div>
      <h3>Recent Logs</h3>
      <pre>
        {entries.map((l, i) => (
          <div key={i}>{l.stream.job}: {l.values[0][1]}</div>
        ))}
      </pre>
    </div>
  );
}