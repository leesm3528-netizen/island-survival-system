# game_data.py
# ─────────────────────────────────────────────────────────────
# 웹 버전의 '두뇌': 데이터와 판정 규칙을 모두 Python이 가지고 있다.
# 브라우저(JavaScript)는 화면과 애니메이션만 담당하고, 정답·정체는 여기서만 판정한다.
# 왜? 정답이나 표류자의 정체를 브라우저로 보내면 개발자 도구로 미리 볼 수 있기 때문.
# (tkinter 버전 island_system.py의 데이터·규칙을 웹용으로 옮겨 온 것)
# ─────────────────────────────────────────────────────────────

import random

MAX_TRIES = 2
EXP_FIRST_TRY = 40
EXP_WITH_HINT = 20
EXP_PER_LEVEL = 100
EVENT_CHANCE = 0.4

SUPPLIES = ["생수 2병", "통조림", "구급상자", "신호탄", "라이터"]
FOODS = ["통조림", "말린 생선", "생수 2병"]

QUESTS = [
    {"id": "q1", "title": "일일 퀘스트: 생존 기초 ① 물",
     "question": "바닷물을 그대로 마시면 안 되는 이유는\n물속에 무엇이 너무 많기 때문인가? (한 단어)",
     "answers": ["소금", "염분", "나트륨"],
     "hint": "바닷물 맛을 떠올려 봐. 그 '짠맛'의 정체가 뭐였지?"},
    {"id": "q2", "title": "일일 퀘스트: 생존 기초 ② 불",
     "question": "불씨를 옮겨 붙여 불을 크게 키우는\n마른 풀·나뭇조각을 무엇이라 하는가?",
     "answers": ["불쏘시개", "부싯깃"],
     "hint": "불○○개. 불을 '쑤셔서' 일으킨다는 뜻이야."},
    {"id": "q3", "title": "일일 퀘스트: 생존 기초 ③ 구조",
     "question": "모래사장에 크게 써서 구조를 요청하는\n국제 조난 신호 알파벳 세 글자는?",
     "answers": ["sos"],
     "hint": "모스 부호로 · · · − − − · · · 야. 앞뒤가 같은 글자지."},
    {"id": "q4", "title": "일일 퀘스트: 생존 기초 ④ 수분",
     "question": "사람이 하루에 마셔야 하는 물은\n최소 약 몇 리터인가? (숫자)",
     "answers": ["2", "2리터", "2l"],
     "hint": "편의점 큰 생수병 한 병 정도였어."},
    {"id": "q5", "title": "일일 퀘스트: 생존 기초 ⑤ 방향",
     "question": "나침반이 없을 때, 아침에 해가 떠오르는 쪽은\n어느 방향인가?",
     "answers": ["동", "동쪽"],
     "hint": "'동해 물과 백두산이~' 해가 뜨는 바다 쪽이야."},
]

# image = perchanceai.app에서 만든 일러스트 (static/img 폴더)
CASTAWAYS = [
    {"id": "researcher", "name": "구명조끼를 입은 여성", "truth": "ally", "image": "castaway_researcher.jpg",
     "story": "파도에 실려 온 나무판자 위에 한 여성이 엎드려 있다. 숨은 붙어 있다.",
     "clues": ["구명조끼 가슴에 '해양 연구소' 로고가 박혀 있다.",
               "손목에 방수 시계와 작은 GPS 장치를 차고 있다.",
               "방수 가방 안에 날짜별로 꼼꼼히 적은 해류 관측 일지가 있다."],
     "reward_items": ["구조 무전기", "신호탄"],
     "explain": "로고·장비·꼼꼼한 기록, 세 단서가 모두 '연구와 구조'를 가리켰어. 믿어도 되는 사람이었지."},
    {"id": "suit", "name": "정장 차림의 남자", "truth": "thief", "image": "castaway_suit.jpg",
     "story": "젖은 정장을 입은 남자가 부서진 보트 조각을 붙잡고 해안에 닿았다.",
     "clues": ["비싼 정장인데, 소매가 남의 옷처럼 손등까지 내려온다.",
               "정신을 차리자마자 '다른 생존자는 없지?'라고 먼저 묻는다.",
               "안주머니에서 이름이 서로 다른 지갑 세 개가 삐져나와 있다."],
     "explain": "몸에 안 맞는 옷, 다른 사람이 없는지부터 확인, 남의 지갑 여러 개. 구조는 하되 가방은 지켜야 했어."},
    {"id": "fisherman", "name": "늙은 낚시꾼", "truth": "ally", "image": "castaway_fisherman.jpg",
     "story": "낡은 낚싯배 파편과 함께 노인이 모래 위로 밀려왔다.",
     "clues": ["손바닥 곳곳에 낚싯줄에 쓸린 굳은살이 있다.",
               "모자에 낚싯바늘이 여러 개 꽂혀 있다.",
               "깨어나자 하늘을 보며 '내일은 남풍이라 고기가 잘 잡히겠군' 하고 중얼거린다."],
     "reward_items": ["낚싯대", "말린 생선"],
     "explain": "굳은살·낚싯바늘·날씨를 읽는 습관. 오랜 경험을 가진 진짜 어부였어. 섬 생활의 스승이 될 사람이지."},
    {"id": "soldier", "name": "군복 차림의 청년", "truth": "neutral", "image": "castaway_soldier.jpg",
     "story": "찢어진 군복을 입은 청년이 기침을 하며 해안가로 기어 올라왔다.",
     "clues": ["목에 건 군번줄의 이름과, 그가 말한 이름이 다르다.",
               "자기 팔의 상처를 붕대로 능숙하게 감는다.",
               "음식을 보자 눈을 떼지 못한다. 며칠은 굶은 것 같다."],
     "explain": "이름이 다른 건 의심스럽지만 응급처치 솜씨는 쓸모 있고, 굶주림은 부담이야. "
                "득도 실도 반반인 사람이라 경계하며 지켜보는 게 가장 무난했어."},
    {"id": "sunglasses", "name": "선글라스를 낀 여성", "truth": "thief", "image": "castaway_sunglasses.jpg",
     "story": "빨간 재킷을 입은 여성이 고무보트에서 굴러떨어져 해안에 쓰러졌다.",
     "clues": ["고무보트에 구멍 하나 없이 멀쩡하다. 조난이라기엔 이상하다.",
               "'구조 신호'라는 말을 듣자 표정이 굳는다.",
               "재킷 안쪽에 이 섬의 좌표와 '보급품 위치'라고 적힌 쪽지가 있다."],
     "explain": "멀쩡한 보트, 구조를 싫어하는 표정, 보급품을 노리는 쪽지. 조난자가 아니라 보급품을 노리고 온 사람이었어."},
]

