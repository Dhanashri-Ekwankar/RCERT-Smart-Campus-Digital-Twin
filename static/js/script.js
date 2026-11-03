// ============================================================
// RCERT SMART CAMPUS DIGITAL TWIN
// FINAL WORKING FRONTEND CONTROLLER
// ============================================================

console.log("RCERT SMART CAMPUS JS LOADED");

let latestData = null;

let temperatureChart = null;
let occupancyChart = null;
let electricityChart = null;
let waterChart = null;


// ============================================================
// CLOCK
// ============================================================

function updateClock() {
    const clock = document.getElementById("clock");
    const dateBox = document.getElementById("date");

    const now = new Date();

    if (clock) {
        clock.textContent = now.toLocaleTimeString("en-IN", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit"
        });
    }

    if (dateBox) {
        dateBox.textContent = now.toLocaleDateString("en-IN", {
            weekday: "short",
            day: "2-digit",
            month: "short",
            year: "numeric"
        });
    }
}

updateClock();
setInterval(updateClock, 1000);


// ============================================================
// NAVIGATION
// ============================================================

function showSection(sectionId) {

    document.querySelectorAll(".section").forEach(section => {
        section.classList.remove("active-section");
    });

    const selected = document.getElementById(sectionId);

    if (selected) {
        selected.classList.add("active-section");
    }

    document.querySelectorAll(".nav-item").forEach(item => {
        item.classList.remove("active");

        const clickCode = item.getAttribute("onclick") || "";

        if (clickCode.includes(sectionId)) {
            item.classList.add("active");
        }
    });

    if (sectionId === "analytics") {
        loadAnalytics();
    }

    if (sectionId === "ml") {
        loadLatestData();
    }

    if (sectionId === "alerts") {
        loadLatestData();
    }
}


// ============================================================
// TEXT HELPER
// ============================================================

function setText(id, value) {

    const element = document.getElementById(id);

    if (element) {
        element.textContent = value;
    }
}


// ============================================================
// LOAD LATEST DATA
// ============================================================

async function loadLatestData() {

    try {

        const response = await fetch(
            "/api/latest-data?time=" + Date.now(),
            {
                cache: "no-store"
            }
        );

        if (!response.ok) {
            throw new Error("API error: " + response.status);
        }

        const result = await response.json();

        console.log("Latest data:", result);

        if (!result.success) {
            throw new Error("API returned unsuccessful response");
        }

        latestData = result;

        updateDashboard(result);

    } catch (error) {

        console.error("Latest data error:", error);

    }
}


// ============================================================
// UPDATE DASHBOARD
// ============================================================

function updateDashboard(result) {

    if (!result || !result.data) {
        return;
    }

    const data = result.data;
    const predictions = result.predictions || {};

    setText(
        "temperature",
        Number(data.temperature).toFixed(1)
    );

    setText(
        "humidity",
        Number(data.humidity).toFixed(1)
    );

    setText(
        "electricity",
        Number(data.electricity).toFixed(1)
    );

    setText(
        "water",
        Number(data.water).toFixed(1)
    );

    setText(
        "occupancy",
        Number(data.occupancy).toFixed(0)
    );


    // LIVE DATA

    setText(
        "liveTemp",
        Number(data.temperature).toFixed(1)
    );

    setText(
        "liveHumidity",
        Number(data.humidity).toFixed(1)
    );

    setText(
        "liveElectricity",
        Number(data.electricity).toFixed(1)
    );

    setText(
        "liveWater",
        Number(data.water).toFixed(1)
    );

    setText(
        "liveOccupancy",
        Number(data.occupancy).toFixed(0)
    );


    // ML PREDICTIONS

    if (
        predictions.occupancy !== undefined &&
        predictions.occupancy !== null
    ) {

        const occupancyPrediction =
            Number(predictions.occupancy).toFixed(0) + "%";

        setText(
            "predOccupancy",
            occupancyPrediction
        );

        setText(
            "bigOccupancy",
            occupancyPrediction
        );
    }


    if (
        predictions.energy !== undefined &&
        predictions.energy !== null
    ) {

        const energyPrediction =
            Number(predictions.energy).toFixed(1) + " kWh";

        setText(
            "predEnergy",
            energyPrediction
        );

        setText(
            "bigEnergy",
            energyPrediction
        );
    }


    // LAST UPDATED

    if (data.timestamp) {

        setText(
            "lastUpdated",
            data.timestamp
        );
    }


    // STATUS

    updateStatus(
        result.status || "Normal"
    );


    // ALERTS

    updateAlerts(
        result.alerts || []
    );
}


