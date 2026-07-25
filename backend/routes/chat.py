"""
Chat route — handles multi-turn conversation with the medical chatbot.
Includes a smart local fallback so answers are ALWAYS provided.
"""

import uuid
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

try:
    from google.genai import errors as genai_errors
except ImportError:
    genai_errors = None

from services import llm_service, rag_service

router = APIRouter()

# In-memory session store: { session_id: [{ role, content }] }
_sessions: Dict[str, List[Dict]] = {}


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    response: Dict[str, Any]


def _detect_language(text: str) -> str:
    """Detect if text is primarily Arabic or English."""
    arabic_chars = len(re.findall(r'[\u0600-\u06FF]', text))
    return "ar" if arabic_chars > len(text) * 0.3 else "en"


SPECIALTY_ALIASES = {
    'neurology': 'Neurology',
    'neurologist': 'Neurology',
    'أعصاب': 'Neurology',
    'مخ وأعصاب': 'Neurology',
    'cardiology': 'Cardiology',
    'cardiologist': 'Cardiology',
    'heart': 'Cardiology',
    'قلب': 'Cardiology',
    'orthopedics': 'Orthopedics',
    'orthopedic': 'Orthopedics',
    'bone': 'Orthopedics',
    'عظام': 'Orthopedics',
    'dermatology': 'Dermatology',
    'dermatologist': 'Dermatology',
    'skin': 'Dermatology',
    'جلدية': 'Dermatology',
    'جلد': 'Dermatology',
    'gastroenterology': 'Gastroenterology',
    'gastroenterologist': 'Gastroenterology',
    'stomach': 'Gastroenterology',
    'belly': 'Gastroenterology',
    'هضمي': 'Gastroenterology',
    'معدة': 'Gastroenterology',
    'pulmonology': 'Pulmonology',
    'pulmonologist': 'Pulmonology',
    'lung': 'Pulmonology',
    'تنفسي': 'Pulmonology',
    'صدارية': 'Pulmonology',
    'endocrinology': 'Endocrinology',
    'endocrinologist': 'Endocrinology',
    'diabetes': 'Endocrinology',
    'غدد': 'Endocrinology',
    'ophthalmology': 'Ophthalmology',
    'ophthalmologist': 'Ophthalmology',
    'eye': 'Ophthalmology',
    'عيون': 'Ophthalmology',
    'oncology': 'Oncology',
    'oncologist': 'Oncology',
    'cancer': 'Oncology',
    'أورام': 'Oncology',
    'urology': 'Urology',
    'urologist': 'Urology',
    'مسالك': 'Urology',
    'gynecology': 'Gynecology',
    'gynecologist': 'Gynecology',
    'ob/gyn': 'Gynecology',
    'obstetrics': 'Gynecology',
    'نساء': 'Gynecology',
    'توليد': 'Gynecology',
    'dentistry': 'Dentistry',
    'dentist': 'Dentistry',
    'dental': 'Dentistry',
    'teeth': 'Dentistry',
    'tooth': 'Dentistry',
    'أسنان': 'Dentistry',
    'pediatrics': 'Pediatrics',
    'pediatrician': 'Pediatrics',
    'child': 'Pediatrics',
    'children': 'Pediatrics',
    'أطفال': 'Pediatrics',
    'طفل': 'Pediatrics',
    'internal medicine': 'Internal Medicine',
    'internal': 'Internal Medicine',
    'باطنة': 'Internal Medicine',
    'allergy': 'Allergy & Immunology',
    'immunology': 'Allergy & Immunology',
    'حساسية': 'Allergy & Immunology',
    'rheumatology': 'Rheumatology',
    'روماتيزم': 'Rheumatology',
    'plastic surgery': 'Plastic Surgery',
    'تجميل': 'Plastic Surgery',
}

BRANCH_ALIASES = {
    'cairo': 'Cairo',
    'القاهرة': 'Cairo',
    'alexandria': 'Alexandria',
    'الإسكندرية': 'Alexandria',
    'الاسكندرية': 'Alexandria',
    'riyadh': 'Riyadh',
    'الرياض': 'Riyadh',
    'dubai': 'Dubai',
    'دبي': 'Dubai',
}


