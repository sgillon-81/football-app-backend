from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/ping")
async def ping():
    return {"message": "pong"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
