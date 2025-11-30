function createChatElement(chatname) {
  const box = document.createElement("div");
  box.className = "chat-box";

  const closeBtn = document.createElement("button");
  closeBtn.className = "close-btn";
  closeBtn.textContent = "×";
  closeBtn.onclick = () => box.remove();
  box.appendChild(closeBtn);

  const container = document.createElement("div");
  container.className = "chat-container";

  const iframe = document.createElement("iframe");
  iframe.src = `https://${chatname}.chatango.com/?m`;
  iframe.loading = "lazy";
  iframe.allowFullscreen = true;

  container.appendChild(iframe);
  box.appendChild(container);

  return box;
}
