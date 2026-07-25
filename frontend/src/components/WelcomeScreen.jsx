/**
 * WelcomeScreen — shown when no messages exist yet.
 */

const SUGGESTIONS = [
  { text: "I've had a severe headache and fever for two days", emoji: '🤒' },
  { text: 'Show me cardiologists in the Riyadh branch', emoji: '❤️' },
  { text: 'What specializations are available in Cairo?', emoji: '🏥' },
  { text: 'I want to book with Dr. Sarah Hassan', emoji: '📅' },
  { text: 'ما هي الأقسام المتاحة في فرع الإسكندرية؟', emoji: '🇦🇪' },
  { text: 'عندي ألم في الصدر منذ يومين', emoji: '💊' },
];

export default function WelcomeScreen({ onSuggestion }) {
  return (
    <div className="welcome-screen">
      <div className="welcome-icon">🩺</div>
      <h2>Al Shifa Medical Assistant</h2>
      <p>
        Describe your symptoms or ask about our doctors, branches, and specializations.
        I speak <strong>Arabic</strong> and <strong>English</strong>.
      </p>
      <div className="suggestion-chips">
        {SUGGESTIONS.map((s, i) => (
          <button
            key={i}
            className="chip"
            onClick={() => onSuggestion(s.text)}
          >
            {s.emoji} {s.text}
          </button>
        ))}
      </div>
    </div>
  );
}
