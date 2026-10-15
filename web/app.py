# app.py
# ─────────────────────────────────────────────────────────────
# 무인도 생존 교육 시스템 — 웹 확장판 (Flask)
# 실행:  py app.py   →  브라우저에서 http://127.0.0.1:5000 열기
#
# Flask = 파이썬으로 '내 컴퓨터 안의 작은 웹 서버'를 만드는 도구 (py -m pip install flask)
# 서버 = 브라우저가 "이 페이지 줘", "이 답 맞아?" 하고 물으면 대답해 주는 프로그램
# API  = 브라우저와 서버가 주고받는 약속된 주소들 (/api/...). 데이터는 JSON 형식으로 주고받는다
# ─────────────────────────────────────────────────────────────

from flask import Flask, jsonify, render_template, request
# jsonify = 파이썬 딕셔너리/리스트를 JSON(브라우저가 읽는 데이터 형식)으로 바꿔 보내기
# render_template = templates 폴더의 HTML 파일을 보내기
# request = 브라우저가 보낸 요청(데이터)을 읽는 도구

import game_data as gd   # 같은 폴더의 game_data.py (데이터 + 판정 규칙)

app = Flask(__name__)    # 웹 서버 앱 만들기. static 폴더(이미지·CSS·JS)는 자동으로 연결된다


# @app.get("/주소") = '이 주소로 요청이 오면 아래 함수를 실행해라'라는 표시(데코레이터)
@app.get("/")
def index():
    """첫 화면(HTML)을 보낸다."""
    return render_template("index.html")


@app.get("/api/setup")
def setup():
    """게임 시작에 필요한 정보: 규칙 숫자, 퀘스트(정답 제외), 표류자(정체 제외)."""
    return jsonify({
        "rules": gd.public_rules(),
        "quests": gd.public_quests(),
        "castaways": gd.public_castaways(),
    })


@app.post("/api/check")
def check():
    """답 판정. 브라우저가 {quest_id, answer, tries}를 보내면 결과를 돌려준다."""
    data = request.get_json()
    return jsonify(gd.check_answer(data["quest_id"], data["answer"], data["tries"]))


@app.post("/api/rescue")
def rescue():
    """표류자 선택 결과. {castaway_id, choice, inventory, exp} → 결과·새 가방·EXP 변화."""
    data = request.get_json()
    return jsonify(gd.resolve_choice(data["castaway_id"], data["choice"],
                                     data["inventory"], data["exp"]))


@app.get("/api/supply")
def supply():
    """레벨업 보급 상자에서 나올 물건을 무작위로 하나 정한다."""
    return jsonify({"item": gd.random_supply()})


# 이 파일을 직접 실행했을 때만 서버를 켠다 (다른 파일에서 import할 때는 켜지지 않음)
if __name__ == "__main__":
    print("브라우저에서 http://127.0.0.1:5000 을 여세요. (끄려면 Ctrl + C)")
    app.run(host="127.0.0.1", port=5000)
