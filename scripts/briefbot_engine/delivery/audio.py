#
# Text-to-Speech Engine: Generates audio from research output
# Supports edge-tts (free, local) and ElevenLabs (premium, API key required)
#

import json
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional


# ElevenLabs API endpoint
ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
ELEVENLABS_DEFAULT_VOICE = "Rachel"  # Clear, professional female voice
ELEVENLABS_VOICES_URL = "https://api.elevenlabs.io/v1/voices"


def clean_text_for_speech(raw_text: str) -> str:
    """
    Strips markdown formatting, URLs, and noise from research output
    so it sounds natural when read aloud by a TTS engine.
    """
    text = raw_text

    # Remove markdown headers (### Header -> Header)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # Remove markdown bold/italic
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,3}([^_]+)_{1,3}', r'\1', text)

    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)

    # Remove markdown links [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

    # Remove score/ID tags like (score:42) or **R01**
    text = re.sub(r'\(score:\d+\)', '', text)
    text = re.sub(r'\*\*[A-Z]\d{2,}\*\*', '', text)

    # Remove separator lines (=== or ---)
    text = re.sub(r'^[=\-]{3,}$', '', text, flags=re.MULTILINE)

    # Remove lines that are purely structural (Mode:, Date range:, etc.)
    text = re.sub(r'^Mode:.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^Date range:.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^Models:.*$', '', text, flags=re.MULTILINE)

    # Remove emoji-heavy stat lines but keep the text
    text = re.sub(r'[^\S\n]*[├└─│]+[^\S\n]*', ' ', text)

    # Collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Strip leading/trailing whitespace per line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)

    return text.strip()


def _resolve_elevenlabs_voice_id(api_key: str, voice_name: str) -> Optional[str]:
    """
    Looks up an ElevenLabs voice ID by name.
    Returns the voice ID string, or None if not found.
    """
    request = urllib.request.Request(
        ELEVENLABS_VOICES_URL,
        headers={
            "xi-api-key": api_key,
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
            for voice in data.get("voices", []):
                if voice.get("name", "").lower() == voice_name.lower():
                    return voice["voice_id"]
    except Exception:
        pass

    return None


def _synthesize_with_elevenlabs(
    text: str,
    output_path: Path,
    api_key: str,
    voice_id: Optional[str] = None,
) -> Path:
    """
    Generates MP3 audio using the ElevenLabs TTS API.
    Uses urllib (stdlib) so no extra dependencies are needed.
    """
    # Resolve voice ID if not provided
    if voice_id is None:
        voice_id = _resolve_elevenlabs_voice_id(api_key, ELEVENLABS_DEFAULT_VOICE)
        if voice_id is None:
            # Fall back to first available voice
            voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel's known ID

    url = ELEVENLABS_TTS_URL.format(voice_id=voice_id)

    payload = json.dumps({
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
        },
    }).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as audio_file:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    audio_file.write(chunk)
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            "ElevenLabs API error {}: {}".format(err.code, body)
        ) from err

    return output_path


def _synthesize_with_edge_tts(text: str, output_path: Path) -> Path:
    """
    Generates MP3 audio using edge-tts (Microsoft Edge TTS).
    Requires: pip install edge-tts
    """
    try:
        import edge_tts
        import asyncio
    except ImportError:
        raise RuntimeError(
            "edge-tts is not installed. Install it with:\n"
            "  pip install edge-tts\n\n"
            "Or add ELEVENLABS_API_KEY to ~/.config/briefbot/.env for premium TTS."
        )

    async def _generate():
        communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        await communicate.save(str(output_path))

    asyncio.run(_generate())
    return output_path


def generate_audio(
    text: str,
    output_path: Path,
    elevenlabs_api_key: Optional[str] = None,
    elevenlabs_voice_id: Optional[str] = None,
) -> Path:
    """
    Generates an MP3 audio file from text.

    Priority:
    1. ElevenLabs (if API key provided) - premium quality
    2. edge-tts (if installed) - free, good quality, no API key needed

    Args:
        text: Raw research output text (will be cleaned for speech)
        output_path: Where to save the MP3 file
        elevenlabs_api_key: Optional ElevenLabs API key for premium TTS
        elevenlabs_voice_id: Optional ElevenLabs voice ID override

    Returns:
        Path to the generated MP3 file

    Raises:
        RuntimeError: If no TTS backend is available
    """
    speech_text = clean_text_for_speech(text)

    # Enforce ElevenLabs character limit (split if needed)
    max_chars = 5000
    if len(speech_text) > max_chars:
        speech_text = speech_text[:max_chars]
        # Cut at last sentence boundary
        last_period = speech_text.rfind('.')
        if last_period > max_chars // 2:
            speech_text = speech_text[:last_period + 1]

    if elevenlabs_api_key:
        return _synthesize_with_elevenlabs(
            speech_text, output_path, elevenlabs_api_key, elevenlabs_voice_id
        )

    return _synthesize_with_edge_tts(speech_text, output_path)


