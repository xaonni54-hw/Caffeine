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

st.set_page_config(page_title="카페인 브레이크", page_icon="🌿", layout="centered", initial_sidebar_state="collapsed")
import html

def esc(value):
    return html.escape(str(value))

st.markdown('''<style>
:root{--ink:#173D36;--green:#166952;--mint:#EDF7F2;--muted:#536F65}
.stApp{background:#F6FAF8;color:var(--ink)}
header[data-testid="stHeader"]{background:transparent;height:0}
[data-testid="stSidebar"], [data-testid="stToolbar"]{display:none}
.block-container{max-width:480px;padding:1.2rem 1rem 8.5rem}
h1{font-size:1.7rem!important;letter-spacing:-.05em}h2{font-size:1.3rem!important}h3{font-size:1.1rem!important}
p,label{word-break:keep-all}button{min-height:48px!important;border-radius:16px!important}
[data-testid="stForm"]{border:0;background:white;border-radius:22px;padding:18px}
[data-testid="stMetric"]{background:#EDF7F2;border-radius:18px;padding:12px}
.hero{background:#DFEEE6;border-radius:28px;padding:24px;margin:12px 0 18px}
.hero .amount{font-size:54px;font-weight:800;line-height:1.3;letter-spacing:-3px}
.hero .unit{font-size:18px;letter-spacing:0;color:#355F51}
.eyebrow{font-size:13px;color:#44675B}.sub{font-size:13px;color:#536F65;margin-top:8px}
.mini-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px}
.mini{background:white;border:1px solid #DFEAE4;border-radius:20px;padding:16px}
.mini b{display:block;font-size:23px;margin:6px 0}.mini span{font-size:13px;color:#536F65}
.row{display:flex;align-items:center;gap:12px;padding:14px 0;border-bottom:1px solid #E2EBE6}
.row .ico{font-size:26px}.row .body{flex:1;min-width:0;overflow-wrap:anywhere}.row strong{font-size:15px}
.row small{display:block;color:#536F65;font-size:12px}.row .value{font-weight:750;white-space:nowrap}
.timer{text-align:center;background:#DFEEE6;border-radius:28px;padding:28px 10px;margin:12px 0}.timer b{font-size:58px;display:block;letter-spacing:-2px}
.st-key-bottom_nav{position:fixed!important;bottom:0;left:50%;transform:translateX(-50%);width:min(100%,480px)!important;background:#FFFFFFF5;backdrop-filter:blur(12px);border-top:1px solid #D8E7DF;padding:10px 10px calc(10px + env(safe-area-inset-bottom));z-index:9999;box-sizing:border-box}
.st-key-bottom_nav [data-testid="stHorizontalBlock"]{display:flex!important;flex-wrap:nowrap!important;gap:4px!important}
.st-key-bottom_nav [data-testid="stColumn"]{min-width:0!important;width:0!important;flex:1 1 0!important}
.st-key-bottom_nav button{padding:8px 1px!important;min-height:54px!important;border:none!important}
.st-key-bottom_nav button p{font-size:12px!important;white-space:nowrap!important}
[data-testid="stMain"]{overflow-x:hidden}
@media(max-width:480px){.block-container{padding-top:.8rem}.hero{padding:22px}.st-key-bottom_nav{border-radius:20px 20px 0 0}}
</style>''', unsafe_allow_html=True)
if "cb_data" not in st.session_state:
    st.session_state.cb_data = empty_data()
if "page" not in st.session_state:
    st.session_state.page = "home"
data = st.session_state.cb_data

def go(page):
    st.session_state.page = page

def jump(label, page, key, primary=False):
    st.button(label, key=key, on_click=go, args=(page,), type="primary" if primary else "secondary", use_container_width=True)

def drink_row(r):
    stamp = datetime.fromisoformat(r["at"]).astimezone(KST)
    mg = "? mg" if r["mg"] is None else f"{r['mg']:g} mg"
    st.markdown(f'<div class="row"><div class="ico">🥤</div><div class="body"><strong>{esc(r["name"])}</strong><small>{stamp:%m.%d · %H:%M}</small></div><div class="value">{mg}</div></div>', unsafe_allow_html=True)

