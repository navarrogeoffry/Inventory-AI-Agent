// App.jsx
import { useState, useEffect } from "react";
import ChatWindow from "./components/ChatWindow";
import MessageList from "./components/MessageList";
import ChatInput from "./components/ChatInput";
import LoadingIndicator from "./components/LoadingIndicator";

export default function App() {
  const [chats, setChats] = useState([]); // List of chat sessions
  const [activeChatId, setActiveChatId] = useState(null); // Current session ID
  const [isLoading, setIsLoading] = useState(false);
  const [input, setInput] = useState("");
  const [darkMode, setDarkMode] = useState(false);

  const getMessages = () => chats.find(c => c.sessionId === activeChatId)?.messages || [];

  const startNewChat = () => {
    const newSessionId = crypto.randomUUID();
    setChats([{ sessionId: newSessionId, messages: [] }, ...chats]);
    setActiveChatId(newSessionId);
  };

  const handleSend = async (userMessage) => {
    const newMessage = { sender: "user", text: userMessage };
    const updatedChats = chats.map(chat => {
      if (chat.sessionId === activeChatId) {
        return { ...chat, messages: [...chat.messages, newMessage] };
      }
      return chat;
    });
    setChats(updatedChats);
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8000/api/process_query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          natural_language_query: userMessage,
          session_id: activeChatId,
          user_id: "frontend-user"
        }),
      });

      const data = await response.json();
      if (data.session_id && !chats.some(chat => chat.sessionId === data.session_id)) {
        // New session ID from backend — add and switch to it
        setChats(prev => [{ sessionId: data.session_id, messages: [] }, ...prev]);
        setActiveChatId(data.session_id);
      }
      

      const botMessages = [];
      if (data.explanation) {
        botMessages.push({ sender: "bot", text: data.explanation });
      }
      if (data.results) {
        const resultsText = JSON.stringify(data.results, null, 2);
        botMessages.push({ sender: "bot", text: resultsText });
      }
      if (data.chart_url) {
        const fullUrl = `http://localhost:8000${data.chart_url}`;
        botMessages.push({ sender: "bot", image: fullUrl });
      }
      

      setChats(prev => prev.map(chat =>
        chat.sessionId === activeChatId
          ? { ...chat, messages: [...chat.messages, ...botMessages] }
          : chat
      ));
    } catch (err) {
      console.error("API error:", err);
      setChats(prev => prev.map(chat =>
        chat.sessionId === activeChatId
          ? { ...chat, messages: [...chat.messages, { sender: "bot", text: "An error occurred. Please try again." }] }
          : chat
      ));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!activeChatId) startNewChat();
  }, []);

  const backgroundColor = darkMode ? "#1e1e1e" : "#ffffff";
  const textColor = darkMode ? "#ffffff" : "#000000";

  return (
    <div style={{ display: 'flex', height: '100vh', backgroundColor, color: textColor }}>
      {/* Sidebar */}
      <div style={{ width: '250px', borderRight: `1px solid ${darkMode ? '#333' : '#ccc'}`, padding: '1rem', background: darkMode ? '#2b2b2b' : '#f0f0f0' }}>
        <button onClick={startNewChat} style={{ marginBottom: '1rem', width: '100%' }}>➕ New Chat</button>
        <button onClick={() => setDarkMode(prev => !prev)} style={{ marginBottom: '1rem', width: '100%' }}>
          {darkMode ? "☀️ Light Mode" : "🌙 Dark Mode"}
        </button>
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {chats.map(chat => (
            <li key={chat.sessionId} style={{ marginBottom: '0.5rem' }}>
              <button
                onClick={() => setActiveChatId(chat.sessionId)}
                style={{
                  background: chat.sessionId === activeChatId ? '#007bff' : '#fff',
                  color: chat.sessionId === activeChatId ? '#fff' : '#000',
                  border: '1px solid #ccc',
                  width: '100%',
                  padding: '0.5rem',
                  textAlign: 'left',
                  cursor: 'pointer'
                }}
              >
                Chat {chat.sessionId.slice(0, 6)}
              </button>
            </li>
          ))}
        </ul>
      </div>

      {/* Chat Window */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
      <ChatWindow darkMode={darkMode}>
           <MessageList messages={getMessages()} darkMode={darkMode} />
           {isLoading && <LoadingIndicator />}
           <ChatInput onSend={handleSend} disabled={isLoading} />
      </ChatWindow>

      </div>
    </div>
  );
}
