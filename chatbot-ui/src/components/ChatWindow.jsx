// ChatWindow.jsx
export default function ChatWindow({ children, darkMode }) {
	const style = {
	  flexGrow: 1,
	  padding: '1rem',
	  backgroundColor: darkMode ? '#1e1e1e' : '#ffffff',
	  color: darkMode ? '#ffffff' : '#000000',
	  overflowY: 'auto',
	};
        
	return <div style={style}>{children}</div>;
        }
        