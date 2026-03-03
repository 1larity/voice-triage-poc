const state = {
  sessionId: null,
  sessionGreeting: null,
  sessionGreetingTtsUrl: null,
  sessionGreetingTtsError: null,
  greetingShown: false,
  stream: null,
  audioContext: null,
  source: null,
  processor: null,
  chunks: [],
  isRecording: false,
  isStopping: false,
  speechDetected: false,
  speechStartedAtMs: null,
  lastSpeechAtMs: null,
  recordingStartedAtMs: null,
  noiseFloorRms: 0.002,
  vad: null,
  continuousMode: false,
  ttsAudio: null,
  selectedVoiceId: null,
};
const API_BASE = "/api/v1";
const DEFAULT_VAD_CONFIG = {
  vad_rms_threshold: 0.006,
  vad_abs_min_rms: 0.0045,
  vad_speech_factor: 2.2,
  vad_noise_alpha: 0.96,
  vad_min_speech_ms: 180,
  vad_silence_hold_ms: 1000,
  vad_max_turn_ms: 30000,
};
state.vad = { ...DEFAULT_VAD_CONFIG };

const chatLog = document.getElementById("chatLog");
const statusText = document.getElementById("statusText");
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const newSessionBtn = document.getElementById("newSessionBtn");
const reindexBtn = document.getElementById("reindexBtn");
const voiceSelect = document.getElementById("voiceSelect");
const capturedDataBox = document.getElementById("capturedDataBox");

function setStatus(message) {
  statusText.textContent = message;
}

function addMessage(role, text, meta = "") {
  const el = document.createElement("article");
  el.className = `message ${role}`;
  const heading = role === "assistant" ? "Assistant" : role === "user" ? "User" : "System";
  el.innerHTML = `
    <p class="message-head">${heading}</p>
    <div>${escapeHtml(text)}</div>
    ${meta ? `<div class="meta">${escapeHtml(meta)}</div>` : ""}
  `;
  chatLog.appendChild(el);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function updateCapturedDataBox(outcome) {
  const payload =
    outcome &&
    typeof outcome === "object" &&
    outcome.workflow === "move_home" &&
    outcome.captured_data
      ? outcome.captured_data
      : {
          current_address: null,
          current_postcode: null,
          new_address: null,
          new_postcode: null,
          move_date: null,
          current_address_verified: false,
          new_address_verified: false,
        };

  capturedDataBox.value = JSON.stringify(payload, null, 2);
}

async function loadVoices() {
  const response = await fetch(`${API_BASE}/voices`);
  if (!response.ok) {
    throw new Error(`Failed to load voices (${response.status})`);
  }

  const payload = await response.json();
  voiceSelect.innerHTML = "";

  if (!payload.voices || payload.voices.length === 0) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No voices found";
    voiceSelect.appendChild(option);
    voiceSelect.disabled = true;
    state.selectedVoiceId = null;
    return;
  }

  payload.voices.forEach((voice) => {
    const option = document.createElement("option");
    option.value = voice.voice_id;
    option.textContent = voice.label;
    voiceSelect.appendChild(option);
  });

  state.selectedVoiceId = payload.default_voice_id || payload.voices[0].voice_id;
  voiceSelect.value = state.selectedVoiceId;
  voiceSelect.disabled = false;
}

async function loadClientConfig() {
  const response = await fetch(`${API_BASE}/config`);
  if (!response.ok) {
    throw new Error(`Failed to load client config (${response.status})`);
  }
  const payload = await response.json();
  state.vad = {
    ...DEFAULT_VAD_CONFIG,
    ...payload,
  };
}

async function setSessionVoice(voiceId, options = {}) {
  const { announce = true } = options;
  if (!state.sessionId || !voiceId) {
    return;
  }
  const response = await fetch(`${API_BASE}/session/${state.sessionId}/voice`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ voice_id: voiceId }),
  });
  if (!response.ok) {
    throw new Error(`Failed to set voice (${response.status})`);
  }
  const payload = await response.json();
  state.selectedVoiceId = payload.voice_id;
  voiceSelect.value = payload.voice_id;
  if (announce) {
    addMessage("system", `Voice set to: ${payload.label}`);
  }
}

function showSessionGreeting() {
  if (state.greetingShown || !state.sessionGreeting) {
    return false;
  }
  addMessage("assistant", state.sessionGreeting);
  state.greetingShown = true;
  return true;
}

