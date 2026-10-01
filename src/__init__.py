"""Agent Skill Manager - Cross-platform skill management for domestic AI agent products.

Layered package layout (mirrors MoneyPrinterTurbo's ``app/`` structure):
    config/       product registry & platform constants
    controllers/  user-facing CLI
    models/       typed data shapes (TypedDicts)
    services/     business logic (sync, audit, watch)
    utils/        cross-platform filesystem helpers + native fs-event watchers
"""

__version__ = "0.13.0"
__all__ = ["config", "controllers", "models", "services", "utils"]
