"""카페인 브레이크 — 개인용 카페인 습관 기록·행동지원 앱.
실행: pip install -r requirements.txt && streamlit run app.py
배포: 두 파일을 GitHub 저장소에 올리고 Streamlit Community Cloud에서
해당 저장소의 app.py를 실행 파일로 선택합니다. GitHub Pages는 지원하지 않습니다.
기록은 사용자별 Streamlit 세션 메모리에만 보관합니다. 영구 저장/로그인/서버 알림은
없습니다. 새로고침, 연결 종료, 서버 재시작 전 JSON 백업을 내려받으세요.
진단·치료·의학적 감량 처방을 제공하지 않습니다.
"""
import copy
import json
import uuid
from datetime import datetime, date, time, timedelta, timezone

import pandas as pd
import streamlit as st

KST = timezone(timedelta(hours=9))

def now():
    return datetime.now(KST)

def empty_data():
    return {"schema_version": 1, "intakes": [], "sleep": [], "urges": [],
            "goal": {"limit": None, "cutoff": "15:00", "action": "카페인 없는 음료 준비하기"}}

def uid():
    return str(uuid.uuid4())

def validate_backup(raw):
    """허용 필드만 복원하고 모든 값을 검증합니다. 코드는 실행하지 않습니다."""
    if not isinstance(raw, dict) or type(raw.get("schema_version")) is not int or raw["schema_version"] != 1:
        raise ValueError("지원하지 않는 백업 형식입니다.")
    out = empty_data()
    def text(v, length=300):
        if not isinstance(v, str) or len(v) > length:
            raise ValueError("문자열 형식 또는 길이가 올바르지 않습니다.")
        return v
    def number(v, lo, hi):
        if type(v) not in (int, float) or not lo <= v <= hi:
            raise ValueError("숫자가 허용 범위를 벗어났습니다.")
        return float(v)
    for key in ("intakes", "sleep", "urges"):
        rows = raw.get(key)
        if not isinstance(rows, list) or len(rows) > 10000:
            raise ValueError("기록 목록 형식이 잘못되었거나 10,000건을 초과했습니다.")
        for r in rows:
            if not isinstance(r, dict):
                raise ValueError("기록 형식이 잘못되었습니다.")
            if key == "intakes":
                dt = datetime.fromisoformat(text(r["at"], 60))
                if dt.tzinfo is None:
                    raise ValueError("섭취 시간에 시간대가 없습니다.")
                row = {"id": uid(), "at": dt.astimezone(KST).isoformat(),
                       "name": text(r["name"], 100),
                       "mg": None if r["mg"] is None else number(r["mg"], 0, 10000),
                       "note": text(r.get("note", ""))}
            elif key == "sleep":
                row = {"id": uid(), "date": date.fromisoformat(text(r["date"], 10)).isoformat(),
                       "hours": number(r["hours"], 0, 24),
                       "difficulty": number(r["difficulty"], 0, 10),
                       "palpitations": r["palpitations"], "note": text(r.get("note", ""))}
                if type(row["palpitations"]) is not bool:
                    raise ValueError("증상 값이 올바르지 않습니다.")
                if any(x["date"] == row["date"] for x in out[key]):
                    raise ValueError("수면 기록에 중복 날짜가 있습니다.")
            else:
                dt = datetime.fromisoformat(text(r["at"], 60))
                if dt.tzinfo is None:
                    raise ValueError("충동 기록에 시간대가 없습니다.")
                row = {"id": uid(), "at": dt.astimezone(KST).isoformat(),
                       "reason": text(r["reason"], 100), "action": text(r["action"], 100),
                       "before": number(r["before"], 0, 10),
                       "after": number(r["after"], 0, 10)}
            out[key].append(row)
    g = raw.get("goal", {})
    if not isinstance(g, dict):
        raise ValueError("목표 형식이 잘못되었습니다.")
    cutoff = time.fromisoformat(text(g.get("cutoff", "15:00"), 8))
    if cutoff.tzinfo is not None:
        raise ValueError("목표 시간은 한국 현지 시각으로 입력하세요.")
    out["goal"] = {"limit": None if g.get("limit") is None else number(g["limit"], 0, 10000),
                   "cutoff": cutoff.strftime("%H:%M"),
                   "action": text(g.get("action", "카페인 없는 음료 준비하기"), 100)}
    return out

import html
import random
import math

