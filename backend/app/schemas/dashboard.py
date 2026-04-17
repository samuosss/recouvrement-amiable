from pydantic import BaseModel
from typing import List


class MonthlyPerformance(BaseModel):
    month: str
    recouvre: float
    objectif: float


class StatutDistribution(BaseModel):
    name: str
    value: int
    color: str


class DashboardStats(BaseModel):
    # KPIs
    total_dossiers: int
    dossiers_actifs: int
    total_clients: int
    montant_total_du: float
    montant_recouvre: float
    taux_recouvrement: float          # percentage 0-100

    # Charts
    monthly_performance: List[MonthlyPerformance]
    status_distribution: List[StatutDistribution]