// LoadingIndicator.jsx
import { motion } from "framer-motion";

export default function LoadingIndicator() {
	return (
		<motion.div 
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			className="flex items-center justify-center space-x-2 py-1"
		>
			<div className="flex space-x-2">
				{[0, 1, 2].map((i) => (
					<div
						key={i}
						className={`h-2.5 w-2.5 rounded-full bg-gradient-to-r from-blue-400 to-indigo-600 dark:from-blue-300 dark:to-indigo-500 opacity-70 loading-dot`}
						style={{
							animationDelay: `${i * 0.15}s`
						}}
					/>
				))}
			</div>
		</motion.div>
	);
}