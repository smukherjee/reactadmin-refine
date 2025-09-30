from locust import HttpUser, between, task


class APIUser(HttpUser):
    wait_time = between(0.5, 2.0)

    def on_start(self):
        # Optionally perform login if your app requires authentication
        pass

    @task(5)
    def get_info(self):
        self.client.get("/api/v1/info")

    @task(3)
    def health(self):
        self.client.get("/health")

    @task(2)
    def metrics(self):
        self.client.get("/metrics")
