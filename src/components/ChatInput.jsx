// ChatInput.jsx
import { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";
import { motion } from "framer-motion";

export default function ChatInput({ onSend, disabled, darkMode }) {
  const [message, setMessage] = useState("");
  const textareaRef = useRef(null);

  // Auto-resize textarea based on content
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "56px"; // Reset height
      const scrollHeight = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = `${Math.min(scrollHeight, 150)}px`; // Limit max height
    }
  }, [message]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSend(message.trim());
      setMessage("");
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = "56px";
      }
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form 
      onSubmit={handleSubmit} 
      className="relative"
      id="chat-input"
    >
      <div className="relative flex items-end bg-white dark:bg-gray-700 rounded-lg shadow-sm border border-gray-200 dark:border-gray-600 focus-within:ring-2 focus-within:ring-primary">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your inventory..."
          className="flex-grow py-3 px-4 bg-transparent outline-none resize-none text-gray-800 dark:text-white min-h-[56px] max-h-[150px]"
          disabled={disabled}
        />
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          type="submit"
          disabled={!message.trim() || disabled}
          onClick={handleSubmit}
          className={`p-3 m-1 rounded-full ${
            message.trim() && !disabled
              ? "bg-blue-700 hover:bg-blue-800 dark:bg-blue-600 dark:hover:bg-blue-500 text-white"
              : "bg-gray-200 text-gray-500 dark:bg-gray-600 dark:text-gray-400"
          } transition-colors`}
          aria-label="Send message"
        >
          <Send size={20} />
        </motion.button>
      </div>
    </form>
  );
}