// ============================================================
// SYSTEM STATUS
// ============================================================

function updateStatus(status) {

    const element =
        document.getElementById("overallStatus");

    if (!element) {
        return;
    }

    const value =
        String(status).toLowerCase();


    if (
        value.includes("critical")
    ) {

        element.textContent =
            "SYSTEM CRITICAL";

        element.style.color =
            "#ff5f6d";

    }

    else if (
        value.includes("warning")
    ) {

        element.textContent =
            "SYSTEM WARNING";

        element.style.color =
            "#ffc857";

    }

    else {

        element.textContent =
            "SYSTEM NORMAL";

        element.style.color =
            "#32e58c";
    }
}


// ============================================================
// ALERTS
// ============================================================

function updateAlerts(alerts) {

    if (!Array.isArray(alerts)) {
        alerts = [];
    }

    const container =
        document.getElementById("alertsContainer");

    const allAlerts =
        document.getElementById("allAlerts");

    const count =
        document.getElementById("alertCount");


    if (count) {
        count.textContent = alerts.length;
    }


    if (alerts.length === 0) {

        const html = `
            <div class="no-alert">
                ✓ System operating normally
            </div>
        `;

        if (container) {
            container.innerHTML = html;
        }

        if (allAlerts) {
            allAlerts.innerHTML = html;
        }

        return;
    }


    let html = "";

    alerts.forEach(alert => {

        html += `
            <div class="alert-item">
                ⚠ ${alert.message || "Campus alert detected"}
            </div>
        `;
    });


    if (container) {
        container.innerHTML = html;
    }

    if (allAlerts) {
        allAlerts.innerHTML = html;
    }
}


// ============================================================
// SIMULATE SENSOR READING
// ============================================================

async function generateReading() {

    try {

        const response =
            await fetch(
                "/api/simulate-reading",
                {
                    method: "POST",
                    cache: "no-store"
                }
            );

        if (!response.ok) {
            throw new Error(
                "Simulation API error"
            );
        }

        const result =
            await response.json();

        console.log(
            "New sensor reading:",
            result
        );

        await loadLatestData();

        await loadAnalytics();

    }

    catch (error) {

        console.error(
            "Simulation error:",
            error
        );
    }
}


// ============================================================
// BUILDING PROFILES
// ============================================================

