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

st.set_page_config(page_title="카페인 브레이크", page_icon="🌿", layout="wide")
if "cb_data" not in st.session_state:
    st.session_state.cb_data = empty_data()
data = st.session_state.cb_data
st.title("🌿 카페인 브레이크")
st.caption("더 참으라는 앱이 아니라, 내 습관을 이해하고 다음 선택을 돕는 앱")
st.warning("의료 안내 · 두근거림이 가라앉지 않거나 가슴 통증·숨참·실신할 것 같은 느낌이 있으면 앱 기록보다 119·응급실 도움을 먼저 받으세요. 반복되는 두근거림이나 불면은 보호자·보건 선생님·의료진에게 상담하세요.")
with st.sidebar:
    st.header("내 기록, 내가 관리")
    st.info("기록은 현재 접속 세션에만 저장됩니다. 새로고침·연결 종료·재시작으로 사라질 수 있으니 사용 후 백업하세요. 서버 파일이나 공용 DB에는 저장하지 않습니다.")
    st.caption("시간 기준: 한국(KST). 이름·학교 등 신원 정보는 입력하지 마세요. 배포 운영자나 호스팅 서비스에 대한 절대적인 비밀 보장은 아니므로 민감한 상세 병력은 기록하지 마세요.")
    st.download_button("JSON 전체 백업", json.dumps(data, ensure_ascii=False, indent=2),
                       file_name=f"caffeine-break-{now().date()}.json", mime="application/json")
    uploaded = st.file_uploader("JSON 백업 복원", type=["json"])
    replace = st.checkbox("복원하면 현재 기록이 대체됨을 확인합니다")
    if st.button("백업 복원하기", disabled=not (uploaded and replace)):
        try:
            if uploaded.size > 5 * 1024 * 1024:
                raise ValueError("백업 파일은 5MB 이하여야 합니다.")
            restored = validate_backup(json.loads(uploaded.getvalue().decode("utf-8-sig")))
            st.session_state.cb_data = restored
            st.session_state.pop("pending_urge", None)
            st.rerun()
        except (ValueError, KeyError, TypeError, OverflowError) as e:
            st.error(f"복원하지 못했습니다. 올바른 앱 백업인지 확인하세요. ({e})")
    with st.expander("모든 기록 초기화"):
        confirmed = st.checkbox("백업 여부를 확인했으며 전체 삭제에 동의합니다")
        if st.button("전체 삭제", disabled=not confirmed):
            st.session_state.cb_data = empty_data()
            st.session_state.pop("pending_urge", None)
            st.rerun()

tabs = st.tabs(["🏠 오늘", "🥤 섭취 기록", "🌱 지금 마시고 싶어요", "🌙 수면·증상", "🎯 나의 목표", "🔎 탐구·기록 관리", "📖 사용 안내"])
today = now().date()
with tabs[0]:
    todays = [r for r in data["intakes"] if datetime.fromisoformat(r["at"]).astimezone(KST).date() == today]
    known = sum(r["mg"] for r in todays if r["mg"] is not None)
    unknown = sum(r["mg"] is None for r in todays)
    a, b, c = st.columns(3)
    a.metric("오늘 확인된 카페인", f"{known:g} mg")
    b.metric("함량 미확인", f"{unknown}건")
    c.metric("오늘 기록한 음료", f"{len(todays)}건")
    st.caption("미확인 함량은 0mg이 아닙니다. 확인된 합계는 실제 총섭취량과 다를 수 있습니다. 기록이 없는 날도 무섭취로 판단하지 않습니다.")
    if data["goal"]["limit"] is not None:
        limit = data["goal"]["limit"]
        st.write(f"직접 설정한 목표: {limit:g} mg 이하 · 의료적 안전 기준이 아닙니다.")
        if known > limit:
            st.info("목표를 넘겼어도 실패가 아니에요. 어떤 상황에서 마셨는지 살펴보고 다음 행동 하나를 골라 보세요.")
    st.subheader("오늘의 작은 행동")
    st.write(data["goal"]["action"])
    st.success("마시기 전에 잠시 멈추기, 기록하기, 카페인 없는 음료를 준비하기도 의미 있는 실천이에요.")

