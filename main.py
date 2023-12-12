import json
import requests
from fastapi import FastAPI
from pydantic import BaseModel
import re

app = FastAPI()


class DouYinParam(BaseModel):
    url: str


class DouYinJson:
    def __init__(self, prompt, user_name, media_url, images_url):
        self.prompt = prompt
        self.user_name = user_name
        self.media_url = media_url
        self.images_url = images_url


@app.get("/")
async def get_main():
    return {"message": "service is running"}


@app.get("/video/")
async def video_service():
    url = "https://upos-sz-mirrorcos.bilivideo.com/upgcxcode/90/60/1333896090/1333896090-1-192.mp4?e=ig8euxZM2rNcNbRV7bdVhwdlhWdjhwdVhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=\u0026uipk=5\u0026nbs=1\u0026deadline=1702356542\u0026gen=playurlv2\u0026os=cosbv\u0026oi=0\u0026trid=2734d6deb1eb454fa9e3b1490ebef500u\u0026mid=10031920\u0026platform=pc\u0026upsig=14a8575ffa2298544798db6ab22c9e5c\u0026uparams=e,uipk,nbs,deadline,gen,os,oi,trid,mid,platform\u0026bvc=vod\u0026nettype=0\u0026orderid=0,3\u0026buvid=A2A051FC-3266-C93B-6CFE-CA06FD97E40A10084infoc\u0026build=0\u0026f=u_0_0\u0026agrr=0\u0026bw=106135\u0026logo=80000000"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.3',
        'Referer': 'https://www.bilibili.com/video/BV1Pr4y1z7Tf/',
        'Accept-Encoding': 'gzip'
    }

    response = requests.get(url, headers=headers, stream=True)

    with open("test.flv", 'wb') as file:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                file.write(chunk)
    return {"result": "success"}


@app.post("/douyin/")
async def douyin_service(param: DouYinParam):
    return await douyin_service_core(param.url)


async def douyin_service_core(url: str):
    share_url = find_urls(url)[0]
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.3',
    }
    short_to_long_api = "https://api.oioweb.cn/api/site/UrlRevert?url="
    long_link_resp = requests.get(short_to_long_api + share_url, headers=headers)
    origin_share_url = json.loads(long_link_resp.text)
    video_id = find_video_id(origin_share_url['result'])[0]
    video_info_url = "https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?reflow_source=reflow_page&a_bogus=hdah&item_ids="
    video_info_resp = requests.get(video_info_url + video_id, headers=headers)
    video_data = json.loads(video_info_resp.text)['item_list'][0]
    vid = video_data['video']['play_addr']['uri']
    user_name = video_data['author']['nickname']

    prompt = "这是user_name发布的抖音视频，如果images_url中有数据，则这个视频是抖音的图文视频，" + \
             "images_url是视频中图片的下载链接集合，media_url是视频背景音乐的下载链接。" + \
             "如果images_url中没有数据，则media_url是视频的下载链接。" + \
             "请将user_name、images_url、media_url都为用户展示出来，user_name不是一个可以访问的链接，" \
             "请以普通文本的方式展示。"
    if check_url(vid):
        images = json.loads(video_info_resp.text)['item_list'][0]['images']
        image_url_list = []
        for image in images:
            image_url_list.append({"image": image['url_list'][0]})

        result = json.dumps(DouYinJson(prompt, user_name, vid, image_url_list).__dict__)
        return {"result": json.loads(result)}
    else:
        video_url = "https://www.iesdouyin.com/aweme/v1/play/?ratio=1080p&line=0&video_id=" + vid
        result = json.dumps(DouYinJson(prompt, user_name, video_url, []).__dict__)
        return {"result": json.loads(result)}


def check_url(url):
    if url.startswith("http") or url.startswith("https"):
        return True
    else:
        return False


def find_urls(text):
    pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    urls = re.findall(pattern, text)
    return urls


def find_video_id(url):
    pattern = r'video/(\d+)/'
    urls = re.findall(pattern, url)
    return urls


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=80)