async function createSession() {
  const response = await fetch(`${API_BASE}/session`, { method: "POST" });
  if (!response.ok) {
    throw new Error(`Failed to create session (${response.status})`);
  }
  const payload = await response.json();
  state.sessionId = payload.session_id;
  state.sessionGreeting = payload.assistant_message;
  state.sessionGreetingTtsUrl = payload.tts_audio_url || null;
  state.sessionGreetingTtsError = payload.tts_error || null;
  state.greetingShown = false;
  chatLog.innerHTML = "";
  updateCapturedDataBox(null);

  const targetVoiceId = state.selectedVoiceId || payload.selected_voice_id;
  if (targetVoiceId) {
    try {
      await setSessionVoice(targetVoiceId, { announce: false });
    } catch (error) {
      addMessage("system", `Could not set voice: ${error}`);
    }
  }
}

async function reindexKnowledgeBase() {
  const response = await fetch(`${API_BASE}/reindex`, { method: "POST" });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Failed to reindex knowledge base (${response.status}): ${detail}`);
  }
  return response.json();
}

async function startRecording() {
  if (state.isRecording || state.isStopping) {
    return;
  }
  if (!state.sessionId) {
    await createSession();
  }
  if (showSessionGreeting()) {
    if (state.sessionGreetingTtsUrl) {
      await playTts(state.sessionGreetingTtsUrl, true);
    } else if (state.sessionGreetingTtsError) {
      addMessage("system", `Greeting TTS unavailable: ${state.sessionGreetingTtsError}`);
    }
  }

  state.stream = await requestMicrophoneStream();
  state.audioContext = new AudioContext();
  state.source = state.audioContext.createMediaStreamSource(state.stream);
  state.processor = state.audioContext.createScriptProcessor(4096, 1, 1);
  state.chunks = [];
  state.speechDetected = false;
  state.speechStartedAtMs = null;
  state.lastSpeechAtMs = null;
  state.recordingStartedAtMs = performance.now();
  state.noiseFloorRms = 0.002;

  state.processor.onaudioprocess = (event) => {
    const channelData = event.inputBuffer.getChannelData(0);
    state.chunks.push(new Float32Array(channelData));
    handleVadFrame(channelData, state.audioContext.sampleRate);
  };

  state.source.connect(state.processor);
  state.processor.connect(state.audioContext.destination);

  state.isRecording = true;
  startBtn.disabled = true;
  stopBtn.disabled = false;
  setStatus("Listening... start speaking.");
}

async function requestMicrophoneStream() {
  const mediaDevices = navigator.mediaDevices;
  if (mediaDevices && typeof mediaDevices.getUserMedia === "function") {
    return mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
  }

  const legacyGetUserMedia =
    navigator.getUserMedia || navigator.webkitGetUserMedia || navigator.mozGetUserMedia;
  if (typeof legacyGetUserMedia === "function") {
    return new Promise((resolve, reject) => {
      legacyGetUserMedia.call(navigator, { audio: true }, resolve, reject);
    });
  }

  const secureHint = window.isSecureContext
    ? "Your browser does not expose microphone APIs here."
    : "Microphone access needs a secure context (HTTPS or localhost).";
  throw new Error(
    `${secureHint} Open this app via https://<host>:<port> or use localhost on the same machine.`,
  );
}

function requestStopRecording(reason) {
  if (!state.isRecording || state.isStopping) {
    return;
  }
  state.isStopping = true;
  void stopRecording({ reason }).catch((error) => {
    addMessage("system", `Could not process recording: ${error}`);
    setStatus("Error while processing audio.");
  });
}

function computeRms(samples) {
  let sumSquares = 0;
  for (let index = 0; index < samples.length; index += 1) {
    const value = samples[index];
    sumSquares += value * value;
  }
  return Math.sqrt(sumSquares / Math.max(1, samples.length));
}

