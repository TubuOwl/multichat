function setupAddChat() {
  $("addBtn").onclick = () => {
    const input = $("chatInput");
    const chatname = cleanName(input.value.trim());

    if (!chatname) {
      alert("Masukkan nama room Chatango.");
      return;
    }

    const chatArea = $("chatArea");
    const exists = Array.from(chatArea.querySelectorAll("iframe"))
      .some(frame => frame.src.includes(chatname));

    if (exists) return alert("Chatroom sudah ada.");

    chatArea.appendChild(createChatElement(chatname));
    input.value = "";
  };
}
