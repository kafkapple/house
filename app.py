import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import requests
from typing import Dict, List, Optional, Tuple, Union
import logging
from pathlib import Path
import sys
import os
import yaml

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 현재 스크립트의 디렉토리를 파이썬 패스에 추가
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from naver_land_service import NaverLandService

def load_yaml_config(file_name: str) -> Optional[Dict]:
    """YAML 설정 파일을 로드합니다."""
    try:
        config_path = Path(__file__).parent / 'config' / file_name
        logger.debug(f"설정 파일 로드 시도: {config_path}")
        
        if not config_path.exists():
            logger.error(f"설정 파일이 없습니다: {config_path}")
            return None
            
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            logger.debug(f"설정 파일 로드 성공: {file_name}")
            return config
    except Exception as e:
        logger.error(f"설정 파일 로드 중 오류 발생: {str(e)}")
        return None

def main():
    st.set_page_config(page_title="부동산 데이터 분석", page_icon="🏢", layout="wide")
    
    # 디버그 로그를 저장할 리스트
    if 'debug_logs' not in st.session_state:
        st.session_state.debug_logs = []
    
    def add_log(message: str):
        st.session_state.debug_logs.append(message)
        logger.debug(message)

    # 설정 로드
    add_log("설정 파일 로드 시작")
    
    headers = load_yaml_config('headers.yaml') or {}
    cookies = load_yaml_config('cookies.yaml') or {}
    apartments = load_yaml_config('apartments.yaml') or {}
    variables = load_yaml_config('variables.yaml') or {}
    
    configs = {
        'headers': headers,
        'cookies': cookies,
        'apartments': apartments,
        'variables': variables
    }
    
    add_log(f"로드된 설정: {list(configs.keys())}")

    # UI 구성
    st.title("부동산 데이터 분석 대시보드")
    
    # 탭 생성
    tab1, tab2, tab3, tab4 = st.tabs(["기본정보", "상세정보", "분석", "디버그"])
    
    with tab4:
        st.subheader("디버그 로그")
        for log in st.session_state.debug_logs:
            st.text(log)
        
        st.subheader("설정 정보")
        if st.checkbox("설정 파일 내용 보기"):
            st.json(configs)

    # 사이드바 설정
    st.sidebar.title("검색 설정")
    
    # 아파트 선택 드롭다운
    apartment_list = apartments.get('apartment_list', {})
    if apartment_list:
        selected_apt = st.sidebar.selectbox(
            "아파트 선택",
            options=list(apartment_list.keys()),
            format_func=lambda x: x
        )
        
        if selected_apt:
            complex_id = apartment_list.get(selected_apt)
            add_log(f"선택된 아파트: {selected_apt} (ID: {complex_id})")
            
            try:
                # NaverLandService 초기화
                service = NaverLandService(
                    headers=headers,
                    cookies=cookies.get('cookies', {}),
                    variables=variables.get('variables', {})
                )
                
                # 데이터 가져오기
                data = service._fetch_data(complex_id)
                
                if data:
                    with tab1:
                        service.display_complex_info()
                else:
                    st.error("데이터를 가져오지 못했습니다.")
                    
            except Exception as e:
                error_msg = f"처리 중 오류 발생: {str(e)}"
                add_log(error_msg)
                st.error(error_msg)
    else:
        st.sidebar.error("아파트 목록을 불러올 수 없습니다.")

if __name__ == "__main__":
    main() 