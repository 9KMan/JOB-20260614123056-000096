"""E-commerce connector — abstracts over platforms, streams everything.

For unknown platforms, falls back to a mock implementation that
yields synthetic data. The mock is the default in dev/test.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncIterator, Dict, List, Optional

from shared.common.http import ServiceClient

logger = logging.getLogger(__name__)


class EcommerceConnector:
    """Base connector interface. Concrete subclasses override the methods."""

    platform: str = "generic"

    def __init__(self, api_key: str = "", base_url: str = "") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client: Optional[ServiceClient] = None

    def _http(self) -> ServiceClient:
        if self._client is None:
            self._client = ServiceClient(self.base_url, name=f"ecom-{self.platform}", timeout=15.0)
        return self._client

    async def list_orders(
        self, since: Optional[str] = None, until: Optional[str] = None, batch_size: int = 100
    ) -> AsyncIterator[Dict[str, Any]]:
        raise NotImplementedError
        yield  # pragma: no cover  (so this is recognized as an async generator)

    async def list_products(self, since: Optional[str] = None) -> AsyncIterator[Dict[str, Any]]:
        raise NotImplementedError
        yield  # pragma: no cover

    async def list_inventory(self) -> AsyncIterator[Dict[str, Any]]:
        raise NotImplementedError
        yield  # pragma: no cover

    async def list_customers(self) -> AsyncIterator[Dict[str, Any]]:
        raise NotImplementedError
        yield  # pragma: no cover

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None


# ---- Mock connector (default for dev/test) ----

class MockEcommerceConnector(EcommerceConnector):
    """Mock implementation that yields synthetic data.

    Realistic enough for development: orders have a stable customer_id
    over time, values vary, statuses follow a distribution.
    """

    platform = "mock"

    def __init__(self, seed: int = 42) -> None:
        super().__init__()
        self._seed = seed
        self._orders: List[Dict[str, Any]] = []
        self._build_synthetic_dataset()

    def _build_synthetic_dataset(self) -> None:
        random.seed(self._seed)
        statuses = ["paid", "shipped", "delivered", "delayed", "disputed"]
        weights = [0.15, 0.20, 0.55, 0.07, 0.03]
        skus = [f"SKU-{i:03d}" for i in range(1, 21)]
        customers = [f"CUST-{i:04d}" for i in range(1, 51)]
        now = datetime.now(timezone.utc)
        for i in range(500):
            ts = now - timedelta(days=random.randint(0, 90), hours=random.randint(0, 23))
            self._orders.append({
                "order_id": f"ORD-{10000 + i}",
                "customer_id": random.choice(customers),
                "ts": ts.isoformat(),
                "value_cents": random.randint(1000, 50000),
                "currency": "USD",
                "status": random.choices(statuses, weights=weights)[0],
                "sku": random.choice(skus),
            })

    async def list_orders(
        self, since: Optional[str] = None, until: Optional[str] = None, batch_size: int = 100
    ) -> AsyncIterator[Dict[str, Any]]:
        for o in self._orders:
            await asyncio.sleep(0)  # yield control
            if since and o["ts"] < since:
                continue
            if until and o["ts"] > until:
                continue
            yield o

    async def list_products(self, since: Optional[str] = None) -> AsyncIterator[Dict[str, Any]]:
        for i in range(1, 21):
            yield {"sku": f"SKU-{i:03d}", "name": f"Product {i}", "price_cents": random.randint(1000, 30000)}

    async def list_inventory(self) -> AsyncIterator[Dict[str, Any]]:
        for i in range(1, 21):
            yield {"sku": f"SKU-{i:03d}", "warehouse": "default", "qty": random.randint(0, 200)}

    async def list_customers(self) -> AsyncIterator[Dict[str, Any]]:
        for i in range(1, 51):
            yield {"customer_id": f"CUST-{i:04d}", "name": f"Customer {i}"}


def make_connector(platform: Optional[str] = None) -> EcommerceConnector:
    """Factory: returns the right connector for the given platform.

    Default (and unknown) is the mock connector. Real platforms should
    be added as new subclasses of EcommerceConnector.
    """
    p = (platform or os.environ.get("KMAN_ECOM_PLATFORM") or "mock").lower()
    if p == "mock":
        return MockEcommerceConnector()
    # TODO: add ShopifyConnector, WooCommerceConnector, etc.
    logger.warning("unknown e-commerce platform %s, falling back to mock", p)
    return MockEcommerceConnector()
