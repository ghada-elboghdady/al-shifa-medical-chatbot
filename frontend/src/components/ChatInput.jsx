/**
 * ChatInput — textarea with voice recording button and send button.
 */

import { useState, useRef, useEffect } from 'react';
import { useVoiceRecorder } from '../hooks/useVoiceRecorder';

export default function ChatInput({ onSend, disabled }) {
  const [text, setText] = useState('');
  const [transcribedPreview, setTranscribedPreview] = useState('');
  const textareaRef = useRef(null);

  const { isRecording, isTranscribing, startRecording, stopRecording, error: voiceError } =
    useVoiceRecorder({
      onTranscribed: (t) => {
        setTranscribedPreview(t);
        setText(t);
      },
    });

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 120) + 'px';
    }
  }, [text]);

  const handleSend = () => {
    const msg = text.trim();
    if (!msg || disabled) return;
    onSend(msg);
    setText('');
    setTranscribedPreview('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleMicClick = () => {
    if (isRecording) {
      stopRecording();
    } else {
      setTranscribedPreview('');
      startRecording();
    }
  };

  return (
    <div className="chat-input-area">
      {transcribedPreview && (
        <div className="transcribe-preview">
          <span className="label">🎤 Transcribed:</span>
          <span>{transcribedPreview}</span>
        </div>
      )}
      {voiceError && (
        <div style={{ fontSize: '11px', color: 'var(--accent-red)', marginBottom: '6px', padding: '0 4px' }}>
          ⚠️ {voiceError}
        </div>
      )}
      <div className="input-container">
        <textarea
          ref={textareaRef}
          className="chat-textarea"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isRecording ? '🔴 Recording... click mic to stop' : isTranscribing ? '⏳ Transcribing...' : 'Describe your symptoms or ask a question... (Arabic or English)'}
          disabled={disabled || isTranscribing}
          rows={1}
        />
        <div className="input-actions">
          <button
            id="mic-btn"
            className={`icon-btn mic-btn ${isRecording ? 'recording' : ''}`}
            onClick={handleMicClick}
            disabled={disabled || isTranscribing}
            title={isRecording ? 'Stop recording' : 'Record voice message'}
          >
            {isRecording ? '⏹️' : isTranscribing ? '⏳' : '🎤'}
          </button>
          <button
            id="send-btn"
            className="icon-btn send-btn"
            onClick={handleSend}
            disabled={!text.trim() || disabled}
            title="Send message"
          >
            ➤
          </button>
        </div>
      </div>
      <div className="input-hint">
        <span>⏎ Enter to send</span>
        <span>⇧⏎ New line</span>
        <span>🌐 Arabic & English supported</span>
      </div>
    </div>
  );
}
