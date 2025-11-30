function isMobile() {
  return /Android|iPhone|iPad|iPod|IEMobile|Mobile|Opera Mini/i.test(navigator.userAgent);
}

function applyMobileOnlySettings() {
  if (!isMobile()) {
    $("prevBtn").style.display = "none";
    $("nextBtn").style.display = "none";
  }
}
