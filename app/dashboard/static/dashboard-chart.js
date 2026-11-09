const chartLines = {
    cpu: document.querySelector("#cpu-history-line"),
    memory: document.querySelector("#memory-history-line"),
    disk: document.querySelector("#disk-history-line"),
};

const historyChartEmpty = document.querySelector(
    "#history-chart-empty",
);


function clampChartPercent(value) {
    const numericValue = Number(value);

    if (!Number.isFinite(numericValue)) {
        return 0;
    }

    return Math.min(100, Math.max(0, numericValue));
}


function createChartPoints(snapshots, fieldName) {
    const left = 40;
    const right = 960;
    const top = 20;
    const bottom = 280;
    const width = right - left;
    const height = bottom - top;
    const lastIndex = Math.max(1, snapshots.length - 1);

    return snapshots.map((snapshot, index) => {
        const x = (
            snapshots.length === 1
                ? left + (width / 2)
                : left + ((index / lastIndex) * width)
        );

        const percent = clampChartPercent(
            snapshot[fieldName],
        );
        const y = bottom - ((percent / 100) * height);

        return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");
}


function clearHistoryChart() {
    Object.values(chartLines).forEach((line) => {
        line.setAttribute("points", "");
    });

    historyChartEmpty.hidden = false;
}


function renderHistoryChart(rawSnapshots) {
    if (!Array.isArray(rawSnapshots) || rawSnapshots.length === 0) {
        clearHistoryChart();
        return;
    }

    const snapshots = rawSnapshots.slice().reverse();

    chartLines.cpu.setAttribute(
        "points",
        createChartPoints(snapshots, "cpu_percent"),
    );
    chartLines.memory.setAttribute(
        "points",
        createChartPoints(snapshots, "memory_percent"),
    );
    chartLines.disk.setAttribute(
        "points",
        createChartPoints(snapshots, "disk_percent"),
    );

    historyChartEmpty.hidden = snapshots.length > 1;
}


document.addEventListener(
    "dashboard:history-loaded",
    (event) => {
        renderHistoryChart(event.detail.snapshots);
    },
);
