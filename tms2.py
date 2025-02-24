import requests
import time
import datetime
import json
import os

# 🔹 텔레그램 봇 설정 (환경변수 사용)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 🔹 API 설정 (경기도 / 린텍스기업(주))
API_URL = "http://apis.data.go.kr/B552584/cleansys/rltmMesureResult"
API_KEY = os.getenv("API_KEY")
AREA_NAME = "경기도"
FACTORY_NAME = "린텍스기업(주)"

# 🔹 중복 방지용 데이터 저장 파일 (Render에서는 /tmp에 저장)
DATA_FILE = "/tmp/prev_data.json"

# 🔹 이전 데이터 불러오기 (Render가 재시작되더라도 일정 기간 유지)
def load_previous_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as file:
            try:
                data = json.load(file)
                return data.get("prev_mesure_dt"), data.get("prev_nox")
            except json.JSONDecodeError:
                return None, None
    return None, None

# 🔹 이전 데이터 저장 (중복 메시지 방지)
def save_previous_data(prev_mesure_dt, prev_nox):
    with open(DATA_FILE, "w") as file:
        json.dump({"prev_mesure_dt": prev_mesure_dt, "prev_nox": prev_nox}, file)

# 🔹 이전 데이터 불러오기
prev_mesure_dt, prev_nox = load_previous_data()

# 🔹 텔레그램 메시지 전송 함수
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(url, data=payload)

# 🔹 API 데이터 가져오기 & 변경 시에만 메시지 보내기
def fetch_and_send_data():
    global prev_nox, prev_mesure_dt

    while True:
        try:
            # 🔹 API 요청 파라미터
            params = {
                "serviceKey": API_KEY,
                "type": "json",
                "areaNm": AREA_NAME,
                "factManageNm": FACTORY_NAME
            }

            # 🔹 API 호출
            response = requests.get(API_URL, params=params)

            # 🔹 응답 상태 코드 및 본문 출력 (디버깅)
            print(f"🔹 API 호출 시간: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
            print(f"🔹 응답 상태 코드: {response.status_code}")
            print(f"🔹 응답 본문: {response.text}")

            # 🔹 응답이 정상이고, 데이터가 존재할 경우 처리
            if response.status_code == 200 and response.text.strip():
                json_data = response.json()

                # 🔹 `items` 키가 존재하고, 리스트가 비어있지 않은지 확인
                if "body" in json_data["response"] and "items" in json_data["response"]["body"]:
                    items = json_data["response"]["body"]["items"]

                    if items:  # 리스트가 비어있지 않을 때만 실행
                        latest_data = items[0]  # 가장 최근 데이터

                        # 📌 API에서 제공하는 데이터의 측정 시간 (`mesure_dt`) 사용
                        mesure_dt = latest_data.get("mesure_dt", "N/A")
                        nox_value = latest_data.get("nox_mesure_value", None)

                        # 🔹 NOx 값이 null이 아니면 변환
                        nox_value = float(nox_value) if nox_value is not None else None

                        # 🚨 기준 초과 시 아이콘 추가
                        nox_icon = " 🚨" if nox_value is not None and nox_value >= 50 else ""

                        # 🔹 중복 메시지 방지 (이미 보낸 데이터는 다시 보내지 않음)
                        if mesure_dt != prev_mesure_dt or nox_value != prev_nox:
                            message = f"""
📢 *굴뚝 측정 데이터 업데이트* 🏭
📅 측정 시간: `{mesure_dt}`  
🔸 질소산화물 (NOx): `{nox_value} ppm`{nox_icon}
"""

                            send_telegram_message(message)
                            print(f"[{mesure_dt}] 데이터 변동 감지 → 메시지 전송 완료!")

                            # 🔹 데이터 저장 (중복 방지)
                            save_previous_data(mesure_dt, nox_value)
                            prev_mesure_dt, prev_nox = mesure_dt, nox_value
                        else:
                            print(f"[{mesure_dt}] 데이터 변경 없음 → 메시지 전송 안 함")
                    else:
                        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] 응답에 'items'가 비어 있음 → API 데이터가 없음")
                else:
                    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] 응답에 'body' 또는 'items' 키 없음 → API 데이터가 없음")
            else:
                raise ValueError("⚠️ API 응답이 비어 있음")

        except Exception as e:
            print(f"⚠️ API 호출 실패: {e}")

        time.sleep(1800)  # 🔹 30분마다 실행 (API 갱신 주기에 맞춤)
    
# 🔹 실행
fetch_and_send_data()
