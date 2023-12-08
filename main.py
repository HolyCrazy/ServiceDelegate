from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import shutil
import asyncio
from git import Repo

app = FastAPI()


class GitRepo(BaseModel):
    git_url: str


@app.get("/")
async def get_main():
    return {"message": "liduodiyi"}


@app.post("/liduo/")
async def print_repo_url(repo: GitRepo):
    return {"message": "liduozuishuai"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=80)