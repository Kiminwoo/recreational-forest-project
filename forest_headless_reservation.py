from playwright.sync_api import Page
import configparser


class ForestReservationSystem:
    def __init__(self, page):  # browser 인스턴스 주입
        self.headless = False
        # self.browser = browser
        self.page = page
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')

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

        self.page.wait_for_timeout(2000)  # AJAX 대기 시간 증가

    def run_reservation_flow(self):
        try:

            # 1. 페이지 완전 로딩 대기
            self.page.wait_for_load_state('networkidle')
            print("📄 페이지 로딩 완료")

            # 2. 지역 선택 (value="1" 사용)
            self.smart_select('#srchSido', '1', 'value')
            print("✅ 서울/인천/경기 지역 선택 완료")

            # 3. 자연휴양림 AJAX 로딩 대기 (더 구체적인 대기)
            self.page.wait_for_function('''
                () => document.querySelector('#srchInstt').children.length > 1
            ''', timeout=10000)
            self.smart_select('#srchInstt', 1, 'index')
            print("✅ 자연휴양림 선택 완료")

            # 4. 숙박시설 AJAX 로딩 대기
            self.page.wait_for_function('''
                () => document.querySelector('#srchForest').children.length > 1
            ''', timeout=10000)
            self.smart_select('#srchForest', 1, 'index')
            print("✅ 숙박시설 선택 완료")

            # 5. 시설 전체 선택
            self.page.wait_for_selector('#srchForest2 option:nth-child(1)', state='attached')
            self.smart_select('#srchForest2', 0, 'index')
            print("✅ 시설 전체 선택 완료")

            # 6. 검색 실행
            self.safe_click('#searchBtn')
            self.page.wait_for_load_state('networkidle')
            print("🔍 검색 실행 완료")

            self.page.wait_for_timeout(3000)

            # 7. 결과 테이블 확인
            # 7. 결과 테이블 확인
            self.page.wait_for_selector('#dayListTable', state='visible', timeout=15000)
            print("📊 예약 현황 로드 완료")

            # 8. 스크래핑 로직
            # 왼쪽 영역 (숙소 목록)
            facilities = self.page.query_selector_all('.list_left .simpleMonthDiv')
            # 오른쪽 영역 (날짜별 예약 현황)
            rows = self.page.query_selector_all('#dayListTbody tr')

            # 데이터 저장용 리스트
            result_data = []

            for facility, row in zip(facilities, rows):
                facility_name = facility.inner_text().strip()
                facility_entry = {
                    "name": facility_name,
                    "dates": []
                }

                days = row.query_selector_all('td')
                for day in days:
                    status_span = day.query_selector('.apt_mark, .apt_mark_2')
                    if status_span:
                        status = status_span.inner_text().strip()
                        date_str = status_span.get_attribute('title').split()[-1]

                        # 상태 필터링 (예/대)
                        if status.startswith(('예', '대')):
                            date_entry = {
                                "date": date_str,
                                "status": status
                            }
                            facility_entry["dates"].append(date_entry)
                    else:
                        continue

                result_data.append(facility_entry)

            # 최종 출력
            print("\n최종 예약 현황:")
            import json
            print(json.dumps(result_data, ensure_ascii=False, indent=2))

        except Exception as e:
            self.page.screenshot(path='reservation_error.png')
            raise

    def close(self):
        self.browser.close()