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
import random

app = FastAPI()


class DouYinJson:
    def __init__(self, prompt, user_name, media_url, images):
        self.prompt = prompt
        self.user_name = user_name
        self.media_url = media_url
        self.images = images


class EmojiJson:
    def __init__(self, prompt, translation, emoji_images, recommend_images):
        self.prompt = prompt
        self.translation = translation
        self.emoji_images = emoji_images
        self.recommend_images = recommend_images


COMBINED_EMOJI = {}
SUPPORTED_EMOJI = {}

COMMON_HEADER = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                  ' Chrome/74.0.3729.169 Safari/537.3',
}


class GlobalEmojiData:
    def __init__(self):
        self.supportedEmoji = SUPPORTED_EMOJI
        self.combinedEmoji = COMBINED_EMOJI


def get_global_emoji_data():
    return GlobalEmojiData()


@app.get("/")
async def get_main():
    return {"message": "service is running"}


class EmojiParam(BaseModel):
    text: str


@app.post("/emoji_message/")
async def emoji_service(param: EmojiParam):
    return await emoji_service_core(param.text)


async def emoji_service_core(text: str):
    # 原始Emoji
    sourceEmojiList = list(filter_emoji(text))
    # 整句Emoji翻译
    translation = await emoji_translation_service(text)
    # 分词Top5
    subWordList = jieba.analyse.extract_tags(text, topK=5)
    # 合并列表
    finalEmojiList = []
    finalEmojiList.extend(sourceEmojiList)
    # 过滤翻译中的非Emoji字符
    finalEmojiList.extend(list(filter_emoji(translation)))

    # 将每个分词转换成对应的emoji表情
    for word in subWordList:
        searchResponse = requests.get(url='https://emojixd.com/search?q=' + word, headers=COMMON_HEADER)
        soup = BeautifulSoup(searchResponse.text, 'html.parser').find('body')
        divs = soup.find_all('div', class_='emoji left mr2 h1')[:5]
        for div in divs:
            finalEmojiList.append(div.text)

    # 过滤空元素
    finalEmojiList = list(filter(None, finalEmojiList))
    # 去重
    finalEmojiList = list(set(finalEmojiList))
    # 去掉组合Emoji
    finalEmojiList = list(filter(lambda emoji: len(emoji) <= 1, finalEmojiList))

    # 保证组合长度
    if len(finalEmojiList) == 1:
        finalEmojiList.append(finalEmojiList[0])

    # 两两组合
    combinedEmojiData = itertools.combinations(finalEmojiList, 2)
    # 获取Emoji的Url
    emojiImagesList = []
    for emojiTuple in combinedEmojiData:
        url = emoji_kitchen_service(emojiTuple[0], emojiTuple[1])
        if url:
            emojiImagesList.append({"image_url": url})

    # 获取推荐表情包
    recommendEmojiList = await emoji_search_service(text, 0, 30)
    # 去除无法访问的URL
    recommendEmojiList = list(filter(lambda x: url_valid(x['image_url']), recommendEmojiList))
    # 推荐数量
    if not emojiImagesList:
        recommendEmojiList = recommendEmojiList[:10]
    else:
        recommendEmojiList = recommendEmojiList[:5]
    # 乱序
    random.shuffle(recommendEmojiList)

    # 去重
    emojiImagesList = list({v['image_url']: v for v in emojiImagesList}.values())
    # 去除无法访问的URL
    emojiImagesList = list(filter(lambda x: url_valid(x['image_url']), emojiImagesList))
    # 乱序
    random.shuffle(emojiImagesList)
    # prompt = "这是用户当前输入消息对应的Emoji处理。translation是用户当前消息的Emoji翻译，" \
    #          "images是用户当前消息对应状态的Emoji图片链接。" \
    #          "请将translation、image_url都为用户展示出来。请将所有的图片都展示出来。" \
    #          "请直接告诉用户[当前消息对应的emoji为translation]。"
    result = json.dumps(EmojiJson('', translation, emojiImagesList, recommendEmojiList).__dict__)
    return {"result": json.loads(result)}


@app.get('/emoji_translation/')
async def emoji_translation_service(text: str):
    url = 'https://www.emojiall.com/zh-hans/text-to-emoji'
    data = {
        'text': text
    }
    response = requests.post(url, headers=COMMON_HEADER, data=data)
    return json.loads(response.text)['data']


@app.get('/emoji_search/')
async def emoji_search_service(text: str, start: int = 0, limit: int = 30):
    url = 'https://doutu.lccyy.com/doutu/all'
    data = {
        'ac': 'search',
        'start': start,
        'limit': limit,
        'keyword': text
    }
    response = requests.post(url=url, headers=COMMON_HEADER, data=data)
    item_info = json.loads(response.text)['items']
    result = []
    for info in item_info:
        result.append({"image_url": info['url']})
    return result


