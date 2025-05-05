// ChatInput.jsx
import { useState } from "react";

export default function ChatInput({ onSend, disabled }) {
  const [input, setInput] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    onSend(input);
    setInput("");
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', padding: '1rem', borderTop: '1px solid #ccc', backgroundColor: '#f9f9f9' }}>
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        disabled={disabled}
        placeholder="Type your message..."
        style={{ flex: 1, padding: '0.75rem', fontSize: '1rem', borderRadius: '6px', border: '1px solid #ccc', marginRight: '0.5rem' }}
      />
      <button type="submit" disabled={disabled} style={{ padding: '0.75rem 1.25rem', backgroundColor: '#007bff', color: '#fff', border: 'none', borderRadius: '6px' }}>
        Send
      </button>
    </form>
  );
}