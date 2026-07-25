/**
 * Sidebar — hospital info panel with branches and hotline.
 */

const BRANCHES = [
  { name: 'Cairo', country: 'Egypt', dotClass: 'cairo', emoji: '🇪🇬' },
  { name: 'Alexandria', country: 'Egypt', dotClass: 'alexandria', emoji: '🇪🇬' },
  { name: 'Riyadh', country: 'Saudi Arabia', dotClass: 'riyadh', emoji: '🇸🇦' },
  { name: 'Dubai', country: 'UAE', dotClass: 'dubai', emoji: '🇦🇪' },
];

export default function Sidebar({ onNewChat }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="hospital-logo">
          <div className="logo-icon">🏥</div>
          <div className="hospital-name">
            <h1>Al Shifa Medical Group</h1>
            <p>مجموعة الشفاء الطبية</p>
          </div>
        </div>
        <button className="new-chat-btn" onClick={onNewChat}>
          ✏️ New Conversation
        </button>
      </div>

      <div className="sidebar-body">
        <div className="sidebar-section-title">Our Branches</div>
        <ul className="branch-list">
          {BRANCHES.map((b) => (
            <li key={b.name} className="branch-item">
              <div className={`branch-dot ${b.dotClass}`} />
              <div className="branch-info">
                <div className="name">{b.emoji} {b.name}</div>
                <div className="country">{b.country}</div>
              </div>
            </li>
          ))}
        </ul>

        <div className="sidebar-section-title">Specializations</div>
        <div style={{ padding: '0 8px', display: 'flex', flexWrap: 'wrap', gap: '5px', marginBottom: '16px' }}>
          {['Neurology', 'Cardiology', 'Orthopedics', 'Dermatology', 'Oncology',
            'Gastroenterology', 'Pulmonology', 'Endocrinology', 'Ophthalmology',
            'Gynecology', 'Urology', 'Rheumatology'].map((s) => (
            <span key={s} style={{
              fontSize: '10px',
              padding: '3px 8px',
              background: 'rgba(59,130,246,0.1)',
              border: '1px solid rgba(59,130,246,0.2)',
              borderRadius: '20px',
              color: 'var(--accent-blue)',
            }}>
              {s}
            </span>
          ))}
        </div>

        <div className="sidebar-section-title">Quick Questions</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {[
            'What branches do you have?',
            'Show cardiologists in Cairo',
            'I have a headache and fever',
          ].map((q, i) => (
            <div key={i} style={{
              padding: '8px 10px',
              fontSize: '11px',
              color: 'var(--text-secondary)',
              borderRadius: 'var(--radius-sm)',
              cursor: 'default',
              lineHeight: 1.4,
            }}>
              💬 {q}
            </div>
          ))}
        </div>
      </div>

      <div className="sidebar-footer">
        <div className="hotline-badge">
          <span className="icon">📞</span>
          <div>
            <div className="label">Emergency Hotline</div>
            <div className="number">19999</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
