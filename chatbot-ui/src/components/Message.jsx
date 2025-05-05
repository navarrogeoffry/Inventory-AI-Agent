import { motion } from "framer-motion";
import { User, Bot } from "lucide-react";

export default function Message({ message }) {
	const isUser = message.sender === "user";
        
	// Try to parse message.text as JSON
	let parsed = null;
	let isTable = false;
	try {
	  parsed = JSON.parse(message.text);
	  isTable = Array.isArray(parsed) && parsed.length > 0 && typeof parsed[0] === 'object';
	} catch (e) {
	  // Not JSON, that's fine
	}
        
	return (
	  <motion.div
	    initial={{ opacity: 0, y: 10 }}
	    animate={{ opacity: 1, y: 0 }}
	    transition={{ duration: 0.3 }}
	    className={`mb-4 flex ${isUser ? 'justify-end' : 'justify-start'}`}
	  >
	    {/* Avatar for bot messages */}
	    {!isUser && (
	      <div className="flex-shrink-0 mr-3">
		<div className="h-8 w-8 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
		  <Bot size={18} className="text-blue-500 dark:text-blue-300" />
		</div>
	      </div>
	    )}
	    
	    {/* Message content */}
	    <div className={`max-w-[80%] ${isTable ? 'w-full' : ''}`}>
	      <div
		className={`rounded-2xl px-4 py-3 shadow-sm ${
		  isUser 
		    ? 'bg-blue-700 dark:bg-blue-600 text-white' 
		    : 'bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100'
		}`}
	      >
		{message.image ? (
		  <div className="overflow-hidden rounded-lg">
		    <img
		      src={message.image}
		      alt="Chart"
		      className="max-w-full h-auto rounded-lg border border-gray-200 dark:border-gray-600"
		      onError={(e) => {
			e.target.onerror = null;
			e.target.src = "";
			e.target.alt = "⚠️ Chart failed to load.";
		      }}
		    />
		  </div>
		) : isTable ? (
		  <div className="overflow-x-auto">
		    <table className="w-full border-collapse">
		      <thead>
			<tr>
			  {Object.keys(parsed[0]).map((key) => (
			    <th 
			      key={key} 
			      className="border border-gray-300 dark:border-gray-600 px-2 py-1 text-left text-xs font-medium bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300"
			    >
			      {key}
			    </th>
			  ))}
			</tr>
		      </thead>
		      <tbody>
			{parsed.map((row, i) => (
			  <tr key={i} className={i % 2 === 0 ? 'bg-white dark:bg-gray-700' : 'bg-gray-50 dark:bg-gray-600'}>
			    {Object.values(row).map((value, j) => (
			      <td 
				key={j} 
				className="border border-gray-300 dark:border-gray-600 px-2 py-1 text-sm"
			      >
				{value !== null && value !== undefined ? String(value) : "N/A"}
			      </td>
			    ))}
			  </tr>
			))}
		      </tbody>
		    </table>
		  </div>
		) : (
		  <p className="whitespace-pre-wrap text-sm md:text-base">{message.text}</p>
		)}
	      </div>
	    </div>
	    
	    {/* Avatar for user messages */}
	    {isUser && (
	      <div className="flex-shrink-0 ml-3">
		<div className="h-8 w-8 rounded-full bg-blue-200 dark:bg-blue-800 flex items-center justify-center">
		  <User size={18} className="text-blue-700 dark:text-blue-300" />
		</div>
	      </div>
	    )}
	  </motion.div>
	);
        }
        