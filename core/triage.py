"""
Deterministic rules-based emergency triage engine.
Strictly maps bystander-reported acute symptoms to medical acuity categories
and specifies necessary hospital ward and equipment requirements.

DISCLAIMER: This module does NOT provide clinical diagnosis. It exclusively
guides emergency transport routing to facilities equipped for the acute presentation.
"""

from typing import Dict, Any, List, Optional


class TriageCategory:
    CARDIAC = "Cardiac"
    STROKE = "Stroke"
    TRAUMA = "Trauma"
    BREATHING = "Breathing"
    BURNS = "Burns"
    UNKNOWN = "Unknown"


# Triage question definitions with localized audio voice prompts
TRIAGE_QUESTIONS = [
    {
        "id": "q_conscious",
        "key": "is_conscious",
        "type": "choice",
        "question": {
            "en": "Is the patient conscious and responsive?",
            "hi": "क्या मरीज होश में है और प्रतिक्रिया दे रहा है?",
            "mr": "रुग्ण शुद्धीवर आहे का आणि प्रतिसाद देत आहे का?",
        },
        "options": [
            {"value": "conscious", "label": {"en": "Conscious & Alert", "hi": "होश में है", "mr": "शुद्धीवर आहे"}},
            {"value": "drowsy", "label": {"en": "Drowsy / Confused", "hi": "सुस्त / भ्रमित", "mr": "गुंगीत / गोंधळलेला"}},
            {"value": "unconscious", "label": {"en": "Unconscious / Unresponsive", "hi": "बेहोश है", "mr": "पूर्ण बेशुद्ध"}},
        ],
        "default": "conscious",
    },
    {
        "id": "q_chest_pain",
        "key": "has_chest_pain",
        "type": "boolean",
        "question": {
            "en": "Is there severe chest pain, heavy pressure, or radiating pain to the left arm/jaw?",
            "hi": "क्या सीने में तेज दर्द, भारीपन या बाएं हाथ/जबड़े में दर्द हो रहा है?",
            "mr": "छातीत तीव्र वेदना, जडपणा किंवा डाव्या हाताकडे जाणारी वेदना आहे का?",
        },
        "options": [
            {"value": "yes", "label": {"en": "Yes, Severe Chest Pain", "hi": "हाँ, सीने में तेज दर्द", "mr": "होय, तीव्र छातीत दुखणे"}},
            {"value": "no", "label": {"en": "No Chest Pain", "hi": "नहीं", "mr": "नाही"}},
        ],
        "default": "no",
    },
    {
        "id": "q_stroke",
        "key": "has_stroke_signs",
        "type": "boolean",
        "question": {
            "en": "Any stroke signs: facial drooping, arm weakness, or slurred speech (FAST)?",
            "hi": "क्या चेहरे का एक तरफ झुकना, हाथ में कमजोरी या बोली लड़खड़ाना (स्ट्रोक के लक्षण) हैं?",
            "mr": "चेहरा एका बाजूला वाकडा होणे, हात अशक्त होणे किंवा बोलताना अडखळणे अशी लक्षणे आहेत का?",
        },
        "options": [
            {"value": "yes", "label": {"en": "Yes, Stroke Signs Present", "hi": "हाँ, स्ट्रोक के लक्षण हैं", "mr": "होय, स्ट्रोकची लक्षणे आहेत"}},
            {"value": "no", "label": {"en": "No Signs", "hi": "नहीं", "mr": "नाही"}},
        ],
        "default": "no",
    },
    {
        "id": "q_trauma",
        "key": "has_severe_trauma",
        "type": "boolean",
        "question": {
            "en": "Is there severe bleeding, fracture, road accident impact, or head injury?",
            "hi": "क्या गंभीर चोट, भारी रक्तस्राव, फ्रैक्चर या सड़क दुर्घटना का प्रभाव है?",
            "mr": "गंभीर जखम, प्रचंड रक्तस्त्राव, फ्रॅक्चर किंवा अपघाताचा आघात आहे का?",
        },
        "options": [
            {"value": "yes", "label": {"en": "Yes, Severe Trauma / Bleeding", "hi": "हाँ, गंभीर चोट / खून बह रहा है", "mr": "होय, गंभीर दुखापत / रक्तस्त्राव"}},
            {"value": "no", "label": {"en": "No Major Trauma", "hi": "नहीं", "mr": "नाही"}},
        ],
        "default": "no",
    },
    {
        "id": "q_breathing",
        "key": "has_breathing_issue",
        "type": "boolean",
        "question": {
            "en": "Is the patient choking, wheezing severely, or struggling for breath?",
            "hi": "क्या मरीज को सांस लेने में अत्यधिक कठिनाई, दम घुटना या घरघराहट हो रही है?",
            "mr": "रुग्णाचा श्वास गुदमरतोय का किंवा श्वास घेण्यास अतिशय त्रास होतोय का?",
        },
        "options": [
            {"value": "yes", "label": {"en": "Yes, Severe Breathlessness", "hi": "हाँ, सांस लेने में भारी तकलीफ", "mr": "होय, श्वास घेण्यास गंभीर त्रास"}},
            {"value": "no", "label": {"en": "Breathing Normal", "hi": "सांस सामान्य है", "mr": "श्वास सामान्य आहे"}},
        ],
        "default": "no",
    },
    {
        "id": "q_burns",
        "key": "has_burns",
        "type": "boolean",
        "question": {
            "en": "Are there severe fire burns, boiling liquid scalds, or chemical exposure?",
            "hi": "क्या आग से जलने, उबलते पानी या केमिकल से झुलसने की गंभीर स्थिति है?",
            "mr": "आगीने होरपळणे, उकळते पाणी किंवा रसायनामुळे भाजल्याची गंभीर स्थिती आहे का?",
        },
        "options": [
            {"value": "yes", "label": {"en": "Yes, Severe Burns", "hi": "हाँ, गंभीर रूप से झुलसा हुआ", "mr": "होय, गंभीर भाजले आहे"}},
            {"value": "no", "label": {"en": "No Burns", "hi": "नहीं", "mr": "नाही"}},
        ],
        "default": "no",
    },
]


