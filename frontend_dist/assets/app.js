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
  participantReview: null,
  participantPlayers: new Map(),
};

const $ = (selector) => document.querySelector(selector);

async function loadTranslations() {
  const response = await fetch("./assets/i18n/et.json?v=4");
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

function destroyParticipantPlayers() {
  for (const player of state.participantPlayers.values()) {
    player.destroy?.();
  }
  state.participantPlayers.clear();
}

function participantVideo(video, message, url) {
  if (window.Hls?.isSupported()) {
    const hls = new window.Hls({ enableWorker: true });
    hls.loadSource(url);
    hls.attachMedia(video);
    hls.on(window.Hls.Events.ERROR, (_event, data) => {
      if (data?.fatal) message.textContent = translate("participants.player_error");
    });
    return { destroy: () => { hls.destroy(); video.pause(); } };
  }
  if (video.canPlayType("application/vnd.apple.mpegurl")) {
    video.src = url;
    const onError = () => { message.textContent = translate("participants.player_error"); };
    video.addEventListener("error", onError);
    return {
      destroy: () => {
        video.removeEventListener("error", onError);
        video.pause();
        video.removeAttribute("src");
        video.load();
      },
    };
  }
  message.textContent = translate("participants.player_unsupported");
  return { destroy: () => {} };
}

function playParticipantSample(video, sample) {
  const previous = video.__sampleEndHandler;
  if (previous) video.removeEventListener("timeupdate", previous);
  if (video.__sampleSeekHandler) {
    video.removeEventListener("loadedmetadata", video.__sampleSeekHandler);
    video.__sampleSeekHandler = null;
  }
  const seek = () => {
    video.__sampleSeekHandler = null;
    video.currentTime = Number(sample.start_second);
    video.play().catch(() => {});
  };
  if (video.readyState >= 1) seek();
  else {
    video.__sampleSeekHandler = seek;
    video.addEventListener("loadedmetadata", seek, { once: true });
  }
  const stopAtEnd = () => {
    if (video.currentTime >= Number(sample.end_second)) {
      video.pause();
      video.removeEventListener("timeupdate", stopAtEnd);
      video.__sampleEndHandler = null;
    }
  };
  video.__sampleEndHandler = stopAtEnd;
  video.addEventListener("timeupdate", stopAtEnd);
}

function participantMapping(card) {
  const input = card.querySelector(".participant-input");
  const unknown = isUnknownParticipantInput(input);
  const value = normalizeParticipantName(input.value);
  return {
    speaker_label: card.dataset.speakerLabel,
    participant_id: value && !unknown ? Number(input.dataset.participantId || 0) || null : null,
    role: card.querySelector(".participant-role").value.trim() || null,
    participant_name: value,
    description: card.querySelector(".participant-description").value.trim() || null,
    organisation: card.querySelector(".participant-organisation").value.trim() || null,
    occupation: card.querySelector(".participant-occupation").value.trim() || null,
    mapping_status: unknown ? "UNKNOWN" : value ? "CONFIRMED" : "UNCONFIRMED",
  };
}

function isUnknownParticipantInput(input) {
  return input.value.trim().toLocaleLowerCase() === translate("participants.unknown").toLocaleLowerCase();
}

function normalizeParticipantName(value) {
  return String(value || "").trim().split(/\s+/).filter(Boolean).map((word) => {
    const letters = Array.from(word.toLocaleLowerCase("et-EE"));
    return letters.length ? letters[0].toLocaleUpperCase("et-EE") + letters.slice(1).join("") : "";
  }).join(" ");
}

function addParticipantOption(list, participant) {
  const existing = [...list.options].find((option) => option.dataset.participantId === String(participant.id));
  if (existing) return;
  const option = document.createElement("option");
  option.value = participant.name;
  option.dataset.participantId = String(participant.id);
  option.textContent = participant.name;
  list.appendChild(option);
}

function addParticipantToAllLists(participant) {
  document.querySelectorAll(".participant-options").forEach((list) => addParticipantOption(list, participant));
}

function participantByInput(input) {
  const name = input.value.trim().toLocaleLowerCase();
  return state.participantReview?.participants.find((participant) => participant.name.trim().toLocaleLowerCase() === name) || null;
}

function updateParticipantDetails(card) {
  const input = card.querySelector(".participant-input");
  const unknown = isUnknownParticipantInput(input);
  const participant = !unknown ? participantByInput(input) : null;
  const editFields = card.querySelector(".participant-new-details");
  const existingDetails = card.querySelector(".participant-existing-details");
  if (!participant) {
    editFields.querySelectorAll("input, textarea").forEach((field) => { field.value = ""; });
  }
  editFields.classList.toggle("hidden", Boolean(participant) || unknown || !input.value.trim());
  existingDetails.classList.toggle("hidden", !participant || unknown);
  if (participant) {
    existingDetails.querySelector("[data-detail=description]").textContent = participant.description || "—";
    existingDetails.querySelector("[data-detail=organisation]").textContent = participant.organisation || "—";
    existingDetails.querySelector("[data-detail=occupation]").textContent = participant.occupation || "—";
  }
}

function renderParticipantReview(data, participants) {
  const container = $("#participantReviewContent");
  container.replaceChildren();
  destroyParticipantPlayers();
  data.speakers.forEach((speaker) => {
    const card = document.createElement("article");
    card.className = "speaker-review-card";
    card.dataset.speakerLabel = speaker.speaker_label;
    const heading = document.createElement("div");
    heading.className = "speaker-review-heading";
    const title = document.createElement("h3");
    title.textContent = speaker.speaker_label;
    heading.appendChild(title);
    const mapping = document.createElement("div");
    mapping.className = "speaker-mapping-fields";
    const selectLabel = document.createElement("label");
    selectLabel.textContent = translate("participants.person");
    const input = document.createElement("input");
    input.className = "participant-input";
    input.type = "text";
    input.maxLength = 500;
    input.placeholder = translate("participants.search_placeholder");
    const list = document.createElement("datalist");
    list.id = `participant-options-${speaker.speaker_label}`;
    list.className = "participant-options";
    const unknownOption = document.createElement("option");
    unknownOption.value = translate("participants.unknown");
    list.appendChild(unknownOption);
    participants.forEach((participant) => addParticipantOption(list, participant));
    if (speaker.participant_id != null) {
      addParticipantOption(list, {
        id: speaker.participant_id,
        name: speaker.participant_name || `#${speaker.participant_id}`,
      });
    }
    input.setAttribute("list", list.id);
    input.value = speaker.mapping_status === "UNKNOWN" ? translate("participants.unknown") : (speaker.participant_name || "");
    if (speaker.participant_id != null) input.dataset.participantId = String(speaker.participant_id);
    const inputRow = document.createElement("div");
    inputRow.className = "participant-input-row";
    const clearInput = document.createElement("button");
    clearInput.type = "button";
    clearInput.className = "participant-clear-input";
    clearInput.textContent = "×";
    clearInput.title = translate("participants.clear_name");
    clearInput.setAttribute("aria-label", translate("participants.clear_name"));
    clearInput.addEventListener("click", () => {
      input.value = "";
      input.dataset.participantId = "";
      input.dispatchEvent(new Event("input"));
      input.focus();
    });
    input.addEventListener("input", () => {
      const match = [...list.options].find((option) => option.value.trim().toLocaleLowerCase() === input.value.trim().toLocaleLowerCase());
      input.dataset.participantId = match?.dataset.participantId || "";
      if (match && !match.dataset.participantId) input.value = match.value;
      updateParticipantDetails(card);
    });
    input.addEventListener("blur", () => {
      input.value = normalizeParticipantName(input.value);
      input.dispatchEvent(new Event("input"));
    });
    inputRow.append(input, clearInput);
    selectLabel.append(inputRow, list);
    const participantDetails = [
      ["description", "participants.description", 4000],
      ["organisation", "participants.organisation", 500],
      ["occupation", "participants.occupation", 500],
    ];
    const existingDetails = document.createElement("div");
    existingDetails.className = "participant-existing-details hidden";
    participantDetails.forEach(([field, labelKey]) => {
      const line = document.createElement("div");
      line.className = "participant-existing-detail";
      line.innerHTML = `<span>${translate(labelKey)}</span><strong data-detail="${field}">—</strong>`;
      existingDetails.appendChild(line);
    });
    const newDetails = document.createElement("div");
    newDetails.className = "participant-new-details hidden";
    const detailLabels = participantDetails.map(([field, labelKey, maxLength]) => {
      const label = document.createElement("label");
      label.textContent = translate(labelKey);
      const detail = document.createElement(field === "description" ? "textarea" : "input");
      detail.className = `participant-${field}`;
      detail.maxLength = maxLength;
      detail.rows = field === "description" ? 2 : undefined;
      label.appendChild(detail);
      return label;
    });
    newDetails.append(...detailLabels);
    const roleLabel = document.createElement("label");
    roleLabel.textContent = translate("participants.role");
    const role = document.createElement("input");
    role.className = "participant-role";
    role.type = "text";
    role.maxLength = 120;
    role.value = speaker.role || "";
    roleLabel.appendChild(role);
    mapping.append(selectLabel, existingDetails, newDetails, roleLabel);
    const samples = document.createElement("div");
    samples.className = "speaker-samples";
    const video = document.createElement("video");
    video.className = "speaker-sample-video";
    video.controls = true;
    video.preload = "metadata";
    video.playsInline = true;
    samples.appendChild(video);
    const playerMessage = document.createElement("p");
    playerMessage.className = "speaker-player-message";
    playerMessage.setAttribute("role", "status");
    samples.appendChild(playerMessage);
    const sampleButtons = document.createElement("div");
    sampleButtons.className = "speaker-sample-buttons";
    speaker.samples.forEach((sample, index) => {
      const sampleCard = document.createElement("div");
      sampleCard.className = "speaker-sample";
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary-button sample-button";
      button.textContent = `${translate("participants.sample")} ${index + 1} · ${formatSeconds(sample.start_second)}–${formatSeconds(sample.end_second)}`;
      button.addEventListener("click", () => playParticipantSample(video, sample));
      const text = document.createElement("p");
      text.className = "speaker-sample-text";
      text.textContent = sample.text;
      sampleCard.append(button, text);
      sampleButtons.appendChild(sampleCard);
    });
    samples.appendChild(sampleButtons);
    card.append(heading, mapping, samples);
    container.appendChild(card);
    updateParticipantDetails(card);
    state.participantPlayers.set(speaker.speaker_label, participantVideo(video, playerMessage, data.media.url));
  });
}

function formatSeconds(value) {
  const seconds = Math.max(0, Number(value) || 0);
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const clock = `${String(minutes).padStart(2, "0")}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
  return hours ? `${String(hours).padStart(2, "0")}:${clock}` : clock;
}

async function showParticipantReview(jobId) {
  const dialog = $("#participantReviewViewer");
  const message = $("#participantReviewMessage");
  const content = $("#participantReviewContent");
  state.participantReview = { jobId };
  message.textContent = translate("participants.loading");
  content.replaceChildren();
  dialog.showModal();
  try {
    const [data, participants] = await Promise.all([
      request(`/jobs/${jobId}/participant-review`),
      request("/participants"),
    ]);
    state.participantReview.data = data;
    state.participantReview.participants = participants;
    renderParticipantReview(data, participants);
    message.textContent = "";
  } catch (error) {
    message.textContent = error.message;
  }
}

async function saveParticipantReview() {
  if (!state.participantReview) return;
  const saveButton = $("#participantReviewSave");
  saveButton.disabled = true;
  try {
  const mappings = [...document.querySelectorAll(".speaker-review-card")].map(participantMapping);
  for (const mapping of mappings) {
    if (mapping.mapping_status !== "CONFIRMED" || mapping.participant_id) continue;
    const existing = state.participantReview.participants.find((participant) => participant.name.trim().toLocaleLowerCase() === mapping.participant_name.trim().toLocaleLowerCase());
    const participant = existing || await request("/participants", {
      method: "POST",
      body: JSON.stringify({
        name: mapping.participant_name,
        description: mapping.description,
        organisation: mapping.organisation,
        occupation: mapping.occupation,
      }),
    });
    if (!existing) {
      state.participantReview.participants.push(participant);
      addParticipantToAllLists(participant);
    }
    mapping.participant_id = participant.id;
  }
  const unresolved = mappings.filter((mapping) => mapping.mapping_status === "UNCONFIRMED");
    const result = await request(`/jobs/${state.participantReview.jobId}/participant-review`, {
      method: "PUT",
      body: JSON.stringify({ mappings, confirm: unresolved.length === 0 }),
    });
    $("#participantReviewMessage").textContent = result.unresolved_labels?.length
      ? `${translate("participants.saved_partial")}: ${result.unresolved_labels.join(", ")}`
      : translate("participants.saved");
    if (result.confirmed) {
      const confirmedJobId = state.participantReview.jobId;
      destroyParticipantPlayers();
      $("#participantReviewViewer").close();
      await loadHistory();
      if (state.job?.id === confirmedJobId) await refreshJob();
    }
  } catch (error) {
    $("#participantReviewMessage").textContent = error.message;
  } finally {
    saveButton.disabled = false;
  }
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
  const primaryArtifacts = artifacts
    .filter((artifact) => ["MD", "VTT"].includes(artifactCategory(artifact)))
    .sort((left, right) => {
      const order = { MD: 0, VTT: 1 };
      return order[artifactCategory(left)] - order[artifactCategory(right)];
    });
  primaryArtifacts.forEach((artifact) => {
    const category = artifactCategory(artifact);
    if (!seenPrimaryTypes.has(category)) {
      seenPrimaryTypes.add(category);
      primary.push(artifact);
    }
  });
  const technical = artifacts.filter((artifact) => !["MD", "VTT"].includes(artifactCategory(artifact)));
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

function artifactCategory(artifact) {
  const type = String(artifact.artifact_type || "").toUpperCase();
  if (type === "MD" || type.includes("TRANSCRIPT_MARKDOWN")) return "MD";
  if (type === "VTT" || type.endsWith("_VTT")) return "VTT";
  return type;
}

function buildArtifactLink(artifact, jobId) {
  const row = document.createElement("li");
  const link = document.createElement("a");
  link.href = `${API_BASE}/jobs/${jobId}/artifacts/${artifact.id}`;
  link.target = "_blank";
  link.rel = "noopener";
  link.addEventListener("click", (event) => {
    event.preventDefault();
    openResultsViewer(jobId);
  });
  link.textContent = artifactCategory(artifact) === "MD"
    ? translate("artifacts.transcript")
    : artifactCategory(artifact) === "VTT"
      ? translate("artifacts.vtt")
      : `${artifact.artifact_type} (${artifact.size_byte} B)`;
  row.appendChild(link);
  return row;
}

function artifactDisplayName(artifact) {
  const category = artifactCategory(artifact);
  const type = String(artifact.artifact_type || "").toUpperCase();
  if (type === "REVIEWED_TRANSCRIPT_MARKDOWN") return translate("artifacts.transcript");
  if (type === "AUTOMATIC_TRANSCRIPT_MARKDOWN") return translate("artifacts.transcript_automatic");
  if (category === "MD") return `${translate("artifacts.transcript_version")} #${artifact.id}`;
  if (category === "VTT") return translate("artifacts.vtt");
  return `${artifact.artifact_type} (${artifact.size_byte} B)`;
}

function artifactDownloadName(artifact) {
  const category = artifactCategory(artifact);
  if (category === "VTT") return "saate-subtiitrid.vtt";
  if (category === "MD") return "transkriptsioon.md";
  const extension = String(artifact.artifact_type || "json").toLowerCase().split("_").pop() || "json";
  return `tehniline-fail.${extension}`;
}

function populateArtifactViewer(artifacts, jobId) {
  const select = $("#artifactViewerSelect");
  const ordered = [...artifacts].sort((left, right) => {
    const rank = (artifact) => {
      const type = String(artifact.artifact_type || "").toUpperCase();
      if (type === "REVIEWED_TRANSCRIPT_MARKDOWN") return 0;
      if (type === "AUTOMATIC_TRANSCRIPT_MARKDOWN") return 1;
      if (artifactCategory(artifact) === "MD") return 2;
      if (artifactCategory(artifact) === "VTT") return 3;
      return 4;
    };
    const leftOrder = rank(left);
    const rightOrder = rank(right);
    return leftOrder - rightOrder || Number(left.id) - Number(right.id);
  });
  select.replaceChildren();
  ordered.forEach((artifact) => {
    const option = document.createElement("option");
    option.value = String(artifact.id);
    option.textContent = artifactDisplayName(artifact);
    select.appendChild(option);
  });
  select.onchange = () => {
    const artifact = ordered.find((item) => String(item.id) === select.value);
    if (artifact) loadArtifactIntoViewer(artifact, jobId);
  };
  if (ordered.length) {
    select.value = String(ordered[0].id);
    loadArtifactIntoViewer(ordered[0], jobId);
  }
}

async function loadArtifactIntoViewer(artifact, jobId) {
  const dialog = $("#artifactViewer");
  const message = $("#artifactViewerMessage");
  const content = $("#artifactViewerContent");
  const download = $("#artifactViewerDownload");
  const url = `${API_BASE}/jobs/${jobId}/artifacts/${artifact.id}`;
  download.dataset.url = url;
  download.dataset.artifactType = artifactCategory(artifact);
  download.dataset.downloadName = artifactDownloadName(artifact);
  message.textContent = translate("artifacts.loading");
  content.textContent = "";
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const text = await response.text();
    const category = artifactCategory(artifact);
    if (category === "MD") {
      content.classList.remove("is-vtt", "is-raw");
      content.innerHTML = renderMarkdown(text);
    } else {
      content.classList.add("is-vtt", "is-raw");
      if (category !== "VTT") {
        try {
          content.textContent = JSON.stringify(JSON.parse(text), null, 2);
        } catch {
          content.textContent = text;
        }
      } else {
        content.textContent = text;
      }
    }
    if (category === "MD") content.classList.remove("is-raw");
    message.textContent = "";
  } catch (error) {
    message.textContent = error.message;
  }
}

