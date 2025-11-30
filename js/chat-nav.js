function setupNavigation() {

  $("nextBtn").onclick = () => {
    const area = $("chatArea");
    area.scrollBy({
      left: area.clientWidth,
      behavior: "smooth"
    });
  };

  $("prevBtn").onclick = () => {
    const area = $("chatArea");
    area.scrollBy({
      left: -area.clientWidth,
      behavior: "smooth"
    });
  };

}