st.set_page_config(page_title="카페인 브레이크",page_icon="🌱",layout="centered",initial_sidebar_state="collapsed")
CLOTHES={"basic":("기본 옷","#8ABBA0","🌱"),"sky":("하늘 셔츠","#91C9F2","☁️"),"peach":("복숭아 니트","#F7B6A1","🍑"),"night":("별빛 옷","#A69ADD","⭐"),"lemon":("레몬 옷","#EBD879","🍋")}
ROOMS={"plant":("🪴 화분",40,"🪴"),"lamp":("💡 조명",60,"💡"),"rug":("🧶 러그",80,"🧶"),"cat":("🐈 고양이 쿠션",100,"🐈")}
MISSIONS={"water":("💧 물 천천히 마시기",1,10,"쉬움"),"rest":("😌 눈 쉬며 휴식하기",3,20,"보통"),"tidy":("🧺 음료 치우고 책상 정리",5,30,"보통"),"walk":("🚶 편안하게 걷기",10,40,"도전")}

def game_default():
    return {"coins":0,"owned":["basic"],"outfit":"basic","room":[],"nickname":"새싹","font":"기본","active":None,"history":[],"last_draw":""}

if "cb_data" not in st.session_state: st.session_state.cb_data=empty_data()
if "game" not in st.session_state: st.session_state.game=game_default()
if "page" not in st.session_state: st.session_state.page="home"
if "logged_out" not in st.session_state: st.session_state.logged_out=False
data=st.session_state.cb_data
game=st.session_state.game

def esc(x): return html.escape(str(x))
def go(p): st.session_state.page=p

def backup():
    out=copy.deepcopy(data)
    out["game"]=copy.deepcopy(game)
    return json.dumps(out,ensure_ascii=False,indent=2)

def restore(raw):
    clean=validate_backup(raw)
    g=raw.get("game",game_default())
    if not isinstance(g,dict): raise ValueError("게임 데이터 오류")
    out=game_default()
    if type(g.get("coins",0)) is not int or not 0<=g.get("coins",0)<=10000000: raise ValueError("코인 오류")
    out["coins"]=g.get("coins",0)
    owned=g.get("owned",["basic"])
    room=g.get("room",[])
    if not isinstance(owned,list) or not owned or not all(isinstance(x,str) and x in CLOTHES for x in owned): raise ValueError("옷 데이터 오류")
    if not isinstance(room,list) or not all(isinstance(x,str) and x in ROOMS for x in room): raise ValueError("방 데이터 오류")
    out["owned"]=list(dict.fromkeys(["basic"]+owned));out["room"]=list(dict.fromkeys(room))
    outfit=g.get("outfit","basic")
    if outfit not in out["owned"]: raise ValueError("착용 데이터 오류")
    out["outfit"]=outfit
    nickname=g.get("nickname","새싹")
    if not isinstance(nickname,str) or len(nickname)>20: raise ValueError("닉네임 오류")
    out["nickname"]=nickname
    if g.get("font","기본") not in ["기본","크게","명조"]: raise ValueError("폰트 오류")
    out["font"]=g.get("font","기본")
    # 진행 중 미션은 복원하지 않아 중복 보상을 방지합니다.
    return clean,out

