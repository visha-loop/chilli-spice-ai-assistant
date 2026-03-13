const loginPanel = document.getElementById("loginPanel");
const dashboard = document.getElementById("dashboard");
const adminForm = document.getElementById("adminForm");
const adminUsername = document.getElementById("adminUsername");
const adminPassword = document.getElementById("adminPassword");
const adminStatus = document.getElementById("adminStatus");
const userBadge = document.getElementById("userBadge");
const summaryGrid = document.getElementById("summaryGrid");
const filterDate = document.getElementById("filterDate");
const filterStatus = document.getElementById("filterStatus");
const filterQuery = document.getElementById("filterQuery");
const applyFiltersBtn = document.getElementById("applyFiltersBtn");
const reservationTable = document.getElementById("reservationTable");
const tableMeta = document.getElementById("tableMeta");

const isLocalHost = ["127.0.0.1", "localhost"].includes(window.location.hostname);
const apiBase =
  isLocalHost && window.location.port === "8000"
    ? ""
    : isLocalHost
      ? window.localStorage.getItem("chilli-spice-api-base") || "http://127.0.0.1:8000"
      : "";

let adminToken = window.localStorage.getItem("chilli-spice-admin-token") || "";

function setStatus(message, isError = false) {
  adminStatus.textContent = message;
  adminStatus.dataset.error = isError ? "true" : "false";
}

function renderSummary(summary) {
  const items = [
    ["Total Bookings", summary.total ?? 0],
    ["Today's Bookings", summary.today ?? 0],
    ["New Requests", summary.new ?? 0],
    ["Confirmed", summary.confirmed ?? 0],
    ["Total Covers", summary.covers ?? 0],
  ];

  summaryGrid.innerHTML = items
    .map(
      ([label, value]) => `
        <article class="summary-card">
          <span>${value}</span>
          <p>${label}</p>
        </article>
      `
    )
    .join("");
}

function renderStatusOptions(statuses) {
  filterStatus.innerHTML =
    '<option value="all">All statuses</option>' +
    statuses.map((status) => `<option value="${status}">${status}</option>`).join("");
}

async function updateReservation(reservationId, payload) {
  const response = await fetch(`${apiBase}/api/admin/reservations/${reservationId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      "x-admin-token": adminToken,
    },
    body: JSON.stringify(payload),
  });
  const result = await response.json();
  if (!response.ok) {
    setStatus(result.detail || "Could not update reservation.", true);
    return;
  }
  await loadReservations();
}

async function deleteReservation(reservationId) {
  const confirmed = window.confirm(`Delete reservation #${reservationId}?`);
  if (!confirmed) {
    return;
  }

  const response = await fetch(`${apiBase}/api/admin/reservations/${reservationId}`, {
    method: "DELETE",
    headers: { "x-admin-token": adminToken },
  });
  const result = await response.json();
  if (!response.ok) {
    setStatus(result.detail || "Could not delete reservation.", true);
    return;
  }
  setStatus(result.message, false);
  await loadReservations();
}

function reservationRow(item) {
  const statusOptions = ["new", "confirmed", "seated", "completed", "cancelled"]
    .map((status) => `<option value="${status}" ${item.status === status ? "selected" : ""}>${status}</option>`)
    .join("");

  return `
    <tr>
      <td>#${item.id}</td>
      <td>
        <strong>${item.name}</strong>
        <span>${item.phone}</span>
      </td>
      <td>${item.date}<span>${item.time}</span></td>
      <td>${item.guests}</td>
      <td>${item.special_requests || "-"}</td>
      <td>
        <select class="row-status" data-id="${item.id}">
          ${statusOptions}
        </select>
      </td>
      <td>
        <textarea class="row-note" data-id="${item.id}" rows="2" placeholder="Internal notes...">${item.internal_notes || ""}</textarea>
        <button class="save-note-btn" type="button" data-id="${item.id}">Save</button>
        <button class="delete-row-btn" type="button" data-id="${item.id}">Delete</button>
      </td>
    </tr>
  `;
}

function bindTableActions() {
  document.querySelectorAll(".row-status").forEach((select) => {
    select.addEventListener("change", async () => {
      await updateReservation(Number(select.dataset.id), { status: select.value });
    });
  });

  document.querySelectorAll(".save-note-btn").forEach((button) => {
    button.addEventListener("click", async () => {
      const id = Number(button.dataset.id);
      const note = document.querySelector(`.row-note[data-id="${id}"]`).value;
      await updateReservation(id, { internal_notes: note });
    });
  });

  document.querySelectorAll(".delete-row-btn").forEach((button) => {
    button.addEventListener("click", async () => {
      await deleteReservation(Number(button.dataset.id));
    });
  });
}

function renderReservations(reservations) {
  if (!reservations.length) {
    reservationTable.innerHTML = '<div class="empty-state">No reservations match the current filters.</div>';
    tableMeta.textContent = "0 results";
    return;
  }

  tableMeta.textContent = `${reservations.length} reservations`;
  reservationTable.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Guest</th>
          <th>Schedule</th>
          <th>Guests</th>
          <th>Requests</th>
          <th>Status</th>
          <th>Internal Notes</th>
        </tr>
      </thead>
      <tbody>
        ${reservations.map(reservationRow).join("")}
      </tbody>
    </table>
  `;
  bindTableActions();
}

async function loadReservations() {
  const params = new URLSearchParams();
  if (filterDate.value) {
    params.set("date", filterDate.value);
  }
  if (filterStatus.value && filterStatus.value !== "all") {
    params.set("status", filterStatus.value);
  }
  if (filterQuery.value.trim()) {
    params.set("q", filterQuery.value.trim());
  }

  const response = await fetch(`${apiBase}/api/admin/reservations?${params.toString()}`, {
    headers: { "x-admin-token": adminToken },
  });
  const payload = await response.json();

  if (!response.ok) {
    setStatus(payload.detail || "Could not load reservations.", true);
    return;
  }

  renderSummary(payload.summary);
  renderStatusOptions(payload.statuses);
  if (params.get("status")) {
    filterStatus.value = params.get("status");
  }
  renderReservations(payload.reservations);
}

adminForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const response = await fetch(`${apiBase}/api/admin/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username: adminUsername.value.trim(),
      password: adminPassword.value,
    }),
  });
  const payload = await response.json();

  if (!response.ok) {
    setStatus(payload.detail || "Login failed.", true);
    return;
  }

  adminToken = payload.token;
  window.localStorage.setItem("chilli-spice-admin-token", adminToken);
  userBadge.textContent = payload.user.username;
  loginPanel.hidden = true;
  dashboard.hidden = false;
  renderSummary(payload.summary);
  await loadReservations();
});

applyFiltersBtn.addEventListener("click", loadReservations);

if (adminToken) {
  loginPanel.hidden = true;
  dashboard.hidden = false;
  loadReservations();
}
