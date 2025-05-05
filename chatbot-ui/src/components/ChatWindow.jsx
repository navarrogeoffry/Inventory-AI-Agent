// ChatWindow.jsx
import { motion } from "framer-motion";

export default function ChatWindow({ children, darkMode, className = "" }) {
	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			className={`p-4 md:p-6 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white overflow-y-auto ${className}`}
		>
			{children}
		</motion.div>
	);
}
        