import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
import folium
from streamlit_folium import st_folium
import random

# 페이지 설정
st.set_page_config(page_title="지하수 수질 연구 대시보드", layout="wide", page_icon="💧")

# 시원한 테마 CSS (전체적인 배경과 탭 스타일 개선)
st.markdown("""
<style>
    /* 전체 배경색 */
    .stApp {
        background-color: #f0f8ff;
    }
    
    /* 사이드바 배경색 */
    [data-testid="stSidebar"] {
        background-color: #e0f7fa;
    }
    
    /* 제목 및 헤더 색상 변경 */
    h1, h2, h3 {
        color: #005f73 !important;
        font-family: 'Malgun Gothic', sans-serif;
    }
    
    /* 탭 스타일 개선 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #e0f7fa;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
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
</style>
""", unsafe_allow_html=True)

st.title("💧 지하수 수질 연구 통합 대시보드")
st.markdown("**입력한 도로명 주소**를 중심으로 지질도, 토지이용도, 수계도 및 지하수 관정 정보를 종합적으로 제공합니다.")

# 사이드바 구성
st.sidebar.header("🔍 검색 옵션")
address = st.sidebar.text_input("대한민국 도로명 주소 입력", value="대전광역시 유성구 과학로 124")

@st.cache_data
def get_coordinates(addr):
    """geopy를 활용하여 주소를 위도, 경도로 변환합니다. 실패 시 점진적으로 주소를 줄여 검색합니다."""
    # 흔히 입력하는 띄어쓰기 교정 (Nominatim 인식률 향상)
    addr_query = addr.replace(" 광역시", "광역시").replace(" 특별시", "특별시").replace(" 도 ", "도 ")
    
    geolocator = Nominatim(user_agent="korea_groundwater_research_app")
    parts = addr_query.split()
    
    # 뒷부분부터 하나씩 단어를 지워가며 검색 (상세 주소가 없을 경우를 대비한 Fallback)
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
        # 반경 약 1km 내외로 랜덤 생성
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

if address:
    with st.spinner("주소 좌표를 변환 중입니다..."):
        lat, lon, is_exact, matched_addr = get_coordinates(address)
    
    if lat and lon:
        if not is_exact:
            st.sidebar.warning(f"상세 주소를 찾을 수 없어 인근 지역('{matched_addr}')의 좌표로 대체합니다. (OpenStreetMap 한계)")
        else:
            st.sidebar.success(f"위치 확인 완료!\n- 위도: {lat:.4f}\n- 경도: {lon:.4f}")
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📍 기본 정보", "🌍 지질도", "🏗️ 토지이용도", "🌊 수계도", "🚰 지하수 관정 정보"])
        
        with tab1:
            st.header("📍 검색 위치 정보")
            col1, col2 = st.columns([1, 2])
            with col1:
                st.info(f"**입력 주소:** {address}")
                st.write(f"**위도 (Latitude):** {lat:.6f}")
                st.write(f"**경도 (Longitude):** {lon:.6f}")
            with col2:
                m1 = folium.Map(location=[lat, lon], zoom_start=15)
                folium.Marker(
                    [lat, lon], 
                    tooltip="검색된 위치", 
                    icon=folium.Icon(color='red', icon='info-sign')
                ).add_to(m1)
                st_folium(m1, width="100%", height=300)
            
        with tab2:
            st.header("🌍 지질도 (Geological Map)")
            st.info("💡 **실제 데이터 소스:** 국가지질자원데이터센터(KIGAM) 및 AI Hub(https://aihub.or.kr/) 지질/수질 데이터")
            st.markdown("아래는 시각화를 위한 **모의 지질 데이터 레이어**입니다. 중앙의 붉은 마커가 입력하신 위치입니다.")
            
            m2 = folium.Map(location=[lat, lon], zoom_start=14)
            # 모의 지질 폴리곤 (주변 층)
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
            st_folium(m2, width="100%", height=500)
            
        with tab3:
            st.header("🏗️ 토지이용도 (Land Use Map)")
            st.info("💡 **실제 데이터 소스:** 환경공간정보서비스 및 AI Hub(https://aihub.or.kr/) 토지이용도 학습 데이터")
            st.markdown("아래는 시각화를 위한 **모의 토지이용 데이터 레이어**입니다.")
            
            m3 = folium.Map(location=[lat, lon], zoom_start=14)
            # 모의 토지이용 폴리곤 (사각형)
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
            st_folium(m3, width="100%", height=500)
            
        with tab4:
            st.header("🌊 수계도 (Water System Map)")
            st.info("💡 하천 및 수계망 정보를 나타내는 섹션입니다. (추후 WAMIS 등과 연동 가능)")
            st.markdown("아래는 시각화를 위한 **모의 하천 및 수계 레이어**입니다.")
            
            m4 = folium.Map(location=[lat, lon], zoom_start=14)
            # 모의 수계선 (하천)
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
            st_folium(m4, width="100%", height=500)
            
        with tab5:
            st.header("🚰 주변 지하수 관정 정보")
            st.info("💡 **실제 데이터 소스:** 국가지하수정보센터(GIMS) 및 AI Hub(https://aihub.or.kr/) 지하수 수위/수질 데이터")
            st.markdown("해당 좌표 반경 내의 **모의 관정 데이터** 목록 및 지도입니다. 표와 지도 마커를 확인하세요.")
            
            df_wells = generate_mock_wells(lat, lon)
            
            col_table, col_map = st.columns(2)
            
            with col_table:
                st.subheader("관정 수질 및 제원 표")
                st.dataframe(df_wells, use_container_width=True, hide_index=True)
                
            with col_map:
                st.subheader("관정 위치")
                m5 = folium.Map(location=[lat, lon], zoom_start=14)
                folium.Marker([lat, lon], tooltip="중심 검색 위치", icon=folium.Icon(color='red', icon='star')).add_to(m5)
                
                # 관정 마커 추가
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
                    
                st_folium(m5, width="100%", height=400)
            
    else:
        st.error("해당 주소를 좌표로 변환할 수 없습니다. 올바른 도로명 주소를 입력해주세요.")
