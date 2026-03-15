"""
Multilingual support using Google Translate (deep-translator).
Translates user query to English for retrieval; translates answer back to user language.
Graph and relations remain in English.
"""
from typing import Optional
from deep_translator import GoogleTranslator
from config.logger import log

# Language code -> display name. Used in UI dropdown.
SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "te": "Telugu",
    "ta": "Tamil",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "pt": "Portuguese",
    "ja": "Japanese",
    "ko": "Korean",
    "zh-CN": "Chinese (Simplified)",
    "ar": "Arabic",
}

# UI labels per language (key -> translation). English is source; others added for common keys.
UI_LABELS = {
    "en": {
        "title": "GraphRAG: Multi-Hop Reasoning System",
        "subtitle": "Knowledge Graph + Vector Retrieval for Tech & AI News",
        "settings": "Settings",
        "query_input": "Query Input",
        "enter_question": "Enter your question:",
        "search": "Search",
        "example_queries": "Example Queries",
        "graph_paths": "Knowledge Graph Paths",
        "view_paths": "View Graph Paths as Text",
        "no_graph_paths": "No graph paths found for this query",
        "answer": "Answer",
        "reasoning_path": "Reasoning Path",
        "source_articles": "Source Articles",
        "no_reasoning": "No reasoning path (no graph or document context retrieved).",
        "no_sources": "No source articles found for this query.",
        "no_data_warning": "No relevant data was found for this query.",
        "try_rephrasing": "Try rephrasing or asking about Tech & AI news covered in the knowledge base.",
        "processing": "Processing query...",
        "error": "Error processing query",
        "language": "Language",
        "voice_query": "Voice input",
        "record_or_upload": "Record or upload voice",
        "play_answer": "Play answer",
        "or_type": "Or type your question below",
        "apply": "Apply",
        "graph_traversal_depth": "Graph Traversal Depth",
        "top_k_documents": "Top K Documents",
        "system_stats": "System Stats",
        "refresh_stats": "Refresh Stats",
        "query_history": "Query History",
        "record": "Record",
        "stop": "Stop",
        "convert_voice_to_text": "Convert voice to text",
        "converting": "Converting...",
        "could_not_recognize": "Could not recognize speech",
    },
    "hi": {
        "title": "GraphRAG: मल्टी-हॉप रीज़निंग सिस्टम",
        "subtitle": "टेक और AI समाचार के लिए नॉलेज ग्राफ + वेक्टर रिट्रीवल",
        "settings": "सेटिंग्स",
        "query_input": "क्वेरी इनपुट",
        "enter_question": "अपना प्रश्न दर्ज करें:",
        "search": "खोजें",
        "example_queries": "उदाहरण प्रश्न",
        "graph_paths": "नॉलेज ग्राफ पथ",
        "view_paths": "ग्राफ पथ टेक्स्ट में देखें",
        "no_graph_paths": "इस क्वेरी के लिए कोई ग्राफ पथ नहीं मिला",
        "answer": "उत्तर",
        "reasoning_path": "तर्क पथ",
        "source_articles": "स्रोत लेख",
        "no_reasoning": "कोई तर्क पथ नहीं (कोई ग्राफ या दस्तावेज़ संदर्भ नहीं मिला)।",
        "no_sources": "इस क्वेरी के लिए कोई स्रोत लेख नहीं मिला।",
        "no_data_warning": "इस क्वेरी के लिए कोई प्रासंगिक डेटा नहीं मिला।",
        "try_rephrasing": "पुनर्गठन करें या नॉलेज बेस में शामिल टेक और AI समाचार के बारे में पूछें।",
        "processing": "क्वेरी संसाधित हो रही है...",
        "error": "क्वेरी संसाधित करने में त्रुटि",
        "language": "भाषा",
        "voice_query": "वॉयस इनपुट",
        "record_or_upload": "रिकॉर्ड करें या वॉयस अपलोड करें",
        "play_answer": "उत्तर सुनें",
        "or_type": "या नीचे अपना प्रश्न टाइप करें",
        "apply": "लागू करें",
        "graph_traversal_depth": "ग्राफ ट्रैवर्सल गहराई",
        "top_k_documents": "शीर्ष K दस्तावेज़",
        "system_stats": "सिस्टम आंकड़े",
        "refresh_stats": "आंकड़े ताज़ा करें",
        "query_history": "क्वेरी इतिहास",
        "record": "रिकॉर्ड करें",
        "stop": "बंद करें",
        "convert_voice_to_text": "आवाज़ को टेक्स्ट में बदलें",
        "converting": "बदल रहा है...",
        "could_not_recognize": "आवाज़ पहचान नहीं सकी",
    },
    "te": {
        "title": "GraphRAG: మల్టీ-హాప్ రీజనింగ్ సిస్టమ్",
        "subtitle": "టెక్ మరియు AI వార్తల కోసం నాలెడ్జ్ గ్రాఫ్ + వెక్టర్ రిట్రీవల్",
        "settings": "సెట్టింగ్‌లు",
        "query_input": "క్వెరీ ఇన్‌పుట్",
        "enter_question": "మీ ప్రశ్నను నమోదు చేయండి:",
        "search": "వెతకండి",
        "example_queries": "ఉదాహరణ ప్రశ్నలు",
        "graph_paths": "నాలెడ్జ్ గ్రాఫ్ మార్గాలు",
        "view_paths": "గ్రాఫ్ మార్గాలు టెక్స్ట్‌లో వీక్షించండి",
        "no_graph_paths": "ఈ క్వెరీకి గ్రాఫ్ మార్గాలు లేవు",
        "answer": "సమాధానం",
        "reasoning_path": "రీజనింగ్ మార్గం",
        "source_articles": "మూల వ్యాసాలు",
        "no_reasoning": "రీజనింగ్ మార్గం లేదు (గ్రాఫ్ లేదా డాక్యుమెంట్ సందర్భం రిట్రీవ్ చేయబడలేదు).",
        "no_sources": "ఈ క్వెరీకి మూల వ్యాసాలు లేవు.",
        "no_data_warning": "ఈ క్వెరీకి సంబంధిత డేటా లేదు.",
        "try_rephrasing": "పునరుద్ధరించండి లేదా నాలెడ్జ్ బేస్‌లో ఉన్న టెక్ మరియు AI వార్తల గురించి అడగండి.",
        "processing": "క్వెరీ ప్రాసెస్ అవుతోంది...",
        "error": "క్వెరీ ప్రాసెస్ చేయడంలో లోపం",
        "language": "భాష",
        "voice_query": "వాయిస్ ఇన్‌పుట్",
        "record_or_upload": "రికార్డ్ చేయండి లేదా వాయిస్ అప్‌లోడ్ చేయండి",
        "play_answer": "సమాధానం వినండి",
        "or_type": "లేదా క్రింద మీ ప్రశ్నను టైప్ చేయండి",
        "apply": "అప్లై చేయండి",
        "graph_traversal_depth": "గ్రాఫ్ ట్రావర్సల్ డెప్త్",
        "top_k_documents": "టాప్ K డాక్యుమెంట్లు",
        "system_stats": "సిస్టమ్ గణాంకాలు",
        "refresh_stats": "గణాంకాలను రిఫ్రెష్ చేయండి",
        "query_history": "క్వెరీ చరిత్ర",
        "record": "రికార్డ్ చేయండి",
        "stop": "ఆపు",
        "convert_voice_to_text": "వాయిస్‌ను టెక్స్ట్‌గా మార్చండి",
        "converting": "మారుతోంది...",
        "could_not_recognize": "వాయిస్ గుర్తించలేకపోయింది",
    },
    "es": {
        "title": "GraphRAG: Sistema de razonamiento multietapa",
        "subtitle": "Grafo de conocimiento + recuperación vectorial para noticias de tecnología e IA",
        "settings": "Ajustes",
        "query_input": "Entrada de consulta",
        "enter_question": "Introduzca su pregunta:",
        "search": "Buscar",
        "example_queries": "Consultas de ejemplo",
        "graph_paths": "Rutas del grafo de conocimiento",
        "view_paths": "Ver rutas del grafo como texto",
        "no_graph_paths": "No se encontraron rutas del grafo para esta consulta",
        "answer": "Respuesta",
        "reasoning_path": "Ruta de razonamiento",
        "source_articles": "Artículos fuente",
        "no_reasoning": "Sin ruta de razonamiento (no se recuperó contexto de grafo o documento).",
        "no_sources": "No se encontraron artículos fuente para esta consulta.",
        "no_data_warning": "No se encontraron datos relevantes para esta consulta.",
        "try_rephrasing": "Intente reformular o preguntar sobre noticias de tecnología e IA en la base de conocimiento.",
        "processing": "Procesando consulta...",
        "error": "Error al procesar la consulta",
        "language": "Idioma",
        "voice_query": "Entrada de voz",
        "record_or_upload": "Grabar o subir voz",
        "play_answer": "Reproducir respuesta",
        "or_type": "O escriba su pregunta abajo",
        "apply": "Aplicar",
        "graph_traversal_depth": "Profundidad de recorrido del grafo",
        "top_k_documents": "Documentos Top K",
        "system_stats": "Estadísticas del sistema",
        "refresh_stats": "Actualizar estadísticas",
        "query_history": "Historial de consultas",
        "record": "Grabar",
        "stop": "Detener",
        "convert_voice_to_text": "Convertir voz a texto",
        "converting": "Convirtiendo...",
        "could_not_recognize": "No se pudo reconocer el audio",
    },
}


