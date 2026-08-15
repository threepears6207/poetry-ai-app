import hashlib
import json
import os
import re
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests
from fastapi import APIRouter
from pydantic import AliasChoices, BaseModel, Field


router = APIRouter()

VIVO_VIDEO_SUBMIT_URL = "https://api-ai.vivo.com.cn/api/v1/submit_task"
VIVO_VIDEO_QUERY_URL = "https://api-ai.vivo.com.cn/api/v1/query_task"
VIVO_PLANNER_URL = "https://api-ai.vivo.com.cn/v1/chat/completions"
SUPPORTED_MODELS = {
    "Doubao-Seedance-1.0-pro",
    "Doubao-Seedance-2.0",
    "Doubao-Seedance-2.0-fast",
}
SUPPORTED_SHOT_TYPES = {"远景", "中景", "近景", "特写", "主观视角"}
SUPPORTED_CAMERA_MOTIONS = {"静止", "缓慢推进", "缓慢拉远", "缓慢平移"}
FIXED_VIDEO_DURATION_SECONDS = 12
MAX_POEM_LINES = 12

BASE_DIR = Path(__file__).parent
VIDEO_DIR = BASE_DIR / "static" / "videos" / "poems"
# 唯一的视频缓存：与正式 video.mp4 一起纳入版本控制，供所有协作者直接复用。
# 不再维护仅本机可见的 video_tasks_cache.json。
CACHE_FILE = BASE_DIR / "static" / "video_cache.json"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

_cache_lock = threading.Lock()


VIDEO_STYLE = (
    "高饱和、明亮、活泼的中国儿童二维卡通动画风格，横版16:9，适合3至7岁儿童观看。"
    "画面第一眼必须像儿童喜欢看的彩色动画片，而不是素雅古风插画、成人国风动画、电影动画、绘本静帧或半写实人物画。"
    "人物无论诗意中是儿童、成年人还是老人，都必须采用儿童卡通化造型：头部明显大于自然比例，约占人物总高度二分之一至三分之一；"
    "圆润或椭圆脸，饱满粉润面颊；眼睛是清楚、简洁的深色椭圆或弯月形；鼻子、嘴巴、眉毛简化且表情鲜明；"
    "身体、手脚、衣袖用胖短、圆润、柔软、易读的二维形状表达。成年身份只能借发式、服装、动作和气质表达，"
    "绝不画成细长脸、自然成人头身比、成熟写实面孔或电影角色。"
    "每一帧必须有鲜明、愉快的高明度彩色大色块，至少同时使用三种主色。优先使用天空蓝、湖水青、草绿、嫩黄、明黄、橙色、"
    "珊瑚粉、桃粉、朱红、宝蓝和亮紫；可少量使用米白作留白和高光，但米白、灰褐、深棕、暗蓝、灰蓝绝不能成为画面主色。"
    "天空、树叶、花朵、被褥、窗帘、衣服、庭院或其他与诗意相关的物体，应形成清晰、丰富、对儿童有吸引力的彩色区域；"
    "画面要明亮、轻快、有层次，而不是用一片浅灰、米白或棕色完成全景。"
    "保留国风水彩质感，但水彩只服务于活泼的卡通画面：使用轻微纸张纹理、柔和边缘和少量自然晕染；"
    "轮廓采用干净、柔和的深棕或淡墨线。禁止低饱和素雅水墨、大片留白导致画面空淡、灰褐木质感、真实木纹、复杂透视、"
    "摄影式晨昏光影、暗蓝电影夜景、赛璐璐硬阴影、粗黑线稿、3D塑料质感、真实照片感和成人动画比例。"
    "构图必须清楚、简洁且有儿童动画的活力：一个清晰主视觉，前景人物或核心意象可爱醒目，背景使用概括的大形状；"
    "树、鸟、花、云、水、山等均用圆润、概括、童趣的形状表达，不使用细密枝条、写实羽毛、真实植物结构或电影布景。"
    "允许眨眼、微笑、轻轻挥手、衣袖摆动、鸟儿扑翅、花瓣飘落、云朵移动、水面轻晃等温和可爱动作；"
    "镜头只允许缓慢推进、轻微平移、柔和水彩溶解或自然连贯转场，不使用快速闪烁、剧烈抖动、快剪或突然变暗。"
    "角色一旦建档，服装主色、辅色、滚边色、腰带色和固定配饰色必须全片固定。除非诗句明确规定特殊服制或颜色，"
    "角色服装必须以天空蓝、湖水青、草绿、嫩黄、明黄、橙色、珊瑚粉、桃粉、朱红、宝蓝或亮紫中的两至三种明亮颜色构成；"
    "黑色、白色、灰色、深棕、灰蓝、暗蓝不得成为人物服装的大面积主色，只可用于头发、轮廓线、鞋子、小型发饰或极少量边缘细节。"
    "夜晚、风雨、秋冬或安静情绪不得成为更换已建档服装颜色的理由。"
    "禁止文字、字幕、诗句、标题、Logo、水印、拼音、乱码、现代建筑、现代服装、现代家具、电子产品，以及恐怖、阴森、暴力、"
    "打斗、危险动作、肢体变形、五官漂移、人物凭空出现或消失。"
)

VIDEO_STYLE_FINAL_LOCK = (
    "【最终视觉锁定】高饱和明亮的中国儿童二维卡通动画风格。每一帧必须具备天空蓝、嫩黄、草绿、橙色、珊瑚粉、"
    "桃粉、朱红、宝蓝或亮紫中的至少三种鲜明主色，并呈现清晰的大色块和轻快的儿童动画氛围。人物必须是大头圆脸、"
    "粉润面颊、简化五官、胖短柔和的卡通比例；背景必须扁平简化、色彩丰富、主视觉清楚。水彩纸张纹理和柔边只能作为轻微质感，"
    "不能把画面变成低饱和、米白灰褐、安静素雅的成人古风插画。禁止成熟成人比例、细长写实脸、电影光影、复杂透视、"
    "灰褐米白主色、灰蓝夜景、半写实古风动画、摄影感、日漫少女脸、赛璐璐硬阴影、粗黑线稿和3D质感。"
    "无论诗句中的人物年龄为何，视觉造型都必须是儿童卡通化，而非写实成年人。"
)

VIDEO_CONSISTENCY_AUDIT = """【强制一致性与空间自检：生成前必须逐项满足】

角色档案必须是唯一确定的答案。identity_profile、visual_fingerprint、must_remain、locations.stable_elements 和 frames.visible_elements 中不得使用“约、约莫、大约、左右、或、或者、可、类似、随意、若干”等表示可替换或不确定的词。每个年龄、性别、脸型、五官比例、体型、发型、发饰、服装颜色、服装款式、固定配饰、树种、围栏或墙体均须一次选定，不得给备选项。

角色的姿势、镜头远近和表情可以变化，但角色外貌绝不可变化。即使睡觉、转身、起身、行走、进入回忆或跨独立视频片段，发髻不得散开，发簪不得消失，衣服颜色、衣服款式、腰带、体型、脸型、五官与人数不得变化。睡眠镜头不得用“头发散落”“衣衫变化”等描述替代既定人物档案。

空间必须物理自洽。糊纸窗在未打开时只能透出光感、影子或模糊轮廓，不能同时清晰看见庭院树枝、地面和雨景；若镜头需要清晰看见窗外，必须明确窗扇已打开，或镜头已切换到窗外或窗边视角。窗框、门框、檐口、船舷是硬边界；室外树干、树枝、泥土、草地、石板、积水和落花不得跨越边界进入室内，除非诗意明确、镜头明确说明了合理进入方式。

reality_mode 规则：没有实际想象画面的镜头只能为 real；只有画面真的呈现想象、回忆或虚景时才为 imagined；只有现实画面和想象画面同时可见时才为 mixed。entry_type 为 none 时，不得声称存在气泡、想象画面或想象范围。

转场必须舒缓。禁止“快速淡入淡出、突然变暗、闪现、突变”等表述；昼夜、回忆、风雨和空间变化只能用缓慢水彩溶解、光线渐变、窗景渐变或明确的自然切换表达。

输出前逐帧核查：人物人数与 characters.count 一致；人物外貌与唯一档案一致；场地、可见元素和 spatial_boundary 不冲突；该句核心意象清楚可见；没有把另一句的天气、人物、空间或元素错误带入本句。"""

