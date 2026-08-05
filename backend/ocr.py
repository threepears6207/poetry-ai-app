import base64
import os
import re

from difflib import SequenceMatcher
from typing import Optional

import requests
from fastapi import APIRouter
from pydantic import BaseModel, Field

from poems import load_poems


router = APIRouter()



class PhotoRequest(BaseModel):
    """
    拍照识诗请求。

    支持三种模式：

    1. text
       已有文字，直接检索诗库

    2. image_base64
       图片上传：
       OCR文字识别
       +
       风景识别

    3. multimodal
       端侧 vivo 多模态模型已经完成图片理解，
       后端直接接收结构化结果。
    """


    # 图片base64
    image: Optional[str] = ""


    # OCR文字 / 端侧识别文字
    text: Optional[str] = ""


    # 模式
    mode: Optional[str] = "text"



    # =========================
    # 新增：端侧多模态字段
    # =========================


    # 图片类型
    #
    # text_poem:
    #   课本诗句
    #
    # handwritten:
    #   手写古诗
    #
    # scene:
    #   风景图片
    image_type: Optional[str] = ""



    # 端侧识别出的物体

    objects: list[str] = Field(
        default_factory=list
    )



    # 端侧识别出的场景标签

    scene_tags: list[str] = Field(
        default_factory=list
    )



    # 模型置信度

    confidence: float = 0.0





def normalize_text(
        text: str
):

    """
    清洗文字。

    去除：
    空格
    标点
    特殊符号
    """


    if not text:

        return ""


    text = text.strip()


    text = re.sub(
        r"[\s，。！？；：、“”‘’（）《》〈〉,.!?;:\"'()\[\]{}<>-]",
        "",
        text
    )


    return text





def clean_base64_image(
        image_base64: str
):

    """
    清理base64图片。
    """


    if not image_base64:

        raise ValueError(
            "image不能为空"
        )



    image_data = image_base64.strip()



    if "," in image_data:

        image_data = image_data.split(
            ",",
            1
        )[1]



    try:

        base64.b64decode(
            image_data
        )


    except Exception:

        raise ValueError(
            "非法base64图片"
        )


    return image_data





def get_baidu_access_token(
        api_key_env: str,
        secret_key_env: str,
        service_name: str
):


    api_key = os.getenv(
        api_key_env
    )


    secret_key = os.getenv(
        secret_key_env
    )



    if not api_key or not secret_key:

        raise RuntimeError(
            f"{service_name}配置缺失"
        )



    response = requests.get(

        "https://aip.baidubce.com/oauth/2.0/token",

        params={

            "grant_type":
                "client_credentials",

            "client_id":
                api_key,

            "client_secret":
                secret_key

        },

        timeout=15

    )



    response.raise_for_status()



    result = response.json()



    token = result.get(
        "access_token"
    )



    if not token:

        raise RuntimeError(
            f"{service_name}获取token失败"
        )



    return token





def get_baidu_ocr_access_token():

    return get_baidu_access_token(

        "BAIDU_OCR_API_KEY",

        "BAIDU_OCR_SECRET_KEY",

        "百度OCR"

    )





def get_baidu_image_access_token():

    return get_baidu_access_token(

        "BAIDU_IMAGE_API_KEY",

        "BAIDU_IMAGE_SECRET_KEY",

        "百度图像识别"

    )





def baidu_ocr_text(
        image_base64: str
):

    """
    百度OCR文字识别。
    """


    image_data = clean_base64_image(
        image_base64
    )



    token = get_baidu_ocr_access_token()



    url = (

        "https://aip.baidubce.com/"

        "rest/2.0/ocr/v1/general_basic"

        f"?access_token={token}"

    )



    response = requests.post(

        url,

        headers={

            "Content-Type":

            "application/x-www-form-urlencoded"

        },

        data={

            "image":

            image_data

        },

        timeout=20

    )



    response.raise_for_status()



    result = response.json()



    if "error_code" in result:

        raise RuntimeError(
            f"OCR失败:{result}"
        )



    words = result.get(
        "words_result",
        []
    )



    return "".join(

        item.get(
            "words",
            ""
        )

        for item in words

        if item.get("words")

    )





