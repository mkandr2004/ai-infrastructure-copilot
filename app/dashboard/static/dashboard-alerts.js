const alertsList = document.querySelector("#alerts-list");
const alertsStatus = document.querySelector("#alerts-status");
const refreshAlertsButton = document.querySelector("#refresh-alerts-button");


function alertLocalDate(timestamp) {
    const date = new Date(timestamp);
    return Number.isNaN(date.getTime())
        ? timestamp
        : date.toLocaleString("fr-FR", {dateStyle: "medium", timeStyle: "short"});
}


function renderAlerts(alerts) {
    if (alerts.length === 0) {
        const message = document.createElement("p");
        message.className = "empty-state";
        message.textContent = "Aucune alerte reçue.";
        alertsList.replaceChildren(message);
        return;
    }

    const cards = alerts.map((alert) => {
        const card = document.createElement("article");
        const heading = document.createElement("div");
        const title = document.createElement("h3");
        const badge = document.createElement("span");
        const summary = document.createElement("p");
        const metadata = document.createElement("p");

        card.className = "alert-card";
        card.dataset.severity = alert.labels.severity || "unknown";
        heading.className = "alert-card-heading";
        title.textContent = alert.labels.alertname || "Alerte";
        badge.className = "alert-status-badge";
        badge.dataset.status = alert.status;
        badge.textContent = alert.status === "resolved" ? "Résolue" : "Active";
        summary.textContent = alert.annotations.summary || "Sans résumé.";
        metadata.className = "detail-meta";
        metadata.textContent = `Reçue ${alertLocalDate(alert.received_at)}`;
        heading.append(title, badge);
        card.append(heading, summary, metadata);
        return card;
    });

    alertsList.replaceChildren(...cards);
}


async function loadAlerts() {
    refreshAlertsButton.disabled = true;
    alertsStatus.textContent = "Chargement des alertes…";
    alertsStatus.dataset.state = "loading";

    try {
        const response = await fetch(
            "/alerts?limit=20",
            {headers: {Accept: "application/json"}, cache: "no-store"},
        );
        const alerts = await response.json();

        if (!response.ok) {
            throw new Error(alerts.detail || `Réponse HTTP ${response.status}`);
        }

        renderAlerts(alerts);
        alertsStatus.textContent = `${alerts.length} alerte(s) disponible(s)`;
        alertsStatus.dataset.state = "success";
    } catch (error) {
        console.error("Échec du chargement des alertes :", error);
        alertsStatus.textContent = error.message;
        alertsStatus.dataset.state = "error";
    } finally {
        refreshAlertsButton.disabled = false;
    }
}


refreshAlertsButton.addEventListener("click", loadAlerts);
document.querySelector("#refresh-button").addEventListener("click", loadAlerts);
loadAlerts();
