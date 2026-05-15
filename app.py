import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
import folium
import streamlit.components.v1 as components
import random
import requests
from datetime import datetime, timedelta

# 날씨 코드 → 아이콘/설명 매핑 (Open-Meteo WMO 코드)
WEATHER_CODES = {
    0: ("☀️", "맑음"), 1: ("🌤️", "대체로 맑음"), 2: ("⛅", "구름 조금"), 3: ("☁️", "흐림"),
    45: ("🌫️", "안개"), 48: ("🌫️", "안개"),
    51: ("🌦️", "이슬비"), 53: ("🌦️", "이슬비"), 55: ("🌦️", "이슬비"),
    61: ("🌧️", "비"), 63: ("🌧️", "비"), 65: ("🌧️", "폭우"),
    71: ("❄️", "눈"), 73: ("❄️", "눈"), 75: ("❄️", "폭설"), 77: ("❄️", "싸락눈"),
    80: ("🌧️", "소나기"), 81: ("🌧️", "소나기"), 82: ("🌧️", "폭우"),
    85: ("❄️", "눈"), 86: ("❄️", "폭설"),
    95: ("⛈️", "뇌우"), 96: ("⛈️", "뇌우"), 99: ("⛈️", "뇌우"),
}

# OSM 토지이용 유형 → 한글명/색상
LANDUSE_STYLES = {
    "residential": ("주거지역", "#ff7f0e"), "commercial": ("상업지역", "#d62728"),
    "industrial": ("공업지역", "#9467bd"), "retail": ("소매지역", "#e377c2"),
    "farmland": ("농경지", "#bcbd22"), "farm": ("농장", "#bcbd22"),
    "forest": ("산림", "#2ca02c"), "grass": ("초지", "#98df8a"),
    "meadow": ("초지", "#98df8a"), "orchard": ("과수원", "#8c564b"),
    "cemetery": ("묘지", "#7f7f7f"), "recreation_ground": ("여가지역", "#17becf"),
    "basin": ("수역", "#1f77b4"), "reservoir": ("저수지", "#1f77b4"),
    "construction": ("건설중", "#ff9896"), "education": ("교육시설", "#aec7e8"),
    "military": ("군사지역", "#c5b0d5"), "quarry": ("채석장", "#7f7f7f"),
}

st.set_page_config(page_title="지하수 수질 연구 대시보드", layout="wide", page_icon="💧")

st.markdown("""
<style>
    .stApp { background-color: #f0f8ff; }
    h1, h2, h3 { color: #005f73 !important; font-family: 'Malgun Gothic', sans-serif; }
    .stTabs [data-baseweb="tab-list"] { gap: 2px; flex-wrap: wrap; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; white-space: pre-wrap; background-color: #e0f7fa;
        border-radius: 4px 4px 0 0; padding: 10px; font-size: 14px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #fff; color: #005f73; font-weight: bold; border-top: 3px solid #005f73;
    }
    .stAlert { background-color: #e0f7fa; color: #005f73; border: 1px solid #b2ebf2; }
    @media (max-width: 768px) {
        h1 { font-size: 1.5rem !important; } h2 { font-size: 1.2rem !important; }
        .stTabs [data-baseweb="tab"] { height: 40px; font-size: 12px; padding: 5px; }
        .block-container { padding-top: 2rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }
    }
</style>
""", unsafe_allow_html=True)

st.title("💧 지하수 수질 연구 통합 대시보드")
st.markdown("**입력한 도로명 주소**를 중심으로 지질도, 토지이용도, 기상/대기질 및 지하수 관정 정보를 종합적으로 제공합니다.")

st.markdown("### 🔍 검색 옵션")
address = st.text_input("대한민국 도로명 주소 입력", value="대전광역시 유성구 과학로 124")

# ─── 함수 정의 ───