page = st.session_state.page
today = now().date()
todays = [r for r in data["intakes"] if datetime.fromisoformat(r["at"]).astimezone(KST).date() == today]
known = sum(r["mg"] for r in todays if r["mg"] is not None)
unknown = sum(r["mg"] is None for r in todays)
st.markdown('<div class="eyebrow">🌿 CAFFEINE BREAK</div>', unsafe_allow_html=True)
with st.expander("❤️ 두근거림이 있나요?"):
    st.error("지속되는 두근거림 또는 가슴 통증·숨참·실신감 → 119·응급실")
    st.caption("반복되는 두근거림·불면은 보호자·의료진과 상담하세요. 이 앱은 진단·치료용이 아닙니다.")
st.caption("💾 세션 종료 시 기록이 사라질 수 있어요 · 설정에서 백업")

if page == "home":
    st.title("오늘은 가볍게 🌿")
    st.markdown(f'<div class="hero"><div class="eyebrow">☕ 오늘 확인된 카페인</div><div class="amount">{known:g}<span class="unit"> mg</span></div><div class="sub">🥤 {len(todays)}회 기록 · ❔ 함량 미확인 {unknown}회</div></div>', unsafe_allow_html=True)
    sleep = next((r for r in data["sleep"] if r["date"] == today.isoformat()), None)
    urges_today = sum(datetime.fromisoformat(r["at"]).astimezone(KST).date() == today for r in data["urges"])
    sleep_text = f"{sleep['hours']:g}시간" if sleep else "—"
    st.markdown(f'<div class="mini-grid"><div class="mini">🌙<b>{sleep_text}</b><span>오늘 수면</span></div><div class="mini">🌱<b>{urges_today}회</b><span>미루기 실천</span></div></div>', unsafe_allow_html=True)
    jump("➕ 마신 음료 기록", "record", "home_record", True)
    jump("⏳ 지금 마시고 싶어요", "pause", "home_pause")
    with st.container(border=True):
        st.markdown("**🎯 오늘의 작은 행동**")
        st.write(data["goal"]["action"])
        if data["goal"]["limit"] is not None:
            st.caption(f"직접 정한 목표 {data['goal']['limit']:g} mg · 안전 기준 아님")
            if known > data["goal"]["limit"]:
                st.caption("🌱 넘겨도 괜찮아요. 다음 선택부터 다시 시작해요.")
    st.subheader("🥤 최근 기록")
    if not data["intakes"]:
        st.caption("아직 비어 있어요. 첫 음료를 기록해 보세요.")
    for r in sorted(data["intakes"], key=lambda r:r["at"], reverse=True)[:3]:
        drink_row(r)
    with st.expander("❔ 숫자 읽는 법"):
        st.caption("미확인 함량은 0mg이 아닙니다. 확인된 합계는 실제 섭취량과 다를 수 있습니다. 기록 없는 날은 무섭취로 간주하지 않습니다.")

