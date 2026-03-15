from locust import HttpUser, task, between

class ShortenerLoadUser(HttpUser):
    wait_time = between(1, 2)

    @task(1)
    def create_link(self):
        self.client.post("/links/shorten", json={
            "original_url": "https://example.com",
            "custom_alias": None
        })

    @task(3)
    def get_root(self):
        self.client.get("/")

class LinkShortenerUser(HttpUser):
    wait_time = between(1, 3)

    @task(2)
    def create_link(self):
        self.client.post("/links/shorten", json={
            "original_url": "https://example.com",
            "custom_alias": None
        })

    @task(5)
    def redirect(self):
        self.client.get("/test", name="/{short_code}")

    @task(1)
    def get_stats(self):
        self.client.get("/links/test/stats", name="/links/{short_code}/stats")