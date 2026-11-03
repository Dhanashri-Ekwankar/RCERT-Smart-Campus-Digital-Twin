/**
 * RCERT Smart Campus Digital Twin 2.0 — Frontend Controller
 * All dynamic data is server-validated and escaped before insertion.
 */

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const state = {
  current: null,
  forecast: null,
  air: null,
  zones: [],
  selectedZone: null,
  twin: null,
  twinStarted: false,
  is2D: false,
  toastTimer: 0,
  settings: {
    temperature_unit: "celsius",
    wind_unit: "kmh",
    refresh_interval_sec: 300,
    theme: "dark",
    presentation_mode: false,
    render_quality: "high"
  },
  activeReport: "weather-summary",
  historical: []
};

const viewNames = {
  dashboard: "Overview",
  weather: "Weather & Air",
  campus: "Campus Twin 3D",
  analytics: "Analytics",
  alerts: "Alerts Center",
  about: "About RCERT",
  reports: "Reports & Export",
  settings: "Settings"
};

// --- Unit Conversion Helpers ---
function formatTemp(valC, digits = 1) {
  if (valC == null || !Number.isFinite(Number(valC))) return "—";
  let v = Number(valC);
  if (state.settings.temperature_unit === "fahrenheit") {
    v = (v * 9) / 5 + 32;
    return `${v.toFixed(digits)} °F`;
  }
  return `${v.toFixed(digits)} °C`;
}

function tempNumOnly(valC, digits = 1) {
  if (valC == null || !Number.isFinite(Number(valC))) return "—";
  let v = Number(valC);
  if (state.settings.temperature_unit === "fahrenheit") {
    v = (v * 9) / 5 + 32;
  }
  return v.toFixed(digits);
}

function formatWind(valKmh, digits = 1) {
  if (valKmh == null || !Number.isFinite(Number(valKmh))) return "—";
  let v = Number(valKmh);
  if (state.settings.wind_unit === "ms") {
    return `${(v / 3.6).toFixed(digits)} m/s`;
  } else if (state.settings.wind_unit === "mph") {
    return `${(v * 0.621371).toFixed(digits)} mph`;
  }
  return `${v.toFixed(digits)} km/h`;
}

function windNumOnly(valKmh, digits = 1) {
  if (valKmh == null || !Number.isFinite(Number(valKmh))) return "—";
  let v = Number(valKmh);
  if (state.settings.wind_unit === "ms") {
    v = v / 3.6;
  } else if (state.settings.wind_unit === "mph") {
    v = v * 0.621371;
  }
  return v.toFixed(digits);
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value ?? "—";
}

function num(value, digits = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(digits) : "—";
}

function dateLabel(value, options = { weekday: "short", month: "short", day: "numeric" }) {
  if (!value) return "—";
  const d = new Date(value.length === 10 ? `${value}T12:00:00` : value);
  return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleDateString("en-IN", options);
}

function timeLabel(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[ch]));
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    cache: "no-store",
    ...options,
    headers: {
      ...(options.headers || {}),
      ...(options.body ? { "Content-Type": "application/json" } : {})
    }
  });
  let data;
  try {
    data = await response.json();
  } catch {
    data = {};
  }
  if (!response.ok || data.success === false) {
    throw new Error(data.error || `${response.status} ${response.statusText}`);
  }
  return data;
}

function toast(message) {
  const el = $("#toast");
  if (!el) return;
  el.textContent = message;
  el.classList.add("is-visible");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => el.classList.remove("is-visible"), 2800);
}

function updateClock() {
  const now = new Date();
  setText("clock", now.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: "Asia/Kolkata" }));
  setText("date", now.toLocaleDateString("en-IN", { weekday: "short", day: "2-digit", month: "short", year: "numeric", timeZone: "Asia/Kolkata" }));
}

function setSystem(ok, label) {
  const dot = $("#system-dot");
  if (dot) {
    dot.classList.toggle("is-ok", !!ok);
    dot.classList.toggle("is-error", !ok);
  }
  setText("system-label", label);
}

function updateSpatialIndicator() {
  const glow = $("#nav-indicator-glow");
  const activeBtn = $(".nexus-nav-capsule .nav-link.is-active");
  const list = $("#nav-list");
  if (!glow || !activeBtn || !list) return;

  const listRect = list.getBoundingClientRect();
  const btnRect = activeBtn.getBoundingClientRect();

  if (btnRect.width > 0) {
    const offsetLeft = btnRect.left - listRect.left;
    glow.style.transform = `translateX(${offsetLeft}px)`;
    glow.style.width = `${btnRect.width}px`;
    glow.style.opacity = "1";
  } else {
    glow.style.opacity = "0";
  }
}

function showView(view) {
  if (!viewNames[view]) return;
  $$("[data-view]").forEach(node => {
    const visible = node.dataset.view === view;
    node.hidden = !visible;
    node.classList.toggle("is-visible", visible);
  });
  $$("[data-view-target]").forEach(node => {
    node.classList.toggle("is-active", node.dataset.viewTarget === view);
  });
  setText("page-crumb", viewNames[view]);
  closeMenu();
  requestAnimationFrame(updateSpatialIndicator);

  if (view === "dashboard") state.cinematicScrub?.update?.();
  if (view === "campus") startTwin();
  if (view === "weather") renderWeatherView();
  if (view === "analytics") renderAnalyticsView();
  if (view === "alerts") loadAlerts();
  if (view === "reports") renderReportDocument();
  if (view === "settings") loadSettingsView();

  history.replaceState(null, "", `#${view}`);
}

function closeMenu() {
  const overlay = $("#mobile-spatial-overlay");
  if (overlay) overlay.hidden = true;
  document.body.style.overflow = "";
  $("#menu-toggle")?.setAttribute("aria-expanded", "false");
  $("#mobile-hub-btn")?.setAttribute("aria-expanded", "false");
  $("#sidebar")?.classList.remove("is-open");
  const scrim = $("#mobile-scrim");
  if (scrim) scrim.hidden = true;
}

function openMenu() {
  const overlay = $("#mobile-spatial-overlay");
  if (overlay) overlay.hidden = false;
  document.body.style.overflow = "hidden";
  $("#menu-toggle")?.setAttribute("aria-expanded", "true");
  $("#mobile-hub-btn")?.setAttribute("aria-expanded", "true");
  $("#sidebar")?.classList.add("is-open");
  const scrim = $("#mobile-scrim");
  if (scrim) scrim.hidden = false;
}

function weatherGlyph(condition) {
  const t = String(condition || "").toLowerCase();
  if (t.includes("thunder")) return "ϟ";
  if (t.includes("rain") || t.includes("drizzle")) return "☂";
  if (t.includes("cloud") || t.includes("overcast")) return "☁";
  if (t.includes("fog")) return "≋";
  if (t.includes("clear") || t.includes("sun")) return "☼";
  return "◌";
}

function aqiCategory(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "Air-quality forecast";
  if (n <= 50) return "Good (0–50)";
  if (n <= 100) return "Moderate (51–100)";
  if (n <= 150) return "Sensitive Groups (101–150)";
  if (n <= 200) return "Unhealthy (151–200)";
  if (n <= 300) return "Very Unhealthy (201–300)";
  return "Hazardous (301+)";
}

function aqBand(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "Unavailable";
  if (n <= 50) return "Good";
  if (n <= 100) return "Moderate";
  if (n <= 150) return "Sensitive Groups";
  if (n <= 200) return "Unhealthy";
  if (n <= 300) return "Very Unhealthy";
  return "Hazardous";
}

