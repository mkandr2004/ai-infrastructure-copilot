const workflowsList = document.querySelector("#workflows-list");
const workflowsStatus = document.querySelector("#workflows-status");
const refreshWorkflowsButton = document.querySelector(
    "#refresh-workflows-button",
);
const workflowForm = document.querySelector("#workflow-form");
const workflowSubmitButton = document.querySelector(
    "#workflow-submit-button",
);
const workflowResult = document.querySelector("#workflow-result");


function setWorkflowPanelStatus(message, state = "loading") {
    workflowsStatus.textContent = message;
    workflowsStatus.dataset.state = state;
}


function workflowLocalDate(timestamp) {
    const date = new Date(timestamp);

    if (Number.isNaN(date.getTime())) {
        return timestamp;
    }

    return date.toLocaleString("fr-FR", {
        dateStyle: "medium",
        timeStyle: "short",
    });
}


function showWorkflowsMessage(message) {
    const paragraph = document.createElement("p");

    paragraph.className = "empty-state";
    paragraph.textContent = message;
    workflowsList.replaceChildren(paragraph);
}


function workflowStatusLabel(status) {
    const labels = {
        pending: "En attente",
        running: "En cours",
        completed: "Terminé",
        failed: "Échec",
    };

    return labels[status] || status;
}


function workflowStepLabel(name) {
    const labels = {
        collect_metrics: "Collecte des métriques",
        analyze_history: "Analyse de l’historique",
        find_similar_incidents: "Recherche d’incidents similaires",
        search_knowledge: "Recherche documentaire",
        build_findings: "Construction des constats",
        produce_diagnosis: "Production du diagnostic",
    };

    return labels[name] || name;
}


function renderWorkflowSteps(steps) {
    const list = document.querySelector("#workflow-result-steps");
    const items = steps.map((step) => {
        const item = document.createElement("li");
        const summary = step.summary || step.error || "Sans résultat";

        item.textContent = (
            `${workflowStepLabel(step.name)} — `
            + `${workflowStatusLabel(step.status)} — ${summary}`
        );

        return item;
    });

    list.replaceChildren(...items);
}


function renderWorkflowFindings(findings) {
    const container = document.querySelector(
        "#workflow-result-findings",
    );

    if (findings.length === 0) {
        const message = document.createElement("p");
        message.className = "empty-state";
        message.textContent = "Aucun constat disponible.";
        container.replaceChildren(message);
        return;
    }

    const cards = findings.map((finding) => {
        const card = document.createElement("article");
        const title = document.createElement("h5");
        const details = document.createElement("p");
        const evidence = document.createElement("p");

        card.className = "workflow-finding";
        card.dataset.severity = finding.severity;
        title.textContent = finding.title;
        details.textContent = finding.details;
        evidence.textContent = finding.evidence.join(" · ");
        card.append(title, details, evidence);

        return card;
    });

    container.replaceChildren(...cards);
}


function renderWorkflow(workflow) {
    workflowResult.hidden = false;

    document.querySelector("#workflow-result-title").textContent = (
        workflow.problem_description
    );

    const status = document.querySelector("#workflow-result-status");
    status.textContent = workflowStatusLabel(workflow.status);
    status.dataset.status = workflow.status;

    document.querySelector("#workflow-result-meta").textContent = (
        `ID ${workflow.id} · créé ${workflowLocalDate(workflow.created_at)} `
        + `· expiration ${workflowLocalDate(workflow.expires_at)}`
    );
    document.querySelector("#workflow-result-sources").textContent = (
        workflow.knowledge_sources.length > 0
            ? workflow.knowledge_sources.join(", ")
            : "Aucune"
    );
    document.querySelector("#workflow-result-incidents").textContent = (
        workflow.similar_incident_ids.length > 0
            ? workflow.similar_incident_ids.join(", ")
            : "Aucun"
    );
    document.querySelector("#workflow-result-diagnosis").textContent = (
        workflow.diagnosis || workflow.error || "Diagnostic indisponible."
    );

    renderWorkflowSteps(workflow.steps);
    renderWorkflowFindings(workflow.findings);
}


