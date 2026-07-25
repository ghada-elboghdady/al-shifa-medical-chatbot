# Al Shifa Medical Group — AI-Powered Medical Chatbot

> A full-stack AI chatbot for Al Shifa Medical Group that accepts bilingual (Arabic/English) patient descriptions, provides medical recommendations, and guides users toward booking the right doctor.

---

## 🎥 Project Demo Video

[![Watch Demo](https://img.shields.io/badge/▶️_Watch_Demo_Video-demo.mp4-blue?style=for-the-badge&logo=playstation)](./demo.mp4)

> 🎬 **[Click here to watch or download demo.mp4](./demo.mp4)**  
> *(Demonstrates bilingual chat, voice input, RAG medical context retrieval, and appointment booking cards)*

---



## System Design & Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  React Frontend (Vite)                  │
│   Chat UI · Action Cards · Voice Input · RTL Support    │
└──────────────────────┬──────────────────────────────────┘
                       │ REST API (HTTP)
┌──────────────────────▼──────────────────────────────────┐
│                  FastAPI Backend                         │
│                                                         │
│  POST /api/chat         POST /api/transcribe            │
│  GET  /api/hospital-data                                │
│                                                         │
│  ┌────────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │  LLM Service   │  │  RAG Service │  │  Voice Svc  │ │
│  │ Gemini 1.5 Flash│  │  ChromaDB   │  │Gemini Audio │ │
│  └────────────────┘  └──────────────┘  └─────────────┘ │
│                              │                          │
│                    ┌─────────▼────────┐                 │
│                    │ Hospital Dataset │                 │
│                    │ hospital_data.json│                │
│                    └──────────────────┘                 │
└─────────────────────────────────────────────────────────┘
```

### How it works

1. **User sends a message** (text or voice) in Arabic or English.
2. **Voice** (optional): Audio is sent to `/api/transcribe` → Gemini transcribes it to text.
3. **RAG retrieval**: The query is embedded with a multilingual model and matched against the hospital knowledge base in ChromaDB to retrieve the most relevant context (doctors, branches, specializations).
4. **LLM generation**: Gemini 1.5 Flash receives the system prompt (hospital identity + RAG context + conversation history) and generates a structured JSON response.
5. **Response routing**: The frontend reads the `type` field:
   - `"medical"` → renders a conversational text bubble with a booking suggestion
   - `"action"` → renders a rich action card (booking info, doctor list, specialization list)

---

## AI Models Used & Rationale

| Model | Purpose | Why |
|-------|---------|-----|
| **Google Gemini 1.5 Flash** | Medical chat + intent classification + response generation | Excellent Arabic/English bilingual support, strong instruction following, JSON mode, fast, free tier available |
| **Gemini 1.5 Flash (multimodal)** | Voice transcription | Same API, supports audio input natively (Arabic + English), no extra service needed |
| **paraphrase-multilingual-MiniLM-L12-v2** | Text embeddings for RAG | Compact, fast, supports Arabic/English, open-source, runs locally with no API key |

---

## Prompt Design Strategy

### Dual Response Mode
The system prompt instructs the LLM to classify every input into one of two modes:

- **Medical answer**: Return `{ "type": "medical", "answer": "...", "suggested_specialty": "...", "suggest_booking": true }`
- **Action response**: Return `{ "type": "action", "action": "book_appointment|list_doctors|list_specializations|list_branches", ... }`

This strict JSON-only constraint prevents mixed responses and makes frontend rendering deterministic.

### Hospital Grounding
RAG context is injected into the system prompt before each response, ensuring the LLM answers using only Al Shifa's actual data (not hallucinated doctors or branches).

### Language Detection
The LLM is instructed to detect the user's language from their input and respond in that same language. Arabic responses are flagged and rendered with RTL text direction.

### Booking Flow
When a user expresses booking intent, the prompt instructs the LLM to extract `doctor_name`, `specialty`, and `branch` from the conversation history and match them against the hospital dataset.

---

## Project Structure

```
dms_project/
├── data/
│   └── hospital_data.json          # Fictional hospital dataset
├── backend/
│   ├── main.py                     # FastAPI app
│   ├── requirements.txt
│   ├── .env.example                # Copy to .env and add your API key
│   ├── routes/
│   │   ├── chat.py                 # POST /api/chat
│   │   └── voice.py                # POST /api/transcribe
│   ├── services/
│   │   ├── llm_service.py          # Gemini integration + RAG context injection
│   │   └── rag_service.py          # ChromaDB vector store
│   └── prompts/
│       └── system_prompt.txt       # Hospital identity + response format instructions
└── frontend/
    ├── src/
    │   ├── App.jsx                 # Main app + session management
    │   ├── api.js                  # Backend API client
    │   ├── index.css               # Global styles (dark medical theme)
    │   ├── components/
    │   │   ├── Sidebar.jsx         # Hospital info panel
    │   │   ├── Message.jsx         # Chat bubble (text or action)
    │   │   ├── ActionCard.jsx      # Structured data cards
    │   │   ├── ChatInput.jsx       # Textarea + voice button
    │   │   └── WelcomeScreen.jsx   # Initial landing screen
    │   └── hooks/
    │       └── useVoiceRecorder.js # Mic recording + transcription hook
    └── index.html
```

---

## Setup & Run

### Prerequisites
- Python 3.10+
- Node.js 18+
- A Google Gemini API key ([get one free](https://aistudio.google.com/app/apikey))

### 1. Configure the API key

```bash
cd backend
cp .env.example .env
# Edit .env and set your GEMINI_API_KEY
```

### 2. Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Start the backend

```bash
cd backend
python main.py
# or: uvicorn main:app --reload
```

The backend will:
- Load the hospital dataset
- Download and initialize the multilingual embedding model (~150MB, first run only)
- Index all hospital data into ChromaDB
- Start on http://localhost:8000

### 4. Install & start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Hospital Test Dataset

**Hospital Group**: Al Shifa Medical Group (مجموعة الشفاء الطبية)  
**Hotline**: 19999

| Branch | Country | Specializations |
|--------|---------|----------------|
| Cairo | Egypt | Neurology, Cardiology, Orthopedics, Dermatology, Gastroenterology, Pulmonology, Endocrinology, Ophthalmology |
| Alexandria | Egypt | Cardiology, Neurology, Orthopedics, Dermatology, Oncology, Urology, Gynecology |
| Riyadh | Saudi Arabia | Cardiology, Neurology, Orthopedics, Pulmonology, Endocrinology, Rheumatology, Urology, Oncology |
| Dubai | UAE | Cardiology, Dermatology, Orthopedics, Gynecology, Ophthalmology, Plastic Surgery, Endocrinology, Gastroenterology |

**28 doctors** across all branches with realistic bios, experience levels, and multilingual capabilities.

---

## Example Conversations

### 1. Multi-turn medical conversation ending in a booking

```
User:  "I've been having a severe headache and fever for two days, what should I do?"
Bot:   [medical answer in English] + [📅 Book with a Neurology specialist →]

User:  "Could this be meningitis?"
Bot:   [follow-up medical answer, confirms serious concern, recommends urgent visit]

User:  "I want to book with Dr. Sarah Hassan in Cairo"
Bot:   [ACTION CARD: book_appointment]
       Doctor: Dr. Sarah Hassan
       Specialty: Neurology
       Branch: Cairo
       Hospital: Al Shifa Medical Group - Cairo Branch
       [✅ Confirm Appointment button]
```

### 2. Listing doctors / specializations

```
User:  "Who are the cardiologists at the Riyadh branch?"
Bot:   [ACTION CARD: list_doctors]
       ❤️ Cardiology Specialists — 🇸🇦 Riyadh Branch (2 doctors)
       👤 Dr. Khalid Al-Mansouri — 22yr exp.
       👤 Dr. Rania Al-Otaibi — 11yr exp.

User:  "What specializations are available at the Alexandria branch?"
Bot:   [ACTION CARD: list_specializations]
       🏥 Available Specializations — 🇪🇬 Alexandria Branch
       [Cardiology] [Neurology] [Orthopedics] [Dermatology] [Oncology] [Urology] [Gynecology]
```

### 3. Arabic conversation with voice input

```
User:  [🎤 records voice in Arabic] → transcribed: "عندي ألم في الصدر منذ يومين"
Bot:   [medical answer in Arabic] ألم الصدر يمكن أن يكون له أسباب متعددة...
       [📅 احجز موعدًا مع أخصائي قلب →]
```

---

## API Reference

### `POST /api/chat`
```json
Request:  { "message": "string", "session_id": "string|null" }
Response: { "session_id": "string", "response": { ... } }
```

### `POST /api/transcribe`
```
Request:  multipart/form-data with audio file
Response: { "transcribed_text": "string" }
```

### `GET /api/hospital-data`
Returns the full hospital dataset (branches, doctors, specializations).
