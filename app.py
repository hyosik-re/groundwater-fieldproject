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
st.markdown("**입력한 도로명 주소**를 중심으로 지질도, 토지이용도, 수계도 및 지하수 관정 정보를 종합적으로 제공합니다.")

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
    for i in range(num_wells):
        w_lat = lat + random.uniform(-0.01, 0.01)
        w_lon = lon + random.uniform(-0.01, 0.01)
        depth = random.randint(30, 150)
        water_level = round(random.uniform(2.0, 15.0), 2)
        ph = round(random.uniform(6.5, 8.0), 1)
        ec = random.randint(150, 500)
        wells.append({
            "관정명": f"지하수관정-{i+1}",
            "위도": round(w_lat, 5),
            "경도": round(w_lon, 5),
            "심도(m)": depth,
            "수위(m)": water_level,
            "pH": ph,
            "EC(µS/cm)": ec
        })
    return pd.DataFrame(wells)

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
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📍 기본 정보", "🌍 지질도", "🏗️ 토지이용", "🌊 수계도", "🚰 관정 정보"])
        
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
            st.info("💡 **실제 데이터 소스:** 국가지질자원데이터센터(KIGAM) 및 AI Hub(https://aihub.or.kr/) 지질/수질 데이터")
            st.markdown("아래는 시각화를 위한 **모의 지질 데이터 레이어**입니다. 중앙의 붉은 마커가 입력하신 위치입니다.")
            
            m2 = folium.Map(location=[lat, lon], zoom_start=14)
            folium.Circle(
                radius=1500,
                location=[lat, lon],
                popup="지층 A (모의: 화강암류)",
                color="#ff9999",
                fill=True,
                fill_color="#ff9999",
                fill_opacity=0.4
            ).add_to(m2)
            folium.Marker([lat, lon], tooltip="검색 위치", icon=folium.Icon(color='red')).add_to(m2)
            render_map(m2, 400)
            
        with tab3:
            st.header("🏗️ 토지이용도 (Land Use Map)")
            st.info("💡 **실제 데이터 소스:** 환경공간정보서비스 및 AI Hub(https://aihub.or.kr/) 토지이용도 학습 데이터")
            st.markdown("아래는 시각화를 위한 **모의 토지이용 데이터 레이어**입니다.")
            
            m3 = folium.Map(location=[lat, lon], zoom_start=14)
            folium.Polygon(
                locations=[
                    [lat+0.008, lon-0.008], [lat+0.008, lon+0.008],
                    [lat-0.008, lon+0.008], [lat-0.008, lon-0.008]
                ],
                color="green",
                fill=True,
                fill_color="green",
                fill_opacity=0.3,
                popup="산림 지역 (모의 데이터)"
            ).add_to(m3)
            folium.Marker([lat, lon], tooltip="검색 위치", icon=folium.Icon(color='red')).add_to(m3)
            render_map(m3, 400)
            
        with tab4:
            st.header("🌊 수계도 (Water System Map)")
            st.info("💡 하천 및 수계망 정보를 나타내는 섹션입니다. (추후 WAMIS 등과 연동 가능)")
            st.markdown("아래는 시각화를 위한 **모의 하천 및 수계 레이어**입니다.")
            
            m4 = folium.Map(location=[lat, lon], zoom_start=14)
            folium.PolyLine(
                locations=[
                    [lat+0.015, lon-0.01], [lat+0.005, lon-0.002], [lat, lon+0.005], [lat-0.01, lon+0.01]
                ],
                color="blue",
                weight=6,
                opacity=0.6,
                tooltip="모의 주요 하천"
            ).add_to(m4)
            folium.Marker([lat, lon], tooltip="검색 위치", icon=folium.Icon(color='red')).add_to(m4)
            render_map(m4, 400)
            
        with tab5:
            st.header("🚰 주변 지하수 관정 정보")
            st.info("💡 **실제 데이터 소스:** 국가지하수정보센터(GIMS) 및 AI Hub(https://aihub.or.kr/) 지하수 수위/수질 데이터")
            st.markdown("해당 좌표 반경 내의 **모의 관정 데이터** 목록 및 지도입니다.")
            
            df_wells = generate_mock_wells(lat, lon)
            
            # 모바일 환경에서는 컬럼이 한 줄로 나오도록 st.columns 대신 위아래로 배치
            st.subheader("관정 수질 및 제원 표")
            st.dataframe(df_wells, use_container_width=True, hide_index=True)
                
            st.subheader("관정 위치")
            m5 = folium.Map(location=[lat, lon], zoom_start=14)
            folium.Marker([lat, lon], tooltip="중심 검색 위치", icon=folium.Icon(color='red', icon='star')).add_to(m5)
            
            for idx, row in df_wells.iterrows():
                popup_html = f"""
                <div style='width: 150px;'>
                    <b>{row['관정명']}</b><br>
                    - 심도: {row['심도(m)']}m<br>
                    - 수위: {row['수위(m)']}m<br>
                    - pH: {row['pH']}<br>
                    - EC: {row['EC(µS/cm)']} µS/cm
                </div>
                """
                folium.Marker(
                    [row['위도'], row['경도']],
                    tooltip=row['관정명'],
                    popup=folium.Popup(popup_html, max_width=200),
                    icon=folium.Icon(color='blue', icon='tint')
                ).add_to(m5)
                
            render_map(m5, 400)
            
    else:
        st.error("해당 주소를 좌표로 변환할 수 없습니다. 올바른 도로명 주소를 입력해주세요.")