def baidu_scene_tags(
        image_base64: str
):

    """
    百度图像识别。

    返回：

    [
        "湖",
        "天空",
        "树"
    ]

    """


    image_data = clean_base64_image(
        image_base64
    )



    token = get_baidu_image_access_token()



    url = (

        "https://aip.baidubce.com/"

        "rest/2.0/image-classify/v2/"

        "advanced_general"

        f"?access_token={token}"

    )



    response = requests.post(

        url,

        headers={

            "Content-Type":

            "application/x-www-form-urlencoded"

        },

        data={

            "image":

            image_data

        },

        timeout=20

    )



    response.raise_for_status()



    result = response.json()



    if "error_code" in result:

        raise RuntimeError(
            f"图像识别失败:{result}"
        )



    tags = []



    for item in result.get(
        "result",
        []
    ):


        keyword = item.get(
            "keyword"
        )


        root = item.get(
            "root"
        )



        if keyword:

            tags.append(
                keyword
            )


        if root:

            tags.append(
                root
            )



    return list(
        dict.fromkeys(tags)
    )
def search_poem_candidates_by_text(
        recognized_text: str
):

    """
    根据文字搜索候选诗。

    返回：

    [
        {
            poem:{},
            score:xx
        }
    ]
    """

    poems = load_poems()


    cleaned_input = normalize_text(
        recognized_text
    )


    if not cleaned_input:

        return []



    candidates = []



    for poem in poems:


        title = poem.get(
            "title",
            ""
        )


        author = poem.get(
            "author",
            ""
        )


        content_list = poem.get(
            "content",
            []
        )


        score = 0

        strong_match = False



        clean_title = normalize_text(
            title
        )


        clean_author = normalize_text(
            author
        )


        clean_content = normalize_text(
            "".join(content_list)
        )



        # 标题匹配

        if clean_title and clean_title in cleaned_input:

            score += 20

            strong_match = True



        # 作者匹配

        if clean_author and clean_author in cleaned_input:

            score += 5



        # 完整正文匹配

        if clean_content and clean_content in cleaned_input:

            score += 50

            strong_match = True



        # 单句匹配

        for line in content_list:


            clean_line = normalize_text(
                line
            )


            if not clean_line:

                continue



            similarity = SequenceMatcher(
                None,
                clean_line,
                cleaned_input
            ).ratio()



            if clean_line in cleaned_input:

                score += 10

                strong_match = True


            elif similarity >= 0.82:

                score += 5



        if strong_match:

            candidates.append(

                {
                    "poem":
                        poem,

                    "score":
                        score

                }

            )



    candidates.sort(

        key=lambda x:x["score"],

        reverse=True

    )


    return candidates[:3]







def expand_scene_keywords(
        scene_tags:list[str]
):

    """
    将图片标签转换为诗歌主题关键词。

    例如：

    湖
    ↓
    水、自然、山水


    月
    ↓
    月亮、夜晚、思乡

    """


    keywords = []



    scene_map = {


        "月":
            [
                "月亮",
                "夜晚",
                "思乡"
            ],



        "夜":
            [
                "夜晚",
                "月亮",
                "思乡"
            ],



        "天空":
            [
                "自然"
            ],



        "云":
            [
                "自然",
                "山水"
            ],



        "山":
            [
                "山水",
                "自然",
                "登高"
            ],



        "湖":
            [
                "水",
                "自然",
                "山水"
            ],



        "河":
            [
                "水",
                "自然"
            ],



        "水":
            [
                "水",
                "自然"
            ],



        "花":
            [
                "春天",
                "自然"
            ],



        "春":
            [
                "春天",
                "自然",
                "花",
                "鸟"
            ],



        "鸟":
            [
                "鸟",
                "动物",
                "自然"
            ],



        "树":
            [
                "自然",
                "春天"
            ],



        "草":
            [
                "自然",
                "春天"
            ],



        "雪":
            [
                "冬天",
                "自然"
            ],



        "雨":
            [
                "春天",
                "自然"
            ]

    }



    for tag in scene_tags:


        for key, values in scene_map.items():


            if key in tag:

                keywords.extend(
                    values
                )



    return list(
        dict.fromkeys(
            keywords
        )
    )








