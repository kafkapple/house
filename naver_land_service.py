"""네이버 부동산 서비스 통합 모듈"""
import requests
import streamlit as st
import logging
import json
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
from config_loader import load_config
import plotly.express as px
import pandas as pd

class NaverLandService:
    def __init__(self, headers: Dict, cookies: Dict, variables: Dict):
        self.organized_data = {}
        self.complex_info = None
        self.unit_types = []
        self.debug_logs = []
        self.raw_response = None
        self.headers = headers
        self.cookies = cookies
        self.variables = variables

    def _fetch_data(self, complex_id: str) -> Dict:
        self.debug_logs = []
        self.raw_response = None
        response = None
        
        try:
            print(f"[DEBUG] API 호출: {complex_id}")
            
            url = f"https://new.land.naver.com/api/complexes/{complex_id}"
            
            # API 호출 시도
            try:
                response = requests.get(url, headers=self.headers, cookies=self.cookies)
                print(f"[DEBUG] 응답 상태: {response.status_code}")
                
                if response.status_code != 200:
                    print(f"[ERROR] API 응답 오류: {response.status_code}")
                    return self.organized_data
                    
                raw_data = response.json()
                self.raw_response = raw_data
                
                # variables.yaml에 정의된 변수 구조에 따라 데이터 파싱
                parsed_data = self._parse_complex_info(raw_data)
                self.complex_info = parsed_data['complex_info']
                self.unit_types = parsed_data['unit_types']
                
                return raw_data
                
            except requests.exceptions.RequestException as req_error:
                print(f"[ERROR] 요청 오류: {str(req_error)}")
                return self.organized_data
                
        except Exception as e:
            print(f"[ERROR] 처리 오류: {str(e)}")
            return self.organized_data

    def _parse_complex_info(self, data: Dict) -> Dict:
        """아파트 단지 정보를 파싱합니다."""
        complex_detail = data.get('complexDetail', {})
        pyeong_details = data.get('complexPyeongDetailList', [])
        
        # Parse complex info
        complex_info = {
            'name': complex_detail.get('complexName'),
            'address': {
                'road': complex_detail.get('roadAddress'),
                'jibun': complex_detail.get('address')
            },
            'stats': {
                'total_units': complex_detail.get('totalHouseholdCount'),
                'total_buildings': complex_detail.get('totalDongCount')
            },
            'current_articles': {
                'sales': complex_detail.get('dealCount', 0),
                'lease': complex_detail.get('leaseCount', 0),
                'rent': complex_detail.get('rentCount', 0)
            }
        }
        
        # Parse unit types with maintenance costs
        unit_types = []
        for pyeong in pyeong_details:
            # 관리비 리스트 파싱
            maintenance_cost_list = pyeong.get('maintenanceCostList', [])
            
            # 평균 관리비 정보
            avg_maintenance = pyeong.get('averageMaintenanceCost', {})
            
            # 매물 통계 정보
            article_stats = pyeong.get('articleStatistics', {})
            
            unit_info = {
                'size': {
                    'supply_area': pyeong.get('supplyArea'),
                    'exclusive_area': pyeong.get('exclusiveArea'),
                    'exclusive_rate': pyeong.get('exclusiveRate')
                },
                'layout': {
                    'rooms': pyeong.get('roomCnt'),
                    'bathrooms': pyeong.get('bathroomCnt'),
                    'structure': pyeong.get('entranceType')
                },
                'maintenance_cost_list': maintenance_cost_list,
                'maintenance_fee': {
                    'average': avg_maintenance.get('averageTotalPrice', '0'),
                    'summer': avg_maintenance.get('summerTotalPrice', '0'),
                    'winter': avg_maintenance.get('winterTotalPrice', '0')
                },
                'price': {
                    'sales': article_stats.get('dealPriceString', '정보없음'),
                    'lease': article_stats.get('leasePriceString', '정보없음'),
                    'rent': article_stats.get('rentPriceString', '정보없음'),
                    'sales_count': article_stats.get('dealCount', 0),
                    'lease_count': article_stats.get('leaseCount', 0),
                    'rent_count': article_stats.get('rentCount', 0)
                }
            }
            unit_types.append(unit_info)
            
            # 디버그 로그 추가
            self.debug_logs.append(f"[DEBUG] 파싱된 평형: {unit_info['size']['supply_area']}㎡")
            self.debug_logs.append(f"[DEBUG] 관리비 데이터 개수: {len(maintenance_cost_list)}")
        
        return {
            'complex_info': complex_info,
            'unit_types': unit_types
        }

    def _organize_complex_data(self, raw_data: Dict) -> Dict:
        """수집된 데이터를 구조화합니다."""
        try:
            print(f"\n[DEBUG] 구조화 시작 - 입력 데이터: {raw_data}")
            
            if not raw_data:
                print("[ERROR] 빈 데이터가 전달되었습니다.")
                return self.organized_data
            
            if 'status' in raw_data:
                print(f"[DEBUG] API 응답 상태: {raw_data['status']}")
            
            if 'error' in raw_data:
                print(f"[ERROR] API 에러 응답: {raw_data['error']}")
                return self.organized_data

            if 'overview' not in raw_data:
                print("[ERROR] overview 데이터가 없습니다.")
                print(f"[DEBUG] 사용 가능한 키: {raw_data.keys()}")
                print(f"[DEBUG] 전체 응답 데이터: {raw_data}")
                return self.organized_data

            overview = raw_data['overview']
            logging.debug(f"overview 데이터 키: {overview.keys()}")
            
            # 1. 단지 기본 정보
            if 'complexDetail' in overview:
                self.organized_data['complex_info'] = self._extract_complex_info(overview['complexDetail'])
                logging.info("단지 기본 정보 추출 완료")
            else:
                logging.warning("complexDetail 정보가 없습니다.")
            
            # 2. 평형별 정보
            if 'complexPyeongDetailList' in overview:
                self.organized_data['area_details'] = self._extract_area_details(overview['complexPyeongDetailList'])
                logging.info("평형별 정보 추출 완료")
            else:
                logging.warning("complexPyeongDetailList 정보가 없습니다.")
            
            # 3. 현재 매물 정보
            if 'articles' in overview and 'articleList' in overview['articles']:
                self.organized_data['current_articles'] = self._extract_articles(overview['articles']['articleList'])
                logging.info("현재 매물 정보 추출 완료")
            else:
                logging.warning("매물 정보가 없습니다.")
            
            logging.info("데이터 구조화 완료")
            logging.debug(f"최종 구조화 데이터 키: {self.organized_data.keys()}")
            
            return self.organized_data
            
        except Exception as e:
            logging.error(f"데이터 구조화 실패: {str(e)}", exc_info=True)
            return self.organized_data

    def _extract_complex_info(self, detail: Dict) -> Dict:
        """단지 기본 정보를 추출합니다."""
        try:
            return {
                'name': detail.get('complexName', '정보없음'),
                'address': {
                    'road': detail.get('roadAddress', ''),
                    'jibun': detail.get('address', ''),
                    'detail': detail.get('detailAddress', '')
                },
                'size': {
                    'total_dong': detail.get('totalDongCount', 0),
                    'total_households': detail.get('totalHouseholdCount', 0),
                    'max_floor': detail.get('highFloor', 0),
                    'min_floor': detail.get('lowFloor', 0)
                },
                'construction': {
                    'company': detail.get('constructionCompanyName', '정보없음'),
                    'approve_date': detail.get('useApproveYmd', '')
                },
                'facility': {
                    'parking_count': detail.get('parkingPossibleCount', 0),
                    'parking_per_household': detail.get('parkingCountByHousehold', 0),
                    'heating_method': detail.get('heatMethodTypeCode', ''),
                    'heating_fuel': detail.get('heatFuelTypeCode', '')
                }
            }
        except Exception as e:
            logging.error(f"단지 정보 추출 실패: {str(e)}")
            return {}
        
    def display_complex_info(self):
        """단지 정보를 탭으로 표시합니다."""
        if not self.complex_info:
            st.error("단지 정보를 가져오는데 실패했습니다.")
            return
        
        # Create tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "주요정보", 
            "관리비 추이", 
            "평형정보",
            "디버그 정보"
        ])
        
        with tab1:
            # 기본 정보 표시
            st.subheader("🏢 단지 개요")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # 현재 매물 현황
                st.metric(
                    "매매 매물", 
                    f"{self.complex_info['current_articles']['sales']}건",
                    delta=None
                )
            with col2:
                st.metric(
                    "전세 매물",
                    f"{self.complex_info['current_articles']['lease']}건",
                    delta=None
                )
            with col3:
                st.metric(
                    "월세 매물",
                    f"{self.complex_info['current_articles']['rent']}건",
                    delta=None
                )
        
        with tab2:
            for unit in self.unit_types:
                st.subheader(f"📊 {unit['size']['supply_area']}㎡ 관리비 추이")
                
                # 관리비 데이터 준비
                maintenance_data = []
                for cost in unit.get('maintenance_cost_list', []):
                    date = datetime.strptime(cost['basisYearMonth'], '%Y%m')
                    maintenance_data.append({
                        'date': date,
                        'cost': int(cost['totalPrice'])
                    })
                
                if maintenance_data:
                    df = pd.DataFrame(maintenance_data)
                    
                    # 관리비 추이 그래프
                    fig = px.line(df, x='date', y='cost',
                                title=f'{unit["size"]["supply_area"]}㎡ 월별 관리비',
                                labels={'date': '날짜', 'cost': '관리비(원)'})
                    fig.update_layout(showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 관리비 통계
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(
                            "평균 관리비",
                            f"{int(unit['maintenance_fee']['average']):,}원"
                        )
                    with col2:
                        st.metric(
                            "여름철 평균",
                            f"{int(unit['maintenance_fee']['summer']):,}원"
                        )
                    with col3:
                        st.metric(
                            "겨울철 평균",
                            f"{int(unit['maintenance_fee']['winter']):,}원"
                        )
        
        with tab3:
            for unit in self.unit_types:
                with st.expander(f"🏠 {unit['size']['supply_area']}㎡ 상세정보"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("📐 면적 정보")
                        st.write(f"- 공급면적: {unit['size']['supply_area']}㎡")
                        st.write(f"- 전용면적: {unit['size']['exclusive_area']}㎡")
                        st.write(f"- 전용률: {unit['size']['exclusive_rate']}%")
                    
                    with col2:
                        st.write("🚪 구조 정보")
                        st.write(f"- 방 개수: {unit['layout']['rooms']}개")
                        st.write(f"- 화장실: {unit['layout']['bathrooms']}개")
                        st.write(f"- 현관구조: {unit['layout']['structure']}")
                    
                    st.write("💰 거래 정보")
                    price_cols = st.columns(3)
                    with price_cols[0]:
                        st.metric("매매가", unit['price']['sales'])
                    with price_cols[1]:
                        st.metric("전세가", unit['price']['lease'])
                    with price_cols[2]:
                        st.metric("월세", unit['price']['rent'])
        
        with tab4:
            st.subheader("🔍 디버그 정보")
            if st.checkbox("원본 데이터 보기"):
                st.json(self.raw_response)
        
    def create_complex_tabs(self, parsed_data):
        """
        # Create tabbed view for complex information
        """
        tabs = {
            '단지정보': {
                '기본정보': parsed_data['complex_info'],
                '시설정보': {
                    '주차': f"세대당 {parsed_data['complex_info']['stats']['parking_ratio']}대",
                    '난방': "개별난방",  # From heatMethodTypeCode
                    '관리실': parsed_data['complex_info'].get('managementOfficeTelNo')
                }
            },
            '평형정보': {
                f"{unit['size']['supply_area']}㎡": {
                    '전용면적': f"{unit['size']['exclusive_area']}㎡",
                    '방/욕실': f"{unit['layout']['rooms']}/{unit['layout']['bathrooms']}",
                    '현관구조': unit['layout']['structure'],
                    '매매가': unit['price']['sales'],
                    '전세가': unit['price']['lease'],
                    '월세': unit['price']['rent']
                } for unit in parsed_data['unit_types']
            },
            '관리비정보': {
                f"{unit['size']['supply_area']}㎡": {
                    '평균': f"{int(unit['maintenance_fee']['average']):,}원",
                    '여름': f"{int(unit['maintenance_fee']['summer']):,}원",
                    '겨울': f"{int(unit['maintenance_fee']['winter']):,}원"
                } for unit in parsed_data['unit_types']
            }
        }
        
        return tabs
        