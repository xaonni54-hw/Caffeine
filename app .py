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

import html, random, math
st.set_page_config(page_title='카페인 브레이크',page_icon='🌱',layout='centered')
st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=Gaegu:wght@400;700&display=swap');
.stApp{background:#f6efda;color:#5b5243} .stApp,button,input,label,p,h1,h2,h3,span{font-family:'Gaegu',cursive!important}header{visibility:hidden}.block-container{max-width:470px;padding:1rem 1rem 7rem}h1{font-size:30px!important}h2{font-size:25px!important}p,label,button,input{font-size:21px!important}button{border:2px solid #c7b58a!important;border-radius:18px!important;background:#fffbed!important;color:#60543e!important;min-height:52px;box-shadow:0 3px 0 #d9c69b!important}button[kind='primary']{background:#bdd29b!important}input{background:#fffdf3!important;border-radius:12px!important}.scene{height:340px;border:3px solid #aa9b77;border-radius:35px 29px 32px 25px;background:radial-gradient(ellipse at 25% 20%,#f6edc8,transparent 50%),linear-gradient(#dfe8bd 77%,#d2c29b 77%);position:relative;overflow:hidden;box-shadow:inset 0 0 50px #ede7c9}.scene:before{content:'✧　　☁　　✧';position:absolute;top:20px;left:20px;color:#9aa77a;font-size:35px}.scene svg{width:225px;height:300px;position:absolute;bottom:9px;left:50%;transform:translateX(-50%)}.deco{position:absolute;bottom:22px;font-size:42px}.stats{display:flex;gap:8px;margin:10px 0}.stat{flex:1;background:#fff9e9;border:2px solid #d7c69e;border-radius:18px;text-align:center;padding:8px;font-size:18px}.stat b{display:block;font-size:27px}.st-key-craving button{width:100%;min-height:76px;font-size:26px!important;background:#b8ce95!important}.st-key-nav{position:fixed;bottom:0;left:50%;transform:translateX(-50%);width:min(100%,470px);background:#f6eed9;padding:10px 8px 18px;z-index:50;border-top:2px solid #d2c49f;border-radius:22px 22px 0 0}.st-key-nav button{font-size:17px!important;padding:2px!important;min-height:50px;box-shadow:none!important}.st-key-nav [data-testid='stHorizontalBlock']{gap:5px;flex-wrap:nowrap}.st-key-nav [data-testid='stColumn']{min-width:0!important;width:16%!important;flex:1!important}.box{font-size:95px;text-align:center;padding:25px;background:#f1dfb1;border:3px dashed #c3a778;border-radius:28px}.shake{animation:shake .3s infinite alternate}@keyframes shake{from{transform:rotate(-9deg) scale(.95)}to{transform:rotate(9deg) scale(1.08)}}.reveal{animation:pop .65s ease-out;text-align:center;background:#fff9e7;padding:25px;border-radius:28px}@keyframes pop{from{transform:scale(.2);opacity:0}to{transform:scale(1);opacity:1}}[data-testid='stDialog'] [role='dialog']{position:fixed!important;top:auto!important;bottom:0!important;left:50%!important;transform:translateX(-50%)!important;width:min(100%,470px)!important;margin:0!important;border-radius:28px 28px 0 0!important;background:#fff8e6!important;max-height:80dvh;overflow:auto}@media(prefers-reduced-motion:reduce){*{animation:none!important}}
</style>''',unsafe_allow_html=True)
COLORS=['#acc9c0','#ddbdc8','#d6cc97','#b7c4de','#c3b2d0']
CATS={'top':'상의','bottom':'하의','suit':'한벌','hat':'모자','face':'얼굴 소품'}
NAMES={'top':['민트 셔츠','딸기 니트','레몬 조끼','하늘 셔츠','라벤더 후드'],'bottom':['민트 반바지','딸기 치마','레몬 바지','하늘 바지','라벤더 치마'],'suit':['숲속 원피스','봄날 원피스','햇살 멜빵','별빛 잠옷','꽃잎 원피스'],'hat':['민트 베레모','딸기 리본','밀짚 모자','하늘 모자','라벤더 리본'],'face':['동그란 안경','하트 안경','별 스티커','볼 꽃잎','작은 반창고']}
ITEMS={f'{cat}_{i}':{'cat':cat,'name':name,'color':COLORS[i]} for cat,names in NAMES.items() for i,name in enumerate(names)}
if 'cb_data' not in st.session_state:st.session_state.cb_data=empty_data()
if 'dress_v3' not in st.session_state:st.session_state.dress_v3={'coins':100,'owned':[],'equipped':{},'room':[],'nickname':'새싹','active':None,'last':None}
if 'page' not in st.session_state:st.session_state.page='home'
g=st.session_state.dress_v3;d=st.session_state.cb_data

def go(page):st.session_state.page=page

def avatar():
    eq=g['equipped']
    def color(cat):return ITEMS.get(eq.get(cat),{}).get('color','#fffdf5')
    suit=bool(eq.get('suit'));top=color('suit') if suit else color('top');bottom=color('suit') if suit else color('bottom')
    hat=''
    if eq.get('hat'):hat=f'<path d="M64 67 Q70 12 113 28 Q156 15 168 66 Z" fill="{color("hat")}"/><path d="M65 62 Q110 80 168 62" fill="none"/>'
    face=''
    if eq.get('face'):face=f'<g fill="none" stroke="{color("face")}" stroke-width="3"><circle cx="92" cy="110" r="13"/><circle cx="137" cy="110" r="13"/><path d="M105 108 L124 108"/></g>'
    return f'''<svg viewBox="0 0 230 300" xmlns="http://www.w3.org/2000/svg"><defs><filter id="pencil"><feTurbulence type="fractalNoise" baseFrequency=".065" numOctaves="2" result="noise"/><feDisplacementMap in="SourceGraphic" in2="noise" scale=".7"/></filter></defs><ellipse cx="116" cy="278" rx="57" ry="9" fill="#8a8068" opacity=".14"/><g stroke="#776354" stroke-width="1.8" stroke-linejoin="round" filter="url(#pencil)"><path d="M61 112 Q43 184 55 237 Q77 254 97 231 L154 234 Q184 196 171 98" fill="#ead6bc"/><path d="M93 236 L93 271 L108 271 L112 237 M128 237 L131 270 L145 270 L144 235" fill="#f8e3cd"/><path d="M88 270 Q100 265 111 272 L111 280 L87 280 Z M128 272 Q139 266 150 273 L151 280 L129 280 Z" fill="#8b7565"/><path d="M78 204 L151 204 L153 242 L121 245 L116 228 L111 245 L78 241 Z" fill="{bottom}"/><path d="M85 157 L64 178 L75 188 L84 181 L80 215 Q113 226 153 215 L147 181 L157 188 L167 177 L145 157 Z" fill="{top}"/><path d="M67 181 L60 200 Q62 208 68 203 L78 187 M155 186 L166 203 Q173 205 172 198 L165 180" fill="#f8e3cd"/><ellipse cx="115" cy="104" rx="55" ry="55" fill="#fbe8d3"/><path d="M59 112 Q43 40 105 35 Q163 28 174 100 L161 128 L155 75 L144 92 L135 64 L126 87 L115 62 L103 86 L91 64 L78 98 L70 133 Z" fill="#e9d5ba"/><path d="M76 65 L68 109 M96 53 L87 87 M122 48 L127 79 M147 55 L159 94" fill="none" opacity=".6"/><path d="M90 106 L90 116 M137 106 L137 116" stroke-width="4"/><ellipse cx="78" cy="124" rx="9" ry="5" fill="#efb6a1" stroke="none"/><ellipse cx="149" cy="124" rx="9" ry="5" fill="#efb6a1" stroke="none"/><path d="M110 130 Q115 134 120 130" fill="none"/>{hat}{face}</g></svg>'''
def scene():
    decorations=''.join(f'<div class="deco" style="left:{5+i*22}%">{x}</div>' for i,x in enumerate(g['room']))
    st.markdown('<div class="scene">'+decorations+avatar()+'</div>',unsafe_allow_html=True)
def choose_commit(key,value):st.session_state[key]=value
@st.dialog('선택')
def sheet(key,options):
    for text,value in options:
        if st.button(text,key=f'sel_{key}_{value}',on_click=choose_commit,args=(key,value),use_container_width=True):st.rerun()
def choose(label,key,options,default=0):
    if key not in st.session_state:st.session_state[key]=options[default][1]
    value=st.session_state[key];text=next((t for t,v in options if v==value),options[default][0])
    if st.button(f'{label}　{text} ⌄',key=key+'_open',use_container_width=True):sheet(key,options)
    return value
@st.dialog('시각')
def clock(key):
    current=st.session_state.get(key,time(23,0))
    st.markdown('## ◷')
    c1,c2=st.columns(2)
    h=c1.selectbox('시',range(24),index=current.hour,key=key+'_hour')
    m=c2.selectbox('분',range(60),index=current.minute,key=key+'_minute')
    if st.button('✓',use_container_width=True,on_click=choose_commit,args=(key,time(h,m))):st.rerun()
def pick_time(label,key,default):
    if key not in st.session_state:st.session_state[key]=default
    if st.button(f'◷ {label}　{st.session_state[key].strftime("%H:%M")}',key=key+'_open',use_container_width=True):clock(key)
    return st.session_state[key]

def equip(item):
    cat=ITEMS[item]['cat'];g['equipped'][cat]=item
    if cat=='suit':g['equipped'].pop('top',None);g['equipped'].pop('bottom',None)
    elif cat in ['top','bottom']:g['equipped'].pop('suit',None)

def saved():st.toast('✓ 저장했어요')

page=st.session_state.page
st.markdown(f'### 🌱 {html.escape(g["nickname"])}　　🪙 {g["coins"]}')
if page=='home':
    today=now().date();total=sum(r['mg'] or 0 for r in d['intakes'] if datetime.fromisoformat(r['at']).date()==today)
    sleep=next((r['hours'] for r in d['sleep'] if r['date']==str(today)),None)
    st.markdown(f'<div class="stats"><div class="stat">☕<b>{total:g} mg</b></div><div class="stat">🌙<b>{sleep if sleep is not None else "—"} h</b></div></div>',unsafe_allow_html=True)
    scene()
    with st.container(key='craving'):st.button('지금 마시고 싶어요',on_click=go,args=('mission',),use_container_width=True)
elif page=='record':
    st.button('🥤 음료',on_click=go,args=('drink',),use_container_width=True)
    st.button('🌙 수면',on_click=go,args=('sleep',),use_container_width=True)
elif page=='drink':
    st.button('‹',on_click=go,args=('record',))
    name=st.text_input('🥤 음료 이름',max_chars=100)
    mg=st.number_input('☕ 캔 전체 카페인 (mg)',0.,10000.,step=5.)
    fraction=choose('얼마나 마셨나요?','fraction',[('반보다 적게',.25),('반절',.5),('반 이상',.75),('전부',1.)],3)
    dt=st.date_input('📅 날짜',value=now().date(),max_value=now().date())
    tm=pick_time('마신 시각','drink_time',now().time().replace(second=0,microsecond=0,tzinfo=None))
    st.markdown(f'## {mg*fraction:g} mg')
    with st.expander('ⓘ'):st.write('반보다 적게는 25%, 반 이상은 75%로 추정해요.')
    if st.button('✓ 저장',type='primary',use_container_width=True):
        if not name.strip():st.error('음료 이름을 입력해 주세요.')
        elif datetime.combine(dt,tm,tzinfo=KST)>now():st.error('미래 시각은 기록할 수 없어요.')
        else:d['intakes'].append({'id':uid(),'name':name.strip(),'at':datetime.combine(dt,tm,tzinfo=KST).isoformat(),'mg':mg*fraction,'note':''});saved()
elif page=='sleep':
    st.button('‹',on_click=go,args=('record',))
    wake_date=st.date_input('📅 일어난 날짜',max_value=now().date(),value=now().date())
    bed_date=st.date_input('📅 잠든 날짜',value=wake_date-timedelta(days=1),max_value=wake_date)
    start=pick_time('잠든 시각','bed_time',time(23))
    end=pick_time('일어난 시각','wake_time',time(7))
    hours=(datetime.combine(wake_date,end)-datetime.combine(bed_date,start)).total_seconds()/3600
    st.markdown(f'## 🌙 {max(0,hours):.1f} h')
    if st.button('✓ 저장',type='primary',use_container_width=True):
        if not 0<hours<=24:st.error('잠든 날짜와 시각을 확인해 주세요. (24시간 이내)')
        elif datetime.combine(wake_date,end,tzinfo=KST)>now():st.error('미래 시각은 기록할 수 없어요.')
        else:
            d['sleep']=[r for r in d['sleep'] if r['date']!=str(wake_date)]
            d['sleep'].append({'id':uid(),'date':str(wake_date),'hours':hours,'difficulty':0,'palpitations':False,'note':''});saved()
elif page=='mission':
    active=g['active']
    if not active:
        reasons=['🥱 졸려요','📚 집중하고 싶어요','🍹 맛이 좋아요','🔁 습관이에요','☁ 스트레스 받아요','💭 그냥 생각나요']
        for i in range(0,len(reasons),2):
            cols=st.columns(2)
            for j,reason in enumerate(reasons[i:i+2]):
                if cols[j].button(reason,type='primary' if st.session_state.get('reason')==reason else 'secondary',use_container_width=True):st.session_state.reason=reason;st.rerun()
        if st.button('참기 시작',type='primary',use_container_width=True):
            if st.session_state.get('reason'):st.session_state.mission_pick=True
        if st.session_state.get('mission_pick'):
            missions=[('💧 물 천천히 마시기',1,10),('🌿 창밖 보며 쉬기',3,20),('🧺 책상 정리하기',5,30),('🎨 작은 그림 그리기',10,40)]
            for title,minutes,coins in missions:
                if st.button(f'{title}　{minutes}분　🪙{coins}',use_container_width=True):g['active']={'title':title,'end':(now()+timedelta(minutes=minutes)).isoformat(),'coins':coins,'reason':st.session_state.reason};st.rerun()
    else:
        st.markdown('## '+active['title'])
        remaining=max(0,math.ceil((datetime.fromisoformat(active['end'])-now()).total_seconds()))
        st.markdown(f'# ⏳ {remaining//60:02}:{remaining%60:02}')
        st.button('↻',use_container_width=True)
        if st.button('✓ 완료',disabled=remaining>0,type='primary',use_container_width=True):
            g['coins']+=active['coins'];d['urges'].append({'id':uid(),'at':now().isoformat(),'reason':active['reason'],'action':active['title'],'before':0,'after':0});g['active']=None;st.session_state.mission_pick=False;st.rerun()
        if st.button('그만하기',use_container_width=True):g['active']=None;st.rerun()
elif page=='shop':
    scene()
    a,b=st.columns(2)
    if a.button('👕 옷장',use_container_width=True):st.session_state.shop_tab='closet'
    if b.button('🪴 방 꾸미기',use_container_width=True):st.session_state.shop_tab='room'
    if st.session_state.get('shop_tab')=='closet':
        cat=choose('옷장','closet_cat',[(v,k) for k,v in CATS.items()])
        if st.button('흰 기본 옷',use_container_width=True):g['equipped']={};st.rerun()
        for item in g['owned']:
            if ITEMS[item]['cat']==cat and st.button(ITEMS[item]['name'],key='wear_'+item,use_container_width=True):equip(item);st.rerun()
    elif st.session_state.get('shop_tab')=='room':
        for emoji,cost in [('🪴',40),('🧸',60),('💡',80),('🌷',50)]:
            owned=emoji in g['room']
            if st.button(f'{emoji}　'+('✓' if owned else f'🪙 {cost}'),key='room_'+emoji,disabled=owned or g['coins']<cost,use_container_width=True):g['coins']-=cost;g['room'].append(emoji);st.rerun()
    st.markdown('<div class="box">🎁</div>',unsafe_allow_html=True)
    if st.button('옷 뽑기　🪙 30',disabled=g['coins']<30,use_container_width=True,type='primary'):
        import time as delay
        anim=st.empty();anim.markdown('<div class="box shake">🎁</div>',unsafe_allow_html=True);delay.sleep(1.2)
        item=random.choice(list(ITEMS));g['coins']-=30;duplicate=item in g['owned']
        if duplicate:g['coins']+=15
        else:g['owned'].append(item)
        g['last']={'id':item,'duplicate':duplicate};anim.empty();st.rerun()
    if g['last']:
        last=g['last'];item=last['id'];obj=ITEMS[item];icon={'top':'👕','bottom':'🩳','suit':'👗','hat':'👒','face':'👓'}[obj['cat']]
        st.markdown(f'<div class="reveal"><div style="font-size:70px">{icon}</div><h2>{obj["name"]}</h2>{"중복 · 🪙 +15" if last["duplicate"] else "✨"}</div>',unsafe_allow_html=True)
        a,b=st.columns(2)
        if a.button('지금 장착',use_container_width=True):equip(item);g['last']=None;st.rerun()
        if b.button('옷장으로',use_container_width=True):g['last']=None;st.session_state.shop_tab='closet';st.rerun()
    with st.expander('ⓘ'):st.write('25종 각 4% · 중복 +15코인 · 현금 결제 없음')
elif page=='stats':
    period=choose('📈','period',[('이번 주','week'),('이번 달','month'),('올해','year')])
    today=now().date()
    if period=='week':start=today-timedelta(days=today.weekday());prev=start-timedelta(days=7);prev_end=start;end=start+timedelta(days=7);freq='D'
    elif period=='month':
        start=today.replace(day=1);prev=(start-timedelta(days=1)).replace(day=1);prev_end=start;end=(start.replace(day=28)+timedelta(days=4)).replace(day=1);freq='D'
    else:start=date(today.year,1,1);prev=date(today.year-1,1,1);prev_end=start;end=date(today.year+1,1,1);freq='MS'
    values={};previous=0
    for r in d['intakes']:
        day=datetime.fromisoformat(r['at']).astimezone(KST).date();mg=r['mg'] or 0
        if start<=day<end:values[day]=values.get(day,0)+mg
        if prev<=day<prev_end:previous+=mg
    total=sum(values.values());difference=total-previous
    noun={'week':'저번 주','month':'지난달','year':'작년'}[period]
    st.markdown(f'# {total:g} mg')
    st.write(f'{noun}보다 {abs(difference):g}mg '+('더 먹었어요' if difference>0 else '덜 먹었어요' if difference<0 else '차이 없어요'))
    idx=pd.date_range(start,end-timedelta(days=1),freq='D');series=pd.Series([values.get(x.date(),0) for x in idx],index=idx)
    if period=='year':series=series.resample('MS').sum()
    st.line_chart(pd.DataFrame({'카페인 (mg)':series}),color='#8aab71')
    with st.expander('☰'):
        for r in list(reversed(d['intakes'])):
            cols=st.columns([5,1]);cols[0].write(f'{r["at"][:10]} · {r["name"]} · {r["mg"] if r["mg"] is not None else "?"}mg')
            if cols[1].button('×',key='del_'+r['id']):d['intakes'].remove(r);st.rerun()
elif page=='settings':
    g['nickname']=st.text_input('✎ 이름',g['nickname'],max_chars=20)
    with st.expander('💾'):
        out=copy.deepcopy(d);out['dress_v3']=copy.deepcopy(g)
        st.download_button('백업',json.dumps(out,ensure_ascii=False,indent=2),'caffeine_backup.json','application/json',use_container_width=True)
        file=st.file_uploader('복원',type=['json'])
        if file and st.button('복원하기'):
            try:
                if file.size>3_000_000:raise ValueError('파일 용량 초과')
                raw=json.load(file);clean=validate_backup(raw);new=raw.get('dress_v3')
                if new is None:raise ValueError('이전 백업에는 새 옷장 데이터가 없어요.')
                if type(new.get('coins')) is not int or not 0<=new['coins']<=10000000:raise ValueError('코인 오류')
                if not isinstance(new.get('owned'),list) or not all(x in ITEMS for x in new['owned']):raise ValueError('옷장 오류')
                if not isinstance(new.get('equipped'),dict) or not all(k in CATS and v in new['owned'] and ITEMS[v]['cat']==k for k,v in new['equipped'].items()):raise ValueError('착용 오류')
                if not isinstance(new.get('room'),list) or not all(x in ['🪴','🧸','💡','🌷'] for x in new['room']):raise ValueError('방 오류')
                if not isinstance(new.get('nickname'),str) or len(new['nickname'])>20:raise ValueError('이름 오류')
                new={k:copy.deepcopy(new[k]) for k in ['coins','owned','equipped','room','nickname']};new.update(active=None,last=None)
                st.session_state.cb_data=clean;st.session_state.dress_v3=new;st.rerun()
            except (ValueError,KeyError,TypeError) as e:st.error(str(e))
        st.write('새로고침·접속 종료 전 백업해 주세요. 자동 저장·계정 로그인은 없어요.')
    with st.expander('🩺'):
        st.write('진단·치료 앱이 아닙니다. 두근거림이 반복되면 진료를 받으세요. 가슴 통증·숨참·실신 느낌이 동반되면 119에 연락하세요.')
    with st.expander('Aa'):st.write('Gaegu 손글씨체 · 온라인 글꼴을 불러오지 못하면 기기 기본 글꼴로 표시돼요.')
with st.container(key='nav'):
    cols=st.columns(6)
    for col,(target,label) in zip(cols,[('home','⌂ 홈'),('record','✎ 기록'),('mission','⌛ 참기'),('shop','♧ 꾸미기'),('stats','↗ 현황'),('settings','⚙ 설정')]):col.button(label,key='nav_'+target,on_click=go,args=(target,),type='primary' if page==target else 'secondary',use_container_width=True)