def search_scene_poem_candidates(
        scene_tags:list[str]
):

    """
    根据风景标签搜索候选诗。


    检索字段：

    tags

    theme_tags

    knowledge_tags


    返回：

    [
        {
            poem:{},
            score:xx
        }
    ]

    """



    poems = load_poems()



    keywords = expand_scene_keywords(
        scene_tags
    )



    if not keywords:

        return []



    candidates = []



    for poem in poems:


        score = 0



        title = poem.get(
            "title",
            ""
        )



        tags = poem.get(
            "tags",
            []
        )


        theme_tags = poem.get(
            "theme_tags",
            []
        )


        knowledge_tags = poem.get(
            "knowledge_tags",
            []
        )



        all_tags = (

            tags

            +

            theme_tags

            +

            knowledge_tags

        )



        tag_text = normalize_text(
            "".join(all_tags)
        )



        title_text = normalize_text(
            title
        )



        for keyword in keywords:


            clean_keyword = normalize_text(
                keyword
            )


            if not clean_keyword:

                continue



            # 标签匹配

            if clean_keyword in tag_text:

                score += 8



            # 标题匹配

            if clean_keyword in title_text:

                score += 10



        if score > 0:


            candidates.append(

                {
                    "poem":
                        poem,

                    "score":
                        score

                }

            )



    candidates.sort(

        key=lambda x:x["score"],

        reverse=True

    )


    return candidates[:3]







def build_candidate_response(
        candidate
):

    """
    构造统一诗卡返回格式。
    """


    poem = candidate.get(
        "poem",
        {}
    )



    return {


        "id":
            poem.get("id"),



        "title":
            poem.get("title"),



        "author":
            poem.get("author"),



        "dynasty":
            poem.get("dynasty"),



        "content":
            poem.get(
                "content",
                []
            ),



        "tags":
            poem.get(
                "tags",
                []
            ),



        "theme_tags":
            poem.get(
                "theme_tags",
                []
            ),



        "score":
            candidate.get(
                "score",
                0
            )

    }