elif page == "record":
    st.title("➕ 오늘의 기록")
    mode = st.radio("기록 종류", ["🥤 음료", "🌙 수면"], horizontal=True, label_visibility="collapsed")
    if mode == "🥤 음료":
        with st.form("drink_mobile", clear_on_submit=True):
            name = st.text_input("🥤 음료 이름", placeholder="예: 아메리카노", max_chars=100)
            mg = st.number_input("☕ 실제 마신 양의 카페인 (mg)", 0.0, 10000.0, 0.0, step=5.0)
            unknown_mg = st.checkbox("❔ 함량을 몰라요")
            with st.expander("🧮 일부만 마셨나요?"):
                st.caption("전체 카페인 × 마신 비율을 위에 입력하세요.")
                st.info("예: 100mg 음료의 절반 → 50mg")
            d = st.date_input("📅 날짜", value=today, max_value=today)
            t = st.time_input("🕒 시간 · 한국", value=now().time().replace(tzinfo=None, second=0, microsecond=0))
            save = st.form_submit_button("✓ 음료 저장", use_container_width=True, type="primary")
        if save:
            at = datetime.combine(d,t,tzinfo=KST)
            if not name.strip():
                st.error("음료 이름을 입력하세요.")
            elif at > now():
                st.error("미래 시각은 기록할 수 없어요.")
            else:
                data["intakes"].append({"id":uid(), "at":at.isoformat(), "name":name.strip(), "mg":None if unknown_mg else mg, "note":""})
                st.rerun()
        if data["intakes"]:
            drink_row(data["intakes"][-1])
    else:
        with st.form("sleep_mobile"):
            sd = st.date_input("📅 기상한 날짜", value=today, max_value=today)
            hours = st.number_input("🌙 잔 시간", 0.0, 24.0, 7.0, step=0.5)
            difficulty = st.slider("😴 잠들기 어려움", 0, 10, 3, help="0 전혀 없음 · 10 매우 심함")
            palps = st.checkbox("❤️ 전날~기상까지 두근거림이 있었어요")
            ss = st.form_submit_button("✓ 수면 저장", use_container_width=True, type="primary")
        if ss:
            data["sleep"] = [r for r in data["sleep"] if r["date"] != sd.isoformat()]
            data["sleep"].append({"id":uid(),"date":sd.isoformat(),"hours":hours,"difficulty":difficulty,"palpitations":palps,"note":""})
            st.rerun()
        st.caption("같은 기상일을 저장하면 해당 날짜의 기록이 수정돼요.")
        if any(r["palpitations"] for r in data["sleep"]):
            st.warning("❤️ 두근거림 기록이 있어요. 반복되면 진료를 받아 보세요. 현재 지속되거나 흉통·숨참·실신감이 있으면 119·응급실.")

elif page == "pause":
    st.title("⏳ 잠깐, 10분만")
    st.caption("참기보다 다른 선택을 시도해요.")
    if "pending_urge" not in st.session_state:
        with st.form("pause_start"):
            reason = st.radio("왜 마시고 싶나요?", ["🥱 졸려요", "📚 집중하고 싶어요", "😋 맛이 좋아요", "🔁 습관이에요", "🌧 스트레스예요"])
            before = st.slider("마시고 싶은 정도", 0, 10, 5)
            action = st.selectbox("대신 해볼 행동", ["💧 카페인 없는 음료", "🌿 잠깐 쉬기", "🙈 음료 치워 두기", "💬 누군가와 이야기"])
            start = st.form_submit_button("▶ 10분 시작", use_container_width=True, type="primary")
        if start:
            st.session_state.pending_urge = {"at":now().isoformat(),"reason":reason,"before":before,"action":action}
            st.rerun()
    else:
        pending = st.session_state.pending_urge
        @st.fragment(run_every="1s")
        def timer():
            deadline = datetime.fromisoformat(st.session_state.pending_urge["at"]) + timedelta(minutes=10)
            import math
            seconds = max(0, math.ceil((deadline-now()).total_seconds()))
            st.markdown(f'<div class="timer">🌿<b>{seconds//60:02d}:{seconds%60:02d}</b><span>{esc(st.session_state.pending_urge["action"])}</span></div>', unsafe_allow_html=True)
            if seconds == 0:
                after = st.slider("지금 마시고 싶은 정도", 0, 10, 5, key="urge_after_mobile")
                if st.button("✓ 실천 저장", type="primary", use_container_width=True):
                    data["urges"].append({"id":uid(),**copy.deepcopy(st.session_state.pending_urge),"after":after})
                    del st.session_state.pending_urge
                    st.rerun()
        timer()
        st.caption("화면이 연결된 동안 갱신돼요 · 백그라운드 알람 없음")
        if st.button("✕ 이번 시도 취소", use_container_width=True):
            del st.session_state.pending_urge
            st.rerun()
    if data["urges"]:
        st.success(f"🌱 지금까지 {len(data['urges'])}번 실천했어요")

