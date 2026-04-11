from phase1.session.orchestrator import Orchestrator
from phase1.session.session_context import SessionContext
from src.integrations.voice.stt import SpeechToText
from src.integrations.voice.tts import TextToSpeech


def post_audio(session_id: str, audio_chunk: bytes, stt: SpeechToText, tts: TextToSpeech) -> list[bytes]:
    user_text = stt.transcribe(audio_chunk)
    turn = Orchestrator().handle(user_text, SessionContext(session_id=session_id))
    return [tts.synthesize(message) for message in turn.messages]
