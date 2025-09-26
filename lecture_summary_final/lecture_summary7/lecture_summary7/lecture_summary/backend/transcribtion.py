from google.cloud import speech_v1p1beta1 as speech
import pydub
from pydub import AudioSegment
import os

def chunk_audio(file_path, chunk_length_ms=50000):  # 50 seconds per chunk
    """Split audio file into chunks for processing"""
    try:
        print(f"Loading audio file: {file_path}")
        audio = AudioSegment.from_mp3(file_path)
        print(f"Audio loaded: {len(audio)}ms duration")
        
        # Convert to mono (single channel) and set sample rate
        audio = audio.set_channels(1).set_frame_rate(48000)
        chunks = []
        
        for i in range(0, len(audio), chunk_length_ms):
            chunk = audio[i:i + chunk_length_ms]
            chunk_path = f"temp_chunk_{i//chunk_length_ms}.wav"
            print(f"Creating chunk: {chunk_path}")
            chunk.export(chunk_path, format="wav")
            chunks.append(chunk_path)
        
        print(f"Successfully created {len(chunks)} chunks")
        return chunks
        
    except Exception as e:
        print(f"Error in chunk_audio: {e}")
        return []

def transcribe_chunk(chunk_path, language_code="ar-JO"):
    """Transcribe a single audio chunk"""
    client = speech.SpeechClient()
    
    with open(chunk_path, "rb") as audio_file:
        content = audio_file.read()
    
    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=48000,  # Match the actual audio sample rate
        language_code=language_code,
        enable_automatic_punctuation=True,
        enable_word_confidence=True,
    )
    
    response = client.recognize(config=config, audio=audio)
    
    transcript = ""
    for result in response.results:
        transcript += result.alternatives[0].transcript + " "
    
    return transcript.strip()

def transcribe_long_arabic_audio(file_path, language_code="ar-JO"):
    """Transcribe long Arabic audio by chunking"""
    print(f"Processing {file_path} for Arabic transcription...")
    
    try:
        # Create audio chunks
        chunks = chunk_audio(file_path)
        print(f"Created {len(chunks)} audio chunks")
        
        full_transcript = ""
        created_chunks = []  # Track which chunks were actually created
        
        for i, chunk_path in enumerate(chunks):
            print(f"Transcribing chunk {i+1}/{len(chunks)}...")
            try:
                # Check if chunk file exists before processing
                if os.path.exists(chunk_path):
                    created_chunks.append(chunk_path)
                    chunk_transcript = transcribe_chunk(chunk_path, language_code)
                    full_transcript += chunk_transcript + " "
                    print(f"Chunk {i+1} transcribed: {chunk_transcript[:100]}...")
                else:
                    print(f"Warning: Chunk file {chunk_path} does not exist, skipping...")
            except Exception as e:
                print(f"Error transcribing chunk {i+1}: {e}")
        
        # Clean up all created chunk files
        for chunk_path in created_chunks:
            try:
                if os.path.exists(chunk_path):
                    os.remove(chunk_path)
                    print(f"Cleaned up: {chunk_path}")
            except Exception as e:
                print(f"Warning: Could not remove chunk file {chunk_path}: {e}")
        
        return full_transcript.strip()
        
    except Exception as e:
        print(f"Error in transcribe_long_arabic_audio: {e}")
        return ""

if __name__ == "__main__":
    # Check for uploaded audio file from Flask app
    # First check in uploads directory (Flask app location)
    uploads_dir = "uploads"
    audio_file = os.path.join(uploads_dir, "audio_input.mp3")
    
    # If not found in uploads, check current directory
    if not os.path.exists(audio_file):
        audio_file = "audio_input.mp3"
        if not os.path.exists(audio_file):
            if os.path.exists("Regression.mp3"):
                audio_file = "Regression.mp3"
            elif os.path.exists("LLM_training.mp3"):
                audio_file = "LLM_training.mp3"
            else:
                print("Error: No audio file found. Please upload an audio file first.")
                exit(1)
    
    # Transcribe the audio file
    result = transcribe_long_arabic_audio(audio_file, "ar-JO")
    
    # Save to input.txt in the root directory
    input_path = "input.txt"
    with open(input_path, "w", encoding="utf-8") as f:
        f.write(result)
    
    print(f"\nFull Arabic transcript saved to input.txt:")
    print(result)