function handleVadFrame(channelData, sampleRate) {
  if (!state.isRecording || state.isStopping) {
    return;
  }

  const nowMs = performance.now();
  const frameDurationMs = (channelData.length / Math.max(1, sampleRate)) * 1000;
  const rms = computeRms(channelData);
  const adaptiveThreshold = Math.max(
    state.vad.vad_abs_min_rms,
    state.vad.vad_rms_threshold,
    state.noiseFloorRms * state.vad.vad_speech_factor,
  );
  const isSpeechFrame = rms >= adaptiveThreshold;

  if (isSpeechFrame) {
    state.lastSpeechAtMs = nowMs;
    if (state.speechStartedAtMs === null) {
      state.speechStartedAtMs = nowMs;
    }
    if (!state.speechDetected && nowMs - state.speechStartedAtMs >= state.vad.vad_min_speech_ms) {
      state.speechDetected = true;
      setStatus("Listening...");
    }
  } else if (!state.speechDetected) {
    state.noiseFloorRms =
      state.vad.vad_noise_alpha * state.noiseFloorRms + (1 - state.vad.vad_noise_alpha) * rms;
    state.speechStartedAtMs = null;
    if (
      state.recordingStartedAtMs !== null &&
      nowMs - state.recordingStartedAtMs > state.vad.vad_max_turn_ms
    ) {
      setStatus("Processing turn...");
      requestStopRecording("max_turn_no_speech");
      return;
    }
  }

  if (
    state.speechDetected &&
    state.lastSpeechAtMs !== null &&
    nowMs - state.lastSpeechAtMs >= state.vad.vad_silence_hold_ms
  ) {
    setStatus("Silence detected. Processing...");
    requestStopRecording("vad_silence");
    return;
  }

  if (
    state.speechDetected &&
    state.recordingStartedAtMs !== null &&
    nowMs - state.recordingStartedAtMs + frameDurationMs >= state.vad.vad_max_turn_ms
  ) {
    setStatus("Processing long turn...");
    requestStopRecording("max_turn");
  }
}

async function stopRecording(options = {}) {
  const { reason = "manual" } = options;
  if (!state.isRecording) {
    state.isStopping = false;
    return;
  }

  state.isRecording = false;
  startBtn.disabled = false;
  stopBtn.disabled = true;
  setStatus("Processing audio...");

  if (state.processor) {
    state.processor.disconnect();
  }
  if (state.source) {
    state.source.disconnect();
  }
  if (state.stream) {
    state.stream.getTracks().forEach((track) => track.stop());
  }

  const inputRate = state.audioContext ? state.audioContext.sampleRate : 44100;
  if (state.audioContext) {
    await state.audioContext.close();
  }

  const chunks = state.chunks;
  const hadSpeech = state.speechDetected;
  state.chunks = [];
  state.speechDetected = false;
  state.speechStartedAtMs = null;
  state.lastSpeechAtMs = null;
  state.recordingStartedAtMs = null;
  state.noiseFloorRms = 0.002;

  const shouldForceProcessWithoutVad =
    reason === "max_turn_no_speech" || (reason === "manual" && chunks.length > 0);

  if (!hadSpeech && !shouldForceProcessWithoutVad) {
    state.isStopping = false;
    if (reason === "manual") {
      setStatus("Stopped.");
    } else {
      setStatus("Listening...");
      if (state.continuousMode) {
        await startRecording();
      }
    }
    return;
  }

  const wavBlob = buildWavBlob(chunks, inputRate, 16000);
  state.isStopping = false;
  await sendTurn(wavBlob);
}

function buildWavBlob(chunks, sourceRate, targetRate) {
  const merged = mergeChunks(chunks);
  const pcm = sourceRate === targetRate ? merged : downsampleBuffer(merged, sourceRate, targetRate);
  const wavBytes = encodeWav(pcm, targetRate);
  return new Blob([wavBytes], { type: "audio/wav" });
}

function mergeChunks(chunks) {
  const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const result = new Float32Array(totalLength);
  let offset = 0;
  chunks.forEach((chunk) => {
    result.set(chunk, offset);
    offset += chunk.length;
  });
  return result;
}

function downsampleBuffer(buffer, sampleRate, targetRate) {
  if (targetRate > sampleRate) {
    return buffer;
  }
  const ratio = sampleRate / targetRate;
  const newLength = Math.round(buffer.length / ratio);
  const result = new Float32Array(newLength);
  let offsetResult = 0;
  let offsetBuffer = 0;

  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
    let accum = 0;
    let count = 0;
    for (let index = offsetBuffer; index < nextOffsetBuffer && index < buffer.length; index += 1) {
      accum += buffer[index];
      count += 1;
    }
    result[offsetResult] = accum / Math.max(1, count);
    offsetResult += 1;
    offsetBuffer = nextOffsetBuffer;
  }
  return result;
}