async function loadWorkflowDetail(workflowId, activeButton) {
    workflowsList.querySelectorAll(".workflow-item").forEach(
        (button) => button.classList.remove("is-active"),
    );

    if (activeButton) {
        activeButton.classList.add("is-active");
    }

    setWorkflowPanelStatus("Chargement du workflow…");

    try {
        const response = await fetch(
            `/workflows/${encodeURIComponent(workflowId)}`,
            {headers: {Accept: "application/json"}, cache: "no-store"},
        );
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || `Réponse HTTP ${response.status}`);
        }

        renderWorkflow(data);
        setWorkflowPanelStatus("Workflow chargé.", "success");
    } catch (error) {
        console.error("Échec de la lecture du workflow :", error);
        setWorkflowPanelStatus(error.message, "error");
    }
}


function createWorkflowButton(workflow) {
    const button = document.createElement("button");
    const title = document.createElement("strong");
    const metadata = document.createElement("span");

    button.type = "button";
    button.className = "workflow-item";
    title.textContent = workflow.problem_description;
    metadata.textContent = (
        `${workflowStatusLabel(workflow.status)} · `
        + workflowLocalDate(workflow.created_at)
    );
    button.append(title, metadata);
    button.addEventListener("click", () => {
        loadWorkflowDetail(workflow.id, button);
    });

    return button;
}


async function loadWorkflows() {
    refreshWorkflowsButton.disabled = true;
    setWorkflowPanelStatus("Chargement des workflows…");

    try {
        const response = await fetch(
            "/workflows?limit=10",
            {headers: {Accept: "application/json"}, cache: "no-store"},
        );
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || `Réponse HTTP ${response.status}`);
        }

        if (data.length === 0) {
            showWorkflowsMessage("Aucun workflow enregistré.");
            workflowResult.hidden = true;
        } else {
            const buttons = data.map(createWorkflowButton);
            workflowsList.replaceChildren(...buttons);
        }

        setWorkflowPanelStatus(
            `${data.length} workflow(s) disponible(s)`,
            "success",
        );
    } catch (error) {
        console.error("Échec du chargement des workflows :", error);
        showWorkflowsMessage("Mémoire des workflows indisponible.");
        setWorkflowPanelStatus(error.message, "error");
    } finally {
        refreshWorkflowsButton.disabled = false;
    }
}


async function submitWorkflow(event) {
    event.preventDefault();
    workflowSubmitButton.disabled = true;
    setWorkflowPanelStatus(
        "Investigation en cours… Cette opération peut prendre plusieurs secondes.",
    );

    const requestBody = {
        problem_description: document.querySelector(
            "#workflow-problem-description",
        ).value.trim(),
        use_knowledge: document.querySelector(
            "#workflow-use-knowledge",
        ).checked,
        include_logs: document.querySelector(
            "#workflow-include-logs",
        ).checked,
        confirm_external_send: document.querySelector(
            "#workflow-confirm-external-send",
        ).checked,
    };

    try {
        const response = await fetch("/workflows", {
            method: "POST",
            headers: {
                Accept: "application/json",
                "Content-Type": "application/json",
            },
            body: JSON.stringify(requestBody),
        });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || `Réponse HTTP ${response.status}`);
        }

        renderWorkflow(data);
        setWorkflowPanelStatus("Investigation terminée.", "success");
        await loadWorkflows();
    } catch (error) {
        console.error("Échec du workflow :", error);
        setWorkflowPanelStatus(error.message, "error");
    } finally {
        workflowSubmitButton.disabled = false;
    }
}


refreshWorkflowsButton.addEventListener("click", loadWorkflows);
document.querySelector("#refresh-button").addEventListener(
    "click",
    loadWorkflows,
);
workflowForm.addEventListener("submit", submitWorkflow);
loadWorkflows();
