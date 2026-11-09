const incidentsList = document.querySelector("#incidents-list");
const incidentsStatus = document.querySelector("#incidents-status");
const refreshIncidentsButton = document.querySelector(
    "#refresh-incidents-button",
);
const incidentDetailPlaceholder = document.querySelector(
    "#incident-detail-placeholder",
);
const incidentDetailContent = document.querySelector(
    "#incident-detail-content",
);

const diagnosisForm = document.querySelector("#diagnosis-form");
const diagnoseButton = document.querySelector("#diagnose-button");
const diagnosisStatus = document.querySelector("#diagnosis-status");
const diagnosisResult = document.querySelector("#diagnosis-result");


function setPanelStatus(element, message, state = "loading") {
    element.textContent = message;
    element.dataset.state = state;
}


function localDate(timestamp) {
    const date = new Date(timestamp);

    if (Number.isNaN(date.getTime())) {
        return timestamp;
    }

    return date.toLocaleString("fr-FR", {
        dateStyle: "medium",
        timeStyle: "short",
    });
}


function percent(value) {
    const numericValue = Number(value);

    return Number.isFinite(numericValue)
        ? `${numericValue.toFixed(1)} %`
        : "Indisponible";
}


function showIncidentsMessage(message) {
    const paragraph = document.createElement("p");

    paragraph.className = "empty-state";
    paragraph.textContent = message;
    incidentsList.replaceChildren(paragraph);
}


function resetIncidentDetail(message) {
    incidentDetailContent.hidden = true;
    incidentDetailPlaceholder.hidden = false;
    incidentDetailPlaceholder.textContent = message;
}


function renderIncidentDetail(incident) {
    incidentDetailPlaceholder.hidden = true;
    incidentDetailContent.hidden = false;

    document.querySelector("#incident-detail-title").textContent = (
        incident.problem_description
    );
    document.querySelector("#incident-detail-created").textContent = (
        `Collecté le ${localDate(incident.collected_at)} · `
        + `expiration ${localDate(incident.expires_at)}`
    );
    document.querySelector("#incident-cpu").textContent = (
        percent(incident.metrics.cpu_percent)
    );
    document.querySelector("#incident-memory").textContent = (
        percent(incident.metrics.memory_percent)
    );
    document.querySelector("#incident-disk").textContent = (
        percent(incident.metrics.disk_percent)
    );
    document.querySelector("#incident-model").textContent = (
        incident.diagnostic_model
    );
    document.querySelector("#incident-sources").textContent = (
        incident.knowledge_sources.length > 0
            ? incident.knowledge_sources.join(", ")
            : "Aucune"
    );
    document.querySelector("#incident-logs").textContent = (
        incident.logs_included ? "Oui" : "Non"
    );
    document.querySelector("#incident-diagnosis").textContent = (
        incident.diagnosis
    );
}


async function loadIncidentDetail(incidentId, activeButton) {
    resetIncidentDetail("Chargement de l’incident…");

    incidentsList.querySelectorAll(".incident-item").forEach(
        (button) => button.classList.remove("is-active"),
    );
    activeButton.classList.add("is-active");

    try {
        const response = await fetch(
            `/incidents/${encodeURIComponent(incidentId)}`,
            {headers: {Accept: "application/json"}, cache: "no-store"},
        );

        if (!response.ok) {
            throw new Error(`Réponse HTTP ${response.status}`);
        }

        renderIncidentDetail(await response.json());
    } catch (error) {
        console.error("Échec de la lecture de l’incident :", error);
        resetIncidentDetail("Impossible de charger cet incident.");
    }
}


function createIncidentButton(incident) {
    const button = document.createElement("button");
    const title = document.createElement("strong");
    const metadata = document.createElement("span");

    button.type = "button";
    button.className = "incident-item";
    title.textContent = incident.problem_description;
    metadata.textContent = (
        `${localDate(incident.created_at)} · `
        + `CPU ${percent(incident.metrics.cpu_percent)}`
    );

    button.append(title, metadata);
    button.addEventListener("click", () => {
        loadIncidentDetail(incident.id, button);
    });

    return button;
}


