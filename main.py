import json
from io import BytesIO
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

app = FastAPI()


class ImageInfo(BaseModel):
    url: str


class EmojiServiceParam(BaseModel):
    firstEmoji: str
    secondEmoji: str


@app.get("/")
async def get_main():
    return {"message": "service is running"}


@app.post("/emoji_kitchen/")
async def emoji_service(param: EmojiServiceParam):
    response = load_page("https://emoji.supply/kitchen/?" + param.firstEmoji + "+" + param.secondEmoji)
    soup = BeautifulSoup(response, 'html.parser')
    image_src = soup.find('img', id='pc').get('src')
    return {"image_url": image_src}


def load_page(url):
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Firefox(options=options)
    driver.get(url)
    content = driver.page_source
    driver.quit()
    return content


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=80)
