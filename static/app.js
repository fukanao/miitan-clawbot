const face = document.querySelector("#face");
const form = document.querySelector("#chatForm");
const input = document.querySelector("#messageInput");
const messages = document.querySelector("#messages");
const statusText = document.querySelector("#status");
const voiceButton = document.querySelector("#voiceButton");
const cameraButton = document.querySelector("#cameraButton");
const cameraTray = document.querySelector("#cameraTray");
const cameraPreview = document.querySelector("#cameraPreview");
const cameraCanvas = document.querySelector("#cameraCanvas");
const captureButton = document.querySelector("#captureButton");
const switchCameraButton = document.querySelector("#switchCameraButton");
const closeCameraButton = document.querySelector("#closeCameraButton");
const photoDraft = document.querySelector("#photoDraft");
const photoDraftImage = document.querySelector("#photoDraftImage");
const clearPhotoButton = document.querySelector("#clearPhotoButton");

const history = [];
let activeImage = "maid_05_tsujo_normal.png";
let cameraStream = null;
let cameraFacingMode = "environment";
let pendingImage = null;
let previousResponseId = null;
let realtimePeer = null;
let realtimeChannel = null;
let realtimeMicStream = null;
let realtimeAudio = null;
let realtimeAssistantDraft = "";

const faceImageBasePath = "../maid_faces/";
const emotionFaces = [
  {
    image: "maid_01_yorokobi_joy.png",
    keywords: ["うれしい", "嬉しい", "よかった", "最高", "ありがとう", "助かる"],
  },
  {
    image: "maid_02_ikari_anger.png",
    keywords: ["怒", "ひどい", "許せ", "だめ", "ダメ"],
  },
  {
    image: "maid_03_kanashimi_sadness.png",
    keywords: ["悲しい", "つらい", "寂しい", "ごめん", "残念"],
  },
  {
    image: "maid_04_tanoshimi_fun.png",
    keywords: ["楽しい", "楽しみ", "わくわく", "面白い", "やってみよう"],
  },
  {
    image: "maid_06_tere_shy.png",
    keywords: ["照れ", "えへへ", "恥ずかしい"],
  },
  {
    image: "maid_07_odoroki_surprise.png",
    keywords: ["びっくり", "驚", "すごい", "まさか"],
  },
  {
    image: "maid_08_komari_troubled.png",
    keywords: ["困", "うーん", "難しい", "確認", "問題", "エラー"],
  },
  {
    image: "maid_09_dojikko_clumsy.png",
    keywords: ["あれ", "うっかり", "ドジ", "間違え"],
  },
];

function addMessage(role, content, image = null, citations = []) {
  const bubble = document.createElement("div");
  bubble.className = `message ${role}`;

  if (image) {
    const snapshot = document.createElement("img");
    snapshot.className = "message-image";
    snapshot.src = image;
    snapshot.alt = "撮影した写真";
    bubble.appendChild(snapshot);
  }

  if (content) {
    const text = document.createElement("span");
    text.textContent = content;
    bubble.appendChild(text);
  }

  if (citations.length) {
    const sourceList = document.createElement("div");
    sourceList.className = "citations";
    citations.forEach((citation) => {
      const link = document.createElement("a");
      link.href = citation.url;
      link.target = "_blank";
      link.rel = "noreferrer";
      link.textContent = citation.title || citation.url;
      sourceList.appendChild(link);
    });
    bubble.appendChild(sourceList);
  }

  messages.appendChild(bubble);
  messages.scrollTop = messages.scrollHeight;
}

function setFace(image) {
  activeImage = image || "maid_05_tsujo_normal.png";
  face.src = `${faceImageBasePath}${encodeURIComponent(activeImage)}`;
}

function setFaceFromText(text) {
  const matched = emotionFaces.find((entry) => entry.keywords.some((keyword) => text.includes(keyword)));
  setFace(matched?.image || "maid_05_tsujo_normal.png");
}

function setPendingImage(image) {
  pendingImage = image;
  photoDraft.hidden = !image;
  photoDraftImage.src = image || "";
  statusText.textContent = image ? "コメントを入れて送信できます" : "会話できます";
}

async function sendMessage(message, image = null) {
  addMessage("user", message, image);
  history.push({ role: "user", content: message });
  statusText.textContent = "OpenAI APIに送信中";

  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      image,
      previous_response_id: previousResponseId,
    }),
  });

  const data = await response.json();
  previousResponseId = data.response_id || previousResponseId;
  addMessage("assistant", data.reply, null, data.citations || []);
  history.push({ role: "assistant", content: data.reply });
  setFace(data.image);
  statusText.textContent = "会話できます";
}