with tabs[1]:
    st.subheader("제품 라벨을 보고 기록하세요")
    st.caption("단위는 '기준량당 mg'입니다. 라벨의 총 내용량과 실제 마신 양을 구분하세요. 초콜릿·보충제 등 다른 카페인 공급원도 기록할 수 있습니다.")
    with st.form("intake", clear_on_submit=True):
        name = st.text_input("음료·식품 이름", max_chars=100)
        d = st.date_input("섭취 날짜", value=today, max_value=today)
        t = st.time_input("섭취 시간 (KST)", value=now().time().replace(tzinfo=None, second=0, microsecond=0))
        unknown_mg = st.checkbox("카페인 함량을 모릅니다")
        unit_mg = st.number_input("라벨 기준량에 든 카페인 (mg)", 0.0, 10000.0, 0.0, step=1.0)
        unit_ml = st.number_input("라벨 기준량 (mL 또는 g)", 1.0, 10000.0, 250.0, step=10.0)
        amount = st.number_input("실제로 섭취한 양 (동일 단위)", 1.0, 10000.0, 250.0, step=10.0)
        note = st.text_input("메모 (선택)", max_chars=300)
        save = st.form_submit_button("섭취 기록 저장")
    if save:
        at = datetime.combine(d, t, tzinfo=KST)
        mg = None if unknown_mg else round(unit_mg * amount / unit_ml, 2)
        if not name.strip():
            st.error("이름을 입력하세요.")
        elif at > now():
            st.error("미래 시각의 섭취는 기록할 수 없습니다.")
        elif mg is not None and mg > 10000:
            st.error("계산량이 너무 큽니다. 라벨 단위와 섭취량을 확인하세요.")
        else:
            data["intakes"].append({"id": uid(), "at": at.isoformat(), "name": name.strip(), "mg": mg, "note": note})
            st.rerun()
    if data["intakes"]:
        df = pd.DataFrame(data["intakes"]).sort_values("at", ascending=False)
        df["at"] = df["at"].map(lambda x: datetime.fromisoformat(x).strftime("%Y-%m-%d %H:%M"))
        st.dataframe(df.drop(columns="id").rename(columns={"at":"섭취 시각", "name":"제품", "mg":"카페인(mg, 빈칸=미확인)", "note":"메모"}), hide_index=True, use_container_width=True)

with tabs[2]:
    st.subheader("먼저 10분, 선택을 미뤄 볼까요?")
    st.caption("이 연습은 치료가 아닙니다. 흉통·숨참 등 위험 증상은 미루지 말고 의료 도움을 받으세요.")
    if "pending_urge" not in st.session_state:
        with st.form("urge_start"):
            reason = st.selectbox("지금 마시고 싶은 이유", ["졸려서", "공부에 집중하고 싶어서", "맛이 좋아서", "습관적으로", "스트레스를 받아서", "그 밖의 이유"])
            before = st.slider("지금 마시고 싶은 정도", 0, 10, 5)
            action = st.selectbox("10분 동안 시도할 행동", ["물 또는 카페인 없는 음료 마시기", "잠깐 쉬고 눈 쉬게 하기", "음료를 시야 밖으로 치우기", "친구·보호자에게 이야기하기"])
            start = st.form_submit_button("10분 미루기 시작")
        if start:
            st.session_state.pending_urge = {"at": now().isoformat(), "reason": reason, "before": before, "action": action}
            st.rerun()
    else:
        pending = st.session_state.pending_urge
        deadline = datetime.fromisoformat(pending["at"]) + timedelta(minutes=10)
        seconds = max(0, int((deadline - now()).total_seconds()))
        st.info(f"선택한 행동: {pending['action']} · 종료 예정: {deadline:%H:%M:%S} (KST)")
        st.write(f"마지막 확인 시 남은 시간: {seconds // 60}분 {seconds % 60}초")
        st.caption("백그라운드 알림이나 자동 알람은 없습니다. 다른 탭으로 이동해도 이 세션에서는 유지됩니다. 아래 버튼으로 시간을 확인하세요.")
        if st.button("남은 시간 새로 확인"):
            st.rerun()
        if seconds == 0:
            after = st.slider("지금 다시 평가한 정도", 0, 10, 5, key="after_urge")
            if st.button("시도 결과 저장"):
                data["urges"].append({"id": uid(), **copy.deepcopy(pending), "after": after})
                del st.session_state.pending_urge
                st.rerun()
        if st.button("이번 시도 취소 (저장 안 함)"):
            del st.session_state.pending_urge
            st.rerun()
    if data["urges"]:
        st.write(f"완료한 실천: {len(data['urges'])}회. 강도가 줄지 않았더라도 관찰하고 시도한 기록은 의미 있어요.")

