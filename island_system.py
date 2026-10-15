# island_system.py
# ─────────────────────────────────────────────────────────────
# 무인도 생존 교육 시스템 (엔딩 추가판)
#   핵심 기능 ① 퀘스트를 차례로 출제하고 답 입력받기
#   핵심 기능 ② CLEAR / 실패 판정 + 오답이면 '미래의 나'가 힌트 주기
#   핵심 기능 ③ 경험치(EXP)·레벨업 + 실패한 퀘스트 재도전 목록
#   보상 연출   레벨업하면 구조 헬기가 보급 상자를 떨어뜨리는 애니메이션
#   돌발 미션   퀘스트 사이·레벨업 직후 '무작위로' 표류자가 해안가에 떠밀려 온다
#               → 단서를 보고 정체를 추리해 [믿는다 / 경계한다 / 지켜본다] 중 선택
#               → 진행 중이던 퀘스트·레벨·EXP는 그대로 유지, 돌발 미션이 끝나면 이어서 진행
#   시연용 키   F2 = 돌발 미션 바로 발생시키기 (무작위를 기다리지 않고 재현하려고)
#   엔딩       탈출 준비도 100% → 버프·디버프 합계로 세 가지 결말 (헬기 / 혼자 뗏목 / 기나긴 표류)
#   퀘스트     quests.json의 100문제를 매번 섞어서 출제 (웹판과 같은 파일을 함께 쓴다)
# ─────────────────────────────────────────────────────────────

import tkinter as tk
import random   # 무작위 뽑기 도구 (보급품, 돌발 미션 발생 여부, 표류자 순서)
import json     # quests.json(문제 데이터 파일)을 읽는 도구
import os       # 파일 경로 다루기
import subprocess, sys   # '처음부터 다시' 할 때 프로그램을 새로 실행하는 도구

# ── 1. 색상과 글꼴 ──
BG = "#0a0f1e"
PANEL = "#111a33"
GLOW = "#3fa9ff"
TEXT = "#d6ecff"
GOLD = "#ffd166"
GREEN = "#5cff9d"
RED = "#ff6b6b"
PURPLE = "#c39bff"
DIM = "#55607a"
FONT = "Malgun Gothic"

# ── 2. 게임 규칙 숫자 ──
MAX_TRIES = 2
EXP_FIRST_TRY = 40
EXP_WITH_HINT = 20
EXP_BASE = 100        # Lv.1 → 2에 필요한 EXP
EXP_STEP = 80         # 레벨이 오를수록 필요 EXP가 이만큼씩 늘어난다 (100 → 180 → 260 ...)
BAR_BLOCKS = 10
EVENT_CHANCE = 0.3    # 퀘스트 하나가 끝날 때마다 돌발 미션이 생길 확률 (0.3 = 30%)

# 엔딩: 탈출 준비도가 ESCAPE_GOAL에 닿으면 섬을 탈출한다
ESCAPE_GOAL = 100
ESCAPE_FIRST_TRY = 5  # 한 번에 맞혔을 때 쌓이는 탈출 준비도
ESCAPE_WITH_HINT = 3  # 힌트를 보고 맞혔을 때
ESCAPE_MIN = 2        # 디버프가 커도 최소 이만큼은 쌓인다 → 언젠가는 반드시 탈출 가능
QUESTS_PER_DAY = 5    # 퀘스트 5개 = 하루

SUPPLIES = ["생수 2병", "통조림", "구급상자", "신호탄", "라이터"]
FOODS = ["통조림", "말린 생선", "생수 2병"]   # 다른 사람이 나눠 먹을 수 있는 물건

# ── 3. 퀘스트 데이터 ──
# 100문제는 같은 폴더의 quests.json에 있다 (웹판도 같은 파일을 읽는다)
# os.path.dirname(__file__) = 이 파이썬 파일이 있는 폴더 → 어디서 실행해도 파일을 찾을 수 있다
QUESTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quests.json")
with open(QUESTS_FILE, encoding="utf-8") as f:   # with = 다 읽으면 파일을 자동으로 닫아 준다
    QUESTS = json.load(f)                        # json.load = JSON 글자 → 파이썬 리스트/딕셔너리

