export default function Message({ message }) {
	const isUser = message.sender === "user";
        
	// Try to parse message.text as JSON
	let parsed = null;
	try {
	  parsed = JSON.parse(message.text);
	} catch (e) {}
        
	const bubbleStyle = {
	  maxWidth: "80%",
	  marginBottom: "1rem",
	  padding: "0.75rem",
	  borderRadius: "8px",
	  backgroundColor: isUser ? "#007bff" : "#e5e5ea",
	  color: isUser ? "#fff" : "#000",
	  alignSelf: isUser ? "flex-end" : "flex-start",
	  overflowX: "auto",
	  whiteSpace: "pre-wrap"
	};
        
	return (
	  <div style={bubbleStyle}>
	    {message.image ? (
	      <img
	        src={message.image}
	        alt="Chart"
	        style={{
		maxWidth: "100%",
		borderRadius: "6px",
		marginTop: "0.5rem"
	        }}
	        onError={(e) => {
		e.target.onerror = null;
		e.target.src = "";
		e.target.alt = "⚠️ Chart failed to load.";
	        }}
	      />
	    ) : parsed && Array.isArray(parsed) ? (
	      <table style={{ width: "100%", borderCollapse: "collapse" }}>
	        <thead>
		<tr>
		  {Object.keys(parsed[0]).map((key) => (
		    <th key={key} style={{ border: "1px solid #ccc", padding: "6px", backgroundColor: "#f9f9f9" }}>
		      {key}
		    </th>
		  ))}
		</tr>
	        </thead>
	        <tbody>
		{parsed.map((row, i) => (
		  <tr key={i}>
		    {Object.values(row).map((value, j) => (
		      <td key={j} style={{ border: "1px solid #ccc", padding: "6px" }}>
		        {value}
		      </td>
		    ))}
		  </tr>
		))}
	        </tbody>
	      </table>
	    ) : (
	      <p>{message.text}</p>
	    )}
	  </div>
	);
        }
        