with tabs[3]:
    st.subheader("기상한 날짜 기준으로 기록")
    st.caption("예: 11월 10일 밤부터 11일 아침까지 잤다면 11일에 기록합니다. 같은 기상일 기록은 수정됩니다.")
    with st.form("sleep"):
        sd = st.date_input("기상 날짜", value=today, max_value=today)
        hours = st.number_input("총 수면 시간", 0.0, 24.0, 7.0, step=0.5)
        difficulty = st.slider("잠들기 어려웠던 정도 (0=전혀 없음, 10=매우 심함)", 0, 10, 3)
        palps = st.checkbox("전날부터 기상할 때까지 두근거림을 느꼈습니다")
        snote = st.text_input("다른 영향 요인: 시험·스트레스·운동 등 (선택)", max_chars=300)
        ss = st.form_submit_button("수면·증상 저장 / 해당 날짜 수정")
    if ss:
        data["sleep"] = [r for r in data["sleep"] if r["date"] != sd.isoformat()]
        data["sleep"].append({"id": uid(), "date": sd.isoformat(), "hours": hours, "difficulty": difficulty, "palpitations": palps, "note": snote})
        st.rerun()
    if any(r["palpitations"] for r in data["sleep"]):
        st.warning("두근거림이 기록되어 있습니다. 반복되거나 수분 이상 지속되면 진료를 받으세요. 원인을 카페인으로 단정하지 마세요. 현재 지속되는 두근거림 또는 흉통·숨참·실신감은 즉시 의료 도움을 받으세요.")
    if data["sleep"]:
        st.dataframe(pd.DataFrame(data["sleep"]).drop(columns="id").sort_values("date", ascending=False).rename(columns={"date":"기상일", "hours":"수면시간", "difficulty":"입면 어려움(0~10)", "palpitations":"두근거림", "note":"메모"}), hide_index=True, use_container_width=True)

with tabs[4]:
    st.subheader("작고 현실적인 목표")
    st.info("앱은 개인별 감량량을 계산하거나 안전 섭취량을 처방하지 않습니다. 성인 기준을 학생의 안전선으로 적용하지 않습니다. 이미 불면·두근거림이 있다면 의료진과 상의하세요. 매일 섭취하던 카페인을 갑자기 끊으면 두통·졸림 등 금단 증상이 생길 수 있습니다.")
    with st.form("goals"):
        enabled = st.checkbox("직접 정한 섭취량 목표를 표시합니다", value=data["goal"]["limit"] is not None)
        limit = st.number_input("직접 설정한 하루 목표 (mg, 의학적 안전선 아님)", 0.0, 10000.0, float(data["goal"]["limit"] or 0), step=5.0)
        cutoff = st.time_input("내가 정한 섭취 마감 시각 (수면 안전을 보장하지 않음)", value=time.fromisoformat(data["goal"]["cutoff"]))
        action = st.text_input("실천할 행동 하나", value=data["goal"]["action"], max_chars=100)
        gs = st.form_submit_button("목표 저장")
    if gs:
        data["goal"] = {"limit": limit if enabled else None, "cutoff": cutoff.strftime("%H:%M"), "action": action.strip() or "카페인 없는 음료 준비하기"}
        st.rerun()
    cutoff_t = time.fromisoformat(data["goal"]["cutoff"])
    late = sum(datetime.fromisoformat(r["at"]).time().replace(tzinfo=None) >= cutoff_t for r in todays)
    st.write(f"오늘 내가 정한 마감 시각({cutoff_t:%H:%M}) 이후의 섭취 기록: {late}건")
    st.caption("이 수치는 개인 행동 목표 점검용이며, 그 이전 섭취가 안전하다는 의미는 아닙니다.")

