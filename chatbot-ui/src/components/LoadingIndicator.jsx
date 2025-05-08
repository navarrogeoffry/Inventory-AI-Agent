// LoadingIndicator.jsx
import { motion } from "framer-motion";

export default function LoadingIndicator() {
	return (
		<motion.div 
			initial={{ opacity: 0, scale: 0.8 }}
			animate={{ opacity: 1, scale: 1 }}
			className="flex items-center justify-center space-x-3 p-4 bg-white dark:bg-gray-800 rounded-full shadow-lg border border-gray-100 dark:border-gray-700"
		>
			{[0, 1, 2].map((i) => (
				<motion.div
					key={i}
					initial={{ scale: 1 }}
					animate={{ 
						scale: [1, 1.5, 1],
						opacity: [0.7, 1, 0.7]
					}}
					transition={{
						repeat: Infinity,
						duration: 1.2,
						delay: i * 0.2,
						ease: "easeInOut"
					}}
					className="h-4 w-4 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 dark:from-blue-400 dark:to-indigo-500 shadow-sm"
				/>
			))}
		</motion.div>
	);
}