@st.cache_data
def get_coordinates(addr):
    geolocator = Nominatim(user_agent="korea_groundwater_research_app")
    parts = addr.replace(" 광역시", "광역시").replace(" 특별시", "특별시").split()
    for i in range(len(parts), 0, -1):
        try:
            loc = geolocator.geocode(" ".join(parts[:i]))
            if loc:
                return loc.latitude, loc.longitude, (i == len(parts)), " ".join(parts[:i])
        except Exception:
            continue
    return None, None, False, ""

@st.cache_data(ttl=3600)
def get_real_weather(lat, lon):
    """Open-Meteo API로 최근 30일 + 오늘 실제 날씨 데이터 조회"""
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": lat, "longitude": lon,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum",
            "current": "temperature_2m,weather_code,wind_speed_10m,relative_humidity_2m",
            "timezone": "Asia/Seoul", "past_days": 30, "forecast_days": 1
        }, timeout=10)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

@st.cache_data(ttl=3600)
def get_air_quality(lat, lon):
    """Open-Meteo Air Quality API로 현재 대기질 조회"""
    try:
        r = requests.get("https://air-quality-api.open-meteo.com/v1/air-quality", params={
            "latitude": lat, "longitude": lon,
            "current": "pm10,pm2_5", "timezone": "Asia/Seoul"
        }, timeout=10)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

@st.cache_data(ttl=86400)
def get_land_use_osm(lat, lon, radius=1500):
    """OpenStreetMap Overpass API로 실제 토지이용 폴리곤 조회"""
    query = f"""[out:json][timeout:25];(way["landuse"](around:{radius},{lat},{lon}););out body;>;out skel qt;"""
    try:
        r = requests.get("https://overpass-api.de/api/interpreter", params={"data": query}, timeout=30)
        if r.status_code != 200:
            return None
        data = r.json()
        nodes = {}
        ways = []
        for el in data.get("elements", []):
            if el["type"] == "node":
                nodes[el["id"]] = [el["lat"], el["lon"]]
            elif el["type"] == "way":
                ways.append(el)
        polygons = []
        for way in ways:
            coords = [nodes[nid] for nid in way.get("nodes", []) if nid in nodes]
            if len(coords) >= 3:
                lu_type = way.get("tags", {}).get("landuse", "unknown")
                polygons.append({"coords": coords, "type": lu_type})
        return polygons
    except Exception:
        return None