async function openResultsViewer(jobId) {
  const dialog = $("#artifactViewer");
  const message = $("#artifactViewerMessage");
  const content = $("#artifactViewerContent");
  const select = $("#artifactViewerSelect");
  select.replaceChildren();
  content.textContent = "";
  message.textContent = translate("artifacts.loading");
  dialog.showModal();
  try {
    const artifacts = await request(`/jobs/${jobId}/artifacts`);
    populateArtifactViewer(artifacts, jobId);
    message.textContent = artifacts.length ? "" : translate("history.loading_results");
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
$("#participantReviewClose").addEventListener("click", () => {
  destroyParticipantPlayers();
  $("#participantReviewViewer").close();
});
$("#participantReviewSave").addEventListener("click", () => saveParticipantReview());
$("#participantReviewViewer").addEventListener("close", destroyParticipantPlayers);

$("#artifactViewerClose").addEventListener("click", () => $("#artifactViewer").close());
$("#artifactViewerDownload").addEventListener("click", async () => {
  const button = $("#artifactViewerDownload");
  try {
    const response = await fetch(button.dataset.url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = button.dataset.downloadName || "tulemus";
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
    const statusColumn = document.createElement("div");
    statusColumn.className = "history-status-column";
    statusColumn.appendChild(status);
    head.append(title, statusColumn);
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
      button.addEventListener("click", () => openResultsViewer(job.id));
      actions.appendChild(button);
    }
    if (job.status === "WAITING_FOR_PARTICIPANTS") {
      const participantsButton = document.createElement("button");
      participantsButton.type = "button";
      participantsButton.className = "results-button history-participant-action";
      participantsButton.textContent = translate("history.participants");
      participantsButton.addEventListener("click", () => showParticipantReview(job.id));
      actions.appendChild(participantsButton);
    }
    item.appendChild(actions);
    container.appendChild(item);
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