def evaluate_triage(answers: Dict[str, str], patient_conditions: str = "") -> Dict[str, Any]:
    """
    Evaluates bystander triage answers and determines the primary emergency category,
    acuity level, required ward bed type, and golden-hour first-aid guidance.

    Returns:
        dict: {
            "category": str,
            "acuity": str ("Critical" | "High" | "Moderate"),
            "required_bed": str ("ICU" | "Trauma" | "General"),
            "primary_facility": str,
            "rationale": str,
            "disclaimer": str
        }
    """
    is_conscious = answers.get("is_conscious", "conscious")
    has_chest_pain = answers.get("has_chest_pain") == "yes"
    has_stroke_signs = answers.get("has_stroke_signs") == "yes"
    has_severe_trauma = answers.get("has_severe_trauma") == "yes"
    has_breathing_issue = answers.get("has_breathing_issue") == "yes"
    has_burns = answers.get("has_burns") == "yes"

    patient_history = (patient_conditions or "").lower()

    # Rule 1: Cardiac Emergency
    if has_chest_pain or ("cardiac" in patient_history and is_conscious != "conscious"):
        return {
            "category": TriageCategory.CARDIAC,
            "acuity": "Critical",
            "required_bed": "ICU",
            "primary_facility": "Cath Lab / Cardiac Care Unit (CCU)",
            "rationale": "Severe chest pain / radiating discomfort indicates suspected Acute Coronary Syndrome (ACS) or myocardial infarction. Immediate Cath Lab access required.",
            "disclaimer": "Rules-based triage suggestion only. Does not replace physical emergency medical diagnosis.",
        }

    # Rule 2: Acute Stroke / Cerebrovascular Incident
    if has_stroke_signs:
        return {
            "category": TriageCategory.STROKE,
            "acuity": "Critical",
            "required_bed": "ICU",
            "primary_facility": "24/7 CT / Stroke Neurology Unit",
            "rationale": "Sudden neurological deficits (facial drooping, limb weakness, speech impairment) indicate acute ischemic/hemorrhagic stroke within the thrombolytic window.",
            "disclaimer": "Rules-based triage suggestion only. Does not replace physical emergency medical diagnosis.",
        }

    # Rule 3: Severe Trauma & Hemorrhagic Shock
    if has_severe_trauma or (is_conscious == "unconscious" and not has_chest_pain):
        return {
            "category": TriageCategory.TRAUMA,
            "acuity": "Critical",
            "required_bed": "Trauma",
            "primary_facility": "Level 1/2 Trauma Bay & Emergency Surgery",
            "rationale": "Major blunt/penetrating injury or loss of consciousness with suspected trauma. Urgent hemodynamic stabilization and surgical evaluation required.",
            "disclaimer": "Rules-based triage suggestion only. Does not replace physical emergency medical diagnosis.",
        }

    # Rule 4: Severe Respiratory Distress
    if has_breathing_issue:
        return {
            "category": TriageCategory.BREATHING,
            "acuity": "High",
            "required_bed": "ICU",
            "primary_facility": "Pulmonary Intensive Care / Ventilatory Support",
            "rationale": "Acute dyspnea, upper airway compromise, or status asthmaticus. High-flow oxygenation and ventilator availability required.",
            "disclaimer": "Rules-based triage suggestion only. Does not replace physical emergency medical diagnosis.",
        }

    # Rule 5: Severe Burns
    if has_burns:
        return {
            "category": TriageCategory.BURNS,
            "acuity": "High",
            "required_bed": "Trauma",
            "primary_facility": "Specialized Burn ICU / Fluid Resuscitation Bay",
            "rationale": "Thermal or chemical injury requiring sterile barrier isolation, Parkland fluid resuscitation, and specialized wound management.",
            "disclaimer": "Rules-based triage suggestion only. Does not replace physical emergency medical diagnosis.",
        }

    # Fallback Rule: Unknown / General Acute
    return {
        "category": TriageCategory.UNKNOWN,
        "acuity": "Moderate" if is_conscious == "conscious" else "Critical",
        "required_bed": "General" if is_conscious == "conscious" else "ICU",
        "primary_facility": "24/7 Multi-Specialty Emergency Room",
        "rationale": "Symptoms do not neatly match a specific organ failure pathway. Routing to comprehensive tertiary care center with broad diagnostic facilities.",
        "disclaimer": "Rules-based triage suggestion only. Does not replace physical emergency medical diagnosis.",
    }


