const chatWindow = document.getElementById('chat-window');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

function sendMessage() {
    const message = userInput.value.trim();
    if (message === '') return;

    appendMessage(message, 'user');
    userInput.value = '';
    chatWindow.scrollTop = chatWindow.scrollHeight;

    setTimeout(() => {
        const response = generateFakeResponse(message);
        appendMessage(response, 'system');
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }, 500); // Simulate response delay
}

function appendMessage(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('chat-message');
    messageDiv.classList.add(sender === 'user' ? 'user-message' : 'system-message');
    messageDiv.innerText = text;
    chatWindow.appendChild(messageDiv);
}

function generateFakeResponse(userMessage) {
    // For now, fake simple responses
    return `You said: "${userMessage}". Here's a placeholder response!`;
}
