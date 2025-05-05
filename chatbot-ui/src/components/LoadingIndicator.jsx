// LoadingIndicator.jsx
import { motion } from "framer-motion";

export default function LoadingIndicator() {
	return (
		<motion.div 
			initial={{ opacity: 0, scale: 0.8 }}
			animate={{ opacity: 1, scale: 1 }}
			className="flex items-center justify-center space-x-1 p-2 bg-white dark:bg-gray-700 rounded-full shadow-lg"
		>
			{[0, 1, 2].map((i) => (
				<motion.div
					key={i}
					initial={{ y: 0 }}
					animate={{ y: [0, -6, 0] }}
					transition={{
						repeat: Infinity,
						duration: 0.6,
						delay: i * 0.1,
						ease: "easeInOut"
					}}
					className="h-2 w-2 rounded-full bg-primary"
				/>
			))}
		</motion.div>
	);
}