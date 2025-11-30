function initChatsFromURL() {
  const url = window.location.href;
  const parts = url.split("?");

  if (parts.length < 2) return;

  const rooms = parts[1].split(",");
  rooms.forEach(room => {
    const name = cleanName(room);
    if (name.length > 0) {
      $("chatArea").appendChild(createChatElement(name));
    }
  });
}
