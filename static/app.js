/* ============================================================
   Brightwood RPG — Client-Side Application Logic
   Handles state management, API calls, recording, and playback
   ============================================================ */

(function () {
  "use strict";

  // ==================== STATE ====================
  const state = {
    playerPos: [260, 260],
    activeNpc: null,
    conversations: {},
    isRecording: false,
    isProcessing: false,
    mediaRecorder: null,
    audioChunks: [],
    recordingStartTime: null,
    timerInterval: null,
  };

  // ==================== DOM REFS ====================
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  let els = {};

  function cacheDom() {
    els = {
      mapImg: $("#map-image"),
      npcBanner: $("#npc-banner"),
      npcName: $("#npc-name"),
      npcTitle: $("#npc-title"),
      npcStatus: $("#npc-status"),
      statusDot: $("#status-dot"),
      chatContainer: $("#chat-container"),
      chatEmpty: $("#chat-empty"),
      btnSpeak: $("#btn-speak"),
      btnClear: $("#btn-clear"),
      btnRecord: $("#btn-record"),
      btnStopRecord: $("#btn-stop-record"),
      recordSection: $("#record-section"),
      recordTimer: $("#record-timer"),
      textInput: $("#text-input"),
      btnSend: $("#btn-send"),
      audioPlayer: $("#npc-audio-player"),
      loadingOverlay: $("#loading-overlay"),
      loadingText: $("#loading-text"),
    };
  }

  // ==================== INITIALIZATION ====================
  document.addEventListener("DOMContentLoaded", () => {
    cacheDom();
    bindMovement();
    bindTeleport();
    bindSpeechControls();
    bindTextInput();

    // Load initial map
    updateMap();
  });

  // ==================== MAP & MOVEMENT ====================
  async function updateMap() {
    const [px, py] = state.playerPos;
    const url = `/api/map?px=${px}&py=${py}&t=${Date.now()}`;
    els.mapImg.src = url;
  }

  async function movePlayer(direction) {
    if (state.isProcessing) return;

    try {
      const res = await fetch("/api/move", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          direction: direction,
          player_pos: state.playerPos,
        }),
      });

      const data = await res.json();
      state.playerPos = data.player_pos;
      state.activeNpc = data.active_npc;

      updateMap();
      updateNpcBanner();
      loadChatHistory();
    } catch (err) {
      console.error("[Move Error]", err);
    }
  }

  async function teleportTo(location) {
    if (state.isProcessing) return;

    try {
      const res = await fetch("/api/teleport", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ location: location }),
      });

      const data = await res.json();
      state.playerPos = data.player_pos;
      state.activeNpc = data.active_npc;

      updateMap();
      updateNpcBanner();
      loadChatHistory();
    } catch (err) {
      console.error("[Teleport Error]", err);
    }
  }

  function bindMovement() {
    $$(".btn-move").forEach((btn) => {
      btn.addEventListener("click", () => movePlayer(btn.dataset.dir));
    });
  }

  function bindTeleport() {
    $$(".btn-teleport").forEach((btn) => {
      btn.addEventListener("click", () => teleportTo(btn.dataset.location));
    });
  }

  // ==================== NPC BANNER ====================
  function updateNpcBanner() {
    const npc = state.activeNpc;

    if (npc) {
      els.npcBanner.classList.add("active");
      els.npcBanner.classList.remove("exploring");
      els.statusDot.className = "status-dot online";
      els.npcName.textContent = npc.name;
      els.npcTitle.textContent = `${npc.title} at ${npc.location}`;
      els.npcStatus.textContent = "In range — record your voice or type a message";
    } else {
      els.npcBanner.classList.remove("active");
      els.npcBanner.classList.add("exploring");
      els.statusDot.className = "status-dot offline";
      els.npcName.textContent = "Exploring Brightwood";
      els.npcTitle.textContent = "Move closer to a villager on the map";
      els.npcStatus.textContent = "No villager in range";
    }
  }

  // ==================== CHAT ====================
  function loadChatHistory() {
    if (!state.activeNpc) {
      els.chatContainer.innerHTML = '<div class="chat-empty" id="chat-empty">Walk near a villager to start a conversation</div>';
      return;
    }

    const npcId = state.activeNpc.id;
    const msgs = state.conversations[npcId] || [];

    if (msgs.length === 0) {
      els.chatContainer.innerHTML = `<div class="chat-empty" id="chat-empty">Start talking to ${state.activeNpc.name}</div>`;
      return;
    }

    renderMessages(msgs);
  }

  function renderMessages(msgs) {
    els.chatContainer.innerHTML = "";

    msgs.forEach((msg) => {
      const div = document.createElement("div");
      div.className = `chat-msg ${msg.role === "user" ? "user" : "npc"}`;

      const label = document.createElement("div");
      label.className = "msg-label";
      label.textContent = msg.role === "user" ? "You" : (state.activeNpc ? state.activeNpc.name : "NPC");

      const text = document.createElement("div");
      text.textContent = msg.content;

      div.appendChild(label);
      div.appendChild(text);
      els.chatContainer.appendChild(div);
    });

    // Scroll to bottom
    els.chatContainer.scrollTop = els.chatContainer.scrollHeight;
  }

  function appendMessage(role, content) {
    if (!state.activeNpc) return;

    const npcId = state.activeNpc.id;
    if (!state.conversations[npcId]) state.conversations[npcId] = [];
    state.conversations[npcId].push({ role, content });

    // Remove empty state message
    const empty = els.chatContainer.querySelector(".chat-empty");
    if (empty) empty.remove();

    const div = document.createElement("div");
    div.className = `chat-msg ${role === "user" ? "user" : "npc"}`;

    const label = document.createElement("div");
    label.className = "msg-label";
    label.textContent = role === "user" ? "You" : (state.activeNpc ? state.activeNpc.name : "NPC");

    const text = document.createElement("div");
    text.textContent = content;

    div.appendChild(label);
    div.appendChild(text);
    els.chatContainer.appendChild(div);
    els.chatContainer.scrollTop = els.chatContainer.scrollHeight;
  }

  // ==================== SPEECH CONTROLS ====================
  function bindSpeechControls() {
    els.btnRecord.addEventListener("click", startRecording);
    els.btnStopRecord.addEventListener("click", stopRecording);
    els.btnSpeak.addEventListener("click", handleSpeak);
    els.btnClear.addEventListener("click", clearChat);
  }

  async function startRecording() {
    if (state.isRecording || state.isProcessing) return;
    if (!state.activeNpc) {
      alert("Move closer to a villager on the map first!");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      state.mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      state.audioChunks = [];

      state.mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) state.audioChunks.push(e.data);
      };

      state.mediaRecorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(state.audioChunks, { type: "audio/webm" });
        sendAudioToApi(blob);
      };

      state.mediaRecorder.start();
      state.isRecording = true;
      state.recordingStartTime = Date.now();

      // UI updates
      els.recordSection.classList.add("recording");
      els.btnRecord.classList.add("active");
      els.btnRecord.disabled = true;
      els.btnStopRecord.disabled = false;

      // Start timer
      state.timerInterval = setInterval(updateRecordTimer, 100);
    } catch (err) {
      console.error("[Mic Error]", err);
      alert("Microphone access denied. Please allow microphone access to record.");
    }
  }

  function stopRecording() {
    if (!state.isRecording || !state.mediaRecorder) return;

    state.mediaRecorder.stop();
    state.isRecording = false;

    // UI updates
    els.recordSection.classList.remove("recording");
    els.btnRecord.classList.remove("active");
    els.btnRecord.disabled = false;
    els.btnStopRecord.disabled = true;

    clearInterval(state.timerInterval);
    els.recordTimer.textContent = "00:00";
  }

  function updateRecordTimer() {
    if (!state.recordingStartTime) return;
    const elapsed = Math.floor((Date.now() - state.recordingStartTime) / 1000);
    const mins = String(Math.floor(elapsed / 60)).padStart(2, "0");
    const secs = String(elapsed % 60).padStart(2, "0");
    els.recordTimer.textContent = `${mins}:${secs}`;
  }

  async function sendAudioToApi(audioBlob) {
    if (!state.activeNpc) return;
    showLoading("Processing voice input...");

    const npcId = state.activeNpc.id;
    const messages = state.conversations[npcId] || [];

    const formData = new FormData();
    formData.append("audio", audioBlob, "recording.webm");
    formData.append("npc_id", npcId);
    formData.append("messages", JSON.stringify(messages));
    formData.append("player_pos", JSON.stringify(state.playerPos));

    try {
      const res = await fetch("/api/talk", { method: "POST", body: formData });
      const data = await res.json();

      if (data.user_text) appendMessage("user", data.user_text);
      if (data.npc_text) appendMessage("assistant", data.npc_text);

      // Play NPC audio
      if (data.audio_url) {
        els.audioPlayer.src = data.audio_url;
        els.audioPlayer.play().catch(() => {});
      }
    } catch (err) {
      console.error("[Talk Error]", err);
      appendMessage("assistant", "(Connection error — please try again)");
    } finally {
      hideLoading();
    }
  }

  // ==================== TEXT INPUT ====================
  function bindTextInput() {
    els.btnSend.addEventListener("click", sendTextMessage);
    els.textInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendTextMessage();
      }
    });
  }

  async function sendTextMessage() {
    const text = els.textInput.value.trim();
    if (!text || state.isProcessing) return;

    if (!state.activeNpc) {
      alert("Move closer to a villager on the map first!");
      return;
    }

    els.textInput.value = "";
    showLoading("Generating response...");

    const npcId = state.activeNpc.id;
    const messages = state.conversations[npcId] || [];

    const formData = new FormData();
    formData.append("user_text", text);
    formData.append("npc_id", npcId);
    formData.append("messages", JSON.stringify(messages));
    formData.append("player_pos", JSON.stringify(state.playerPos));

    try {
      const res = await fetch("/api/talk", { method: "POST", body: formData });
      const data = await res.json();

      if (data.user_text) appendMessage("user", data.user_text);
      if (data.npc_text) appendMessage("assistant", data.npc_text);

      if (data.audio_url) {
        els.audioPlayer.src = data.audio_url;
        els.audioPlayer.play().catch(() => {});
      }
    } catch (err) {
      console.error("[Talk Error]", err);
      appendMessage("assistant", "(Connection error — please try again)");
    } finally {
      hideLoading();
    }
  }

  // ==================== HANDLE SPEAK BUTTON ====================
  async function handleSpeak() {
    // If there's text in the input, send it; otherwise start recording
    const text = els.textInput.value.trim();
    if (text) {
      sendTextMessage();
    } else {
      if (state.isRecording) {
        stopRecording();
      } else {
        startRecording();
      }
    }
  }

  // ==================== CLEAR CHAT ====================
  function clearChat() {
    if (!state.activeNpc) return;
    const npcId = state.activeNpc.id;
    state.conversations[npcId] = [];
    els.chatContainer.innerHTML = `<div class="chat-empty">Start talking to ${state.activeNpc.name}</div>`;
    els.audioPlayer.src = "";
    els.audioPlayer.pause();
  }

  // ==================== LOADING ====================
  function showLoading(text) {
    state.isProcessing = true;
    els.loadingText.textContent = text || "Processing...";
    els.loadingOverlay.classList.add("active");
    els.btnSpeak.disabled = true;
    els.btnSend.disabled = true;
  }

  function hideLoading() {
    state.isProcessing = false;
    els.loadingOverlay.classList.remove("active");
    els.btnSpeak.disabled = false;
    els.btnSend.disabled = false;
  }
})();
