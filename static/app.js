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
let recognition = null;
let cameraStream = null;
let cameraFacingMode = "environment";
let pendingImage = null;

const faceImageBasePath = "../maid_faces/";

function addMessage(role, content, image = null) {
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

  messages.appendChild(bubble);
  messages.scrollTop = messages.scrollHeight;
}

function setFace(image) {
  activeImage = image || "maid_05_tsujo_normal.png";
  face.src = `${faceImageBasePath}${encodeURIComponent(activeImage)}`;
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
  statusText.textContent = "OpenClawに送信中";

  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, image }),
  });

  const data = await response.json();
  addMessage("assistant", data.reply);
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

function setupVoiceInput() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    voiceButton.disabled = true;
    voiceButton.title = "このブラウザは音声入力に未対応です";
    return;
  }

  recognition = new SpeechRecognition();
  recognition.lang = "ja-JP";
  recognition.interimResults = false;
  recognition.continuous = false;

  recognition.addEventListener("result", (event) => {
    const transcript = event.results[0][0].transcript;
    input.value = transcript;
    form.requestSubmit();
  });

  recognition.addEventListener("end", () => {
    voiceButton.classList.remove("listening");
  });

  voiceButton.addEventListener("click", () => {
    voiceButton.classList.add("listening");
    recognition.start();
  });
}

setupVoiceInput();
addMessage("assistant", "こんにちは。ブラウザから会話できます。");
