(() => {
  const tutorMessageEl = document.getElementById('tutorMessage');
  const statusTextEl = document.getElementById('statusText');
  const agentIcon = document.getElementById('agentSpeakingIcon');
  const endSessionBtn = document.getElementById('endSessionBtn');
  const sessionTimer = document.getElementById('sessionTimer');
  const studentNameEl = document.getElementById('studentName');
  const topicsListEl = document.getElementById('topicsList');
  const sessionNotesEl = document.getElementById('sessionNotes');

  let pc = null; // RTCPeerConnection
  let localStream = null;
  let remoteAudioEl = null;
  let remoteAnalyser, remoteData;
  let isConnected = false;
  let isMuted = false;
  let muteButton = null;
  let sessionStartTime = null;
  let timerInterval = null;
  let isAgentSpeaking = false;

  // Initialize the tutor session
  async function initTutor() {
    try {
      // Initialize UI elements
      muteButton = document.getElementById('muteButton');
      if (muteButton) {
        muteButton.addEventListener('click', toggleMute);
      }
      
      if (endSessionBtn) {
        endSessionBtn.addEventListener('click', endSession);
      }
      
      
      // Load student name and topics
      loadStudentInfo();
      loadLectureTopics();
      
      // Start session timer
      startSessionTimer();
      
      statusTextEl.textContent = 'Connecting to AI Tutor...';
      
      // Setup WebRTC exactly like ai_mock_interview
      await ensureRealtime();
      
    } catch (error) {
      console.error('Failed to initialize tutor:', error);
      console.error('Error details:', error.message);
      console.error('Error stack:', error.stack);
      statusTextEl.textContent = `Connection failed: ${error.message}. Please refresh and try again.`;
    }
  }

  // --- Realtime WebRTC helpers (copied exactly from ai_mock_interview) ---
  async function ensureRealtime() {
    if (pc) return pc;
    updateStatus('Starting real-time session...', true);

    // Capture mic and a dummy video track (some browsers expect one)
    localStream = await navigator.mediaDevices.getUserMedia({ audio: true });

    // Create hidden audio tag for remote playback
    remoteAudioEl = document.getElementById('realtime-remote-audio');
    if (!remoteAudioEl) {
      remoteAudioEl = document.createElement('audio');
      remoteAudioEl.id = 'realtime-remote-audio';
      remoteAudioEl.autoplay = true;
      remoteAudioEl.playsInline = true;
      remoteAudioEl.style.display = 'none';
      document.body.appendChild(remoteAudioEl);
    }

    pc = new RTCPeerConnection();
    localStream.getTracks().forEach(t => pc.addTrack(t, localStream));

    const remoteStream = new MediaStream();
    pc.addEventListener('track', event => {
      remoteStream.addTrack(event.track);
      remoteAudioEl.srcObject = remoteStream;
      // Setup analyser when the first audio track arrives
      if (event.track.kind === 'audio') {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const source = ctx.createMediaStreamSource(remoteStream);
        remoteAnalyser = ctx.createAnalyser();
        remoteAnalyser.fftSize = 256;
        remoteData = new Uint8Array(remoteAnalyser.frequencyBinCount);
        source.connect(remoteAnalyser);
      }
    });

    // Create a data channel to send initial instructions if needed
    const dc = pc.createDataChannel('oai-events');
    dc.addEventListener('open', () => {
      // Request the assistant to begin speaking immediately using session instructions
      try {
        dc.send(JSON.stringify({ type: 'response.create' }));
      } catch (e) {}
    });

    // Listen for incoming data channel messages (transcription)
    pc.addEventListener('datachannel', (event) => {
      const channel = event.channel;
      channel.addEventListener('message', (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('Received data channel message:', data);
          
          // Handle different types of messages
          if (data.type === 'conversation.item.output_audio_buffer.speech_started') {
            // Agent started speaking
            isAgentSpeaking = true;
            console.log('Agent started speaking');
          } else if (data.type === 'conversation.item.output_audio_buffer.speech_stopped') {
            // Agent stopped speaking
            isAgentSpeaking = false;
            console.log('Agent stopped speaking');
          } else if (data.type === 'conversation.item.input_audio_buffer.committed') {
            // User started speaking
            isAgentSpeaking = false;
          }
        } catch (error) {
          console.error('Error parsing data channel message:', error);
        }
      });
    });

    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);

    // Ask server to mint ephemeral session
    const sessionRes = await fetch('/tutor/realtime/session', { method: 'POST' });
    const sessionJson = await sessionRes.json();
    if (!sessionRes.ok) {
      throw new Error(sessionJson && sessionJson.message ? sessionJson.message : 'Failed to create realtime session');
    }

    const baseUrl = 'https://api.openai.com/v1/realtime';
    const model = (window.OPENAI_REALTIME_MODEL || 'gpt-4o-mini-realtime-preview');
    console.log('Starting SDP negotiation with model:', model);
    console.log('Session client_secret:', sessionJson.client_secret ? 'present' : 'missing');
    
    const sdpRes = await fetch(`${baseUrl}?model=${encodeURIComponent(model)}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${sessionJson.client_secret && sessionJson.client_secret.value ? sessionJson.client_secret.value : ''}`,
        'OpenAI-Beta': 'realtime=v1',
        'Content-Type': 'application/sdp',
        'Accept': 'application/sdp'
      },
      body: offer.sdp
    });

    console.log('SDP response status:', sdpRes.status);
    
    if (!sdpRes.ok) {
      const errorText = await sdpRes.text();
      console.error('SDP response error:', sdpRes.status, errorText);
      throw new Error(`SDP negotiation failed: ${sdpRes.status} ${errorText}`);
    }
    
    const answerSDP = await sdpRes.text();
    await pc.setRemoteDescription({ type: 'answer', sdp: answerSDP });
    updateStatus('Live session connected. Speak to the tutor!', true);
    
    // Enable mute button
    if (muteButton) {
      muteButton.disabled = false;
    }
    
    
    // Add connection state handling
    pc.onconnectionstatechange = () => {
      console.log('Connection state:', pc.connectionState);
      if (pc.connectionState === 'connected') {
        updateStatus('Live session connected. Speak to the tutor!', true);
        if (muteButton) muteButton.disabled = false;
      } else if (pc.connectionState === 'disconnected' || pc.connectionState === 'failed' || pc.connectionState === 'closed') {
        updateStatus('Connection lost. Please refresh.', false);
        if (muteButton) muteButton.disabled = true;
        teardownRealtime();
        setTimeout(initTutor, 2000); // Attempt to re-initialize after a delay
      } else if (pc.connectionState === 'connecting') {
        updateStatus('Connecting...', false);
      }
    };
    
    return pc;
  }

  async function teardownRealtime() {
    if (pc) {
      pc.getSenders().forEach(s => { try { s.track && s.track.stop(); } catch(e){} });
      try { pc.close(); } catch(e){}
      pc = null;
    }
    if (localStream) {
      localStream.getTracks().forEach(t => { try { t.stop(); } catch(e){} });
      localStream = null;
    }
    
    isAgentSpeaking = false;
    
    updateStatus('Ready to connect', false);
  }

  function updateStatus(message, connected) {
    statusTextEl.textContent = message;
    isConnected = connected;
    
    if (!connected && muteButton) {
      muteButton.disabled = true;
    }
  }

  // Toggle mute functionality
  function toggleMute() {
    if (!localStream) return;
    
    isMuted = !isMuted;
    
    // Enable/disable audio tracks
    localStream.getAudioTracks().forEach(track => {
      track.enabled = !isMuted;
    });
    
    // Update button appearance
    if (muteButton) {
      const muteIcon = document.getElementById('muteIcon');
      const muteText = document.getElementById('muteText');
      
      if (isMuted) {
        muteButton.classList.add('muted');
        muteIcon.textContent = '🔇';
        muteText.textContent = 'Unmute';
        statusTextEl.textContent = 'Microphone muted - AI will continue speaking';
      } else {
        muteButton.classList.remove('muted');
        muteIcon.textContent = '🎤';
        muteText.textContent = 'Mute';
        statusTextEl.textContent = 'Live session connected. Speak to the tutor!';
      }
    }
    
    console.log('Microphone', isMuted ? 'muted' : 'unmuted');
  }

  // Load student information
  async function loadStudentInfo() {
    try {
      const response = await fetch('/tutor/student-name');
      if (response.ok) {
        const data = await response.json();
        if (studentNameEl) {
          studentNameEl.textContent = data.name;
        }
      } else {
        // Fallback to default
        if (studentNameEl) {
          studentNameEl.textContent = 'Student';
        }
      }
    } catch (error) {
      console.error('Failed to load student name:', error);
      if (studentNameEl) {
        studentNameEl.textContent = 'Student';
      }
    }
  }

  // Load lecture topics from key_points.txt
  async function loadLectureTopics() {
    try {
      const response = await fetch('/tutor/topics');
      if (response.ok) {
        const topics = await response.json();
        if (topicsListEl && topics.length > 0) {
          topicsListEl.innerHTML = topics.map(topic => 
            `<div class="topic-item">${topic}</div>`
          ).join('');
        }
      } else {
        // Fallback: show loading message
        if (topicsListEl) {
          topicsListEl.innerHTML = '<div class="topic-item">Topics will be loaded from your lecture notes</div>';
        }
      }
    } catch (error) {
      console.error('Failed to load topics:', error);
      if (topicsListEl) {
        topicsListEl.innerHTML = '<div class="topic-item">Unable to load topics</div>';
      }
    }
  }

  // Start session timer
  function startSessionTimer() {
    sessionStartTime = Date.now();
    timerInterval = setInterval(updateTimer, 1000);
  }

  // Update session timer
  function updateTimer() {
    if (!sessionStartTime) return;
    
    const elapsed = Date.now() - sessionStartTime;
    const minutes = Math.floor(elapsed / 60000);
    const seconds = Math.floor((elapsed % 60000) / 1000);
    
    if (sessionTimer) {
      sessionTimer.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
  }


  // Agent speaking animation
  function tickAgent() {
    if (remoteAnalyser && agentIcon) {
      remoteAnalyser.getByteTimeDomainData(remoteData);
      let sum = 0;
      for (let i = 0; i < remoteData.length; i++) {
        const v = (remoteData[i] - 128) / 128;
        sum += v * v;
      }
      const rms = Math.sqrt(sum / remoteData.length);
      const scale = 1 + Math.min(0.25, rms * 3);
      
      // Update visual feedback based on speaking state
      if (isAgentSpeaking || rms > 0.01) {
        agentIcon.classList.add('speaking');
        agentIcon.style.boxShadow = `0 0 ${Math.max(20, rms*120).toFixed(0)}px rgba(245, 158, 11, 0.6)`;
        agentIcon.style.transform = `scale(${scale.toFixed(3)}) translateY(${(Math.min(16, rms*60)).toFixed(0)}px)`;
      } else {
        agentIcon.classList.remove('speaking');
        agentIcon.style.boxShadow = `0 0 ${Math.max(20, rms*120).toFixed(0)}px rgba(59, 130, 246, 0.6)`;
        agentIcon.style.transform = `scale(${scale.toFixed(3)}) translateY(${(Math.min(16, rms*60)).toFixed(0)}px)`;
      }
    }
    requestAnimationFrame(tickAgent);
  }

  // End session
  function endSession() {
    if (confirm('Are you sure you want to end the tutoring session?')) {
      // Stop timer
      if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
      }
      
      
      // Cleanup WebRTC
      teardownRealtime();
      
      // Redirect to explanation page
      window.location.href = '/explanation';
    }
  }

  // Auto-start realtime on page load (like ai_mock_interview)
  (async () => {
    try {
      await initTutor();
    } catch (e) {
      console.warn('Tutor initialization failed:', e);
    }
    // Start agent animation
    requestAnimationFrame(tickAgent);
  })();

  // Cleanup on page unload
  window.addEventListener('beforeunload', () => {
    if (timerInterval) {
      clearInterval(timerInterval);
    }
    teardownRealtime();
  });

})();