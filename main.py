from io import BytesIO

from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI()


class ImageInfo(BaseModel):
    url: str


@app.get("/")
async def get_main():
    return {"message": "service is running"}


@app.post("/ocr/")
async def print_repo_url(info: ImageInfo):
    url = info.url
    response = requests.get(url)
    image_in_memory = BytesIO(response.content)
    response = requests.post('https://api.oioweb.cn/api/ocr/recognition', files={'file': image_in_memory})
    return {"response": response}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=80)
