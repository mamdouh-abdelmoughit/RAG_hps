import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [isThinking, setIsThinking] = useState(false); // Track whether the bot is thinking
  const [isPdfMode, setIsPdfMode] = useState(false); // Track whether PDF mode is active
  const chatContainerRef = useRef(null);
  const fileInputRef = useRef(null); // Ref to reset file input

  useEffect(() => {
    scrollToBottom();
  }, [messages, isThinking]);

  const scrollToBottom = () => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  };

  const handleInputChange = (e) => {
    setInputText(e.target.value);
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (file.type !== 'application/pdf') {
      setMessages([...messages, { text: 'Please upload a PDF file.', sender: 'bot' }]);
      return;
    }

    setIsUploading(true);
    setMessages([...messages, { text: 'Uploading PDF...', sender: 'user' }]);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post('http://localhost:8000/uploadpdf/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setMessages((prevMessages) => [
        ...prevMessages.slice(0, -1), // Remove "Uploading PDF..." message
        { text: response.data.message, sender: 'bot' }, // Use backend's message
      ]);
      setIsPdfMode(true); // Switch to PDF mode
    } catch (error) {
      console.error('Error uploading PDF:', error);
      let errorMessage = 'Error processing PDF.';
      if (error.response && error.response.data && error.response.data.detail) {
        errorMessage = error.response.data.detail;
      }
      setMessages((prevMessages) => [
        ...prevMessages.slice(0, -1), // Remove "Uploading PDF..." message
        { text: errorMessage, sender: 'bot' },
      ]);
    } finally {
      setIsUploading(false);
      // Reset file input to allow re-uploading the same file
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleSendMessage = async () => {
    if (!inputText.trim()) return;

    const userMessage = { text: inputText, sender: 'user' };
    setMessages([...messages, userMessage]);
    setInputText('');
    setIsThinking(true);

    try {
      const response = await axios.post('http://localhost:8000/ask/', { query: inputText });
      const botMessage = { 
        text: response.data.answer, 
        sender: 'bot',
      };
      setMessages((prevMessages) => [...prevMessages, botMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      let errorMessage = 'Failed to get response from the chatbot.';
      if (error.response && error.response.data && error.response.data.detail) {
        errorMessage = error.response.data.detail;
      }
      const botMessage = { text: `Error: ${errorMessage}`, sender: 'bot' };
      setMessages((prevMessages) => [...prevMessages, botMessage]);
    } finally {
      setIsThinking(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleClearChat = () => {
    setMessages([]);
  };

  const handleClearPdf = () => {
    setIsPdfMode(false);
    setMessages([...messages, { text: 'PDF mode cleared. Now in General mode.', sender: 'bot' }]);
  };

  return (
    <div className="app-container">
      <h1>Chatbot</h1>
      {/* Mode indicator */}
      <div className="mode-indicator">
        {isPdfMode ? 'Mode: PDF (Querying uploaded PDF)' : 'Mode: General (General questions)'}
      </div>
      {/* Action buttons */}
      <div className="action-buttons">
        <button onClick={handleClearChat} className="action-button">
          Clear Chat
        </button>
        {isPdfMode && (
          <button onClick={handleClearPdf} className="action-button">
            Clear PDF
          </button>
        )}
      </div>
      {/* Chat container */}
      <div className="chat-container" ref={chatContainerRef}>
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.sender}`}>
            {message.text}
          </div>
        ))}
        {isThinking && (
          <div className="message bot thinking">
            <span className="thinking-dots">Bot is thinking</span>
          </div>
        )}
      </div>
      {/* Input container */}
      <div className="input-container">
        {/* PDF upload button */}
        <div className="upload-container">
          <input
            type="file"
            id="pdf-upload"
            accept=".pdf"
            onChange={handleFileUpload}
            disabled={isUploading || isPdfMode} // Disable if uploading or in PDF mode
            style={{ display: 'none' }}
            ref={fileInputRef} // Add ref to reset file input
          />
          <label htmlFor="pdf-upload" className="upload-button">
            {isUploading ? 'Uploading...' : 'Upload PDF'}
          </label>
        </div>
        {/* Message input */}
        <textarea
          value={inputText}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          placeholder="Type your message..."
          className="message-input"
          disabled={isUploading || isThinking}
        />
        {/* Send button */}
        <button onClick={handleSendMessage} className="send-button" disabled={isUploading || isThinking}>
          Send
        </button>
      </div>
    </div>
  );
}

export default App;