VIDEO_PLANNER_SYSTEM_PROMPT = """你是一名专业的中国传统儿童绘本动画分镜导演。

你的任务是为任意一首中国古诗设计连续、可动画化、适合3至7岁儿童观看的横版国风水彩视频分镜。必须先完整理解全诗，再设计镜头。不得把某一首诗、某一句的位置、某一种天气、某个时间、某个角色或某种转场写成固定套路；每首诗都必须仅依据本次输入的诗句、作者、朝代和意象标签，独立推导人物、空间、时间、天气、动作、情绪和镜头变化。

分镜必须满足：
1. 人数是硬约束。人物类别、每类确切人数、角色关系与每个角色出现的诗句，全部由本诗语义决定。不得为了热闹添加儿童、诗人、路人、动物或配角；一个人的诗不得出现不相干人物；诗中确有多人、群体、主角与配角时，必须分别建档，并在对应镜头精确控制人数。
2. 年龄与性别不是默认约束。诗中明确儿童、老者、女子、男子、父子、兄弟等信息时必须遵守；诗中未明确时，可以自由设计年龄和性别，不得把儿童、男童、女童或诗人本人当成默认答案。无论如何，一旦为某个角色确定外貌，该角色在全部镜头、全部独立视频片段中必须保持同一张脸、同一发型、同一服装和同一人数。
3. 每个被命名人物或群体必须有可重复的详细视觉身份档案。身份档案不得出现“或、可、大约、类似、随意”等可变表述；必须一次选定脸型、眉眼比例、鼻唇特征、肤色、体型、发型、发饰、服装主色、辅色、滚边色、腰带色、固定配饰色和服装款式。不得换脸、换发髻、换衣服、换性别、忽胖忽瘦、五官漂移，或把一个人改成另一个人；群体人数不得无故增减。角色外貌与服装配色一旦选定，必须跨全诗全部镜头、全部独立片段完全一致，夜晚、风雨、季节或情绪变化均不得改变。
4. 场地按镜头而非按全诗一刀切。室内、室外、窗内望向窗外、船上望岸、庭院与山路等必须分别建档；每一镜只能出现其明确列出的可见场地和元素，不得把室内家具搬到室外，或把室外元素无故塞进室内。每个镜头必须写 spatial_boundary；若同时可见室内与室外，窗框、门框、檐口或船舷是明确物理边界，户外树干、树枝、泥土、石板、草地、积水和落花只能位于边界之外，室内地面、床榻、墙面和窗内不得出现这些户外元素。只有诗意明确要求且空间逻辑成立时，元素才可通过门窗进入，并必须说明原因。
5. 若诗句出现时间变化、天气变化、回忆、想象、视线转换或空间转换，必须在该句对应镜头中用可见场景、光线、天气、动作或自然转场表现。无文字云朵气泡推进镜头只在诗义确实是主动想象、思念或遥想时选用，不得套用到所有虚写句。
6. 每句最核心的意象必须成为画面主体或明确可见重点，而不是泛化成“人物难过”“人物发呆”。情绪强度不得超过原诗；惜春、感慨、宁静等轻微情绪优先使用环境、动作停顿、光线和色调表达，只有原诗明确表达强烈悲伤时才允许泪珠。
7. 画风必须严格遵守用户提供的 VIDEO_STYLE：高饱和、明亮、活泼的中国儿童二维卡通动画风格。每句镜头都必须为本句诗意独立推导三至五种明确颜色、颜色分布和色彩情绪；颜色必须服从时间、天气、季节、情绪和核心意象，不能为了鲜艳凭空添加诗意之外的物体、人物或天气。夜晚、风雨、秋冬、孤寂、惜别、思念、山雾和远行可以出现深色、冷色或安静画面，但必须保留儿童动画的清楚辨识、主色重点色对比色层次和至少一种鲜明重点色；不得变成灰蒙、脏褐、电影滤镜或写实阴郁画面。清晨、春天、晴朗、童趣、生机、鸟鸣、花叶、水面和节日等诗意，应优先用高明度颜色突出本句核心意象。不得生成日本动漫、美少女漫画、赛璐璐硬阴影、粗黑描边、写实电影、3D塑料质感或非国风的现代都市卡通。
8. 每个镜头必须确定摄影机锚点、人物空间锚点和观看方向。location_id 必须表示摄影机所在的实际物理空间，不得只因为窗外、门外、岸边或远景是画面主体就把 location_id 写成另一个空间。若诗句建立人物经窗、门、廊口、船舷或其他边界观看相邻空间，而当前句没有明确“走出、进入、登上、下船、穿过、来到、抵达”等跨空间动作，摄影机和人物必须持续停留在原空间；打开边界只改变可见范围，绝不代表人物整体跨越边界。人物可以自然把头部、视线、手臂、上半身或双手伸向边界外侧以看景、扶边界、推窗或互动，但下半身、双脚和臀部必须持续锚定在原空间，并从原空间自然延伸。若窗外、门外、岸边或相邻空间的意象是本句 primary_visual，必须明确边界已经打开或摄影机在边界内侧，使该意象清晰出现；不得用关闭的窗纸、模糊影子或只有声音替代。只有诗句明确跨空间时，才可先展示人物经过边界的连续动作，再切换摄影机位置。不得让人物整个人没有连续移动就突然出现在窗外、窗台外、门外、船外或另一空间，不得瞬移、跳变或用错误遮挡代替实际移动。
9. 人物、动物、群体、关系、动作主体和观察者只能依据本次输入 poem_content 中实际出现的诗句判断，不得依据诗题、作者、朝代、标签、推荐语、未传入的完整原诗、历史背景或外部常识新增。若本次全部诗句仅描述自然景物、建筑、器物、季节或自然现象，且没有明确人物、第一人称、第二人称、人物称谓、人物动作或人物关系，has_character 必须为 false，characters 必须为空数组，所有镜头不得添加任何角色或动物。每句的 primary_visual 必须包含该句最重要的具体意象或动作，并在 scene 和 visible_elements 中实际清楚出现，不得只画结果、影子、声音、文字、抽象情绪或事后痕迹替代。野火、风雨、雷电、冰雪、夜色等可以采用圆润、概括、非恐怖的儿童动画表现，但不得删除诗义：例如“野火烧不尽”必须可见小范围、可控的橙红野火和明黄火光，以及未被烧尽的草根或嫩绿草芽；不得出现人物靠近火源、受伤、惊恐、灾难或失控毁坏场面。

10. 每句镜头时长由服务端按“12秒 ÷ 输入诗句数”平均分配。每一镜最多安排一个主体主要动作和一个连续的镜头动作；主体动作只能是缓慢、可在该镜头时长内看清起止的动作，例如缓慢转头、抬手、俯身观察、迈上几级台阶或缓慢行走。不得在同一镜中连续安排跑动、跨越多个场地、登完一整层楼、穿过门窗后又到达新地点、从近景切到远景等多个阶段。若诗意必须跨空间，先用连续移动清楚表现过程；镜头仅缓慢跟随、缓慢推进、轻微平移或自然转场，不得快速奔跑、冲出、追逐、快速切换机位或突然抵达。
严格只输出合法 JSON，不得输出 Markdown、解释、注释或任何 JSON 之外的文字。

""" + VIDEO_CONSISTENCY_AUDIT

