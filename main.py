from fastapi import FastAPI

app = FastAPI(title="AsRun Analyzer")

@app.get("/")
async def root():
    return {"message": "AsRun Analyzer API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