@router.post("/ocr")
def recognize_photo(
        request: PhotoRequest
):
    """
    拍照识诗统一接口。


    支持：

    1. text

    文字直接搜索诗库


    2. image_base64

    图片:
        OCR
        ↓
        文字匹配

    失败:
        风景识别


    3. multimodal

    接收端侧vivo多模态结果：

    {
        image_type,
        objects,
        scene_tags,
        confidence
    }

    """


    mode = request.mode or "text"



    try:



        # ==================================
        # 模式1：纯文字
        # ==================================

        if mode == "text":


            recognized_text = (

                request.text

                or

                request.image

                or

                ""

            )



            candidates = (

                search_poem_candidates_by_text(

                    recognized_text

                )

            )



            if not candidates:


                return {


                    "success":False,


                    "mode":mode,


                    "match_type":"text",



                    "recognized_text":

                        recognized_text,



                    "candidates":[],



                    "message":

                        "未匹配到对应古诗"

                }




            candidate_data = [

                build_candidate_response(item)

                for item in candidates

            ]



            return {



                "success":True,


                "mode":mode,


                "match_type":"text",



                "recognized_text":

                    recognized_text,



                "candidates":

                    candidate_data,



                # 兼容旧前端

                "data":

                    candidate_data[0],



                "matched_poem":

                    candidate_data[0]

            }






        # ==================================
        # 模式2：图片上传
        # ==================================

        if mode == "image_base64":



            if not request.image:


                return {


                    "success":False,


                    "mode":mode,


                    "message":

                        "image不能为空"

                }




            # ------------------------------
            # 第一步 OCR
            # ------------------------------


            recognized_text = (

                baidu_ocr_text(

                    request.image

                )

            )



            text_candidates = (

                search_poem_candidates_by_text(

                    recognized_text

                )

            )




            if text_candidates:


                candidate_data = [

                    build_candidate_response(item)

                    for item in text_candidates

                ]



                return {


                    "success":True,


                    "mode":mode,


                    "match_type":"text",



                    "recognized_text":

                        recognized_text,



                    "candidates":

                        candidate_data,



                    "data":

                        candidate_data[0],



                    "matched_poem":

                        candidate_data[0]

                }




            # ------------------------------
            # 第二步 风景识别
            # ------------------------------


            scene_tags = (

                baidu_scene_tags(

                    request.image

                )

            )



            scene_candidates = (

                search_scene_poem_candidates(

                    scene_tags

                )

            )




            if not scene_candidates:


                return {


                    "success":False,


                    "mode":mode,


                    "match_type":"scene",



                    "recognized_text":

                        recognized_text,



                    "scene_tags":

                        scene_tags,



                    "candidates":[],



                    "message":

                        "未匹配到风景古诗"

                }




            candidate_data = [

                build_candidate_response(item)

                for item in scene_candidates

            ]



            return {



                "success":True,


                "mode":mode,


                "match_type":"scene",



                "recognized_text":

                    recognized_text,



                "scene_tags":

                    scene_tags,



                "candidates":

                    candidate_data,



                "data":

                    candidate_data[0],



                "matched_poem":

                    candidate_data[0]

            }






        # ==================================
        # 模式3：vivo多模态输入
        # ==================================

        if mode == "multimodal":



            # ------------------------------
            # 优先使用端侧文字
            # ------------------------------


            if request.text:



                text_candidates = (

                    search_poem_candidates_by_text(

                        request.text

                    )

                )



                if text_candidates:



                    candidate_data = [

                        build_candidate_response(item)

                        for item in text_candidates

                    ]



                    return {



                        "success":True,


                        "mode":mode,


                        "match_type":"text",



                        "recognized_text":

                            request.text,



                        "image_type":

                            request.image_type,



                        "confidence":

                            request.confidence,



                        "candidates":

                            candidate_data,



                        "data":

                            candidate_data[0],



                        "matched_poem":

                            candidate_data[0]

                    }






            # ------------------------------
            # 无文字，使用场景标签
            # ------------------------------



            scene_tags = request.scene_tags



            if not scene_tags:


                scene_tags = request.objects





            scene_candidates = (

                search_scene_poem_candidates(

                    scene_tags

                )

            )



            if not scene_candidates:


                return {



                    "success":False,


                    "mode":mode,


                    "match_type":"scene",



                    "image_type":

                        request.image_type,



                    "scene_tags":

                        scene_tags,



                    "confidence":

                        request.confidence,



                    "candidates":[],



                    "message":

                        "未匹配到风景古诗"

                }




            candidate_data = [

                build_candidate_response(item)

                for item in scene_candidates

            ]



            return {



                "success":True,


                "mode":mode,


                "match_type":"scene",



                "image_type":

                    request.image_type,



                "objects":

                    request.objects,



                "scene_tags":

                    scene_tags,



                "confidence":

                    request.confidence,



                "candidates":

                    candidate_data,



                "data":

                    candidate_data[0],



                "matched_poem":

                    candidate_data[0]

            }





        return {


            "success":False,


            "mode":mode,


            "message":

                "mode参数错误"

        }




    except Exception as e:



        return {


            "success":False,


            "mode":mode,


            "message":

                "拍照识诗失败",


            "error":

                str(e)

        }