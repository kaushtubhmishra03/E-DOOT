import os
import requests
from typing import Dict, Any, List

RED_FLAG_KEYWORDS = [
    "chest pain", "heart attack", "cant breathe", "difficulty breathing", "shortness of breath",
    "unconscious", "passed out", "stroke", "facial droop", "slurred speech", "severe bleeding",
    "head trauma", "poison", "choking", "anaphylaxis", "severe burn",
    # Hindi keywords
    "सीने में दर्द", "सांस फूलना", "बेहोश", "दौरा", "खून बहना", "हार्ट अटैक",
    # Marathi keywords
    "छातीत दुखणे", "श्वास घेण्यास त्रास", "शुद्ध हरपणे", "रक्तस्त्राव"
]


class GeminiHealthAssistant:
    """Provides patient doubt-clearing powered by Gemini with clinical red-flag guardrails."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()

    def check_for_emergency(self, query: str) -> bool:
        """Scan user query for critical emergency keywords."""
        q_lower = query.lower()
        return any(flag in q_lower for flag in RED_FLAG_KEYWORDS)

    def answer_health_doubt(self, query: str, language: str = "en") -> Dict[str, Any]:
        """
        Process a user health doubt.
        If emergency keywords are present, interrupts with immediate SOS redirection.
        Otherwise queries Gemini Flash or smart fallback.
        """
        # Red-Flag Emergency Guardrail
        if self.check_for_emergency(query):
            emergency_messages = {
                "en": (
                    "🚨 **CRITICAL EMERGENCY WARNING**\n\n"
                    "The symptoms you described may be life-threatening and require immediate physical medical care. "
                    "**Do not wait for online advice!**\n\n"
                    "👉 **Tap the red Emergency SOS button on your screen immediately or dial 108 / 112.**"
                ),
                "hi": (
                    "🚨 **गंभीर आपातकालीन चेतावनी**\n\n"
                    "आपके द्वारा बताए गए लक्षण जानलेवा हो सकते हैं और तत्काल अस्पताल में इलाज की आवश्यकता है। "
                    "**ऑनलाइन उत्तर की प्रतीक्षा न करें!**\n\n"
                    "👉 **तुरंत स्क्रीन पर लाल रंग का Emergency SOS बटन दबाएं या 108 / 112 पर कॉल करें।**"
                ),
                "mr": (
                    "🚨 **तातडीचा इशारा**\n\n"
                    "आपण वर्णन केलेली लक्षणे गंभीर असू शकतात आणि त्वरित वैद्यकीय उपचारांची गरज आहे. "
                    "**कृपया वाट पाहू नका!**\n\n"
                    "👉 **त्वरित स्क्रीनवरील लाल Emergency SOS बटण दाबा किंवा 108 / 112 वर कॉल करा.**"
                ),
            }
            return {
                "status": "emergency_intercept",
                "is_emergency": True,
                "answer": emergency_messages.get(language, emergency_messages["en"]),
                "provider": "e_doot_safety_guardrail",
            }

        # Attempt Gemini 2.5/1.5 Flash API call if key exists
        if self.api_key:
            try:
                endpoint = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
                    f"?key={self.api_key}"
                )
                system_instruction = (
                    f"You are 'Arogya Saathi', the compassionate health assistant on the E-Doot healthcare platform. "
                    f"Respond in {language}. Provide clear, friendly, educational answers to general health doubts, "
                    f"diet, lifestyle, and medication timing concepts. Keep answers brief (max 3-4 bullet points). "
                    f"Always end with a short note advising consultation with their doctor for personalized prescription advice. "
                    f"Never provide formal diagnoses."
                )
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": system_instruction},
                                {"text": f"User question: {query}"}
                            ]
                        }
                    ]
                }
                res = requests.post(endpoint, json=payload, timeout=8)
                if res.status_code == 200:
                    data = res.json()
                    answer_text = (
                        data.get("candidates", [{}])[0]
                        .get("content", {})
                        .get("parts", [{}])[0]
                        .get("text", "")
                    )
                    if answer_text:
                        return {
                            "status": "success",
                            "is_emergency": False,
                            "answer": answer_text,
                            "provider": "gemini-api",
                        }
            except Exception as e:
                print(f"[Gemini Assistant] API call failed: {e}. Using fallback.")

        # Contextual Fallback Generator (for demo or offline/no-API-key use)
        fallback_answer = self._generate_fallback_response(query, language)
        return {
            "status": "success",
            "is_emergency": False,
            "answer": fallback_answer,
            "provider": "smart_local_assistant",
        }

    def _generate_fallback_response(self, query: str, language: str) -> str:
        q = query.lower()
        if "blood pressure" in q or "bp" in q or "बीपी" in q:
            if language == "hi":
                return (
                    "🩺 **रक्तचाप (Blood Pressure) संबंधी मार्गदर्शन:**\n"
                    "- सामान्य बीपी लगभग 120/80 mmHg माना जाता है।\n"
                    "- नमक (सोडियम) कम लें और रोजाना 30 मिनट हल्की वॉक करें।\n"
                    "- यदि बीपी 140/90 से अधिक रहता है, तो अपने डॉक्टर से सलाह लें।\n\n"
                    "*नोट: यह केवल सामान्य जानकारी है। अपनी दवाएं डॉक्टर की सलाह से ही लें।*"
                )
            return (
                "🩺 **Blood Pressure Guidance:**\n"
                "- Normal adult BP is generally around 120/80 mmHg.\n"
                "- Reduce dietary sodium (salt) and stay hydrated with moderate daily walking.\n"
                "- If your readings consistently exceed 140/90 mmHg, consult your physician.\n\n"
                "*Disclaimer: Educational only. Never alter medications without clinical consultation.*"
            )

        if "fever" in q or "बुखार" in q or "ताप" in q:
            if language == "hi":
                return (
                    "🌡️ **बुखार के लिए प्राथमिक सुझाव:**\n"
                    "- भरपूर पानी और नारियल पानी पिएं, आराम करें।\n"
                    "- माथे पर सामान्य पानी की ठंडी पट्टी रखें।\n"
                    "- यदि बुखार 102°F से अधिक है या 3 दिन से बना हुआ है, तो तुरंत क्लिनिक जाएं।\n\n"
                    "*नोट: बिना डॉक्टर के पूछे एंटीबायोटिक्स न लें।*"
                )
            return (
                "🌡️ **Fever First-Aid Tips:**\n"
                "- Stay well hydrated (water, electrolytes) and get adequate rest.\n"
                "- Use a lukewarm sponge compress on the forehead.\n"
                "- Seek medical attention if fever exceeds 102°F or persists for more than 48–72 hours.\n\n"
                "*Disclaimer: Consult a licensed physician before starting antipyretics or antibiotics.*"
            )

        # General helpful health response
        if language == "hi":
            return (
                "🌿 **आरोग्य साथी स्वास्थ्य सलाह:**\n"
                f"- आपके सवाल: *\"{query}\"* के संबंध में: स्वस्थ आहार, 7-8 घंटे की पर्याप्त नींद और पर्याप्त पानी पीना स्वास्थ्य के लिए सर्वोत्तम है।\n"
                "- यदि यह लक्षण बार-बार हो रहे हैं, तो E-Doot ऐप से तुरंत डॉक्टर अपॉइंटमेंट बुक करें।\n\n"
                "*टिप: लाइव Gemini API सक्षम करने के लिए .env फ़ाइल में GEMINI_API_KEY जोड़ें।*"
            )
        return (
            "🌿 **Arogya Saathi Health Guidance:**\n"
            f"- Regarding your query *\"{query}\"*: Maintaining good hydration, balanced nutrition, and consistent sleep hygiene are the cornerstones of recovery.\n"
            "- If you are experiencing persistent discomfort, you can book an outpatient consultation directly from the E-Doot appointments tab.\n\n"
            "*Tip: Add your `GEMINI_API_KEY` in .env for real-time generative AI health answers.*"
        )


gemini_assistant = GeminiHealthAssistant()
