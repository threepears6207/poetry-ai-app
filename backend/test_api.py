import requests

BASE_URL = "http://127.0.0.1:8000"


def print_result(name, response):
    print(f"\n=== {name} ===")
    print("status:", response.status_code)

    try:
        print("json:", response.json())
    except Exception:
        print("text:", response.text)

    if response.status_code == 200:
        print("result: PASS")
    else:
        print("result: FAIL")


def test_ping():
    response = requests.get(f"{BASE_URL}/ping")
    print_result("GET /ping", response)


def test_search():
    response = requests.get(
        f"{BASE_URL}/poems/search",
        params={
            "keyword": "春",
            "page": 1,
            "page_size": 10
        }
    )
    print_result("GET /poems/search", response)


def test_poem_detail():
    response = requests.get(f"{BASE_URL}/poems/poem_001")
    print_result("GET /poems/poem_001", response)


def test_recommend():
    response = requests.get(
        f"{BASE_URL}/recommend",
        params={
            "user_id": "test_user",
            "limit": 5
        }
    )
    print_result("GET /recommend", response)


def test_add_record():
    response = requests.post(
        f"{BASE_URL}/record",
        json={
            "user_id": "test_user",
            "poem_id": "poem_001",
            "duration_seconds": 30
        }
    )
    print_result("POST /record", response)


def test_record_summary():
    response = requests.get(
        f"{BASE_URL}/record/summary",
        params={
            "user_id": "test_user"
        }
    )
    print_result("GET /record/summary", response)


def test_ocr():
    response = requests.post(
        f"{BASE_URL}/ocr",
        json={
            "image": "床前明月光疑是地上霜",
            "mode": "text"
        }
    )
    print_result("POST /ocr", response)


if __name__ == "__main__":
    print("开始测试后端接口，请确认 FastAPI 已经启动：")
    print(BASE_URL)

    test_ping()
    test_search()
    test_poem_detail()
    test_recommend()
    test_add_record()
    test_record_summary()
    test_ocr()

    print("\n全部测试执行完毕。")