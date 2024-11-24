from tqdm import tqdm
import json
import requests
import pandas as pd


def get_header(apt_code='6372'):
    headers = {
    "Accept-Encoding": "gzip",
    "Host": "new.land.naver.com",
    'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IlJFQUxFU1RBVEUiLCJpYXQiOjE3MzI0Mjk1MTIsImV4cCI6MTczMjQ0MDMxMn0.WsebHViURDIKb0mH4nP0BG4Zlr8YSw4c41FLilVNmIY',
    'referer': f'https://new.land.naver.com/complexes/{apt_code}?ms=36.321777,127.40236,17&a=APT&e=RETAIL',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    }
    return headers
#     get_sido_info()의 함수는 서울시, 경기도, 부산시…등의 특별시와 도의 고유코드를 list 형식으로 return 해주는 함수이다.


# 즉 LG개포자이의 고유 코드는 아래와 같이 구할수 있는 것이다.
# sido_list=get_sido_info() 
# gungu_list=get_gungu_info(sido_list[0])
# dong_list=get_dong_info(gungu_list[0])
# get_apt_list(dong_list[0])[0]
def get_sido_info():
    down_url = 'https://new.land.naver.com/api/regions/list?cortarNo=0000000000'
    r = requests.get(down_url,data={"sameAddressGroup":"false"},headers=get_header())
    r.encoding = "utf-8-sig"
    temp=json.loads(r.text)
    temp=list(pd.DataFrame(temp["regionList"])["cortarNo"])
    return temp

# get_gungu_info(sido_code)함수는 get_sido_info()에서 return받은 리스트의 값중 하나를 함수 인자로 넣으면 시/군/구의 고유코드를 list 형식으로 return 해주는 함수이다.

def get_gungu_info(sido_code):
    down_url = f'https://new.land.naver.com/api/regions/list?cortarNo={sido_code}'
    r = requests.get(down_url,data={"sameAddressGroup":"false"},headers=get_header())
    r.encoding = "utf-8-sig"
    temp=json.loads(r.text)
    temp=list(pd.DataFrame(temp['regionList'])["cortarNo"])
    return temp

# get_dong_info(gungu_code)함수는 get_gungu_info(sido_code)에서 return받은 리스트의 값중 하나를 함수 인자로 넣으면 읍/면/동의 고유코드를 list 형식으로 return 해주는 함수이다.

def get_dong_info(gungu_code):
    down_url = f'https://new.land.naver.com/api/regions/list?cortarNo={gungu_code}'
    r = requests.get(down_url,data={"sameAddressGroup":"false"},headers=get_header())
    r.encoding = "utf-8-sig"
    temp=json.loads(r.text)
    temp=list(pd.DataFrame(temp['regionList'])["cortarNo"])
    return temp
# get_apt_list(dong_code)함수는 get_dong_info(gungu_code)에서 return받은 리스트의 값중 하나를 함수 인자로 넣으면 아파트의 고유코드를 list 형식으로 return 해주는 함수이다.

def get_apt_list(dong_code):
    down_url = f'https://new.land.naver.com/api/regions/complexes?cortarNo={dong_code}&realEstateType=APT&order='
    r = requests.get(down_url,data={"sameAddressGroup":"false"},headers=get_header())
    r.encoding = "utf-8-sig"
    temp=json.loads(r.text)
    try:
        temp=list(pd.DataFrame(temp['complexList'])["complexNo"])
    except:
        temp=[]
    return temp

#### get info
def get_apt_info(apt_code):
    down_url = f'https://new.land.naver.com/api/complexes/{apt_code}?sameAddressGroup=false'
    r = requests.get(down_url,data={"sameAddressGroup":"false"},headers=get_header(apt_code))
    r.encoding = "utf-8-sig"
    temp=json.loads(r.text)
    return temp
def get_school_info(apt_code):
    down_url = f'https://new.land.naver.com/api/complexes/{apt_code}/schools'
    r = requests.get(down_url,headers=get_header(apt_code))
    r.encoding = "utf-8-sig"
    temp_school=json.loads(r.text)
    return temp_school
##################가격정보
def apt_price(apt_code,index):
    p_num=temp["complexPyeongDetailList"][index]["pyeongNo"]
    down_url = f'https://new.land.naver.com/api/complexes/{apt_code}/prices?complexNo={apt_code}&tradeType=A1&year=5&priceChartChange=true&areaNo={p_num}&areaChange=true&type=table'

    r = requests.get(down_url,headers=get_header(apt_code))
    r.encoding = "utf-8-sig"
    temp_price=json.loads(r.text)
    return temp_price

