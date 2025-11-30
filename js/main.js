document.addEventListener("DOMContentLoaded", () => {
  
  // Deteksi mobile → sembunyikan tombol desktop
  applyMobileOnlySettings();

  // Muat chat dari URL
  initChatsFromURL();

  // Tombol tambah chat
  setupAddChat();

  // Tombol prev-next
  setupNavigation();

});

