from playwright.sync_api import Page
import configparser
import json
import time
from send_telegram import send_telegram_message
from regional_telegram import RegionalTelegramSender

class ForestReservationSystem:
    def __init__(self, page):  # browser 인스턴스 주입
        self.headless = False
        # self.browser = browser
        self.page = page
        self.config = configparser.ConfigParser()
        self.config.read('config.ini', encoding='utf-8')
        self.all_results = []  # 전체 결과 저장용

        # 지역별 텔레그램 전송 시스템 초기화
        self.telegram_sender = RegionalTelegramSender()

    def safe_click(self, selector, timeout=10000):
        self.page.wait_for_selector(selector, state='attached', timeout=timeout)
        self.page.click(selector)

    def smart_select(self, selector, value, select_by='value'):
        """개선된 선택 함수"""
        self.page.wait_for_selector(selector, state='attached')

        if select_by == 'value':
            self.page.select_option(selector, value=str(value))
        elif select_by == 'text':
            self.page.select_option(selector, label=value)
        elif select_by == 'index':
            self.page.select_option(selector, index=value)

        self.page.wait_for_timeout(3000)  # AJAX 대기 시간 증가

    def get_select_options(self, selector):
        """select box의 모든 옵션 추출"""
        options = []
        select_element = self.page.query_selector(selector)
        if select_element:
            option_elements = select_element.query_selector_all('option')
            for option in option_elements:
                value = option.get_attribute('value')
                text = option.inner_text()
                if value and value != "":  # 빈 값 제외
                    options.append({'value': value, 'text': text})
        return options

    def scrape_current_results(self, context_info):
        """개선된 스크래핑 로직: 모든 시설 포함 보장"""
        try:
            self.page.wait_for_selector('#dayListTable', state='visible', timeout=50000)

            # 모든 시설명 추출
            facilities = self.page.query_selector_all('.list_left .simpleMonthDiv')
            # 모든 행 추출 (시설별 날짜 데이터)
            rows = self.page.query_selector_all('#dayListTbody tr')

            # 시설-행 일치 검증
            if len(facilities) != len(rows):
                print(f"⚠️ 시설-행 불일치: 시설={len(facilities)}개, 행={len(rows)}개")
                self.page.screenshot(path='mismatch_error.png')

            current_result = {
                "context": context_info,
                "data": []
            }

            print(f"🔍 스크래핑 시작: 총 {len(facilities)}개 시설")

            for idx, (facility, row) in enumerate(zip(facilities, rows)):
                facility_name = facility.inner_text().strip()
                facility_entry = {
                    "name": facility_name,
                    "dates": []
                }

                # 날짜 셀 추출 (첫 번째 셀 제외)
                days = row.query_selector_all('td:not(.list_left)')

                for day in days:
                    status_span = day.query_selector('.apt_mark, .apt_mark_2')
                    if status_span:
                        status = status_span.inner_text().strip()
                        date_str = status_span.get_attribute('title')
                        if date_str:
                            date_str = date_str.split()[-1]  # "2025.06.15" 추출

                        if status.startswith(('예', '대')):
                            facility_entry["dates"].append({
                                "date": date_str,
                                "status": status
                            })

                # 예약 가능 여부와 관계없이 모든 시설 포함
                current_result["data"].append(facility_entry)
                print(f"  - 시설 {idx + 1}: {facility_name} ({len(facility_entry['dates'])}개 일자)")

            # 최종 요약 출력
            total_dates = sum(len(f['dates']) for f in current_result["data"])
            print(f"📊 스크래핑 완료: 시설 {len(facilities)}개, 예약 일자 {total_dates}개")

            return current_result

        except Exception as e:
            print(f"❌ 스크래핑 오류: {str(e)}")
            self.page.screenshot(path='scraping_error.png')
            return None

    def run_comprehensive_scraping(self):
        """지역별 실시간 전송이 포함된 전수 스크래핑"""
        try:
            self.page.wait_for_load_state('networkidle')
            print("📄 페이지 로딩 완료")

            # 월 선택 옵션 수집
            month_options = self.get_select_options('#monthSelectBox')
            print(f"📅 월 옵션 수: {len(month_options)}개")

            # 지역 선택 옵션 수집
            region_options = self.get_select_options('#srchSido')
            print(f"🌍 지역 옵션 수: {len(region_options)}개")

            total_combinations = 0
            processed_combinations = 0

            for month_idx, month_option in enumerate(month_options):
                print(f"\n🗓️ [{month_idx + 1}/{len(month_options)}] 월 선택: {month_option['text']}")
                self.smart_select('#monthSelectBox', month_option['value'], 'value')

                for region_idx, region_option in enumerate(region_options):
                    # 🔥 지역 코드와 지역명 추출
                    current_region_code = region_option['value']
                    current_region_name = region_option['text']

                    print(f"  🌏 [{region_idx + 1}/{len(region_options)}] 지역 선택: {current_region_name}")
                    self.smart_select('#srchSido', current_region_code, 'value')

                    # 자연휴양림 옵션 로딩
                    self.page.wait_for_function('''
                        () => document.querySelector('#srchInstt').children.length > 1
                    ''', timeout=10000)

                    forest_options = self.get_select_options('#srchInstt')
                    print(f"    🌲 자연휴양림 옵션 수: {len(forest_options)}개")

                    for forest_idx, forest_option in enumerate(forest_options):
                        print(f"    🏕️ [{forest_idx + 1}/{len(forest_options)}] 휴양림: {forest_option['text']}")
                        self.smart_select('#srchInstt', forest_option['value'], 'value')

                        # 숙박시설 옵션 로딩
                        self.page.wait_for_function('''
                            () => document.querySelector('#srchForest').children.length > 1
                        ''', timeout=10000)

                        accommodation_options = self.get_select_options('#srchForest')
                        print(f"      🏠 숙박시설 옵션 수: {len(accommodation_options)}개")

                        for acc_idx, acc_option in enumerate(accommodation_options):
                            total_combinations += 1

                            # 🔥 컨텍스트 정보에 지역 코드 포함
                            context_info = {
                                "month": month_option['text'],
                                "region": current_region_name,
                                "region_code": current_region_code,  # 지역 코드 추가
                                "forest": forest_option['text'],
                                "accommodation": acc_option['text']
                            }

                            print(f"      🏘️ [{acc_idx + 1}/{len(accommodation_options)}] 숙박시설: {acc_option['text']}")

                            # 검색 실행
                            self.smart_select('#srchForest', acc_option['value'], 'value')
                            self.page.wait_for_selector('#srchForest2 option:nth-child(1)', state='attached')
                            self.smart_select('#srchForest2', 0, 'index')

                            self.safe_click('#searchBtn')
                            self.page.wait_for_load_state('networkidle')
                            self.page.wait_for_timeout(2000)

                            # 결과 스크래핑
                            result = self.scrape_current_results(context_info)

                            if result and result["data"]:
                                self.all_results.append(result)
                                processed_combinations += 1
                                print(f"        ✅ 데이터 수집 완료 ({len(result['data'])}개 시설)")

                                # 🔥 지역별 텔레그램 전송
                                self.telegram_sender.send_to_region(
                                    current_region_code,  # 지역 코드로 채팅방 구분
                                    context_info,
                                    result["data"]
                                )

                            else:
                                print(f"        ⚠️ 예약 가능한 데이터 없음")

            print(f"\n🎉 지역별 전수 스크래핑 완료!")
            print(f"📊 총 조합 수: {total_combinations}")
            print(f"📈 데이터 수집 성공: {processed_combinations}")

            return self.all_results

        except Exception as e:
            print(f"❌ 전수 스크래핑 실패: {str(e)}")
            self.page.screenshot(path='comprehensive_scraping_error.png')
            raise

    def save_results_to_file(self, filename='comprehensive_results.json'):
        """결과를 파일로 저장"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.all_results, f, ensure_ascii=False, indent=2)
        print(f"💾 결과 저장 완료: {filename}")

    # temp test code
    # def run_june_region_test(self):
    #     """2025년 6월 기준 지역별 간소화 테스트"""
    #     try:
    #         self.page.wait_for_load_state('networkidle')
    #         print("📄 테스트 시작: 2025년 6월")
    #
    #         # 1. 월 선택 (6월 고정)
    #         month_options = self.get_select_options('#monthSelectBox')
    #         june_option = next((m for m in month_options if '6월' in m['text']), None)
    #         if not june_option:
    #             print("⚠️ 6월 옵션 없음")
    #             return
    #
    #         self.smart_select('#monthSelectBox', june_option['value'], 'value')
    #         print(f"📅 월 선택: {june_option['text']}")
    #
    #         # 2. 지역 옵션 수집
    #         region_options = self.get_select_options('#srchSido')
    #         print(f"🌍 테스트 지역 수: {len(region_options)}개")
    #
    #         for region in region_options:
    #             region_code = region['value']
    #             region_name = region['text']
    #             print(f"\n▶️ [{region_name}] 테스트 시작")
    #
    #             # 3. 지역 선택
    #             self.smart_select('#srchSido', region_code, 'value')
    #
    #             # 4. 자연휴양림 첫 번째 옵션 선택
    #             self.page.wait_for_function('''
    #                 () => document.querySelector('#srchInstt').children.length > 1
    #             ''', timeout=10000)
    #
    #             forest_options = self.get_select_options('#srchInstt')
    #             if not forest_options:
    #                 print(f"⚠️ {region_name} 휴양림 없음")
    #                 continue
    #
    #             first_forest = forest_options[0]
    #             self.smart_select('#srchInstt', first_forest['value'], 'value')
    #             print(f"🌲 휴양림 선택: {first_forest['text']}")
    #
    #             # 5. 숙박시설 첫 번째 옵션 선택
    #             self.page.wait_for_function('''
    #                 () => document.querySelector('#srchForest').children.length > 1
    #             ''', timeout=10000)
    #
    #             acc_options = self.get_select_options('#srchForest')
    #             if not acc_options:
    #                 print(f"⚠️ {region_name} 숙박시설 없음")
    #                 continue
    #
    #             first_acc = acc_options[0]
    #             self.smart_select('#srchForest', first_acc['value'], 'value')
    #             print(f"🏠 숙박시설 선택: {first_acc['text']}")
    #
    #             # 6. 시설 전체 선택
    #             self.page.wait_for_selector('#srchForest2 option:nth-child(1)', state='attached')
    #             self.smart_select('#srchForest2', 0, 'index')
    #
    #             # 7. 검색 실행
    #             self.safe_click('#searchBtn')
    #             self.page.wait_for_load_state('networkidle')
    #             self.page.wait_for_timeout(2000)
    #
    #             # 8. 스크래핑 및 전송
    #             context_info = {
    #                 "month": june_option['text'],
    #                 "region": region_name,
    #                 "region_code": region_code,
    #                 "forest": first_forest['text'],
    #                 "accommodation": first_acc['text']
    #             }
    #
    #             result = self.scrape_current_results(context_info)
    #             if result and result["data"]:
    #                 self.telegram_sender.send_to_region(region_code, context_info, result["data"])
    #                 print(f"📤 {region_name} 전송 완료")
    #             else:
    #                 print(f"⚠️ {region_name} 데이터 없음")
    #
    #         print("\n✅ 모든 지역 테스트 완료")
    #
    #     except Exception as e:
    #         print(f"❌ 테스트 실패: {str(e)}")
    #         self.page.screenshot(path='june_test_error.png')

    def run_june_region_test(self, target_region_code="8"):
        """2025년 6월 기준 특정 지역 테스트 (기본값: 부산/경남)"""
        try:
            self.page.wait_for_load_state('networkidle')
            print(f"📄 테스트 시작: 2025년 6월 [지역: {target_region_code}]")

            # 1. 월 선택 (6월 고정)
            month_options = self.get_select_options('#monthSelectBox')
            june_option = next((m for m in month_options if '6월' in m['text']), None)
            if not june_option:
                print("⚠️ 6월 옵션 없음")
                return

            self.smart_select('#monthSelectBox', june_option['value'], 'value')
            print(f"📅 월 선택: {june_option['text']}")

            # 2. 지역 옵션 수집 및 필터링
            region_options = self.get_select_options('#srchSido')
            target_region = next((r for r in region_options if r['value'] == target_region_code), None)

            if not target_region:
                print(f"⚠️ 지정된 지역 코드({target_region_code}) 없음")
                return

            region_code = target_region['value']
            region_name = target_region['text']
            print(f"\n▶️ [{region_name}] 테스트 시작")

            # 3. 지역 선택
            self.smart_select('#srchSido', region_code, 'value')

            # 4. 자연휴양림 첫 번째 옵션 선택
            self.page.wait_for_function('''
                () => document.querySelector('#srchInstt').children.length > 1
            ''', timeout=10000)

            forest_options = self.get_select_options('#srchInstt')
            if not forest_options:
                print(f"⚠️ {region_name} 휴양림 없음")
                return

            first_forest = forest_options[0]
            self.smart_select('#srchInstt', first_forest['value'], 'value')
            print(f"🌲 휴양림 선택: {first_forest['text']}")

            # 5. 숙박시설 첫 번째 옵션 선택
            self.page.wait_for_function('''
                () => document.querySelector('#srchForest').children.length > 1
            ''', timeout=10000)

            acc_options = self.get_select_options('#srchForest')
            if not acc_options:
                print(f"⚠️ {region_name} 숙박시설 없음")
                return

            first_acc = acc_options[0]
            self.smart_select('#srchForest', first_acc['value'], 'value')
            print(f"🏠 숙박시설 선택: {first_acc['text']}")

            # 6. 시설 전체 선택
            self.page.wait_for_selector('#srchForest2 option:nth-child(1)', state='attached')
            self.smart_select('#srchForest2', 0, 'index')

            # 7. 검색 실행
            self.safe_click('#searchBtn')
            self.page.wait_for_load_state('networkidle')
            self.page.wait_for_timeout(3000)

            # 8. 스크래핑 및 전송
            context_info = {
                "month": june_option['text'],
                "region": region_name,
                "region_code": region_code,
                "forest": first_forest['text'],
                "accommodation": first_acc['text']
            }

            result = self.scrape_current_results(context_info)
            if result and result["data"]:
                self.telegram_sender.send_to_region(region_code, context_info, result["data"])
                print(f"📤 {region_name} 전송 완료")
            else:
                print(f"⚠️ {region_name} 데이터 없음")

            print(f"\n✅ {region_name} 테스트 완료")

        except Exception as e:
            print(f"❌ 테스트 실패: {str(e)}")
            self.page.screenshot(path=f'error_{target_region_code}.png')


    def run_reservation_flow(self):
        """기존 메서드를 전수 스크래핑으로 대체"""
        results = self.run_comprehensive_scraping()
        return results