VIDEO_PLANNER_USER_TEMPLATE = """古诗：《{poem_title}》
作者：{dynasty}代{poet_name}
意象标签：{tags}
诗句：
{numbered_poem_lines}

请严格按顺序完成以下任务，最终只输出一个 JSON。

【第一步：完整理解全诗】
逐句输出 translation（准确白话翻译）、writing_type（实写或虚写）、semantic_role（本句在全诗中的作用）、key_imagery（本句最应被孩子一眼看见的核心可画意象）、character_position（人物在哪里和如何移动；无人时为空字符串）、time_weather_light（本句画面的时间、天气和光线）。必须按本诗语义判断，不得按句号位置套用，也不得把全诗时间锁死为同一个时刻。

【第二步：从诗意确定人物数量与角色，不得擅自加人】
输出 characters 数组。人物、动物、群体、关系、动作主体和观察者只能依据本次 poem_content 的实际诗句判断；不得依据诗题、作者、朝代、标签、推荐语、未传入的完整原诗、历史背景或外部常识新增。若全部诗句仅描述自然景物、建筑、器物、季节或自然现象，且没有明确人物、第一人称、第二人称、人物称谓、人物动作或人物关系，characters 必须为空数组，has_character 必须为 false，所有镜头不得添加人物或动物。只有诗中存在明确人物动作、第一人称观察、明确关系人物或确有必要的观看主体时，才创建角色。
每个角色的 role 只能是 principal（主要人物）、supporting（有明确诗意作用的配角）或 background_group（诗中明确出现、无需单独刻画的群体）。count 必须为该角色或该群体的确切人数；不得因为画面好看添加任何角色，不得把不确定人数写成“许多”“一些”。
诗中明确年龄或性别时，identity_profile 必须如实采用；诗中未明确时，不得默认设为儿童、男童、女童或作者本人，可自行选择合适的年龄和性别，但选择后必须完整固定。每个角色必须有稳定 id、role、count、source_evidence、identity_profile、visual_fingerprint、must_remain。source_evidence 必须逐字写出该角色可从本次 poem_content 的哪一句、哪个词语推出；不得引用诗题、作者、标签或未传入诗句。
identity_profile 必须刻画该角色或群体的外观：年龄段和性别仅在诗意需要或已选择时写明；还必须一次确定脸型、眉眼鼻唇比例、肤色、体型、发型与发饰、服装主色、辅色、滚边色、服装款式、腰带色和固定配饰色，不得使用“或、可、大约、类似、随意”等可变表述。除非诗句明确规定特殊服制或颜色，服装必须从天空蓝、湖水青、草绿、嫩黄、明黄、橙色、珊瑚粉、桃粉、朱红、宝蓝、亮紫中选定两至三种作为大面积主辅色；黑色、白色、灰色、深棕、灰蓝、暗蓝只能用于头发、轮廓线、鞋子、小型发饰或极少量边缘细节，不得成为服装大面积主色。visual_fingerprint 用一句话压缩最不能变化的脸、发、衣、配饰特征。must_remain 列出全诗绝不可改变的外观要素。角色外貌和服装配色一旦选定，跨全诗所有镜头绝不可更改；夜晚、风雨、季节或情绪变化不得成为换衣服或改变配色的理由。已命名人物均只有两只手、两条手臂；群体总人数与服装特征必须保持一致。

【第三步：按实际空间建立场地】
输出 locations 数组。一个 location 是一个可见空间，例如室内卧房、窗外庭院、庭院、船上、水岸、山路；每个场地必须有稳定 id、kind（indoor、outdoor、view_through_window、on_water 或 other）、stable_elements（仅该场地稳定存在的建筑、家具、地貌或背景）和 spatial_relation（它和其他场地如何相连或可见）。不要生成全诗通用 outdoor_elements 或 recurring_elements；鸟、雨、落花、雾、云等短暂意象只写入真正需要它的镜头。stable_elements 不得为了装饰添加诗意之外的花瓶、帷幔、家具、人物或动物。

【第四步：逐句镜头与可选想象转场】
每句对应一个镜头。每个镜头必须输出 scene（完整、可直接绘制的具体场景，不得写成半句）、primary_visual、color_palette、color_distribution、color_mood、location_id、visible_location_ids、camera_anchor、character_space_anchor、view_direction、visible_elements、forbidden_elements、spatial_boundary、characters_present、character_blocking、transition_from_previous、reality_mode、imagination_transition、shot_type、character_position、hand_pose、time_weather_light、emotion_visualization、camera_motion、subject_motion、opening_state、ending_state。
characters_present 是对象数组，每项必须包含已有角色 id 和该镜头实际出现的 count；该 count 不得超过该角色在 characters 中的总 count。若本句无人则为空数组。一个人的诗不得出现第二人；群体镜头必须明确群体实际出现人数。visible_location_ids 只能填写 locations 中已有的 id；forbidden_elements 必须列出该镜头最容易被模型误放进来的不该出现元素，特别是室内外转换时。spatial_boundary 必须写清实际空间关系；若有窗、门、廊、船舷等边界，必须写明哪些元素位于边界哪一侧，以及绝不能越界的元素。
reality_mode 只能是 real、imagined 或 mixed。imagination_transition 必须是对象：若诗意不是主动想象、思念或遥想，entry_type 必须为 none；若确是主动想象、思念或遥想，可按诗意选择 cloud_bubble_push_in（先出现无文字云朵气泡、镜头推进到气泡内画面）、window_or_view_transition、soft_dissolve 或 direct_cut。必须同时写明 reality_state、bubble_content（无文字画面；未用气泡则为空字符串）、camera_action、imagination_scope（仅本句或持续到后续哪些句）和 exit_type。不得把气泡转场套用到所有虚写句；昼夜、风雨、视线或实际空间变化应优先用光线、天气、窗景或自然转场表现。
shot_type 只能从远景、中景、近景、特写、主观视角中选择并按诗意使用；远景中人物高度不得超过画面总高度10%；主观视角不得出现视角主体自身的脸、手或身体。虚写、比喻、夸张不可机械画成实体，例如“疑是银河落九天”画瀑布，不画真实银河；“疑是地上霜”画冷白月光，不画真实霜晶。
每句最重要的具体名词、自然现象或动作必须同时在 scene 和 visible_elements 实际出现；不得只画结果、影子、声音、文字说明、抽象情绪或事后痕迹替代。野火、风雨、雷电、冰雪、夜色等可以采用圆润、概括、非恐怖的儿童动画表现，但不得删除诗义；例如“野火烧不尽”必须可见小范围、可控的橙红野火和明黄火光，以及未被烧尽的草根或嫩绿草芽，不得出现人物靠近火源、受伤、惊恐、灾难或失控毁坏场面。
primary_visual 必须优先于泛化表情，且在该镜头中清楚可见。若 primary_visual 位于窗外、门外、岸边或相邻空间，必须在 visible_elements 中实际列出该意象，并明确边界已经打开或摄影机位于人物所在空间的边界内侧；不得用关闭的窗纸、模糊影子或只有声音替代。color_palette 必须给出三至五种明确颜色并按画面占比从高到低排列；color_distribution 必须说明主色、核心意象色、对比色分别落在哪些本镜头真实存在的元素上；color_mood 必须说明色彩如何贴合本句时间、天气、季节和情绪。夜色、雨雪、秋冬或宁静可保留相应深冷或素色，但必须有鲜明重点色和清楚对比，不得整镜低饱和灰蒙；明媚、生机、童趣、晴朗等诗意应让高明度颜色成为核心意象的明显色块。不得因为色彩要求添加诗意之外的物体、人物或天气。camera_anchor 必须说明摄影机所在的实际物理空间和固定位置；character_space_anchor 必须说明每个出现人物的下半身、双脚和臀部锚定在哪个真实空间或稳定物体上，并说明头部、视线、手臂、上半身或双手是否自然伸向边界外侧；view_direction 必须说明摄影机和人物经何处看向何方。若镜头同时呈现相邻空间，必须以窗框、门框、檐口、船舷、栏杆或廊柱建立清晰边界；未明确跨越边界时，人物的下半身、双脚和臀部不得离开既定空间，头部、手臂、上半身和双手可从原空间自然伸向边界外侧。人物若要整体换到另一空间，必须在本镜或相邻镜中写出连续、可见的移动过程，不得瞬移或跳变。

【第五步：情绪必须明确外化】
不得只写“若有所思”“神情悠远”“氛围忧伤”等抽象描述。真正的疑惑或误认允许清晰“？”；感叹允许“！”或强烈景观表现；思念或乡愁允许无文字云朵气泡，内部必须是具体人物或场景。轻微惜春、感慨、宁静优先使用花叶疏密、光线、停顿、视线、动作和环境色调，不得默认哭泣；只有明确悲伤或忧愁才允许小泪珠、冷蓝色调和动作放慢。禁止诗句、字幕、标题、Logo、水印、拼音、乱码和对白文字；仅允许“？”、“！”及本句明确要求的无文字气泡作为规定情绪符号。

【第六步：画风、动态与承接】
全部镜头必须严格统一为：{video_style}。
仅允许云、水面、树叶、花瓣、衣袖、窗帘、雨丝、雾气、月光等轻柔自然运动；人物仅允许眨眼、呼吸、缓慢抬头、低头、转身、行走等自然动作。禁止快速闪烁、剧烈抖动、突然变焦、过快剪辑、画面跳变、恐怖、暴力、打斗、追逐、危险动作、现代建筑、现代服装、现代家具、汽车、电线、电子产品、多手、多脚、肢体变形、五官漂移和人物凭空出现或消失。上一镜 ending_state 必须能自然承接下一镜 opening_state。

{consistency_audit}

【第七步：片段分组】
整首诗只规划为一条连续12秒视频。每句对应一个镜头，镜头数必须等于输入诗句数；每句时长由服务端按“12秒 ÷ 诗句数”平均分配。segments 只能输出一个片段，line_indices 必须覆盖全部诗句，duration_seconds 必须为12，transition_to_next 为空字符串。视频不生成对白、配音或背景音乐。

严格输出以下 JSON 结构：
{{
  "line_analysis": [
    {{"line": "诗句1", "translation": "准确白话翻译", "writing_type": "实写或虚写", "semantic_role": "本句语义作用", "key_imagery": "本句核心可见意象", "character_position": "人物位置和动作；无人时为空字符串", "time_weather_light": "本句时间、天气和光线"}}
  ],
  "has_character": true,
  "characters": [
    {{"id": "principal_1", "role": "principal", "count": 1, "source_evidence": "本次诗句中支持该角色出现的具体句子和词语", "identity_profile": "详细且可重复的外观身份档案", "visual_fingerprint": "一句话固定脸、发、衣、配饰特征", "must_remain": ["不可改变的外观要素"]}}
  ],
  "locations": [
    {{"id": "room_1", "kind": "indoor", "stable_elements": ["只属于这个场地的稳定元素"], "spatial_relation": "与其他场地的可见或通行关系"}}
  ],
  "frames": [
    {{"index": 0, "line": "诗句1", "scene": "完整且可直接绘制的具体场景", "primary_visual": "必须最醒目出现的核心意象", "color_palette": ["按占比排序的三至五种明确颜色"], "color_distribution": "主色、核心意象色、对比色分别出现在哪些已有元素上", "color_mood": "色彩如何贴合本句时间、天气、季节和情绪", "location_id": "room_1", "visible_location_ids": ["room_1"], "camera_anchor": "摄影机的实际物理位置", "character_space_anchor": "人物身体、脚和手所在的实际空间", "view_direction": "摄影机和人物通过何处看向何方", "visible_elements": ["本镜头真正可见的元素"], "forbidden_elements": ["本镜头不得出现的易混入元素"], "spatial_boundary": "空间边界及不得越界规则", "characters_present": [{{"id": "principal_1", "count": 1}}], "character_blocking": "每名出现人物的位置、朝向、双手和动作；无人时为空字符串", "transition_from_previous": "首镜为空字符串；否则写实际可见转场", "reality_mode": "real、imagined或mixed", "imagination_transition": {{"entry_type": "none、cloud_bubble_push_in、window_or_view_transition、soft_dissolve或direct_cut", "reality_state": "现实与想象关系", "bubble_content": "无文字画面；未用气泡为空字符串", "camera_action": "实际镜头动作", "imagination_scope": "仅本句或持续范围", "exit_type": "如何回到现实；未用时为空字符串"}}, "shot_type": "远景、中景、近景、特写或主观视角", "character_position": "人物位置和动作；无人时为空字符串", "hand_pose": "人物双手位置与姿态；无人时为空字符串", "time_weather_light": "该镜头时间、天气和光线", "emotion_visualization": "明确但不过度的情绪外化", "camera_motion": "静止、缓慢推进、缓慢拉远、缓慢平移或自然转场", "subject_motion": "具体轻柔运动", "opening_state": "镜头起始状态", "ending_state": "镜头结束状态"}}
  ],
  "segments": [
    {{"segment_index": 0, "line_indices": [0, 1], "duration_seconds": 12, "transition_to_next": ""}}
  ]
}}"""


