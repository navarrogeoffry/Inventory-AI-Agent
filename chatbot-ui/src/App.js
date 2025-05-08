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
  const [loadingStates, setLoadingStates] = useState({}); // Track loading state per chat
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isMobile, setIsMobile] = useState(false);
  const [darkMode, setDarkMode] = useState(() => {
    // Check for saved preference or use system preference
    const saved = localStorage.getItem("darkMode");
    return saved ? JSON.parse(saved) : window.matchMedia("(prefers-color-scheme: dark)").matches;
  });
  const messagesEndRef = useRef(null);

  const getMessages = () => {
    const activeChat = chats.find(c => c.sessionId === activeChatId);
    return activeChat?.messages || [];
  };

  const getChatTitle = (chat) => {
    if (!chat) return "New Conversation";
    
    // If there are messages, use the first user message as the title
    const firstUserMessage = chat.messages.find(m => m.sender === "user");
    if (firstUserMessage) {
      // Truncate long messages to 30 chars
      return firstUserMessage.text.length > 30 
        ? firstUserMessage.text.substring(0, 30) + "..." 
        : firstUserMessage.text;
    }
    
    return `Chat ${chat.sessionId.slice(0, 6)}`;
  };

  // Helper function to check if a chat is loading
  const isChatLoading = (sessionId) => {
    return loadingStates[sessionId] === true;
  };

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

  // Check if on mobile/small screen
  const checkMobile = () => {
    setIsMobile(window.innerWidth < 768);
    if (window.innerWidth < 768) {
      setSidebarOpen(false);
    }
  };

  useEffect(() => {
    // Initial check on component mount
    checkMobile();
    // Add listener for resize events
    window.addEventListener("resize", checkMobile);
    // Clean up event listener on unmount
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  const startNewChat = () => {
    const newSessionId = crypto.randomUUID();
    setChats(prevChats => [{
      sessionId: newSessionId,
      messages: []
    }, ...prevChats]);
    setActiveChatId(newSessionId);
  };

  // Start a new chat if none exists on first load
  useEffect(() => {
    if (chats.length === 0) {
      startNewChat();
    }
  }, [chats.length]);

  // Scroll to bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [getMessages().length]);

  const handleSend = async (userMessage) => {
    if (!userMessage.trim()) return;
    
    const newMessage = { sender: "user", text: userMessage };
    setChats(prevChats => prevChats.map(chat => {
      if (chat.sessionId === activeChatId) {
        return { ...chat, messages: [...chat.messages, newMessage] };
      }
      return chat;
    }));
    
    // Set loading state for this specific chat
    setLoadingStates(prev => ({
      ...prev,
      [activeChatId]: true
    }));
    
    // Start loading timestamp to ensure minimum loading time
    const loadingStartTime = Date.now();
    const minLoadingTime = 1500; // minimum 1.5 second loading

    // Get the backend port from environment variables or use default
    const backendPort = process.env.REACT_APP_BACKEND_PORT || 8000;
    const apiUrl = `http://localhost:${backendPort}/api/process_query`;
    
    try {
      const response = await fetch(apiUrl, {
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
        // Get the backend port from environment variables or use default
        const backendPort = process.env.REACT_APP_BACKEND_PORT || 8000;
        const fullUrl = `http://localhost:${backendPort}${data.chart_url}`;
        botMessages.push({ sender: "bot", image: fullUrl });
      }
      
      // Ensure loading shows for at least the minimum time
      const loadingElapsed = Date.now() - loadingStartTime;
      const remainingLoadTime = Math.max(0, minLoadingTime - loadingElapsed);
      
      setTimeout(() => {
        setChats(prev => prev.map(chat =>
          chat.sessionId === activeChatId
            ? { ...chat, messages: [...chat.messages, ...botMessages] }
            : chat
        ));
        
        // Only turn off loading after messages are added
        setLoadingStates(prev => ({
          ...prev,
          [activeChatId]: false
        }));
      }, remainingLoadTime);
      
    } catch (err) {
      console.error("API error:", err);
      
      // Ensure loading shows for at least the minimum time
      const loadingElapsed = Date.now() - loadingStartTime;
      const remainingLoadTime = Math.max(0, minLoadingTime - loadingElapsed);
      
      setTimeout(() => {
        setChats(prev => prev.map(chat =>
          chat.sessionId === activeChatId
            ? { ...chat, messages: [...chat.messages, { sender: "bot", text: "An error occurred. Please try again." }] }
            : chat
        ));
        
        // Turn off loading after error message is added
        setLoadingStates(prev => ({
          ...prev,
          [activeChatId]: false
        }));
      }, remainingLoadTime);
    }
  };

  // Delete chat
  const deleteChat = (sessionId) => {
    // Also remove loading state for this chat
    setLoadingStates(prev => {
      const newStates = {...prev};
      delete newStates[sessionId];
      return newStates;
    });
    
    setChats(prev => prev.filter(chat => chat.sessionId !== sessionId));
    if (activeChatId === sessionId) {
      const newActive = chats.find(c => c.sessionId !== sessionId);
      setActiveChatId(newActive ? newActive.sessionId : null);
      if (!newActive) startNewChat();
    }
  };

  // Handle suggested prompt selection
  const handleSuggestedPrompt = (promptText) => {
    handleSend(promptText);
  };

  // Check if the active chat is loading
  const isActiveLoading = activeChatId ? isChatLoading(activeChatId) : false;

  return (
    <div className={`flex h-screen ${darkMode ? 'dark' : ''}`}>
      {/* Fixed navigation header with menu toggle */}
      <div className="fixed top-0 left-0 right-0 z-40 flex items-center justify-between bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 shadow-sm h-14 px-4">
        <div className="flex items-center">
          <button 
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 rounded-full bg-blue-700 dark:bg-blue-600 text-white shadow-md hover:bg-blue-800 dark:hover:bg-blue-500 transition-colors cursor-pointer pointer-events-auto"
            aria-label="Toggle sidebar"
          >
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
          
          <h2 className="ml-4 font-medium text-gray-800 dark:text-white truncate flex items-center">
            {activeChatId && chats.find(c => c.sessionId === activeChatId) 
              ? getChatTitle(chats.find(c => c.sessionId === activeChatId))
              : "New Conversation"}
              
            {isActiveLoading && (
              <span className="ml-2 px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300 rounded-full animate-pulse">
                Processing...
              </span>
            )}
          </h2>
        </div>
        
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setDarkMode(!darkMode)}
          className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 cursor-pointer pointer-events-auto"
          aria-label="Toggle dark mode"
        >
          {darkMode ? <Sun size={20} className="text-amber-400" /> : <Moon size={20} className="text-gray-700" />}
        </motion.button>
      </div>

      {/* Flexible container for sidebar and main content */}
      <div className="w-full flex pt-14 h-screen">
        {/* Sidebar - Desktop (push content) */}
        <AnimatePresence>
          {sidebarOpen && !isMobile && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 256, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className="h-[calc(100%-3.5rem)] bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 shadow-lg md:shadow-none flex flex-col overflow-hidden pointer-events-auto flex-shrink-0"
            >
              <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                <h1 className="text-lg font-bold text-gray-800 dark:text-white">Inventory AI</h1>
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

        {/* Sidebar - Mobile (overlay) */}
        <AnimatePresence>
          {sidebarOpen && isMobile && (
            <motion.div
              initial={{ x: -300, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: -300, opacity: 0 }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className="fixed top-14 left-0 z-[35] w-64 h-[calc(100%-3.5rem)] bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 shadow-lg flex flex-col overflow-hidden pointer-events-auto"
            >
              <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                <h1 className="text-lg font-bold text-gray-800 dark:text-white">Inventory AI</h1>
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
                        layoutId={`mobile-chat-${chat.sessionId}`}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        className="relative"
                      >
                        <button
                          onClick={() => {
                            setActiveChatId(chat.sessionId);
                            setSidebarOpen(false); // Auto-close on mobile
                          }}
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
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Backdrop for mobile sidebar */}
        <AnimatePresence>
          {sidebarOpen && isMobile && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.5 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 bg-black z-30 pointer-events-auto"
              onClick={() => setSidebarOpen(false)}
            />
          )}
        </AnimatePresence>

        <div className="flex-1 flex flex-col min-w-0 bg-gray-50 dark:bg-gray-800 relative">
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
            {isActiveLoading && (
              <div className="absolute bottom-24 left-0 right-0 flex flex-col items-center z-50">
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-4 flex flex-col items-center">
                  <LoadingIndicator />
                  <span className="mt-2 text-sm text-gray-600 dark:text-gray-300 font-medium">
                    Analyzing your request...
                  </span>
                </div>
              </div>
            )}
          </ChatWindow>
          
          {/* Input area */}
          <div className="bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 p-4">
            <ChatInput onSend={handleSend} disabled={isActiveLoading} darkMode={darkMode} />
          </div>
        </div>
      </div>
    </div>
  );
}

