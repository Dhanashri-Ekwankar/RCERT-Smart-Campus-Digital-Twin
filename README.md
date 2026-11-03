# RCERT Smart Campus Digital Twin

> **Presentation build · Local Flask application · Data-source-first design**

A campus intelligence dashboard for Rajiv Gandhi College of Engineering, Research & Technology (RCERT), Chandrapur. The application combines location-aware weather and air-quality forecasts, a conceptual campus twin, transparent camera analytics, and persistent incident handling. It is designed to remain useful without IoT devices or a camera.

## What it is — and what it is not

- **Weather intelligence:** Open-Meteo current-condition estimates, hourly forecasts, daily forecasts, and CAMS-derived air-quality forecasts for RCERT (19.9501° N, 79.2993° E; `Asia/Kolkata`). These are model-based forecasts, not readings from instruments installed on campus.
- **Hardware-independent architecture:** The application is engineered to operate 100% independently of physical meters, ESP32 microcontrollers, or physical sensors.
- **Campus twin:** An interactive, conceptual 3D spatial visualization of the 18 RCERT campus zones using Three.js.
- **Phase 2 CCTV deferral:** CCTV streaming, YOLO computer vision, and facial analysis are intentionally reserved for Phase 2 hardware rollout. The current Phase 1 release operates independently of all video and camera hardware.
- **Legacy data:** `dataset/campus_sensor_data.csv`, the old `sensor_readings` table, and the bundled scikit-learn models are synthetic-project artifacts. They are preserved for reproducibility and are excluded from active weather intelligence and analytics.

## Features

### Campus Intelligence

- Current temperature, apparent temperature, humidity, dew point, pressure, wind, gusts, clouds, rainfall, visibility, UV, sunrise, and sunset when returned by the provider.
- Hourly weather forecast and seven-day daily forecast; rainfall, humidity, wind, temperature, and UV visualizations.
- PM2.5, PM10, US/EU AQI, dust, ozone, nitrogen dioxide, sulphur dioxide, and carbon monoxide forecasts where returned by Open-Meteo.
- Evidence-linked insights show their supporting value, time window, source, and forecast classification.
- Weather requests are cached. On failure, a last successful response is returned with `stale: true`; if no cached response exists the UI shows unavailable rather than generated values.
- Open-Meteo attribution is displayed near forecast data.

### Optional Vision Intelligence

- Browser webcam and uploaded-video workflows are user initiated; no camera starts on page load.
- YOLO11n ONNX person detections are returned by the inference API and are the only source for bounding boxes. Missing model/runtime errors are displayed rather than replaced by decorative detections.
- A configurable virtual line records observed entry/exit crossings using short-lived tracking IDs, with duplicate suppression.
- Only minimal anonymous event metadata is persisted. Detection frames are processed transiently and are not stored.
- Demo mode, if used, is separately labeled and does not submit demonstration events to the actual event API.

### Analytics and Alerts

- Footfall summaries are based only on actual validated camera events; weather analysis is based only on provider forecasts.
- Time filters and CSV export operate on the selected source and date range.
- Weather/camera alerts are backed by a value, timestamp, and source. Acknowledge and resolve actions are persisted in SQLite.
- Stale camera status is shown as stale rather than LIVE.

### RCERT Information

The About view uses verified institutional facts and links to the official site. The official RCERT website identifies the college as established in 1983, lists college code 4163, and identifies Chandrapur. Other statistics or claims should be added only after verification from an official source.

## Run locally on Windows

From PowerShell or Command Prompt:

```powershell
cd "C:\Users\samya\Downloads\FINAL YEAR PROJECT zip\FINAL YEAR PROJECT\RCERT_SMART_CAMPUS_FINAL"
uv venv .venv --python 3.14
uv pip install --python .venv\Scripts\python.exe -r requirements.txt -r requirements-dev.txt
.venv\Scripts\python.exe app.py
```

Open **http://127.0.0.1:5001/**. The Flask development server is bound to loopback with debug mode and reloader disabled; it is intended for a local demo, not public production hosting.

If `.venv` already exists, reuse it rather than recreating it. To stop the server, press `Ctrl+C` in its terminal.

### YOLO model

The optional vision page requires the YOLO11n ONNX asset at `models/yolo11n.onnx`, plus ONNX Runtime and Pillow from `requirements.txt`. The model is sourced from the official Ultralytics assets release. If the model is absent or cannot load, the API returns an unavailable/error state and the page must not imply detections are running. Model files are not retrained by the application.

## Test and verify

```powershell
.venv\Scripts\python.exe -m pytest -q --basetemp .pytest-tmp
```

