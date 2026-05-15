import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
import folium
import streamlit.components.v1 as components
import random, requests
from datetime import datetime, timedelta

WEATHER_CODES = {
    0:("☀️","맑음"),1:("🌤️","대체로 맑음"),2:("⛅","구름 조금"),3:("☁️","흐림"),
    45:("🌫️","안개"),48:("🌫️","안개"),51:("🌦️","이슬비"),53:("🌦️","이슬비"),55:("🌦️","이슬비"),
    61:("🌧️","비"),63:("🌧️","비"),65:("🌧️","폭우"),71:("❄️","눈"),73:("❄️","눈"),75:("❄️","폭설"),
    80:("🌧️","소나기"),81:("🌧️","소나기"),82:("🌧️","폭우"),
    95:("⛈️","뇌우"),96:("⛈️","뇌우"),99:("⛈️","뇌우"),
}
LANDUSE_STYLES = {
    "residential":("주거지역","#ff7f0e"),"commercial":("상업지역","#d62728"),
    "industrial":("공업지역","#9467bd"),"retail":("소매지역","#e377c2"),
    "farmland":("농경지","#bcbd22"),"farm":("농장","#bcbd22"),
    "forest":("산림","#2ca02c"),"grass":("초지","#98df8a"),
    "meadow":("초지","#98df8a"),"orchard":("과수원","#8c564b"),
    "basin":("수역","#1f77b4"),"reservoir":("저수지","#1f77b4"),
    "construction":("건설중","#ff9896"),"education":("교육시설","#aec7e8"),
    "cemetery":("묘지","#7f7f7f"),"military":("군사지역","#c5b0d5"),
}

st.set_page_config(page_title="지하수 수질 연구 대시보드", layout="wide", page_icon="💧")
st.markdown("""<style>
.stApp{background-color:#f0f8ff}
h1,h2,h3{color:#005f73 !important;font-family:'Malgun Gothic',sans-serif}
.stTabs [data-baseweb="tab-list"]{gap:2px;flex-wrap:wrap}
.stTabs [data-baseweb="tab"]{height:50px;white-space:pre-wrap;background-color:#e0f7fa;border-radius:4px 4px 0 0;padding:10px;font-size:14px}
.stTabs [aria-selected="true"]{background-color:#fff;color:#005f73;font-weight:bold;border-top:3px solid #005f73}
@media(max-width:768px){
h1{font-size:1.5rem !important}h2{font-size:1.2rem !important}
.stTabs [data-baseweb="tab"]{height:40px;font-size:12px;padding:5px}
.block-container{padding:2rem 1rem !important}
}
</style>""", unsafe_allow_html=True)

st.title("💧 지하수 수질 연구 통합 대시보드")
st.markdown("**도로명 주소** 기반으로 지형, 지질, 토지이용, 기상, 관정 정보를 종합 제공합니다.")
address = st.text_input("🔍 대한민국 도로명 주소 입력", value="대전광역시 유성구 과학로 124")

@st.cache_data
def get_coordinates(addr):
    geolocator = Nominatim(user_agent="korea_gw_app")
    parts = addr.replace(" 광역시","광역시").replace(" 특별시","특별시").split()
    for i in range(len(parts),0,-1):
        try:
            loc = geolocator.geocode(" ".join(parts[:i]))
            if loc: return loc.latitude, loc.longitude, (i==len(parts)), " ".join(parts[:i])
        except: continue
    return None,None,False,""

@st.cache_data(ttl=86400)
def get_real_weather(lat, lon):
    try:
        end = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        r = requests.get("https://archive-api.open-meteo.com/v1/archive", params={
            "latitude":lat,"longitude":lon,"timezone":"Asia/Seoul","start_date":start,"end_date":end,
            "daily":"weather_code,temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum"
        }, timeout=15)
        if r.status_code==200: return r.json()
    except: pass
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude":lat,"longitude":lon,"timezone":"Asia/Seoul","past_days":92,"forecast_days":1,
            "daily":"weather_code,temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum",
            "current":"temperature_2m,weather_code,wind_speed_10m,relative_humidity_2m"
        }, timeout=10)
        if r.status_code==200: return r.json()
    except: pass
    return None

