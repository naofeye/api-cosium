"""
Load test for OptiFlow API.
Usage: pip install locust && locust -f scripts/load_test.py --host=http://localhost:8000
Then open http://localhost:8089 to start the test.
"""

from locust import HttpUser, between, task


class OptiFlowUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self) -> None:
        """Login and get auth cookies."""
        self.client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@optiflow.local",
                "password": "Admin123",
            },
        )

    @task(5)
    def dashboard(self) -> None:
        self.client.get("/api/v1/dashboard/summary")

    @task(3)
    def list_clients(self) -> None:
        self.client.get("/api/v1/clients?page=1&page_size=25")

    @task(3)
    def list_cases(self) -> None:
        self.client.get("/api/v1/cases")

    @task(2)
    def list_devis(self) -> None:
        self.client.get("/api/v1/devis")

    @task(2)
    def list_factures(self) -> None:
        self.client.get("/api/v1/factures")

    @task(1)
    def analytics(self) -> None:
        self.client.get("/api/v1/analytics/dashboard")

    @task(1)
    def search(self) -> None:
        self.client.get("/api/v1/search?q=Dupont")

    @task(1)
    def notifications(self) -> None:
        self.client.get("/api/v1/notifications/unread-count")
