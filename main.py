import json
import requests
from fastapi import FastAPI
from pydantic import BaseModel
import re
import jieba
import jieba.analyse
import jieba.posseg
from bs4 import BeautifulSoup
import itertools

app = FastAPI()


class DouYinParam(BaseModel):
    url: str


class EmojiParam(BaseModel):
    text: str


class DouYinJson:
    def __init__(self, prompt, user_name, media_url, images):
        self.prompt = prompt
        self.user_name = user_name
        self.media_url = media_url
        self.images = images


class EmojiJson:
    def __init__(self, prompt, translation, images):
        self.prompt = prompt
        self.translation = translation
        self.images = images


COMBINED_EMOJI = {}
SUPPORTED_EMOJI = {}


class GlobalEmojiData:
    def __init__(self):
        self.supportedEmoji = SUPPORTED_EMOJI
        self.combinedEmoji = COMBINED_EMOJI


def get_global_emoji_data():
    return GlobalEmojiData()


@app.get("/")
async def get_main():
    return {"message": "service is running"}


@app.post("/emoji/")
async def emoji_service(param: EmojiParam):
    return await emoji_service_core(param.text)


async def emoji_service_core(text: str):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.3',
    }

    # 分词Top5
    subWordList = jieba.analyse.extract_tags(text, topK=5)

    finalEmojiList = []
    # 将每个分词转换成对应的emoji表情
    for word in subWordList:
        emojiList = []
        searchResponse = requests.get(url='https://emojixd.com/search?q=' + word, headers=headers)
        soup = BeautifulSoup(searchResponse.text, 'html.parser').find('body')
        divs = soup.find_all('div', class_='emoji left mr2 h1')[:5]
        for div in divs:
            print(div.text)
            emojiList.append(div.text)
        finalEmojiList.append(emojiList)

    # 过滤空的元素
    finalEmojiList = list(filter(None, finalEmojiList))

    print("emoji_list", finalEmojiList)
    if len(finalEmojiList) == 1:
        finalEmojiList.append(finalEmojiList[0])

    # 两两组合
    combinedEmojiData = itertools.combinations(finalEmojiList, 2)

    emojiImagesList = []
    for emojiTuple in combinedEmojiData:
        firstEmojiList = emojiTuple[0]
        secondEmojiList = emojiTuple[1]
        combinedEmojiList = list(itertools.product(firstEmojiList, secondEmojiList))
        for t in combinedEmojiList:
            url = get_url_from_emoji_kitchen(t[0], t[1])
            if url:
                emojiImagesList.append({"emoji_url": url})

    # 整句翻译
    translation = await get_emoji_translation(text)
    if len(emojiImagesList) < 3:
        emojiTranslation = list(filter_emoji(translation))
        combinedEmojiList = list(itertools.product(emojiTranslation, emojiTranslation))
        for t in combinedEmojiList:
            url = get_url_from_emoji_kitchen(t[0], t[1])
            if url:
                emojiImagesList.append({"emoji_url": url})

    prompt = "这是用户当前输入消息对应的Emoji处理。translation是用户当前消息的Emoji翻译，" \
             "images是用户当前消息对应状态的Emoji图片链接。" \
             "请将translation、emoji_url都为用户展示出来。请将所有的图片都展示出来。" \
             "请直接告诉用户[当前消息对应的emoji为translation]。"
    result = json.dumps(EmojiJson(prompt, translation, emojiImagesList).__dict__)
    return {"result": json.loads(result)}


async def get_emoji_translation(text: str):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.3',
    }
    url = "https://www.qudou100.com/apis/yule/wordtoemjio"
    data = {
        'word': text
    }
    response = requests.post(url, headers=headers, data=data)
    return json.loads(response.text)['data']


def get_url_from_emoji_kitchen(firstEmoji: str, secondEmoji: str):
    emojiData = get_emoji_json()['data']
    knownSupportedEmoji = get_supported_emoji()['knownSupportedEmoji']

    firstEmojiUnicode = emoji_to_unicode(firstEmoji)
    secondEmojiUnicode = emoji_to_unicode(secondEmoji)

    if firstEmojiUnicode == '' or secondEmojiUnicode == '':
        return ''

    url = ""
    if firstEmojiUnicode in knownSupportedEmoji:
        url = get_composed_emoji_url(emojiData[firstEmojiUnicode], firstEmojiUnicode, secondEmojiUnicode)

    if not url and secondEmojiUnicode in knownSupportedEmoji:
        url = get_composed_emoji_url(emojiData[secondEmojiUnicode], secondEmojiUnicode, firstEmojiUnicode)

    return url


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

    prompt = "这是user_name发布的抖音视频，如果images中有数据，则这个视频是抖音的图文视频，" \
             "images中的image_url是视频中图片的下载链接集合，media_url是视频背景音乐的下载链接。" \
             "如果images中没有数据，则media_url是视频的下载链接。" \
             "请将user_name、image_url、media_url都为用户展示出来，请将所有的图片都展示出来，user_name不是一个可以访问的链接，" \
             "请以普通文本的方式展示。"
    if check_music(vid):
        images = video_data['images']
        image_url_list = []
        for image in images:
            image_url_list.append({"image_url": image['url_list'][0]})
        audio_url = vid
        if not check_url(vid):
            audio_url = "https://www.iesdouyin.com/aweme/v1/play/?ratio=1080p&line=0&video_id=" + vid
        result = json.dumps(DouYinJson(prompt, user_name, audio_url, image_url_list).__dict__)
        return {"result": json.loads(result)}
    else:
        video_url = "https://www.iesdouyin.com/aweme/v1/play/?ratio=1080p&line=0&video_id=" + vid
        result = json.dumps(DouYinJson(prompt, user_name, video_url, []).__dict__)
        return {"result": json.loads(result)}


def check_url(url: str):
    if url.startswith("http") or url.startswith("https"):
        return True
    else:
        return False


def check_music(vid: str):
    if 'mp3' in vid or 'music' in vid:
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


def read_json_file(filename):
    with open(filename, 'r') as f:
        data = json.load(f)
    return data


def emoji_to_unicode(emoji_str):
    if len(emoji_str) != 1:
        return ''
    return hex(ord(emoji_str))[2:].zfill(4)


def get_emoji_json():
    global COMBINED_EMOJI
    if not COMBINED_EMOJI:
        COMBINED_EMOJI = read_json_file("emoji_data.json")
    return COMBINED_EMOJI


def get_supported_emoji():
    global SUPPORTED_EMOJI
    if not SUPPORTED_EMOJI:
        SUPPORTED_EMOJI = read_json_file("supported_emoji.json")
    return SUPPORTED_EMOJI


def get_composed_emoji_url(data: dict, firstEmojiCode: str, secondEmojiCode: str):
    for item in data['combinations']:
        if item['leftEmojiCodepoint'] == secondEmojiCode:
            return "https://www.gstatic.com/android/keyboard/emojikitchen/" + item['date'] + \
                   '/u' + item['leftEmojiCodepoint'] + "/u" + item['leftEmojiCodepoint'] + '_u' + \
                   firstEmojiCode + ".png"
    return ''


def filter_emoji(src):
    emoji_pattern = re.compile(u'[\U0001F300-\U0001F7D9]')
    return "".join(emoji_pattern.findall(src))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=80)
