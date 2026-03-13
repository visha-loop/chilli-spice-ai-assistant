const chatMessages = document.getElementById("chatMessages");
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const reservationForm = document.getElementById("reservationForm");
const reservationStatus = document.getElementById("reservationStatus");
const quickPrompts = document.getElementById("quickPrompts");
const menuGrid = document.getElementById("menuGrid");
const showPopularBtn = document.getElementById("showPopularBtn");
const menuPrevBtn = document.getElementById("menuPrevBtn");
const menuNextBtn = document.getElementById("menuNextBtn");
const entryCards = document.querySelectorAll(".entry-card");

let sessionId = window.localStorage.getItem("chilli-spice-session") || null;
let latestChips = [];
const isLocalHost = ["127.0.0.1", "localhost"].includes(window.location.hostname);
const apiBase =
  isLocalHost && window.location.port === "8000"
    ? ""
    : isLocalHost
      ? window.localStorage.getItem("chilli-spice-api-base") || "http://127.0.0.1:8000"
      : "";

function persistSession(id) {
  sessionId = id;
  if (id) {
    window.localStorage.setItem("chilli-spice-session", id);
  }
}

function addMessage(role, text) {
  const bubble = document.createElement("article");
  bubble.className = `message ${role}`;

  const label = document.createElement("span");
  label.className = "message-label";
  label.textContent = role === "assistant" ? "Chilli Spice" : "You";

  const content = document.createElement("p");
  content.textContent = text;

  bubble.append(label, content);
  chatMessages.appendChild(bubble);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function renderQuickPrompts(chips) {
  latestChips = chips || [];
  quickPrompts.innerHTML = "";
  latestChips.forEach((chip) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "prompt-chip";
    button.textContent = chip;
    button.addEventListener("click", () => sendChat(chip));
    quickPrompts.appendChild(button);
  });
}

function renderMenuCards(items) {
  menuGrid.innerHTML = "";
  items.forEach((item, index) => {
    const card = document.createElement("article");
    card.className = "menu-card";
    card.innerHTML = `
      <div class="menu-visual">
        <img src="${item.image}" alt="${item.name}" loading="lazy" />
      </div>
      <div class="menu-card-top">
        <span class="menu-category">${item.cuisine} · ${item.category}</span>
        <span class="menu-price">INR ${item.price}</span>
      </div>
      <h3>${item.name}</h3>
      <p>${item.description}</p>
      <div class="menu-meta">
        <span>${item.spice_level}</span>
        <span>${item.best_for}</span>
      </div>
      <div class="menu-order">${String(index + 1).padStart(2, "0")}</div>
    `;
    card.addEventListener("click", () => sendChat(`Tell me about ${item.name}`));
    menuGrid.appendChild(card);
  });
}

async function loadMenu() {
  const response = await fetch(`${apiBase}/api/menu`);
  const payload = await response.json();
  const featured = payload.menu.filter(
    (item) => item.tags.includes("popular") || ["Indian", "Italian", "Chinese"].includes(item.cuisine)
  );
  renderMenuCards(featured.length ? featured : payload.menu);
}

async function sendChat(message) {
  addMessage("user", message);
  chatInput.value = "";

  const response = await fetch(`${apiBase}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });

  const payload = await response.json();
  persistSession(payload.session_id);
  addMessage("assistant", payload.answer);
  renderQuickPrompts(payload.chips);
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = chatInput.value.trim();
  if (!message) {
    return;
  }
  await sendChat(message);
});

showPopularBtn.addEventListener("click", () => {
  sendChat("What are your most popular dishes?");
});

menuPrevBtn.addEventListener("click", () => {
  menuGrid.scrollBy({ left: -380, behavior: "smooth" });
});

menuNextBtn.addEventListener("click", () => {
  menuGrid.scrollBy({ left: 380, behavior: "smooth" });
});

entryCards.forEach((card) => {
  card.addEventListener("click", () => {
    const targetId = card.dataset.target;
    const target = document.getElementById(targetId);
    if (!target) {
      return;
    }
    target.scrollIntoView({ behavior: "smooth", block: "start" });
    if (targetId === "chatSection") {
      chatInput.focus();
    }
  });
});

reservationForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const formData = new FormData(reservationForm);
  const payload = Object.fromEntries(formData.entries());
  payload.guests = Number(payload.guests);

  const response = await fetch(`${apiBase}/api/reservations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const result = await response.json();
  if (!response.ok) {
    reservationStatus.textContent = result.detail || "Could not save reservation.";
    return;
  }

  reservationStatus.textContent = result.message;
  reservationForm.reset();
});

addMessage(
  "assistant",
  "Good evening. I can help you discover the menu, narrow dishes by preference, and reserve a table without leaving the chat."
);
renderQuickPrompts([
  "Show authentic Indian dishes",
  "Recommend Italian pasta",
  "Show spicy Chinese options",
]);
loadMenu();
