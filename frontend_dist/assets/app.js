const API_BASE = window.ERR2TEXT_API_BASE || "/api/v1";
const POLL_INTERVAL_MS = 30_000;
const STOP_POLL_STATUSES = new Set(["WAITING_FOR_PARTICIPANTS", "IN_REVIEW", "FINISHED", "CANCELLED"]);
const PROCESSING_STATUSES = new Set(["DOWNLOADING", "DIARIZING", "MATERIALIZING_AUTOMATIC_DRAFT", "WAITING_FOR_RESULT"]);

const state = {
  resolved: null,
  job: null,
  pollTimer: null,
  historyTimer: null,
  historyJobs: [],
  queueStatus: null,
  openHistoryArtifacts: new Set(),
  staleHistoryJobIds: new Set(),
  staleJobStatus: false,
  translations: null,
};

const $ = (selector) => document.querySelector(selector);

async function loadTranslations() {
  const response = await fetch("./assets/i18n/et.json?v=2");
  if (!response.ok) throw new Error("Translations could not be loaded");
  state.translations = await response.json();
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    element.textContent = translate(element.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
    element.placeholder = translate(element.dataset.i18nPlaceholder);
  });
  document.querySelectorAll("[data-i18n-aria-label]").forEach((element) => {
    element.setAttribute("aria-label", translate(element.dataset.i18nAriaLabel));
  });
  document.querySelectorAll("[data-i18n-title]").forEach((element) => {
    element.title = translate(element.dataset.i18nTitle);
  });
}

function translate(key) {
  return state.translations?.[key] || key;
}

function userError(error) {
  return state.translations?.[`errors.${error.code}`] || error.message;
}

function showErrorOverlay(message) {
  $("#errorViewerMessage").textContent = message;
  $("#errorViewer").showModal();
}

function setMessage(selector, message, isError = false) {
  const element = $(selector);
  element.textContent = message || "";
  element.classList.toggle("error", Boolean(message && isError));
}

function setResolveLocked(locked) {
  $("#sourceUrl").disabled = locked;
  $("#clearUrlButton").disabled = locked;
  $("#resolveButton").disabled = locked;
}

function resetResolveFlow() {
  state.resolved = null;
  $("#sourceUrl").value = "";
  $("#metadataCard").classList.add("hidden");
  $("#mediaCard").classList.add("hidden");
  $("#mediaChoices").replaceChildren();
  setMessage("#resolveMessage", "");
  setMessage("#jobMessage", "");
  setResolveLocked(false);
  $("#sourceUrl").focus();
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    });
  } catch (_) {
    throw new Error(translate("errors.connection"));
  }
  let payload = null;
  try { payload = await response.json(); } catch (_) { /* empty response */ }
  if (!response.ok) {
    const detail = payload?.detail;
    const message = typeof detail === "string" ? detail : detail?.message || translate("errors.request");
    const error = new Error(message);
    error.code = detail?.error;
    throw error;
  }
  return payload;
}

function formatLocalDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const pad = (part) => String(part).padStart(2, "0");
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())} ${pad(date.getDate())}.${pad(date.getMonth() + 1)}.${date.getFullYear()}`;
}

function formatLocalDateOnly(value) {
  if (!value) return "-";
  if (/^\d{8}$/.test(String(value))) {
    const text = String(value);
    return `${text.slice(6, 8)}.${text.slice(4, 6)}.${text.slice(0, 4)}`;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const pad = (part) => String(part).padStart(2, "0");
  return `${pad(date.getDate())}.${pad(date.getMonth() + 1)}.${date.getFullYear()}`;
}

function renderMetadata(data) {
  $("#metadataTitle").textContent = data.title || "-";
  $("#metadataPublished").textContent = formatLocalDateOnly(data.published_date);
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

function runResultLabel(status) {
  return status ? (translate(`run.${status}`) || status) : "";
}

function renderJob(job) {
  state.job = job;
  state.staleJobStatus = false;
  $("#jobCard").classList.remove("hidden");
  $("#jobId").textContent = `#${job.id}`;
  const status = $("#jobStatus");
  status.textContent = statusLabel(job.status);
  status.classList.toggle("is-success", false);
  status.classList.toggle("is-pending", ["WAITING_FOR_PARTICIPANTS", "IN_REVIEW"].includes(job.status));
  status.classList.toggle("is-success", job.status === "FINISHED");
  status.classList.toggle("is-error", job.status === "CANCELLED");
  status.classList.toggle("is-processing", PROCESSING_STATUSES.has(job.status));
  status.classList.toggle("is-stale", state.staleJobStatus);
  $("#jobSubmitted").textContent = formatLocalDate(job.submitted_at);
  $("#jobUpdated").textContent = formatLocalDate(job.resolved_at);
  const error = $("#jobError");
  error.textContent = job.error_message || "";
  error.classList.toggle("hidden", !job.error_message);
  $("#jobProgressNote").textContent = STOP_POLL_STATUSES.has(job.status)
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

