function $(id) {
  return document.getElementById(id);
}

function cleanName(text) {
  return text.replace(/[^a-zA-Z0-9-]/g, "");
}
