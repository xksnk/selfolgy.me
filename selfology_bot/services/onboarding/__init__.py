"""
Onboarding System v2 - Кластерная архитектура

Компоненты:
- ClusterRouter: Навигация по кластерам из JSON
- OnboardingOrchestratorV2: Управление 3 режимами (авто/программа/закончить)

Legacy (disabled):
- OnboardingOrchestrator: Старый оркестратор
- FatigueDetector: Определение усталости
"""

# v2 - активная система
from .cluster_router import ClusterRouter
from .orchestrator_v2 import OnboardingOrchestratorV2

# Legacy - закомментировано
# from .orchestrator import OnboardingOrchestrator
# from .fatigue_detector import FatigueDetector

__all__ = ['ClusterRouter', 'OnboardingOrchestratorV2']