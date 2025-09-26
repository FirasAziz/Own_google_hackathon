from flask import Flask, request, redirect, url_for, render_template, send_file, flash, jsonify, session
import os
import subprocess
import sys
import random
import json
from werkzeug.utils import secure_filename
import threading
import time
import requests
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# OpenAI Realtime API configuration
app.config['OPENAI_REALTIME_MODEL'] = os.getenv('OPENAI_REALTIME_MODEL', 'gpt-4o-mini-realtime-preview')
app.config['OPENAI_REALTIME_VOICE'] = os.getenv('OPENAI_REALTIME_VOICE', 'alloy')

# Configuration
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
GENERATED_FOLDER = 'generated_documents'
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a', 'flac'}

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
os.makedirs(GENERATED_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_key_topics_with_gemini(lecture_content):
    """Extract 4-5 key points from lecture content using Gemini API"""
    try:
        from google import genai
        from dotenv import load_dotenv
        
        # Load environment variables
        load_dotenv()
        
        # Get Gemini API key
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not found in environment variables")
        
        # Initialize Gemini client
        client = genai.Client(api_key=api_key)
        
        # Create prompt for key points extraction
        prompt = f"""
أنت مساعد ذكي لاستخراج النقاط الأساسية من المحاضرات. من النص التالي، استخرج 4-5 نقاط أساسية فقط:

النص:
{lecture_content}

المطلوب:
- استخرج 4-5 نقاط أساسية فقط
- كل نقطة في سطر منفصل
- اجعل النقاط مختصرة وواضحة
- ركز على المفاهيم الأساسية والمهمة
- لا تضع أرقام أو رموز، فقط النقاط

النقاط الأساسية:
"""
        
        # Generate key points using Gemini
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        key_points_text = response.text or str(response)
        
        # Parse the response to get individual points
        lines = key_points_text.strip().split('\n')
        key_points = []
        
        for line in lines:
            line = line.strip()
            # Remove common prefixes and clean up
            line = line.lstrip('•-*123456789. ').strip()
            if line and len(line) > 5:  # Only include meaningful points
                key_points.append(line)
        
        # Limit to 5 points maximum
        key_points = key_points[:5]
        
        # Save key points to file
        key_points_path = 'key_points.txt'
        with open(key_points_path, 'w', encoding='utf-8') as f:
            for point in key_points:
                f.write(f"{point}\n")
        
        print(f"✅ Key points extracted and saved to {key_points_path}")
        return key_points
        
    except Exception as e:
        print(f"❌ Error extracting key points with Gemini: {e}")
        # Fallback to simple extraction
        return extract_key_topics_fallback(lecture_content)

def extract_key_topics_fallback(lecture_content):
    """Fallback method to extract key topics if Gemini fails"""
    lines = lecture_content.split('\n')
    topics = []
    
    for line in lines:
        line = line.strip()
        # Look for main headings and key points
        if line.startswith('**') and line.endswith('**'):
            # Main topic
            topic = line.replace('**', '').strip()
            if topic and len(topic) > 3:
                topics.append(topic)
        elif line.startswith('*   **') and line.endswith('**'):
            # Sub-topic
            topic = line.replace('*   **', '').replace('**', '').strip()
            if topic and len(topic) > 3:
                topics.append(topic)
    
    # Remove duplicates and limit to 5 most important topics
    unique_topics = list(dict.fromkeys(topics))
    return unique_topics[:5]

def run_script(script_path, *args):
    """Run a Python script and return the result using an absolute path."""
    try:
        project_root = os.path.abspath(os.path.dirname(__file__))
        # script_path may be relative (e.g., 'transcribtion.py' or 'backend/transcribtion.py')
        normalized = script_path.replace('backend/', '').replace('backend\\', '')
        abs_script = os.path.join(project_root, normalized)
        result = subprocess.run([sys.executable, abs_script] + list(args),
                                capture_output=True, text=True, cwd=project_root)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

@app.route('/')
def welcome():
    """Welcome page with introduction"""
    return render_template('welcome.html')

@app.route('/upload')
def index():
    """Main page with audio upload form"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'audio' not in request.files:
        flash('No audio file selected')
        return redirect(url_for('index'))
    
    if 'student_name' not in request.form or not request.form['student_name'].strip():
        flash('Please enter your name')
        return redirect(url_for('index'))
    
    file = request.files['audio']
    if file.filename == '':
        flash('No audio file selected')
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        # Store student name in session
        session['student_name'] = request.form['student_name'].strip()
        
        filename = secure_filename(file.filename)
        # Use a consistent filename for processing
        filename = 'audio_input.mp3'
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Run transcription from backend directory (use absolute path)
        success, stdout, stderr = run_script('transcribtion.py')
        if not success:
            flash(f'Transcription failed: {stderr}')
            return redirect(url_for('index'))
        
        flash('Audio uploaded and transcribed successfully!')
        return redirect(url_for('process'))
    else:
        flash('Invalid file type. Please upload MP3, WAV, M4A, or FLAC files.')
        return redirect(url_for('index'))

@app.route('/process')
def process():
    """Process the transcribed audio and generate PDF"""
    try:
        # Run generate_lec1.py
        success, stdout, stderr = run_script('generate_lec1.py')
        if not success:
            flash(f'Note generation failed: {stderr}')
            return redirect(url_for('index'))
        
        # Run document_export.py
        success, stdout, stderr = run_script('document_export.py')
        if not success:
            flash(f'PDF generation failed: {stderr}')
            return redirect(url_for('index'))
        
        flash('Lecture notes generated successfully!')
        return redirect(url_for('explanation'))
        
    except Exception as e:
        flash(f'Processing failed: {str(e)}')
        return redirect(url_for('index'))

@app.route('/explanation')
def explanation():
    return render_template('explanation.html')

@app.route('/tutor')
def tutor():
    return render_template('tutor.html')

@app.route('/tutor/topics')
def tutor_topics():
    """Get lecture topics from key_points.txt"""
    try:
        key_points_path = 'key_points.txt'
        if os.path.exists(key_points_path):
            with open(key_points_path, 'r', encoding='utf-8') as f:
                topics = [line.strip() for line in f.readlines() if line.strip()]
            return jsonify(topics)
        else:
            return jsonify([])
    except Exception as e:
        app.logger.error(f'Error loading topics: {e}')
        return jsonify([])

@app.route('/tutor/student-name')
def tutor_student_name():
    """Get student name from session"""
    student_name = session.get('student_name', 'Student')
    return jsonify({'name': student_name})

@app.route('/download')
def download_pdf():
    """Download the generated PDF"""
    # Use absolute path to ensure we find the file regardless of working directory
    pdf_path = os.path.abspath(os.path.join(GENERATED_FOLDER, 'final_document.pdf'))
    if os.path.exists(pdf_path):
        return send_file(pdf_path, as_attachment=True, download_name='lecture_notes.pdf')
    else:
        flash('PDF not found. Please try processing again.')
        return redirect(url_for('index'))

@app.route('/upload_explanation', methods=['POST'])
def upload_explanation():
    """Handle second audio upload for explanation"""
    if 'audio' not in request.files:
        flash('No audio file selected')
        return redirect(url_for('explanation'))
    
    file = request.files['audio']
    if file.filename == '':
        flash('No audio file selected')
        return redirect(url_for('explanation'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Use a different filename for explanation
        filename = 'explanation_input.mp3'
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Run transcription for explanation
        success, stdout, stderr = run_script('transcribtion.py')
        if not success:
            flash(f'Explanation transcription failed: {stderr}')
            return redirect(url_for('explanation'))
        
        # Process explanation (you might want to modify this based on your needs)
        success, stdout, stderr = run_script('generate_lec1.py')
        if not success:
            flash(f'Explanation processing failed: {stderr}')
            return redirect(url_for('explanation'))
        
        # Generate updated PDF
        success, stdout, stderr = run_script('document_export.py')
        if not success:
            flash(f'Updated PDF generation failed: {stderr}')
            return redirect(url_for('explanation'))
        
        flash('Explanation added successfully!')
        return redirect(url_for('explanation'))
    else:
        flash('Invalid file type. Please upload MP3, WAV, M4A, or FLAC files.')
        return redirect(url_for('explanation'))

@app.route('/tutor/realtime/session', methods=['POST'])
def tutor_realtime_session():
    """Create a session for OpenAI Realtime API for the AI Tutor"""
    try:
        # Check if OpenAI API key is available
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            return jsonify({'error': 'OpenAI API key not configured'}), 500

        # Get student name from session
        student_name = session.get('student_name', 'الطالب')
        
        # Read the lecture content from output.txt
        output_path = 'output.txt'
        if not os.path.exists(output_path):
            return jsonify({'error': 'Lecture notes not found. Please generate notes first.'}), 400

        with open(output_path, 'r', encoding='utf-8') as f:
            lecture_content = f.read()
        
        # Extract key topics from lecture content using Gemini API
        app.logger.info("Extracting key points from lecture content using Gemini API...")
        key_topics = extract_key_topics_with_gemini(lecture_content)
        app.logger.info(f"Extracted {len(key_topics)} key points")

        # Create session with OpenAI Realtime API
        model = app.config['OPENAI_REALTIME_MODEL']
        voice = app.config['OPENAI_REALTIME_VOICE']
        
        # Read key points from the saved file
        key_points_path = 'key_points.txt'
        key_points_content = ""
        
        if os.path.exists(key_points_path):
            app.logger.info("Reading key points from key_points.txt file")
            with open(key_points_path, 'r', encoding='utf-8') as f:
                key_points_content = f.read().strip()
        else:
            app.logger.warning("key_points.txt not found, using extracted topics directly")
            # Fallback: use the extracted topics directly
            key_points_content = "\n".join([f"- {topic}" for topic in key_topics])
        
        instructions = f"""You are an AI tutor for {student_name}. Speak only in Jordanian Arabic.

Given these key points from a lecture (key_points.txt):
{key_points_content}

IMPORTANT: Start speaking immediately when the session begins. Do not wait for the user to speak first.

Your task:
1. IMMEDIATELY greet: "السلام عليكم {student_name}، أنا معلمك الذكي. جاهز نبدأ بالمحاضرة؟"
2. Wait for response, then explain the lecture content step by step
3. After each topic, ask a question and wait for answer
4. Use warm, encouraging tone. Keep explanations simple and practical
5. Cover all the key points from the lecture

Start speaking NOW."""



        def create_session(using_model: str):
            return requests.post(
                'https://api.openai.com/v1/realtime/sessions',
                headers={
                    'Authorization': f'Bearer {openai_api_key}',
                    'OpenAI-Beta': 'realtime=v1',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': using_model,
                    'voice': voice,
                    'modalities': ['text', 'audio'],
                    'instructions': instructions,
                },
                timeout=20,
            )

        try:
            resp = create_session(model)
            app.logger.info(f'Session creation response status: {resp.status_code}')
        except Exception as e:
            app.logger.error(f'Network error creating session: {str(e)}')
            return jsonify({'error': 'network_error', 'message': str(e)}), 502

        if not resp.ok:
            app.logger.error(f'Session creation failed with status {resp.status_code}: {resp.text[:500]}')
            # Fallback: try alternate realtime model name if available
            alt_model = 'gpt-4o-mini-realtime-preview'
            if model != alt_model:
                try:
                    app.logger.info(f'Trying fallback model: {alt_model}')
                    alt_resp = create_session(alt_model)
                    if alt_resp.ok:
                        app.logger.info('Fallback model succeeded')
                        return jsonify(alt_resp.json())
                    else:
                        app.logger.error(f'Fallback model also failed: {alt_resp.status_code}: {alt_resp.text[:500]}')
                except Exception as e:
                    app.logger.error(f'Fallback model network error: {str(e)}')
                    alt_resp = None

            try:
                data = resp.json()
            except Exception:
                data = {'status_code': resp.status_code, 'text': resp.text[:400]}
            # Log details for debugging
            try:
                app.logger.error('Realtime upstream error %s: %s', resp.status_code, resp.text[:400])
            except Exception:
                pass
            return jsonify({'error': 'upstream_error', 'upstream': data}), 502

        data = resp.json()
        # Pass through the entire session object (client_secret.value, id, etc.)
        return jsonify(data)

    except Exception as e:
        app.logger.error(f'Error creating tutor session: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500

# Quiz functionality
def generate_quiz_questions():
    """Generate quiz questions from lecture content using Gemini API"""
    try:
        from google import genai
        
        # Get Gemini API key
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not found in environment variables")
        
        # Initialize Gemini client
        client = genai.Client(api_key=api_key)
        
        # Read lecture content
        with open("output.txt", "r", encoding="utf-8") as f:
            lecture_content = f.read()
        
        # Generate quiz questions
        prompt = f"""
        Based on the lecture content below, generate 5 multiple-choice questions that test understanding of the key concepts.

        Each question should have 4 answer options (only one correct). Questions should be in Arabic and cover different aspects of the lecture.

        Return the result strictly in JSON array format, where each item follows this structure:

        {{
          "question": "string (in Arabic)",
          "right_answer": "string (in Arabic)",
          "wrong_answer1": "string (in Arabic)",
          "wrong_answer2": "string (in Arabic)",
          "wrong_answer3": "string (in Arabic)"
        }}

        ---

        lecture_content:
        {lecture_content}
        """
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        quiz_json = response.text or str(response)
        
        # Clean up JSON if it has markdown formatting
        if quiz_json.startswith('```json'):
            quiz_json = quiz_json.replace('```json', '').replace('```', '').strip()
        
        # Parse and validate JSON
        quiz_data = json.loads(quiz_json)
        
        # Save to file
        with open("quiz.json", "w", encoding="utf-8") as f:
            json.dump(quiz_data, f, ensure_ascii=False, indent=2)
        
        return quiz_data
        
    except Exception as e:
        app.logger.error(f'Error generating quiz questions: {str(e)}')
        raise e

def randomize_answers(question_data):
    """Randomize the order of answers for a question"""
    answers = [
        question_data["right_answer"],
        question_data["wrong_answer1"],
        question_data["wrong_answer2"],
        question_data["wrong_answer3"]
    ]
    
    # Shuffle answers
    random.shuffle(answers)
    
    # Find correct answer index
    correct_index = answers.index(question_data["right_answer"])
    
    return {
        "question": question_data["question"],
        "answers": answers,
        "correct_index": correct_index,
        "correct_answer": question_data["right_answer"]
    }

@app.route('/quiz')
def quiz():
    """Display the quiz page"""
    return render_template('quiz.html')

@app.route('/quiz/generate', methods=['POST'])
def generate_quiz():
    """Generate quiz questions from lecture content"""
    try:
        quiz_data = generate_quiz_questions()
        
        # Randomize answers for each question
        randomized_questions = []
        for question in quiz_data:
            randomized_questions.append(randomize_answers(question))
        
        # Store in session for scoring
        session['quiz_questions'] = randomized_questions
        session['quiz_answers'] = [q['correct_index'] for q in randomized_questions]
        session['current_question'] = 0
        session['user_answers'] = []
        session['quiz_start_time'] = time.time()
        
        return jsonify({
            'success': True,
            'total_questions': len(randomized_questions),
            'questions': randomized_questions
        })
        
    except Exception as e:
        app.logger.error(f'Error generating quiz: {str(e)}')
        return jsonify({'error': str(e)}), 500

@app.route('/quiz/submit', methods=['POST'])
def submit_quiz_answer():
    """Submit an answer for the current question"""
    try:
        data = request.get_json()
        answer_index = data.get('answer_index')
        
        if 'user_answers' not in session:
            session['user_answers'] = []
        
        session['user_answers'].append(answer_index)
        session['current_question'] = session.get('current_question', 0) + 1
        
        return jsonify({'success': True})
        
    except Exception as e:
        app.logger.error(f'Error submitting answer: {str(e)}')
        return jsonify({'error': str(e)}), 500

@app.route('/quiz/result')
def quiz_result():
    """Display quiz results"""
    try:
        if 'quiz_answers' not in session or 'user_answers' not in session:
            return redirect(url_for('quiz'))
        
        correct_answers = session['quiz_answers']
        user_answers = session['user_answers']
        questions = session.get('quiz_questions', [])
        
        # Calculate score
        correct_count = sum(1 for i, answer in enumerate(user_answers) 
                          if i < len(correct_answers) and answer == correct_answers[i])
        total_questions = len(correct_answers)
        score_percentage = (correct_count / total_questions) * 100 if total_questions > 0 else 0
        
        # Calculate time taken
        start_time = session.get('quiz_start_time', time.time())
        time_taken = time.time() - start_time
        
        # Determine performance level
        if score_percentage >= 80:
            performance_level = "ممتاز"
            performance_color = "green"
        elif score_percentage >= 60:
            performance_level = "جيد"
            performance_color = "blue"
        elif score_percentage >= 40:
            performance_level = "مقبول"
            performance_color = "orange"
        else:
            performance_level = "يحتاج تحسين"
            performance_color = "red"
        
        # Prepare detailed results
        detailed_results = []
        for i, question in enumerate(questions):
            if i < len(user_answers) and i < len(correct_answers):
                is_correct = user_answers[i] == correct_answers[i]
                detailed_results.append({
                    'question': question['question'],
                    'user_answer': question['answers'][user_answers[i]] if user_answers[i] < len(question['answers']) else "لم يتم الإجابة",
                    'correct_answer': question['correct_answer'],
                    'is_correct': is_correct
                })
        
        return render_template('quiz_result.html', 
                             score_percentage=score_percentage,
                             correct_count=correct_count,
                             total_questions=total_questions,
                             performance_level=performance_level,
                             performance_color=performance_color,
                             time_taken=time_taken,
                             detailed_results=detailed_results)
        
    except Exception as e:
        app.logger.error(f'Error calculating quiz results: {str(e)}')
        return redirect(url_for('quiz'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