font="serif" if game["font"]=="명조" else "system-ui, sans-serif"
size=19 if game["font"]=="크게" else 16
st.markdown(f'''<style>
.stApp{{background:#F4F8F3;color:#254B3C;font-family:{font}}}
[data-testid="stSidebar"],[data-testid="stToolbar"]{{display:none}}
header[data-testid="stHeader"]{{height:0;background:transparent}}
.block-container{{max-width:480px;padding:1rem 1rem 8rem}}
h1{{font-size:1.65rem!important}}h2{{font-size:1.25rem!important}}h3{{font-size:1.1rem!important}}
p,label,input{{font-size:{size}px!important;font-family:{font}!important}}button{{border-radius:16px!important;min-height:48px!important}}
[data-testid="stForm"]{{border-radius:22px;background:white}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:14px 0}}
.stat{{background:white;border-radius:18px;padding:12px 4px;text-align:center;font-size:12px}}.stat b{{display:block;font-size:23px;margin:6px 0}}
.room{{position:relative;height:270px;background:linear-gradient(#DFEDE0 78%,#D0B999 78%);border:6px solid white;border-radius:28px;overflow:hidden;text-align:center}}
.character{{position:absolute;left:50%;bottom:23px;transform:translateX(-50%);width:145px;height:210px}}
.head{{position:absolute;left:25px;top:15px;background:#FFE2B9;width:96px;height:90px;border-radius:44%;box-shadow:inset 0 8px #77543F}}
.face{{font-size:27px;padding-top:28px}}.body{{position:absolute;top:100px;left:20px;width:106px;height:85px;border-radius:25px 25px 16px 16px;font-size:31px;padding-top:14px;box-sizing:border-box}}
.feet{{position:absolute;bottom:4px;width:100%;font-size:28px;letter-spacing:17px;padding-left:12px;box-sizing:border-box}}.deco{{position:absolute;bottom:19px;font-size:35px}}
.name{{text-align:center;margin:8px;color:#456451;font-size:14px}}
.st-key-craving button{{min-height:83px!important;background:#236B4A!important;color:white!important;border:0!important;box-shadow:0 8px 20px #236B4A25}}
.st-key-craving button p{{font-size:22px!important;font-weight:800!important}}
.st-key-bottom_nav{{position:fixed!important;bottom:0;left:50%;transform:translateX(-50%);width:min(100%,480px)!important;background:#FFFFFAF5;border-top:1px solid #DEE8DC;padding:8px 6px calc(8px + env(safe-area-inset-bottom));z-index:9999;box-sizing:border-box}}
.st-key-bottom_nav [data-testid="stHorizontalBlock"]{{display:flex!important;flex-wrap:nowrap!important;gap:2px!important}}
.st-key-bottom_nav [data-testid="stColumn"]{{min-width:0!important;width:0!important;flex:1 1 0!important}}
.st-key-bottom_nav button{{padding:8px 0!important;border:0!important}}
.st-key-bottom_nav button p{{font-size:11px!important;white-space:nowrap}}
.timer{{text-align:center;border-radius:25px;background:#E1EEDC;padding:25px;font-size:48px;font-weight:bold}}
</style>''',unsafe_allow_html=True)

if st.session_state.logged_out:
    st.title("🌱 카페인 브레이크")
    st.caption("이 기기의 앱 잠금 상태입니다. 실제 계정 인증은 아닙니다.")
    if st.button("🔓 다시 시작",type="primary",use_container_width=True):
        st.session_state.logged_out=False;st.rerun()
    st.stop()

st.caption(f"🌱 CAFFEINE BREAK　·　🪙 {game['coins']}")
today=now().date()
todays=[r for r in data["intakes"] if datetime.fromisoformat(r["at"]).astimezone(KST).date()==today]
known=sum(r["mg"] for r in todays if r["mg"] is not None)
unknown=sum(r["mg"] is None for r in todays)
page=st.session_state.page

if page=="home":
    st.title(f"{game['nickname']}의 작은 쉼 🌱")
    sleep=next((r for r in data["sleep"] if r["date"]==today.isoformat()),None)
    hours=f"{sleep['hours']:g}h" if sleep else "—"
    st.markdown(f'<div class="stats"><div class="stat">☕ 카페인<b>{known:g}</b>mg · 확인된 양</div><div class="stat">🌙 수면<b>{hours}</b>오늘 기상</div><div class="stat">🪙 코인<b>{game["coins"]}</b>미션 보상</div></div>',unsafe_allow_html=True)
    outfit=CLOTHES[game["outfit"]]
    decos="".join(f'<span class="deco" style="{"left" if i%2==0 else "right"}:{8+(i//2)*12}%">{ROOMS[k][2]}</span>' for i,k in enumerate(game["room"]))
    st.markdown(f'<div class="room">{decos}<div class="character"><div class="head"><div class="face">• ᴗ •</div></div><div class="body" style="background:{outfit[1]}">{outfit[2]}</div><div class="feet">👟👟</div></div></div><div class="name">{esc(outfit[0])} · {esc(game["nickname"])}</div>',unsafe_allow_html=True)
    with st.container(key="craving"):
        st.button("⏳ 지금 마시고 싶어요",on_click=go,args=("mission",),use_container_width=True)
    a,b=st.columns(2)
    a.button("➕ 음료·수면",on_click=go,args=("record",),use_container_width=True)
    b.button("🎁 옷·방 꾸미기",on_click=go,args=("shop",),use_container_width=True)
    st.caption(f"❔ 함량 미확인 {unknown}건 · 분량 선택값은 추정치예요")

