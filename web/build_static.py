# build_static.py
# ─────────────────────────────────────────────────────────────
# GitHub Pages 배포용 '정적 사이트'를 만드는 스크립트.
# GitHub Pages는 Python 서버를 실행할 수 없어서, Python이 미리 데이터 파일(data.json)을
# 만들어 두고 브라우저(game.js)가 그 파일로 판정하게 한다.
#
# 실행:  py build_static.py   →  저장소 맨 위의 docs/ 폴더가 새로 만들어진다
# 데이터(game_data.py)를 고친 뒤에는 이 스크립트를 다시 실행하고 커밋·푸시하면 사이트에 반영된다.
# ─────────────────────────────────────────────────────────────

import base64
import hashlib
import json
import shutil
from pathlib import Path   # Path = 파일·폴더 경로를 다루는 도구

import game_data as gd

HERE = Path(__file__).parent          # 이 파일이 있는 폴더 (web/)
OUT = HERE.parent / "docs"            # 결과 폴더 (저장소 맨 위의 docs/)


def sha256(text):
    """글자를 SHA-256 해시(되돌릴 수 없는 지문)로 바꾼다. 정답을 그대로 노출하지 않으려고."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def encode(obj):
    """데이터를 base64로 인코딩한다 (한눈에 안 보이게 가리는 정도 — 암호는 아님)."""
    return base64.b64encode(json.dumps(obj, ensure_ascii=False).encode("utf-8")).decode("ascii")


def build_data():
    quests = []
    for q in gd.QUESTS:
        quests.append({
            "id": q["id"], "title": q["title"], "question": q["question"], "hint": q["hint"],
            "answer_hashes": [sha256(gd.normalize(a)) for a in q["answers"]],
            "reveal": encode(q["answers"][0]),   # 두 번 틀렸을 때 공개할 정답
        })
    castaways = []
    for c in gd.CASTAWAYS:
        secret = {"truth": c["truth"], "best": gd.BEST_CHOICE[c["truth"]],
                  "truth_name": gd.TRUTH_NAME[c["truth"]], "explain": c["explain"],
                  "reward_items": c.get("reward_items", [])}
        castaways.append({k: c[k] for k in ("id", "name", "story", "clues", "image")} | {"secret": encode(secret)})
        # 딕셔너리1 | 딕셔너리2 = 두 딕셔너리를 합친 새 딕셔너리
    rules = {"max_tries": gd.MAX_TRIES, "exp_per_level": gd.EXP_PER_LEVEL, "event_chance": gd.EVENT_CHANCE,
             "exp_first_try": gd.EXP_FIRST_TRY, "exp_with_hint": gd.EXP_WITH_HINT,
             "supplies": gd.SUPPLIES, "foods": gd.FOODS}
    return {"rules": rules, "quests": quests, "castaways": castaways}


def main():
    if OUT.exists():
        shutil.rmtree(OUT)                                   # 이전 결과 지우고 새로 만들기
    shutil.copytree(HERE / "static", OUT / "static")         # CSS·JS·이미지 복사
    html = (HERE / "templates" / "index.html").read_text(encoding="utf-8-sig")
    # game.js보다 먼저 '정적 모드'라는 표시를 넣는다 → game.js가 서버 대신 data.json을 쓴다
    html = html.replace('<script src="static/game.js">',
                        '<script>window.STATIC_MODE = true;</script>\n  <script src="static/game.js">')
    (OUT / "index.html").write_text(html, encoding="utf-8")
    (OUT / "data.json").write_text(json.dumps(build_data(), ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / ".nojekyll").write_text("")                       # GitHub Pages가 파일을 가공하지 않도록
    print(f"완료: {OUT}")


if __name__ == "__main__":
    main()