The automated tests cover API shapes, weather normalization/cache/stale behavior, source labeling, event validation and duplicate crossing suppression, alert persistence, camera config persistence, and safe preservation of legacy database rows. A browser smoke check should additionally exercise navigation, weather refresh/failure states, campus selection/3D fallback, CSV export, alert controls, and responsive widths.

Camera inference requires an available camera or uploaded video. The app never requests camera access until the user starts a session; test with consent and do not connect a CCTV stream unless authorized.

## API reference

| Method | Endpoint | Purpose / classification |
|---|---|---|
| `GET` | `/api/health` | Database, provider, and vision-model availability |
| `GET` | `/api/weather/current` | Open-Meteo current-condition estimate (`forecast`) |
| `GET` | `/api/weather/forecast` | Hourly and daily weather forecast (`forecast`) |
| `GET` | `/api/air-quality` | CAMS air-quality forecast (`forecast_estimate`) |
| `GET` | `/api/campus` | Official campus identity and location |
| `GET` | `/api/campus/zones` | Campus zone list; geometry is conceptual |
| `GET` | `/api/analytics/summary` | Weather + actual anonymous movement summary, with source flags |
| `GET` | `/api/analytics/footfall` | Time-filtered actual camera entry/exit events |
| `GET` | `/api/analytics/weather` | Forecast charts/insights with provider source and stale state |
| `GET` | `/api/analytics/export.csv` | CSV export of actual anonymous footfall events |
| `GET` | `/api/alerts` | Persistent alerts with category/severity/state filters |
| `POST` | `/api/alerts/{id}/acknowledge` | Persist acknowledgement |
| `POST` | `/api/alerts/{id}/resolve` | Persist resolution |
| `GET` | `/api/cameras/status` | Browser-reported camera status; old connected status becomes stale |
| `POST` | `/api/cameras/connect` | Record a browser camera session after permission/start succeeds |
| `POST` | `/api/cameras/stop` | Record camera stop |
| `POST` | `/api/vision/config` | Validate and persist confidence/zone/virtual-line settings |
| `POST` | `/api/vision/infer` | Actual YOLO11n inference on a transient JPEG frame; no frame storage |
| `POST` | `/api/vision/events` | Validated anonymous entry/exit events; rejects images/demo/person fields |
| `GET` | `/api/vision/events` | Anonymous actual event history |
| `GET` | `/api/vision/summary` | Counts derived from actual event records only |
| `POST` | `/api/iot-data` | Optional, validated actual IoT measurement ingestion; absent fields remain absent |
| `GET` | `/api/history` | Separate actual IoT records and source-labeled legacy rows |
| `POST` | `/api/simulate-reading` | Retired legacy simulator; returns HTTP 410 |

All API payloads carry a source, timestamp, and data classification where applicable. The old `/api/latest-data` and `/api/analytics` paths remain compatibility aliases but do not feed synthetic readings into the new dashboard.

## Database and data stewardship

SQLite is kept at `database/campus.db`. Startup uses additive `CREATE TABLE IF NOT EXISTS` migrations and preserves the existing `sensor_readings` rows. New tables store weather snapshots, actual IoT measurements with missing values left `NULL`, anonymous vision events, cameras/configuration, and persistent alerts. No camera frames or biometric attributes are persisted.

The dataset generator and legacy training script can overwrite their synthetic CSV/model artifacts when run manually; **do not run those scripts as part of normal application startup**. The web app does not train models or seed synthetic sensor records.

## External sources and attribution

- Weather / forecast: [Open-Meteo Forecast API](https://open-meteo.com/en/docs)
- Air quality: [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api)
- Data license and attribution: [Open-Meteo license](https://open-meteo.com/en/license)
- Institutional information: [RCERT official website](https://www.rcert.ac.in/)
- YOLO model asset: [Ultralytics YOLO11 release assets](https://github.com/ultralytics/assets/releases/tag/v8.3.0)

Open-Meteo’s free service is for non-commercial use and its CC BY 4.0 data requires attribution. Verify current terms before using the app for anything commercial or public-facing.

## Known limitations

- Weather and air-quality values are forecast/model estimates, not on-campus sensors.
- No authorized RTSP URL or CCTV credentials are included; browser camera or uploaded video is the supported opt-in demonstration path.
- Campus 3D geometry is conceptual until an authoritative plan or verified building coordinates are supplied.
- Camera-derived counts cover only the configured camera view; they are not campus-wide occupancy without suitable entrance coverage and a baseline.
- The bundled old energy/occupancy ML models were trained on synthetic data and are intentionally not used for live intelligence.