BEST_CHOICE = {"ally": "trust", "thief": "guard", "neutral": "guard"}
TRUTH_NAME = {"ally": "믿을 수 있는 조력자", "thief": "보급품을 노린 사람", "neutral": "득실이 반반인 사람"}


def normalize(text):
    """공백·대소문자 차이를 없앤다."""
    return str(text).strip().replace(" ", "").lower()


def find(items, item_id):
    """id로 항목 하나를 찾는다. 없으면 None."""
    return next((it for it in items if it["id"] == item_id), None)


def public_quests():
    """브라우저로 보낼 퀘스트 정보. 정답(answers)은 빼고 보낸다."""
    return [{k: q[k] for k in ("id", "title", "question", "hint")} for q in QUESTS]
    # {k: q[k] for k in (...)} = 딕셔너리 컴프리헨션: 필요한 이름표만 골라 새 딕셔너리 만들기


def public_castaways():
    """브라우저로 보낼 표류자 정보. 정체(truth)와 해설(explain)은 빼고 보낸다."""
    return [{k: c[k] for k in ("id", "name", "story", "clues", "image")} for c in CASTAWAYS]


def check_answer(quest_id, answer, tries):
    """답을 판정한다. tries = 이번 답 이전까지 틀린 횟수(힌트·신호탄 포함)."""
    q = find(QUESTS, quest_id)
    if q is None:
        return {"error": "unknown quest"}
    correct = normalize(answer) in [normalize(a) for a in q["answers"]]
    result = {"correct": correct}
    if correct:
        result["exp"] = EXP_FIRST_TRY if tries == 0 else EXP_WITH_HINT
    elif tries + 1 >= MAX_TRIES:
        result["reveal"] = q["answers"][0]   # 기회를 다 썼을 때만 정답 공개
    return result


def resolve_choice(castaway_id, choice, inventory, exp):
    """표류자 선택 결과를 계산한다. 새 가방과 EXP 변화량을 돌려준다."""
    c = find(CASTAWAYS, castaway_id)
    if c is None or choice not in ("trust", "guard", "watch"):
        return {"error": "bad request"}
    inv = list(inventory)
    truth, name = c["truth"], c["name"]
    delta = 0

    if truth == "ally":
        if choice == "trust":
            inv.extend(c["reward_items"])
            text, delta = f"{name}이(가) 고마워하며 [{', '.join(c['reward_items'])}]을(를) 나눠 주었다!", 60
        elif choice == "guard":
            inv.append(c["reward_items"][0])
            text, delta = f"조심스럽게 대하자 {name}도(는) 거리를 두었다. 작은 도움 [{c['reward_items'][0]}]만 받았다.", 20
        else:
            text = f"{name}은(는) 혼자 섬 반대편으로 걸어가 버렸다. 좋은 동료를 놓쳤다."
    elif truth == "thief":
        if choice == "trust":
            if inv:
                stolen = random.choice(inv)
                inv.remove(stolen)
                text = f"밤사이 [{stolen}]이(가) 사라졌다! {name}도(는) 함께 사라졌다."
            else:
                delta = -min(exp, 30)
                text = f"훔칠 물건이 없자 {name}은(는) 식량을 몰래 먹어 치웠다. (EXP {delta})"
        elif choice == "guard":
            text, delta = f"가방을 몸에 지닌 채 구조했다. {name}은(는) 다음 날 조용히 떠났다. 피해 없음! (판단력 보너스)", 40
        else:
            text, delta = f"멀리서 지켜보는 사이 {name}은(는) 배를 고쳐 떠났다. 피해는 없었다.", 10
    else:  # neutral
        if choice == "trust":
            food = next((f for f in inv if f in FOODS), None)
            if food:
                inv.remove(food)
                text = f"{name}이(가) 응급처치법을 가르쳐 주었다. 대신 [{food}]을(를) 나눠 먹었다."
            else:
                text = f"{name}이(가) 응급처치법을 가르쳐 주었다. 나눠 먹을 식량이 없어 함께 굶었다."
            delta = 20
        elif choice == "guard":
            text, delta = f"거리를 두고 지켜보니 {name}은(는) 섬 지도를 그려 두고 떠났다.", 30
        else:
            text, delta = f"{name}은(는) 며칠 뒤 다른 해안으로 떠났다. 아무 일도 없었다.", 10

    return {
        "text": text,
        "exp_delta": delta,
        "inventory": inv,
        "correct": choice == BEST_CHOICE[truth],
        "truth_name": TRUTH_NAME[truth],
        "explain": c["explain"],
    }


def random_supply():
    return random.choice(SUPPLIES)