def get_first_aid_guidance(category: str, language: str = "en") -> Dict[str, Any]:
    """
    Returns step-by-step first aid guidance tailored to the triaged category.
    Used for Proposal 1: Golden Hour Interactive Guidance.
    """
    guidance_map = {
        TriageCategory.CARDIAC: {
            "title": {"en": "Suspected Cardiac Crisis", "hi": "हार्ट अटैक / सीने में दर्द प्राथमिक उपचार", "mr": "हार्ट अटॅक प्राथमिक उपचार"},
            "steps": [
                {
                    "step": 1,
                    "en": "Keep the patient seated comfortably with back supported. Do not let them walk.",
                    "hi": "मरीज को पीठ के सहारे आराम से बैठाएं। उन्हें चलने न दें।",
                    "mr": "रुग्णाला पाठीचा आधार देऊन शांत बसवा. त्यांना चालू देऊ नका.",
                },
                {
                    "step": 2,
                    "en": "Loosen tight clothing around the neck, chest, and waist to ease breathing.",
                    "hi": "गले, सीने और कमर के आसपास के तंग कपड़े ढीले कर दें ताकि सांस लेना आसान हो।",
                    "mr": "श्वास घेणे सोपे व्हावे म्हणून मान आणि छातीभोवतीचे घट्ट कपडे सैल करा.",
                },
                {
                    "step": 3,
                    "en": "If patient is conscious and has no aspirin allergy, ask if they take prescribed Sorbitrate/Aspirin.",
                    "hi": "यदि मरीज होश में है और कोई एलर्जी नहीं है, तो डॉक्टर द्वारा सुझाई गई दवा की जांच करें।",
                    "mr": "रुग्ण शुद्धीवर असल्यास डॉक्टरांनी सुचवलेले औषध जवळ आहे का ते पहा.",
                },
                {
                    "step": 4,
                    "en": "If patient becomes completely unresponsive and stops normal breathing, begin chest compressions (CPR at 100-120 bpm).",
                    "hi": "यदि मरीज बेहोश हो जाए और सांस रुक जाए, तो तुरंत छाती के बीच सीपीआर (100-120 प्रति मिनट) शुरू करें।",
                    "mr": "रुग्ण बेशुद्ध झाल्यास व श्वास थांबल्यास त्वरित छातीवर सीपीआर (CPR) सुरू करा.",
                },
            ],
            "has_cpr_metronome": True,
        },
        TriageCategory.STROKE: {
            "title": {"en": "Suspected Acute Stroke (FAST)", "hi": "स्ट्रोक / लकवा प्राथमिक कदम", "mr": "स्ट्रोक प्राथमिक काळजी"},
            "steps": [
                {
                    "step": 1,
                    "en": "Note the exact time symptoms started. Stroke treatments are time-critical (Golden 4.5 hours).",
                    "hi": "लक्षण शुरू होने का सटीक समय नोट करें। स्ट्रोक का इलाज समय पर निर्भर करता है।",
                    "mr": "लक्षणे सुरू झाल्याची अचूक वेळ नोंदवा. स्ट्रोकच्या उपचारात वेळ अत्यंत महत्त्वाची असते.",
                },
                {
                    "step": 2,
                    "en": "Position the patient with head and shoulders slightly elevated (approx 30 degrees).",
                    "hi": "मरीज के सिर और कंधों को थोड़ा ऊपर (लगभग 30 डिग्री) उठाकर रखें।",
                    "mr": "रुग्णाचे डोके आणि खांदे थोडे वर (सुमारे ३० अंश) आधार देऊन ठेवा.",
                },
                {
                    "step": 3,
                    "en": "NEVER give water, food, or aspirin pills (swallowing reflex may be paralyzed, causing choking).",
                    "hi": "मरीज को पानी, खाना या एस्पिरिन बिल्कुल न दें (गले की मांसपेशियां सुन्न होने से दम घुट सकता है)।",
                    "mr": "रुग्णाला पाणी, अन्न किंवा औषध अजिबात देऊ नका.",
                },
            ],
            "has_cpr_metronome": False,
        },
        TriageCategory.TRAUMA: {
            "title": {"en": "Trauma & Severe Bleeding", "hi": "गंभीर चोट व रक्तस्राव नियंत्रण", "mr": "गंभीर दुखापत व रक्तस्त्राव"},
            "steps": [
                {
                    "step": 1,
                    "en": "Apply continuous, firm direct pressure on the bleeding wound with a clean cloth or bandage.",
                    "hi": "साफ कपड़े या पट्टी से घाव पर लगातार सीधा और मजबूत दबाव बनाए रखें।",
                    "mr": "स्वच्छ कापडाने जखमेवर थेट आणि मजबूत दाब देऊन रक्तस्त्राव थांबवा.",
                },
                {
                    "step": 2,
                    "en": "Do NOT move the patient's neck or spine if high-speed accident or fall is suspected.",
                    "hi": "सड़क दुर्घटना या ऊंचाई से गिरने पर मरीज की गर्दन और रीढ़ को बिल्कुल न हिलाएं।",
                    "mr": "अपघात झाल्यास रुग्णाची मान किंवा पाठीचा कणा अजिबात हलवू नका.",
                },
                {
                    "step": 3,
                    "en": "Keep the patient warm with a jacket/blanket to prevent traumatic hypothermic shock.",
                    "hi": "मरीज को शॉक से बचाने के लिए चादर या जैकेट से गर्म रखें।",
                    "mr": "रुग्णाला उबदार ठेवा जेणेकरून शरीराचे तापमान कमी होणार नाही.",
                },
            ],
            "has_cpr_metronome": False,
        },
        TriageCategory.BREATHING: {
            "title": {"en": "Respiratory Crisis & Choking", "hi": "सांस फूलना / दम घुटना", "mr": "श्वास घेण्यास त्रास"},
            "steps": [
                {
                    "step": 1,
                    "en": "Sit the patient upright in a 'tripod' position (leaning forward with hands on knees).",
                    "hi": "मरीज को आगे की ओर झुकाकर सीधा बैठाएं ताकि फेफड़ों पर दबाव कम हो।",
                    "mr": "रुग्णाला पुढे थोडे वाकवून सरळ बसवा जेणेकरून श्वास घेणे सोपे होईल.",
                },
                {
                    "step": 2,
                    "en": "Ensure fresh air circulation; clear away crowded bystanders.",
                    "hi": "मरीज के आसपास भीड़ न लगाएं, खुली हवा आने दें।",
                    "mr": "रुग्णाभोवती गर्दी करू नका, मोकळी हवा येऊ द्या.",
                },
                {
                    "step": 3,
                    "en": "If patient carries a prescribed rescue inhaler (Salbutamol), assist them in taking 2 puffs.",
                    "hi": "यदि मरीज के पास उनका इनहेलर है, तो उन्हें 2 कश लेने में मदद करें।",
                    "mr": "रुग्णाकडे इनहेलर असल्यास त्यांना २ पफ घेण्यास मदत करा.",
                },
            ],
            "has_cpr_metronome": False,
        },
        TriageCategory.BURNS: {
            "title": {"en": "Severe Burn Management", "hi": "गंभीर जलन प्राथमिक उपचार", "mr": "भाजल्यास प्राथमिक उपचार"},
            "steps": [
                {
                    "step": 1,
                    "en": "Cool the burn under gentle running tap water for at least 10–15 minutes. NEVER use ice or toothpaste.",
                    "hi": "जली हुई जगह पर 10-15 मिनट तक सामान्य बहता पानी डालें। बर्फ, घी या टूथपेस्ट कभी न लगाएं।",
                    "mr": "भाजलेल्या भागावर १०-१५ मिनिटे वाहते थंड पाणी टाका. बर्फ किंवा पेस्ट लावू नका.",
                },
                {
                    "step": 2,
                    "en": "Do NOT peel off clothing stuck to the burn. Cut around loose fabric only.",
                    "hi": "जले हुए स्थान पर चिपके हुए कपड़े को जबरदस्ती न खींचें।",
                    "mr": "जखमेला चिकटलेले कपडे ओढून काढू नका.",
                },
                {
                    "step": 3,
                    "en": "Cover loosely with clean plastic cling wrap or sterile non-adherent cloth.",
                    "hi": "साफ और ढीले कपड़े या प्लास्टिक रैप से ढकें ताकि संक्रमण न हो।",
                    "mr": "जखम स्वच्छ कापडाने सैल झाकून ठेवा.",
                },
            ],
            "has_cpr_metronome": False,
        },
        TriageCategory.UNKNOWN: {
            "title": {"en": "Acute Emergency Protocol", "hi": "सामान्य आपातकालीन प्रोटोकॉल", "mr": "आपत्कालीन प्रोटोकॉल"},
            "steps": [
                {
                    "step": 1,
                    "en": "Check Airway, Breathing, and Circulation (ABC).",
                    "hi": "मरीज की सांस और नब्ज की जांच करें।",
                    "mr": "रुग्णाचा श्वास आणि नाडी तपासा.",
                },
                {
                    "step": 2,
                    "en": "If unconscious but breathing normally, place in Recovery Position (on their side) to prevent choking on vomit.",
                    "hi": "यदि मरीज बेहोश है पर सांस ले रहा है, तो करवट दिलाकर रिकवरी स्थिति में लिटाएं।",
                    "mr": "रुग्ण बेशुद्ध असल्यास त्याला एका कुशीवर वळवून ठेवा.",
                },
                {
                    "step": 3,
                    "en": "Stay with the patient until the dispatched ambulance arrives.",
                    "hi": "एंबुलेंस आने तक मरीज के साथ ही रहें।",
                    "mr": "रुग्णवाहिका येईपर्यंत रुग्णासोबतच थांबा.",
                },
            ],
            "has_cpr_metronome": False,
        },
    }

    entry = guidance_map.get(category, guidance_map[TriageCategory.UNKNOWN])
    return {
        "title": entry["title"].get(language, entry["title"]["en"]),
        "steps": [
            {"step": s["step"], "text": s.get(language, s["en"])}
            for s in entry["steps"]
        ],
        "has_cpr_metronome": entry.get("has_cpr_metronome", False),
    }