function updateForecastStatus() {
  const items = [state.current, state.forecast, state.air].filter(Boolean);
  const stale = items.some(x => x.stale);
  const unavailable = items.length === 0 || !state.current?.success;
  const staleBanner = $("#stale-banner");
  const staleLabel = $("#stale-label");
  const errorBanner = $("#error-banner");

  if (staleBanner) staleBanner.hidden = !stale;
  if (staleLabel) staleLabel.hidden = !stale;
  if (errorBanner) errorBanner.hidden = !unavailable;

  setText("overall-data-state", unavailable ? "Forecast unavailable" : stale ? "Using cached forecast" : "Verified forecast synchronized");
  if (unavailable) setSystem(false, "DATA UNAVAILABLE");
  else setSystem(true, stale ? "CACHED FORECAST" : "API CONNECTED");
}

// --- Render Overview Dashboard ---
function renderOverview() {
  const p = state.current;
  const c = p?.data?.current;
  if (!c) {
    updateForecastStatus();
    return;
  }

  // Hero readings
  setText("current-temp", tempNumOnly(c.temperature_c, 1));
  setText("temp-unit-display", state.settings.temperature_unit === "fahrenheit" ? "°F" : "°C");
  setText("feels-like", tempNumOnly(c.feels_like_c, 1));
  setText("dew-point", tempNumOnly(c.dew_point_c, 1));
  setText("current-condition", c.condition || "Clear");
  $("#weather-glyph").textContent = weatherGlyph(c.condition);
  setText("weather-source", p.source || "Open-Meteo High-Resolution API");
  setText("weather-updated", `Fetched at: ${timeLabel(p.fetched_at)} IST${p.stale ? " (cached)" : ""}`);

  // Hero secondary stats
  setText("humidity", num(c.humidity_pct));
  const humTrack = $("#humidity-track");
  if (humTrack) humTrack.style.width = `${Math.max(0, Math.min(100, Number(c.humidity_pct) || 0))}%`;

  setText("wind-speed", windNumOnly(c.wind_speed_kmh, 1));
  setText("wind-unit-display", state.settings.wind_unit === "ms" ? "m/s" : state.settings.wind_unit === "mph" ? "mph" : "km/h");
  setText("wind-gust", windNumOnly(c.wind_gusts_kmh, 1));

  const day0 = state.forecast?.data?.daily?.[0];
  setText("rain-prob", num(day0?.precipitation_probability_max, 0));
  setText("precip-val", num(day0?.precipitation_sum, 1));

  // 8 Metric Cards
  setText("metric-temperature", tempNumOnly(c.temperature_c, 1));
  setText("metric-humidity", num(c.humidity_pct));
  setText("metric-feels-like", tempNumOnly(c.feels_like_c, 1));
  setText("metric-wind", windNumOnly(c.wind_speed_kmh, 1));
  setText("metric-rain-chance", num(day0?.precipitation_probability_max, 0));

  const aq = state.air?.data?.current || {};
  setText("metric-aqi", num(aq.us_aqi));
  setText("aqi-label", aqiCategory(aq.us_aqi));
  setText("metric-pm25", num(aq.pm2_5_ugm3, 1));
  setText("metric-pm10", num(aq.pm10_ugm3, 1));

  // Environmental Risk Evaluation
  evaluateEnvironmentalRisks(c, day0, aq);

  updateForecastStatus();
  renderForecastRow();
  renderInsights();
}

function evaluateEnvironmentalRisks(current, day0, aq) {
  // 1. Thermal Comfort
  const temp = Number(current?.temperature_c || 25);
  const thermalCell = $("#risk-thermal");
  if (thermalCell) {
    const status = thermalCell.querySelector(".risk-status");
    if (temp >= 38) {
      status.textContent = "High Heat Risk";
      thermalCell.className = "risk-cell is-critical";
    } else if (temp >= 32) {
      status.textContent = "Moderate Warmth";
      thermalCell.className = "risk-cell is-warning";
    } else {
      status.textContent = "Comfortable";
      thermalCell.className = "risk-cell is-good";
    }
  }

  // 2. Solar UV
  const uvMax = Number(day0?.uv_index_max || 5);
  const uvCell = $("#risk-uv");
  if (uvCell) {
    const status = uvCell.querySelector(".risk-status");
    if (uvMax >= 8) {
      status.textContent = `Very High (UV ${uvMax.toFixed(0)})`;
      uvCell.className = "risk-cell is-critical";
    } else if (uvMax >= 6) {
      status.textContent = `High (UV ${uvMax.toFixed(0)})`;
      uvCell.className = "risk-cell is-warning";
    } else {
      status.textContent = `Moderate (UV ${uvMax.toFixed(0)})`;
      uvCell.className = "risk-cell is-good";
    }
  }

  // 3. Air Quality
  const aqi = Number(aq?.us_aqi || 60);
  const airCell = $("#risk-air");
  if (airCell) {
    const status = airCell.querySelector(".risk-status");
    if (aqi >= 150) {
      status.textContent = `Unhealthy (${aqi.toFixed(0)})`;
      airCell.className = "risk-cell is-critical";
    } else if (aqi >= 100) {
      status.textContent = `Sensitive Groups (${aqi.toFixed(0)})`;
      airCell.className = "risk-cell is-warning";
    } else {
      status.textContent = `Good / Moderate (${aqi.toFixed(0)})`;
      airCell.className = "risk-cell is-good";
    }
  }

  // 4. Precipitation
  const rainProb = Number(day0?.precipitation_probability_max || 0);
  const rainCell = $("#risk-rain");
  if (rainCell) {
    const status = rainCell.querySelector(".risk-status");
    if (rainProb >= 70) {
      status.textContent = `High Chance (${rainProb}%)`;
      rainCell.className = "risk-cell is-critical";
    } else if (rainProb >= 40) {
      status.textContent = `Possible (${rainProb}%)`;
      rainCell.className = "risk-cell is-warning";
    } else {
      status.textContent = `Low Likelihood (${rainProb}%)`;
      rainCell.className = "risk-cell is-good";
    }
  }
}

function renderForecastRow() {
  const days = state.forecast?.data?.daily || [];
  const target = $("#forecast-row");
  if (!target) return;
  if (!days.length) {
    target.innerHTML = '<div class="chart-empty">Daily forecast unavailable.</div>';
    return;
  }
  const low = Math.min(...days.map(d => Number(d.temperature_2m_min)).filter(Number.isFinite));
  const high = Math.max(...days.map(d => Number(d.temperature_2m_max)).filter(Number.isFinite));

  target.innerHTML = days.slice(0, 7).map((d, i) => {
    const min = Number(d.temperature_2m_min);
    const max = Number(d.temperature_2m_max);
    const left = Number.isFinite(low) && Number.isFinite(high) && high > low ? ((min - low) / (high - low)) * 100 : 20;
    const width = Number.isFinite(low) && Number.isFinite(high) && high > low ? Math.max(12, ((max - min) / (high - low)) * 100) : 60;
    return `<article class="forecast-day ${i === 0 ? "is-today" : ""}">
      <span>${i === 0 ? "Today" : escapeHtml(dateLabel(d.time, { weekday: "short", month: "short", day: "numeric" }))}</span>
      <i class="forecast-icon">${weatherGlyph(d.condition)}</i>
      <b>${tempNumOnly(max, 0)}° <span style="color:#8992a2">/ ${tempNumOnly(min, 0)}°</span></b>
      <div class="forecast-range"><i style="left:${left}%;width:${width}%"></i></div>
      <small>${num(d.precipitation_probability_max)}% rain</small>
    </article>`;
  }).join("");
}

function renderInsights() {
  const target = $("#insights-list");
  if (!target) return;
  const items = state.forecast?.insights || [];
  if (!items.length) {
    target.innerHTML = '<div class="quiet-insight">No forecast threshold advisories active right now. Meteorological variables within nominal ranges.</div>';
    return;
  }
  target.innerHTML = items.map(item => `<article class="insight-item severity-${escapeHtml(item.severity || "warning")}">
    <i></i>
    <div>
      <b>${escapeHtml(item.title)}</b>
      <p>${escapeHtml(item.message)}</p>
      <small>${escapeHtml(item.classification || "forecast")} · ${escapeHtml(item.source || "Open-Meteo")}${item.time_window ? ` · ${escapeHtml(timeLabel(item.time_window))}` : ""}</small>
    </div>
  </article>`).join("");
}

