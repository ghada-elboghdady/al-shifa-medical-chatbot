/**
 * App — main application component.
 * Manages conversation state, session ID, and message flow.
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import Message from './components/Message';
import ChatInput from './components/ChatInput';
import WelcomeScreen from './components/WelcomeScreen';
import { sendMessage, clearSession } from './api';
import './index.css';

let msgId = 0;
const nextId = () => `msg-${++msgId}`;

function ChatHeader({ onNewChat }) {
  return (
    <div className="chat-header">
      <div className="chat-header-avatar">
        🩺
        <div className="online-dot" />
      </div>
      <div className="chat-header-info">
        <h2>Al Shifa Medical Assistant</h2>
        <p>● Online — responds in Arabic &amp; English</p>
      </div>
    </div>
  );
}

export default function App() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const addMessage = useCallback((msg) => {
    setMessages((prev) => [...prev, { id: nextId(), timestamp: new Date().toISOString(), ...msg }]);
  }, []);

  const handleSend = useCallback(async (text) => {
    if (isLoading) return;

    // Add user message immediately
    addMessage({ role: 'user', text });

    // Show typing indicator
    const typingId = nextId();
    setMessages((prev) => [
      ...prev,
      { id: typingId, type: 'typing', role: 'bot', timestamp: new Date().toISOString() },
    ]);
    setIsLoading(true);

    try {
      const result = await sendMessage(text, sessionId);

      // Save session ID from first response
      if (!sessionId && result.session_id) {
        setSessionId(result.session_id);
      }

      // Remove typing indicator and add bot response
      setMessages((prev) =>
        prev
          .filter((m) => m.id !== typingId)
          .concat({
            id: nextId(),
            role: 'bot',
            response: result.response,
            timestamp: new Date().toISOString(),
          })
      );
    } catch (err) {
      setMessages((prev) =>
        prev
          .filter((m) => m.id !== typingId)
          .concat({
            id: nextId(),
            role: 'bot',
            response: {
              type: 'general',
              language: 'en',
              answer: `⚠️ Connection error: ${err.message}. Please make sure the backend is running on http://localhost:8000`,
            },
            timestamp: new Date().toISOString(),
          })
      );
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, sessionId, addMessage]);

  const handleNewChat = useCallback(async () => {
    if (sessionId) {
      await clearSession(sessionId).catch(() => {});
    }
    setMessages([]);
    setSessionId(null);
  }, [sessionId]);

  const handleSuggestBooking = useCallback((specialty) => {
    const msg = specialty
      ? `I'd like to book an appointment with a ${specialty} specialist`
      : "I'd like to book an appointment";
    handleSend(msg);
  }, [handleSend]);

  return (
    <div className="app">
      <Sidebar onNewChat={handleNewChat} />
      <main className="chat-main">
        <ChatHeader onNewChat={handleNewChat} />
        <div className="chat-messages">
          {messages.length === 0 ? (
            <WelcomeScreen onSuggestion={handleSend} />
          ) : (
            messages.map((msg) => (
              <Message
                key={msg.id}
                msg={msg}
                onSuggestBooking={handleSuggestBooking}
              />
            ))
          )}
          <div ref={messagesEndRef} />
        </div>
        <ChatInput onSend={handleSend} disabled={isLoading} />
      </main>
    </div>
  );
}