# ── 돌발 미션: 해안가로 떠밀려 오는 표류자들 ──
# truth(정체)는 화면에 처음엔 숨겨 두고, 플레이어가 단서로 추리한 뒤에 공개한다
#   "ally"    = 믿을 수 있는 조력자 → '함께 지낸다'가 정답
#   "thief"   = 보급품을 노리는 사람 → '구조하되 경계한다'가 정답
#   "neutral" = 득실이 반반인 사람   → '구조하되 경계한다'가 무난
# clues는 3개: 처음엔 ①② 두 개만 보이고, ③(결정적 단서)은 [더 살펴보기]를 눌러야 보인다
# look은 애니메이션에서 사람 모습을 그릴 때 쓰는 정보 (머리 모양·색, 옷 색 등)
CASTAWAYS = [
    {
        "name": "구명조끼를 입은 여성", "truth": "ally",
        "look": {"hair": "long", "hair_color": "#3b2416", "shirt": "#e9ecef", "vest": True},
        "story": "파도에 실려 온 나무판자 위에 한 여성이 엎드려 있다. 숨은 붙어 있다.",
        "clues": ["구명조끼 가슴에 '해양 연구소' 로고가 박혀 있다.",
                  "손목에 방수 시계와 작은 GPS 장치를 차고 있다.",
                  "방수 가방 안에 날짜별로 꼼꼼히 적은 해류 관측 일지가 있다."],
        "reward_items": ["구조 무전기", "신호탄"],
        # effects = 선택별 버프/디버프: (이름, 퀘스트마다 탈출 준비도 증감, 즉시 증감)
        "effects": {"trust": ("구조 무전기 연락", 5, 0), "guard": ("무전 주파수 메모", 2, 0)},
        "explain": "로고·장비·꼼꼼한 기록, 세 단서가 모두 '연구와 구조'를 가리켰어. 믿어도 되는 사람이었지.",
    },
    {
        "name": "정장 차림의 남자", "truth": "thief",
        "look": {"hair": "short", "hair_color": "#111111", "shirt": "#2b2d42"},
        "story": "젖은 정장을 입은 남자가 부서진 보트 조각을 붙잡고 해안에 닿았다.",
        "clues": ["비싼 정장인데, 소매가 남의 옷처럼 손등까지 내려온다.",
                  "정신을 차리자마자 '다른 생존자는 없지?'라고 먼저 묻는다.",
                  "안주머니에서 이름이 서로 다른 지갑 세 개가 삐져나와 있다."],
        "effects": {"trust": ("뗏목 재료 도난", -2, -10)},
        "explain": "몸에 안 맞는 옷, 다른 사람이 없는지부터 확인, 남의 지갑 여러 개. 구조는 하되 가방은 지켜야 했어.",
    },
    {
        "name": "늙은 낚시꾼", "truth": "ally",
        "look": {"hair": "cap", "hair_color": "#9a9a9a", "shirt": "#6a994e"},
        "story": "낡은 낚싯배 파편과 함께 노인이 모래 위로 밀려왔다.",
        "clues": ["손바닥 곳곳에 낚싯줄에 쓸린 굳은살이 있다.",
                  "모자에 낚싯바늘이 여러 개 꽂혀 있다.",
                  "깨어나자 하늘을 보며 '내일은 남풍이라 고기가 잘 잡히겠군' 하고 중얼거린다."],
        "reward_items": ["낚싯대", "말린 생선"],
        "effects": {"trust": ("뗏목 만드는 법", 4, 0), "guard": ("물고기 잡는 요령", 2, 0)},
        "explain": "굳은살·낚싯바늘·날씨를 읽는 습관. 오랜 경험을 가진 진짜 어부였어. 섬 생활의 스승이 될 사람이지.",
    },
    {
        "name": "군복 차림의 청년", "truth": "neutral",
        "look": {"hair": "short", "hair_color": "#4a3728", "shirt": "#606c38"},
        "story": "찢어진 군복을 입은 청년이 기침을 하며 해안가로 기어 올라왔다.",
        "clues": ["목에 건 군번줄의 이름과, 그가 말한 이름이 다르다.",
                  "자기 팔의 상처를 붕대로 능숙하게 감는다.",
                  "음식을 보자 눈을 떼지 못한다. 며칠은 굶은 것 같다."],
        "effects": {"trust": ("응급처치 지식", 1, 0), "guard": ("섬 지도", 2, 0)},
        "explain": "이름이 다른 건 의심스럽지만 응급처치 솜씨는 쓸모 있고, 굶주림은 부담이야. "
                   "득도 실도 반반인 사람이라 경계하며 지켜보는 게 가장 무난했어.",
    },
    {
        "name": "선글라스를 낀 여성", "truth": "thief",
        "look": {"hair": "long", "hair_color": "#b5651d", "shirt": "#d62828", "glasses": True},
        "story": "빨간 재킷을 입은 여성이 고무보트에서 굴러떨어져 해안에 쓰러졌다.",
        "clues": ["고무보트에 구멍 하나 없이 멀쩡하다. 조난이라기엔 이상하다.",
                  "'구조 신호'라는 말을 듣자 표정이 굳는다.",
                  "재킷 안쪽에 이 섬의 좌표와 '보급품 위치'라고 적힌 쪽지가 있다."],
        "effects": {"trust": ("보급품 위치 유출", -2, -10)},
        "explain": "멀쩡한 보트, 구조를 싫어하는 표정, 보급품을 노리는 쪽지. 조난자가 아니라 보급품을 노리고 온 사람이었어.",
    },
]

# 선택지: (내부 이름, 버튼 글자) 묶음의 리스트. ( , ) 처럼 괄호로 묶은 값 = 튜플(바꿀 수 없는 리스트)
CHOICES = [("trust", "함께 지낸다\n(믿는다)"),
           ("guard", "구조하되\n경계한다"),
           ("watch", "멀리서\n지켜본다")]
BEST_CHOICE = {"ally": "trust", "thief": "guard", "neutral": "guard"}
TRUTH_NAME = {"ally": "믿을 수 있는 조력자", "thief": "보급품을 노린 사람", "neutral": "득실이 반반인 사람"}

# ── 4. 진행 상태 ──
order = random.sample(QUESTS, len(QUESTS))   # random.sample = 섞인 복사본 (매번 다른 순서로 출제)
current = 0
tries = 0
in_retry = False
finished = False
judged = False         # 현재 퀘스트의 판정이 끝나 '다음으로 넘어가기를 기다리는 중'인가?

level = 1
exp = 0
clear_count = 0
retry_list = []
weak_list = []
inventory = []

# 돌발 미션용 상태
castaways_left = list(CASTAWAYS)
random.shuffle(castaways_left)   # random.shuffle(리스트) = 순서를 무작위로 섞기 (매번 다른 사람이 먼저 등장)
pending_events = []    # 대기열: 아직 처리하지 못한 돌발 미션들 (먼저 생긴 것부터 처리)
busy = False           # 화면 위에 애니메이션이나 돌발 미션 창이 떠 있는 중인가?
events_seen = 0        # 지금까지 발생한 돌발 미션 수
judge_log = []         # 판단 기록: (이름, 맞았는지) 튜플들

# 엔딩용 상태
escape = 0             # 탈출 준비도 (0 → ESCAPE_GOAL)
mods = []              # 받은 버프/디버프: {'name', 'mod', 'who'} 딕셔너리들
attempts = 0           # 판정이 끝난 퀘스트 수 (→ 생존 일수 계산)


def exp_needed(lv):
    """이 레벨에서 다음 레벨까지 필요한 EXP. 레벨이 높을수록 많이 필요하다."""
    return EXP_BASE + EXP_STEP * (lv - 1)


def net_mod():
    """버프·디버프 합계. 플러스면 빨리, 마이너스면 느리게 탈출한다."""
    return sum(m["mod"] for m in mods)


def day():
    """생존 일수 = 1 + (푼 퀘스트 수 ÷ 하루 퀘스트 수의 몫)."""
    return 1 + attempts // QUESTS_PER_DAY


def escape_gain(tries_used):
    """퀘스트 클리어 1번에 쌓이는 탈출 준비도 = 기본값 + 버프 합계 (최소 ESCAPE_MIN)."""
    base = ESCAPE_FIRST_TRY if tries_used == 0 else ESCAPE_WITH_HINT
    return max(ESCAPE_MIN, base + net_mod())


def normalize(text):
    return text.strip().replace(" ", "").lower()