class VideoGenerateRequest(BaseModel):
    poem_id: str = ""
    poem_title: str = Field(
        default="",
        validation_alias=AliasChoices("poem_title", "title"),
    )
    poem_content: List[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("poem_content", "content"),
    )
    poet_name: str = ""
    dynasty: str = ""
    tags: List[str] = Field(default_factory=list)
    model: str = "Doubao-Seedance-2.0-fast"
    duration: int = 12
    ratio: str = "16:9"
    force_regenerate: bool = False
    dry_run: bool = False


def _now_text() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _cache_key(poem_id: str, poem_title: str) -> str:
    value = poem_id.strip() if poem_id.strip() else hashlib.md5(poem_title.strip().encode("utf-8")).hexdigest()
    return re.sub(r"[^a-zA-Z0-9_-]", "_", value) or "untitled"


def _load_cache() -> dict:
    empty = {"poems": {}, "tasks": {}, "groups": {}}
    if not CACHE_FILE.exists():
        return empty
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as file:
            cache = json.load(file)
        cache.setdefault("poems", {})
        cache.setdefault("tasks", {})
        cache.setdefault("groups", {})
        return cache
    except Exception:
        return empty


def _save_cache(cache: dict) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _cache_lock:
        temp_file = CACHE_FILE.with_suffix(".json.tmp")
        with open(temp_file, "w", encoding="utf-8") as file:
            json.dump(cache, file, ensure_ascii=False, indent=2)
        os.replace(temp_file, CACHE_FILE)


def _request_params() -> dict:
    return {
        "request_id": str(uuid.uuid4()),
        "system_time": int(time.time()),
        "module": "aigc",
    }


def _request_headers() -> dict:
    app_key = os.getenv("VIVO_APP_KEY", "").strip()
    if not app_key:
        raise RuntimeError("缺少 VIVO_APP_KEY，无法调用视频生成接口")
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {app_key}",
    }


def _validate_request(request: VideoGenerateRequest) -> str:
    if not request.poem_title.strip():
        return "poem_title 不能为空"
    if not request.poem_content:
        return "poem_content 不能为空"
    if request.model not in SUPPORTED_MODELS:
        return f"不支持的视频模型：{request.model}"
    if any(not line.strip() for line in request.poem_content):
        return "poem_content 不能包含空诗句"
    if len(request.poem_content) > MAX_POEM_LINES:
        return f"连续诗词学习视频最多支持{MAX_POEM_LINES}句，请减少 poem_content 后重试"
    if request.duration != FIXED_VIDEO_DURATION_SECONDS:
        return f"连续诗词学习视频固定为{FIXED_VIDEO_DURATION_SECONDS}秒，请传 duration={FIXED_VIDEO_DURATION_SECONDS}"
    if request.ratio != "16:9":
        return "诗词学习视频固定为横版16:9"
    return ""


def _safe_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _text_list(value: Any, max_items: int = 12) -> List[str]:
    if not isinstance(value, list):
        return []
    return [_safe_text(item) for item in value if _safe_text(item)][:max_items]


def _safe_count(value: Any, default: int = 1) -> int:
    try:
        count = int(value)
    except (TypeError, ValueError):
        return default
    return count if 1 <= count <= 99 else default


def _shot_duration_text(total_seconds: int, frame_count: int) -> str:
    """将平均镜头时长格式化为适合提示词阅读的秒数。"""
    if frame_count <= 0:
        raise ValueError("视频至少需要一个镜头")
    seconds = total_seconds / frame_count
    return f"{seconds:.2f}".rstrip("0").rstrip(".")


def _normalize_characters(raw_characters: Any, raw_plan: Dict[str, Any]) -> List[dict]:
    characters = []
    if isinstance(raw_characters, list):
        for index, item in enumerate(raw_characters):
            if not isinstance(item, dict):
                continue
            character_id = re.sub(r"[^a-zA-Z0-9_-]", "_", _safe_text(item.get("id"), f"character_{index + 1}"))
            if not character_id:
                character_id = f"character_{index + 1}"
            role = _safe_text(item.get("role"), "supporting")
            if role not in {"principal", "supporting", "background_group"}:
                role = "supporting"
            characters.append({
                "id": character_id,
                "role": role,
                "count": _safe_count(item.get("count")),
                "source_evidence": _safe_text(item.get("source_evidence")),
                "identity_profile": _safe_text(item.get("identity_profile"), _safe_text(item.get("character_desc"))),
                "visual_fingerprint": _safe_text(item.get("visual_fingerprint"), _safe_text(item.get("character_anchor"))),
                "must_remain": _text_list(item.get("must_remain")),
            })
    if characters:
        return characters
    legacy_desc = _safe_text(raw_plan.get("character_desc"))
    if not legacy_desc:
        return []
    return [{
        "id": "principal_1",
        "role": "principal",
        "count": 1,
        "source_evidence": _safe_text(raw_plan.get("source_evidence")),
        "identity_profile": legacy_desc,
        "visual_fingerprint": _safe_text(raw_plan.get("character_anchor"), legacy_desc),
        "must_remain": ["脸型", "发型", "服装颜色与款式", "体型", "固定配饰"],
    }]


def _normalize_character_presence(raw_presence: Any, characters: List[dict]) -> List[dict]:
    character_counts = {character["id"]: character["count"] for character in characters}
    normalized = []
    if not isinstance(raw_presence, list):
        return normalized
    for item in raw_presence:
        if isinstance(item, dict):
            character_id = _safe_text(item.get("id"))
            requested_count = _safe_count(item.get("count"))
        else:
            character_id = _safe_text(item)
            requested_count = character_counts.get(character_id, 1)
        total_count = character_counts.get(character_id)
        if not total_count or any(entry["id"] == character_id for entry in normalized):
            continue
        normalized.append({"id": character_id, "count": min(requested_count, total_count)})
    return normalized


def _normalize_locations(raw_locations: Any, raw_plan: Dict[str, Any]) -> List[dict]:
    locations = []
    if isinstance(raw_locations, list):
        for index, item in enumerate(raw_locations):
            if not isinstance(item, dict):
                continue
            location_id = re.sub(r"[^a-zA-Z0-9_-]", "_", _safe_text(item.get("id"), f"location_{index + 1}"))
            if not location_id:
                location_id = f"location_{index + 1}"
            kind = _safe_text(item.get("kind"), "other")
            if kind not in {"indoor", "outdoor", "view_through_window", "on_water", "other"}:
                kind = "other"
            locations.append({
                "id": location_id,
                "kind": kind,
                "stable_elements": _text_list(item.get("stable_elements")),
                "spatial_relation": _safe_text(item.get("spatial_relation")),
            })
    if locations:
        return locations
    return [{
        "id": "main_location",
        "kind": "other",
        "stable_elements": _text_list([raw_plan.get("world_context"), raw_plan.get("scene_context")]),
        "spatial_relation": "按诗句语义自然呈现场地与视线关系",
    }]