def _generate_local_response(message: str) -> Dict[str, Any]:
    """
    Generate a helpful response locally using hospital data, intent, and entity extraction.
    This acts as a smart local engine when the external AI API is unavailable.
    """
    msg_lower = message.lower().strip()
    lang = _detect_language(message)
    hospital_data = rag_service.get_hospital_data()
    doctors = hospital_data.get("doctors", [])
    branches = hospital_data.get("branches", [])

    # Entity 1: Detect Branch
    detected_branch = None
    for b_key, b_val in BRANCH_ALIASES.items():
        if b_key in msg_lower:
            detected_branch = b_val
            break

    # Entity 2: Detect Specialty
    detected_specialty = None
    for s_key, s_val in SPECIALTY_ALIASES.items():
        if s_key in msg_lower:
            detected_specialty = s_val
            break

    # Entity 3: Detect Doctor Name
    detected_doctor = None
    for doc in doctors:
        d_name_en = doc["name"].lower().replace("dr. ", "").replace("dr ", "").strip()
        d_name_ar = doc["name_ar"].lower().replace("د. ", "").replace("د ", "").strip()

        if d_name_en in msg_lower or d_name_ar in msg_lower:
            detected_doctor = doc
            break
        name_parts_en = [p for p in d_name_en.split() if len(p) > 3]
        if any(p in msg_lower for p in name_parts_en):
            detected_doctor = doc
            break
        name_parts_ar = [p for p in d_name_ar.split() if len(p) > 3]
        if any(p in msg_lower for p in name_parts_ar):
            detected_doctor = doc
            break

    # --- Greetings ---
    greetings_en = ['hello', 'hi', 'hey', 'good morning', 'good evening', 'good afternoon']
    greetings_ar = ['مرحبا', 'اهلا', 'السلام عليكم', 'صباح الخير', 'مساء الخير']

    if any(g == msg_lower or f"{g} " in msg_lower for g in greetings_en):
        return {
            "type": "general",
            "language": "en",
            "answer": "Hello! 👋 Welcome to Al Shifa Medical Group. I'm your medical assistant. How can I help you today?\n\nYou can ask me about:\n• Our doctors and specializations\n• Branch locations (Cairo, Alexandria, Riyadh, Dubai)\n• Book an appointment\n• Medical advice and symptoms"
        }
    if any(g == msg_lower or f"{g} " in msg_lower for g in greetings_ar):
        return {
            "type": "general",
            "language": "ar",
            "answer": "مرحباً! 👋 أهلاً بك في مجموعة الشفاء الطبية. أنا مساعدك الطبي. كيف يمكنني مساعدتك اليوم؟\n\nيمكنك السؤال عن:\n• أطبائنا وتخصصاتنا\n• فروعنا (القاهرة، الإسكندرية، الرياض، دبي)\n• حجز موعد\n• استشارة طبية"
        }

    # --- Booking Intent ---
    booking_kws = ['book', 'appointment', 'reserve', 'حجز', 'موعد', 'احجز']
    is_booking = any(kw in msg_lower for kw in booking_kws)

    if is_booking:
        if detected_doctor:
            doc = detected_doctor
            return {
                "type": "action",
                "action": "book_appointment",
                "doctor_name": doc["name"],
                "specialty": doc["specialty"],
                "branch": doc["branch"],
                "hospital": doc.get("hospital", f"Al Shifa Medical Group - {doc['branch']} Branch"),
                "hospital_id": "al_shifa_group",
                "branch_id": doc["branch_id"],
                "doctor_id": doc["id"]
            }

        # Filter doctors by detected branch and/or specialty
        if detected_specialty or detected_branch:
            # Check if requested specialty exists in hospital data
            all_hospital_specs = set()
            branch_specs_map = {}
            for b in branches:
                b_name = b.get("name", "").replace(" Branch", "").strip()
                specs = set(b.get("specializations", []))
                branch_specs_map[b_name.lower()] = specs
                all_hospital_specs.update(specs)

            if detected_specialty and detected_specialty not in all_hospital_specs:
                specs_list = sorted(list(all_hospital_specs))
                specs_str = ", ".join(specs_list)
                if lang == "ar":
                    return {
                        "type": "general",
                        "language": "ar",
                        "answer": f"عذراً، تخصص {detected_specialty} غير متاح حالياً في مجموعة الشفاء الطبية. 🏥\n\nالتخصصات المتاحة لدينا في فروعنا تشمل:\n• {specs_str}\n\nهل ترغب في حجز موعد في أحد التخصصات المتاحة؟"
                    }
                return {
                    "type": "general",
                    "language": "en",
                    "answer": f"We're sorry, but **{detected_specialty}** is currently not an available specialization at Al Shifa Medical Group. 🏥\n\nOur available specializations across our branches include:\n• {specs_str}\n\nWould you like to book an appointment in one of our available departments?"
                }

            # Check if requested specialty exists at the requested branch
            if detected_specialty and detected_branch:
                branch_specs = branch_specs_map.get(detected_branch.lower(), set())
                if branch_specs and detected_specialty not in branch_specs:
                    available_at_branches = [b.get("name", "").replace(" Branch", "").strip() for b in branches if detected_specialty in b.get("specializations", [])]
                    branches_str = ", ".join(available_at_branches)
                    if lang == "ar":
                        return {
                            "type": "general",
                            "language": "ar",
                            "answer": f"عذراً، تخصص {detected_specialty} غير متاح في فرع {detected_branch}. 🏥\n\nهذا التخصص متاح في الفروع التالية: {branches_str}.\n\nهل ترغب في الحجز في أحد هذه الفروع؟"
                        }
                    return {
                        "type": "general",
                        "language": "en",
                        "answer": f"We're sorry, but **{detected_specialty}** is not available at our **{detected_branch}** branch. 🏥\n\nIt is available at our **{branches_str}** branch(es).\n\nWould you like to book an appointment at one of these branches?"
                    }

            matching_doctors = doctors
            if detected_branch:
                matching_doctors = [d for d in matching_doctors if d.get("branch", "").lower() == detected_branch.lower()]
            if detected_specialty:
                matching_doctors = [d for d in matching_doctors if d.get("specialty", "").lower() == detected_specialty.lower()]

            if matching_doctors:
                doc = matching_doctors[0]
                return {
                    "type": "action",
                    "action": "book_appointment",
                    "doctor_name": doc["name"],
                    "specialty": doc["specialty"],
                    "branch": doc["branch"],
                    "hospital": doc.get("hospital", f"Al Shifa Medical Group - {doc['branch']} Branch"),
                    "hospital_id": "al_shifa_group",
                    "branch_id": doc["branch_id"],
                    "doctor_id": doc["id"]
                }
            elif detected_specialty:
                target_branch = detected_branch or "Cairo"
                return {
                    "type": "action",
                    "action": "book_appointment",
                    "doctor_name": f"Al Shifa {detected_specialty} Specialist",
                    "specialty": detected_specialty,
                    "branch": target_branch,
                    "hospital": f"Al Shifa Medical Group - {target_branch} Branch",
                    "hospital_id": "al_shifa_group",
                    "branch_id": f"{target_branch.lower()}_branch",
                    "doctor_id": "doc_general"
                }

        if lang == "ar":
            return {
                "type": "general",
                "language": "ar",
                "answer": "يسعدني مساعدتك في حجز موعد! 📅\n\nمن فضلك أخبرني:\n• ما هو التخصص الذي تحتاجه؟\n• هل تفضل فرع معين؟ (القاهرة، الإسكندرية، الرياض، دبي)\n\nيمكنك قول مثلاً: \"أريد حجز موعد مع طبيب أعصاب في الرياض\""
            }
        return {
            "type": "general",
            "language": "en",
            "answer": "I'd be happy to help you book an appointment! 📅\n\nPlease tell me:\n• What specialty do you need?\n• Do you prefer a specific branch? (Cairo, Alexandria, Riyadh, Dubai)\n\nYou can say something like: \"I want to book an appointment with a neurologist in Riyadh\""
        }

    # --- Doctors Intent ---
    doctor_kws = ['doctor', 'doctors', 'طبيب', 'دكتور', 'أطباء', 'specialist', 'أخصائي']
    is_doctor_query = any(kw in msg_lower for kw in doctor_kws) or (detected_specialty is not None) or (detected_doctor is not None)

    if is_doctor_query:
        filtered_docs = doctors
        if detected_doctor:
            filtered_docs = [detected_doctor]
        else:
            if detected_branch:
                filtered_docs = [d for d in filtered_docs if d.get("branch", "").lower() == detected_branch.lower()]
            if detected_specialty:
                filtered_docs = [d for d in filtered_docs if d.get("specialty", "").lower() == detected_specialty.lower()]

        if filtered_docs:
            return {
                "type": "action",
                "action": "list_doctors",
                "specialty": detected_specialty or "All Specialties",
                "branch": detected_branch or "All Branches",
                "doctors": [
                    {"id": d["id"], "name": d["name"], "specialty": d["specialty"],
                     "experience_years": d.get("experience_years", 0)}
                    for d in filtered_docs[:10]
                ]
            }

    # --- Branches Intent ---
    branch_kws = ['branch', 'branches', 'location', 'locations', 'where', 'فرع', 'فروع', 'أين', 'عنوان']
    if any(kw in msg_lower for kw in branch_kws) and not is_doctor_query:
        if branches:
            return {
                "type": "action",
                "action": "list_branches",
                "branches": [
                    {"id": b["id"], "name": b["name"], "country": b["country"], "phone": b["phone"]}
                    for b in branches
                ]
            }

    # --- Specializations Intent ---
    spec_kws = ['specializ', 'specialty', 'department', 'تخصص', 'قسم']
    if any(kw in msg_lower for kw in spec_kws) and not is_doctor_query:
        all_specs = set()
        target_branches = branches
        if detected_branch:
            target_branches = [b for b in branches if b.get("name", "").lower().startswith(detected_branch.lower())]
        for b in target_branches:
            all_specs.update(b.get("specializations", []))
        if all_specs:
            return {
                "type": "action",
                "action": "list_specializations",
                "branch": detected_branch or "All Branches",
                "specializations": sorted(list(all_specs))
            }

    # --- Medical symptoms (common keywords) ---
    symptom_map = {
        'headache': ('Neurology', 'Headaches can be caused by tension, stress, dehydration, lack of sleep, or underlying conditions like migraines.'),
        'صداع': ('Neurology', 'الصداع قد يكون ناتجاً عن التوتر، الإجهاد، الجفاف، قلة النوم، أو حالات كامنة مثل الصداع النصفي.'),
        'heart': ('Cardiology', 'Heart-related symptoms should always be taken seriously. Common concerns include chest pain, palpitations, and shortness of breath.'),
        'قلب': ('Cardiology', 'أعراض القلب يجب أخذها على محمل الجد دائماً. من الأعراض الشائعة ألم الصدر، خفقان القلب، وضيق التنفس.'),
        'chest': ('Cardiology', 'Chest pain can have many causes. If severe or sudden, please seek emergency care immediately.'),
        'صدر': ('Cardiology', 'ألم الصدر يمكن أن يكون له أسباب عديدة. إذا كان شديدًا أو مفاجئًا، يرجى طلب الرعاية الطارئة فورًا.'),
        'stomach': ('Gastroenterology', 'Stomach issues can include pain, bloating, nausea, or acid reflux. Dietary changes often help.'),
        'belly': ('Gastroenterology', 'Stomach issues can include pain, bloating, nausea, or acid reflux. Dietary changes often help.'),
        'معدة': ('Gastroenterology', 'مشاكل المعدة قد تشمل الألم، الانتفاخ، الغثيان، أو ارتجاع الحمض.'),
        'بطن': ('Gastroenterology', 'مشاكل البطن قد تشمل الألم، الانتفاخ، الغثيان، أو ارتجاع الحمض.'),
        'skin': ('Dermatology', 'Skin conditions range from rashes and acne to more serious conditions. A dermatologist can help diagnose and treat.'),
        'جلد': ('Dermatology', 'حالات الجلد تتراوح من الطفح الجلدي وحب الشباب إلى حالات أكثر خطورة.'),
        'bone': ('Orthopedics', 'Bone and joint issues may include fractures, arthritis, or sports injuries.'),
        'عظام': ('Orthopedics', 'مشاكل العظام والمفاصل قد تشمل الكسور، التهاب المفاصل، أو إصابات رياضية.'),
        'leg': ('Orthopedics', 'Leg pain can be caused by muscle cramps, joint issues, or nerve problems.'),
        'رجل': ('Orthopedics', 'ألم الساق يمكن أن يكون ناتجًا عن تشنجات العضلات، مشاكل المفاصل، أو مشاكل الأعصاب.'),
        'arm': ('Orthopedics', 'Arm pain can be related to muscle strain, joint issues, or nerve problems.'),
        'ذراع': ('Orthopedics', 'ألم الذراع يمكن أن يكون مرتبطًا بإجهاد العضلات، مشاكل المفاصل، أو مشاكل الأعصاب.'),
        'eye': ('Ophthalmology', 'Eye concerns may include vision changes, redness, dryness, or pain.'),
        'عين': ('Ophthalmology', 'مشاكل العين قد تشمل تغيرات في الرؤية، احمرار، جفاف، أو ألم.'),
        'child': ('Pediatrics', 'For children\'s health concerns, our pediatric specialists provide comprehensive care.'),
        'طفل': ('Pediatrics', 'لمخاوف صحة الأطفال، يقدم أخصائيو الأطفال لدينا رعاية شاملة.'),
        'teeth': ('Dentistry', 'Dental issues including toothaches, gum problems, and oral health require a dental specialist.'),
        'أسنان': ('Dentistry', 'مشاكل الأسنان بما في ذلك ألم الأسنان، مشاكل اللثة، وصحة الفم تتطلب أخصائي أسنان.'),
        'pregnant': ('Obstetrics & Gynecology', 'Pregnancy care is important for both mother and baby. Regular check-ups are essential.'),
        'حامل': ('Obstetrics & Gynecology', 'رعاية الحمل مهمة لكل من الأم والطفل. الفحوصات المنتظمة ضرورية.'),
        'back pain': ('Orthopedics', 'Back pain is one of the most common complaints. It can be caused by poor posture, muscle strain, or disc problems.'),
        'fever': ('Internal Medicine', 'Fever is usually a sign that your body is fighting an infection. If it persists or is high, seek medical attention.'),
        'حمى': ('Internal Medicine', 'الحمى عادة علامة على أن جسمك يحارب عدوى. إذا استمرت أو كانت مرتفعة، اطلب رعاية طبية.'),
        'cough': ('Pulmonology', 'A persistent cough can be caused by infections, allergies, or respiratory conditions.'),
        'سعال': ('Pulmonology', 'السعال المستمر قد يكون ناتجاً عن عدوى، حساسية، أو حالات تنفسية.'),
        'allergy': ('Allergy & Immunology', 'Allergies can cause sneezing, itching, watery eyes, and skin reactions. Identification and management is key.'),
        'حساسية': ('Allergy & Immunology', 'الحساسية قد تسبب العطاس، الحكة، دموع العين، وردود فعل جلدية.'),
    }

    for keyword, (specialty, advice) in symptom_map.items():
        if keyword in msg_lower:
            if lang == "ar":
                return {
                    "type": "medical",
                    "language": "ar",
                    "answer": f"{advice}\n\nننصحك بشدة بزيارة أحد أخصائيي {specialty} في مجموعة الشفاء الطبية للحصول على تشخيص دقيق وخطة علاج مناسبة.\n\nهل ترغب في حجز موعد؟",
                    "suggested_specialty": specialty,
                    "suggest_booking": True
                }
            return {
                "type": "medical",
                "language": "en",
                "answer": f"{advice}\n\nWe strongly recommend consulting with one of our {specialty} specialists at Al Shifa Medical Group for an accurate diagnosis and treatment plan.\n\nWould you like me to help you book an appointment?",
                "suggested_specialty": specialty,
                "suggest_booking": True
            }

    # --- Default response ---
    if lang == "ar":
        return {
            "type": "general",
            "language": "ar",
            "answer": "شكراً لتواصلك مع مجموعة الشفاء الطبية! 🏥\n\nيمكنني مساعدتك في:\n• وصف أعراضك للحصول على نصيحة طبية\n• البحث عن أطباء وتخصصات\n• معرفة فروعنا ومواقعها\n• حجز موعد\n\nكيف يمكنني مساعدتك؟"
        }
    return {
        "type": "general",
        "language": "en",
        "answer": "Thank you for reaching out to Al Shifa Medical Group! 🏥\n\nI can help you with:\n• Describing your symptoms for medical guidance\n• Finding doctors and specializations\n• Learning about our branch locations\n• Booking an appointment\n\nHow can I assist you today?"
    }


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint.
    Accepts a patient message and returns either a medical answer or a structured action.
    Always provides an answer — uses local fallback if AI API is unavailable.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # Create or reuse session
    session_id = request.session_id or str(uuid.uuid4())
    if session_id not in _sessions:
        _sessions[session_id] = []

    history = _sessions[session_id]

    # Get LLM response
    try:
        response = await llm_service.chat(
            message=request.message,
            history=history,
            session_id=session_id,
        )
    except Exception as exc:
        # Detect Gemini API errors and use LOCAL FALLBACK instead of error messages
        exc_str = str(exc)
        print(f"[Chat] AI API error: {exc_str[:200]}")
        
        if "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str:
            print("[Chat] Rate limited — using local fallback")
            response = _generate_local_response(request.message)
        elif "503" in exc_str or "UNAVAILABLE" in exc_str:
            print("[Chat] Service unavailable — using local fallback")
            response = _generate_local_response(request.message)
        elif "403" in exc_str or "PERMISSION_DENIED" in exc_str:
            print("[Chat] Permission denied — using local fallback")
            response = _generate_local_response(request.message)
        elif "404" in exc_str or "NOT_FOUND" in exc_str:
            print("[Chat] Model not found — using local fallback")
            response = _generate_local_response(request.message)
        elif "400" in exc_str or "INVALID_ARGUMENT" in exc_str or "API_KEY" in exc_str.upper():
            print("[Chat] Invalid API key — using local fallback")
            response = _generate_local_response(request.message)
        else:
            print("[Chat] Unknown error — using local fallback")
            response = _generate_local_response(request.message)

    # Store the assistant response as text for context (never store raw JSON/dict objects in history)
    if "answer" in response and isinstance(response["answer"], str) and not response["answer"].strip().startswith('{'):
        assistant_content = response["answer"]
    elif response.get("type") == "action" or "action" in response:
        act = response.get("action", "")
        if act == "book_appointment":
            assistant_content = f"Showed appointment booking card for {response.get('doctor_name', 'specialist')} ({response.get('specialty', '')})."
        elif act == "list_doctors":
            assistant_content = f"Listed available {response.get('specialty', '')} doctors."
        elif act == "list_branches":
            assistant_content = "Listed hospital branches (Cairo, Alexandria, Riyadh, Dubai)."
        elif act == "list_specializations":
            assistant_content = f"Listed available specializations for {response.get('branch', 'hospital')}."
        else:
            assistant_content = f"Provided action options for {act}."
    else:
        assistant_content = "Provided assistance to patient."

    history.append({"role": "assistant", "content": assistant_content})

    # Limit history to last 20 turns
    if len(history) > 20:
        _sessions[session_id] = history[-20:]

    return ChatResponse(session_id=session_id, response=response)


@router.delete("/chat/{session_id}")
async def clear_session(session_id: str):
    """Clear a conversation session."""
    if session_id in _sessions:
        del _sessions[session_id]
    return {"status": "cleared", "session_id": session_id}


@router.get("/chat/{session_id}/history")
async def get_history(session_id: str):
    """Get conversation history for a session."""
    return {
        "session_id": session_id,
        "history": _sessions.get(session_id, []),
    }
