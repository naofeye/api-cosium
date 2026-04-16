"""Load test Locust : simule 50 users concurrents sur les endpoints critiques.

Usage :
  pip install locust
  locust -f scripts/load_test.py --host=http://localhost:8000 --users 50 --spawn-rate 5 --run-time 2m --headless

Cible SLO : P95 < 3s sur les endpoints liste (actions, clients, dashboard).
"""
from __future__ import annotations

import os
import random

from locust import HttpUser, between, task


API_BASE = "/api/v1"
TEST_EMAIL = os.getenv("LOAD_TEST_EMAIL", "admin@optiflow.com")
TEST_PASSWORD = os.getenv("LOAD_TEST_PASSWORD", "admin123")


class OptiFlowUser(HttpUser):
    """Simule un opticien qui navigue entre ses dossiers."""

    wait_time = between(1, 3)

    def on_start(self) -> None:
        """Login et stockage du token JWT pour les requetes suivantes."""
        resp = self.client.post(
            f"{API_BASE}/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            name="POST /auth/login",
        )
        if resp.status_code != 200:
            self.environment.runner.quit()
            return
        token = resp.cookies.get("optiflow_token")
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}

    @task(3)
    def list_clients(self) -> None:
        page = random.randint(1, 5)
        self.client.get(
            f"{API_BASE}/clients?page={page}",
            headers=self.headers,
            name="GET /clients?page=N",
        )

    @task(3)
    def list_actions(self) -> None:
        self.client.get(f"{API_BASE}/action-items", headers=self.headers, name="GET /action-items")

    @task(2)
    def dashboard_metrics(self) -> None:
        self.client.get(f"{API_BASE}/dashboard/kpis", headers=self.headers, name="GET /dashboard/kpis")

    @task(2)
    def list_cases(self) -> None:
        self.client.get(f"{API_BASE}/cases?page=1", headers=self.headers, name="GET /cases?page=1")

    @task(1)
    def list_factures(self) -> None:
        self.client.get(f"{API_BASE}/factures?page=1", headers=self.headers, name="GET /factures?page=1")

    @task(1)
    def health(self) -> None:
        # Appel public, sans auth
        self.client.get(f"{API_BASE}/admin/health", name="GET /admin/health")