def _sanitize_scene_text(scene: Any, fallback: str) -> str:
    """拦截明确不允许的文字、水印和现代元素，保留已确认的情绪视觉符号。"""
    forbidden_terms = (
        "字幕", "诗句", "标题", "标志", "水印", "边框", "拼音", "乱码",
        "现代建筑", "现代服装", "现代家具", "汽车", "电线", "电子产品",
    )
    text = _safe_text(scene, fallback)
    if any(term in text for term in forbidden_terms):
        return f"围绕“{fallback}”的古典诗意场景"
    return text


def _default_spatial_boundary(location_id: str, visible_location_ids: List[str], locations: List[dict]) -> str:
    """为规划模型漏填边界时保留最低限度的空间约束。"""
    locations_by_id = {location["id"]: location for location in locations}
    current_kind = locations_by_id.get(location_id, {}).get("kind", "other")
    visible_kinds = {
        locations_by_id.get(visible_id, {}).get("kind", "other")
        for visible_id in visible_location_ids
    }
    if current_kind == "indoor" and visible_kinds & {"outdoor", "view_through_window"}:
        return (
            "窗框或门框是室内外硬边界：室外树干、树枝、泥土、石板、草地、积水和落花只能位于边界外；"
            "室内地面、床榻、墙面和窗内不得出现这些户外元素"
        )
    if current_kind == "indoor":
        return "本镜头只在室内；不得出现室外树干、泥土、草地、石板、积水或无来由的落花"
    if current_kind == "outdoor":
        return "本镜头只在室外；不得出现未经诗意说明的室内床榻、墙面、家具或窗内陈设"
    return "不同场地只能按镜头明确的可见关系连接，元素不得无故跨越场地边界"


def _default_camera_motion(shot_type: str) -> str:
    return {
        "远景": "缓慢推进",
        "中景": "缓慢平移",
        "近景": "缓慢推进",
        "特写": "静止",
        "主观视角": "缓慢平移",
    }.get(shot_type, "静止")


def _default_emotion_visualization(line: str) -> str:
    if any(token in line for token in ("谁", "何", "疑", "问")):
        return "人物头顶出现一个清晰的大问号“？”"
    return "通过明确人物表情、姿态和环境色调表现当前诗意，不出现文字"


def _build_fallback_video_plan(request: VideoGenerateRequest, error: str = "") -> dict:
    """视频模块自身的降级规划，不调用图片模块或读取图片规划结果。"""
    human_keywords = ("举头", "低头", "锄禾", "独坐", "遥望", "乘舟", "送", "我", "君", "汝", "余", "吾", "望", "行", "登", "看")
    has_character = any(word in "".join(request.poem_content) for word in human_keywords)
    characters = []
    if has_character:
        characters = [{
            "id": "principal_1",
            "role": "principal",
            "count": 1,
            "identity_profile": (
                f"本诗中唯一的{request.dynasty or '古代'}人物；年龄与性别不作预设，"
                "使用符合诗意的古代服饰与发式，整首诗保持同一张脸、同一发型和同一服装"
            ),
            "visual_fingerprint": "同一张脸、同一发型、同一套古代服饰与固定配饰，全片不变",
            "must_remain": ["脸型", "发型", "服装颜色与款式", "固定配饰", "人数为一人"],
        }]
    frames = []
    for index, line in enumerate(request.poem_content):
        scene = _sanitize_scene_text(line, line)
        frames.append({
            "index": index,
            "line": line,
            "scene": scene,
            "primary_visual": scene,
            "color_palette": [],
            "color_distribution": "按当前诗句的时间、天气、季节和核心意象安排主色、重点色与对比色",
            "color_mood": "保持适合儿童理解的清楚色彩层次，并遵守当前诗句的情绪",
            "location_id": "main_location",
            "visible_location_ids": ["main_location"],
            "camera_anchor": "主场地内，以当前诗句的主体为中心拍摄",
            "character_space_anchor": "人物的脚、身体和双手始终位于主场地内" if has_character else "",
            "view_direction": "在主场地内朝当前诗句的核心意象观看",
            "visible_elements": [],
            "forbidden_elements": [],
            "spatial_boundary": "不同场地只能按诗句语义自然连接，元素不得无故跨越场地边界",
            "characters_present": [{"id": "principal_1", "count": 1}] if has_character else [],
            "character_blocking": "主要人物按当前诗句在场地中自然活动" if has_character else "",
            "transition_from_previous": "" if index == 0 else "按相邻诗句语义自然转场",
            "reality_mode": "real",
            "imagination_transition": {
                "entry_type": "none",
                "reality_state": "现实画面",
                "bubble_content": "",
                "camera_action": "",
                "imagination_scope": "",
                "exit_type": "",
            },
            "shot_type": "中景",
            "character_position": "按当前诗句在统一场景中自然活动" if has_character else "",
            "hand_pose": "双手动作自然且符合人体结构" if has_character else "",
            "time_weather_light": "按当前诗句语义自然呈现时间、天气和光线",
            "emotion_visualization": _default_emotion_visualization(line),
            "camera_motion": "缓慢平移",
            "subject_motion": "云、水面、树叶或人物进行轻柔自然运动",
            "opening_state": f"呈现“{line}”对应的初始诗意画面",
            "ending_state": f"自然收束到“{line}”对应的画面状态",
        })
    return _normalize_video_plan({
        "has_character": has_character,
        "characters": characters,
        "locations": [{
            "id": "main_location",
            "kind": "other",
            "stable_elements": [],
            "spatial_relation": "按诗句语义自然呈现场地与视线关系",
        }],
        "frames": frames,
        "planner_error": error,
    }, request)


def _normalize_video_plan(raw_plan: Dict[str, Any], request: VideoGenerateRequest) -> dict:
    raw_frames = raw_plan.get("frames") if isinstance(raw_plan.get("frames"), list) else []
    raw_analysis = raw_plan.get("line_analysis") if isinstance(raw_plan.get("line_analysis"), list) else []
    characters = _normalize_characters(raw_plan.get("characters"), raw_plan)
    locations = _normalize_locations(raw_plan.get("locations"), raw_plan)
    location_ids = {location["id"] for location in locations}
    default_location_id = locations[0]["id"]
    analysis_by_line = {
        _safe_text(item.get("line")): item
        for item in raw_analysis
        if isinstance(item, dict) and _safe_text(item.get("line"))
    }
    normalized_frames = []
    for index, poem_line in enumerate(request.poem_content):
        raw_frame = raw_frames[index] if index < len(raw_frames) and isinstance(raw_frames[index], dict) else {}
        shot_type = _safe_text(raw_frame.get("shot_type"), "中景")
        if shot_type not in SUPPORTED_SHOT_TYPES:
            shot_type = "中景"
        camera_motion = _safe_text(raw_frame.get("camera_motion"), _default_camera_motion(shot_type))
        if camera_motion not in SUPPORTED_CAMERA_MOTIONS:
            camera_motion = _default_camera_motion(shot_type)
        analysis = analysis_by_line.get(poem_line, {})
        location_id = _safe_text(raw_frame.get("location_id"), default_location_id)
        if location_id not in location_ids:
            location_id = default_location_id
        visible_location_ids = [item for item in _text_list(raw_frame.get("visible_location_ids")) if item in location_ids]
        if location_id not in visible_location_ids:
            visible_location_ids.insert(0, location_id)
        spatial_boundary = _safe_text(
            raw_frame.get("spatial_boundary"),
            _default_spatial_boundary(location_id, visible_location_ids, locations),
        )
        characters_present = _normalize_character_presence(raw_frame.get("characters_present"), characters)
        if not characters_present and len(characters) == 1 and _safe_text(raw_frame.get("character_position")):
            characters_present = [{"id": characters[0]["id"], "count": 1}]
        raw_imagination = raw_frame.get("imagination_transition") if isinstance(raw_frame.get("imagination_transition"), dict) else {}
        entry_type = _safe_text(raw_imagination.get("entry_type"), "none")
        if entry_type not in {"none", "cloud_bubble_push_in", "window_or_view_transition", "soft_dissolve", "direct_cut"}:
            entry_type = "none"
        normalized_frames.append({
            "index": index,
            "line": poem_line,
            "scene": _sanitize_scene_text(raw_frame.get("scene"), poem_line),
            "primary_visual": _safe_text(raw_frame.get("primary_visual"), _safe_text(analysis.get("key_imagery"), poem_line)),
            "color_palette": _text_list(raw_frame.get("color_palette"))[:5],
            "color_distribution": _safe_text(
                raw_frame.get("color_distribution"),
                "按本句时间、天气、季节和核心意象安排主色、重点色与对比色",
            ),
            "color_mood": _safe_text(
                raw_frame.get("color_mood"),
                "保持适合儿童理解的清楚色彩层次，并遵守当前诗句的情绪",
            ),
            "location_id": location_id,
            "visible_location_ids": visible_location_ids,
            "camera_anchor": _safe_text(
                raw_frame.get("camera_anchor"),
                f"摄影机位于 {location_id} 内，按本镜头主视觉拍摄",
            ),
            "character_space_anchor": _safe_text(
                raw_frame.get("character_space_anchor"),
                "人物的脚、身体和双手位于当前主场地内" if characters_present else "",
            ),
            "view_direction": _safe_text(
                raw_frame.get("view_direction"),
                "摄影机在当前主场地内朝本镜头核心意象观看",
            ),
            "visible_elements": _text_list(raw_frame.get("visible_elements")),
            "forbidden_elements": _text_list(raw_frame.get("forbidden_elements")),
            "spatial_boundary": spatial_boundary,
            "characters_present": characters_present,
            "character_blocking": _safe_text(raw_frame.get("character_blocking"), _safe_text(raw_frame.get("character_position"))),
            "transition_from_previous": _safe_text(raw_frame.get("transition_from_previous")),
            "reality_mode": _safe_text(raw_frame.get("reality_mode"), "real") if _safe_text(raw_frame.get("reality_mode"), "real") in {"real", "imagined", "mixed"} else "real",
            "imagination_transition": {
                "entry_type": entry_type,
                "reality_state": _safe_text(raw_imagination.get("reality_state"), "现实画面" if entry_type == "none" else "由现实进入诗意想象"),
                "bubble_content": _safe_text(raw_imagination.get("bubble_content")) if entry_type == "cloud_bubble_push_in" else "",
                "camera_action": _safe_text(raw_imagination.get("camera_action")),
                "imagination_scope": _safe_text(raw_imagination.get("imagination_scope")),
                "exit_type": _safe_text(raw_imagination.get("exit_type")),
            },
            "shot_type": shot_type,
            "character_position": _safe_text(raw_frame.get("character_position"), _safe_text(analysis.get("character_position"))),
            "hand_pose": _safe_text(raw_frame.get("hand_pose")),
            "time_weather_light": _safe_text(raw_frame.get("time_weather_light"), _safe_text(analysis.get("time_weather_light"), "按当前诗句语义自然呈现时间、天气和光线")),
            "emotion_visualization": _safe_text(raw_frame.get("emotion_visualization"), _default_emotion_visualization(poem_line)),
            "camera_motion": camera_motion,
            "subject_motion": _safe_text(raw_frame.get("subject_motion"), "画面主体进行轻柔自然运动"),
            "opening_state": _safe_text(raw_frame.get("opening_state"), f"呈现“{poem_line}”对应的初始画面"),
            "ending_state": _safe_text(raw_frame.get("ending_state"), f"自然收束到“{poem_line}”对应的画面状态"),
        })
    segments = [{
        "segment_index": 0,
        "line_indices": list(range(len(normalized_frames))),
        "duration_seconds": request.duration,
        "transition_to_next": "",
    }]
    return {
        "line_analysis": raw_analysis,
        "has_character": bool(characters),
        "characters": characters,
        "locations": locations,
        "frames": normalized_frames,
        "segments": segments,
        "planner_error": _safe_text(raw_plan.get("planner_error")),
    }