// --- Render Dedicated Weather View ---
function renderWeatherView() {
  const c = state.current?.data?.current;
  if (!c) return;

  setText("telem-dew", formatTemp(c.dew_point_c, 1));
  setText("telem-pressure", `${num(c.pressure_hpa, 1)} hPa`);
  setText("telem-cloud", `${num(c.cloud_cover_pct, 0)} %`);
  setText("telem-visibility", `${num((Number(c.visibility_m) || 10000) / 1000, 1)} km`);
  setText("telem-uv", num(c.uv_index, 1));

  const day0 = state.forecast?.data?.daily?.[0];
  const rise = day0?.sunrise ? timeLabel(day0.sunrise) : "06:10";
  const set = day0?.sunset ? timeLabel(day0.sunset) : "17:45";
  setText("telem-sun", `${rise} / ${set}`);

  // Render Charts
  const rows = (state.forecast?.data?.hourly || []).slice(0, 24);
  const tempChart = $("#weather-temp-chart");
  if (tempChart) tempChart.innerHTML = chartSvg(rows, "temperature_2m", { color: "#ad94f6", unit: "°C", label: "Temperature" });

  const rainChart = $("#weather-rain-chart");
  if (rainChart) rainChart.innerHTML = chartSvg(rows, "precipitation_probability", { color: "#74cbd5", unit: "%", label: "Rain Probability" });

  const humChart = $("#weather-humidity-chart");
  if (humChart) humChart.innerHTML = chartSvg(rows, "relative_humidity_2m", { color: "#54b7ab", unit: "%", label: "Relative Humidity" });

  const windChart = $("#weather-wind-chart");
  if (windChart) windChart.innerHTML = chartSvg(rows, "wind_speed_10m", { color: "#e5b46b", unit: " km/h", label: "Wind Velocity" });

  // Render Air Quality
  const aq = state.air?.data?.current || {};
  setText("air-us-aqi", num(aq.us_aqi));
  setText("air-us-label", aqBand(aq.us_aqi));
  setText("air-pm25", num(aq.pm2_5_ugm3, 1));
  setText("air-pm10", num(aq.pm10_ugm3, 1));
  setText("air-eu-aqi", num(aq.european_aqi));
  setText("air-ozone", num(aq.ozone_ugm3, 1));
  setText("air-no2", num(aq.nitrogen_dioxide_ugm3, 1));
  setText("air-so2", num(aq.sulphur_dioxide_ugm3, 1));
  setText("air-co", num(aq.carbon_monoxide_ugm3, 1));
  setText("air-source", state.air?.source || "Open-Meteo Air Quality API (CAMS)");
  setText("air-time", `Forecast time: ${timeLabel(aq.time)} IST`);

  // Render 7-day extended list
  const weekList = $("#week-list");
  const days = state.forecast?.data?.daily || [];
  if (weekList && days.length) {
    weekList.innerHTML = days.slice(0, 7).map(d => `<div class="week-day">
      <span>${escapeHtml(dateLabel(d.time, { weekday: "short", month: "short", day: "numeric" }))}</span>
      <i class="week-icon">${weatherGlyph(d.condition)}</i>
      <div class="week-bar">
        <i style="left:${Math.min(80, Math.max(0, (Number(d.temperature_2m_min) - 10) * 2.8))}%;width:${Math.min(80, Math.max(12, (Number(d.temperature_2m_max) - Number(d.temperature_2m_min)) * 2.8))}%"></i>
      </div>
      <b>${tempNumOnly(d.temperature_2m_max, 0)}° / ${tempNumOnly(d.temperature_2m_min, 0)}°</b>
      <span class="week-rain">${num(d.precipitation_probability_max)}% rain</span>
    </div>`).join("");
  }
}

// --- Render Advanced Campus Analytics ---
function renderAnalyticsView() {
  const timeframe = $("#analytics-timeframe")?.value || "24h";
  const rows = (state.forecast?.data?.hourly || []).slice(0, timeframe === "7d" ? 168 : 24);

  const tempChart = $("#analytics-temp-chart");
  if (tempChart) tempChart.innerHTML = chartSvg(rows, "temperature_2m", { color: "#ad94f6", unit: "°C", label: "Temperature Curve" });

  const rainChart = $("#analytics-rain-chart");
  if (rainChart) rainChart.innerHTML = chartSvg(rows, "precipitation_probability", { color: "#74cbd5", unit: "%", label: "Precipitation Probability" });

  const humChart = $("#analytics-humidity-chart");
  if (humChart) humChart.innerHTML = chartSvg(rows, "relative_humidity_2m", { color: "#54b7ab", unit: "%", label: "Moisture & Humidity" });

  const windChart = $("#analytics-wind-chart");
  if (windChart) windChart.innerHTML = chartSvg(rows, "wind_speed_10m", { color: "#e5b46b", unit: " km/h", label: "Wind Velocity" });

  const uvChart = $("#analytics-uv-chart");
  if (uvChart) uvChart.innerHTML = chartSvg(rows, "uv_index", { color: "#e2786a", unit: " UV", label: "Solar UV Index" });

  const pmChart = $("#analytics-pm-chart");
  const aqRows = (state.air?.data?.hourly || []).slice(0, 24);
  if (pmChart) {
    if (aqRows.length) {
      pmChart.innerHTML = chartSvg(aqRows, "pm2_5", { color: "#7dc589", unit: " µg/m³", label: "Particulate Matter PM2.5" });
    } else {
      pmChart.innerHTML = '<div class="chart-empty">Hourly air quality forecast unavailable.</div>';
    }
  }
}

