# async def emoji_service_core_v1(text: str):
#     # 分词Top5
#     subWordList = jieba.analyse.extract_tags(text, topK=5)
#
#     finalEmojiList = []
#     # 将每个分词转换成对应的emoji表情
#     for word in subWordList:
#         emojiList = []
#         searchResponse = requests.get(url='https://emojixd.com/search?q=' + word, headers=COMMON_HEADER)
#         soup = BeautifulSoup(searchResponse.text, 'html.parser').find('body')
#         divs = soup.find_all('div', class_='emoji left mr2 h1')[:5]
#         for div in divs:
#             emojiList.append(div.text)
#         finalEmojiList.append(emojiList)
#
#     # 过滤空的元素
#     finalEmojiList = list(filter(None, finalEmojiList))
#
#     if len(finalEmojiList) == 1:
#         finalEmojiList.append(finalEmojiList[0])
#
#     # 两两组合
#     combinedEmojiData = itertools.combinations(finalEmojiList, 2)
#
#     emojiImagesList = []
#     for emojiTuple in combinedEmojiData:
#         firstEmojiList = emojiTuple[0]
#         secondEmojiList = emojiTuple[1]
#         combinedEmojiList = list(itertools.product(firstEmojiList, secondEmojiList))
#         for t in combinedEmojiList:
#             url = get_url_from_emoji_kitchen(t[0], t[1])
#             if url:
#                 emojiImagesList.append({"emoji_url": url})
#
#     # 整句翻译
#     translation = await get_emoji_translation_v1(text)
#     if len(emojiImagesList) < 3:
#         emojiTranslation = list(filter_emoji(translation))
#         combinedEmojiList = list(itertools.product(emojiTranslation, emojiTranslation))
#         for t in combinedEmojiList:
#             url = get_url_from_emoji_kitchen(t[0], t[1])
#             if url:
#                 emojiImagesList.append({"emoji_url": url})
#
#     prompt = "这是用户当前输入消息对应的Emoji处理。translation是用户当前消息的Emoji翻译，" \
#              "images是用户当前消息对应状态的Emoji图片链接。" \
#              "请将translation、emoji_url都为用户展示出来。请将所有的图片都展示出来。" \
#              "请直接告诉用户[当前消息对应的emoji为translation]。"
#     result = json.dumps(EmojiJson(prompt, translation, emojiImagesList).__dict__)
#     return {"result": json.loads(result)}


# async def emoji_translation_service_v1(text: str):
#     url = "https://www.qudou100.com/apis/yule/wordtoemjio"
#     data = {
#         'word': text
#     }
#     response = requests.post(url, headers=COMMON_HEADER, data=data)
#     return json.loads(response.text)['data']