@app.get('/emoji_kitchen/')
def emoji_kitchen_service(firstEmoji: str, secondEmoji: str):
    emojiData = get_emoji_json()['data']
    knownSupportedEmoji = get_supported_emoji()['knownSupportedEmoji']

    firstEmojiUnicode = emoji_to_unicode(firstEmoji)
    secondEmojiUnicode = emoji_to_unicode(secondEmoji)

    if firstEmojiUnicode == '' or secondEmojiUnicode == '':
        return ''

    url = ""
    if firstEmojiUnicode in knownSupportedEmoji:
        url = compose_emoji_url(emojiData[firstEmojiUnicode], firstEmojiUnicode, secondEmojiUnicode)

    if not url and secondEmojiUnicode in knownSupportedEmoji:
        url = compose_emoji_url(emojiData[secondEmojiUnicode], secondEmojiUnicode, firstEmojiUnicode)

    return url


class DouYinParam(BaseModel):
    url: str


@app.post("/douyin/")
async def douyin_service(param: DouYinParam):
    return await douyin_service_core(param.url)


async def douyin_service_core(url: str):
    share_url = find_urls(url)[0]
    short_to_long_api = "https://api.oioweb.cn/api/site/UrlRevert?url="
    long_link_resp = requests.get(short_to_long_api + share_url, headers=COMMON_HEADER)
    origin_share_url = json.loads(long_link_resp.text)
    video_id = find_video_id(origin_share_url['result'])[0]
    video_info_url = "https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?reflow_source=reflow_page&a_bogus=hdah&item_ids="
    video_info_resp = requests.get(video_info_url + video_id, headers=COMMON_HEADER)
    video_data = json.loads(video_info_resp.text)['item_list'][0]
    vid = video_data['video']['play_addr']['uri']
    user_name = video_data['author']['nickname']

    prompt = "这是user_name发布的抖音视频，如果images中有数据，则这个视频是抖音的图文视频，" \
             "images中的image_url是视频中图片的下载链接集合，media_url是视频背景音乐的下载链接。" \
             "如果images中没有数据，则media_url是视频的下载链接。" \
             "请将user_name、image_url、media_url都为用户展示出来，请将所有的图片都展示出来，user_name不是一个可以访问的链接，" \
             "请以普通文本的方式展示。"
    if check_douyin_music(vid):
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


# 判断字符是否为URL
def check_url(url: str):
    if url.startswith("http") or url.startswith("https"):
        return True
    else:
        return False


# 检查vid是否为音频
def check_douyin_music(vid: str):
    if 'mp3' in vid or 'music' in vid:
        return True
    else:
        return False


# 从字符串中提取URL
def find_urls(text):
    pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    urls = re.findall(pattern, text)
    return urls


# 从URL中获取videoId
def find_video_id(url):
    pattern = r'video/(\d+)/'
    urls = re.findall(pattern, url)
    return urls


# 读取JSON文件
def read_json_file(filename):
    with open(filename, 'r') as f:
        data = json.load(f)
    return data


# 将Emoji转换为Unicode
def emoji_to_unicode(emoji_str):
    if len(emoji_str) > 1:
        emoji_list = [hex(ord(emoji))[2:].zfill(4) for emoji in list(emoji_str)]
        return '-'.join(emoji_list)
    return hex(ord(emoji_str))[2:].zfill(4)


# 获取包含Emoji编码的JSON文件
def get_emoji_json():
    global COMBINED_EMOJI
    if not COMBINED_EMOJI:
        COMBINED_EMOJI = read_json_file("emoji_data.json")
    return COMBINED_EMOJI


# 获取支持的Emoji列表
def get_supported_emoji():
    global SUPPORTED_EMOJI
    if not SUPPORTED_EMOJI:
        SUPPORTED_EMOJI = read_json_file("supported_emoji.json")
    return SUPPORTED_EMOJI


# 拼接合成后的Emoji的URL
def compose_emoji_url(data: dict, firstEmojiCode: str, secondEmojiCode: str):
    for item in data['combinations']:
        if item['leftEmojiCodepoint'] == secondEmojiCode:
            return "https://www.gstatic.com/android/keyboard/emojikitchen/" + item['date'] + \
                   '/u' + item['leftEmojiCodepoint'] + "/u" + item['leftEmojiCodepoint'] + '_u' + \
                   firstEmojiCode + ".png"
    return ''


# 去除字符串中所有的非Emoji字符
def filter_emoji(text: str):
    emoji_pattern = re.compile(u'[\U0001F300-\U0001F7D9]')
    return "".join(emoji_pattern.findall(text))


# 验证URL是否可以访问
def url_valid(url: str):
    try:
        response = requests.get(url, headers=COMMON_HEADER, timeout=3)
        if response.status_code == 200:
            return True
        else:
            return False
    except Exception as _:
        return False


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=80)
