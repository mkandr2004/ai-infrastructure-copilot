from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MetricSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collected_at: datetime
    cpu_percent: float
    memory_total_gb: float
    memory_used_gb: float
    memory_available_gb: float
    memory_percent: float
    disk_total_gb: float
    disk_used_gb: float
    disk_free_gb: float
    disk_percent: float
    created_at: datetime
