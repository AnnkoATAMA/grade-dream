import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import router

app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/nicerace")
def health():
    return "nice!"

app.router.include_router(router.router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run(app, host="localhost")