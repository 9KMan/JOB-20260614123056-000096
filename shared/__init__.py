"""KMan Workflow Automations & Data Analyses Platform.

A microservice-based platform for e-commerce/dropshipping account
management: rule-based automations, AI-driven judgment calls, data
analyses, scheduled reporting, and a WhatsApp workspace adapter.

Each service is independently deployable. Services communicate over
REST + Redis queues. If one service fails, the rest keep running.
"""

__version__ = "0.1.0"