const zoneProfiles = {

    "Boys Hostel": {
        temp: 1.1,
        humidity: 6,
        occupancy: 1.12,
        electricity: 1.20,
        water: 1.35
    },

    "MBA": {
        temp: -0.4,
        humidity: 2,
        occupancy: 0.72,
        electricity: 0.72,
        water: 0.62
    },

    "Polytechnic": {
        temp: 0.5,
        humidity: 4,
        occupancy: 0.82,
        electricity: 0.95,
        water: 0.75
    },

    "Auditorium": {
        temp: 0.8,
        humidity: 5,
        occupancy: 0.35,
        electricity: 1.35,
        water: 0.45
    },

    "Mechanical Department": {
        temp: 1.8,
        humidity: 7,
        occupancy: 0.88,
        electricity: 1.30,
        water: 0.80
    },

    "Electrical Department": {
        temp: 0.7,
        humidity: 3,
        occupancy: 0.84,
        electricity: 1.28,
        water: 0.72
    },

    "Mining Department": {
        temp: 1.2,
        humidity: 5,
        occupancy: 0.91,
        electricity: 1.15,
        water: 0.82
    },

    "KAKA CANTEEN": {
        temp: 2.0,
        humidity: 8,
        occupancy: 0.65,
        electricity: 1.45,
        water: 1.50
    },

    "Computer Science Department": {
        temp: 0.3,
        humidity: 1,
        occupancy: 0.95,
        electricity: 1.40,
        water: 0.55
    },

    "Civil Department": {
        temp: 0.4,
        humidity: 3,
        occupancy: 0.80,
        electricity: 0.85,
        water: 0.70
    },

    "Data Science Department": {
        temp: 0.2,
        humidity: 1,
        occupancy: 0.93,
        electricity: 1.25,
        water: 0.52
    },

    "Electronics Department": {
        temp: 0.9,
        humidity: 3,
        occupancy: 0.78,
        electricity: 1.22,
        water: 0.60
    },

    "Girls Hostel": {
        temp: 1.0,
        humidity: 6,
        occupancy: 1.08,
        electricity: 1.18,
        water: 1.30
    },

    "RCERT Main Building": {
        temp: -0.3,
        humidity: 2,
        occupancy: 0.58,
        electricity: 0.90,
        water: 0.50
    },

    "Main Gate": {
        temp: 1.3,
        humidity: 5,
        occupancy: 0.30,
        electricity: 0.25,
        water: 0.10
    }
};


// ============================================================
// BUILDING DATA
// ============================================================

function calculateZoneData(name, type) {

    if (!latestData || !latestData.data) {
        return null;
    }

    const campus =
        latestData.data;

    const profile =
        zoneProfiles[name] || {
            temp: 0,
            humidity: 0,
            occupancy: 0.70,
            electricity: 0.70,
            water: 0.60
        };


    let temperature =
        Number(campus.temperature)
        + profile.temp;

    let humidity =
        Number(campus.humidity)
        + profile.humidity;

    let occupancy =
        Number(campus.occupancy)
        * profile.occupancy;

    let electricity =
        Number(campus.electricity)
        * profile.electricity;

    let water =
        Number(campus.water)
        * profile.water;


    if (type === "Hostel") {
        occupancy += 5;
    }

    if (type === "Food Facility") {
        occupancy += 8;
        water += 5;
    }

    if (type === "Entrance") {
        occupancy += 5;
    }


    temperature =
        Math.max(
            20,
            Math.min(
                45,
                temperature
            )
        );

    humidity =
        Math.max(
            30,
            Math.min(
                95,
                humidity
            )
        );

    occupancy =
        Math.max(
            0,
            Math.min(
                100,
                occupancy
            )
        );


    return {

        temperature:
            temperature.toFixed(1),

        humidity:
            humidity.toFixed(1),

        occupancy:
            occupancy.toFixed(0),

        electricity:
            Math.max(
                0,
                electricity
            ).toFixed(1),

        water:
            Math.max(
                0,
                water
            ).toFixed(1)
    };
}


// ============================================================
// BUILDING STATUS
// ============================================================

function calculateZoneStatus(data) {

    if (!data) {

        return {
            status: "NORMAL",
            score: 85
        };
    }


    let score = 100;

    const temperature =
        Number(data.temperature);

    const humidity =
        Number(data.humidity);

    const occupancy =
        Number(data.occupancy);

    const electricity =
        Number(data.electricity);


    if (temperature >= 35) {
        score -= 25;
    }
    else if (temperature >= 32) {
        score -= 12;
    }


    if (humidity >= 80) {
        score -= 15;
    }
    else if (humidity >= 70) {
        score -= 5;
    }


    if (occupancy >= 90) {
        score -= 12;
    }
    else if (occupancy >= 80) {
        score -= 5;
    }


    if (electricity >= 25) {
        score -= 15;
    }
    else if (electricity >= 18) {
        score -= 7;
    }


    score =
        Math.max(
            35,
            Math.min(
                100,
                score
            )
        );


    let status = "NORMAL";

    if (score < 55) {
        status = "CRITICAL";
    }
    else if (score < 75) {
        status = "WARNING";
    }


    return {
        status: status,
        score: score
    };
}