elif page=="record":
    st.title("➕ 기록")
    mode=st.radio("종류",["🥤 음료","🌙 수면"],horizontal=True,label_visibility="collapsed")
    if mode=="🥤 음료":
        st.caption("캔·병 전체의 카페인 함량을 입력하세요. 100mL당 표기라면 전체 용량으로 먼저 환산하세요.")
        name=st.text_input("🥤 음료 이름",max_chars=100)
        mg=st.number_input("☕ 캔·병 전체 카페인 (mg)",0.0,10000.0,0.0,step=5.0)
        missing=st.checkbox("❔ 함량을 몰라요")
        portions={"반절 먹었어요":0.5,"반보다 작게 먹었어요":0.25,"다 먹었어요":1.0,"반 이상 먹었어요":0.75}
        portion=st.radio("얼마나 먹었나요?",list(portions),index=2)
        result=round(mg*portions[portion],2)
        st.info("❔ 함량 미확인" if missing else f"☕ {result:g} mg · 전체의 {portions[portion]*100:g}%로 계산")
        st.caption("‘반보다 작게’=25%, ‘반 이상’=75% 추정. 정확한 분량을 의미하지 않아요.")
        d=st.date_input("📅 날짜",today,max_value=today)
        t=st.time_input("🕒 한국 시간",now().time().replace(tzinfo=None,second=0,microsecond=0))
        if st.button("✓ 저장",type="primary",use_container_width=True):
            at=datetime.combine(d,t,tzinfo=KST)
            if not name.strip(): st.error("음료 이름을 입력하세요")
            elif at>now(): st.error("미래 시각은 저장할 수 없어요")
            else:
                data["intakes"].append({"id":uid(),"at":at.isoformat(),"name":name.strip(),"mg":None if missing else result,"note":f"전체 {mg:g}mg · {portion} · {portions[portion]*100:g}% 추정"});st.success("✓ 저장했어요")
    else:
        d=st.date_input("📅 기상일",today,max_value=today)
        hours=st.number_input("🌙 수면 시간",0.0,24.0,7.0,step=0.5)
        diff=st.slider("😴 잠들기 어려움",0,10,3)
        palps=st.checkbox("❤️ 두근거림이 있었어요")
        if st.button("✓ 수면 저장",type="primary",use_container_width=True):
            data["sleep"]=[r for r in data["sleep"] if r["date"]!=d.isoformat()]
            data["sleep"].append({"id":uid(),"date":d.isoformat(),"hours":hours,"difficulty":diff,"palpitations":palps,"note":""});st.success("✓ 저장했어요")

elif page=="mission":
    st.title("🌱 참기 미션")
    active=game["active"]
    if active is None:
        reason=st.radio("왜 마시고 싶나요?",["🥱 졸려요","📚 집중하고 싶어요","😋 맛이 좋아요","🔁 습관이에요","🌧 스트레스예요"])
        if st.button("▶ 참기 시작",type="primary",use_container_width=True):
            game["active"]={"stage":"choose","reason":reason,"id":uid()};st.rerun()
    elif active["stage"]=="choose":
        st.caption(f"{active['reason']} → 대신 해볼 미션을 골라요")
        symptoms=st.checkbox("현재 두근거림·흉통·숨참·어지럼이 있어요")
        if symptoms: st.warning("운동하지 마세요. 지속되는 두근거림·흉통·숨참·실신감은 119·응급실 도움을 받으세요.")
        order=["rest","water","tidy","walk"] if "졸려" in active["reason"] else ["water","tidy","rest","walk"]
        for k in order:
            title,minutes,coins,level=MISSIONS[k]
            with st.container(border=True):
                st.markdown(f"**{title}**")
                st.caption(f"{level} · {minutes}분 · 🪙 {coins}")
                if st.button("이 미션 하기",key="mission_"+k,disabled=(k=="walk" and symptoms),use_container_width=True):
                    active.update({"stage":"running","mission":k,"start":now().isoformat()});st.rerun()
        st.caption("걷기는 몸 상태가 괜찮을 때만 편안하게. 힘든 운동은 하지 않아요.")
        if st.button("취소"):
            game["active"]=None;st.rerun()
    else:
        key=active["mission"]
        title,minutes,reward,level=MISSIONS[key]
        st.subheader(title)
        st.caption(f"{level} · 🪙 {reward} · 힘들면 언제든 중단해요")
        @st.fragment(run_every="1s")
        def countdown():
            a=game["active"]
            remain=max(0,math.ceil((datetime.fromisoformat(a["start"])+timedelta(minutes=minutes)-now()).total_seconds()))
            st.markdown(f'<div class="timer">{remain//60:02d}:{remain%60:02d}</div>',unsafe_allow_html=True)
            if remain==0:
                done=st.checkbox("미션을 실제로 실천했어요")
                if st.button(f"🪙 {reward} 받기",disabled=not done,type="primary",use_container_width=True):
                    game["coins"]+=reward
                    game["history"].append({"id":a["id"],"mission":key,"at":now().isoformat(),"coins":reward})
                    data["urges"].append({"id":uid(),"at":a["start"],"reason":a["reason"],"action":title,"before":5,"after":5})
                    game["active"]=None;st.rerun()
        countdown()
        st.caption("앱이 연결된 동안 갱신 · 백그라운드 알림 없음")
        if st.button("✕ 중단 · 보상 없음",use_container_width=True):
            game["active"]=None;st.rerun()