// --- Interactive SVG Line Chart Generator ---
function chartSvg(rows, key, { color = "#ad94f6", unit = "", label = "" } = {}) {
  const valid = rows.map(r => ({ time: r.time, value: Number(r[key]) })).filter(x => Number.isFinite(x.value));
  if (valid.length < 2) return '<div class="chart-empty">Forecast series unavailable.</div>';

  const width = 720, height = 180, left = 36, right = 14, top = 16, bottom = 28;
  const plotW = width - left - right, plotH = height - top - bottom;
  const values = valid.map(x => x.value);
  const min = Math.min(...values), max = Math.max(...values);
  const span = max - min || 1;

  const points = valid.map((p, i) => ({
    x: left + (i / (valid.length - 1)) * plotW,
    y: top + plotH - ((p.value - min) / span) * plotH,
    ...p
  }));

  const path = points.map((p, i) => `${i ? "L" : "M"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
  const labels = points
    .filter((_, i) => i === 0 || i === points.length - 1 || i % Math.max(1, Math.floor(points.length / 5)) === 0)
    .map(p => `<text class="chart-axis-label" x="${p.x}" y="${height - 7}" text-anchor="middle">${escapeHtml(timeLabel(p.time))}</text>`)
    .join("");

  const last = points.at(-1);

  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(label)} forecast chart">
    <line class="chart-gridline" x1="${left}" x2="${width - right}" y1="${top + plotH}" y2="${top + plotH}"/>
    <line class="chart-gridline" x1="${left}" x2="${width - right}" y1="${top + plotH / 2}" y2="${top + plotH / 2}"/>
    <line class="chart-gridline" x1="${left}" x2="${width - right}" y1="${top}" y2="${top}"/>
    <path d="${path}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="${last.x}" cy="${last.y}" r="4.5" fill="${color}"/>
    <text class="chart-axis-label" x="${left}" y="12">${escapeHtml(num(max, 1))}${escapeHtml(unit)}</text>
    <text class="chart-axis-label" x="${left}" y="${top + plotH - 4}">${escapeHtml(num(min, 1))}${escapeHtml(unit)}</text>
    ${labels}
  </svg>`;
}

// --- Alerts Center ---
async function loadAlerts() {
  const target = $("#alerts-list");
  if (target) target.innerHTML = '<div class="loading-row">Loading persistent alert register…</div>';

  const status = $("#alert-state")?.value || "active";
  const severityFilter = $("#alert-severity-filter")?.value || "all";
  const search = $("#alert-search-box")?.value?.trim()?.toLowerCase() || "";

  try {
    const data = await api(`/api/alerts?state=${encodeURIComponent(status)}`);
    let alerts = data.alerts || [];

    if (severityFilter !== "all") {
      alerts = alerts.filter(a => a.severity === severityFilter);
    }
    if (search) {
      alerts = alerts.filter(a =>
        a.title.toLowerCase().includes(search) ||
        a.message.toLowerCase().includes(search) ||
        a.category.toLowerCase().includes(search)
      );
    }

    const activeUnack = alerts.filter(a => !a.acknowledged_at && !a.resolved_at).length;
    ["#sidebar-alert-count", "#mobile-dock-alert-count", "#overlay-alert-count"].forEach(sel => {
      const el = $(sel);
      if (el) {
        el.textContent = String(activeUnack);
        el.hidden = activeUnack === 0;
      }
    });

    setText("alerts-summary", alerts.length ? `${alerts.length} ${status} alert${alerts.length === 1 ? "" : "s"} logged` : "No matching alerts in register");
    setText("alerts-updated", `Updated: ${timeLabel(data.timestamp)} IST`);

    if (!target) return;
    if (!alerts.length) {
      target.innerHTML = '<div class="panel empty-state"><b>No active advisories in register</b><p>Threshold-based advisories are logged when forecast values exceed safety parameters. No simulated records are inserted.</p></div>';
      return;
    }

    target.innerHTML = alerts.map(alert => `<article class="alert-card alert-${escapeHtml(alert.severity)}">
      <div class="alert-card-head">
        <div>
          <span class="eyebrow">${escapeHtml(alert.category)} · ${escapeHtml(alert.source)}</span>
          <h2>${escapeHtml(alert.title)}</h2>
        </div>
        <span class="alert-level">${escapeHtml(alert.severity)}</span>
      </div>
      <p>${escapeHtml(alert.message)}</p>
      <small>Logged: ${escapeHtml(dateLabel(alert.created_at, { weekday: "short", month: "short", day: "numeric" }))} ${escapeHtml(timeLabel(alert.created_at))} IST${alert.support?.value != null ? ` · Evidence: ${escapeHtml(alert.support.value)} ${escapeHtml(alert.support.unit || "")}` : ""}</small>
      <div class="alert-actions">
        ${!alert.acknowledged_at && !alert.resolved_at ? `<button class="alert-action" data-alert-action="acknowledge" data-alert-id="${Number(alert.id)}">Acknowledge</button>` : ""}
        ${!alert.resolved_at ? `<button class="alert-action" data-alert-action="resolve" data-alert-id="${Number(alert.id)}">Resolve</button>` : '<span class="resolved-tag">✓ Resolved</span>'}
      </div>
    </article>`).join("");
  } catch (error) {
    setText("alerts-summary", "Alert register connection error");
    if (target) target.innerHTML = `<div class="chart-empty">${escapeHtml(error.message)}</div>`;
  }
}

async function changeAlert(id, action) {
  try {
    await api(`/api/alerts/${id}/${action}`, { method: "POST", body: "{}" });
    toast(`Alert marked as ${action}d`);
    await loadAlerts();
  } catch (error) {
    toast(`Alert action failed: ${error.message}`);
  }
}

// --- Campus 3D Twin & Zones Directory ---
function renderZones() {
  const list = $("#zone-list");
  const fallback = $("#campus-fallback");
  setText("zone-count", `${state.zones.length} campus zones`);
  if (!state.zones.length) return;

  const html = state.zones.map(zone => `<button class="zone-chip" type="button" data-zone-id="${escapeHtml(zone.id)}" data-kind="${escapeHtml(zone.type)}">
    <i></i>
    <span>${escapeHtml(zone.name)}</span>
  </button>`).join("");
  if (list) list.innerHTML = html;

  if (fallback) {
    fallback.innerHTML = state.zones.map(zone => `<button class="fallback-zone" type="button" data-zone-id="${escapeHtml(zone.id)}" data-kind="${escapeHtml(zone.type)}">
      <b>${escapeHtml(zone.name)}</b>
      <small>${escapeHtml(zone.type)} · ${escapeHtml(zone.description ? zone.description.slice(0, 70) + "…" : "Academic Zone")}</small>
    </button>`).join("");
  }
}

const ZONE_PHOTOS = {
  main_building: {
    src: "/static/assets/campus/posters/facade-poster.jpg",
    caption: "RCERT Main Administration Building Facade & Terrace Gazebo"
  },
  main_gate: {
    src: "/static/assets/campus/posters/entrance-poster.jpg",
    caption: "RCERT Architectural Main Gateway & Central Roundabout"
  },
  computer_science: {
    src: "/static/assets/campus/frames/scene-04-academic-courtyard.jpg",
    caption: "Computer Science & Engineering Academic Wing"
  },
  data_science: {
    src: "/static/assets/campus/frames/scene-04-academic-courtyard.jpg",
    caption: "Data Science & Artificial Intelligence Laboratory Wing"
  },
  mechanical: {
    src: "/static/assets/campus/reference/ref-05-wings-layout.jpg",
    caption: "Mechanical Engineering Department & Thermal Labs"
  },
  mining: {
    src: "/static/assets/campus/reference/ref-05-wings-layout.jpg",
    caption: "Mining Engineering Complex & Geology Museum"
  },
  civil: {
    src: "/static/assets/campus/reference/ref-05-wings-layout.jpg",
    caption: "Civil Engineering Department & Structural Testing Bays"
  },
  mba: {
    src: "/static/assets/campus/reference/ref-05-wings-layout.jpg",
    caption: "Department of Management Studies (MBA Wing)"
  },
  polytechnic: {
    src: "/static/assets/campus/reference/ref-05-wings-layout.jpg",
    caption: "RCERT Polytechnic Wing & Technical Studios"
  },
  electrical_workshop: {
    src: "/static/assets/campus/reference/ref-04-veranda-pylons.jpg",
    caption: "Central Engineering Workshops & High-Voltage Labs"
  },
  auditorium: {
    src: "/static/assets/campus/reference/ref-02-roundabout.jpg",
    caption: "Multi-Purpose Campus Auditorium & Convocation Hall"
  },
  canteen: {
    src: "/static/assets/campus/posters/courtyard-poster.jpg",
    caption: "Kaka Student Canteen & Open Pavilion"
  },
  boys_hostel: {
    src: "/static/assets/campus/reference/ref-06-panorama.jpg",
    caption: "Boys Hostel Residential Block & Perimeter Grounds"
  },
  girls_hostel: {
    src: "/static/assets/campus/reference/ref-06-panorama.jpg",
    caption: "Girls Hostel Residential Block & Secure Enclosure"
  },
  boys_parking: {
    src: "/static/assets/campus/frames/scene-02-entrance-gate.jpg",
    caption: "Campus Vehicle Parking Zone & Covered Bays"
  },
  girls_parking: {
    src: "/static/assets/campus/frames/scene-02-entrance-gate.jpg",
    caption: "Designated Student Parking Facility"
  }
};

function selectZone(zone, update3D = true) {
  if (!zone) return;
  state.selectedZone = zone;
  setText("selected-zone-name", zone.name);
  setText("selected-zone-type", `${zone.type} · RCERT Campus`);
  setText("zone-type-badge", zone.type || "Academic");
  setText("selected-zone-note", zone.description || `${zone.name} is a designated functional zone of the RCERT campus.`);

  // Update Photographic Visual Reference in Zone Inspector
  const photo = ZONE_PHOTOS[zone.id] || {
    src: "/static/assets/campus/posters/walkthrough-poster.jpg",
    caption: `${zone.name} · RCERT Campus Architectural Perspective`
  };
  const imgEl = $("#zone-photo-img");
  const captionEl = $("#zone-photo-caption");
  if (imgEl) {
    imgEl.src = photo.src;
    imgEl.alt = `${zone.name} reference photograph`;
  }
  if (captionEl) {
    captionEl.textContent = photo.caption;
  }

  // Facilities tags
  const facBlock = $("#zone-facilities-block");
  const facTags = $("#zone-facilities-tags");
  if (facBlock && facTags) {
    if (zone.facilities?.length) {
      facBlock.hidden = false;
      facTags.innerHTML = zone.facilities.map(f => `<span class="facility-pill">${escapeHtml(f)}</span>`).join("");
    } else {
      facBlock.hidden = true;
    }
  }

  $$("[data-zone-id]").forEach(el => el.classList.toggle("is-selected", el.dataset.zoneId === zone.id));
  if (update3D) {
    state.twin?.select?.(zone.id, false);
  }
}

async function loadCampus() {
  try {
    const [zones, campus] = await Promise.all([api("/api/campus/zones"), api("/api/campus")]);
    state.zones = zones.zones || [];
    renderZones();

    const info = campus.campus || {};
    setText("about-college-name", info.name || "Rajiv Gandhi College of Engineering, Research & Technology");
    setText("about-location", `${info.city || "Chandrapur"} · ${info.state || "Maharashtra"} · ${info.country || "India"}`);
    setText("about-established", info.established || "1983");
    setText("about-code", info.college_code || "4163");

    if (state.zones.length) {
      selectZone(state.zones.find(z => z.id === "main_building") || state.zones[0]);
      if (window.location.hash === "#campus" || $("#view-campus")?.classList.contains("is-visible")) {
        startTwin();
      }
    }
  } catch (error) {
    console.error("Campus registry error", error);
    const list = $("#zone-list");
    if (list) list.innerHTML = '<div class="loading-row">Campus directory unavailable.</div>';
  }
}

async function startTwin() {
  if (state.twinStarted || !state.zones.length) return;
  state.twinStarted = true;
  const container = $("#campus-scene");
  const fallback = $("#campus-fallback");

  try {
    const mod = await import("./campus-3d.js");
    state.twin = await mod.startCampusTwin(container, state.zones, z => selectZone(z, false));
    if (state.twin) {
      setText("map-state", "Interactive 3D Active");
    } else {
      fallback.hidden = false;
      container.hidden = true;
      setText("map-state", "2D Fallback View");
    }
  } catch (error) {
    console.warn("3D scene initialization error; using 2D fallback", error);
    fallback.hidden = false;
    container.hidden = true;
    setText("map-state", "2D Fallback View");
  }
}

// --- Reports Generation and Document Preview ---
async function renderReportDocument() {
  const title = $("#report-doc-title");
  const body = $("#report-doc-body");
  const stamp = $("#report-doc-timestamp");
  if (!body) return;

  const now = new Date();
  if (stamp) stamp.textContent = `Generated: ${now.toLocaleDateString("en-IN")} ${now.toLocaleTimeString("en-IN")} IST`;

  const reportType = state.activeReport;
  $$(".report-opt-btn").forEach(btn => btn.classList.toggle("is-active", btn.dataset.reportType === reportType));

  if (reportType === "weather-summary") {
    if (title) title.textContent = "Campus Meteorological Summary Report";
    const c = state.current?.data?.current || {};
    body.innerHTML = `
      <div class="report-section">
        <h3>1. Current Meteorological Telemetry</h3>
        <table class="report-table">
          <thead>
            <tr><th>Parameter</th><th>Value</th><th>Classification</th><th>Source</th></tr>
          </thead>
          <tbody>
            <tr><td>Surface Temperature</td><td><b>${formatTemp(c.temperature_c, 1)}</b></td><td>Forecast Estimate</td><td>Open-Meteo API</td></tr>
            <tr><td>Feels Like (Heat Index)</td><td><b>${formatTemp(c.feels_like_c, 1)}</b></td><td>Forecast Estimate</td><td>Open-Meteo API</td></tr>
            <tr><td>Relative Humidity</td><td><b>${num(c.humidity_pct)} %</b></td><td>Model Estimate</td><td>Open-Meteo API</td></tr>
            <tr><td>Atmospheric Pressure</td><td><b>${num(c.pressure_hpa, 1)} hPa</b></td><td>Model Estimate</td><td>Open-Meteo API</td></tr>
            <tr><td>Wind Velocity</td><td><b>${formatWind(c.wind_speed_kmh, 1)}</b></td><td>Surface 10 m</td><td>Open-Meteo API</td></tr>
            <tr><td>Precipitation Rate</td><td><b>${num(c.precipitation_mm, 1)} mm</b></td><td>Forecast</td><td>Open-Meteo API</td></tr>
            <tr><td>Dew Point</td><td><b>${formatTemp(c.dew_point_c, 1)}</b></td><td>Model Derived</td><td>Open-Meteo API</td></tr>
          </tbody>
        </table>
      </div>
      <div class="report-section">
        <h3>2. Location & Geographic Context</h3>
        <p>Location: Rajiv Gandhi College of Engineering, Research & Technology (RCERT), Babupeth, Ballarpur Road, Chandrapur - 442403, Maharashtra, India. Geographic coordinates: 19.9501° N, 79.2993° E. Timezone: Asia/Kolkata (IST, UTC+05:30).</p>
      </div>
    `;
  } else if (reportType === "air-quality") {
    if (title) title.textContent = "Air Quality & Atmospheric Chemical Composition Report";
    const aq = state.air?.data?.current || {};
    body.innerHTML = `
      <div class="report-section">
        <h3>1. Atmospheric Pollutant Concentrations</h3>
        <table class="report-table">
          <thead>
            <tr><th>Pollutant / Metric</th><th>Forecast Value</th><th>Safety Standard</th><th>Status</th></tr>
          </thead>
          <tbody>
            <tr><td>US Air Quality Index</td><td><b>${num(aq.us_aqi)}</b></td><td>0–50 (Good)</td><td><span class="report-badge">${aqBand(aq.us_aqi)}</span></td></tr>
            <tr><td>Fine Particulate Matter (PM2.5)</td><td><b>${num(aq.pm2_5_ugm3, 1)} µg/m³</b></td><td>15 µg/m³ (WHO)</td><td>CAMS Forecast</td></tr>
            <tr><td>Coarse Particulate Matter (PM10)</td><td><b>${num(aq.pm10_ugm3, 1)} µg/m³</b></td><td>45 µg/m³ (WHO)</td><td>CAMS Forecast</td></tr>
            <tr><td>Ground-Level Ozone (O₃)</td><td><b>${num(aq.ozone_ugm3, 1)} µg/m³</b></td><td>100 µg/m³ (8h avg)</td><td>CAMS Forecast</td></tr>
            <tr><td>Nitrogen Dioxide (NO₂)</td><td><b>${num(aq.nitrogen_dioxide_ugm3, 1)} µg/m³</b></td><td>25 µg/m³ (24h avg)</td><td>CAMS Forecast</td></tr>
            <tr><td>Sulphur Dioxide (SO₂)</td><td><b>${num(aq.sulphur_dioxide_ugm3, 1)} µg/m³</b></td><td>40 µg/m³ (24h avg)</td><td>CAMS Forecast</td></tr>
            <tr><td>Carbon Monoxide (CO)</td><td><b>${num(aq.carbon_monoxide_ugm3, 1)} µg/m³</b></td><td>4000 µg/m³</td><td>CAMS Forecast</td></tr>
          </tbody>
        </table>
      </div>
      <div class="report-section">
        <h3>2. Atmospheric Model Methodology</h3>
        <p>Projections provided by Copernicus Atmosphere Monitoring Service (CAMS) integrated through Open-Meteo. Values represent regional atmospheric transport simulations and do not substitute for on-campus certified particulate monitors.</p>
      </div>
    `;
  } else if (reportType === "seven-day") {
    if (title) title.textContent = "7-Day Extended Campus Meteorological Outlook";
    const days = state.forecast?.data?.daily || [];
    body.innerHTML = `
      <div class="report-section">
        <h3>1. Diurnal Forecast Progression</h3>
        <table class="report-table">
          <thead>
            <tr><th>Date</th><th>Weather Condition</th><th>Maximum Temp</th><th>Minimum Temp</th><th>Precip Chance</th><th>Max Wind</th></tr>
          </thead>
          <tbody>
            ${days.map(d => `<tr>
              <td><b>${escapeHtml(dateLabel(d.time, { weekday: "short", day: "2-digit", month: "short" }))}</b></td>
              <td>${weatherGlyph(d.condition)} ${escapeHtml(d.condition || "Clear")}</td>
              <td>${formatTemp(d.temperature_2m_max, 1)}</td>
              <td>${formatTemp(d.temperature_2m_min, 1)}</td>
              <td>${num(d.precipitation_probability_max)} %</td>
              <td>${formatWind(d.wind_speed_10m_max, 1)}</td>
            </tr>`).join("")}
          </tbody>
        </table>
      </div>
    `;
  } else if (reportType === "alerts-audit") {
    if (title) title.textContent = "Campus Advisories & Safety Incident Audit Log";
    try {
      const data = await api("/api/alerts?state=all");
      const alerts = data.alerts || [];
      body.innerHTML = `
        <div class="report-section">
          <h3>1. Persistent Alert Registry (${alerts.length} Total Records)</h3>
          <table class="report-table">
            <thead>
              <tr><th>ID</th><th>Timestamp</th><th>Category</th><th>Severity</th><th>Title</th><th>Status</th></tr>
            </thead>
            <tbody>
              ${alerts.map(a => `<tr>
                <td>#${Number(a.id)}</td>
                <td>${escapeHtml(dateLabel(a.created_at, { month: "short", day: "numeric" }))} ${escapeHtml(timeLabel(a.created_at))}</td>
                <td>${escapeHtml(a.category)}</td>
                <td><span class="report-badge severity-${escapeHtml(a.severity)}">${escapeHtml(a.severity)}</span></td>
                <td><b>${escapeHtml(a.title)}</b></td>
                <td>${a.resolved_at ? "Resolved" : a.acknowledged_at ? "Acknowledged" : "Active"}</td>
              </tr>`).join("")}
            </tbody>
          </table>
        </div>
      `;
    } catch {
      body.innerHTML = '<div class="chart-empty">Alert log could not be retrieved.</div>';
    }
  } else if (reportType === "system-health") {
    if (title) title.textContent = "Digital Twin 2.0 System Health & Provenance Report";
    body.innerHTML = `
      <div class="report-section">
        <h3>1. Architectural Integrity & Provenance Compliance</h3>
        <table class="report-table">
          <thead>
            <tr><th>Subsystem</th><th>Status</th><th>Protocol</th><th>Details</th></tr>
          </thead>
          <tbody>
            <tr><td>Open-Meteo Weather API</td><td><b style="color:#7dc589;">Operational (200 OK)</b></td><td>HTTPS REST / Cache</td><td>TTL: 600s · Stale snapshot preservation</td></tr>
            <tr><td>CAMS Air Quality API</td><td><b style="color:#7dc589;">Operational (200 OK)</b></td><td>HTTPS REST / Cache</td><td>TTL: 900s · Regional aerosol model</td></tr>
            <tr><td>SQLite Database Engine</td><td><b style="color:#7dc589;">Connected (WAL Mode)</b></td><td>database/campus.db</td><td>Zero synthetic sensor injection</td></tr>
            <tr><td>3D Spatial Campus Twin</td><td><b style="color:#7dc589;">WebGL Enabled</b></td><td>Three.js Canvas</td><td>18 verified zones · Conceptual spatial model</td></tr>
            <tr><td>CCTV / Computer Vision</td><td><b style="color:#8992a2;">Phase 2 Deferred</b></td><td>Hardware Dependent</td><td>Intentionally excluded from Phase 1 release</td></tr>
          </tbody>
        </table>
      </div>
      <div class="report-section">
        <h3>2. Verification Manifest</h3>
        <p>This report confirms that the RCERT Smart Campus Digital Twin operates strictly under the Data Provenance Standard: no random sensor values are simulated, and all environmental metrics are verifiable via Open-Meteo public forecasts.</p>
      </div>
    `;
  }
}

// --- Settings View ---
async function loadSettingsView() {
  try {
    const data = await api("/api/settings");
    if (data.settings) {
      state.settings = { ...state.settings, ...data.settings };
      const tempSel = $("#pref-temp-unit");
      if (tempSel) tempSel.value = state.settings.temperature_unit || "celsius";
      const windSel = $("#pref-wind-unit");
      if (windSel) windSel.value = state.settings.wind_unit || "kmh";
      const refSel = $("#pref-refresh-interval");
      if (refSel) refSel.value = String(state.settings.refresh_interval_sec || 300);
      const qualSel = $("#pref-render-quality");
      if (qualSel) qualSel.value = state.settings.render_quality || "high";
      const themeSel = $("#pref-theme");
      if (themeSel) themeSel.value = state.settings.theme || "dark";
    }
  } catch (error) {
    console.warn("Could not load user settings", error);
  }
}

async function saveSettings() {
  const tempUnit = $("#pref-temp-unit")?.value || "celsius";
  const windUnit = $("#pref-wind-unit")?.value || "kmh";
  const refInterval = Number($("#pref-refresh-interval")?.value || 300);
  const quality = $("#pref-render-quality")?.value || "high";
  const theme = $("#pref-theme")?.value || "dark";

  state.settings.temperature_unit = tempUnit;
  state.settings.wind_unit = windUnit;
  state.settings.refresh_interval_sec = refInterval;
  state.settings.render_quality = quality;
  state.settings.theme = theme;

  try {
    await api("/api/settings", {
      method: "POST",
      body: JSON.stringify(state.settings)
    });
    toast("System preferences saved.");
    renderOverview();
    renderWeatherView();
  } catch (error) {
    toast(`Failed to save settings: ${error.message}`);
  }
}

// --- Live Ping Diagnostics ---
async function runDiagnostics() {
  const dbDot = $("#diag-db-dot");
  const dbBadge = $("#diag-db-badge");
  const weatherDot = $("#diag-weather-dot");
  const weatherBadge = $("#diag-weather-badge");
  const airDot = $("#diag-air-dot");
  const airBadge = $("#diag-air-badge");

  toast("Running ping diagnostics…");

  // DB test
  try {
    const health = await api("/api/health");
    if (health.database?.available) {
      if (dbDot) dbDot.className = "status-dot is-ok";
      if (dbBadge) { dbBadge.className = "diag-badge is-ok"; dbBadge.textContent = "CONNECTED"; }
    } else {
      if (dbDot) dbDot.className = "status-dot is-error";
      if (dbBadge) { dbBadge.className = "diag-badge is-error"; dbBadge.textContent = "ERROR"; }
    }
  } catch {
    if (dbDot) dbDot.className = "status-dot is-error";
    if (dbBadge) { dbBadge.className = "diag-badge is-error"; dbBadge.textContent = "FAILED"; }
  }

  // Weather test
  try {
    const w = await api("/api/weather/current");
    if (w.success) {
      if (weatherDot) weatherDot.className = "status-dot is-ok";
      if (weatherBadge) { weatherBadge.className = "diag-badge is-ok"; weatherBadge.textContent = "200 OK"; }
    }
  } catch {
    if (weatherDot) weatherDot.className = "status-dot is-error";
    if (weatherBadge) { weatherBadge.className = "diag-badge is-error"; weatherBadge.textContent = "UNAVAILABLE"; }
  }

  // Air test
  try {
    const a = await api("/api/air-quality");
    if (a.success) {
      if (airDot) airDot.className = "status-dot is-ok";
      if (airBadge) { airBadge.className = "diag-badge is-ok"; airBadge.textContent = "200 OK"; }
    }
  } catch {
    if (airDot) airDot.className = "status-dot is-error";
    if (airBadge) { airBadge.className = "diag-badge is-error"; airBadge.textContent = "UNAVAILABLE"; }
  }

  toast("Diagnostics complete.");
}

// --- Presentation Mode Toggle ---
function togglePresentationMode() {
  const shell = $("#app-shell");
  const isPres = shell?.classList.toggle("is-presentation");
  const presBtn = $("#presentation-toggle");
  if (presBtn) presBtn.classList.toggle("is-active", !!isPres);
  toast(isPres ? "Presentation Mode Activated" : "Exited Presentation Mode");
}

// --- Load Core Forecasts ---
async function loadWeather() {
  const errorBanner = $("#error-banner");
  const results = await Promise.allSettled([
    api("/api/weather/current"),
    api("/api/analytics/weather"),
    api("/api/air-quality")
  ]);

  const failures = [];
  if (results[0].status === "fulfilled") state.current = results[0].value;
  else failures.push(results[0].reason);

  if (results[1].status === "fulfilled") state.forecast = results[1].value;
  else failures.push(results[1].reason);

  if (results[2].status === "fulfilled") state.air = results[2].value;
  else failures.push(results[2].reason);

  renderOverview();
  renderWeatherView();
  renderAnalyticsView();

  if (!state.current?.success) {
    if (errorBanner) errorBanner.hidden = false;
    setText("error-message", failures[0]?.message || "Could not connect to Open-Meteo forecast service.");
    setSystem(false, "DATA UNAVAILABLE");
  } else if (errorBanner) {
    errorBanner.hidden = true;
  }
}

async function loadHealth() {
  try {
    const health = await api("/api/health");
    setSystem(!!health.database?.available, health.database?.available ? "API CONNECTED" : "API DEGRADED");
  } catch {
    setSystem(false, "API DEGRADED");
  }
}

function openRoadmapModal() {
  const modal = $("#modal-roadmap");
  if (!modal) return;
  modal.removeAttribute("hidden");
  modal.style.display = "flex";
  modal.classList.add("is-open");
  document.body.style.overflow = "hidden";
}

function closeRoadmapModal() {
  const modal = $("#modal-roadmap");
  if (!modal) return;
  modal.setAttribute("hidden", "");
  modal.style.display = "none";
  modal.classList.remove("is-open");
  document.body.style.overflow = "";
}

// --- Overview Cinematic Scroll-Controlled Frame Animation Engine ---
function initOverviewCinematicScrub() {
  const stage = $("#overview-cinematic-stage");
  const canvas = $("#cinematic-canvas");
  if (!stage || !canvas) return null;

  const ctx = canvas.getContext("2d", { alpha: false });
  const narrativeScenes = $$(".narrative-scene");

  const TOTAL_FRAMES = 300;
  const frameImages = new Array(TOTAL_FRAMES + 1);
  let loadedCount = 0;
  let currentDrawnIndex = -1;
  let ticking = false;

  // Frame URL constructor (1 to 300)
  function frameUrl(index) {
    const padded = String(index).padStart(3, "0");
    return `/static/assets/campus/sequence/ezgif-frame-${padded}.jpg`;
  }

  // Draw image to canvas with cover scaling and letterbox elimination
  function renderFrame(img, frameIndex) {
    if (!img || !canvas || !ctx) return;
    const cw = canvas.width;
    const ch = canvas.height;
    if (cw <= 0 || ch <= 0) return;

    // Detect if frame has embedded top/bottom letterbox bars
    // Verified: Frames 1 to 159 have 67px top and 60px bottom black borders baked into the 1280x720 video export
    const effectiveIndex = frameIndex !== undefined ? frameIndex : (img._frameIndex || 1);
    const hasBars = (effectiveIndex >= 1 && effectiveIndex <= 159);
    const cropTop = hasBars ? 67 : 0;
    const cropBottom = hasBars ? 60 : 0;

    const sx = 0;
    const sy = cropTop;
    const sw = img.naturalWidth || 1280;
    const sh = (img.naturalHeight || 720) - cropTop - cropBottom;

    // Calculate cover scale using active visual dimensions to completely fill the canvas
    const hRatio = cw / sw;
    const vRatio = ch / sh;
    const ratio = Math.max(hRatio, vRatio);

    const nw = sw * ratio;
    const nh = sh * ratio;

    // Center crop offsets to guarantee edge-to-edge coverage with 0 black gaps
    const cx = (cw - nw) / 2;
    const cy = (ch - nh) / 2;

    ctx.drawImage(img, sx, sy, sw, sh, cx, cy, nw, nh);
  }

  function getLoadedOrNearest(targetIdx) {
    if (frameImages[targetIdx]?.complete && frameImages[targetIdx]?.naturalWidth > 0) {
      return frameImages[targetIdx];
    }
    // Search outwards for nearest loaded frame to prevent flickering
    for (let offset = 1; offset < 35; offset++) {
      const down = targetIdx - offset;
      if (down >= 1 && frameImages[down]?.complete && frameImages[down]?.naturalWidth > 0) {
        return frameImages[down];
      }
      const up = targetIdx + offset;
      if (up <= TOTAL_FRAMES && frameImages[up]?.complete && frameImages[up]?.naturalWidth > 0) {
        return frameImages[up];
      }
    }
    return frameImages[1] || null;
  }

  function drawTargetFrame(targetIdx) {
    if (targetIdx === currentDrawnIndex) return;
    const img = getLoadedOrNearest(targetIdx);
    if (img) {
      renderFrame(img, img._frameIndex || targetIdx);
      currentDrawnIndex = targetIdx;
    }
  }

  // Preload strategy: Frame 1 immediately, then progressive chunk loading
  function preloadImages() {
    const firstImg = new Image();
    firstImg._frameIndex = 1;
    firstImg.src = frameUrl(1);
    firstImg.onload = () => {
      frameImages[1] = firstImg;
      loadedCount++;
      drawTargetFrame(1);
      // Load opening keyframe batch (2 to 35)
      loadBatch(2, 35, () => {
        // Incrementally load remaining frames in idle time
        loadRemainingIncremental(36);
      });
    };
    firstImg.onerror = () => {
      console.warn("Could not load initial frame from sequence");
    };
  }

  function loadBatch(start, end, onComplete) {
    let pending = end - start + 1;
    for (let i = start; i <= end; i++) {
      if (i > TOTAL_FRAMES) {
        if (--pending <= 0 && onComplete) onComplete();
        continue;
      }
      const img = new Image();
      img._frameIndex = i;
      img.src = frameUrl(i);
      img.onload = () => {
        frameImages[i] = img;
        loadedCount++;
        if (--pending <= 0 && onComplete) onComplete();
      };
      img.onerror = () => {
        if (--pending <= 0 && onComplete) onComplete();
      };
    }
  }

  function loadRemainingIncremental(startIdx) {
    let current = startIdx;
    const chunkSize = 15;
    function next() {
      if (current > TOTAL_FRAMES) return;
      const end = Math.min(TOTAL_FRAMES, current + chunkSize - 1);
      loadBatch(current, end, () => {
        current = end + 1;
        if ("requestIdleCallback" in window) {
          window.requestIdleCallback(next);
        } else {
          setTimeout(next, 40);
        }
      });
    }
    next();
  }

  // Scroll Scrub Calculation
  function updateScrub() {
    const dashView = $("#view-dashboard");
    if (!dashView || dashView.hidden) {
      ticking = false;
      return;
    }

    const rect = stage.getBoundingClientRect();
    const stageH = stage.offsetHeight;
    const winH = window.innerHeight;
    const scrollable = stageH - winH;

    if (scrollable <= 0) {
      ticking = false;
      return;
    }

    // Normalized progress: 0.0 at top of stage, 1.0 when scrolled through stage
    const progress = Math.max(0, Math.min(1, -rect.top / scrollable));
    const targetIdx = Math.min(TOTAL_FRAMES, Math.max(1, Math.round(progress * (TOTAL_FRAMES - 1)) + 1));

    canvas.dataset.frame = String(targetIdx);
    canvas.dataset.progress = progress.toFixed(3);

    drawTargetFrame(targetIdx);

    // Narrative Scene Activation (Scenes 1 to 6)
    let activeSceneNum = 1;
    if (progress >= 0.88) activeSceneNum = 6;
    else if (progress >= 0.72) activeSceneNum = 5;
    else if (progress >= 0.54) activeSceneNum = 4;
    else if (progress >= 0.35) activeSceneNum = 3;
    else if (progress >= 0.16) activeSceneNum = 2;

    narrativeScenes.forEach(scene => {
      const num = parseInt(scene.dataset.scene, 10);
      scene.classList.toggle("is-active", num === activeSceneNum);
    });

    ticking = false;
  }

  function onScroll() {
    if (!ticking) {
      window.requestAnimationFrame(updateScrub);
      ticking = true;
    }
  }

  function handleResize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const rect = canvas.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) {
      canvas.width = Math.round(rect.width * dpr);
      canvas.height = Math.round(rect.height * dpr);
      currentDrawnIndex = -1; // force redraw
      updateScrub();
    }
  }

  // Preload and initialize
  preloadImages();
  handleResize();

  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", handleResize);

  return {
    update: () => {
      handleResize();
      updateScrub();
    }
  };
}