async function loadIncidents() {
    refreshIncidentsButton.disabled = true;
    setPanelStatus(incidentsStatus, "Chargement des incidents…");

    try {
        const response = await fetch(
            "/incidents?limit=10",
            {headers: {Accept: "application/json"}, cache: "no-store"},
        );

        if (!response.ok) {
            throw new Error(`Réponse HTTP ${response.status}`);
        }

        const incidents = await response.json();

        if (incidents.length === 0) {
            showIncidentsMessage("Aucun incident enregistré.");
            resetIncidentDetail("Aucun incident à afficher.");
        } else {
            const buttons = incidents.map(createIncidentButton);
            incidentsList.replaceChildren(...buttons);
            await loadIncidentDetail(incidents[0].id, buttons[0]);
        }

        setPanelStatus(
            incidentsStatus,
            `${incidents.length} incident(s) disponible(s)`,
            "success",
        );
    } catch (error) {
        console.error("Échec du chargement des incidents :", error);
        showIncidentsMessage("Mémoire Redis indisponible.");
        resetIncidentDetail("Impossible de consulter les incidents.");
        setPanelStatus(
            incidentsStatus,
            "Mémoire Redis indisponible.",
            "error",
        );
    } finally {
        refreshIncidentsButton.disabled = false;
    }
}


async function responsePayload(response) {
    try {
        return await response.json();
    } catch {
        return {};
    }
}


function renderDiagnosis(data) {
    diagnosisResult.hidden = false;
    document.querySelector("#diagnosis-model").textContent = data.model;
    document.querySelector("#diagnosis-sources").textContent = (
        data.knowledge_sources.length > 0
            ? data.knowledge_sources.join(", ")
            : "Aucune"
    );
    document.querySelector("#diagnosis-incident").textContent = (
        data.incident_saved
            ? `Enregistré (${data.incident_id})`
            : "Non enregistré"
    );
    document.querySelector("#diagnosis-output").textContent = (
        data.diagnosis
    );
}


async function submitDiagnosis(event) {
    event.preventDefault();
    diagnosisResult.hidden = true;
    diagnoseButton.disabled = true;
    setPanelStatus(
        diagnosisStatus,
        "Diagnostic Gemini en cours… Cette opération peut prendre plusieurs secondes.",
    );

    const requestBody = {
        problem_description: document.querySelector(
            "#problem-description",
        ).value.trim(),
        use_knowledge: document.querySelector("#use-knowledge").checked,
        save_incident: document.querySelector("#save-incident").checked,
        include_logs: document.querySelector("#include-logs").checked,
        confirm_external_send: document.querySelector(
            "#confirm-external-send",
        ).checked,
    };

    try {
        const response = await fetch("/diagnose", {
            method: "POST",
            headers: {
                Accept: "application/json",
                "Content-Type": "application/json",
            },
            body: JSON.stringify(requestBody),
        });
        const data = await responsePayload(response);

        if (!response.ok) {
            throw new Error(
                typeof data.detail === "string"
                    ? data.detail
                    : `Réponse HTTP ${response.status}`,
            );
        }

        renderDiagnosis(data);
        setPanelStatus(diagnosisStatus, "Diagnostic terminé.", "success");

        if (data.incident_saved) {
            await loadIncidents();
        }
    } catch (error) {
        console.error("Échec du diagnostic :", error);
        setPanelStatus(diagnosisStatus, error.message, "error");
    } finally {
        diagnoseButton.disabled = false;
    }
}


refreshIncidentsButton.addEventListener("click", loadIncidents);
document.querySelector("#refresh-button").addEventListener(
    "click",
    loadIncidents,
);
diagnosisForm.addEventListener("submit", submitDiagnosis);
loadIncidents();