elif page=="shop":
    st.title("🎁 나의 옷장 · 방")
    st.subheader(f"🪙 {game['coins']}")
    tab=st.radio("상점",["🎲 옷 뽑기","👕 옷장","🪴 방 꾸미기"],horizontal=True,label_visibility="collapsed")
    if tab=="🎲 옷 뽑기":
        st.caption("게임 코인만 사용 · 현금 결제 없음")
        st.info("1회 🪙 30 · 기본 옷 제외 4종 각 25% · 중복은 🪙 15 반환")
        if st.button("🎲 옷 뽑기 · 30",disabled=game["coins"]<30,type="primary",use_container_width=True):
            chosen=random.choice([k for k in CLOTHES if k!="basic"])
            game["coins"]-=30
            if chosen in game["owned"]:
                game["coins"]+=15;game["last_draw"]=f"{CLOTHES[chosen][0]} 중복! 15코인 반환"
            else:
                game["owned"].append(chosen);game["last_draw"]=f"{CLOTHES[chosen][0]} 획득!"
            st.rerun()
        if game["last_draw"]: st.success(game["last_draw"])
    elif tab=="👕 옷장":
        for k in game["owned"]:
            label=CLOTHES[k]
            if st.button(f"{label[2]} {label[0]} {'✓' if game['outfit']==k else '입기'}",key="wear_"+k,use_container_width=True):
                game["outfit"]=k;st.rerun()
    else:
        for k,(title,cost,emoji) in ROOMS.items():
            owned=k in game["room"]
            if st.button(f"{title} · {'배치 완료 ✓' if owned else str(cost)+' 코인'}",key="room_"+k,disabled=owned or game["coins"]<cost,use_container_width=True):
                game["coins"]-=cost;game["room"].append(k);st.rerun()

elif page=="goal":
    st.title("🎯 나의 목표")
    with st.form("goals"):
        action=st.text_input("🌱 실천할 행동",data["goal"]["action"],max_chars=100)
        enabled=st.checkbox("☕ 직접 정한 mg 목표",value=data["goal"]["limit"] is not None)
        limit=st.number_input("하루 목표 mg",0.0,10000.0,float(data["goal"]["limit"] or 0))
        cutoff=st.time_input("🕒 내가 정한 마감",time.fromisoformat(data["goal"]["cutoff"]))
        if st.form_submit_button("✓ 목표 저장",use_container_width=True):
            data["goal"]={"limit":limit if enabled else None,"cutoff":cutoff.strftime("%H:%M"),"action":action or "카페인 없는 음료 준비하기"};st.success("저장했어요")
    st.caption("목표는 안전 섭취량이 아닙니다. 증상이 있다면 감량 방법을 의료진과 상의하세요.")
    if data["intakes"]:
        st.subheader("📊 최근 기록")
        frame=pd.DataFrame(data["intakes"])
        frame["섭취일"]=frame["at"].map(lambda x:datetime.fromisoformat(x).astimezone(KST).date().isoformat())
        daily=frame.groupby("섭취일")["mg"].sum(min_count=1)
        st.line_chart(daily.rename("확인된 카페인(mg)"),height=180)
        st.caption("미확인은 0이 아니에요. 기록 없는 날은 무섭취로 판단하지 않아요.")