// ============================================================
// BUILDING CLICK
// ============================================================

function selectBuilding(
    name,
    type = "Zone"
) {

    const modal =
        document.getElementById(
            "buildingModal"
        );

    if (!modal) {
        return;
    }


    setText(
        "modalBuilding",
        name
    );

    setText(
        "modalType",
        type
    );


    const zoneData =
        calculateZoneData(
            name,
            type
        );


    if (!zoneData) {

        setText(
            "modalTemp",
            "--"
        );

        setText(
            "modalHumidity",
            "--"
        );

        setText(
            "modalOccupancy",
            "--"
        );

        setText(
            "modalEnergy",
            "--"
        );

        setText(
            "modalWater",
            "--"
        );

        setText(
            "modalStatus",
            "WAITING"
        );

        modal.classList.add("show");

        return;
    }


    setText(
        "modalTemp",
        zoneData.temperature + " °C"
    );

    setText(
        "modalHumidity",
        zoneData.humidity + " %"
    );

    setText(
        "modalOccupancy",
        zoneData.occupancy + " %"
    );

    setText(
        "modalEnergy",
        zoneData.electricity + " kWh"
    );

    setText(
        "modalWater",
        zoneData.water + " L"
    );

    setText(
        "modalSource",
        "SIMULATED"
    );


    const health =
        calculateZoneStatus(
            zoneData
        );


    setText(
        "modalStatus",
        health.status
    );


    const healthBar =
        document.getElementById(
            "zoneHealthBar"
        );

    if (healthBar) {

        healthBar.style.width =
            health.score + "%";
    }


    const selected =
        document.getElementById(
            "selectedBuilding"
        );

    if (selected) {

        selected.innerHTML = `
            <strong>${name}</strong>
            <br><br>
            <span>Zone Type: ${type}</span>
            <br><br>
            <span>
                Digital Twin Health:
                <strong>${health.score}%</strong>
            </span>
            <br><br>
            <span>
                Monitoring:
                Simulated / IoT-ready
            </span>
        `;
    }


    modal.classList.add("show");
}


// ============================================================
// CLOSE MODAL
// ============================================================

function closeModal() {

    const modal =
        document.getElementById(
            "buildingModal"
        );

    if (modal) {
        modal.classList.remove("show");
    }
}


window.addEventListener(
    "click",
    function(event) {

        const modal =
            document.getElementById(
                "buildingModal"
            );

        if (
            modal &&
            event.target === modal
        ) {
            closeModal();
        }
    }
);


window.addEventListener(
    "keydown",
    function(event) {

        if (event.key === "Escape") {
            closeModal();
        }
    }
);


// ============================================================
// ANALYTICS
// ============================================================

async function loadAnalytics() {

    try {

        const response =
            await fetch(
                "/api/analytics?time=" + Date.now(),
                {
                    cache: "no-store"
                }
            );

        if (!response.ok) {
            throw new Error(
                "Analytics API error"
            );
        }

        const result =
            await response.json();

        console.log(
            "Analytics:",
            result
        );


        if (
            !result.success ||
            !result.data ||
            result.data.length === 0
        ) {
            return;
        }


        const records =
            [...result.data].reverse();


        const labels =
            records.map(
                item => {

                    const date =
                        new Date(
                            item.timestamp
                        );

                    return date.toLocaleTimeString(
                        "en-IN",
                        {
                            hour: "2-digit",
                            minute: "2-digit"
                        }
                    );
                }
            );


        const temperatures =
            records.map(
                item =>
                    Number(
                        item.temperature
                    )
            );


        const occupancies =
            records.map(
                item =>
                    Number(
                        item.occupancy
                    )
            );


        const electricity =
            records.map(
                item =>
                    Number(
                        item.electricity
                    )
            );


        const water =
            records.map(
                item =>
                    Number(
                        item.water
                    )
            );


        createCharts(
            labels,
            temperatures,
            occupancies,
            electricity,
            water
        );

    }

    catch (error) {

        console.error(
            "Analytics error:",
            error
        );
    }
}