$("#errorViewerOk").addEventListener("click", () => $("#errorViewer").close());
$("#jobInfoClose").addEventListener("click", () => $("#jobInfoViewer").close());
$("#jobHistoryClose").addEventListener("click", () => $("#jobHistoryViewer").close());

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
  const historyCard = $("#historyCard");
  container.replaceChildren();
  if (!state.historyJobs.length) {
    historyCard.classList.add("hidden");
    return;
  }
  historyCard.classList.remove("hidden");
  renderDiarizationNotice();
  state.historyJobs.forEach((job) => {
    const item = document.createElement("article");
    item.className = "history-item";
    item.dataset.jobId = String(job.id);
    const head = document.createElement("div");
    head.className = "history-item-head";
    const title = document.createElement("div");
    title.className = "history-title";
    title.textContent = job.title || job.submitted_url;
    const status = document.createElement("span");
    status.className = "status-badge";
    status.textContent = statusLabel(job.status);
    status.classList.toggle("is-success", false);
    status.classList.toggle("is-pending", ["WAITING_FOR_PARTICIPANTS", "IN_REVIEW"].includes(job.status));
    status.classList.toggle("is-success", job.status === "FINISHED");
    status.classList.toggle("is-error", job.status === "CANCELLED");
    status.classList.toggle("is-processing", PROCESSING_STATUSES.has(job.status));
    status.classList.toggle("is-stale", state.staleHistoryJobIds.has(job.id));
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
    const actions = document.createElement("div");
    actions.className = "history-actions";
    const infoButton = document.createElement("button");
    infoButton.type = "button";
    infoButton.className = "secondary-button";
    infoButton.textContent = translate("history.info");
    infoButton.addEventListener("click", () => showJobInfo(job.id));
    actions.appendChild(infoButton);
    const historyButton = document.createElement("button");
    historyButton.type = "button";
    historyButton.className = "secondary-button";
    historyButton.textContent = translate("history.processing");
    historyButton.addEventListener("click", () => showJobHistory(job.id));
    actions.appendChild(historyButton);
    if (["WAITING_FOR_PARTICIPANTS", "IN_REVIEW", "FINISHED"].includes(job.status)) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "results-button";
      button.textContent = translate("history.results");
      button.addEventListener("click", () => loadHistoryArtifacts(job, item));
      actions.appendChild(button);
    }
    item.appendChild(actions);
    container.appendChild(item);
    if (["WAITING_FOR_PARTICIPANTS", "IN_REVIEW", "FINISHED"].includes(job.status) && state.openHistoryArtifacts.has(job.id)) {
      loadHistoryArtifacts(job, item);
    }
  });
}

function renderDiarizationNotice() {
  const notice = $("#diarizationNotice");
  const queue = state.queueStatus;
  if (!queue || !state.historyJobs.length) {
    notice.classList.add("hidden");
    notice.replaceChildren();
    return;
  }
  const running = Number(queue.running_diarizations) || 0;
  const maximum = Number(queue.max_concurrent_diarizations) || 1;
  const firstLine = document.createElement("div");
  firstLine.append(document.createTextNode(translate("history.diarization_running")));
  const runningValue = document.createElement("strong");
  runningValue.textContent = String(running);
  firstLine.append(runningValue, document.createTextNode(translate("history.diarization_limit")));
  const maximumValue = document.createElement("strong");
  maximumValue.textContent = String(maximum);
  firstLine.append(maximumValue, document.createTextNode(")."));
  notice.replaceChildren(firstLine);
  if (running === 1) {
    const secondLine = document.createElement("div");
    secondLine.textContent = translate("history.diarization_queue");
    notice.appendChild(secondLine);
  }
  notice.classList.remove("hidden");
}

function appendInfoRow(container, label, value) {
  if (value === null || value === undefined || value === "") return;
  const row = document.createElement("div");
  const name = document.createElement("dt");
  name.textContent = label;
  const text = document.createElement("dd");
  text.textContent = String(value);
  row.append(name, text);
  container.appendChild(row);
}

async function showJobInfo(jobId) {
  const dialog = $("#jobInfoViewer");
  const content = $("#jobInfoContent");
  content.textContent = translate("history.loading_info");
  dialog.showModal();
  try {
    const job = await request(`/jobs/${jobId}`);
    const grid = document.createElement("dl");
    grid.className = "job-info-grid";
    appendInfoRow(grid, translate("metadata.title_label"), job.source_title || job.media_title);
    appendInfoRow(grid, translate("metadata.published_label"), formatLocalDateOnly(job.source_published_date));
    appendInfoRow(grid, translate("metadata.description_label"), job.source_description || job.media_description);
    appendInfoRow(grid, translate("source.url_label"), job.submitted_url);
    appendInfoRow(grid, translate("history.media_type"), job.media_type);
    content.replaceChildren(grid);
  } catch (error) {
    content.textContent = error.message;
  }
}

