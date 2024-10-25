import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import router

app = FastAPI()

origins = [
    "http://localhost",
    "http://127.0.0.1",
    "https://annko.jp"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthcheck")
def nice():
    return "healthy!"

@app.get("/nicerace")
def nice():
    return "nice!"

app.router.include_router(router.router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run(app, host="localhost")