@st.cache_data(ttl=3600)
def get_current_weather(lat, lon):
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude":lat,"longitude":lon,"timezone":"Asia/Seoul","forecast_days":1,
            "current":"temperature_2m,weather_code,wind_speed_10m,relative_humidity_2m"
        }, timeout=10)
        if r.status_code==200: return r.json()
    except: pass
    return None

@st.cache_data(ttl=3600)
def get_air_quality(lat, lon):
    try:
        r = requests.get("https://air-quality-api.open-meteo.com/v1/air-quality", params={
            "latitude":lat,"longitude":lon,"current":"pm10,pm2_5","timezone":"Asia/Seoul"
        }, timeout=10)
        if r.status_code==200: return r.json()
    except: pass
    return None

@st.cache_data(ttl=86400)
def get_land_use_osm(lat, lon, radius=1500):
    query = f'[out:json][timeout:25];(way["landuse"](around:{radius},{lat},{lon}););out body;>;out skel qt;'
    try:
        r = requests.get("https://overpass-api.de/api/interpreter", params={"data":query}, timeout=30)
        if r.status_code!=200: return None
        data = r.json()
        nodes = {e["id"]:[e["lat"],e["lon"]] for e in data.get("elements",[]) if e["type"]=="node"}
        polys = []
        for e in data.get("elements",[]):
            if e["type"]=="way":
                coords = [nodes[n] for n in e.get("nodes",[]) if n in nodes]
                if len(coords)>=3:
                    polys.append({"coords":coords,"type":e.get("tags",{}).get("landuse","unknown")})
        return polys
    except: return None

@st.cache_data
def generate_mock_wells(lat, lon, n=7):
    wells = []
    usages = ["생활용","농업용","공업용","먹는물","관측용"]
    for i in range(n):
        ph = round(random.uniform(6.5,8.0),1)
        ec = random.randint(150,500)
        no3 = round(random.uniform(0.5,15.0),1)
        grade = "✅ 적합" if (6.5<=ph<=8.5 and ec<300 and no3<10) else ("⚠️ 보통" if (5.8<=ph<=9.0 and ec<500 and no3<20) else "❌ 부적합")
        wells.append({"관정명":f"지하수관정-{i+1}","용도":random.choice(usages),
            "위도":round(lat+random.uniform(-0.01,0.01),5),"경도":round(lon+random.uniform(-0.01,0.01),5),
            "심도(m)":random.randint(30,150),"수위(m)":round(random.uniform(2,15),2),
            "pH":ph,"EC(µS/cm)":ec,"NO₃(mg/L)":no3,"수질등급":grade})
    return pd.DataFrame(wells)

def render_map(m, height=450):
    components.html(m._repr_html_(), height=height)

