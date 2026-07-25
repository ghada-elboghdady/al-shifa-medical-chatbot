/**
 * Message component — renders a single chat message (user or bot).
 * Handles: medical text responses, action cards, typing indicator.
 */

import ActionCard from './ActionCard';

function formatTime(date) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function isArabic(text = '') {
  return /[\u0600-\u06FF]/.test(text);
}

function TypingIndicator() {
  return (
    <div className="message-row bot">
      <div className="message-avatar">🩺</div>
      <div className="message-content">
        <div className="typing-indicator">
          <div className="typing-dot" />
          <div className="typing-dot" />
          <div className="typing-dot" />
        </div>
      </div>
    </div>
  );
}

function resolveResponse(resp) {
  if (!resp) return { type: 'general', answer: "I'm here to help. Could you please try again?" };

  let current = resp;
  if (typeof current === 'string') {
    try {
      current = JSON.parse(current);
    } catch {
      return { type: 'general', answer: current.replace(/```json|```/g, '').trim() };
    }
  }

  if (typeof current?.answer === 'string' && current.answer.trim().startsWith('{')) {
    try {
      const parsedInside = JSON.parse(current.answer);
      if (parsedInside && typeof parsedInside === 'object' && (parsedInside.type || parsedInside.action || parsedInside.answer)) {
        current = parsedInside;
      }
    } catch {
      // ignore
    }
  }

  return current;
}

function BotMessage({ msg, onSuggestBooking }) {
  const rawResponse = msg.response;
  const response = resolveResponse(rawResponse);

  // Action response (structured UI card)
  if (response?.type === 'action' || response?.action) {
    return (
      <div className="message-row bot">
        <div className="message-avatar">🩺</div>
        <div className="message-content">
          <ActionCard data={response} onSuggestBooking={onSuggestBooking} />
          <span className="message-time">{formatTime(new Date(msg.timestamp))}</span>
        </div>
      </div>
    );
  }

  // Extract the human-readable answer — NEVER show raw JSON
  const extractAnswer = (resp) => {
    if (!resp) return "I'm here to help. Could you please try again?";

    let text = "";

    // 1. Direct answer string
    if (typeof resp.answer === 'string' && resp.answer.trim()) {
      text = resp.answer.replace(/\\n/g, '\n').trim();
    } else if (typeof resp === 'string') {
      text = resp.replace(/```json|```/g, '').trim();
    } else if (typeof resp === 'object') {
      for (const key of ['answer', 'text', 'message', 'content', 'response']) {
        if (typeof resp[key] === 'string' && resp[key].trim()) {
          text = resp[key].replace(/\\n/g, '\n').trim();
          break;
        }
      }
    }

    if (!text) {
      text = typeof resp === 'string' ? resp : JSON.stringify(resp, null, 2);
    }

    // 2. If text still contains JSON fragments or braces, strip JSON syntax
    if (text.includes('"answer"') || text.includes('"type"') || text.startsWith('{') || text.includes('}')) {
      const ansMatch = text.match(/"answer"\s*:\s*"([\s\S]*?)"/);
      if (ansMatch && ansMatch[1]) {
        text = ansMatch[1].replace(/\\n/g, '\n').replace(/\\"/g, '"');
      } else {
        text = text
          .replace(/"(type|language|suggested_specialty|suggest_booking|action)"\s*:\s*"?[^",\n\}]+"?/g, '')
          .replace(/"answer"\s*:\s*/g, '')
          .replace(/[\{\}\[\]"]+/g, '')
          .replace(/^\s*,\s*/gm, '')
          .replace(/\n\s*\n/g, '\n')
          .trim();
      }
    }

    return text || "I'm here to help. Could you please try again?";
  };

  const text = extractAnswer(response);
  const lang = response?.language || (isArabic(text) ? 'ar' : 'en');
  const rtl = lang === 'ar';
  const suggestBooking = response?.suggest_booking;
  const suggestedSpec = response?.suggested_specialty;

  // Split text into paragraphs for nicer rendering
  const paragraphs = text.split(/\n\n+/).filter(Boolean);

  return (
    <div className="message-row bot">
      <div className="message-avatar">🩺</div>
      <div className="message-content">
        {lang && (
          <span className={`lang-badge ${lang}`}>
            {lang === 'ar' ? '🇦🇪 AR' : '🇬🇧 EN'}
          </span>
        )}
        <div className="message-bubble" dir={rtl ? 'rtl' : 'ltr'}>
          {paragraphs.length > 1
            ? paragraphs.map((p, i) => <p key={i} style={{ margin: '0 0 8px 0' }}>{p}</p>)
            : text
          }
        </div>
        {suggestBooking && suggestedSpec && (
          <button
            className="suggest-booking-banner"
            onClick={() => onSuggestBooking && onSuggestBooking(suggestedSpec)}
            title="Click to book an appointment"
          >
            📅 Book an appointment with a {suggestedSpec} specialist →
          </button>
        )}
        {suggestBooking && !suggestedSpec && (
          <button
            className="suggest-booking-banner"
            onClick={() => onSuggestBooking && onSuggestBooking()}
          >
            📅 Book an appointment at Al Shifa Medical Group →
          </button>
        )}
        <span className="message-time">{formatTime(new Date(msg.timestamp))}</span>
      </div>
    </div>
  );
}

function UserMessage({ msg }) {
  const text = msg.text;
  const rtl = isArabic(text);

  return (
    <div className="message-row user">
      <div className="message-avatar">👤</div>
      <div className="message-content">
        <div className="message-bubble" dir={rtl ? 'rtl' : 'ltr'}>
          {text}
        </div>
        <span className="message-time">{formatTime(new Date(msg.timestamp))}</span>
      </div>
    </div>
  );
}

export { TypingIndicator };

export default function Message({ msg, onSuggestBooking }) {
  if (msg.type === 'typing') {
    return <TypingIndicator />;
  }
  if (msg.role === 'user') {
    return <UserMessage msg={msg} />;
  }
  return <BotMessage msg={msg} onSuggestBooking={onSuggestBooking} />;
}
