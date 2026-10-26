from fastapi import FastAPI

from modules.user.router import router as user_router
from modules.knowledge.router import router as knowledge_router
from modules.admin.router import router as admin_router
from modules.leave.router import router as leave_router
from modules.assistant.router import router as assistant_router
from modules.audio.router import router as audio_router
from modules.audio.job_router import router as audio_job_router

app = FastAPI()

app.include_router(user_router)

app.include_router(knowledge_router)

app.include_router(admin_router)

app.include_router(leave_router)

app.include_router(assistant_router)


app.include_router(audio_job_router)
app.include_router(audio_router)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


@app.post("/post/postData")
async def say_postData(username: str,role:str):
    return {"message": f"Hello {username}: {role}"}