def show_notice(text, color):
    """상단 알림 줄에 메시지를 3초 동안 보여 준다."""
    notice_label.config(text=text, fg=color)
    root.after(3000, lambda: notice_label.config(text="") if notice_label.cget("text") == text else None)


# ── 5. 상태창 ──
def update_status():
    need = exp_needed(level)
    filled = exp * BAR_BLOCKS // need
    bar = "■" * filled + "□" * (BAR_BLOCKS - filled)
    level_label.config(text=f"Lv.{level}")
    exp_label.config(text=f"EXP {bar} {exp}/{need}")
    good = sum(1 for _, ok in judge_log if ok)
    # sum(1 for ...) = 조건에 맞는 것이 몇 개인지 세기. _ 는 '안 쓰는 값'이라는 관례적 이름
    retry_count_label.config(text=f"재도전 {len(retry_list)} · 판단 {good}/{len(judge_log)}")
    bag_label.config(text=f"[가방] {', '.join(inventory) if inventory else '비어 있음'}")
    pct = min(100, escape * 100 // ESCAPE_GOAL)
    escape_label.config(text=f"DAY {day()}   탈출 준비 {'■' * (pct // 10)}{'□' * (10 - pct // 10)} {pct}%")
    # :+d = 숫자 앞에 항상 부호(+/-)를 붙여 표시
    buff_label.config(text="   ".join(f"{'▲' if m['mod'] > 0 else '▼'} {m['name']} {m['mod']:+d}" for m in mods),
                      fg=GREEN if net_mod() >= 0 else RED)
    # 신호탄 버튼: 가방에 신호탄이 있고, 퀘스트를 푸는 중이고, 아직 힌트를 안 봤을 때만 누를 수 있다
    can_use = "신호탄" in inventory and not judged and not finished and not busy and tries == 0
    flare_button.config(state="normal" if can_use else "disabled",
                        text=f"신호탄 쏘기 ×{inventory.count('신호탄')}")
    # .count(값) = 리스트 안에 그 값이 몇 개 있는지 세기


def use_flare():
    """[5단계 직접 수정 기능] 신호탄을 쏘아 미래의 나에게 힌트를 미리 받는다.
    왜? 보급품이 가방에 쌓이기만 하고 쓸 데가 없었다 → 생존 아이템에 '쓰임새'를 주려고.
    규칙: 신호탄 1개 소모, 힌트를 본 것이므로 맞혀도 EXP는 절반(EXP_WITH_HINT)."""
    global tries
    if "신호탄" not in inventory:
        return
    inventory.remove("신호탄")
    tries = 1   # '힌트를 이미 본 상태'로 만든다 → 남은 기회 1번, 정답이면 EXP 20
    quest = order[current]
    hint_label.config(text=f"[미래의 나] 신호탄 확인! {quest['hint']}")
    result_label.config(text=f"신호탄 사용 (남은 기회 {MAX_TRIES - tries})", fg=GOLD)
    update_status()
    answer_entry.focus()


def gain_exp(amount):
    """EXP를 얻고 레벨업 여부(True/False)를 돌려준다."""
    global exp, level
    exp += amount
    leveled = False
    while exp >= exp_needed(level):
        exp -= exp_needed(level)
        level += 1
        leveled = True
    update_status()
    return leveled


def lose_exp(amount):
    """EXP를 잃는다. 0 아래로는 내려가지 않게 한다. 실제로 잃은 양을 돌려준다."""
    global exp
    lost = min(exp, amount)
    exp -= lost
    update_status()
    return lost


# ── 6. 레벨업 보상 애니메이션: 구조 헬기의 보급품 투하 ──
SCENE_W, SCENE_H = 480, 260
HOVER_X = 240
GROUND_Y = 197


def draw_scene(cv):
    cv.create_rectangle(0, 0, SCENE_W, SCENE_H, fill="#13234a", outline="")
    for sx, sy in [(40, 40), (120, 70), (300, 35), (430, 60), (200, 55), (380, 95)]:
        cv.create_text(sx, sy, text="·", fill=TEXT, font=(FONT, 14))
    cv.create_rectangle(0, 215, SCENE_W, SCENE_H, fill="#0d3b66", outline="")
    cv.create_oval(120, 195, 360, 240, fill="#e9c46a", outline="")
    cv.create_line(320, 212, 332, 160, fill="#8b5a2b", width=5)
    for dx, dy in [(-32, 8), (32, 8), (-22, -10), (26, -12)]:
        cv.create_line(332, 160, 332 + dx, 160 + dy, fill="#2a9d8f", width=4)
    cv.create_text(SCENE_W // 2, 18, text="◆ LEVEL UP · SUPPLY DROP ◆",
                   fill=GOLD, font=(FONT, 12, "bold"))


def draw_helicopter(cv, x, y, frame):
    cv.delete("heli")
    t = "heli"
    cv.create_line(x + 25, y, x + 72, y - 6, fill="#7d8ea3", width=5, tags=t)
    if frame % 2 == 0:
        cv.create_line(x + 72, y - 16, x + 72, y + 4, fill=TEXT, width=2, tags=t)
    else:
        cv.create_line(x + 62, y - 6, x + 82, y - 6, fill=TEXT, width=2, tags=t)
    cv.create_oval(x - 32, y - 15, x + 32, y + 15, fill="#4a5a6a", outline=GLOW, width=2, tags=t)
    cv.create_oval(x - 28, y - 10, x - 6, y + 6, fill="#9ad1ff", outline="", tags=t)
    cv.create_line(x - 12, y + 14, x - 12, y + 22, fill="#7d8ea3", width=2, tags=t)
    cv.create_line(x + 12, y + 14, x + 12, y + 22, fill="#7d8ea3", width=2, tags=t)
    cv.create_line(x - 22, y + 22, x + 22, y + 22, fill="#7d8ea3", width=3, tags=t)
    cv.create_line(x, y - 15, x, y - 21, fill="#7d8ea3", width=3, tags=t)
    half = 52 if frame % 2 == 0 else 16
    cv.create_line(x - half, y - 21, x + half, y - 21, fill=TEXT, width=3, tags=t)


def draw_crate(cv, x, y, with_chute):
    cv.delete("crate")
    t = "crate"
    if with_chute:
        cv.create_arc(x - 28, y - 60, x + 28, y - 8, start=0, extent=180,
                      fill="#e76f51", outline="", tags=t)
        cv.create_line(x - 28, y - 34, x - 10, y - 10, fill=TEXT, tags=t)
        cv.create_line(x + 28, y - 34, x + 10, y - 10, fill=TEXT, tags=t)
    cv.create_rectangle(x - 12, y - 10, x + 12, y + 10, fill="#a0522d",
                        outline="#5c2e0e", width=2, tags=t)
    cv.create_line(x - 12, y - 10, x + 12, y + 10, fill="#5c2e0e", width=2, tags=t)
    cv.create_line(x + 12, y - 10, x - 12, y + 10, fill="#5c2e0e", width=2, tags=t)


def play_supply_drop(on_finish):
    """레벨업 보상 애니메이션(약 4초). 끝나면 on_finish(콜백)를 실행한다."""
    global busy
    busy = True
    reward = random.choice(SUPPLIES)
    inventory.append(reward)
    update_status()

    cv = tk.Canvas(root, width=SCENE_W, height=SCENE_H, bg=BG,
                   highlightthickness=2, highlightbackground=GOLD)
    cv.place(relx=0.5, rely=0.55, anchor="center")
    draw_scene(cv)

    def step(frame):
        global busy
        if frame < 40:
            hx = 560 - 8 * frame
        elif frame < 50:
            hx = HOVER_X
        else:
            hx = HOVER_X - 8 * (frame - 50)
        draw_helicopter(cv, hx, 70, frame)

        if frame >= 48:
            cy = min(95 + 3 * (frame - 48), GROUND_Y)
            draw_crate(cv, HOVER_X, cy, with_chute=cy < GROUND_Y)

        if frame == 88:
            cv.create_text(SCENE_W // 2, 100, text=f"보급 상자 획득!  [ {reward} ]",
                           fill=GOLD, font=(FONT, 14, "bold"))
            cv.create_text(SCENE_W // 2, 126, text=f"Lv.{level} 달성 · 미래의 나가 보낸 구조 헬기",
                           fill=TEXT, font=(FONT, 10))

        if frame < 140:
            # 주의: cv.after가 아니라 root.after! 그림판이 스스로 예약한 타이머 안에서
            #       자기 자신을 destroy하면 tkinter 내부 오류가 난다 (3단계 시험에서 발견·수정)
            root.after(30, step, frame + 1)
        else:
            cv.destroy()
            busy = False
            on_finish()

    step(0)


# ── 7. 돌발 미션: 표류자 애니메이션 + 단서 추리 + 선택 ──
EV_W, EV_H = 500, 190
SHORE_X = 175   # 표류자가 멈추는 해안가 x 위치


def draw_beach(cv):
    """해안가 배경: 노을 하늘, 바다, 모래사장."""
    cv.create_rectangle(0, 0, EV_W, EV_H, fill="#22335e", outline="")
    cv.create_oval(400, 20, 440, 60, fill="#ffb4a2", outline="")                 # 지는 해
    cv.create_rectangle(0, 85, EV_W, EV_H, fill="#1d6fa5", outline="")           # 바다
    # create_polygon = 점 여러 개를 이어 만든 다각형. (x1,y1, x2,y2, ...) 순서로 적는다
    cv.create_polygon(0, 105, 140, 95, 250, EV_H, 0, EV_H, fill="#e9c46a", outline="")  # 모래사장
    cv.create_text(EV_W // 2, 14, text="― 해안가 ―", fill=DIM, font=(FONT, 9))


def draw_waves(cv, frame):
    """파도 줄무늬. frame에 따라 x를 조금씩 밀어 출렁이는 것처럼 보이게 한다."""
    cv.delete("wave")
    shift = (frame * 3) % 40
    for i in range(3):    # range(3) = 0, 1, 2 → 파도 세 줄
        y = 110 + i * 28
        for x in range(260 - shift + i * 12, EV_W, 40):   # range(시작, 끝, 간격)
            cv.create_line(x, y, x + 10, y - 4, x + 20, y, smooth=True,
                           fill="#8ecae6", width=2, tags="wave")


def draw_castaway(cv, x, y, look):
    """해안가에 누워 떠밀려 오는 사람을 그린다 (머리가 왼쪽)."""
    cv.delete("person")
    t = "person"
    cv.create_rectangle(x - 52, y + 8, x + 56, y + 15, fill="#8b5a2b", outline="", tags=t)   # 나무판자
    if look["hair"] == "long":
        cv.create_oval(x - 64, y - 11, x - 30, y + 13, fill=look["hair_color"], outline="", tags=t)  # 긴 머리
    cv.create_rectangle(x - 30, y - 7, x + 18, y + 7, fill=look["shirt"], outline="", tags=t)   # 몸통(옷)
    # .get("vest") = 딕셔너리에 "vest"가 있으면 그 값, 없으면 None(거짓)을 돌려준다 → 없어도 오류가 나지 않음
    if look.get("vest"):
        cv.create_rectangle(x - 26, y - 8, x + 4, y + 8, fill="#f77f00", outline="", tags=t)  # 구명조끼
    cv.create_line(x + 18, y - 3, x + 48, y - 3, fill="#3d405b", width=5, tags=t)              # 다리
    cv.create_line(x + 18, y + 4, x + 46, y + 4, fill="#3d405b", width=5, tags=t)
    cv.create_oval(x - 48, y - 9, x - 30, y + 9, fill="#f1c27d", outline="", tags=t)            # 얼굴
    if look["hair"] == "short":
        cv.create_arc(x - 49, y - 10, x - 29, y + 10, start=90, extent=180,
                      fill=look["hair_color"], outline="", tags=t)                            # 짧은 머리
    elif look["hair"] == "cap":
        cv.create_arc(x - 50, y - 11, x - 28, y + 11, start=90, extent=180,
                      fill="#264653", outline="", tags=t)                                     # 모자
        cv.create_line(x - 40, y - 13, x - 40, y + 13, fill="#264653", width=3, tags=t)
    if look.get("glasses"):
        cv.create_oval(x - 40, y - 7, x - 34, y - 1, fill="#000000", outline="", tags=t)        # 선글라스
        cv.create_oval(x - 40, y + 1, x - 34, y + 7, fill="#000000", outline="", tags=t)
    # cv.scale(태그, 기준x, 기준y, 가로배율, 세로배율) = 그 태그의 그림 전체를 (x, y)를 중심으로 확대
    # 왜? 좌표를 하나하나 고치지 않고 한 줄로 사람을 1.6배 크게 보이게 하려고
    cv.scale(t, x, y, 1.6, 1.6)


def resolve_choice(c, choice):
    """선택 결과를 계산해서 (결과 문장, 얻은 EXP)를 돌려준다. 가방·EXP도 여기서 바뀐다."""
    truth = c["truth"]
    name = c["name"]
    if truth == "ally":
        if choice == "trust":
            inventory.extend(c["reward_items"])   # .extend(리스트) = 리스트의 항목을 모두 이어 붙이기
            return f"{name}이(가) 고마워하며 [{', '.join(c['reward_items'])}]을(를) 나눠 주었다!", 60
        if choice == "guard":
            inventory.append(c["reward_items"][0])
            return f"조심스럽게 대하자 {name}도(는) 거리를 두었다. 작은 도움 [{c['reward_items'][0]}]만 받았다.", 20
        return f"{name}은(는) 혼자 섬 반대편으로 걸어가 버렸다. 좋은 동료를 놓쳤다.", 0

    if truth == "thief":
        if choice == "trust":
            if inventory:
                stolen = random.choice(inventory)
                inventory.remove(stolen)          # .remove(값) = 리스트에서 그 값을 하나 지우기
                update_status()
                return f"밤사이 [{stolen}]이(가) 사라졌다! {name}도(는) 함께 사라졌다.", 0
            lost = lose_exp(30)
            return f"훔칠 물건이 없자 {name}은(는) 식량을 몰래 먹어 치웠다. (EXP -{lost})", 0
        if choice == "guard":
            return f"가방을 몸에 지닌 채 구조했다. {name}은(는) 다음 날 조용히 떠났다. 피해 없음! (판단력 보너스)", 40
        return f"멀리서 지켜보는 사이 {name}은(는) 배를 고쳐 떠났다. 피해는 없었다.", 10

    # neutral
    if choice == "trust":
        food = next((f for f in inventory if f in FOODS), None)
        # next((조건에 맞는 것), None) = 조건에 맞는 첫 번째 항목, 없으면 None
        if food:
            inventory.remove(food)
            return f"{name}이(가) 응급처치법을 가르쳐 주었다. 대신 [{food}]을(를) 나눠 먹었다.", 20
        return f"{name}이(가) 응급처치법을 가르쳐 주었다. 나눠 먹을 식량이 없어 함께 굶었다.", 20
    if choice == "guard":
        return f"거리를 두고 지켜보니 {name}은(는) 섬 지도를 그려 두고 떠났다.", 30
    return f"{name}은(는) 며칠 뒤 다른 해안으로 떠났다. 아무 일도 없었다.", 10


def start_event(c, on_done):
    """돌발 미션 창을 띄운다: 떠밀려 오는 애니메이션 → 단서 → 선택 → 결과 → [계속]."""
    global busy, events_seen
    busy = True
    events_seen += 1
    lock_input()   # 뒤에 있는 퀘스트 입력칸은 잠가 둔다 (진행 상태는 그대로)

    box = tk.Frame(root, bg=PANEL, highlightbackground=RED, highlightthickness=2)
    box.place(relx=0.5, rely=0.5, anchor="center", width=550, height=660)
    tk.Label(box, text="⚠ 돌발 미션 : 해안가에 표류자 발견", bg=PANEL, fg=RED,
             font=(FONT, 13, "bold")).pack(pady=(10, 6))
    cv = tk.Canvas(box, width=EV_W, height=EV_H, bg=BG, highlightthickness=0)
    cv.pack()
    draw_beach(cv)
    info = tk.Frame(box, bg=PANEL)   # 단서·버튼·결과가 들어갈 아래쪽 칸
    info.pack(fill="both", expand=True, padx=18, pady=8)

    def arrive(frame):
        """표류자가 파도를 타고 오른쪽에서 해안가로 밀려오는 애니메이션 (약 2.5초)."""
        draw_waves(cv, frame)
        x = max(560 - 5 * frame, SHORE_X)        # max = 둘 중 큰 값 → SHORE_X보다 왼쪽으로 가지 않음
        bob = 0 if x == SHORE_X else (3 if frame % 12 < 6 else -3)   # 물 위에서는 위아래로 출렁
        draw_castaway(cv, x, 140 + bob, c["look"])
        if x > SHORE_X:
            root.after(30, arrive, frame + 1)
        else:
            cv.create_text(EV_W // 2, 50, text="해안가에 누군가 떠밀려 왔다!",
                           fill=GOLD, font=(FONT, 13, "bold"))
            show_clues()

    def show_clues():
        """이야기와 단서 ①②를 보여 주고, ③은 [더 살펴보기]로 숨겨 둔다."""
        tk.Label(info, text=f"[{c['name']}]  {c['story']}", bg=PANEL, fg=TEXT,
                 font=(FONT, 10), wraplength=500, justify="left").pack(anchor="w")
        tk.Label(info, text=f"단서 ① {c['clues'][0]}", bg=PANEL, fg=GLOW,
                 font=(FONT, 10), wraplength=500, justify="left").pack(anchor="w", pady=(6, 0))
        tk.Label(info, text=f"단서 ② {c['clues'][1]}", bg=PANEL, fg=GLOW,
                 font=(FONT, 10), wraplength=500, justify="left").pack(anchor="w")
        clue3 = tk.Label(info, text="단서 ③ ???  (더 살펴보면 알 수 있다)", bg=PANEL, fg=DIM,
                         font=(FONT, 10), wraplength=500, justify="left")
        clue3.pack(anchor="w")

        def look_closer():
            clue3.config(text=f"단서 ③ {c['clues'][2]}", fg=GOLD)
            look_button.config(state="disabled", text="모두 살펴봤다")

        look_button = tk.Button(info, text="◎ 더 살펴보기", command=look_closer,
                                font=(FONT, 9), bg=PANEL, fg=GOLD, relief="solid", bd=1)
        look_button.pack(pady=(6, 4))
        tk.Label(info, text="[미래의 나] 구한다고 다 도움이 되는 건 아니야. 단서로 판단해.",
                 bg=PANEL, fg=PURPLE, font=(FONT, 9)).pack()

        row = tk.Frame(info, bg=PANEL)
        row.pack(pady=8)
        for key, label in CHOICES:   # 튜플 (key, label)을 두 변수로 나눠 받기
            # lambda k=key: ... = 반복문 안에서 '지금의 key 값'을 버튼마다 따로 기억시키는 방법
            #   (k=key 없이 쓰면 모든 버튼이 마지막 key 값만 기억하는 실수가 생긴다)
            tk.Button(row, text=label, command=lambda k=key: choose(k, row),
                      font=(FONT, 10, "bold"), bg=GLOW, fg=BG, activebackground=GOLD,
                      relief="flat", width=12, height=2).pack(side="left", padx=5)

    def choose(choice, row):
        """선택 → 결과 계산 → 정체 공개 + 미래의 나 해설."""
        row.destroy()   # 선택 버튼 줄을 없애 두 번 고르지 못하게
        text, gained = resolve_choice(c, choice)
        correct = choice == BEST_CHOICE[c["truth"]]
        judge_log.append((c["name"], correct))
        leveled = gain_exp(gained) if gained > 0 else False
        effect = c.get("effects", {}).get(choice)   # 엔딩에 영향을 주는 버프/디버프 (없으면 None)
        if effect:
            global escape
            name, mod, instant = effect               # 튜플을 세 변수로 나눠 받기
            mods.append({"name": name, "mod": mod, "who": c["name"]})
            escape = max(0, escape + instant)
        update_status()

        verdict = "✔ 좋은 판단" if correct else "✘ 아쉬운 판단"
        tk.Label(info, text=f"{verdict}   EXP +{gained}", bg=PANEL,
                 fg=GREEN if correct else RED, font=(FONT, 12, "bold")).pack(pady=(4, 2))
        tk.Label(info, text=text, bg=PANEL, fg=TEXT, font=(FONT, 10),
                 wraplength=500).pack()
        if effect:
            if mod > 0:
                effect_text, effect_color = f"▲ 버프 [{name}] 퀘스트마다 탈출 +{mod}", GREEN
            else:
                effect_text, effect_color = f"▼ 디버프 [{name}] 퀘스트마다 탈출 {mod} · 탈출 준비 {instant}", RED
            tk.Label(info, text=effect_text, bg=PANEL, fg=effect_color,
                     font=(FONT, 10, "bold")).pack(pady=(2, 0))
        tk.Label(info, text=f"정체: {TRUTH_NAME[c['truth']]}", bg=PANEL, fg=GOLD,
                 font=(FONT, 10, "bold")).pack(pady=(4, 0))
        tk.Label(info, text=f"[미래의 나] {c['explain']}", bg=PANEL, fg=PURPLE,
                 font=(FONT, 9), wraplength=500).pack(pady=(2, 6))
        tk.Button(info, text="계속 ▶", command=lambda: finish(leveled),
                  font=(FONT, 10, "bold"), bg=GOLD, fg=BG, relief="flat", width=10).pack()

    def finish(leveled):
        global busy
        box.destroy()
        busy = False
        if leveled:
            play_supply_drop(on_done)   # 돌발 미션으로 레벨업했으면 보급 헬기도 등장
        else:
            on_done()

    arrive(0)


def pick_castaway():
    """아직 등장하지 않은 표류자 한 명을 꺼낸다. 없으면 None."""
    return castaways_left.pop(0) if castaways_left else None


def run_events_then(final):
    """대기열의 돌발 미션을 하나씩 모두 처리한 뒤 final 함수를 실행한다.
    ★ 돌발 상황 해결의 핵심: 새 일은 대기열에 넣고, 기존 진행(final)은 끝까지 미뤄 두었다가 이어서 한다."""
    if pending_events:
        c = pending_events.pop(0)
        start_event(c, lambda: run_events_then(final))
    else:
        final()


def resume_quest():
    """F2로 퀘스트 도중에 생긴 돌발 미션이 끝났을 때, 풀던 퀘스트로 그대로 돌아간다."""
    if not finished and not judged:
        answer_entry.config(state="normal")
        submit_button.config(state="normal")
        answer_entry.focus()
        update_status()


def on_force_event(event=None):
    """F2 키 = 시연용으로 돌발 미션을 바로 발생시킨다."""
    c = pick_castaway()
    if c is None:
        show_notice("[알림] 더 이상 떠밀려 올 사람이 없습니다.", DIM)
        return
    pending_events.append(c)
    if not busy:
        run_events_then(resume_quest)
    # busy(다른 창이 떠 있는 중)라면 대기열에만 넣어 두고, 지금 창이 끝나면 차례대로 처리된다


# ── 8. 퀘스트 진행 ──
def show_quest():
    global judged
    judged = False
    quest = order[current]
    round_name = "재도전" if in_retry else "QUEST"
    progress_label.config(text=f"DAY {day()} · {round_name} {current + 1} / {len(order)}")
    title_label.config(text=f"【 {quest['title']} 】")
    question_label.config(text=quest["question"])
    hint_label.config(text="")
    result_label.config(text="")
    answer_entry.config(state="normal")
    submit_button.config(state="normal")
    answer_entry.delete(0, tk.END)
    answer_entry.focus()
    update_status()


def next_quest():
    global current, tries, order, in_retry, retry_list
    current += 1
    tries = 0
    if current < len(order):
        show_quest()
    elif not in_retry and len(retry_list) > 0:
        order = retry_list
        retry_list = []
        current = 0
        in_retry = True
        show_notice("[알림] 재도전 퀘스트가 발동되었습니다.", GOLD)
        show_quest()
    else:
        # 문제를 다 풀었는데 아직 탈출 준비가 덜 됐다 → 섞어서 다시 (혼자서도 결국은 탈출 가능)
        order = random.sample(QUESTS, len(QUESTS))
        current = 0
        in_retry = False
        retry_list = []
        show_notice("[알림] 아직 섬을 벗어나지 못했다. 생존 퀘스트가 다시 시작된다.", GOLD)
        show_quest()


def finish_quest(leveled, delay):
    """퀘스트 판정이 끝난 뒤의 흐름: (레벨업 연출) → (돌발 미션) → 다음 퀘스트."""
    # 무작위로 돌발 미션 발생. random.random() = 0 이상 1 미만의 무작위 소수
    roll = random.random() < EVENT_CHANCE
    # 시연을 위해: 첫 라운드 3번째 퀘스트까지 한 번도 안 나왔다면 반드시 한 번은 발생
    must = events_seen == 0 and not in_retry and current == 2
    if (roll or must) and not in_retry and castaways_left:
        pending_events.append(pick_castaway())

    def go():
        if busy:                     # F2로 띄운 창이 아직 떠 있으면 잠시 뒤 다시 시도
            root.after(300, go)
        elif leveled:
            play_supply_drop(after_level)
        else:
            after_level()

    def after_level():
        # 탈출 준비 완료면 엔딩, 아니면 (돌발 미션) → 다음 퀘스트
        if escape >= ESCAPE_GOAL:
            show_ending()
        else:
            run_events_then(next_quest)

    root.after(delay, go)


def draw_raft(cv, x, y):
    """엔딩용 뗏목 (갑판 + 돛대 + 삼각 돛)."""
    cv.delete("raft")
    cv.create_rectangle(x - 22, y, x + 22, y + 7, fill="#8b5a2b", outline="#5c3b1e", tags="raft")
    cv.create_line(x, y, x, y - 30, fill="#5c3b1e", width=3, tags="raft")
    cv.create_polygon(x + 2, y - 30, x + 2, y - 4, x + 22, y - 6, fill="#f1e3c6", outline="", tags="raft")


def draw_rain(cv, frame):
    """기나긴 표류 엔딩의 비. frame마다 빗줄기 위치를 조금씩 옮긴다."""
    cv.delete("rain")
    for i in range(45):
        rx = (i * 53 + frame * 7) % EV_W
        ry = (i * 37 + frame * 11) % EV_H
        cv.create_line(rx, ry, rx - 4, ry + 10, fill="#9fb3c8", tags="rain")


def show_ending():
    """탈출 준비도 100% → 엔딩. 버프·디버프 합계로 세 가지 결말이 갈린다."""
    global finished, busy
    finished = True
    busy = True
    lock_input()
    net = net_mod()
    # dict.fromkeys(...) = 순서는 지키면서 중복 이름을 없애는 방법
    allies = ", ".join(dict.fromkeys(m["who"] for m in mods if m["mod"] > 0))
    betrayers = ", ".join(dict.fromkeys(m["who"] for m in mods if m["mod"] < 0))
    days = day()
    if net > 0:
        kind, color, title = "ENDING A · RESCUE", GREEN, "구조 헬기 귀환"
        story = (f"{allies}의 도움으로 탈출 준비가 빠르게 끝났다.\n"
                 f"생존 {days}일째 아침, 무전을 받은 구조 헬기가 해안에 내려앉았다.")
        future = "사람을 보는 눈이 너를 살렸어. 혼자였다면 훨씬 오래 걸렸을 거야."
    elif net == 0:
        kind, color, title = "ENDING B · SOLO", GOLD, "홀로 뗏목 탈출"
        story = ("누구의 도움도 없이, 직접 배운 생존 지식만으로 뗏목을 완성했다.\n"
                 f"생존 {days}일째, 혼자 노를 저어 수평선을 넘었다.")
        future = "오래 걸렸지만, 그 시간이 지금의 나를 만들었지."
    else:
        kind, color, title = "ENDING C · DRIFT", RED, "기나긴 표류"
        story = (f"{betrayers}에게 속아 귀한 것을 잃었다. 다시 처음부터 준비해야 했다.\n"
                 f"생존 {days}일째, 비바람 속에서 겨우 섬을 떠났다.")
        future = "그때 단서를 더 살펴봤더라면… 사실, 이게 내가 겪은 이야기야. 그래서 이 시스템을 만든 거고."

    box = tk.Frame(root, bg=PANEL, highlightbackground=GOLD, highlightthickness=2)
    box.place(relx=0.5, rely=0.5, anchor="center", width=550, height=540)
    cv = tk.Canvas(box, width=EV_W, height=EV_H, bg=BG, highlightthickness=0)
    cv.pack(pady=(14, 8))
    draw_beach(cv)
    if net < 0:   # 폭풍우: 하늘과 바다를 어둡게 다시 칠한다
        cv.create_rectangle(0, 0, EV_W, 85, fill="#2b2f3a", outline="")
        cv.create_rectangle(0, 85, EV_W, EV_H, fill="#1c3b52", outline="")
        cv.create_polygon(0, 105, 140, 95, 250, EV_H, 0, EV_H, fill="#9c8a62", outline="")

    def animate(frame):
        if net > 0:   # 헬기가 날아와 해안에 내려앉는다
            x = max(560 - 6 * frame, 300)
            y = min(40 + frame, 105)
            draw_helicopter(cv, x, y, frame)
        else:         # 뗏목이 수평선 쪽으로 떠나간다 (표류 엔딩은 비까지)
            draw_raft(cv, 240 + frame * 1.2, 112 + (2 if frame % 20 < 10 else -2))
            if net < 0:
                draw_rain(cv, frame)
        if frame < 180:
            root.after(40, animate, frame + 1)

    animate(0)

    good = sum(1 for _, ok in judge_log if ok)
    tk.Label(box, text=kind, bg=PANEL, fg=color, font=(FONT, 10, "bold")).pack()
    tk.Label(box, text=title, bg=PANEL, fg=GOLD, font=(FONT, 18, "bold")).pack(pady=(2, 6))
    tk.Label(box, text=story, bg=PANEL, fg=TEXT, font=(FONT, 10), wraplength=500,
             justify="center").pack()
    tk.Label(box, text=f"[미래의 나] {future}", bg=PANEL, fg=PURPLE, font=(FONT, 10),
             wraplength=500).pack(pady=(10, 10))
    tk.Label(box, text=(f"생존 {days}일 · 푼 퀘스트 {attempts}개 · 최종 Lv.{level}\n"
                        f"클리어 {clear_count}개 · 표류자 판단 {good}/{len(judge_log)} · 버프 합계 {net:+d}"),
             bg=BG, fg=TEXT, font=(FONT, 10), padx=16, pady=8).pack()
    tk.Button(box, text="처음부터 다시", command=restart_game, font=(FONT, 11, "bold"),
              bg=GOLD, fg=BG, relief="flat", width=14).pack(pady=14)


def restart_game():
    """이 프로그램을 새로 실행하고 지금 창은 닫는다 → 모든 상태가 처음으로 돌아간다."""
    subprocess.Popen([sys.executable, os.path.abspath(__file__)])
    root.destroy()


def lock_input():
    answer_entry.config(state="disabled")
    submit_button.config(state="disabled")
    flare_button.config(state="disabled")


def on_submit():
    global tries, clear_count, judged, escape, attempts
    if busy or judged:   # 애니메이션·돌발 미션 중이거나 이미 판정했으면 무시
        return
    user_text = answer_entry.get()
    if normalize(user_text) == "":
        result_label.config(text="[경고] 답을 입력하십시오.", fg=GOLD)
        return

    quest = order[current]
    correct_list = [normalize(a) for a in quest["answers"]]

    if normalize(user_text) in correct_list:
        reward = EXP_FIRST_TRY if tries == 0 else EXP_WITH_HINT
        clear_count += 1
        attempts += 1
        gain = escape_gain(tries)
        escape += gain
        result_label.config(text=f"▶ QUEST CLEAR   EXP +{reward} · 탈출 +{gain}", fg=GREEN)
        hint_label.config(text="")
        judged = True
        lock_input()
        leveled = gain_exp(reward)
        if leveled:
            show_notice(f"[알림] 레벨이 올랐습니다!  Lv.{level}", GOLD)
        finish_quest(leveled, 900 if leveled else 1200)
    else:
        tries += 1
        if tries < MAX_TRIES:
            result_label.config(text=f"✘ 오답 (남은 기회 {MAX_TRIES - tries})", fg=RED)
            hint_label.config(text=f"[미래의 나] {quest['hint']}")
            answer_entry.delete(0, tk.END)
            update_status()   # 힌트가 이미 나왔으니 신호탄 버튼을 잠그기 위해
        else:
            result_label.config(text=f"▶ QUEST FAILED   정답: {quest['answers'][0]}", fg=RED)
            if in_retry:
                weak_list.append(quest)
            else:
                retry_list.append(quest)
            attempts += 1
            judged = True
            update_status()
            lock_input()
            finish_quest(False, 2000)


# ── 9. 화면 만들기 ──
root = tk.Tk()
root.title("SYSTEM :: 무인도 생존 교육")
root.geometry("600x740")
root.configure(bg=BG)

panel = tk.Frame(root, bg=PANEL, highlightbackground=GLOW, highlightthickness=2)
panel.pack(padx=20, pady=20, fill="both", expand=True)

tk.Label(panel, text="◆  S Y S T E M  ◆", bg=PANEL, fg=GLOW,
         font=(FONT, 16, "bold")).pack(pady=(16, 4))

status = tk.Frame(panel, bg=BG, highlightbackground=GLOW, highlightthickness=1)
status.pack(padx=24, pady=(4, 0), fill="x")
level_label = tk.Label(status, text="", bg=BG, fg=GOLD, font=(FONT, 12, "bold"))
level_label.pack(side="left", padx=10, pady=4)
exp_label = tk.Label(status, text="", bg=BG, fg=GLOW, font=(FONT, 11))
exp_label.pack(side="left", padx=4)
retry_count_label = tk.Label(status, text="", bg=BG, fg=DIM, font=(FONT, 9))
retry_count_label.pack(side="right", padx=10)

# 엔딩 조건: 생존 일수 · 탈출 준비도 · 받은 버프/디버프
escape_label = tk.Label(panel, text="", bg=PANEL, fg=GREEN, font=(FONT, 10, "bold"))
escape_label.pack(pady=(4, 0))
buff_label = tk.Label(panel, text="", bg=PANEL, fg=GREEN, font=(FONT, 9), wraplength=520)
buff_label.pack()

bag_label = tk.Label(panel, text="", bg=PANEL, fg=DIM, font=(FONT, 9))
bag_label.pack(pady=(2, 0))

notice_label = tk.Label(panel, text="", bg=PANEL, fg=GOLD, font=(FONT, 10, "bold"))
notice_label.pack(pady=(2, 0))

tk.Label(panel,
         text="[알림] 미래의 당신이 설계한 생존 교육 시스템이 활성화되었습니다.\n"
              "퀘스트를 클리어하여 무인도에서 살아남으십시오.",
         bg=PANEL, fg=TEXT, font=(FONT, 9), justify="center",
         wraplength=480).pack(pady=(2, 8))

progress_label = tk.Label(panel, text="", bg=PANEL, fg=GLOW, font=(FONT, 9, "bold"))
progress_label.pack()

title_label = tk.Label(panel, text="", bg=PANEL, fg=GOLD, font=(FONT, 12, "bold"))
title_label.pack(pady=(2, 0))

question_label = tk.Label(panel, text="", bg=PANEL, fg=TEXT, font=(FONT, 11), justify="center")
question_label.pack(pady=(8, 12))

answer_entry = tk.Entry(panel, font=(FONT, 12), width=24, justify="center",
                        bg=BG, fg=TEXT, insertbackground=TEXT,
                        disabledbackground=BG, disabledforeground=DIM,
                        relief="flat", highlightthickness=1,
                        highlightbackground=GLOW, highlightcolor=GOLD)
answer_entry.pack(ipady=4)

# [확인] 버튼과 [신호탄] 버튼을 가로로 나란히 놓기 위한 틀
button_row = tk.Frame(panel, bg=PANEL)
button_row.pack(pady=10)
submit_button = tk.Button(button_row, text="확 인", command=on_submit, font=(FONT, 11, "bold"),
                          bg=GLOW, fg=BG, activebackground=GOLD, relief="flat", width=12)
submit_button.pack(side="left", padx=4)
# 5단계 직접 수정 기능: 가방의 신호탄으로 힌트를 미리 보기
flare_button = tk.Button(button_row, text="신호탄 쏘기 (힌트)", command=use_flare,
                         font=(FONT, 9, "bold"), bg=PANEL, fg=GOLD,
                         activebackground=GOLD, activeforeground=BG,
                         disabledforeground=DIM, relief="solid", bd=1, width=16)
flare_button.pack(side="left", padx=4)

result_label = tk.Label(panel, text="", bg=PANEL, fg=TEXT, font=(FONT, 11, "bold"))
result_label.pack()

hint_label = tk.Label(panel, text="", bg=PANEL, fg=PURPLE, font=(FONT, 10),
                      wraplength=460, justify="center")
hint_label.pack(pady=(6, 0))

tk.Label(panel, text="F2 : 돌발 미션 시연", bg=PANEL, fg=DIM,
         font=(FONT, 8)).pack(side="bottom", pady=6)

answer_entry.bind("<Return>", lambda event: on_submit())
root.bind("<F2>", on_force_event)   # 창 어디서든 F2 키를 누르면 on_force_event 실행

update_status()
show_quest()
root.mainloop()
