Perf testing guide

1. Build the backend image and start the stack:

```bash
cd backend
# build image (assumes Dockerfile exists in backend/)
docker compose -f docker-compose.perf.yml up --build -d

# wait for services to be healthy
sleep 5
```

2. Run Locust (locally or in a separate container). Example local run (in the backend venv):

```bash
# install locust in your venv: pip install locust
cd backend
locust -f tests/locustfile.py --host http://localhost:8000
```

3. Open http://localhost:8089 in your browser to start a test (default Locust UI port).

4. After testing, bring down the stack:

```bash
docker compose -f docker-compose.perf.yml down
```

Notes:
- The docker-compose file starts Redis and the backend (uvicorn). Adjust CPU/memory limits in compose as needed.
- If your app requires authentication for endpoints under test, update `tests/locustfile.py` to perform login in `on_start()` and reuse tokens in headers.
*** End Patch