function stopCameraStream() {
  if (!cameraStream) return;
  cameraStream.getTracks().forEach((track) => track.stop());
  cameraStream = null;
}

function updateCameraModeLabel() {
  const isRearCamera = cameraFacingMode === "environment";
  switchCameraButton.textContent = isRearCamera ? "前面" : "背面";
  switchCameraButton.title = isRearCamera ? "前面カメラに切替" : "背面カメラに切替";
  cameraPreview.classList.toggle("user-facing", !isRearCamera);
}

async function openCamera() {
  if (!navigator.mediaDevices?.getUserMedia) {
    addMessage("assistant", "このブラウザではカメラを使えません。");
    return;
  }

  try {
    stopCameraStream();
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: cameraFacingMode } },
      audio: false,
    });
    cameraPreview.srcObject = cameraStream;
    cameraTray.hidden = false;
    updateCameraModeLabel();
    statusText.textContent = "撮影できます";
  } catch (error) {
    addMessage("assistant", "カメラを開けませんでした。ブラウザの許可を確認してください。");
    statusText.textContent = "カメラエラー";
  }
}

function closeCamera() {
  stopCameraStream();
  cameraPreview.srcObject = null;
  cameraTray.hidden = true;
  statusText.textContent = "会話できます";
}

async function switchCamera() {
  cameraFacingMode = cameraFacingMode === "environment" ? "user" : "environment";
  updateCameraModeLabel();

  if (!cameraTray.hidden) {
    switchCameraButton.disabled = true;
    statusText.textContent = "カメラ切替中";
    await openCamera();
    switchCameraButton.disabled = false;
  }
}

function captureImage() {
  const width = cameraPreview.videoWidth;
  const height = cameraPreview.videoHeight;
  if (!width || !height) return null;

  const maxSide = 1024;
  const scale = Math.min(1, maxSide / Math.max(width, height));
  cameraCanvas.width = Math.round(width * scale);
  cameraCanvas.height = Math.round(height * scale);

  const context = cameraCanvas.getContext("2d");
  context.drawImage(cameraPreview, 0, 0, cameraCanvas.width, cameraCanvas.height);
  return cameraCanvas.toDataURL("image/jpeg", 0.82);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  const image = pendingImage;

  input.value = "";
  setPendingImage(null);
  input.disabled = true;
  form.querySelector("button").disabled = true;
  cameraButton.disabled = true;

  try {
    await sendMessage(message, image);
  } catch (error) {
    addMessage("assistant", "通信で問題が起きました。設定を確認してください。");
    setFace("maid_08_komari_troubled.png");
    statusText.textContent = "通信エラー";
  } finally {
    input.disabled = false;
    form.querySelector("button").disabled = false;
    cameraButton.disabled = false;
    input.focus();
  }
});

cameraButton.addEventListener("click", () => {
  if (cameraStream) {
    closeCamera();
    return;
  }

  openCamera();
});

captureButton.addEventListener("click", async () => {
  const image = captureImage();
  if (!image) return;

  closeCamera();
  setPendingImage(image);
  input.focus();
});

switchCameraButton.addEventListener("click", switchCamera);
closeCameraButton.addEventListener("click", closeCamera);
clearPhotoButton.addEventListener("click", () => {
  setPendingImage(null);
  input.focus();
});
updateCameraModeLabel();

function handleRealtimeEvent(event) {
  if (event.type === "conversation.item.input_audio_transcription.completed" && event.transcript) {
    addMessage("user", event.transcript);
    return;
  }

  if (event.type === "response.output_text.delta" && event.delta) {
    realtimeAssistantDraft += event.delta;
    return;
  }

  if (event.type === "response.output_audio_transcript.delta" && event.delta) {
    realtimeAssistantDraft += event.delta;
    return;
  }

  if (event.type === "response.done") {
    const text = realtimeAssistantDraft.trim();
    if (text) {
      addMessage("assistant", text);
      setFaceFromText(text);
    }
    realtimeAssistantDraft = "";
    statusText.textContent = "音声で会話できます";
    return;
  }

  if (event.type === "error") {
    const message = event.error?.message || "Realtime APIでエラーが起きました。";
    addMessage("assistant", message);
    statusText.textContent = "音声エラー";
    setFace("maid_08_komari_troubled.png");
  }
}

