const API_BASE = window.ERR2TEXT_API_BASE || "/api/v1";
const POLL_INTERVAL_MS = 30_000;
const FINAL_STATUSES = new Set(["SUCCEEDED", "FAILED", "CANCELLED"]);

const state = {
  resolved: null,
  job: null,
  pollTimer: null,
  historyTimer: null,
  historyJobs: [],
  translations: null,
};

const $ = (selector) => document.querySelector(selector);

async function loadTranslations() {
  const response = await fetch("./assets/i18n/et.json");
  if (!response.ok) throw new Error("Translations could not be loaded");
  state.translations = await response.json();
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    element.textContent = translate(element.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
    element.placeholder = translate(element.dataset.i18nPlaceholder);
  });
}

function translate(key) {
  return state.translations?.[key] || key;
}

function setMessage(selector, message, isError = false) {
  const element = $(selector);
  element.textContent = message || "";
  element.classList.toggle("error", Boolean(message && isError));
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  let payload = null;
  try { payload = await response.json(); } catch (_) { /* empty response */ }
  if (!response.ok) {
    const detail = payload?.detail;
    const message = typeof detail === "string" ? detail : detail?.message || translate("errors.request");
    throw new Error(message);
  }
  return payload;
}

function formatLocalDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function renderMetadata(data) {
  $("#metadataTitle").textContent = data.title || "-";
  $("#metadataPublished").textContent = data.published_date || "-";
  $("#metadataDescription").textContent = data.description || "-";
  $("#metadataCard").classList.remove("hidden");
}

function renderMediaChoices(items) {
  const container = $("#mediaChoices");
  container.replaceChildren();
  items.forEach((item, index) => {
    const label = document.createElement("label");
    label.className = "media-choice";
    const radio = document.createElement("input");
    radio.type = "radio";
    radio.name = "media";
    radio.value = String(index);
    radio.checked = index === 0;
    const body = document.createElement("div");
    const title = document.createElement("div");
    title.className = "media-choice-title";
    title.textContent = item.title || translate("media.untitled");
    const meta = document.createElement("div");
    meta.className = "muted";
    meta.textContent = [item.media_type, item.duration_seconds ? `${item.duration_seconds}s` : null]
      .filter(Boolean).join(" · ");
    const assets = document.createElement("div");
    assets.className = "asset-list";
    (item.assets || []).forEach((asset) => {
      const badge = document.createElement("span");
      badge.className = "asset-badge";
      badge.textContent = asset.asset_type;
      assets.appendChild(badge);
    });
    body.append(title, meta, assets);
    label.append(radio, body);
    container.appendChild(label);
  });
  $("#mediaCard").classList.remove("hidden");
}

function statusLabel(status) {
  return translate(`status.${status}`) || status;
}

function renderJob(job) {
  state.job = job;
  $("#jobCard").classList.remove("hidden");
  $("#jobId").textContent = `#${job.id}`;
  const status = $("#jobStatus");
  status.textContent = statusLabel(job.status);
  status.classList.toggle("is-success", false);
  status.classList.toggle("is-pending", job.status === "SUCCEEDED");
  status.classList.toggle("is-error", ["FAILED", "CANCELLED"].includes(job.status));
  $("#jobSubmitted").textContent = formatLocalDate(job.submitted_at);
  $("#jobUpdated").textContent = formatLocalDate(job.resolved_at);
  const error = $("#jobError");
  error.textContent = job.error_message || "";
  error.classList.toggle("hidden", !job.error_message);
  $("#jobProgressNote").textContent = FINAL_STATUSES.has(job.status)
    ? statusLabel(job.status)
    : translate("job.polling");
}

function renderEvents(events) {
  const container = $("#eventList");
  container.replaceChildren();
  events.forEach((event) => {
    const row = document.createElement("div");
    row.className = "event";
    const head = document.createElement("div");
    head.className = "event-head";
    const type = document.createElement("span");
    type.className = "event-type";
    type.textContent = event.event_type;
    const time = document.createElement("span");
    time.className = "event-time";
    time.textContent = formatLocalDate(event.event_at);
    head.append(type, time);
    const detail = document.createElement("div");
    detail.className = "event-detail";
    detail.textContent = event.detail;
    row.append(head, detail);
    container.appendChild(row);
  });
}

function renderArtifacts(artifacts) {
  const container = $("#artifactList");
  container.replaceChildren();
  if (!artifacts.length) {
    container.classList.add("hidden");
    return;
  }
  container.appendChild(buildArtifactLinks(artifacts, state.job.id));
  container.classList.remove("hidden");
}

