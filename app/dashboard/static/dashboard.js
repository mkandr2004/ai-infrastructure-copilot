const refreshButton = document.querySelector(
    "#refresh-button",
);

const statusBadge = document.querySelector(
    "#api-status",
);

const collectionTime = document.querySelector(
    "#collection-time",
);

const historyLimit = document.querySelector(
    "#history-limit",
);

const historyStatus = document.querySelector(
    "#history-status",
);

const historyBody = document.querySelector(
    "#history-body",
);


function metricElements(metricName) {
    return {
        value: document.querySelector(
            `#${metricName}-value`,
        ),
        bar: document.querySelector(
            `#${metricName}-bar`,
        ),
    };
}


function metricLevel(percent) {
    if (percent >= 90) {
        return "critical";
    }

    if (percent >= 75) {
        return "warning";
    }

    return "normal";
}


function updateMetric(metricName, rawValue) {
    const elements = metricElements(metricName);
    const numericValue = Number(rawValue);

    const safeValue = Math.min(
        100,
        Math.max(0, numericValue),
    );

    elements.value.textContent = (
        `${safeValue.toFixed(1)} %`
    );

    elements.bar.style.width = `${safeValue}%`;

    elements.bar.dataset.level = metricLevel(
        safeValue,
    );
}


function updateStatus(message, state) {
    statusBadge.textContent = message;

    statusBadge.className = (
        `status-badge status-${state}`
    );
}


function formatTimestamp(timestamp) {
    const date = new Date(timestamp);

    if (Number.isNaN(date.getTime())) {
        return timestamp;
    }

    return date.toLocaleString(
        "fr-FR",
        {
            dateStyle: "medium",
            timeStyle: "medium",
        },
    );
}


async function loadCurrentMetrics() {
    refreshButton.disabled = true;

    updateStatus(
        "Collecte en cours…",
        "loading",
    );

    try {
        const response = await fetch(
            "/metrics",
            {
                headers: {
                    Accept: "application/json",
                },
                cache: "no-store",
            },
        );

        if (!response.ok) {
            throw new Error(
                `Réponse HTTP ${response.status}`,
            );
        }

        const metrics = await response.json();

        updateMetric(
            "cpu",
            metrics.cpu.percent,
        );

        updateMetric(
            "memory",
            metrics.memory.percent,
        );

        updateMetric(
            "disk",
            metrics.disk.percent,
        );

        collectionTime.textContent = (
            formatTimestamp(metrics.timestamp)
        );

        collectionTime.dateTime = metrics.timestamp;

        updateStatus(
            "API opérationnelle",
            "success",
        );
    } catch (error) {
        console.error(
            "Échec du chargement des métriques :",
            error,
        );

        updateStatus(
            "API indisponible",
            "error",
        );
    } finally {
        refreshButton.disabled = false;
    }
}


function percentageText(value) {
    const numericValue = Number(value);

    if (!Number.isFinite(numericValue)) {
        return "Indisponible";
    }

    return `${numericValue.toFixed(1)} %`;
}


function createHistoryCell(content) {
    const cell = document.createElement("td");

    cell.textContent = content;

    return cell;
}


function createHistoryRow(snapshot) {
    const row = document.createElement("tr");

    row.append(
        createHistoryCell(
            formatTimestamp(snapshot.collected_at),
        ),
        createHistoryCell(
            percentageText(snapshot.cpu_percent),
        ),
        createHistoryCell(
            percentageText(
                snapshot.memory_percent,
            ),
        ),
        createHistoryCell(
            percentageText(
                snapshot.disk_percent,
            ),
        ),
    );

    return row;
}


function showHistoryMessage(message) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");

    cell.colSpan = 4;
    cell.textContent = message;

    row.append(cell);
    historyBody.append(row);
}


async function loadHistory() {
    historyStatus.textContent = (
        "Chargement de l’historique…"
    );
    historyStatus.dataset.state = "loading";

    try {
        const limit = encodeURIComponent(
            historyLimit.value,
        );

        const response = await fetch(
            `/metrics/history?limit=${limit}`,
            {
                headers: {
                    Accept: "application/json",
                },
                cache: "no-store",
            },
        );

        if (!response.ok) {
            throw new Error(
                `Réponse HTTP ${response.status}`,
            );
        }

        const snapshots = await response.json();

        document.dispatchEvent(
            new CustomEvent(
                "dashboard:history-loaded",
                {detail: {snapshots}},
            ),
        );

        historyBody.replaceChildren();

        if (snapshots.length === 0) {
            showHistoryMessage(
                "Aucune mesure enregistrée dans PostgreSQL.",
            );
        } else {
            snapshots.forEach((snapshot) => {
                historyBody.append(
                    createHistoryRow(snapshot),
                );
            });
        }

        historyStatus.textContent = (
            `${snapshots.length} mesure(s) affichée(s)`
        );
        historyStatus.dataset.state = "success";
    } catch (error) {
        console.error(
            "Échec du chargement de l’historique :",
            error,
        );

        document.dispatchEvent(
            new CustomEvent(
                "dashboard:history-loaded",
                {detail: {snapshots: []}},
            ),
        );

        historyBody.replaceChildren();
        showHistoryMessage(
            "Historique PostgreSQL indisponible.",
        );

        historyStatus.textContent = (
            "Historique PostgreSQL indisponible."
        );
        historyStatus.dataset.state = "error";
    }
}


function loadDashboard() {
    loadCurrentMetrics();
    loadHistory();
}


refreshButton.addEventListener(
    "click",
    loadDashboard,
);

historyLimit.addEventListener(
    "change",
    loadHistory,
);

loadDashboard();