def generate_mock_polygons(center_lat, center_lon, grid_size=4, step=0.005, p_type="geology"):
    polygons = []
    types = [("화강암류", "#ff9999"), ("편마암류", "#99ff99"), ("퇴적암", "#9999ff"), ("충적층", "#ffff99")]
    s_lat = center_lat - (grid_size // 2) * step
    s_lon = center_lon - (grid_size // 2) * step
    for i in range(grid_size):
        for j in range(grid_size):
            t_name, t_color = random.choice(types)
            p_lat, p_lon = s_lat + i * step, s_lon + j * step
            locs = [
                [p_lat + random.uniform(0, step*0.1), p_lon + random.uniform(0, step*0.1)],
                [p_lat + step - random.uniform(0, step*0.1), p_lon + random.uniform(0, step*0.1)],
                [p_lat + step - random.uniform(0, step*0.1), p_lon + step - random.uniform(0, step*0.1)],
                [p_lat + random.uniform(0, step*0.1), p_lon + step - random.uniform(0, step*0.1)],
            ]
            polygons.append({"locations": locs, "name": t_name, "color": t_color})
    return polygons

@st.cache_data
def generate_mock_wells(lat, lon, num_wells=7):
    wells = []
    usages = ["생활용", "농업용", "공업용", "먹는물", "관측용"]
    for i in range(num_wells):
        w_lat, w_lon = lat + random.uniform(-0.01, 0.01), lon + random.uniform(-0.01, 0.01)
        depth, wl = random.randint(30, 150), round(random.uniform(2.0, 15.0), 2)
        ph, ec, no3 = round(random.uniform(6.5, 8.0), 1), random.randint(150, 500), round(random.uniform(0.5, 15.0), 1)
        if ph >= 6.5 and ph <= 8.5 and ec < 300 and no3 < 10:
            grade = "✅ 적합"
        elif ph >= 5.8 and ph <= 9.0 and ec < 500 and no3 < 20:
            grade = "⚠️ 보통"
        else:
            grade = "❌ 부적합"
        wells.append({"관정명": f"지하수관정-{i+1}", "용도": random.choice(usages),
            "위도": round(w_lat, 5), "경도": round(w_lon, 5), "심도(m)": depth, "수위(m)": wl,
            "pH": ph, "EC(µS/cm)": ec, "NO₃(mg/L)": no3, "수질등급": grade})
    return pd.DataFrame(wells)

def render_map(m, height=400):
    components.html(m._repr_html_(), height=height)

# ─── 메인 로직 ───

if address:
    with st.spinner("주소 좌표를 변환 중입니다..."):
        lat, lon, is_exact, matched_addr = get_coordinates(address)

    if lat and lon:
        if not is_exact:
            st.warning(f"상세 주소를 찾을 수 없어 인근 지역('{matched_addr}')의 좌표로 대체합니다.")
        else:
            st.success(f"위치 확인 완료! (위도: {lat:.4f}, 경도: {lon:.4f})")

        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📍 기본 정보", "🌍 지질도", "🏗️ 토지이용", "⛅ 지역 날씨", "🚰 관정 정보"])

        # ── 탭1: 기본 정보 ──
        with tab1:
            st.header("📍 검색 위치 정보")
            st.info(f"**입력 주소:** {address}  \n**좌표:** {lat:.6f}, {lon:.6f}")
            m1 = folium.Map(location=[lat, lon], zoom_start=15)
            folium.Marker([lat, lon], tooltip="검색된 위치", icon=folium.Icon(color='red', icon='info-sign')).add_to(m1)
            render_map(m1, 350)

        # ── 탭2: 지질도 (모의) ──
        with tab2:
            st.header("🌍 지질도 (Geological Map)")
            st.info("💡 **데이터 출처:** 정확한 지질 정보는 [국가지질자원데이터센터(KIGAM)](https://mgeo.kigam.re.kr/) 에서 확인 가능합니다. 아래는 **모의 데이터**입니다.")
            m2 = folium.Map(location=[lat, lon], zoom_start=14)
            for poly in generate_mock_polygons(lat, lon, 6, 0.006):
                folium.Polygon(locations=poly["locations"], color="gray", weight=1,
                    fill=True, fill_color=poly["color"], fill_opacity=0.5, popup=f"지층: {poly['name']}").add_to(m2)
            folium.Marker([lat, lon], tooltip="검색 위치", icon=folium.Icon(color='red')).add_to(m2)
            render_map(m2, 400)
            st.markdown("**🗺️ 범례:** 🟥 화강암류 | 🟩 편마암류 | 🟦 퇴적암 | 🟨 충적층")

        # ── 탭3: 토지이용도 (실제 OSM 데이터) ──
        with tab3:
            st.header("🏗️ 토지이용도 (Land Use Map)")
            st.info("💡 **데이터 출처:** [OpenStreetMap](https://www.openstreetmap.org/) 실제 데이터 기반. 보다 정확한 국내 토지이용 정보는 [환경공간정보서비스(EGIS)](https://egis.me.go.kr/) 참고.")

            with st.spinner("OpenStreetMap에서 토지이용 데이터를 조회 중..."):
                land_data = get_land_use_osm(lat, lon)

            m3 = folium.Map(location=[lat, lon], zoom_start=14)

            if land_data and len(land_data) > 0:
                st.success(f"✅ 반경 1.5km 내 **{len(land_data)}개**의 토지이용 영역을 발견했습니다.")
                found_types = set()
                for poly in land_data:
                    lu_type = poly["type"]
                    name, color = LANDUSE_STYLES.get(lu_type, (lu_type, "#888888"))
                    found_types.add(f"{name}")
                    folium.Polygon(locations=poly["coords"], color="white", weight=1,
                        fill=True, fill_color=color, fill_opacity=0.5, popup=f"토지이용: {name} ({lu_type})").add_to(m3)
                folium.Marker([lat, lon], tooltip="검색 위치", icon=folium.Icon(color='red')).add_to(m3)
                render_map(m3, 400)
                st.markdown(f"**🗺️ 발견된 토지이용 유형:** {' | '.join(found_types)}")
            else:
                st.warning("⚠️ 이 지역에 대한 OpenStreetMap 토지이용 데이터가 없습니다. 모의 데이터로 표시합니다.")
                mock_land = [("산림지역", "#2ca02c"), ("주거지역", "#ff7f0e"), ("상업지역", "#d62728"), ("농경지", "#bcbd22"), ("수역", "#1f77b4")]
                s_lat, s_lon = lat - 3*0.005, lon - 3*0.005
                for i in range(6):
                    for j in range(6):
                        n, c = random.choice(mock_land)
                        p = s_lat + i*0.005
                        q = s_lon + j*0.005
                        folium.Polygon(locations=[[p,q],[p+0.005,q],[p+0.005,q+0.005],[p,q+0.005]],
                            color="white", weight=1, fill=True, fill_color=c, fill_opacity=0.5, popup=n).add_to(m3)
                folium.Marker([lat, lon], tooltip="검색 위치", icon=folium.Icon(color='red')).add_to(m3)
                render_map(m3, 400)

        # ── 탭4: 실제 날씨 (Open-Meteo API) ──
        with tab4:
            st.header("⛅ 최근 한달 지역 날씨 및 대기질")
            st.info("💡 **데이터 출처:** [Open-Meteo API](https://open-meteo.com/) (실시간 기상 데이터) 및 [Open-Meteo Air Quality API](https://open-meteo.com/) (실시간 대기질)")

            weather_data = get_real_weather(lat, lon)
            air_data = get_air_quality(lat, lon)

            if weather_data and "current" in weather_data:
                cur = weather_data["current"]
                w_code = cur.get("weather_code", 0)
                icon, desc = WEATHER_CODES.get(w_code, ("❓", "알 수 없음"))

                st.subheader("📊 현재 날씨 (실시간)")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("날씨", f"{icon} {desc}")
                c2.metric("기온", f"{cur.get('temperature_2m', '-')} ℃")
                c3.metric("풍속", f"{cur.get('wind_speed_10m', '-')} km/h")
                c4.metric("습도", f"{cur.get('relative_humidity_2m', '-')} %")

                if air_data and "current" in air_data:
                    ac = air_data["current"]
                    pm10 = ac.get("pm10", 0)
                    pm25 = ac.get("pm2_5", 0)
                    ca, cb = st.columns(2)
                    pm10_status = "좋음" if pm10 <= 30 else ("보통" if pm10 <= 80 else "나쁨")
                    pm25_status = "좋음" if pm25 <= 15 else ("보통" if pm25 <= 35 else "나쁨")
                    ca.metric("미세먼지(PM10)", f"{pm10} µg/m³", delta=pm10_status, delta_color="inverse" if pm10 > 80 else "off")
                    cb.metric("초미세먼지(PM2.5)", f"{pm25} µg/m³", delta=pm25_status, delta_color="inverse" if pm25 > 35 else "off")

                st.markdown("---")

                # 일별 데이터 차트
                daily = weather_data.get("daily", {})
                if daily:
                    dates = daily.get("time", [])
                    df_w = pd.DataFrame({
                        "날짜": pd.to_datetime(dates),
                        "날씨": [WEATHER_CODES.get(c, ("❓","?"))[0] for c in daily.get("weather_code", [])],
                        "상태": [WEATHER_CODES.get(c, ("❓","?"))[1] for c in daily.get("weather_code", [])],
                        "평균기온(℃)": daily.get("temperature_2m_mean", []),
                        "최고기온(℃)": daily.get("temperature_2m_max", []),
                        "최저기온(℃)": daily.get("temperature_2m_min", []),
                        "강수량(mm)": daily.get("precipitation_sum", []),
                    })
                    df_w.set_index("날짜", inplace=True)

                    st.subheader("🌡️ 일별 기온 추이 (실측)")
                    st.line_chart(df_w[["최고기온(℃)", "평균기온(℃)", "최저기온(℃)"]])

                    st.subheader("🌧️ 일별 강수량 (실측)")
                    st.bar_chart(df_w["강수량(mm)"], color="#005f73")

                    with st.expander("📅 날짜별 상세 데이터 (날씨 아이콘 포함)"):
                        st.dataframe(df_w, use_container_width=True)
            else:
                st.error("⚠️ 날씨 데이터를 가져오지 못했습니다. 잠시 후 다시 시도해주세요.")

        # ── 탭5: 관정 정보 (모의) ──
        with tab5:
            st.header("🚰 주변 지하수 관정 정보")
            st.info("💡 **데이터 출처:** 관정 정보는 [국가지하수정보센터(GIMS)](https://www.gims.go.kr/) 참고. 수질 등급은 [환경부 수질기준](https://www.me.go.kr/) 기준. 현재 **모의 데이터**입니다.")

            df_wells = generate_mock_wells(lat, lon)

            st.subheader("📊 관정 수질 요약")
            total = len(df_wells)
            good = len(df_wells[df_wells['수질등급'].str.contains('적합')])
            normal = len(df_wells[df_wells['수질등급'].str.contains('보통')])
            bad = len(df_wells[df_wells['수질등급'].str.contains('부적합')])
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("전체", f"{total}개")
            s2.metric("✅ 적합", f"{good}개")
            s3.metric("⚠️ 보통", f"{normal}개")
            s4.metric("❌ 부적합", f"{bad}개")

            st.markdown("---")
            st.subheader("관정 수질 및 제원 표")
            st.dataframe(df_wells, use_container_width=True, hide_index=True)

            st.subheader("관정 위치")
            m5 = folium.Map(location=[lat, lon], zoom_start=14)
            folium.Marker([lat, lon], tooltip="중심 검색 위치", icon=folium.Icon(color='red', icon='star')).add_to(m5)
            for _, row in df_wells.iterrows():
                wc = 'green' if '적합' in row['수질등급'] else ('orange' if '보통' in row['수질등급'] else 'red')
                popup = f"<div style='width:170px'><b>{row['관정명']}</b> ({row['용도']})<br>심도:{row['심도(m)']}m | pH:{row['pH']} | EC:{row['EC(µS/cm)']}<br>등급: {row['수질등급']}</div>"
                folium.Marker([row['위도'], row['경도']], tooltip=f"{row['관정명']} ({row['수질등급']})",
                    popup=folium.Popup(popup, max_width=220), icon=folium.Icon(color=wc, icon='tint')).add_to(m5)
            render_map(m5, 400)

    else:
        st.error("해당 주소를 좌표로 변환할 수 없습니다. 올바른 도로명 주소를 입력해주세요.")

# 하단 출처 요약
st.markdown("---")
st.markdown("""
### 📚 데이터 출처
| 분류 | 출처 | 데이터 유형 |
|------|------|-----------|
| 기상 | [Open-Meteo](https://open-meteo.com/) | ✅ 실시간 API |
| 대기질 | [Open-Meteo Air Quality](https://open-meteo.com/) | ✅ 실시간 API |
| 토지이용 | [OpenStreetMap](https://www.openstreetmap.org/) | ✅ 실제 데이터 |
| 지질 | [KIGAM](https://mgeo.kigam.re.kr/) | ⚠️ 모의 데이터 |
| 지하수 관정 | [GIMS](https://www.gims.go.kr/) | ⚠️ 모의 데이터 |
""")
st.caption("© 2026 지하수 수질 연구 통합 대시보드 | Powered by Streamlit")