function buildArtifactLinks(artifacts, jobId) {
  const wrapper = document.createElement("div");
  const heading = document.createElement("h3");
  heading.textContent = translate("artifacts.title");
  wrapper.appendChild(heading);
  const primary = [];
  const seenPrimaryTypes = new Set();
  artifacts.filter((artifact) => ["MD", "VTT"].includes(artifact.artifact_type)).forEach((artifact) => {
    if (!seenPrimaryTypes.has(artifact.artifact_type)) {
      seenPrimaryTypes.add(artifact.artifact_type);
      primary.push(artifact);
    }
  });
  const technical = artifacts.filter((artifact) => !["MD", "VTT"].includes(artifact.artifact_type));
  const primaryList = document.createElement("ul");
  primary.forEach((artifact) => primaryList.appendChild(buildArtifactLink(artifact, jobId)));
  wrapper.appendChild(primaryList);
  if (technical.length) {
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = translate("artifacts.technical");
    const technicalList = document.createElement("ul");
    technical.forEach((artifact) => technicalList.appendChild(buildArtifactLink(artifact, jobId)));
    details.append(summary, technicalList);
    wrapper.appendChild(details);
  }
  return wrapper;
}

function buildArtifactLink(artifact, jobId) {
  const row = document.createElement("li");
  const link = document.createElement("a");
  link.href = `${API_BASE}/jobs/${jobId}/artifacts/${artifact.id}`;
  link.target = "_blank";
  link.rel = "noopener";
  if (["MD", "VTT"].includes(artifact.artifact_type)) {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      openArtifactViewer(link.href, artifact.artifact_type);
    });
  } else {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      window.open(link.href, "_blank", "noopener,noreferrer");
    });
  }
  link.textContent = artifact.artifact_type === "MD"
    ? translate("artifacts.transcript")
    : artifact.artifact_type === "VTT"
      ? translate("artifacts.vtt")
      : `${artifact.artifact_type} (${artifact.size_byte} B)`;
  row.appendChild(link);
  return row;
}

async function openArtifactViewer(url, artifactType) {
  const dialog = $("#artifactViewer");
  const title = $("#artifactViewerTitle");
  const message = $("#artifactViewerMessage");
  const content = $("#artifactViewerContent");
  const download = $("#artifactViewerDownload");
  download.dataset.url = url;
  download.dataset.artifactType = artifactType;
  title.textContent = artifactType === "VTT"
    ? translate("artifacts.vtt")
    : translate("artifacts.transcript");
  message.textContent = translate("artifacts.loading");
  content.textContent = "";
  dialog.showModal();
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const text = await response.text();
    if (artifactType === "MD") {
      content.classList.remove("is-vtt");
      content.innerHTML = renderMarkdown(text);
    } else {
      content.classList.add("is-vtt");
      content.textContent = text;
    }
    message.textContent = "";
  } catch (error) {
    message.textContent = error.message;
  }
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function renderInlineMarkdown(value) {
  return escapeHtml(value)
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>");
}

function renderMarkdown(markdown) {
  return markdown.split(/\r?\n/).map((line) => {
    if (!line.trim()) return "";
    if (line.startsWith("# ")) return `<h1>${renderInlineMarkdown(line.slice(2))}</h1>`;
    if (line.startsWith("> ")) return `<blockquote>${renderInlineMarkdown(line.slice(2))}</blockquote>`;
    const segment = line.match(/^\*\*([^*]+)\*\* \(\*([^*]+)\*\): (.*)$/);
    if (segment) {
      return `<p class="transcript-segment"><strong>${escapeHtml(segment[1])}</strong> <span class="transcript-time">${escapeHtml(segment[2])}</span><br>${renderInlineMarkdown(segment[3])}</p>`;
    }
    return `<p>${renderInlineMarkdown(line)}</p>`;
  }).join("");
}