if address:
    with st.spinner("좌표 변환 중..."):
        lat, lon, is_exact, matched = get_coordinates(address)
    if lat and lon:
        if not is_exact:
            st.warning(f"인근 지역('{matched}')의 좌표로 대체합니다.")
        else:
            st.success(f"위치 확인! (위도: {lat:.4f}, 경도: {lon:.4f})")

        tabs = st.tabs(["📍 기본정보","🗺️ 지형도","🌍 지질도","🏗️ 토지이용","⛅ 날씨/대기질","🚰 관정정보"])

        with tabs[0]:
            st.header("📍 검색 위치")
            st.info(f"**주소:** {address}\n\n**좌표:** {lat:.6f}, {lon:.6f}")
            m1 = folium.Map(location=[lat,lon], zoom_start=15)
            folium.Marker([lat,lon], tooltip="검색 위치", icon=folium.Icon(color='red',icon='info-sign')).add_to(m1)
            render_map(m1)

        with tabs[1]:
            st.header("🗺️ 기본 지형도")
            st.info("💡 **출처:** [OpenTopoMap](https://opentopomap.org/) — 등고선, 도로, 건물 등 지형 정보를 포함한 실제 지형도입니다.")
            m_topo = folium.Map(location=[lat,lon], zoom_start=14, tiles=None)
            folium.TileLayer(tiles='https://tile.opentopomap.org/{z}/{x}/{y}.png',
                attr='OpenTopoMap', name='지형도', max_zoom=17).add_to(m_topo)
            folium.Marker([lat,lon], tooltip="검색 위치", icon=folium.Icon(color='red')).add_to(m_topo)
            render_map(m_topo)

        with tabs[2]:
            st.header("🌍 지질도 (Geological Map)")
            st.info("💡 **출처:** [Macrostrat](https://macrostrat.org/) 글로벌 지질 타일 서비스 — 실제 지질 데이터 기반 지도입니다. 국내 상세 지질은 [KIGAM](https://mgeo.kigam.re.kr/) 참고.")
            m2 = folium.Map(location=[lat,lon], zoom_start=13, tiles=None)
            folium.TileLayer(tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
                attr='OSM', name='기본지도', subdomains='abc').add_to(m2)
            folium.TileLayer(tiles='https://tiles.macrostrat.org/carto/{z}/{x}/{y}.png',
                attr='<a href="https://macrostrat.org">Macrostrat</a>',
                name='지질도', overlay=True, opacity=0.7).add_to(m2)
            folium.Marker([lat,lon], tooltip="검색 위치", icon=folium.Icon(color='red')).add_to(m2)
            folium.LayerControl().add_to(m2)
            render_map(m2)
            st.caption("지질도 레이어가 보이지 않으면 지도 우측 상단 레이어 컨트롤에서 '지질도'를 활성화하세요.")

        with tabs[3]:
            st.header("🏗️ 토지이용도 (Land Use)")
            st.info("💡 **출처:** [OpenStreetMap](https://www.openstreetmap.org/) 실제 데이터. 국내 상세 정보는 [EGIS](https://egis.me.go.kr/) 참고.")
            with st.spinner("OpenStreetMap에서 토지이용 데이터 조회 중..."):
                land = get_land_use_osm(lat, lon)
            m3 = folium.Map(location=[lat,lon], zoom_start=14, tiles='CartoDB positron')
            if land and len(land)>0:
                st.success(f"✅ 반경 1.5km 내 **{len(land)}개** 토지이용 영역 발견")
                types_found = set()
                for p in land:
                    nm, cl = LANDUSE_STYLES.get(p["type"],(p["type"],"#888"))
                    types_found.add(nm)
                    folium.Polygon(locations=p["coords"], color="white", weight=1,
                        fill=True, fill_color=cl, fill_opacity=0.6, popup=f"{nm} ({p['type']})").add_to(m3)
                folium.Marker([lat,lon], tooltip="검색 위치", icon=folium.Icon(color='red')).add_to(m3)
                render_map(m3)
                st.markdown(f"**발견된 유형:** {' · '.join(types_found)}")
            else:
                st.warning("이 지역의 OSM 토지이용 데이터가 없습니다.")
                folium.Marker([lat,lon], tooltip="검색 위치", icon=folium.Icon(color='red')).add_to(m3)
                render_map(m3)

        with tabs[4]:
            st.header("⛅ 날씨 및 대기질")
            st.info("💡 **출처:** [Open-Meteo](https://open-meteo.com/) 실시간 기상 + 과거 1년 | [Open-Meteo Air Quality](https://open-meteo.com/) 대기질")
            cur_w = get_current_weather(lat, lon)
            air = get_air_quality(lat, lon)
            if cur_w and "current" in cur_w:
                c = cur_w["current"]
                ic, ds = WEATHER_CODES.get(c.get("weather_code",0),("❓","알수없음"))
                st.subheader("📊 현재 날씨 (실시간)")
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("날씨",f"{ic} {ds}")
                c2.metric("기온",f"{c.get('temperature_2m','-')} ℃")
                c3.metric("풍속",f"{c.get('wind_speed_10m','-')} km/h")
                c4.metric("습도",f"{c.get('relative_humidity_2m','-')} %")
            if air and "current" in air:
                ac = air["current"]
                pm10, pm25 = ac.get("pm10",0), ac.get("pm2_5",0)
                a1, a2 = st.columns(2)
                a1.metric("미세먼지(PM10)", f"{pm10} µg/m³", delta="좋음" if pm10<=30 else ("보통" if pm10<=80 else "나쁨"), delta_color="off" if pm10<=80 else "inverse")
                a2.metric("초미세먼지(PM2.5)", f"{pm25} µg/m³", delta="좋음" if pm25<=15 else ("보통" if pm25<=35 else "나쁨"), delta_color="off" if pm25<=35 else "inverse")
            st.markdown("---")
            with st.spinner("최근 1년 기상 데이터 조회 중..."):
                hist = get_real_weather(lat, lon)
            if hist and "daily" in hist:
                d = hist["daily"]
                df = pd.DataFrame({
                    "날짜": pd.to_datetime(d.get("time",[])),
                    "날씨": [WEATHER_CODES.get(c,("❓","?"))[0] for c in d.get("weather_code",[])],
                    "평균기온(℃)": d.get("temperature_2m_mean",[]),
                    "최고기온(℃)": d.get("temperature_2m_max",[]),
                    "최저기온(℃)": d.get("temperature_2m_min",[]),
                    "강수량(mm)": d.get("precipitation_sum",[]),
                }).set_index("날짜")
                st.subheader(f"🌡️ 일별 기온 추이 ({len(df)}일)")
                st.line_chart(df[["최고기온(℃)","평균기온(℃)","최저기온(℃)"]])
                st.subheader("🌧️ 일별 강수량")
                st.bar_chart(df["강수량(mm)"], color="#005f73")
                with st.expander("📅 상세 데이터 표"):
                    st.dataframe(df, use_container_width=True)
            else:
                st.error("기상 데이터를 가져오지 못했습니다. 잠시 후 다시 시도해주세요.")

        with tabs[5]:
            st.header("🚰 주변 지하수 관정 정보")
            st.info("💡 **출처:** 실제 관정 데이터는 [국가지하수정보센터(GIMS)](https://www.gims.go.kr/) 에서 제공됩니다. 현재는 API키가 필요하여 **모의 데이터**로 표시합니다.")
            df_w = generate_mock_wells(lat, lon)
            st.subheader("📊 수질 요약")
            t = len(df_w)
            g = len(df_w[df_w['수질등급'].str.contains('적합')])
            n = len(df_w[df_w['수질등급'].str.contains('보통')])
            b = len(df_w[df_w['수질등급'].str.contains('부적합')])
            s1,s2,s3,s4 = st.columns(4)
            s1.metric("전체",f"{t}개"); s2.metric("✅ 적합",f"{g}개"); s3.metric("⚠️ 보통",f"{n}개"); s4.metric("❌ 부적합",f"{b}개")
            st.dataframe(df_w, use_container_width=True, hide_index=True)
            m5 = folium.Map(location=[lat,lon], zoom_start=14)
            folium.Marker([lat,lon], tooltip="중심", icon=folium.Icon(color='red',icon='star')).add_to(m5)
            for _,r in df_w.iterrows():
                wc = 'green' if '적합' in r['수질등급'] else ('orange' if '보통' in r['수질등급'] else 'red')
                folium.Marker([r['위도'],r['경도']], tooltip=f"{r['관정명']}({r['수질등급']})",
                    popup=f"<b>{r['관정명']}</b><br>pH:{r['pH']} EC:{r['EC(µS/cm)']} 등급:{r['수질등급']}",
                    icon=folium.Icon(color=wc,icon='tint')).add_to(m5)
            render_map(m5)
    else:
        st.error("주소를 좌표로 변환할 수 없습니다.")

st.markdown("---")
st.markdown("""
### 📚 데이터 출처
| 분류 | 출처 | 유형 |
|------|------|------|
| 지형도 | [OpenTopoMap](https://opentopomap.org/) | ✅ 실제 |
| 지질도 | [Macrostrat](https://macrostrat.org/) | ✅ 실제 |
| 토지이용 | [OpenStreetMap](https://openstreetmap.org/) | ✅ 실제 |
| 기상 | [Open-Meteo](https://open-meteo.com/) | ✅ 실제 |
| 대기질 | [Open-Meteo Air Quality](https://open-meteo.com/) | ✅ 실제 |
| 관정 | [GIMS](https://www.gims.go.kr/) | ⚠️ 모의 |
""")
st.caption("© 2026 지하수 수질 연구 통합 대시보드 | Powered by Streamlit")
