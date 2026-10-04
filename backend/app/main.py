from fastapi import FastAPI

app = FastAPI(title="AERIS API", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "aeris-backend"}
