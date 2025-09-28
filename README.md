# Lecture Assist 🎓

Transform your audio lectures into comprehensive notes with AI-powered transcription and document generation.

## Features

- 🎵 **Audio Upload**: Drag-and-drop interface for audio files (MP3, WAV, M4A, FLAC)
- 📝 **AI Transcription**: Automatic transcription using Google Cloud Speech API
- 📄 **Note Generation**: AI-powered lecture note generation
- 📊 **PDF Export**: Professional PDF documents with structured content
- 🌐 **Web Interface**: Modern, responsive web application
- 🎓 **AI Tutor**: Interactive Arabic tutoring with live audio conversation
- 🔄 **Additional Content**: Upload supplementary explanations

## Project Structure

```
lecture-assist/
├── backend/
│   ├── app.py                 # Flask web application
│   ├── transcribtion.py       # Audio transcription script
│   ├── generate_lec1.py       # Note generation script
│   ├── document_export.py     # PDF generation script
│   ├── templates/             # HTML templates
│   ├── static/               # CSS and static files
│   ├── fonts/                # Arabic fonts for PDF generation
│   └── requirements.txt      # Python dependencies
├── uploads/                  # Temporary audio uploads
├── processed/               # Processed files
├── generated_documents/     # Generated PDFs
├── input.txt               # Transcribed text input
├── output.txt              # Generated notes output
├── start_app.sh            # Easy startup script
└── README.md               # This documentation
```

## Setup Instructions

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Google Cloud Credentials

Set your Google Cloud credentials environment variable:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"
```

### 3. Run the Application

```bash
cd backend
python app.py
```

The application will be available at `http://localhost:5000`

## Usage

1. **Upload Audio**: Drag and drop your lecture audio file
2. **Generate Notes**: Click "Generate Notes" to process the audio
3. **Download PDF**: Download your comprehensive lecture notes
4. **Speak with AI Tutor**: Interactive Arabic tutoring with live audio conversation
5. **Add Content**: Optionally upload additional explanations

## Supported Audio Formats

- MP3
- WAV
- M4A
- FLAC

## AI Tutor Feature

The AI Tutor provides an interactive learning experience with the following capabilities:

- **Live Audio Conversation**: Real-time voice interaction using OpenAI Realtime API
- **Arabic Language Support**: All explanations and questions in Arabic
- **Interactive Q&A**: The tutor asks questions and provides feedback
- **Lecture-Based Content**: Uses your generated lecture notes as the knowledge base
- **Visual Feedback**: Animated speaking indicator with pulse effects
- **No Mute Required**: Continuous audio conversation without manual controls

### How it Works:
1. After generating your lecture notes, click "Speak with AI Tutor"
2. The system reads your `output.txt` file and creates a personalized tutor
3. The tutor explains concepts, asks questions, and provides corrections
4. All conversation happens through live audio using WebRTC technology

## API Endpoints

- `GET /` - Main upload page
- `POST /upload` - Upload audio file
- `GET /process` - Process uploaded audio
- `GET /explanation` - Show results page
- `GET /download` - Download generated PDF
- `GET /tutor` - AI Tutor interactive session
- `POST /tutor/realtime/session` - Create OpenAI Realtime session
- `POST /upload_explanation` - Upload additional audio

## Technology Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, JavaScript
- **AI Services**: Google Cloud Speech API, OpenAI Realtime API
- **Document Generation**: Custom PDF generation
- **Audio Processing**: PyDub
- **Real-time Communication**: WebRTC, WebSocket

## Requirements

- Python 3.8+
- Google Cloud Speech API credentials
- OpenAI API key (for AI Tutor feature)
- FFmpeg (for audio processing)

## License

This project is for educational and personal use.