function encodeWav(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  writeAscii(view, 0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeAscii(view, 8, "WAVE");
  writeAscii(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeAscii(view, 36, "data");
  view.setUint32(40, samples.length * 2, true);

  floatTo16BitPcm(view, 44, samples);
  return buffer;
}

function writeAscii(view, offset, text) {
  for (let index = 0; index < text.length; index += 1) {
    view.setUint8(offset + index, text.charCodeAt(index));
  }
}

function floatTo16BitPcm(view, offset, input) {
  for (let index = 0; index < input.length; index += 1, offset += 2) {
    const sample = Math.max(-1, Math.min(1, input[index]));
    view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
  }
}

async function sendTurn(wavBlob) {
  const formData = new FormData();
  formData.append("audio", wavBlob, "turn.wav");

  const response = await fetch(`${API_BASE}/session/${state.sessionId}/turn`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const detail = await response.text();
    addMessage("system", `Request failed: ${detail}`);
    setStatus("Ready. Click Start Listening.");
    return;
  }

  const payload = await response.json();
  if (payload.selected_voice_id) {
    state.selectedVoiceId = payload.selected_voice_id;
    if (!voiceSelect.disabled) {
      voiceSelect.value = payload.selected_voice_id;
    }
  }
  addMessage("user", payload.transcript);
  addMessage("assistant", payload.assistant_response);
  updateCapturedDataBox(payload.outcome);
  if (payload.tts_audio_url) {
    await playTts(payload.tts_audio_url, true);
  } else if (payload.tts_error) {
    addMessage("system", `TTS unavailable: ${payload.tts_error}`);
  }

  if (state.continuousMode) {
    setStatus("Listening for next turn...");
    await startRecording();
  } else {
    setStatus("Ready. Click Start Listening.");
  }
}

async function playTts(ttsAudioUrl, waitForEnd = false) {
  try {
    if (state.ttsAudio) {
      state.ttsAudio.pause();
      state.ttsAudio = null;
    }
    const player = new Audio(ttsAudioUrl);
    state.ttsAudio = player;
    await player.play();
    if (waitForEnd) {
      await new Promise((resolve) => {
        player.onended = resolve;
        player.onerror = resolve;
      });
    }
  } catch (error) {
    addMessage("system", `TTS playback failed: ${error}`);
  }
}

startBtn.addEventListener("click", async () => {
  try {
    state.continuousMode = true;
    await startRecording();
  } catch (error) {
    addMessage("system", `Could not start recording: ${error}`);
    setStatus("Microphone unavailable.");
  }
});

stopBtn.addEventListener("click", async () => {
  try {
    state.continuousMode = false;
    await stopRecording({ reason: "manual" });
  } catch (error) {
    addMessage("system", `Could not process recording: ${error}`);
    setStatus("Error while processing audio.");
  }
});

newSessionBtn.addEventListener("click", async () => {
  try {
    await createSession();
    setStatus("New session ready.");
  } catch (error) {
    addMessage("system", `Could not create session: ${error}`);
  }
});

reindexBtn.addEventListener("click", async () => {
  reindexBtn.disabled = true;
  const previousStatus = statusText.textContent;
  setStatus("Reindexing knowledge base...");
  try {
    const payload = await reindexKnowledgeBase();
    addMessage(
      "system",
      `Knowledge base reindexed: ${payload.chunk_count} chunks from ${payload.kb_file_count} files.`,
    );
    setStatus("Knowledge base reindex complete.");
  } catch (error) {
    addMessage("system", `Knowledge base reindex failed: ${error}`);
    setStatus(previousStatus || "Ready. Click Start Listening.");
  } finally {
    reindexBtn.disabled = false;
  }
});

voiceSelect.addEventListener("change", async () => {
  const voiceId = voiceSelect.value;
  state.selectedVoiceId = voiceId;
  if (!state.sessionId) {
    return;
  }
  try {
    await setSessionVoice(voiceId);
  } catch (error) {
    addMessage("system", `Could not set voice: ${error}`);
  }
});

async function initializeUi() {
  let configError = null;
  try {
    await loadClientConfig();
  } catch (error) {
    state.vad = { ...DEFAULT_VAD_CONFIG };
    configError = error;
  }

  try {
    await loadVoices();
    updateCapturedDataBox(null);
    setStatus("Ready. Click Start Listening.");
    if (configError) {
      addMessage("system", `Client config unavailable, using defaults: ${configError}`);
    }
  } catch (error) {
    addMessage("system", `Failed to initialize session: ${error}`);
  }
}

initializeUi();