with tabs[5]:
    st.subheader("기록을 탐구로 연결하기")
    days = st.selectbox("조회 기간", [7, 14, 30, 90], index=2)
    first = today - timedelta(days=days - 1)
    intake_rows = []
    for r in data["intakes"]:
        day = datetime.fromisoformat(r["at"]).astimezone(KST).date()
        if first <= day <= today:
            intake_rows.append({"date": day.isoformat(), "mg": r["mg"], "unknown": int(r["mg"] is None)})
    if intake_rows:
        idf = pd.DataFrame(intake_rows)
        daily = idf.groupby("date").agg(known_mg=("mg", lambda s: s.sum(min_count=1)), unknown=("unknown", "sum")).reset_index()
        st.write("기록한 날짜별 확인된 섭취량 (mg)")
        plot = daily.set_index("date")[["known_mg"]].copy()
        plot.index = pd.to_datetime(plot.index)
        plot = plot.reindex(pd.date_range(first, today))
        st.line_chart(plot.rename(columns={"known_mg":"확인된 카페인(mg)"}))
        st.caption("기록 없는 날과 함량을 전부 모르는 날은 결측치입니다. 선이 이어져 보여도 무섭취나 연속 관측을 뜻하지 않습니다. 일부 함량이 미확인이면 확인된 합계만 표시됩니다.")
        st.dataframe(daily.rename(columns={"date":"섭취일", "known_mg":"확인된 합계(mg)", "unknown":"미확인 건수"}), hide_index=True)
        # 전날 섭취와 다음 기상일을 연결하며 미확인 함량이 있는 날은 상관 계산에서 제외합니다.
        complete = daily[daily["unknown"] == 0].copy()
        complete["wake_date"] = (pd.to_datetime(complete["date"]) + pd.Timedelta(days=1)).dt.strftime("%Y-%m-%d")
        if data["sleep"]:
            sdf = pd.DataFrame(data["sleep"])
            pairs = complete.merge(sdf, left_on="wake_date", right_on="date", suffixes=("_intake", "_sleep"))
            st.write(f"전날 섭취 ↔ 다음 기상일 수면 비교 가능 자료: {len(pairs)}쌍")
            if len(pairs) >= 5 and pairs["known_mg"].nunique() > 1 and pairs["hours"].nunique() > 1:
                corr = pairs["known_mg"].corr(pairs["hours"])
                st.metric("기술적 피어슨 상관계수", f"{corr:.2f}")
            else:
                st.info("서로 다른 섭취량·수면시간을 포함한 5쌍 이상의 기록이 있어야 탐색용 상관계수를 표시합니다. 5쌍이 충분한 과학적 근거라는 뜻은 아닙니다.")
            if not pairs.empty:
                st.dataframe(pairs[["date_intake", "wake_date", "known_mg", "hours", "difficulty"]].rename(columns={"date_intake":"섭취일", "wake_date":"다음 기상일", "known_mg":"전날 확인된 카페인(mg)", "hours":"수면시간", "difficulty":"입면 어려움"}), hide_index=True)
    else:
        st.info("선택한 기간에 섭취 기록이 없습니다. 실제 사용 기록을 쌓으면 변화가 표시됩니다.")
    st.warning("상관관계는 원인·결과를 증명하지 않습니다. 누락된 음료, 스트레스, 생활 리듬, 자기보고 오차 등이 영향을 줍니다. 데이터 수집을 위해 일부러 카페인을 더 섭취하지 마세요.")
    st.markdown("**탐구 메모 예시**: 문제 발견 → 관련 자료 조사 → 기능 설계 → 자연스러운 사용 기록 → 불편한 점 수정 → 자료의 한계 검토. AI가 만든 코드의 계산 원리를 이해하고, AI 활용 범위와 본인의 수정 내용을 구분해 남겨 보세요.")
    st.divider()
    st.subheader("개별 기록 삭제 · CSV 내보내기")
    key = st.selectbox("관리할 기록", ["intakes", "sleep", "urges"], format_func=lambda k: {"intakes":"섭취", "sleep":"수면", "urges":"충동 미루기"}[k])
    records = data[key]
    if records:
        frame = pd.DataFrame(records)
        st.download_button("선택한 기록 CSV 다운로드", frame.to_csv(index=False).encode("utf-8-sig"), file_name=f"caffeine-{key}.csv", mime="text/csv")
        labels = {r["id"]: f"{r.get('at', r.get('date', ''))} · {r.get('name', r.get('reason', str(r.get('hours', '')) + '시간'))}" for r in records}
        selected = st.selectbox("삭제할 항목", list(labels), format_func=lambda x: labels[x])
        delete_ok = st.checkbox("선택한 항목의 삭제를 확인합니다")
        if st.button("선택 항목 삭제", disabled=not delete_ok):
            data[key] = [r for r in records if r["id"] != selected]
            st.rerun()
    else:
        st.caption("관리할 기록이 없습니다.")

