import json
import time
import requests
import pandas as pd
from typing import List, Dict, Optional
from tqdm import tqdm
from difflib import SequenceMatcher
import os
class NaverLandCrawler:
    def __init__(self, auth_token: str):
        """Initialize crawler with auth token"""
        self.base_url = "https://new.land.naver.com/api"
        self.auth_token = auth_token
        
    def _get_headers(self, apt_code: str = '6372') -> Dict:
        """Get request headers"""
        headers = {
            "Accept-Encoding": "gzip",
            "Host": "new.land.naver.com",
            'authorization': f'Bearer {self.auth_token}',
            'referer': f'https://new.land.naver.com/complexes/{apt_code}?ms=36.321777,127.40236,17&a=APT&e=RETAIL',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        }
        return headers

    def _make_request(self, endpoint: str, params: Optional[Dict] = None, apt_code: Optional[str] = None) -> Dict:
        """Make API request with retry logic"""
        url = f"{self.base_url}/{endpoint}"
        max_retries = 3
        delay = 1

        for attempt in range(max_retries):
            try:
                headers = self._get_headers(apt_code) if apt_code else self._get_headers()
                response = requests.get(
                    url, 
                    data=params or {"sameAddressGroup": "false"}, 
                    headers=headers,
                    timeout=10
                )
                response.encoding = "utf-8-sig"
                
                if not response.text:
                    raise ValueError("Empty response received")
                
                return json.loads(response.text)
            
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {str(e)}")
                print(f"URL: {url}")
                if attempt == max_retries - 1:
                    print(f"Error making request to {endpoint}: {str(e)}")
                    return {}
                time.sleep(delay)
                delay *= 2

    def get_region_codes(self, parent_code: str = "0000000000") -> List[str]:
        """
        Get region codes (sido/gungu/dong)
        Args:
            parent_code: 상위 지역 코드
                - "0000000000": 전국 시/도 목록
                - "1100000000": 서울시 구/군 목록
                - "3000000000": 대전시 구/군 목록
                등...
        Returns:
            List of region codes
        """
        try:
            endpoint = f"regions/list?cortarNo={parent_code}"
            data = self._make_request(endpoint)
            
            if not data or 'regionList' not in data:
                print(f"Warning: No data found for parent_code: {parent_code}")
                return []
            
            regions_df = pd.DataFrame(data.get("regionList", []))
            if regions_df.empty:
                return []
            
            # 디버깅을 위한 지역 정보 출력
            if parent_code == "0000000000":  # 시/도 목록 조회시
                for _, row in regions_df.iterrows():
                    print(f"Found region: {row['cortarName']} ({row['cortarNo']})")
                
            return list(regions_df["cortarNo"])
            
        except Exception as e:
            print(f"Error getting region codes for parent_code {parent_code}: {str(e)}")
            return []

    def get_apt_list(self, dong_code: str) -> List[str]:
        """Get apartment codes for a dong"""
        try:
            endpoint = f"regions/complexes?cortarNo={dong_code}&realEstateType=APT&order="
            response = self._make_request(endpoint)
            
            if not response:
                print(f"Warning: No data received for dong_code: {dong_code}")
                return []
            
            if 'complexList' not in response:
                print(f"Warning: No complexList in response for dong_code: {dong_code}")
                return []
            
            apt_list = pd.DataFrame(response.get('complexList', []))
            if apt_list.empty:
                # print(f"Info: No apartments found in dong_code: {dong_code}")
                return []
            
            return list(apt_list["complexNo"])
        
        except Exception as e:
            print(f"Error getting apartment list for dong_code: {dong_code}")
            print(f"Error details: {str(e)}")
            print(f"Response: {response if 'response' in locals() else 'No response'}")
            return []

    def get_apt_info(self, apt_code: str) -> Dict:
        """Get apartment details"""
        endpoint = f"complexes/{apt_code}?sameAddressGroup=false"
        return self._make_request(endpoint, apt_code=apt_code)

    def get_school_info(self, apt_code: str) -> Dict:
        """Get school information"""
        endpoint = f"complexes/{apt_code}/schools"
        return self._make_request(endpoint, apt_code=apt_code)

    def get_price_info(self, apt_code: str, area_no: str) -> Dict:
        """Get price information"""
        return self._make_request(
            f"complexes/{apt_code}/prices",
            {
                "complexNo": apt_code,
                "tradeType": "A1",
                "year": "5",
                "priceChartChange": "true",
                "areaNo": area_no,
                "areaChange": "true",
                "type": "table"
            }
        )

    def process_apt_data(self, apt_code: str) -> Optional[pd.DataFrame]:
        """Process apartment data into DataFrame"""
        try:
            apt_info = self.get_apt_info(apt_code)
            school_info = self.get_school_info(apt_code)
            
            # Get area list
            try:
                area_list = apt_info["complexDetail"]["pyoengNames"].split(", ")
                ex_flag=1
            except KeyError:
                ex_flag=0
                print('Error')
                temp_data=pd.DataFrame(columns=temp_data.columns)
            if ex_flag==1:
                temp_data=pd.DataFrame(index=range(len(area_list)))
                # Process data for each area
                rows = []
                for i, area in enumerate(area_list):
                    row = self._extract_apt_info(apt_info, school_info, i, area, apt_code)
                    rows.append(row)
                    
            return pd.DataFrame(rows)
        except Exception as e:
            print(f"Error processing apt {apt_code}: {str(e)}")
            return None

    def _extract_apt_info(self, apt_info: Dict, school_info: Dict, 
                         area_idx: int, area: str, apt_code: str) -> Dict:
 
        """Extract apartment information for a specific area"""
        data = {
            "아파트명": self._safe_get(apt_info, ["complexDetail", "complexName"]),
            "거래 수": self._safe_get(apt_info, ["complexDetail", "dealCount"]),
            "전세 거래 수": self._safe_get(apt_info, ["complexDetail", "leaseCount"]),
            "월세 거래 수": self._safe_get(apt_info, ["complexDetail", "rentCount"]),
            "단기 전세 거래 수": self._safe_get(apt_info, ["complexDetail", "shortTermLeaseCount"]),
            "용적률": self._safe_get(apt_info, ["complexDetail", "batlRatio"]),
            "건폐율": self._safe_get(apt_info, ["complexDetail", "btlRatio"]),
            "주차대수": self._safe_get(apt_info, ["complexDetail", "parkingPossibleCount"]),
            "난방": self._safe_get(apt_info, ["complexDetail", "heatMethodTypeCode"]),
            "건설사": self._safe_get(apt_info, ["complexDetail", "constructionCompanyName"]),
            "면적": area,
            "법정동주소": f"{self._safe_get(apt_info, ['complexDetail', 'address'])} {self._safe_get(apt_info, ['complexDetail', 'detailAddress'])}",
            "도로명주소": f"{self._safe_get(apt_info, ['complexDetail', 'roadAddressPrefix'])} {self._safe_get(apt_info, ['complexDetail', 'roadAddress'])}",
            "세대수": self._safe_get(apt_info, ["complexDetail", "totalHouseholdCount"]),
            "임대세대수": self._safe_get(apt_info, ["complexDetail", "totalLeaseHouseholdCount"]),
            "최고층": self._safe_get(apt_info, ["complexDetail", "highFloor"]),
            "최저층": self._safe_get(apt_info, ["complexDetail", "lowFloor"]),
            "latitude": self._safe_get(apt_info, ["complexDetail", "latitude"]),
            "longitude": self._safe_get(apt_info, ["complexDetail", "longitude"]),
        }
        try:
            
            
            data.update({
                "공급면적": self._safe_get(apt_info, ["complexPyeongDetailList", area_idx, "supplyArea"]),
                "전용면적": self._safe_get(apt_info, ["complexPyeongDetailList", area_idx, "exclusiveArea"]),
                "전용율": self._safe_get(apt_info, ["complexPyeongDetailList", area_idx, "exclusiveRate"]),
                "방수": self._safe_get(apt_info, ["complexPyeongDetailList", area_idx, "roomCnt"]),
                "욕실": self._safe_get(apt_info, ["complexPyeongDetailList", area_idx, "bathroomCnt"]),
                "해당면적_세대수": self._safe_get(apt_info, ["complexPyeongDetailList", area_idx, "householdCountByPyeong"]),
                "현관구조": self._safe_get(apt_info, ["complexPyeongDetailList", area_idx, "entranceType"]),
                "재산세": self._safe_get(apt_info, ["complexPyeongDetailList", area_idx, "landPriceMaxByPtp", "landPriceTax", "propertyTax"]),
                "재산세합계": self._safe_get(apt_info, ["complexPyeongDetailList", area_idx, "landPriceMaxByPtp", "landPriceTax", "propertyTotalTax"]),
                "지방교육세": self._safe_get(apt_info, ["complexPyeongDetailList", area_idx, "landPriceMaxByPtp", "landPriceTax", "localEduTax"]),
                "재산세_도시지역분": self._safe_get(apt_info, ["complexPyeongDetailList", area_idx, "landPriceMaxByPtp", "landPriceTax", "cityAreaTax"]),
                "종합부동산세": self._safe_get(apt_info, ["complexPyeongDetailList", area_idx, "landPriceMaxByPtp", "landPriceTax", "realEstateTotalTax"]),
                "결정세액": self._safe_get(apt_info, ["complexPyeongDetailList", area_idx, "landPriceMaxByPtp", "landPriceTax", "decisionTax"]),
                "농어촌특별세": self._safe_get(apt_info, ["complexPyeongDetailList", area_idx, "landPriceMaxByPtp", "landPriceTax", "ruralSpecialTax"]),
            })
        except KeyError:
            pass

        try:
            print('Price info')
            price_info = self.get_price_info(apt_code, 0) apt_info["complexDetail"])["cortarNo"])
            data.update({
                "일반평균가": self._safe_get(price_info, ["marketPrices", 0, "dealAveragePrice"]),
                "일반평균가변화량": self._safe_get(price_info, ["marketPrices", 0, "dealAveragePriceChangeAmount"]),
                "하위평균가": self._safe_get(price_info, ["marketPrices", 0, "dealLowPriceLimit"]),
                "상위평균가": self._safe_get(price_info, ["marketPrices", 0, "dealUpperPriceLimit"]),
                "전세 일반평균가": self._safe_get(price_info, ["marketPrices", 0, "leaseAveragePrice"]),
                "전세 일반평균가변화량": self._safe_get(price_info, ["marketPrices", 0, "leaseAveragePriceChangeAmount"]),
                "전세 상위평균가": self._safe_get(price_info, ["marketPrices", 0, "leaseUpperPriceLimit"]),
                "전세 하위평균가": self._safe_get(price_info, ["marketPrices", 0, "lowPriceLimit"]),
                "매매가대비전세가": self._safe_get(price_info, ["marketPrices", 0, "leasePerDealRate"]),
                "보증금": self._safe_get(price_info, ["marketPrices", 0, "deposit"]),
            })
        except KeyError:
            pass

        try:
            data.update({
                "겨울관리비": self._safe_get(price_info, ["complexPyeongDetailList", area_idx, "averageMaintenanceCost", "winterTotalPrice"]),
                "여름관리비": self._safe_get(price_info, ["complexPyeongDetailList", area_idx, "averageMaintenanceCost", "summerTotalPrice"]),
                "매매호가": self._safe_get(price_info, ["complexPyeongDetailList", area_idx, "articleStatistics", "dealPriceString"]),
                "전세호가": self._safe_get(price_info, ["complexPyeongDetailList", area_idx, "articleStatistics", "leasePriceString"]),
                "월세호가": self._safe_get(price_info, ["complexPyeongDetailList", area_idx, "articleStatistics", "rentPriceString"]),
                "실거래가": self._safe_get(price_info, ["complexPyeongDetailList", area_idx, "articleStatistics", "rentPriceString"]),
            })
        except KeyError:
            pass

        # Add school information
        try:
            data.update({
                "등학교_학군정보": school_info['schools'][0]["schoolName"],
                "초등학교_설립정보": school_info['schools'][0]["organizationType"],
                "초등학교_남학생수": school_info['schools'][0]["maleStudentCount"],
                "초등학교_여학생수": school_info['schools'][0]["femaleStudentCount"]
            })
        except (KeyError, IndexError):
            pass
            
        return data

    @staticmethod
    def _safe_get(data: Dict, keys: List[str], default: str = "") -> str:
        """Safely get nested dictionary value"""
        for key in keys:
            try:
                data = data[key]
            except (KeyError, TypeError, IndexError):
                return default
        return data

    def get_region_name(self, region_code: str) -> str:
        """Get region name from code"""
        endpoint = f"regions/list?cortarNo={region_code}"
        data = self._make_request(endpoint)
        
        try:
            regions = pd.DataFrame(data.get("regionList", []))
            matching_region = regions[regions["cortarNo"] == region_code]
            if not matching_region.empty:
                return matching_region.iloc[0]["cortarName"]
        except (KeyError, AttributeError, IndexError):
            pass
        return "Unknown"

    def get_apt_name(self, apt_code: str) -> str:
        """Get apartment name from code"""
        endpoint = f"complexes/{apt_code}?sameAddressGroup=false"
        data = self._make_request(endpoint, apt_code=apt_code)
        
        try:
            return data["complexDetail"]["complexName"]
        except (KeyError, TypeError):
            return "Unknown"

    def collect_all_data(self) -> None:
        """Collect all apartment data with names"""
        try:
            sido_codes = self.get_region_codes()
            if not sido_codes:
                raise ValueError("No sido codes retrieved")
            
            for sido in tqdm(sido_codes, desc="시/도"):
                sido_name = self.get_region_name(sido)
                print(f"\n시/도: {sido_name} ({sido})")
                
                gungu_codes = self.get_region_codes(sido)
                for gungu in tqdm(gungu_codes, desc="군/구"):
                    gungu_name = self.get_region_name(gungu)
                    print(f"  군/구: {gungu_name} ({gungu})")
                    
                    dong_codes = self.get_region_codes(gungu)
                    for dong in tqdm(dong_codes, desc="동"):
                        dong_name = self.get_region_name(dong)
                        print(f"    동: {dong_name} ({dong})")
                        
                        apt_codes = self.get_apt_list(dong)
                        for apt_code in tqdm(apt_codes, desc="아파트"):
                            apt_name = self.get_apt_name(apt_code)
                            print(f"      아파트: {apt_name} ({apt_code})")
                            
                            df = self.process_apt_data(apt_code)
                            if df is not None:
                                # Save individual apartment data
                                filename = f"{sido_name}_{gungu_name}_{dong_name}_{apt_name}.csv"
                                filename = "".join(c for c in filename if c.isalnum() or c in ['_', '-']).rstrip()
                                
                                df.to_csv(f"data/apartments/{filename}.csv", encoding="CP949")
                            
                            time.sleep(0.5)  # Rate limiting
                    
        except Exception as e:
            print(f"Error in data collection: {str(e)}")

    def search_region_code(self, region_name: str, city_name: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Search region code by name with city filter
        Args:
            region_name: 구/군 이름 (예: "중구")
            city_name: 시/도 이름 (예: "서울시", "대전시")
        """
        # 시/도 코드와 이름 매핑
        sido_mapping = {
            "1100000000": "서울시",
            "2600000000": "부산시",
            "2700000000": "대구시",
            "2800000000": "인천시",
            "2900000000": "광주시",
            "3000000000": "대전시",
            "3100000000": "울산시",
            "3600000000": "세종시",
            "4100000000": "경기도",
            "4200000000": "강원도",
            "4300000000": "충청북도",
            "4400000000": "충청남도",
            "4500000000": "전라북도",
            "4600000000": "전라남도",
            "4700000000": "경상북도",
            "4800000000": "경상남도",
            "5000000000": "제주도"
        }
        
        matching_regions = []
        
        # city_name으로 시도 코드 찾기
        if city_name:
            target_sido_codes = []
            normalized_city = city_name.replace("시", "").replace("도", "")
            for code, name in sido_mapping.items():
                if normalized_city in name.replace("시", "").replace("도", ""):
                    target_sido_codes.append(code)
                    print(f"Found matching city: {name} ({code})")
            
            if not target_sido_codes:
                print(f"Warning: Cannot find sido code for {city_name}")
                return []
        else:
            # city_name이 없으면 모든 시도 검색
            target_sido_codes = list(sido_mapping.keys())
        
        # 찾은 시도 코드에 대해서만 구/군 검색
        for sido in target_sido_codes:
            sido_name = sido_mapping[sido]
            sido_info = self._make_request(f"regions/list?cortarNo={sido}")
            
            try:
                regions_df = pd.DataFrame(sido_info.get("regionList", []))
                if regions_df.empty:
                    continue
                
                # 구/군 검색
                if region_name:
                    matches = regions_df[regions_df["cortarName"].str.contains(region_name, na=False)]
                    if not matches.empty:
                        for _, row in matches.iterrows():
                            matching_regions.append({
                                "code": row["cortarNo"],
                                "name": row["cortarName"],
                                "type": row["cortarType"],
                                "sido": sido_name
                            })
                else:
                    # region_name이 없으면 해당 시/도의 모든 구/군 포함
                    for _, row in regions_df.iterrows():
                        matching_regions.append({
                            "code": row["cortarNo"],
                            "name": row["cortarName"],
                            "type": row["cortarType"],
                            "sido": sido_name
                        })
                    
            except Exception as e:
                print(f"Warning: Error processing sido {sido}: {str(e)}")
                continue
        
        if not matching_regions:
            location_str = f"{city_name + ' ' if city_name else ''}{region_name if region_name else ''}"
            print(f"No matching regions found for: {location_str.strip()}")
        else:
            print(f"\nFound {len(matching_regions)} matching regions:")
            for region in matching_regions:
                print(f"- {region['sido']} {region['name']} ({region['code']})")
        
        return matching_regions

    def get_string_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity ratio between two strings"""
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

    def search_apt_by_name(self, apt_name: str, region_name: Optional[str] = None, city_name: Optional[str] = None) -> List[Dict[str, str]]:
        """Search apartment by name with improved error handling"""
        matching_apts = []
        best_match = {"similarity": 0, "apt": None}
        search_term = apt_name.lower().replace(" ", "")
        
        # 지역 코드 가져오기
        try:
            if city_name or region_name:
                matching_regions = self.search_region_code(region_name, city_name)
                if not matching_regions:
                    location_str = f"{city_name or ''} {region_name or ''}"
                    print(f"'{location_str.strip()}' 지역을 찾을 수 없습니다.")
                    return []
                region_codes = [region['code'] for region in matching_regions]
            else:
                sido_codes = self.get_region_codes()
                region_codes = []
                for sido in sido_codes:
                    gungu_codes = self.get_region_codes(sido)
                    region_codes.extend(gungu_codes)

            # 각 지역에서 아파트 검색
            for code in tqdm(region_codes, desc="지역 검색중"):
                try:
                    dong_codes = self.get_region_codes(code)
                    for dong in dong_codes:
                        apt_list = self.get_apt_list(dong)
                        if not apt_list:  # 빈 리스트면 다음 동으로 진행
                            continue
                        
                        for apt_code in apt_list:
                            try:
                                apt_info = self.get_apt_info(apt_code)
                                if not apt_info or 'complexDetail' not in apt_info:
                                    continue
                                
                                current_apt_name = apt_info["complexDetail"]["complexName"]
                                normalized_name = current_apt_name.lower().replace(" ", "")
                                
                                # 기본 문자열 매칭으로 1차 필터링
                                if search_term in normalized_name or normalized_name in search_term:
                                    similarity = self.get_string_similarity(search_term, normalized_name)
                                    if similarity > best_match["similarity"]:
                                        best_match = {
                                            "similarity": similarity,
                                            "apt": {
                                                "code": apt_code,
                                                "name": current_apt_name,
                                                "address": apt_info["complexDetail"]["address"],
                                                "total_households": apt_info["complexDetail"].get("totalHouseholdCount", "N/A"),
                                                "construction_year": apt_info["complexDetail"].get("constructionYear", "N/A"),
                                                "similarity": similarity
                                            }
                                        }
                                        print(f"\n새로운 매칭 발견! (유사도: {similarity:.2%})")
                                        print(f"아파트명: {current_apt_name}")
                                        print(f"주소: {apt_info['complexDetail']['address']}")
                                        
                                        if similarity > 0.9:  # 매우 높은 유사도
                                            matching_apts.append(best_match["apt"])
                                            return matching_apts
                                            
                            except Exception as e:
                                print(f"Warning: Error processing apartment {apt_code}: {str(e)}")
                                continue
                            
                except Exception as e:
                    print(f"Warning: Error processing region {code}: {str(e)}")
                    continue
                
        except Exception as e:
            print(f"Error in apartment search: {str(e)}")
            return []
        
        if best_match["apt"] and best_match["similarity"] > 0.3:
            matching_apts.append(best_match["apt"])
        
        return matching_apts

    def collect_region_data(self, region_code: str) -> None:
        """Collect data for specific region"""
        try:
            region_name = self.get_region_name(region_code)
            print(f"수집 지역: {region_name} ({region_code})")
            
            # Get apartment list for the region
            apt_codes = []
            dong_codes = self.get_region_codes(region_code)
            
            for dong in tqdm(dong_codes, desc="동 검색중"):
                apt_codes.extend(self.get_apt_list(dong))
            
            # Collect data for each apartment
            for apt_code in tqdm(apt_codes, desc="아파트 데이터 수집중"):
                apt_name = self.get_apt_name(apt_code)
                print(f"  아파트: {apt_name} ({apt_code})")
                
                df = self.process_apt_data(apt_code)
                if df is not None:
                    filename = f"{region_name}_{apt_name}.csv"
                    filename = "".join(c for c in filename if c.isalnum() or c in ['_', '-']).rstrip()
                    df.to_csv(f"data/apartments/{filename}.csv", encoding="CP949")
                
                time.sleep(0.5)
                
        except Exception as e:
            print(f"Error collecting region data: {str(e)}")

    def collect_apt_data(self, apt_code: str) -> None:
        """Collect data for specific apartment"""
        try:
            apt_name = self.get_apt_name(apt_code)
            print(f"아파트: {apt_name} ({apt_code})")
            
            df = self.process_apt_data(apt_code)
            if df is not None:
                filename = f"{apt_name}.csv"
                filename = "".join(c for c in filename if c.isalnum() or c in ['_', '-']).rstrip()
                df.to_csv(f"data/apartments/{filename}.csv", encoding="CP949")
                print(f"데이터 저장 완료: {filename}")
                
        except Exception as e:
            print(f"Error collecting apartment data: {str(e)}")

    def search_and_collect_apt_data(self, apt_name: str, region_name: Optional[str] = None, city_name: Optional[str] = None) -> None:
        """
        아파트 검색 및 데이터 수집 통합 함수
        Args:
            apt_name: 아파트 이름 (예: "현대아파트")
            region_name: 구/군 이름 (예: "중구"), Optional
            city_name: 시/도 이름 (예: "서울시", "대전시"), Optional
        """
        # 시/도 코드 매핑 (필요한 경우 추가)
        city_codes = {
            "서울시": "1100000000",
            "대전시": "3000000000",
            "부산시": "2600000000",
            "대구시": "2700000000",
            "인천시": "2800000000",
            "광주시": "2900000000",
            "울산시": "3100000000",
            "세종시": "3600000000",
            "경기도": "4100000000",
            "강원도": "4200000000",
            "충청북도": "4300000000",
            "충청남도": "4400000000",
            "전라북도": "4500000000",
            "전라남도": "4600000000",
            "경상북도": "4700000000",
            "경상남도": "4800000000",
            "제주도": "5000000000"
        }

        # 검색 시작 메시지 구성
        search_location = []
        if city_name:
            search_location.append(city_name)
            # 특정 시/도 코드가 있으면 해당 코드로 검색
            if city_name in city_codes:
                parent_code = city_codes[city_name]
                print(f"Searching in {city_name} (code: {parent_code})")
        if region_name:
            search_location.append(region_name)
        
        location_str = " ".join(search_location) if search_location else "전국"
        print(f"\n'{apt_name}' 검색 시작 (지역: {location_str})")
        
        matching_apts = self.search_apt_by_name(apt_name, region_name, city_name)
        
        if not matching_apts:
            print("\n유사한 아파트를 찾을 수 없습니다.")
            return
        
        # 여러 결과가 있을 경우 선택 옵션 제공
        if len(matching_apts) > 1:
            print("\n여러 개의 아파트가 검색되었습니다:")
            for i, apt in enumerate(matching_apts, 1):
                print(f"\n{i}. {apt['name']}")
                print(f"   주소: {apt['address']}")
                print(f"   세대수: {apt['total_households']}")
                print(f"   준공년도: {apt['construction_year']}")
                print(f"   유사도: {apt['similarity']:.2%}")
            
            while True:
                try:
                    selection = input("\n데이터를 수집할 아파트 번호를 선택하세요 (1-{len(matching_apts)}): ")
                    selected_idx = int(selection) - 1
                    if 0 <= selected_idx < len(matching_apts):
                        best_match = matching_apts[selected_idx]
                        break
                    print("올바른 번호를 입력하세요.")
                except ValueError:
                    print("숫자를 입력하세요.")
        else:
            best_match = matching_apts[0]
        
        print(f"\n선택된 아파트:")
        print(f"아파트명: {best_match['name']}")
        print(f"주소: {best_match['address']}")
        print(f"세대수: {best_match['total_households']}")
        print(f"준���년도: {best_match['construction_year']}")
        
        confirm = input("\n이 아파트의 데이터를 수집하시겠습니까? (y/n): ")
        
        if confirm.lower() == 'y':
            print(f"\n{best_match['name']} 데이터 수집 중...")
            self.collect_apt_data(best_match['code'])
        else:
            print("데이터 수집을 취소합니다.")

# 사용 예시


if __name__ == "__main__":
    AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IlJFQUxFU1RBVEUiLCJpYXQiOjE3MzI0Mjk1MTIsImV4cCI6MTczMjQ0MDMxMn0.WsebHViURDIKb0mH4nP0BG4Zlr8YSw4c41FLilVNmIY"  # 실제 토큰으로 교체
    crawler = NaverLandCrawler(AUTH_TOKEN)
    path = "data/apartments"
    os.makedirs(path, exist_ok=True)
    #crawler.collect_all_data()
    # 예시: "래미안프레스티지" -> "래미안 프레스티지" 같은 유사 이름도 찾을 수 있음
    # crawler.search_and_collect_apt_data("래미안프레스티지", "강남구", "서울시")
    
    # 예시: "힐스테이트" -> 가장 유사한 힐스테이트 단지를 찾음
    # crawler.search_and_collect_apt_data("힐스테이트", "서초구", "서울시")

    # crawler.search_and_collect_apt_data("현대아파트", "중구", "대전시")
    # 시/도만으로 검색
    crawler.search_and_collect_apt_data("현대2단지", region_name="중구", city_name="대전시")
    
    # 구/군만으로 검색
    #crawler.search_and_collect_apt_data("현대2단지", region_name="중구")
    
    # # 시/도와 구/군 모두 지정
    # crawler.search_and_collect_apt_data("현대아파트", "중구", "대전시")
    
    # # 전국 검색
    # crawler.search_and_collect_apt_data("현대아파트")