$("#artifactViewerClose").addEventListener("click", () => $("#artifactViewer").close());
$("#artifactViewerDownload").addEventListener("click", async () => {
  const button = $("#artifactViewerDownload");
  try {
    const response = await fetch(button.dataset.url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const blob = await response.blob();
    const extension = button.dataset.artifactType === "VTT" ? "vtt" : "md";
    const objectUrl = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = button.dataset.artifactType === "VTT" ? "saate-subtiitrid.vtt" : "transkriptsioon.md";
    anchor.click();
    URL.revokeObjectURL(objectUrl);
  } catch (error) {
    $("#artifactViewerMessage").textContent = error.message;
  }
});
$("#artifactViewer").addEventListener("click", (event) => {
  if (event.target === $("#artifactViewer")) $("#artifactViewer").close();
});

function renderHistory() {
  const container = $("#historyList");
  container.replaceChildren();
  if (!state.historyJobs.length) {
    const empty = document.createElement("div");
    empty.className = "history-empty";
    empty.textContent = translate("history.empty");
    container.appendChild(empty);
    return;
  }
  state.historyJobs.forEach((job) => {
    const item = document.createElement("article");
    item.className = "history-item";
    const head = document.createElement("div");
    head.className = "history-item-head";
    const title = document.createElement("div");
    title.className = "history-title";
    title.textContent = job.title || job.submitted_url;
    const status = document.createElement("span");
    status.className = "status-badge";
    status.textContent = statusLabel(job.status);
    status.classList.toggle("is-success", false);
    status.classList.toggle("is-pending", job.status === "SUCCEEDED");
    status.classList.toggle("is-error", ["FAILED", "CANCELLED"].includes(job.status));
    head.append(title, status);
    const meta = document.createElement("div");
    meta.className = "history-meta";
    const id = document.createElement("span");
    id.textContent = `#${job.id}`;
    const submitted = document.createElement("span");
    submitted.textContent = `${translate("history.submitted")}: ${formatLocalDate(job.submitted_at)}`;
    meta.append(id, submitted);
    if (job.error_message) {
      const error = document.createElement("span");
      error.textContent = job.error_message;
      meta.appendChild(error);
    }
    item.append(head, meta);
    if (job.status === "SUCCEEDED") {
      const actions = document.createElement("div");
      actions.className = "history-actions";
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary-button";
      button.textContent = translate("history.results");
      button.addEventListener("click", () => loadHistoryArtifacts(job, item));
      actions.appendChild(button);
      item.appendChild(actions);
    }
    container.appendChild(item);
  });
}

async function loadHistoryArtifacts(job, parent) {
  const existing = parent.querySelector(".history-artifacts");
  if (existing) { existing.remove(); return; }
  const box = document.createElement("div");
  box.className = "history-artifacts";
  box.textContent = translate("history.loading_results");
  parent.appendChild(box);
  try {
    const artifacts = await request(`/jobs/${job.id}/artifacts`);
    box.replaceChildren();
    box.appendChild(buildArtifactLinks(artifacts, job.id));
  } catch (error) {
    box.textContent = error.message;
    box.classList.add("error");
  }
}

async function loadHistory() {
  const jobs = await request("/jobs");
  state.historyJobs = jobs;
  renderHistory();
  scheduleHistoryPolling();
}

async function refreshActiveHistory() {
  const active = state.historyJobs.filter((job) => !FINAL_STATUSES.has(job.status));
  if (!active.length) return scheduleHistoryPolling();
  const refreshed = await Promise.all(active.map((job) => request(`/jobs/${job.id}`)));
  const byId = new Map(refreshed.map((job) => [job.id, job]));
  state.historyJobs = state.historyJobs.map((job) => byId.get(job.id) || job);
  renderHistory();
  scheduleHistoryPolling();
}

function scheduleHistoryPolling() {
  if (state.historyTimer) window.clearTimeout(state.historyTimer);
  if (!state.historyJobs.some((job) => !FINAL_STATUSES.has(job.status))) return;
  state.historyTimer = window.setTimeout(() => {
    refreshActiveHistory().catch((error) => setMessage("#historyMessage", error.message, true));
  }, POLL_INTERVAL_MS);
}

async function refreshJob() {
  if (!state.job) return;
  const [job, events] = await Promise.all([
    request(`/jobs/${state.job.id}`),
    request(`/jobs/${state.job.id}/events`),
  ]);
  renderJob(job);
  renderEvents(events);
  if (FINAL_STATUSES.has(job.status)) {
    stopPolling();
    if (job.status === "SUCCEEDED") renderArtifacts(await request(`/jobs/${job.id}/artifacts`));
  }
}

function startPolling() {
  stopPolling();
  state.pollTimer = window.setInterval(() => {
    refreshJob().catch((error) => setMessage("#jobMessage", error.message, true));
  }, POLL_INTERVAL_MS);
}

function stopPolling() {
  if (state.pollTimer) window.clearInterval(state.pollTimer);
  state.pollTimer = null;
}

$("#resolveForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = $("#resolveButton");
  const url = $("#sourceUrl").value.trim();
  if (!url) return setMessage("#resolveMessage", translate("errors.url_required"), true);
  button.disabled = true;
  setMessage("#resolveMessage", translate("source.resolving"));
  $("#metadataCard").classList.add("hidden");
  $("#mediaCard").classList.add("hidden");
  try {
    state.resolved = await request("/resolve", { method: "POST", body: JSON.stringify({ url }) });
    renderMetadata(state.resolved);
    renderMediaChoices(state.resolved.media_items || []);
    setMessage("#resolveMessage", translate("source.resolved"));
  } catch (error) {
    setMessage("#resolveMessage", error.message, true);
  } finally {
    button.disabled = false;
  }
});

$("#jobForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const selected = $("input[name=media]:checked");
  if (!selected || !state.resolved) return;
  const button = $("#createJobButton");
  button.disabled = true;
  setMessage("#jobMessage", translate("media.creating"));
  try {
    const item = state.resolved.media_items[Number(selected.value)];
    const job = await request("/jobs", {
      method: "POST",
      body: JSON.stringify({
        source_url: state.resolved.source_url,
        confirm: true,
        selected_media: item,
        title: state.resolved.title,
        description: state.resolved.description,
        published_date: state.resolved.published_date,
      }),
    });
    renderJob(job);
    await refreshJob();
    if (!FINAL_STATUSES.has(state.job.status)) startPolling();
    await loadHistory();
    setMessage("#jobMessage", translate("media.created"));
  } catch (error) {
    setMessage("#jobMessage", error.message, true);
  } finally {
    button.disabled = false;
  }
});

$("#historyRefreshButton").addEventListener("click", () => {
  loadHistory().catch((error) => setMessage("#historyMessage", error.message, true));
});

loadTranslations()
  .then(() => loadHistory())
  .catch((error) => setMessage("#historyMessage", error.message, true));