// ============================================================
// CHARTS
// ============================================================

function createCharts(
    labels,
    temperatures,
    occupancies,
    electricity,
    water
) {

    if (
        typeof Chart ===
        "undefined"
    ) {

        console.error(
            "Chart.js is not loaded"
        );

        return;
    }


    const commonOptions = {

        responsive: true,

        maintainAspectRatio: false,

        plugins: {

            legend: {
                display: false
            }
        },

        scales: {

            x: {

                ticks: {
                    color: "#71859c",
                    maxTicksLimit: 8
                },

                grid: {
                    color:
                        "rgba(255,255,255,0.04)"
                }
            },

            y: {

                ticks: {
                    color: "#71859c"
                },

                grid: {
                    color:
                        "rgba(255,255,255,0.04)"
                }
            }
        }
    };


    const tempCanvas =
        document.getElementById(
            "temperatureChart"
        );

    if (tempCanvas) {

        if (temperatureChart) {
            temperatureChart.destroy();
        }

        temperatureChart =
            new Chart(
                tempCanvas,
                {

                    type: "line",

                    data: {

                        labels: labels,

                        datasets: [{

                            data:
                                temperatures,

                            borderColor:
                                "#4da3ff",

                            backgroundColor:
                                "rgba(77,163,255,0.08)",

                            fill: true,

                            tension: 0.35,

                            pointRadius: 2
                        }]
                    },

                    options:
                        commonOptions
                }
            );
    }


    const occupancyCanvas =
        document.getElementById(
            "occupancyChart"
        );

    if (occupancyCanvas) {

        if (occupancyChart) {
            occupancyChart.destroy();
        }

        occupancyChart =
            new Chart(
                occupancyCanvas,
                {

                    type: "line",

                    data: {

                        labels: labels,

                        datasets: [{

                            data:
                                occupancies,

                            borderColor:
                                "#32e58c",

                            backgroundColor:
                                "rgba(50,229,140,0.08)",

                            fill: true,

                            tension: 0.35,

                            pointRadius: 2
                        }]
                    },

                    options:
                        commonOptions
                }
            );
    }


    const electricityCanvas =
        document.getElementById(
            "electricityChart"
        );

    if (electricityCanvas) {

        if (electricityChart) {
            electricityChart.destroy();
        }

        electricityChart =
            new Chart(
                electricityCanvas,
                {

                    type: "bar",

                    data: {

                        labels: labels,

                        datasets: [{

                            data:
                                electricity,

                            backgroundColor:
                                "rgba(255,200,87,0.55)",

                            borderRadius: 4
                        }]
                    },

                    options:
                        commonOptions
                }
            );
    }


    const waterCanvas =
        document.getElementById(
            "waterChart"
        );

    if (waterCanvas) {

        if (waterChart) {
            waterChart.destroy();
        }

        waterChart =
            new Chart(
                waterCanvas,
                {

                    type: "line",

                    data: {

                        labels: labels,

                        datasets: [{

                            data:
                                water,

                            borderColor:
                                "#35d9ff",

                            backgroundColor:
                                "rgba(53,217,255,0.08)",

                            fill: true,

                            tension: 0.35,

                            pointRadius: 2
                        }]
                    },

                    options:
                        commonOptions
                }
            );
    }
}


// ============================================================
// INITIAL LOAD
// ============================================================

console.log(
    "Starting RCERT dashboard..."
);

loadLatestData();

loadAnalytics();


// ============================================================
// AUTO REFRESH
// ============================================================

setInterval(
    loadLatestData,
    5000
);

setInterval(
    loadAnalytics,
    15000
);


// ============================================================
// AUTO SENSOR SIMULATION
// ============================================================

setInterval(
    generateReading,
    15000
);

console.log(
    "RCERT dashboard controller ready."
);