function stopRealtimeChat() {
  if (realtimeChannel) {
    realtimeChannel.close();
    realtimeChannel = null;
  }
  if (realtimePeer) {
    realtimePeer.close();
    realtimePeer = null;
  }
  if (realtimeMicStream) {
    realtimeMicStream.getTracks().forEach((track) => track.stop());
    realtimeMicStream = null;
  }
  if (realtimeAudio) {
    realtimeAudio.srcObject = null;
    realtimeAudio.remove();
    realtimeAudio = null;
  }
  realtimeAssistantDraft = "";
  voiceButton.classList.remove("listening");
  voiceButton.title = "音声会話";
  statusText.textContent = "会話できます";
}

function readableRealtimeError(error) {
  const message = error?.message || "音声会話の接続に失敗しました。";
  if (message.includes("<!DOCTYPE html>") || message.includes("<html")) {
    const statusMatch = message.match(/HTTP\s+\d+/);
    return `OpenAI Realtime APIへの接続に失敗しました: ${statusMatch ? statusMatch[0] : "サーバーエラー"}。少し待ってもう一度試してください。`;
  }
  return message;
}

async function createRealtimeAnswer(offerSdp) {
  const tokenResponse = await fetch("/api/realtime/token");
  if (!tokenResponse.ok) {
    throw new Error(await tokenResponse.text());
  }

  const tokenData = await tokenResponse.json();
  const ephemeralKey = tokenData.value;
  const realtimeUrl = tokenData.realtime_url || "https://api.openai.com/v1/realtime/calls";
  if (!ephemeralKey) {
    throw new Error("Realtime APIの一時トークンを取得できませんでした。");
  }

  const sdpResponse = await fetch(realtimeUrl, {
    method: "POST",
    body: offerSdp,
    headers: {
      Authorization: `Bearer ${ephemeralKey}`,
      "Content-Type": "application/sdp",
    },
  });

  if (!sdpResponse.ok) {
    const detail = await sdpResponse.text();
    throw new Error(`OpenAI Realtime APIへの接続に失敗しました: HTTP ${sdpResponse.status} ${detail}`);
  }

  return sdpResponse.text();
}

async function startRealtimeChat() {
  if (!navigator.mediaDevices?.getUserMedia || !window.RTCPeerConnection) {
    addMessage("assistant", "このブラウザでは音声会話を使えません。");
    return;
  }

  try {
    statusText.textContent = "音声接続中";
    voiceButton.disabled = true;

    realtimePeer = new RTCPeerConnection();
    realtimeAudio = document.createElement("audio");
    realtimeAudio.autoplay = true;
    realtimeAudio.hidden = true;
    document.body.appendChild(realtimeAudio);
    realtimePeer.ontrack = (event) => {
      realtimeAudio.srcObject = event.streams[0];
    };

    realtimeMicStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    realtimeMicStream.getAudioTracks().forEach((track) => {
      realtimePeer.addTrack(track, realtimeMicStream);
    });

    realtimeChannel = realtimePeer.createDataChannel("oai-events");
    realtimeChannel.addEventListener("message", (event) => {
      try {
        handleRealtimeEvent(JSON.parse(event.data));
      } catch (error) {
        console.warn("Realtime event parse failed", error);
      }
    });

    const offer = await realtimePeer.createOffer();
    await realtimePeer.setLocalDescription(offer);

    const answerSdp = await createRealtimeAnswer(offer.sdp);

    await realtimePeer.setRemoteDescription({
      type: "answer",
      sdp: answerSdp,
    });

    voiceButton.classList.add("listening");
    voiceButton.title = "音声会話を終了";
    statusText.textContent = "音声で会話できます";
  } catch (error) {
    stopRealtimeChat();
    addMessage("assistant", readableRealtimeError(error));
    setFace("maid_08_komari_troubled.png");
    statusText.textContent = "音声エラー";
  } finally {
    voiceButton.disabled = false;
  }
}

voiceButton.addEventListener("click", () => {
  if (realtimePeer) {
    stopRealtimeChat();
    return;
  }

  startRealtimeChat();
});

window.addEventListener("beforeunload", stopRealtimeChat);

function setupVoiceInput() {
  voiceButton.title = "音声会話";
}

setupVoiceInput();
addMessage("assistant", "こんにちは。ブラウザから会話できます。");