def _normalize_lang(lang: str) -> str:
    """Map UI codes to deep_translator / gTTS codes."""
    if lang == "zh-CN":
        return "zh-CN"
    return lang.split("-")[0] if lang else "en"


def translate_to_english(text: str, source_lang: Optional[str] = None) -> str:
    """Translate user query to English for retrieval. Graph/vector search uses English."""
    if not text or not text.strip():
        return text
    try:
        if source_lang and _normalize_lang(source_lang) == "en":
            return text
        t = GoogleTranslator(source=source_lang or "auto", target="en")
        out = t.translate(text.strip())
        return out or text
    except Exception as e:
        log.warning(f"Translation to English failed: {e}, using original")
        return text


def translate_to_language(text: str, target_lang: str, source_lang: str = "en") -> str:
    """Translate answer (or any text) from English to user language."""
    if not text or not text.strip():
        return text
    target = _normalize_lang(target_lang)
    if target == "en":
        return text
    try:
        t = GoogleTranslator(source=source_lang, target=target)
        out = t.translate(text.strip())
        return out or text
    except Exception as e:
        log.warning(f"Translation to {target_lang} failed: {e}, using original")
        return text


def get_ui_label(key: str, lang: str) -> str:
    """Return localized UI label. Fallback to English if key or lang missing."""
    lang = _normalize_lang(lang)
    labels = UI_LABELS.get(lang, UI_LABELS["en"])
    return labels.get(key, UI_LABELS["en"].get(key, key))
