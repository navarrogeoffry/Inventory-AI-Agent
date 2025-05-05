// App.js
import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X, Plus, Sun, Moon, ChevronRight, MessageSquare } from "lucide-react";

// Components
import ChatWindow from "./components/ChatWindow";
import MessageList from "./components/MessageList";
import ChatInput from "./components/ChatInput";
import LoadingIndicator from "./components/LoadingIndicator";

export default function App() {
  const [chats, setChats] = useState([]); // List of chat sessions
  const [activeChatId, setActiveChatId] = useState(null); // Current session ID
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [darkMode, setDarkMode] = useState(() => {
    // Check for saved preference or use system preference
    const saved = localStorage.getItem("darkMode");
    return saved ? JSON.parse(saved) : window.matchMedia("(prefers-color-scheme: dark)").matches;
  });
  const messagesEndRef = useRef(null);

  // Save dark mode preference
  useEffect(() => {
    localStorage.setItem("darkMode", JSON.stringify(darkMode));
    // Apply dark mode to document
    if (darkMode) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [darkMode]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chats, activeChatId]);

  // Initialize on first load
  useEffect(() => {
    if (!activeChatId && chats.length === 0) startNewChat();
  }, [activeChatId, chats.length, startNewChat]);

  const getMessages = () => chats.find(c => c.sessionId === activeChatId)?.messages || [];
  
  const getChatTitle = (chat) => {
    const firstUserMessage = chat.messages.find(m => m.sender === "user")?.text;
    if (firstUserMessage) {
      return firstUserMessage.length > 25 
        ? firstUserMessage.substring(0, 25) + "..." 
        : firstUserMessage;
    }
    return `Chat ${chat.sessionId.slice(0, 6)}`;
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  function startNewChat() {
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

  // Delete chat
  const deleteChat = (sessionId) => {
    setChats(prev => prev.filter(chat => chat.sessionId !== sessionId));
    if (activeChatId === sessionId) {
      setActiveChatId(chats.length > 1 ? chats[0].sessionId : null);
      if (!chats[0]) startNewChat();
    }
  };

  // Handle suggested prompt selection
  const handleSuggestedPrompt = (promptText) => {
    handleSend(promptText);
  };

  return (
    <div className={`flex h-screen ${darkMode ? 'dark' : ''}`}>
      {/* Mobile sidebar toggle */}
      <div className="fixed top-4 left-4 z-30 md:hidden">
        <button 
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-2 rounded-full bg-blue-700 dark:bg-blue-600 text-white shadow-lg"
        >
          {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {/* Sidebar */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ x: -300, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -300, opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="fixed md:relative z-20 w-64 h-full bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 shadow-lg md:shadow-none flex flex-col"
          >
            <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
              <h1 className="text-lg font-bold text-gray-800 dark:text-white">Inventory AI</h1>
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setDarkMode(!darkMode)}
                className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                {darkMode ? <Sun size={20} className="text-amber-400" /> : <Moon size={20} className="text-gray-700" />}
              </motion.button>
            </div>
            
            <div className="p-4">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={startNewChat}
                className="w-full flex items-center justify-center gap-2 p-3 bg-blue-700 hover:bg-blue-800 dark:bg-blue-600 dark:hover:bg-blue-500 text-white rounded-lg shadow hover:shadow-md transition-all"
              >
                <Plus size={18} />
                <span>New Chat</span>
              </motion.button>
            </div>
            
            <div className="flex-1 overflow-auto p-2">
              <div className="space-y-2">
                {chats.length === 0 ? (
                  <p className="text-center text-gray-500 dark:text-gray-400 p-4">No chats yet</p>
                ) : (
                  chats.map(chat => (
                    <motion.div
                      key={chat.sessionId}
                      layoutId={`chat-${chat.sessionId}`}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -20 }}
                      className="relative"
                    >
                      <button
                        onClick={() => setActiveChatId(chat.sessionId)}
                        className={`group w-full flex items-center gap-3 p-3 rounded-lg transition-all ${
                          chat.sessionId === activeChatId 
                            ? "bg-blue-700 dark:bg-blue-600 text-white" 
                            : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
                        }`}
                      >
                        <MessageSquare size={18} className={chat.sessionId === activeChatId ? "text-white" : "text-gray-500 dark:text-gray-400"} />
                        <span className="flex-1 truncate text-left">{getChatTitle(chat)}</span>
                        {chat.sessionId === activeChatId && (
                          <motion.button
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteChat(chat.sessionId);
                            }}
                            className="opacity-0 group-hover:opacity-100 p-1 rounded-full hover:bg-red-500 hover:text-white"
                          >
                            <X size={16} />
                          </motion.button>
                        )}
                      </button>
                    </motion.div>
                  ))
                )}
              </div>
            </div>
            
            <div className="p-4 text-xs text-center text-gray-500 dark:text-gray-400 border-t border-gray-200 dark:border-gray-700">
              Inventory AI Agent v1.0
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 bg-gray-50 dark:bg-gray-800">
        {/* Chat header */}
        <header className="flex items-center justify-between p-4 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 shadow-sm">
          <h2 className="font-medium text-gray-800 dark:text-white truncate">
            {activeChatId && chats.find(c => c.sessionId === activeChatId) 
              ? getChatTitle(chats.find(c => c.sessionId === activeChatId))
              : "New Conversation"}
          </h2>
          <div className="flex items-center">
            {/* Any header actions here */}
          </div>
        </header>
        
        {/* Chat window */}
        <ChatWindow darkMode={darkMode} className="flex-1 relative overflow-y-auto">
          {getMessages().length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-6">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="max-w-md"
              >
                <h3 className="text-2xl font-bold mb-2 text-gray-800 dark:text-white">Welcome to Inventory AI</h3>
                <p className="text-gray-600 dark:text-gray-400 mb-8">
                  Ask me questions about your inventory in natural language. I can help with queries, visualizations, and insights.
                </p>
                <div className="space-y-4">
                  <motion.div
                    whileHover={{ scale: 1.03 }}
                    className="p-3 bg-white dark:bg-gray-700 rounded-lg shadow-sm border border-gray-200 dark:border-gray-600 cursor-pointer"
                    onClick={() => handleSuggestedPrompt("Show me top 5 selling items")}
                  >
                    <p className="flex items-center gap-2 text-gray-800 dark:text-white">
                      <ChevronRight size={16} className="text-blue-600 dark:text-blue-400" />
                      Show me top 5 selling items
                    </p>
                  </motion.div>
                  <motion.div
                    whileHover={{ scale: 1.03 }}
                    className="p-3 bg-white dark:bg-gray-700 rounded-lg shadow-sm border border-gray-200 dark:border-gray-600 cursor-pointer"
                    onClick={() => handleSuggestedPrompt("Generate a pie chart of my inventory by value")}
                  >
                    <p className="flex items-center gap-2 text-gray-800 dark:text-white">
                      <ChevronRight size={16} className="text-blue-600 dark:text-blue-400" />
                      Generate a pie chart of my inventory by value
                    </p>
                  </motion.div>
                </div>
              </motion.div>
            </div>
          ) : (
            <>
              <MessageList messages={getMessages()} darkMode={darkMode} />
              <div ref={messagesEndRef} />
            </>
          )}
          {isLoading && (
            <div className="absolute bottom-0 left-0 right-0 flex justify-center p-4">
              <LoadingIndicator />
            </div>
          )}
        </ChatWindow>
        
        {/* Input area */}
        <div className="bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 p-4">
          <ChatInput onSend={handleSend} disabled={isLoading} darkMode={darkMode} />
        </div>
      </div>
    </div>
  );
}