elif page == "stats":
    st.title("📊 나의 변화")
    days = st.radio("기간", [7,14,30], horizontal=True, format_func=lambda x:f"{x}일", label_visibility="collapsed")
    first = today-timedelta(days=days-1)
    rows=[]
    for r in data["intakes"]:
        day=datetime.fromisoformat(r["at"]).astimezone(KST).date()
        if first<=day<=today:
            rows.append({"date":day.isoformat(),"mg":r["mg"],"unknown":int(r["mg"] is None)})
    if rows:
        frame=pd.DataFrame(rows)
        daily=frame.groupby("date").agg(mg=("mg",lambda s:s.sum(min_count=1)),unknown=("unknown","sum")).reset_index()
        st.subheader("☕ 확인된 카페인 · mg")
        plot=daily.set_index("date")[["mg"]]
        plot.index=pd.to_datetime(plot.index)
        plot=plot.reindex(pd.date_range(first,today))
        st.line_chart(plot.rename(columns={"mg":"카페인(mg)"}),height=220)
        with st.expander("❔ 그래프 읽는 법"):
            st.caption("빈 날은 미기록 또는 전부 미확인인 날입니다. 일부 함량을 모르면 실제 총량보다 작을 수 있어요. 선이 연결되어도 연속 관측을 뜻하지 않습니다.")
        if data["sleep"]:
            complete=daily[daily["unknown"]==0].copy()
            complete["wake_date"]=(pd.to_datetime(complete["date"])+pd.Timedelta(days=1)).dt.strftime("%Y-%m-%d")
            pairs=complete.merge(pd.DataFrame(data["sleep"]),left_on="wake_date",right_on="date",suffixes=("_intake","_sleep"))
            with st.expander("🔬 전날 섭취 ↔ 다음 날 수면"):
                st.caption(f"비교 가능한 기록 {len(pairs)}쌍 · 함량 미확인 날 제외")
                if len(pairs)>=5 and pairs["mg"].nunique()>1 and pairs["hours"].nunique()>1:
                    st.metric("탐색용 상관계수",f"{pairs['mg'].corr(pairs['hours']):.2f}")
                else:
                    st.caption("다양한 섭취량·수면시간을 포함한 5쌍 이상에서 표시해요. 5쌍이 충분한 근거라는 뜻은 아니에요.")
                st.caption("상관 ≠ 원인. 누락·스트레스·생활 리듬의 영향이 있어요. 탐구를 위해 더 마시지 마세요.")
    else:
        st.info("☕ 음료를 기록하면 변화가 보여요")
    sleeps=sorted([r for r in data["sleep"] if first.isoformat()<=r["date"]<=today.isoformat()],key=lambda r:r["date"])
    if sleeps:
        st.subheader("🌙 수면 시간")
        sdf=pd.DataFrame(sleeps).set_index("date")[["hours"]]
        sdf.index=pd.to_datetime(sdf.index)
        st.line_chart(sdf.reindex(pd.date_range(first,today)).rename(columns={"hours":"수면(시간)"}),height=200)
    st.caption(f"🌱 전체 미루기 실천 {len(data['urges'])}회")