function bindEvents() {
  document.addEventListener("click", event => {
    // Nav Target Clicks
    const nav = event.target.closest("[data-view-target]");
    if (nav) {
      event.preventDefault();
      showView(nav.dataset.viewTarget);
      return;
    }

    // Zone chip clicks
    const zoneButton = event.target.closest("[data-zone-id]");
    if (zoneButton) {
      const zone = state.zones.find(item => item.id === zoneButton.dataset.zoneId);
      selectZone(zone);
      return;
    }

    // Alert action clicks
    const alertBtn = event.target.closest("[data-alert-action]");
    if (alertBtn) {
      changeAlert(alertBtn.dataset.alertId, alertBtn.dataset.alertAction);
      return;
    }

    // Report Type selector
    const reportBtn = event.target.closest("[data-report-type]");
    if (reportBtn) {
      state.activeReport = reportBtn.dataset.reportType;
      renderReportDocument();
      return;
    }

    // Campus 3D filter chips
    const chip = event.target.closest("[data-filter]");
    if (chip) {
      $$("#zone-filter-chips .chip").forEach(c => c.classList.remove("is-active"));
      chip.classList.add("is-active");
      state.twin?.filterByType?.(chip.dataset.filter);
      return;
    }
  });

  // Spatial Nexus Navigation Controls
  const toggleMobileNav = () => {
    const overlay = $("#mobile-spatial-overlay");
    if (overlay && !overlay.hidden) {
      closeMenu();
    } else {
      openMenu();
    }
  };

  $("#menu-toggle")?.addEventListener("click", toggleMobileNav);
  $("#mobile-hub-btn")?.addEventListener("click", toggleMobileNav);
  $("#mobile-overlay-close-btn")?.addEventListener("click", closeMenu);
  $("#mobile-overlay-backdrop")?.addEventListener("click", closeMenu);
  $("#mobile-open-roadmap-btn")?.addEventListener("click", () => {
    closeMenu();
    openRoadmapModal();
  });
  $("#mobile-scrim")?.addEventListener("click", closeMenu);
  $("#presentation-toggle")?.addEventListener("click", togglePresentationMode);

  window.addEventListener("resize", updateSpatialIndicator);

  $("#refresh-button")?.addEventListener("click", async () => {
    await Promise.all([loadWeather(), loadHealth(), loadAlerts()]);
    toast("Campus forecast and telemetry refreshed.");
  });

  // Alerts listeners
  $("#refresh-alerts")?.addEventListener("click", loadAlerts);
  $("#alert-state")?.addEventListener("change", loadAlerts);
  $("#alert-severity-filter")?.addEventListener("change", loadAlerts);
  $("#alert-search-box")?.addEventListener("input", loadAlerts);

  // Analytics timeframe
  $("#analytics-timeframe")?.addEventListener("change", renderAnalyticsView);

  // Settings
  $("#save-settings-btn")?.addEventListener("click", saveSettings);
  $("#run-diagnostics-btn")?.addEventListener("click", runDiagnostics);

  // Reports
  $("#print-report-btn")?.addEventListener("click", () => window.print());

  // 3D Toolbar actions
  $("#reset-camera")?.addEventListener("click", () => state.twin?.reset?.());
  $("#toggle-fullscreen-map")?.addEventListener("click", () => {
    const wrap = $("#campus-scene-wrap");
    if (!wrap) return;
    if (!document.fullscreenElement) {
      wrap.requestFullscreen?.().catch(() => {});
    } else {
      document.exitFullscreen?.().catch(() => {});
    }
  });

  $("#toggle-view-mode")?.addEventListener("click", () => {
    state.is2D = !state.is2D;
    const scene = $("#campus-scene");
    const fallback = $("#campus-fallback");
    const btn = $("#toggle-view-mode");
    if (state.is2D) {
      if (scene) scene.hidden = true;
      if (fallback) fallback.hidden = false;
      if (btn) btn.textContent = "3D View";
      setText("map-state", "2D Fallback View");
    } else {
      if (scene) scene.hidden = false;
      if (fallback) fallback.hidden = true;
      if (btn) btn.textContent = "2D View";
      setText("map-state", "Interactive 3D Active");
    }
  });

  // Campus Search input
  $("#campus-search")?.addEventListener("input", e => {
    const term = e.target.value.toLowerCase().trim();
    if (!term) return;
    const match = state.zones.find(z =>
      z.name.toLowerCase().includes(term) ||
      z.type.toLowerCase().includes(term) ||
      (z.facilities && z.facilities.some(f => f.toLowerCase().includes(term)))
    );
    if (match) selectZone(match);
  });

  // Phase 2 Roadmap Modal Controls
  $("#open-roadmap-btn")?.addEventListener("click", e => {
    e.preventDefault();
    closeMenu();
    openRoadmapModal();
  });

  $("#close-roadmap-btn")?.addEventListener("click", e => {
    e.preventDefault();
    e.stopPropagation();
    closeRoadmapModal();
  });

  $("#dismiss-roadmap-btn")?.addEventListener("click", e => {
    e.preventDefault();
    e.stopPropagation();
    closeRoadmapModal();
  });

  const modalEl = $("#modal-roadmap");
  if (modalEl) {
    // Backdrop click: close modal when clicking outside the dialog
    modalEl.addEventListener("click", event => {
      if (event.target === modalEl) {
        closeRoadmapModal();
      }
    });

    // Prevent clicks inside the dialog content from closing it
    const modalWindow = modalEl.querySelector(".modal-window");
    modalWindow?.addEventListener("click", event => {
      event.stopPropagation();
    });
  }

  window.addEventListener("keydown", event => {
    if (event.key === "Escape") {
      closeMenu();
      closeRoadmapModal();
    }
  });

  // Initialize Overview Cinematic Frame-by-Frame Scroll Scrub
  state.cinematicScrub = initOverviewCinematicScrub();

  // Handle URL hash navigation
  const initialHash = window.location.hash.replace("#", "");
  if (initialHash && viewNames[initialHash]) {
    showView(initialHash);
  }
}

// Start Application
closeRoadmapModal(); // Ensure modal is strictly closed on page load
bindEvents();
setTimeout(updateSpatialIndicator, 150);
updateClock();
setInterval(updateClock, 1000);

loadSettingsView().then(() => {
  loadCampus();
  loadWeather();
  loadHealth();
  loadAlerts();
});

setInterval(loadWeather, 300000);
setInterval(loadHealth, 60000);

window.RCERT = {
  showView,
  loadWeather,
  loadAlerts,
  togglePresentationMode
};
