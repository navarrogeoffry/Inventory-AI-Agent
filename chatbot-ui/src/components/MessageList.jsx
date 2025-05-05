// MessageList.jsx
import Message from "./Message";
import { useEffect, useRef } from "react";

export default function MessageList({ messages }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
 {messages
  .filter((msg) => msg && typeof msg === "object")
  .map((message, i) => (
    <Message key={i} message={message} />
))}

      <div ref={bottomRef} />
    </div>
  );
}