function formatDuration(milliseconds) {
  const totalMinutes = Math.max(0, Math.floor(milliseconds / 60000));
  const days = Math.floor(totalMinutes / 1440);
  const hours = Math.floor((totalMinutes % 1440) / 60);
  const minutes = totalMinutes % 60;
  const parts = [];
  if (days) parts.push(`${days} ${translate(days === 1 ? "duration.day_one" : "duration.day_many")}`);
  if (hours) parts.push(`${hours} ${translate(hours === 1 ? "duration.hour_one" : "duration.hour_many")}`);
  if (minutes || !parts.length) parts.push(`${minutes} ${translate(minutes === 1 ? "duration.minute_one" : "duration.minute_many")}`);
  return parts.join(" ");
}

async function showJobHistory(jobId) {
  const dialog = $("#jobHistoryViewer");
  const content = $("#jobHistoryContent");
  content.textContent = translate("history.loading_info");
  dialog.showModal();
  try {
    const events = await request(`/jobs/${jobId}/events`);
    const table = document.createElement("table");
    table.className = "job-history-table";
    const head = document.createElement("thead");
    const headRow = document.createElement("tr");
    ["history.status", "history.start", "history.duration", "history.result"].forEach((key) => {
      const cell = document.createElement("th");
      cell.textContent = translate(key);
      headRow.appendChild(cell);
    });
    head.appendChild(headRow);
    const body = document.createElement("tbody");
    events.forEach((event, index) => {
      const next = events[index + 1];
      const start = new Date(event.event_at);
      const duration = next ? formatDuration(new Date(next.event_at) - start) : "";
      const row = document.createElement("tr");
      [statusLabel(event.status), formatLocalDate(event.event_at), duration, runResultLabel(event.run_status)].forEach((value) => {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.appendChild(cell);
      });
      body.appendChild(row);
    });
    table.append(head, body);
    content.replaceChildren(table);
  } catch (error) {
    content.textContent = error.message;
  }
}

async function loadHistoryArtifacts(job, parent) {
  const existing = parent.querySelector(".history-artifacts");
  if (existing) {
    existing.remove();
    state.openHistoryArtifacts.delete(job.id);
    return;
  }
  state.openHistoryArtifacts.add(job.id);
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
  const [jobsResult, queueResult] = await Promise.allSettled([
    request("/jobs"),
    request("/queue-status"),
  ]);
  if (jobsResult.status === "rejected") throw jobsResult.reason;
  state.historyJobs = jobsResult.value;
  state.queueStatus = queueResult.status === "fulfilled" ? queueResult.value : null;
  state.staleHistoryJobIds.clear();
  renderHistory();
  scheduleHistoryPolling();
}

async function refreshActiveHistory() {
  const active = state.historyJobs.filter((job) => !STOP_POLL_STATUSES.has(job.status));
  if (!active.length) return scheduleHistoryPolling();
  const results = await Promise.allSettled(active.map((job) => request(`/jobs/${job.id}`)));
  const byId = new Map();
  results.forEach((result, index) => {
    const jobId = active[index].id;
    if (result.status === "fulfilled") {
      byId.set(jobId, result.value);
      state.staleHistoryJobIds.delete(jobId);
    } else {
      state.staleHistoryJobIds.add(jobId);
    }
  });
  state.historyJobs = state.historyJobs.map((job) => byId.get(job.id) || job);
  try {
    state.queueStatus = await request("/queue-status");
  } catch (_) {
    state.queueStatus = null;
  }
  renderHistory();
  scheduleHistoryPolling();
}

function scheduleHistoryPolling() {
  if (state.historyTimer) window.clearTimeout(state.historyTimer);
  if (!state.historyJobs.some((job) => !STOP_POLL_STATUSES.has(job.status))) return;
  state.historyTimer = window.setTimeout(() => {
    refreshActiveHistory().catch(() => {
      scheduleHistoryPolling();
    });
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
  if (STOP_POLL_STATUSES.has(job.status)) {
    stopPolling();
    if (["WAITING_FOR_PARTICIPANTS", "IN_REVIEW", "FINISHED"].includes(job.status)) renderArtifacts(await request(`/jobs/${job.id}/artifacts`));
  }
}

function startPolling() {
  stopPolling();
  state.pollTimer = window.setInterval(() => {
    refreshJob().catch(() => {
      state.staleJobStatus = true;
      $("#jobStatus").classList.add("is-stale");
    });
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
  setResolveLocked(true);
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
    setMessage("#resolveMessage", "");
    showErrorOverlay(userError(error));
    setResolveLocked(false);
  } finally {
    button.disabled = !state.resolved;
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
    state.job = job;
    stopPolling();
    resetResolveFlow();
    await loadHistory();
  } catch (error) {
    setMessage("#jobMessage", error.message, true);
  } finally {
    button.disabled = false;
  }
});

$("#historyRefreshButton").addEventListener("click", () => {
  loadHistory().catch((error) => setMessage("#historyMessage", error.message, true));
});

$("#clearUrlButton").addEventListener("click", () => {
  if (!$("#clearUrlButton").disabled) resetResolveFlow();
});
$("#cancelMediaButton").addEventListener("click", resetResolveFlow);

loadTranslations()
  .then(() => loadHistory())
  .catch((error) => setMessage("#historyMessage", error.message, true));
