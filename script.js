function createChatElement(chatname) {
  const box = document.createElement("div");
  box.className = "chat-box";

  const close = document.createElement("button");
  close.className = "close-btn";
  close.innerHTML = "×";
  close.onclick = () => box.remove();
  box.appendChild(close);

  const container = document.createElement("div");
  container.className = "chat-container";

  const iframe = document.createElement("iframe");
  iframe.src = `https://${chatname}.chatango.com/?m`;
  iframe.loading = "lazy";
  iframe.setAttribute("allowfullscreen", "true");

  container.appendChild(iframe);
  box.appendChild(container);

  return box;
}

// LOAD ROOM FROM URL
function initChats() {
  const url = window.location.href;
  const rawData = url.split("?");
  if (rawData.length < 2) return;

  const rooms = rawData[1].split(",");
  rooms.forEach(room => {
    const chatname = room.replace(/[^a-zA-Z0-9-]/g, "");
    if (chatname.length > 0) {
      const chatEl = createChatElement(chatname);
      document.getElementById("chatArea").appendChild(chatEl);
    }
  });
}
window.onload = initChats;

// ADD CHAT MANUAL
function addChat() {
  const input = document.getElementById("chatInput");
  const chatname = input.value.trim();
  if (!chatname) return alert("Masukkan nama room Chatango.");

  const chatArea = document.getElementById("chatArea");
  const exists = Array.from(chatArea.querySelectorAll("iframe"))
    .some(iframe => iframe.src.includes(chatname));

  if (exists) return alert("Chatroom sudah ada.");

  chatArea.appendChild(createChatElement(chatname));
  input.value = "";
}

// GET CURRENT SLIDE INDEX
function getCurrentIndex() {
  const area = document.getElementById("chatArea");
  const boxes = area.querySelectorAll(".chat-box");

  let nearestIndex = 0;
  let minDistance = Infinity;

  boxes.forEach((box, i) => {
    const offset = box.offsetLeft;
    const distance = Math.abs(area.scrollLeft - offset);
    if (distance < minDistance) {
      minDistance = distance;
      nearestIndex = i;
    }
  });

  return nearestIndex;
}

// NEXT (LOOP)
function nextChat() {
  const area = document.getElementById("chatArea");
  const boxes = area.querySelectorAll(".chat-box");

  let index = getCurrentIndex() + 1;
  if (index >= boxes.length) index = 0;

  area.scrollTo({
    left: boxes[index].offsetLeft,
    behavior: "smooth"
  });
}

// PREV (LOOP)
function prevChat() {
  const area = document.getElementById("chatArea");
  const boxes = area.querySelectorAll(".chat-box");

  let index = getCurrentIndex() - 1;
  if (index < 0) index = boxes.length - 1;

  area.scrollTo({
    left: boxes[index].offsetLeft,
    behavior: "smooth"
  });
}

// MOBILE CHECK — hide buttons on desktop
function isMobile() {
  return /Android|iPhone|iPad|iPod|Opera Mini|IEMobile|Mobile/i.test(navigator.userAgent);
}

document.addEventListener("DOMContentLoaded", () => {
  if (!isMobile()) {
    document.getElementById("prevBtn").style.display = "none";
    document.getElementById("nextBtn").style.display = "none";
  }
});
