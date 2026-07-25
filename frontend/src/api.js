// API client for the Al Shifa Medical Chatbot backend

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Send a chat message and get a response.
 * @param {string} message
 * @param {string|null} sessionId
 * @returns {Promise<{session_id: string, response: object}>}
 */
export async function sendMessage(message, sessionId = null) {
  const res = await fetch(`${BASE_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Server error: ${res.status}`);
  }
  return res.json();
}

/**
 * Transcribe an audio blob.
 * @param {Blob} audioBlob
 * @returns {Promise<{transcribed_text: string}>}
 */
export async function transcribeAudio(audioBlob) {
  const formData = new FormData();
  formData.append('file', audioBlob, 'recording.webm');
  const res = await fetch(`${BASE_URL}/api/transcribe`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Transcription error: ${res.status}`);
  }
  return res.json();
}

/**
 * Get hospital data for sidebar.
 */
export async function getHospitalData() {
  const res = await fetch(`${BASE_URL}/api/hospital-data`);
  if (!res.ok) return null;
  return res.json();
}

/**
 * Clear a session.
 */
export async function clearSession(sessionId) {
  await fetch(`${BASE_URL}/api/chat/${sessionId}`, { method: 'DELETE' });
}