elif page=="settings":
    st.title("⚙️ 설정")
    with st.expander("👤 계정 관리"):
        st.caption("현재는 로그인 서버가 없는 게스트 모드예요. 실제 회원가입·기기 간 자동 동기화는 지원하지 않아요.")
        nick=st.text_input("닉네임",game["nickname"],max_chars=20)
        if st.button("✓ 닉네임 저장"):
            game["nickname"]=nick or "새싹";st.rerun()
        st.caption("로그아웃은 앱 화면 잠금일 뿐 보안 인증 기능이 아닙니다.")
        if st.button("🚪 로그아웃 · 화면 잠금"):
            st.session_state.logged_out=True;st.rerun()
    with st.expander("🔤 폰트 관리"):
        font_choice=st.radio("글자",["기본","크게","명조"],index=["기본","크게","명조"].index(game["font"]))
        if font_choice!=game["font"]:
            game["font"]=font_choice;st.rerun()
    with st.expander("💾 백업 · 복원"):
        st.warning("세션 종료·새로고침으로 기록·코인·옷이 사라질 수 있어요. 사용 후 백업하세요.")
        st.download_button("⬇ 기록·코인·옷 백업",backup(),file_name="caffeine-break.json",mime="application/json",use_container_width=True)
        f=st.file_uploader("⬆ JSON 복원",type=["json"])
        ok=st.checkbox("현재 데이터를 대체합니다")
        if st.button("복원",disabled=not(f and ok)):
            try:
                if f.size>5*1024*1024: raise ValueError("5MB 이하만 가능")
                clean,g=restore(json.loads(f.getvalue().decode("utf-8-sig")))
                st.session_state.cb_data=clean;st.session_state.game=g;st.rerun()
            except (ValueError,TypeError,KeyError,OverflowError) as e: st.error(f"복원 실패: {e}")
        st.caption("진행 중 미션은 복원하지 않아요. 백업은 공개 GitHub에 올리지 마세요. 코인은 현금 가치가 없으며 백업 조작 방지 서버는 없습니다.")
    with st.expander("🗂 기록 삭제"):
        key=st.selectbox("종류",["intakes","sleep","urges"])
        rows=data[key]
        if rows:
            opts={r["id"]:f"{r.get('at',r.get('date',''))[:16]} · {r.get('name',r.get('action','수면'))}" for r in rows}
            chosen=st.selectbox("항목",list(opts),format_func=lambda x:opts[x])
            check=st.checkbox("선택 기록 삭제 확인")
            if st.button("삭제",disabled=not check):
                data[key]=[r for r in rows if r["id"]!=chosen];st.rerun()
        all_ok=st.checkbox("모든 기록·코인·아이템 삭제 확인")
        if st.button("전체 초기화",disabled=not all_ok):
            st.session_state.cb_data=empty_data();st.session_state.game=game_default();st.rerun()
    with st.expander("ℹ️ 안전 · 사용 안내"):
        st.error("지속되는 두근거림 또는 가슴 통증·숨참·실신감 → 119·응급실. 이런 증상이 있을 때 운동하지 마세요.")
        st.caption("앱은 진단·치료용이 아닙니다. 반복되는 불면·두근거림은 보호자·의료진에게 상담하세요. 갑작스러운 카페인 중단은 두통·졸림을 유발할 수 있어요. 미션 보상은 건강 개선을 보장하지 않아요.")
        st.caption("세션 전용 저장 · 실명·학교·상세 병력은 입력하지 마세요. 로그아웃은 인증 기능이 아닙니다. 장기 계정·동기화에는 별도 서버가 필요합니다.")
        st.markdown("[카페인 정보](https://medlineplus.gov/caffeine.html) · [두근거림 안내](https://www.nhs.uk/symptoms/heart-palpitations/)")
        st.code("pip install -r requirements.txt\nstreamlit run app.py")

with st.container(key="bottom_nav"):
    for col,(p,label) in zip(st.columns(6,gap="small"),[("home","🏠 홈"),("record","➕ 기록"),("mission","⏳ 미션"),("shop","🎁 꾸미기"),("goal","🎯 목표"),("settings","⚙️ 설정")]):
        with col:
            st.button(label,key="nav_"+p,on_click=go,args=(p,),type="primary" if page==p else "secondary",use_container_width=True)
