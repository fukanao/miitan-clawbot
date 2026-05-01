const face = document.querySelector("#face");
const form = document.querySelector("#chatForm");
const input = document.querySelector("#messageInput");
const messages = document.querySelector("#messages");
const statusText = document.querySelector("#status");
const voiceButton = document.querySelector("#voiceButton");

const history = [];
let activeImage = "maid_05_tsujo_normal.png";
let recognition = null;

function addMessage(role, content) {
  const bubble = document.createElement("div");
  bubble.className = `message ${role}`;
  bubble.textContent = content;
  messages.appendChild(bubble);
  messages.scrollTop = messages.scrollHeight;
}

function setFace(image) {
  activeImage = image || "maid_05_tsujo_normal.png";
  face.src = `/maid_faces/${encodeURIComponent(activeImage)}`;
}

async function sendMessage(message) {
  addMessage("user", message);
  history.push({ role: "user", content: message });
  statusText.textContent = "OpenClawに送信中";

  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });

  const data = await response.json();
  addMessage("assistant", data.reply);
  history.push({ role: "assistant", content: data.reply });
  setFace(data.image);
  statusText.textContent = "会話できます";

  if ("speechSynthesis" in window && data.reply) {
    const utterance = new SpeechSynthesisUtterance(data.reply);
    utterance.lang = "ja-JP";
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) return;

  input.value = "";
  input.disabled = true;
  form.querySelector("button").disabled = true;

  try {
    await sendMessage(message);
  } catch (error) {
    addMessage("assistant", "通信で問題が起きました。設定を確認してください。");
    setFace("maid_08_komari_troubled.png");
    statusText.textContent = "通信エラー";
  } finally {
    input.disabled = false;
    form.querySelector("button").disabled = false;
    input.focus();
  }
});

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
