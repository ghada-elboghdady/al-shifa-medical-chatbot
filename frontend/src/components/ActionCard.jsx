/**
 * ActionCard — renders structured action responses from the chatbot.
 * Handles: book_appointment, list_doctors, list_specializations, list_branches
 */

const BRANCH_FLAGS = {
  Cairo: '🇪🇬',
  Alexandria: '🇪🇬',
  Riyadh: '🇸🇦',
  Dubai: '🇦🇪',
};

function BookingCard({ data }) {
  return (
    <div className="action-card">
      <div className="action-card-header">
        <div className="action-card-icon booking">📅</div>
        <div>
          <div className="action-card-title">Appointment Booking</div>
          <div className="action-card-subtitle">Ready to confirm your appointment</div>
        </div>
      </div>
      <div className="action-card-body">
        <div className="action-field">
          <span className="action-field-label">Doctor</span>
          <span className="action-field-value highlight">{data.doctor_name}</span>
        </div>
        <div className="action-field">
          <span className="action-field-label">Specialty</span>
          <span className="action-field-value">{data.specialty}</span>
        </div>
        <div className="action-field">
          <span className="action-field-label">Branch</span>
          <span className="action-field-value">
            {BRANCH_FLAGS[data.branch] || '🏥'} {data.branch}
          </span>
        </div>
        <div className="action-field">
          <span className="action-field-label">Hospital</span>
          <span className="action-field-value">{data.hospital}</span>
        </div>
      </div>
      <button
        className="book-btn"
        onClick={() => alert(`Booking confirmed with ${data.doctor_name} at ${data.hospital}!\n\nIn a real system, this would open the booking form.`)}
      >
        ✅ Confirm Appointment
      </button>
    </div>
  );
}

function ListDoctorsCard({ data }) {
  return (
    <div className="action-card">
      <div className="action-card-header">
        <div className="action-card-icon list-doctors">👨‍⚕️</div>
        <div>
          <div className="action-card-title">{data.specialty} Specialists</div>
          <div className="action-card-subtitle">
            {BRANCH_FLAGS[data.branch] || '🏥'} {data.branch} Branch — {data.doctors?.length || 0} doctors
          </div>
        </div>
      </div>
      <div className="action-card-body">
        <div className="doctors-grid">
          {(data.doctors || []).map((doc, i) => (
            <div className="doctor-chip" key={doc.id || i}>
              <div className="doctor-avatar-sm">👤</div>
              <div className="doctor-chip-name">{doc.name}</div>
              {doc.experience_years && (
                <div className="doctor-chip-exp">{doc.experience_years}yr exp.</div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ListSpecializationsCard({ data }) {
  return (
    <div className="action-card">
      <div className="action-card-header">
        <div className="action-card-icon list-specs">🏥</div>
        <div>
          <div className="action-card-title">Available Specializations</div>
          <div className="action-card-subtitle">
            {BRANCH_FLAGS[data.branch] || '🏥'} {data.branch} Branch
          </div>
        </div>
      </div>
      <div className="action-card-body">
        <div className="spec-tags">
          {(data.specializations || []).map((spec, i) => (
            <span className="spec-tag" key={i}>{spec}</span>
          ))}
        </div>
      </div>
    </div>
  );
}

function ListBranchesCard({ data }) {
  return (
    <div className="action-card">
      <div className="action-card-header">
        <div className="action-card-icon list-branches">🌍</div>
        <div>
          <div className="action-card-title">Our Branches</div>
          <div className="action-card-subtitle">Al Shifa Medical Group locations</div>
        </div>
      </div>
      <div className="action-card-body">
        <div className="branch-cards">
          {(data.branches || []).map((branch, i) => (
            <div className="branch-card-item" key={i}>
              <div className="branch-card-flag">
                {BRANCH_FLAGS[branch.name] || '🏥'}
              </div>
              <div>
                <div className="branch-card-name">{branch.name}</div>
                <div className="branch-card-country">{branch.country} · {branch.phone}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function HumanHandoffCard({ data }) {
  return (
    <div className="action-card">
      <div className="action-card-header">
        <div className="action-card-icon list-specs">🎧</div>
        <div>
          <div className="action-card-title">Transferring to Agent</div>
          <div className="action-card-subtitle">Connecting you with a human representative</div>
        </div>
      </div>
      <div className="action-card-body">
        <p style={{ margin: '8px 0', fontSize: '14px' }}>
          {data.message || "Please hold on while we transfer your chat to an available customer service representative."}
        </p>
      </div>
    </div>
  );
}

export default function ActionCard({ data, onSuggestBooking }) {
  const action = data?.action;

  if (action === 'book_appointment') {
    return <BookingCard data={data} />;
  }
  if (action === 'list_doctors') {
    return <ListDoctorsCard data={data} />;
  }
  if (action === 'list_specializations') {
    return <ListSpecializationsCard data={data} />;
  }
  if (action === 'list_branches') {
    return <ListBranchesCard data={data} />;
  }
  if (action === 'human_handoff') {
    return <HumanHandoffCard data={data} />;
  }

  // Unknown action — fallback
  return (
    <div className="action-card">
      <div className="action-card-header">
        <div className="action-card-icon list-specs">ℹ️</div>
        <div>
          <div className="action-card-title">Information</div>
        </div>
      </div>
      <pre style={{ fontSize: '11px', color: 'var(--text-secondary)', overflowX: 'auto' }}>
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}