with tabs[6]:
    st.markdown("""
### 시작하기
1. 제품 라벨을 확인해 섭취 기록을 입력하세요. 함량이 없으면 ‘미확인’을 선택하세요.
2. 마시고 싶을 때 10분 미루기 기능으로 다른 행동을 시도하세요.
3. 기상 후 수면 상태를 기록하고 자연스럽게 쌓인 자료만 비교하세요.
4. 종료하기 전에 사이드바에서 **JSON 전체 백업**을 내려받으세요.

### 저장과 개인정보
- 로그인·공용 저장소·외부 AI API를 사용하지 않습니다. 사용자별 세션에만 기록합니다.
- 기기를 바꾸거나 세션이 종료되면 JSON 백업을 업로드해 복원해야 합니다.
- 복원은 현재 기록을 대체합니다. 먼저 현재 기록을 백업하세요.
- CSV는 분석용이고, 앱 복원은 JSON만 지원합니다. 백업에는 건강 정보가 있으니 공개 GitHub에 올리지 마세요.
- 이 앱은 의료기기가 아니며 진단, 치료, 의학적 감량 계획, 체내 카페인 농도 예측을 제공하지 않습니다.

### GitHub와 실행
GitHub에 `app.py`와 `requirements.txt` 두 파일을 올리세요.
GitHub 자체나 GitHub Pages는 Python 웹앱을 실행하지 않습니다.
Streamlit Community Cloud에서 저장소를 연결하고 메인 파일을 `app.py`로 지정하면 됩니다.
로컬 실행은 아래 명령을 사용하세요.
```bash
pip install -r requirements.txt
streamlit run app.py
```
### 건강 정보 참고 자료
- [FDA: 카페인의 과다 섭취와 점진적인 줄이기](https://www.fda.gov/consumers/consumer-updates/spilling-beans-how-much-caffeine-too-much)
- [MedlinePlus: 카페인과 수면·심박수·의존](https://medlineplus.gov/caffeine.html)
- [NHS: 두근거림과 응급 진료가 필요한 증상](https://www.nhs.uk/symptoms/heart-palpitations/)

학생의 실제 건강 문제는 보호자·보건 선생님·의료진과 상의하세요.
""")

st.caption("카페인 브레이크 · 기록은 판단이 아니라 이해를 위한 도구입니다. 사용 후 JSON 백업을 잊지 마세요.")
