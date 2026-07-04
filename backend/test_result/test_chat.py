"""
诗芽小学堂 - 年龄分层对话测试
用法：python test_chat.py
在终端里直接输入，输入 exit 或 quit 结束对话。
结束后自动保存完整对话到 test_result.txt
"""

import requests

BASE_URL = "http://127.0.0.1:8000/chat"

POET_PARAMS = {
    "poet_name": "王之涣",
    "dynasty":   "唐",
    "poem_title": "登鹳雀楼",
    "poem_content": "白日依山尽，黄河入海流，欲穷千里目，更上一层楼。",
}

AGE = 7   # ← 改这里切换年龄：3（小班/中班）或 6（大班/学前班）

DIVIDER = "=" * 55


def send_message(message: str, history: list) -> str:
    payload = {
        "message": message,
        "age": AGE,
        **POET_PARAMS,
        "history": history,
    }
    try:
        resp = requests.post(BASE_URL, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if data.get("success"):
            return data["reply"]
        else:
            return f"[接口报错] {data.get('error')} | {data.get('raw')}"
    except Exception as e:
        return f"[请求失败] {e}"


def run():
    history = []
    log = []
    poet  = POET_PARAMS["poet_name"]
    title = POET_PARAMS["poem_title"]
    age_label = "3-4岁档" if AGE <= 4 else "5-7岁档"
    round_num = 0

    print(f"\n{DIVIDER}")
    print(f"  诗芽小学堂 · 对话测试")
    print(f"  诗人：{poet}   诗目：《{title}》")
    print(f"  年龄：{AGE}岁（{age_label}）")
    print(f"  输入 exit 或 quit 结束")
    print(f"{DIVIDER}\n")

    while True:
        if round_num == 0:
            print(f"【第1轮】诗人主动开口...")
            user_input = ""
        else:
            try:
                user_input = input(f"【第{round_num + 1}轮】你：").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\n对话已中断。")
                break

            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                print(f"\n对话结束，共 {round_num} 轮。")
                break

        reply = send_message(user_input, history)
        print(f"\n{poet}：{reply}\n")

        if user_input != "":
            history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": reply})

        display_q = "（诗人主动开口）" if user_input == "" else user_input
        log.append(f"【第{round_num + 1}轮】")
        log.append(f"你：{display_q}")
        log.append(f"{poet}：{reply}")
        log.append("")

        round_num += 1

    if log:
        output = (
            f"诗人：{poet}   诗目：《{title}》   年龄：{AGE}岁（{age_label}）\n"
            f"{DIVIDER}\n\n"
            + "\n".join(log)
        )
        with open("test_result.txt", "w", encoding="utf-8") as f:
            f.write(output)
        print("对话已保存到 test_result.txt")


if __name__ == "__main__":
    run()
