"""
Voice support: Speech-to-Text (STT) and Text-to-Speech (TTS) using Google APIs.
"""
import io
import os
import tempfile
from typing import Optional, Tuple
import speech_recognition as sr
from gtts import gTTS
from config.logger import log

try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False

# gTTS language code (same as our UI codes for common languages)
GTTTS_LANG_MAP = {
    "en": "en",
    "hi": "hi",
    "te": "te",
    "ta": "ta",
    "es": "es",
    "fr": "fr",
    "de": "de",
    "pt": "pt",
    "ja": "ja",
    "ko": "ko",
    "zh-CN": "zh-cn",
    "ar": "ar",
}


def _detect_format(audio_bytes: bytes) -> Optional[str]:
    """Detect format from magic bytes. Returns format string for pydub or None."""
    if len(audio_bytes) < 12:
        return None
    # WebM/Matroska
    if audio_bytes[:4] == b"\x1a\x45\xdf\xa3":
        return "webm"
    # OGG
    if audio_bytes[:4] == b"OggS":
        return "ogg"
    # WAV (RIFF....WAVE)
    if audio_bytes[:4] == b"RIFF" and audio_bytes[8:12] == b"WAVE":
        return "wav"
    # MP3 (ID3 or 0xff 0xfb)
    if audio_bytes[:3] == b"ID3" or (audio_bytes[0] == 0xFF and (audio_bytes[1] & 0xE0) == 0xE0):
        return "mp3"
    return None


def _audio_to_pcm_wav(audio_bytes: bytes, content_type: str = "audio/wav") -> Optional[bytes]:
    """Convert audio bytes to PCM WAV (16-bit mono 16kHz) for speech_recognition. Returns None on failure."""
    if not HAS_PYDUB:
        # Only accept raw bytes if they are already WAV
        if _detect_format(audio_bytes) == "wav":
            return audio_bytes
        return None
    # Order: try detected format first, then browser-friendly formats (webm, ogg), then wav/mp3
    detected = _detect_format(audio_bytes)
    if content_type:
        ct = content_type.lower()
        if "webm" in ct:
            preferred = "webm"
        elif "ogg" in ct:
            preferred = "ogg"
        elif "mp3" in ct:
            preferred = "mp3"
        elif "wav" in ct:
            preferred = "wav"
        else:
            preferred = detected
    else:
        preferred = detected
    formats_to_try = [f for f in [preferred, "webm", "ogg", "mp3", "wav"] if f]
    formats_to_try = list(dict.fromkeys(formats_to_try))  # dedup order preserved
    for fmt in formats_to_try:
        try:
            with tempfile.NamedTemporaryFile(suffix=f".{fmt}", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp.flush()
                tmp_path = tmp.name
            try:
                seg = AudioSegment.from_file(tmp_path, format=fmt)
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
            seg = seg.set_channels(1).set_frame_rate(16000)
            buf = io.BytesIO()
            seg.export(buf, format="wav", codec="pcm_s16le")
            return buf.getvalue()
        except Exception as e:
            log.debug(f"pydub format {fmt} failed: {e}")
            continue
    return None


def speech_to_text(audio_bytes: bytes, content_type: str = "audio/wav") -> Tuple[Optional[str], Optional[str]]:
    """
    Convert audio bytes to text using Google Web Speech API.
    Accepts WAV, WebM, OGG, MP3; converts to PCM WAV for recognition.
    Returns (text, error_message). text is None on failure.
    """
    if not audio_bytes:
        return None, "No audio data"
    wav_bytes = _audio_to_pcm_wav(audio_bytes, content_type)
    if wav_bytes is None:
        msg = (
            "Unsupported audio format. Use WAV, or install pydub + ffmpeg for WebM/MP3: "
            "pip install pydub and install ffmpeg on your system."
        )
        log.error(f"STT: {msg}")
        return None, msg
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio, language="en-IN")
        return (text.strip() if text else None), None
    except sr.UnknownValueError:
        return None, "Could not understand audio"
    except sr.RequestError as e:
        log.error(f"STT request error: {e}")
        return None, "Speech service error. Check network."
    except Exception as e:
        log.error(f"STT error: {e}")
        return None, str(e)


def text_to_speech(text: str, lang: str = "en") -> Optional[bytes]:
    """
    Convert text to speech using gTTS. Returns MP3 bytes or None.
    Truncates very long text to avoid timeouts (e.g. first ~500 chars).
    """
    if not text or not text.strip():
        return None
    text = text.strip()
    if len(text) > 500:
        text = text[:497] + "..."
    lang_code = GTTTS_LANG_MAP.get(lang, "en")
    try:
        tts = gTTS(text=text, lang=lang_code, slow=False)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        return buf.getvalue()
    except Exception as e:
        log.error(f"TTS error: {e}")
        return None
