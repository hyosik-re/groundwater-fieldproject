import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
import folium
import streamlit.components.v1 as components
import random

# 페이지 설정
st.set_page_config(page_title="지하수 수질 연구 대시보드", layout="wide", page_icon="💧")

# 모바일 친화적 테마 CSS (전체적인 배경과 탭 스타일 개선 및 반응형 추가)
st.markdown("""
<style>
    /* 전체 배경색 */
    .stApp {
        background-color: #f0f8ff;
    }
    
    /* 제목 및 헤더 색상 변경 */
    h1, h2, h3 {
        color: #005f73 !important;
        font-family: 'Malgun Gothic', sans-serif;
    }
    
    /* 탭 스타일 개선 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        flex-wrap: wrap; /* 모바일에서 탭이 넘어갈 경우 줄바꿈 */
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #e0f7fa;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
        font-size: 14px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff;
        color: #005f73;
        font-weight: bold;
        border-top: 3px solid #005f73;
    }
    
    /* Info 박스 스타일 */
    .stAlert {
        background-color: #e0f7fa;
        color: #005f73;
        border: 1px solid #b2ebf2;
    }

    /* 모바일 최적화 (가로 768px 이하 스크린) */
    @media (max-width: 768px) {
        h1 { font-size: 1.5rem !important; }
        h2 { font-size: 1.2rem !important; }
        h3 { font-size: 1.1rem !important; }
        p, div, span, label { font-size: 0.9rem !important; }
        
        /* 탭 크기 축소 */
        .stTabs [data-baseweb="tab"] {
            height: 40px;
            font-size: 12px;
            padding: 5px;
        }
        
        /* 상단 및 좌우 여백 축소 */
        .block-container {
            padding-top: 2rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)

st.title("💧 지하수 수질 연구 통합 대시보드")
st.markdown("**입력한 도로명 주소**를 중심으로 지질도, 토지이용도, 기상/대기질 및 지하수 관정 정보를 종합적으로 제공합니다. (제공되는 지도 데이터는 데모를 위한 모의 데이터입니다)")

# 모바일을 위해 사이드바 대신 메인 화면 상단에 검색창 배치
st.markdown("### 🔍 검색 옵션")
address = st.text_input("대한민국 도로명 주소 입력", value="대전광역시 유성구 과학로 124")

@st.cache_data
def get_coordinates(addr):
    """geopy를 활용하여 주소를 위도, 경도로 변환합니다. 실패 시 점진적으로 주소를 줄여 검색합니다."""
    addr_query = addr.replace(" 광역시", "광역시").replace(" 특별시", "특별시").replace(" 도 ", "도 ")
    
    geolocator = Nominatim(user_agent="korea_groundwater_research_app")
    parts = addr_query.split()
    
    for i in range(len(parts), 0, -1):
        test_addr = " ".join(parts[:i])
        try:
            location = geolocator.geocode(test_addr)
            if location:
                is_exact = (i == len(parts))
                return location.latitude, location.longitude, is_exact, test_addr
        except Exception as e:
            continue
            
    return None, None, False, ""

@st.cache_data
def generate_mock_wells(lat, lon, num_wells=7):
    """주변 관정 모의 데이터 생성"""
    wells = []
    usages = ["생활용", "농업용", "공업용", "먹는물", "관측용"]
    for i in range(num_wells):
        w_lat = lat + random.uniform(-0.01, 0.01)
        w_lon = lon + random.uniform(-0.01, 0.01)
        depth = random.randint(30, 150)
        water_level = round(random.uniform(2.0, 15.0), 2)
        ph = round(random.uniform(6.5, 8.0), 1)
        ec = random.randint(150, 500)
        no3 = round(random.uniform(0.5, 15.0), 1)
        
        # 수질 등급 판정 (환경부 지하수 수질기준 참고)
        if ph >= 6.5 and ph <= 8.5 and ec < 300 and no3 < 10:
            grade = "✅ 적합"
        elif ph >= 5.8 and ph <= 9.0 and ec < 500 and no3 < 20:
            grade = "⚠️ 보통"
        else:
            grade = "❌ 부적합"
        
        wells.append({
            "관정명": f"지하수관정-{i+1}",
            "용도": random.choice(usages),
            "위도": round(w_lat, 5),
            "경도": round(w_lon, 5),
            "심도(m)": depth,
            "수위(m)": water_level,
            "pH": ph,
            "EC(µS/cm)": ec,
            "NO₃(mg/L)": no3,
            "수질등급": grade
        })
    return pd.DataFrame(wells)

@st.cache_data
def generate_mock_weather():
    """최근 30일간의 모의 날씨 데이터 생성"""
    dates = pd.date_range(end=pd.Timestamp.today(), periods=30)
    weather_data = []
    temp = random.uniform(10.0, 25.0) 
    for d in dates:
        temp += random.uniform(-2.0, 2.0)
        precip = 0 if random.random() > 0.3 else random.uniform(1.0, 40.0)
        
        if precip > 0:
            status, icon = "비/눈", ("❄️" if temp < 0 else "🌧️")
        else:
            status, icon = "맑음/흐림", ("☁️" if random.random() > 0.5 else "☀️")
            
        pm10 = random.randint(15, 80)
        
        weather_data.append({
            "날짜": d.date(),
            "날씨": icon,
            "평균기온(℃)": round(temp, 1),
            "강수량(mm)": round(precip, 1),
            "미세먼지(PM10)": pm10
        })
    df = pd.DataFrame(weather_data)
    df.set_index("날짜", inplace=True)
    return df

def generate_mock_polygons(center_lat, center_lon, grid_size=4, step=0.005, p_type="geology"):
    """중심 좌표 주변으로 격자 형태의 모의 폴리곤 레이어를 생성합니다."""
    polygons = []
    if p_type == "geology":
        types = [("화강암류", "#ff9999"), ("편마암류", "#99ff99"), ("퇴적암", "#9999ff"), ("충적층", "#ffff99")]
    else:
        types = [("산림지역", "#2ca02c"), ("주거지역", "#ff7f0e"), ("상업지역", "#d62728"), ("농경지", "#bcbd22"), ("수역", "#1f77b4")]
        
    start_lat = center_lat - (grid_size // 2) * step
    start_lon = center_lon - (grid_size // 2) * step
    
    for i in range(grid_size):
        for j in range(grid_size):
            t_name, t_color = random.choice(types)
            p_lat = start_lat + i * step
            p_lon = start_lon + j * step
            
            p1 = [p_lat + random.uniform(0, step*0.1), p_lon + random.uniform(0, step*0.1)]
            p2 = [p_lat + step - random.uniform(0, step*0.1), p_lon + random.uniform(0, step*0.1)]
            p3 = [p_lat + step - random.uniform(0, step*0.1), p_lon + step - random.uniform(0, step*0.1)]
            p4 = [p_lat + random.uniform(0, step*0.1), p_lon + step - random.uniform(0, step*0.1)]
            
            polygons.append({
                "locations": [p1, p2, p3, p4],
                "name": t_name,
                "color": t_color
            })
    return polygons

def render_map(m, height=400):
    """WebView에서 통신 오류(iframe 차단)를 방지하기 위해 순수 HTML로 지도를 렌더링합니다."""
    components.html(m._repr_html_(), height=height)

if address:
    with st.spinner("주소 좌표를 변환 중입니다..."):
        lat, lon, is_exact, matched_addr = get_coordinates(address)
    
    if lat and lon:
        if not is_exact:
            st.warning(f"상세 주소를 찾을 수 없어 인근 지역('{matched_addr}')의 좌표로 대체합니다. (OpenStreetMap 한계)")
        else:
            st.success(f"위치 확인 완료! (위도: {lat:.4f}, 경도: {lon:.4f})")
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📍 기본 정보", "🌍 지질도", "🏗️ 토지이용", "⛅ 지역 날씨", "🚰 관정 정보"])
        
        with tab1:
            st.header("📍 검색 위치 정보")
            st.info(f"**입력 주소:** {address}  \n**좌표:** {lat:.6f}, {lon:.6f}")
            m1 = folium.Map(location=[lat, lon], zoom_start=15)
            folium.Marker(
                [lat, lon], 
                tooltip="검색된 위치", 
                icon=folium.Icon(color='red', icon='info-sign')
            ).add_to(m1)
            render_map(m1, 350)
            
        with tab2:
            st.header("🌍 지질도 (Geological Map)")
            st.info("💡 **데이터 출처 안내:** 정확한 전국 지질 정보는 [국가지질자원데이터센터(KIGAM)](https://mgeo.kigam.re.kr/)에서 확인 가능합니다. 아래는 데모용 **모의 지층 분포도**입니다.")
            
            m2 = folium.Map(location=[lat, lon], zoom_start=14)
            geo_polygons = generate_mock_polygons(lat, lon, grid_size=6, step=0.006, p_type="geology")
            for poly in geo_polygons:
                folium.Polygon(
                    locations=poly["locations"], color="gray", weight=1,
                    fill=True, fill_color=poly["color"], fill_opacity=0.5,
                    popup=f"지층: {poly['name']}"
                ).add_to(m2)
            folium.Marker([lat, lon], tooltip="검색 위치", icon=folium.Icon(color='red')).add_to(m2)
            render_map(m2, 400)
            
            st.markdown("""
            **🗺️ 범례 (Legend)**
            | 색상 | 지질 유형 |
            |------|----------|
            | 🟥 | 화강암류 |
            | 🟩 | 편마암류 |
            | 🟦 | 퇴적암 |
            | 🟨 | 충적층 |
            """)
            
        with tab3:
            st.header("🏗️ 토지이용도 (Land Use Map)")
            st.info("💡 **데이터 출처 안내:** 정확한 전국 토지이용 정보는 [환경공간정보서비스(EGIS)](https://egis.me.go.kr/)에서 제공됩니다. 아래는 데모용 **모의 토지이용도**입니다.")
            
            m3 = folium.Map(location=[lat, lon], zoom_start=14)
            land_polygons = generate_mock_polygons(lat, lon, grid_size=6, step=0.005, p_type="land_use")
            for poly in land_polygons:
                folium.Polygon(
                    locations=poly["locations"], color="white", weight=1,
                    fill=True, fill_color=poly["color"], fill_opacity=0.6,
                    popup=f"토지이용: {poly['name']}"
                ).add_to(m3)
            folium.Marker([lat, lon], tooltip="검색 위치", icon=folium.Icon(color='red')).add_to(m3)
            render_map(m3, 400)
            
            st.markdown("""
            **🗺️ 범례 (Legend)**
            | 색상 | 토지이용 유형 |
            |------|-------------|
            | 🟢 | 산림지역 |
            | 🟠 | 주거지역 |
            | 🔴 | 상업지역 |
            | 🟡 | 농경지 |
            | 🔵 | 수역 |
            """)
            
        with tab4:
            st.header("⛅ 최근 한달 지역 날씨 및 대기질")
            st.info("💡 **데이터 출처 안내:** 기상 및 대기질 정보는 [기상청 기상자료개방포털](https://data.kma.go.kr/) 및 [한국환경공단 에어코리아](https://www.airkorea.or.kr/) 기준을 참고한 데이터입니다.")
            
            df_weather = generate_mock_weather()
            latest = df_weather.iloc[-1]
            
            st.subheader("📊 오늘의 날씨 요약")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("오늘의 날씨", latest["날씨"])
            col2.metric("평균 기온", f"{latest['평균기온(℃)']} ℃")
            col3.metric("강수량", f"{latest['강수량(mm)']} mm")
            col4.metric("미세먼지(PM10)", f"{latest['미세먼지(PM10)']} µg/m³", delta="나쁨" if latest['미세먼지(PM10)'] > 50 else "보통", delta_color="inverse")
            
            st.markdown("---")
            st.subheader("🌡️ 일별 평균 기온 추이")
            st.line_chart(df_weather["평균기온(℃)"], color="#FF4B4B")
            
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.subheader("🌧️ 일별 강수량")
                st.bar_chart(df_weather["강수량(mm)"], color="#005f73")
            with col_chart2:
                st.subheader("🌫️ 미세먼지(PM10) 추이")
                st.line_chart(df_weather["미세먼지(PM10)"], color="#808080")
            
            with st.expander("📅 날짜별 상세 데이터 표 보기 (날씨 아이콘 포함)"):
                st.dataframe(df_weather, use_container_width=True)
            
        with tab5:
            st.header("🚰 주변 지하수 관정 정보")
            st.info("💡 **데이터 출처 안내:** 관정 및 수질 정보는 [국가지하수정보센터(GIMS)](https://www.gims.go.kr/) 및 [AI Hub 지하수 수위/수질 데이터](https://aihub.or.kr/)를 참고합니다. 수질 등급은 [환경부 지하수 수질기준](https://www.me.go.kr/)을 기준으로 판정합니다.")
            st.markdown("해당 좌표 반경 내의 **모의 관정 데이터** 목록 및 지도입니다.")
            
            df_wells = generate_mock_wells(lat, lon)
            
            # 수질 요약 메트릭
            st.subheader("📊 관정 수질 요약")
            total = len(df_wells)
            good = len(df_wells[df_wells['수질등급'].str.contains('적합')])
            normal = len(df_wells[df_wells['수질등급'].str.contains('보통')])
            bad = len(df_wells[df_wells['수질등급'].str.contains('부적합')])
            
            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            col_s1.metric("전체 관정 수", f"{total}개")
            col_s2.metric("✅ 적합", f"{good}개")
            col_s3.metric("⚠️ 보통", f"{normal}개")
            col_s4.metric("❌ 부적합", f"{bad}개")
            
            st.markdown("---")
            st.subheader("관정 수질 및 제원 표")
            st.dataframe(df_wells, use_container_width=True, hide_index=True)
                
            st.subheader("관정 위치")
            m5 = folium.Map(location=[lat, lon], zoom_start=14)
            folium.Marker([lat, lon], tooltip="중심 검색 위치", icon=folium.Icon(color='red', icon='star')).add_to(m5)
            
            for idx, row in df_wells.iterrows():
                well_color = 'green' if '적합' in row['수질등급'] else ('orange' if '보통' in row['수질등급'] else 'red')
                popup_html = f"""
                <div style='width: 170px;'>
                    <b>{row['관정명']}</b> ({row['용도']})<br>
                    - 심도: {row['심도(m)']}m<br>
                    - 수위: {row['수위(m)']}m<br>
                    - pH: {row['pH']}<br>
                    - EC: {row['EC(µS/cm)']} µS/cm<br>
                    - NO₃: {row['NO₃(mg/L)']} mg/L<br>
                    - 등급: {row['수질등급']}
                </div>
                """
                folium.Marker(
                    [row['위도'], row['경도']],
                    tooltip=f"{row['관정명']} ({row['수질등급']})",
                    popup=folium.Popup(popup_html, max_width=220),
                    icon=folium.Icon(color=well_color, icon='tint')
                ).add_to(m5)
                
            render_map(m5, 400)
            
    else:
        st.error("해당 주소를 좌표로 변환할 수 없습니다. 올바른 도로명 주소를 입력해주세요.")

# 하단 푸터: 전체 데이터 출처 요약
st.markdown("---")
st.markdown("""
### 📚 데이터 출처 및 참고 자료
| 분류 | 기관/서비스 | URL |
|------|-----------|-----|
| 지질 정보 | 국가지질자원데이터센터 (KIGAM) | [mgeo.kigam.re.kr](https://mgeo.kigam.re.kr/) |
| 토지이용 | 환경공간정보서비스 (EGIS) | [egis.me.go.kr](https://egis.me.go.kr/) |
| 기상 정보 | 기상청 기상자료개방포털 | [data.kma.go.kr](https://data.kma.go.kr/) |
| 대기질 | 한국환경공단 에어코리아 | [airkorea.or.kr](https://www.airkorea.or.kr/) |
| 지하수 관정 | 국가지하수정보센터 (GIMS) | [gims.go.kr](https://www.gims.go.kr/) |
| 수질 기준 | 환경부 | [me.go.kr](https://www.me.go.kr/) |
| AI 학습데이터 | AI Hub | [aihub.or.kr](https://aihub.or.kr/) |

> ⚠️ **참고:** 현재 대시보드에 표시되는 데이터는 **데모용 모의 데이터**입니다. 실제 연구에는 위 기관의 공식 데이터를 활용하세요.
""")
st.caption("© 2026 지하수 수질 연구 통합 대시보드 | Powered by Streamlit")