def plan_poem_video_sequence(request: VideoGenerateRequest) -> dict:
    """独立的视频规划模型调用；不得读取或调用 generate.py。"""
    user_prompt = VIDEO_PLANNER_USER_TEMPLATE.format(
        poem_title=request.poem_title,
        dynasty=request.dynasty,
        poet_name=request.poet_name,
        tags="、".join(request.tags) if request.tags else "无",
        numbered_poem_lines="\n".join(f"{index + 1}. {line}" for index, line in enumerate(request.poem_content)),
        video_style=VIDEO_STYLE,
        consistency_audit=VIDEO_CONSISTENCY_AUDIT,
    )
    try:
        response = requests.post(
            VIVO_PLANNER_URL,
            headers=_request_headers(),
            json={
                "requestId": str(uuid.uuid4()),
                "model": "Volc-DeepSeek-V3.2",
                "messages": [
                    {"role": "system", "content": VIDEO_PLANNER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout=90,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
        content = re.sub(r"```json|```", "", content).strip()
        raw_plan = json.loads(content)
        if not isinstance(raw_plan, dict):
            raise ValueError("视频规划模型未返回 JSON 对象")
        return _normalize_video_plan(raw_plan, request)
    except Exception as error:
        return _build_fallback_video_plan(request, str(error))


def _character_contract(characters: List[dict]) -> str:
    if not characters:
        return "本诗不需要固定人物；不得凭空添加儿童、诗人、路人、配角或动物。"
    blocks = []
    for character in characters:
        must_remain = "、".join(character.get("must_remain", [])) or "脸、发、衣、配饰与体型"
        blocks.append(
            f"角色 {character['id']}（{character['role']}，总人数={character['count']}）：{character['identity_profile']}\n"
            f"固定视觉指纹：{character['visual_fingerprint']}\n"
            f"绝不可改变：{must_remain}"
        )
    return "\n\n".join(blocks)


def _location_contract(locations: List[dict]) -> str:
    blocks = []
    for location in locations:
        elements = "、".join(location.get("stable_elements", [])) or "无额外固定元素"
        relation = location.get("spatial_relation") or "按镜头指定的可见关系呈现"
        blocks.append(f"场地 {location['id']}（{location['kind']}）：稳定元素={elements}；空间关系={relation}")
    return "\n".join(blocks) or "场地由每个镜头的 location_id 明确指定。"


def _build_shot_block(frame: dict, number: int, duration_seconds: str) -> str:
    imagination = frame.get("imagination_transition", {})
    imagination_text = (
        f"想象/转场：entry_type={imagination.get('entry_type', 'none')}；"
        f"现实关系={imagination.get('reality_state', '') or '无'}；"
        f"气泡内画面={imagination.get('bubble_content', '') or '无'}；"
        f"镜头动作={imagination.get('camera_action', '') or '无'}；"
        f"持续范围={imagination.get('imagination_scope', '') or '无'}；"
        f"退出方式={imagination.get('exit_type', '') or '无'}"
    )
    present_characters = "、".join(
        f"{item['id']}（{item['count']}人）" for item in frame["characters_present"]
    ) or "无人"
    color_palette = "、".join(frame.get("color_palette", [])) or "必须由本句诗意选定三至五种清楚可辨的颜色"
    return (
        f"【镜头{number}｜约{duration_seconds}秒｜对应诗句“{frame['line']}”】\n"
        f"采用{frame['shot_type']}。\n"
        f"场景：{frame['scene']}\n"
        f"本镜头必须最醒目呈现：{frame['primary_visual']}\n"
        "本镜头色彩脚本（必须实际出现在画面中）：\n"
        f"主色板：{color_palette}\n"
        f"色彩分布：{frame.get('color_distribution', '')}\n"
        f"色彩情绪：{frame.get('color_mood', '')}\n"
        "不得因为夜晚、雨天、室内、秋冬或安静情绪，把整镜处理成单一灰褐、米白、灰蓝或暗蓝电影画面；"
        "也不得为了鲜艳添加诗意之外的人物、动物、物体或天气。\n"
        f"当前主场地：{frame['location_id']}；可见场地：{'、'.join(frame['visible_location_ids']) or '仅主场地'}\n"
        "空间调度（必须实际呈现）：\n"
        f"摄影机锚点：{frame.get('camera_anchor', '')}\n"
        f"人物空间锚点：{frame.get('character_space_anchor', '') or '无人'}\n"
        f"观看方向：{frame.get('view_direction', '')}\n"
        "严格保持上述空间关系；未明确跨越边界时，人物的下半身、双脚和臀部不得离开既定空间，"
        "头部、视线、手臂、上半身或双手可从原空间自然伸向边界外侧；打开边界只改变可见范围。"
        "人物若要整体换到另一空间，必须有连续、可见的移动过程，不得瞬移或跳变。\n"
        f"只允许出现的本镜头元素：{'、'.join(frame['visible_elements']) or '按场景和主意象所需'}\n"
        f"本镜头不得出现：{'、'.join(frame['forbidden_elements']) or '无额外限制'}\n"
        f"空间硬边界：{frame['spatial_boundary']}\n"
        f"可出现人物（仅限这些已建档角色及人数）：{present_characters}\n"
        f"人物调度：{frame['character_blocking'] or '无人'}\n"
        f"与上一镜的实际衔接：{frame['transition_from_previous'] or '本段开场'}\n"
        f"现实状态：{frame['reality_mode']}；{imagination_text}\n"
        f"时间、天气与光线：{frame['time_weather_light']}\n"
        f"人物位置：{frame['character_position'] or '无人或无须出现人物'}\n"
        f"双手姿态：{frame['hand_pose'] or '无人或无须出现人物'}\n"
        f"明确情绪外化：{frame['emotion_visualization']}\n"
        f"镜头运动：{frame['camera_motion']}。\n"
        f"画面内运动：{frame['subject_motion']}。\n"
        f"本镜头约 {duration_seconds} 秒：只允许一个可看清起止的主体主要动作，以及一个缓慢连续的镜头动作；"
        "不得快速跑动、跨越多个场地、完成多阶段动作、快速切换机位或突然抵达。\n"
        f"镜头从“{frame['opening_state']}”自然发展到“{frame['ending_state']}”。"
    )


def build_segment_video_prompt(request: VideoGenerateRequest, plan: dict, segment: dict) -> str:
    frame_indices = segment.get("line_indices", [])
    frames = [plan["frames"][index] for index in frame_indices if 0 <= index < len(plan["frames"])]
    if not frames:
        raise ValueError("视频片段没有可用镜头")
    shot_seconds = _shot_duration_text(request.duration, len(frames))
    line_count = len(frames)
    shot_blocks = "\n\n".join(
        _build_shot_block(frame, index + 1, shot_seconds)
        for index, frame in enumerate(frames)
    )
    return (
        f"为{request.dynasty}代{request.poet_name}的古诗《{request.poem_title}》制作一条完整、连续的儿童诗意动画。\n\n"
        f"本片总时长{request.duration}秒，横版16:9。全诗共{line_count}句；每句约{shot_seconds}秒。整首诗只提交一条连续视频任务，"
        "所有镜头必须在同一条视频内按诗句顺序自然衔接，不得拆成独立视频，不得跳过、调换或重复任何诗句对应画面。\n\n"
        "【固定视觉契约】\n"
        f"{VIDEO_STYLE}。\n\n"
        "【全诗人物数量与身份档案：即使本段与其他片段独立生成，也必须逐字遵守】\n"
        f"{_character_contract(plan.get('characters', []))}\n"
        "所有已建档人物或群体必须保持规定的总人数。只有当前镜头明确列出的角色及人数可以出现；"
        "不得添加路人、儿童、诗人、配角、动物或其他人物。诗中未明确年龄或性别时，不要把儿童、男童、女童或作者本人视为默认答案；"
        "但已在身份档案中选定的外貌必须跨片段完全一致，不得换脸、换发髻、换衣服、改变性别、增减肢体或增减人数。"
        "身份档案中的脸型、眉眼鼻唇比例、肤色、体型、发型、发饰、服装精确颜色、服装款式、腰带和固定配饰均为唯一答案，"
        "不得自行改写成另一种人物。\n\n"
        "【全诗场地档案】\n"
        f"{_location_contract(plan.get('locations', []))}\n"
        "每个镜头只可呈现它列出的场地、可见元素和人物；不同场地之间只能按镜头指定的转场连接。"
        "镜头中写明的空间硬边界必须严格执行：窗框、门框、檐口、船舷等是物理分界线，"
        "未经当前镜头明确许可，室外树干、树枝、泥土、草地、石板、积水和落花不得跨越边界进入室内；"
        "室内床榻、墙面、家具不得无故出现在室外。\n\n"
        f"本片镜头必须按下列诗句顺序出现。每个镜头约{shot_seconds}秒；第N镜的结束状态必须成为第N+1镜的开场状态。"
        "不得调换、遗漏、重复或添加诗意之外的主要人物、动物、物体。\n\n"
        f"{shot_blocks}\n\n"
        "每个镜头的核心意象必须清楚可见并成为画面重点，不得用泛化难过、发呆或抽象气泡代替。"
        "若当前镜头的诗义涉及时间、天气、回忆、想象或空间变化，必须按本镜头写明的时间、天气与光线及具体场景真实呈现，"
        "不得套用其他诗句的时间或天气。\n"
        "人物、建筑、家具、自然元素、季节和空间关系必须遵守本镜头的场地、可见元素、禁止元素与人物名单。"
        "远景中若有人物，人物高度不得超过画面总高度的10%。"
        "主观视角时，不得出现视角主体自身的脸、手或身体。\n"
        "只允许云、水面、树叶、花瓣、衣袖、窗帘、雨丝、雾气、月光轻柔自然运动；"
        "只允许人物眨眼、呼吸、缓慢抬头、低头、转身、迈上几级台阶或缓慢行走；"
        "只允许缓慢推进、缓慢拉远、缓慢平移或自然转场。\n"
        f"每个镜头约 {shot_seconds} 秒：每镜最多一个可看清起止的主体主要动作和一个连续镜头动作；"
        "不得快速跑动、冲出、追逐、跨越多个场地、完成多阶段动作、快速切换机位或突然抵达。\n"
        "禁止文字、字幕、诗句、标题、Logo、水印、边框、拼音、乱码、对白文字、"
        "现代建筑、现代服装、现代家具、汽车、电线、电子产品、恐怖内容、阴森内容、"
        "暴力、打斗、追逐、危险动作、多手、多脚、肢体变形、五官漂移、人物凭空出现或消失、"
        "快速闪烁、剧烈抖动、突然变焦、过快剪辑、画面跳变、日本动漫、日漫少女脸、漫画分镜、"
        "赛璐璐硬阴影、粗黑线稿、夸张大眼、非国风的现代都市卡通、3D塑料质感、写实电影、成人动漫比例、"
        "照片质感、复杂逼真室内陈设和强烈灰褐滤镜。\n"
        "情绪外化仅允许当前镜头指定的视觉方式。思维气泡和云朵气泡内部只能有画面，不得出现文字；"
        "只有镜头指定为疑惑或感叹时，才允许出现清晰的“？”或“！”情绪符号。\n"
        f"{VIDEO_CONSISTENCY_AUDIT}\n"
        "视频内无对白、无配音、无字幕。前端将静音播放视频，并单独播放轻柔背景音乐。\n"
        f"最后一镜（第{line_count}镜）必须在本句的核心意象上自然停留并结束，不得另起一个故事或突然跳变。\n"
        f"{VIDEO_STYLE_FINAL_LOCK}\n"
        f" --ratio {request.ratio} --dur {request.duration}"
    )


def _public_task_result(record: dict, from_cache: bool = False) -> dict:
    return {
        "success": record.get("status") not in {"failed", "download_failed"},
        "from_cache": from_cache,
        "task_id": record.get("task_id", ""),
        "segment_index": record.get("segment_index"),
        "line_indices": record.get("line_indices", []),
        "poem_id": record.get("poem_id", ""),
        "poem_title": record.get("poem_title", ""),
        "model": record.get("model", ""),
        "duration": record.get("duration", 0),
        "ratio": record.get("ratio", ""),
        "status": record.get("status", ""),
        "prompt": record.get("prompt", ""),
        "video_url": record.get("video_url", ""),
        "error": record.get("error", ""),
        "created_at": record.get("created_at", ""),
        "updated_at": record.get("updated_at", ""),
    }


def _group_status(segment_records: List[dict]) -> str:
    statuses = [record.get("status", "unknown") for record in segment_records]
    if statuses and all(status == "succeeded" for status in statuses):
        return "succeeded"
    if statuses and all(status in {"failed", "download_failed"} for status in statuses):
        return "failed"
    if any(status in {"failed", "download_failed"} for status in statuses):
        return "partial_failed"
    if any(status in {"submitted", "queued", "running", "processing"} for status in statuses):
        return "processing"
    return "submitted"


def _public_group_result(group: dict, cache: dict, from_cache: bool = False) -> dict:
    records = [cache["tasks"][task_id] for task_id in group.get("segment_task_ids", []) if task_id in cache["tasks"]]
    status = _group_status(records) if records else group.get("status", "submitted")
    return {
        "success": status != "failed",
        "from_cache": from_cache,
        "group_id": group.get("group_id", ""),
        "poem_id": group.get("poem_id", ""),
        "poem_title": group.get("poem_title", ""),
        "model": group.get("model", ""),
        "duration": group.get("duration", 0),
        "ratio": group.get("ratio", ""),
        "status": status,
        "segments": [_public_task_result(record, from_cache=from_cache) for record in records],
        "error": group.get("error", ""),
        "created_at": group.get("created_at", ""),
        "updated_at": group.get("updated_at", ""),
    }


def _ready_single_video_candidate(group: dict, cache: dict) -> dict | None:
    """Return a locally playable continuous-video record, if this group has one."""
    poem_id = str(group.get("poem_id") or "").strip()
    task_ids = group.get("segment_task_ids", [])
    records = [cache["tasks"][task_id] for task_id in task_ids if task_id in cache["tasks"]]
    if not poem_id or len(records) != 1:
        return None

    record = records[0]
    if record.get("status") != "succeeded" or not record.get("video_url"):
        return None

    return {
        "poem_id": poem_id,
        "poem_title": group.get("poem_title", ""),
        "group_id": group.get("group_id", ""),
        "status": "succeeded",
        "video_url": record["video_url"],
        "updated_at": group.get("updated_at") or record.get("updated_at") or "",
        "created_at": group.get("created_at") or record.get("created_at") or "",
    }


def _latest_ready_group(cache: dict, cache_key: str = "") -> dict | None:
    """Choose the newest successful one-segment video, without querying the provider."""
    latest_group = None
    latest_order = ("", "", "")
    for group in cache["groups"].values():
        if cache_key and group.get("cache_key") != cache_key:
            continue
        candidate = _ready_single_video_candidate(group, cache)
        if not candidate:
            continue
        candidate_order = (candidate["updated_at"], candidate["created_at"], candidate["group_id"])
        if candidate_order > latest_order:
            latest_group = group
            latest_order = candidate_order
    return latest_group


def _download_video(source_url: str, cache_key: str, task_id: str) -> str:
    poem_dir = VIDEO_DIR / cache_key
    poem_dir.mkdir(parents=True, exist_ok=True)
    # 每首诗只维护一条正式视频。只有显式重新生成且下载成功时，才原子替换旧版本。
    file_path = poem_dir / "video.mp4"
    temp_path = file_path.with_suffix(".mp4.tmp")
    with requests.get(source_url, stream=True, timeout=(15, 180)) as response:
        response.raise_for_status()
        with open(temp_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file.write(chunk)
    os.replace(temp_path, file_path)
    return f"/static/videos/poems/{cache_key}/{file_path.name}"


def _submit_segment_task(request: VideoGenerateRequest, cache_key: str, group_id: str, segment: dict, prompt: str) -> tuple[dict | None, dict | None]:
    try:
        response = requests.post(
            VIVO_VIDEO_SUBMIT_URL,
            params=_request_params(),
            headers=_request_headers(),
            json={"model": request.model, "content": [{"type": "text", "text": prompt}]},
            timeout=60,
        )
        result = response.json()
    except requests.exceptions.Timeout:
        return None, {"error": "视频任务提交超时，请稍后重试"}
    except Exception as error:
        return None, {"error": f"视频任务提交异常：{error}"}
    if result.get("code") != 0:
        return None, {
            "error": result.get("message", "视频任务提交失败"),
            "code": result.get("code"),
            "trace_id": result.get("trace_id", ""),
            "data": result.get("data"),
        }
    task_id = result.get("data", {}).get("id", "")
    if not task_id:
        return None, {"error": "视频接口未返回 task_id", "raw": result}
    return {
        "task_id": task_id,
        "group_id": group_id,
        "segment_index": segment["segment_index"],
        "line_indices": segment["line_indices"],
        "cache_key": cache_key,
        "poem_id": request.poem_id,
        "poem_title": request.poem_title,
        "model": request.model,
        "duration": request.duration,
        "ratio": request.ratio,
        "status": "submitted",
        "video_url": "",
        "error": "",
        "prompt": prompt,
        "created_at": _now_text(),
        "updated_at": _now_text(),
    }, None


@router.post("/generate/video")
def submit_poem_video(request: VideoGenerateRequest):
    """为任意句数的诗提交一条连续12秒视频；dry_run 只返回视频规划与提示词。"""
    validation_error = _validate_request(request)
    if validation_error:
        return {"success": False, "error": validation_error}
    cache_key = _cache_key(request.poem_id, request.poem_title)
    cache = _load_cache()
    cached_pointer = cache["poems"].get(cache_key)
    cached_group_id = cached_pointer.get("group_id", "") if isinstance(cached_pointer, dict) else ""
    cached_group = cache["groups"].get(cached_group_id)
    if not request.force_regenerate and not request.dry_run:
        ready_group = _latest_ready_group(cache, cache_key)
        if ready_group:
            return _public_group_result(ready_group, cache, from_cache=True)
        if cached_group:
            return _public_group_result(cached_group, cache, from_cache=True)

    plan = plan_poem_video_sequence(request)
    prompts = []
    try:
        for segment in plan["segments"]:
            prompts.append({
                "segment_index": segment["segment_index"],
                "line_indices": segment["line_indices"],
                "prompt": build_segment_video_prompt(request, plan, segment),
            })
    except Exception as error:
        return {"success": False, "error": f"视频提示词构建失败：{error}"}
    if request.dry_run:
        return {
            "success": True,
            "dry_run": True,
            "poem_id": request.poem_id,
            "poem_title": request.poem_title,
            "model": request.model,
            "duration": request.duration,
            "ratio": request.ratio,
            "plan": plan,
            "segments": prompts,
        }

    group_id = str(uuid.uuid4())
    group = {
        "group_id": group_id,
        "cache_key": cache_key,
        "poem_id": request.poem_id,
        "poem_title": request.poem_title,
        "model": request.model,
        "duration": request.duration,
        "ratio": request.ratio,
        "status": "submitting",
        "segment_task_ids": [],
        "error": "",
        "created_at": _now_text(),
        "updated_at": _now_text(),
    }
    cache["groups"][group_id] = group
    cache["poems"][cache_key] = {"group_id": group_id}
    for prompt_item in prompts:
        segment = plan["segments"][prompt_item["segment_index"]]
        record, failure = _submit_segment_task(request, cache_key, group_id, segment, prompt_item["prompt"])
        if failure:
            group["status"] = "partial_submission_failed" if group["segment_task_ids"] else "failed"
            group["error"] = failure["error"]
            group["updated_at"] = _now_text()
            _save_cache(cache)
            return _public_group_result(group, cache)
        cache["tasks"][record["task_id"]] = record
        group["segment_task_ids"].append(record["task_id"])
        group["updated_at"] = _now_text()
        _save_cache(cache)
    group["status"] = "submitted"
    group["updated_at"] = _now_text()
    _save_cache(cache)
    return _public_group_result(group, cache)


def _query_video_task(task_id: str, cache: dict) -> dict:
    record = cache["tasks"].get(task_id)
    if record and record.get("status") == "succeeded" and record.get("video_url"):
        return _public_task_result(record, from_cache=True)
    try:
        response = requests.get(
            VIVO_VIDEO_QUERY_URL,
            params={"task_id": task_id, **_request_params()},
            headers=_request_headers(),
            timeout=60,
        )
        result = response.json()
    except requests.exceptions.Timeout:
        return {"success": False, "task_id": task_id, "error": "视频任务查询超时"}
    except Exception as error:
        return {"success": False, "task_id": task_id, "error": f"视频任务查询异常：{error}"}
    if result.get("code") != 0:
        return {
            "success": False,
            "task_id": task_id,
            "error": result.get("message", "视频任务查询失败"),
            "code": result.get("code"),
            "trace_id": result.get("trace_id", ""),
        }
    data = result.get("data", {})
    if record is None:
        record = {
            "task_id": task_id,
            "cache_key": f"task_{task_id}",
            "poem_id": "",
            "poem_title": "",
            "model": data.get("model", ""),
            "duration": data.get("duration", 0),
            "ratio": data.get("ratio", ""),
            "created_at": _now_text(),
            "video_url": "",
            "error": "",
        }
    record["status"] = data.get("status", "unknown")
    record["updated_at"] = _now_text()
    record["error"] = data.get("error") or ""
    record["resolution"] = data.get("resolution", "")
    if record["status"] == "succeeded":
        source_url = data.get("content", {}).get("video_url", "")
        if not source_url:
            record["status"] = "download_failed"
            record["error"] = "视频任务成功，但结果中没有 video_url"
        else:
            try:
                record["video_url"] = _download_video(source_url, record["cache_key"], task_id)
            except Exception as error:
                record["status"] = "download_failed"
                record["error"] = f"视频生成成功，但下载到本地失败：{error}"
    cache["tasks"][task_id] = record
    return _public_task_result(record)


@router.get("/generate/video/ready-poems")
def list_ready_poem_videos():
    """只读取本地视频缓存；每首诗返回最近一次已下载成功的连续视频。"""
    cache = _load_cache()
    latest_by_poem: dict[str, dict] = {}

    for group in cache["groups"].values():
        candidate = _ready_single_video_candidate(group, cache)
        if not candidate:
            continue
        poem_id = candidate["poem_id"]
        current = latest_by_poem.get(poem_id)
        candidate_order = (candidate["updated_at"], candidate["created_at"], candidate["group_id"])
        current_order = (
            current.get("updated_at", ""),
            current.get("created_at", ""),
            current.get("group_id", ""),
        ) if current else ("", "", "")
        if not current or candidate_order > current_order:
            latest_by_poem[poem_id] = candidate

    videos = sorted(latest_by_poem.values(), key=lambda item: item["poem_id"])
    return {"success": True, "videos": videos}


@router.get("/generate/video/{task_id}")
def query_poem_video(task_id: str):
    """查询单个视频片段；成功后立即下载 MP4 到视频模块自己的静态目录。"""
    cache = _load_cache()
    result = _query_video_task(task_id, cache)
    _save_cache(cache)
    return result


@router.get("/generate/video/group/{group_id}")
def query_poem_video_group(group_id: str):
    """顺序汇总一首诗的多个视频片段状态，并下载已完成的 MP4。"""
    cache = _load_cache()
    group = cache["groups"].get(group_id)
    if not group:
        return {"success": False, "group_id": group_id, "error": "视频任务组不存在或服务已重启"}
    for task_id in group.get("segment_task_ids", []):
        _query_video_task(task_id, cache)
    records = [cache["tasks"][task_id] for task_id in group.get("segment_task_ids", []) if task_id in cache["tasks"]]
    group["status"] = _group_status(records)
    group["updated_at"] = _now_text()
    _save_cache(cache)
    return _public_group_result(group, cache)
