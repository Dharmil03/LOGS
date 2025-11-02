import { useState } from "react";
import axios from "axios";

export default function ChatBox({ metrics, logs }) {
  const [response, setResponse] = useState("");
  const askAI = async () => {
    const res = await axios.post("http://localhost:5000/analyze", { metrics, logs });
    setResponse(res.data.insight);
  };

  return (
    <div>
      <button onClick={askAI}>Ask Gemini AI</button>
      <p>{response}</p>
    </div>
  );
}
