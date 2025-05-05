// MessageList.jsx
import { motion } from "framer-motion";
import Message from "./Message";

export default function MessageList({ messages, darkMode }) {
  // Create staggered animation effect for messages
  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.05
      }
    }
  };

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="space-y-4 py-3 px-1"
    >
      {messages.map((message, index) => (
        <Message key={index} message={message} />
      ))}
    </motion.div>
  );
}