sido_list=get_sido_info()
print(sido_list)
for m in tqdm(range(len(sido_list))):
    gungu_list=get_gungu_info(sido_list[m])
    gungu_apt_list=[0]*len(gungu_list)
    print(gungu_list)
    for j in tqdm(range(len(gungu_list))):#구 마다 하나씩 저장
        dong_list=get_dong_info(gungu_list[j])
        dong_apt_list=[0]*len(dong_list)
        print(dong_list)
        for k in tqdm(range(len(dong_list))):#동마다 하나씩 저장
            apt_list=get_apt_list(dong_list[k])
            apt_list_data=[0]*len(apt_list)
            print(apt_list)
            for n in tqdm(range(len(apt_list))):#아파트 마다 하나씩 저장
                temp=get_apt_info(apt_list[n])
                try:
                    area_list=temp["complexDetail"]["pyoengNames"].split(", ")
                    ex_flag=1
                except KeyError:   
                    ex_flag=0
                    print('Error')
                    temp_data=pd.DataFrame(columns=temp_data.columns)
                if ex_flag==1:
                    temp_school=get_school_info(apt_list[n])
                    temp_data=pd.DataFrame(index=range(len(area_list)))
                    for i in tqdm(range(len(area_list))):
                        #print(temp["complexDetail"]["address"],temp["complexDetail"]["complexName"])
                        temp_data.loc[i,"아파트명"]=temp["complexDetail"]["complexName"]
                        temp_data.loc[i,"면적"]=area_list[i]
                        temp_data.loc[i,"법정동주소"]=temp["complexDetail"]["address"]+" "+temp["complexDetail"]["detailAddress"]
                        try:
                            temp_data.loc[i,"도로명주소"]=temp["complexDetail"]["roadAddressPrefix"]+" "+temp["complexDetail"]["roadAddress"]
                        except KeyError:
                            temp_data.loc[i,"도로명주소"]=temp["complexDetail"]["roadAddressPrefix"]
                        temp_data.loc[i,"latitude"]=temp["complexDetail"]["latitude"]
                        temp_data.loc[i,"longitude"]=temp["complexDetail"]["longitude"]
                        temp_data.loc[i,"세대수"]=temp["complexDetail"]["totalHouseholdCount"]
                        temp_data.loc[i,"임대세대수"]=temp["complexDetail"]["totalLeaseHouseholdCount"]
                        temp_data.loc[i,"최고층"]=temp["complexDetail"]["highFloor"]
                        temp_data.loc[i,"최저층"]=temp["complexDetail"]["lowFloor"]
                        try:
                            temp_data.loc[i,"용적률"]=temp["complexDetail"]["batlRatio"]
                        except KeyError:
                            temp_data.loc[i,"용적률"]=""
                        try:
                            temp_data.loc[i,"건폐율"]=temp["complexDetail"]["btlRatio"]
                        except KeyError:
                            temp_data.loc[i,"건폐율"]=""
                        try:
                            temp_data.loc[i,"주차대수"]=temp["complexDetail"]["parkingPossibleCount"]
                        except KeyError:
                            temp_data.loc[i,"주차대수"]=""
                        try:
                            temp_data.loc[i,"건설사"]=temp["complexDetail"]["constructionCompanyName"]
                        except KeyError:   
                            temp_data.loc[i,"건설사"]=""
                        try:
                            temp_data.loc[i,"난방"]=temp["complexDetail"]["heatMethodTypeCode"]
                        except KeyError:   
                            temp_data.loc[i,"난방"]=""
                        try:
                            temp_data.loc[i,"공급면적"]=temp["complexPyeongDetailList"][i]["supplyArea"]
                        except KeyError:   
                            temp_data.loc[i,"공급면적"]=""
                        try:
                            temp_data.loc[i,"전용면적"]=temp["complexPyeongDetailList"][i]["exclusiveArea"]
                        except KeyError:   
                            temp_data.loc[i,"전용면적"]=""
                        try:
                            temp_data.loc[i,"전용율"]=temp["complexPyeongDetailList"][i]["exclusiveRate"]
                        except KeyError:   
                            temp_data.loc[i,"전용율"]=""
                        try:
                            temp_data.loc[i,"방수"]=temp["complexPyeongDetailList"][i]["roomCnt"]
                        except KeyError:   
                            temp_data.loc[i,"방수"]=""
                        try:
                            temp_data.loc[i,"욕실수"]=temp["complexPyeongDetailList"][i]["bathroomCnt"]
                        except KeyError:   
                            temp_data.loc[i,"욕실수"]=""
                        try:
                            temp_data.loc[i,"해당면적_세대수"]=temp["complexPyeongDetailList"][i]["householdCountByPyeong"]
                        except KeyError:   
                            temp_data.loc[i,"해당면적_세대수"]=""
                        try:
                            temp_data.loc[i,"현관구조"]=temp["complexPyeongDetailList"][i]["entranceType"]
                        except KeyError:   
                            temp_data.loc[i,"현관구조"]=""
                        try:
                            temp_data.loc[i,"재산세"]=temp["complexPyeongDetailList"][i]["landPriceMaxByPtp"]["landPriceTax"]["propertyTax"]
                        except KeyError:   
                            temp_data.loc[i,"재산세"]=""
                        try:
                            temp_data.loc[i,"재산세합계"]=temp["complexPyeongDetailList"][i]["landPriceMaxByPtp"]["landPriceTax"]["propertyTotalTax"]
                        except KeyError:   
                            temp_data.loc[i,"재산세합계"]=""
                        try:
                            temp_data.loc[i,"지방교육세"]=temp["complexPyeongDetailList"][i]["landPriceMaxByPtp"]["landPriceTax"]["localEduTax"]
                        except KeyError:   
                            temp_data.loc[i,"지방교육세"]=""
                        try:
                            temp_data.loc[i,"재산세_도시지역분"]=temp["complexPyeongDetailList"][i]["landPriceMaxByPtp"]["landPriceTax"]["cityAreaTax"]
                        except KeyError:   
                            temp_data.loc[i,"재산세_도시지역분"]=""
                        try:
                            temp_data.loc[i,"종합부동산세"]=temp["complexPyeongDetailList"][i]["landPriceMaxByPtp"]["landPriceTax"]["realEstateTotalTax"]
                        except KeyError:   
                            temp_data.loc[i,"종합부동산세"]=""
                        try:
                            temp_data.loc[i,"결정세액"]=temp["complexPyeongDetailList"][i]["landPriceMaxByPtp"]["landPriceTax"]["decisionTax"]
                        except KeyError:   
                            temp_data.loc[i,"결정세액"]=""
                        try:
                            temp_data.loc[i,"농어촌특별세"]=temp["complexPyeongDetailList"][i]["landPriceMaxByPtp"]["landPriceTax"]["ruralSpecialTax"]
                        except KeyError:   
                            temp_data.loc[i,"농어촌특별세"]=""    

                        temp_price=apt_price(apt_list[0],i)
                        try:
                            temp_data.loc[i,"가격"]=temp_price["marketPrices"][0]["dealAveragePrice"]
                        except KeyError:   
                            temp_data.loc[i,"가격"]=""
                        try:
                            temp_data.loc[i,"겨울관리비"]=temp["complexPyeongDetailList"][i]["averageMaintenanceCost"]["winterTotalPrice"]
                        except KeyError:   
                            temp_data.loc[i,"겨울관리비"]=""
                        try:
                            temp_data.loc[i,"여름관리비"]=temp["complexPyeongDetailList"][i]["averageMaintenanceCost"]["summerTotalPrice"]
                        except KeyError:   
                            temp_data.loc[i,"여름관리비"]=""
                        try:
                            temp_data.loc[i,"매매호가"]=temp["complexPyeongDetailList"][i]["articleStatistics"]["dealPriceString"]
                        except KeyError:   
                            temp_data.loc[i,"매매호가"]=""
                        try:
                            temp_data.loc[i,"전세호가"]=temp["complexPyeongDetailList"][i]["articleStatistics"]["leasePriceString"]
                        except KeyError:   
                            temp_data.loc[i,"전세호가"]=""
                        try:
                            temp_data.loc[i,"월세호가"]=temp["complexPyeongDetailList"][i]["articleStatistics"]["rentPriceString"]
                        except KeyError:   
                            temp_data.loc[i,"월세호가"]=""
                        try:
                            temp_data.loc[i,"실거래가"]=temp["complexPyeongDetailList"][i]["articleStatistics"]["rentPriceString"]
                        except KeyError:   
                            temp_data.loc[i,"실거래가"]=""

                            
                        try:
                            temp_data.loc[i,"초등학교_학군정보"]=temp_school['schools'][0]["schoolName"]
                        except KeyError:   
                            temp_data.loc[i,"초등학교_학군정보"]=""
                        except IndexError :   
                            temp_data.loc[i,"초등학교_학군정보"]=""
                        try:
                            temp_data.loc[i,"초등학교_설립정보"]=temp_school['schools'][0]["organizationType"]
                        except KeyError:   
                            temp_data.loc[i,"초등학교_설립정보"]=""
                        except IndexError :   
                            temp_data.loc[i,"초등학교_설립정보"]=""
                        try:
                            temp_data.loc[i,"초등학교_남학생수"]=temp_school['schools'][0]["maleStudentCount"]
                        except KeyError:   
                            temp_data.loc[i,"초등학교_남학생수"]=""
                        except IndexError :   
                            temp_data.loc[i,"초등학교_남학생수"]=""
                        try:
                            temp_data.loc[i,"초등학교_여학생수"]=temp_school['schools'][0]["femaleStudentCount"]
                        except KeyError:   
                            temp_data.loc[i,"초등학교_여학생수"]=""
                        except IndexError :   
                            temp_data.loc[i,"초등학교_여학생수"]=""

                    #time.sleep(1)
                apt_list_data[n]=temp_data
            if apt_list_data==[]:
                dong_apt_list[k]=pd.DataFrame(columns=temp_data.columns)
            else:
                dong_apt_list[k]=pd.concat(apt_list_data)
        gungu_apt_list[j]=pd.concat(dong_apt_list)
        file_name=temp["complexDetail"]["roadAddressPrefix"]+".csv"
        gungu_apt_list[j].to_csv(file_name,encoding="CP949")
        print(f"{file_name} saved")
    final_data=pd.concat(gungu_apt_list)
    final_file_name=temp["complexDetail"]["roadAddressPrefix"].split()[0]+".csv"
    final_data.to_csv(final_file_name,encoding="CP949")
    print(f"{final_file_name} saved")