elif page == "settings":
    st.title("⚙️ 나의 설정")
    with st.expander("🎯 목표", expanded=True):
        with st.form("goal_mobile"):
            action=st.text_input("🌱 작은 행동 하나",value=data["goal"]["action"],max_chars=100)
            enabled=st.checkbox("☕ 직접 정한 mg 목표 사용",value=data["goal"]["limit"] is not None)
            limit=st.number_input("하루 목표 (mg)",0.0,10000.0,float(data["goal"]["limit"] or 0),step=5.0)
            cutoff=st.time_input("🕒 내가 정한 마감 시간",value=time.fromisoformat(data["goal"]["cutoff"]))
            st.caption("의학적 안전선이 아닙니다. 불면·두근거림이 있다면 감량 방법을 의료진과 상의하세요.")
            gs=st.form_submit_button("✓ 목표 저장",use_container_width=True)
        if gs:
            data["goal"]={"limit":limit if enabled else None,"cutoff":cutoff.strftime("%H:%M"),"action":action.strip() or "카페인 없는 음료 준비하기"}
            st.rerun()
        late=sum(datetime.fromisoformat(r["at"]).time().replace(tzinfo=None)>=time.fromisoformat(data["goal"]["cutoff"]) for r in todays)
        st.caption(f"오늘 마감 시간 이후 기록 {late}회 · 이전 섭취의 안전을 보장하지 않아요")
    with st.expander("💾 백업 · 복원"):
        st.caption("세션 종료·새로고침으로 기록이 사라질 수 있어요. 백업은 공개 저장소에 올리지 마세요.")
        st.download_button("⬇ 전체 백업",json.dumps(data,ensure_ascii=False,indent=2),file_name=f"caffeine-break-{today}.json",mime="application/json",use_container_width=True)
        uploaded=st.file_uploader("⬆ JSON 복원",type=["json"])
        confirm=st.checkbox("현재 기록을 대체합니다")
        if st.button("복원",disabled=not(uploaded and confirm),use_container_width=True):
            try:
                if uploaded.size>5*1024*1024:
                    raise ValueError("5MB 이하 파일만 지원합니다")
                restored=validate_backup(json.loads(uploaded.getvalue().decode("utf-8-sig")))
                st.session_state.cb_data=restored
                st.session_state.pop("pending_urge",None)
                st.rerun()
            except (ValueError,KeyError,TypeError,OverflowError) as e:
                st.error(f"복원 실패: {e}")
    with st.expander("🗂 기록 관리"):
        key=st.selectbox("종류",["intakes","sleep","urges"],format_func=lambda k:{"intakes":"🥤 음료","sleep":"🌙 수면","urges":"🌱 미루기"}[k])
        records=data[key]
        if records:
            st.download_button("⬇ CSV",pd.DataFrame(records).to_csv(index=False).encode("utf-8-sig"),file_name=f"caffeine-{key}.csv",mime="text/csv")
            labels={r["id"]:f"{r.get('at',r.get('date',''))[:16]} · {r.get('name',r.get('reason',str(r.get('hours',''))+'시간'))}" for r in records}
            selected=st.selectbox("항목",list(labels),format_func=lambda x:labels[x])
            ok=st.checkbox("이 항목을 삭제합니다")
            if st.button("🗑 선택 삭제",disabled=not ok):
                data[key]=[r for r in records if r["id"]!=selected]
                st.rerun()
        else:
            st.caption("기록이 없어요")
        clear=st.checkbox("모든 기록을 삭제합니다")
        if st.button("🗑 전체 초기화",disabled=not clear):
            st.session_state.cb_data=empty_data()
            st.session_state.pop("pending_urge",None)
            st.rerun()
    with st.expander("ℹ️ 안내 · 건강 정보"):
        st.markdown("""- 🥤 라벨의 **실제 마신 양 기준 mg**을 기록해요.
- 🌙 **기상한 날짜**에 수면을 기록해요.
- 💾 세션 저장만 지원해요. JSON 백업으로 기기 간 옮겨요.
- 🔒 이름·학교·상세 병력은 입력하지 마세요. 호스팅의 절대적 비밀 보장은 아니에요.
- 🩺 진단·치료·안전 섭취량 처방을 하지 않아요. 성인 기준을 학생에게 적용하지 않아요.
- 🌱 갑작스러운 중단은 두통·졸림 등 금단 증상을 일으킬 수 있어요. 증상이 있다면 의료진과 감량 방법을 상의하세요.

[카페인 · FDA](https://www.fda.gov/consumers/consumer-updates/spilling-beans-how-much-caffeine-too-much) · [MedlinePlus](https://medlineplus.gov/caffeine.html) · [두근거림 · NHS](https://www.nhs.uk/symptoms/heart-palpitations/)
""")
        st.code("pip install -r requirements.txt\nstreamlit run app.py",language="bash")
        st.caption("GitHub에 두 파일 업로드 → Streamlit Community Cloud 연결 → app.py 배포. GitHub Pages에서는 실행되지 않아요.")

with st.container(key="bottom_nav"):
    cols=st.columns(5,gap="small")
    for col,(target,label) in zip(cols,[("home","🏠 홈"),("record","➕ 기록"),("pause","⏳ 쉬기"),("stats","📊 변화"),("settings","⚙️ 설정")]):
        with col:
            jump(label,target,f"nav_{target}",page==target)
