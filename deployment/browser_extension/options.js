async function load() {
  const { endpoint = "http://localhost:8080", jurisdiction = "", language = "en" } =
    await chrome.storage.sync.get(["endpoint", "jurisdiction", "language"]);
  document.getElementById("endpoint").value = endpoint;
  document.getElementById("jurisdiction").value = jurisdiction;
  document.getElementById("language").value = language;
}

async function save() {
  await chrome.storage.sync.set({
    endpoint: document.getElementById("endpoint").value.trim() || "http://localhost:8080",
    jurisdiction: document.getElementById("jurisdiction").value,
    language: document.getElementById("language").value,
  });
  const saved = document.getElementById("saved");
  saved.classList.add("visible");
  setTimeout(() => saved.classList.remove("visible"), 2000);
}

document.getElementById("save").addEventListener("click", save);
load();
