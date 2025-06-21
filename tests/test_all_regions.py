from foresttrip_headless_login import foresttrip_login
from regional_telegram import RegionalTelegramSender
import configparser
import time


class AllRegionsTest:
    def __init__(self, page):
        self.page = page
        self.telegram_sender = RegionalTelegramSender()
        self.config = configparser.ConfigParser()
        self.config.read('config.ini', encoding='utf-8')

    def safe_click(self, selector, timeout=10000):
        self.page.wait_for_selector(selector, state='attached', timeout=timeout)
        self.page.click(selector)

    def smart_select(self, selector, value, select_by='value'):
        self.page.wait_for_selector(selector, state='attached')

        if select_by == 'value':
            self.page.select_option(selector, value=str(value))
        elif select_by == 'index':
            self.page.select_option(selector, index=value)

        self.page.wait_for_timeout(3000)

    def get_select_options(self, selector):
        """select box의 모든 옵션 추출"""
        options = []
        select_element = self.page.query_selector(selector)
        if select_element:
            option_elements = select_element.query_selector_all('option')
            for option in option_elements:
                value = option.get_attribute('value')
                text = option.inner_text()
                if value and value != "":
                    options.append({'value': value, 'text': text})
        return options

    def scrape_region_data(self, context_info):
        """해당 지역 스크래핑 (간소화 버전)"""
        try:
            self.page.wait_for_selector('#dayListTable', state='visible', timeout=15000)

            facilities = self.page.query_selector_all('.list_left .simpleMonthDiv')
            rows = self.page.query_selector_all('#dayListTbody tr')

            result_data = []

            # 최대 3개 시설만 추출
            for facility, row in list(zip(facilities, rows))[:3]:
                facility_name = facility.inner_text().strip()
                facility_entry = {
                    "name": facility_name,
                    "dates": []
                }

                days = row.query_selector_all('td')
                date_count = 0

                for day in days:
                    if date_count >= 5:  # 최대 5개 날짜만
                        break

                    status_span = day.query_selector('.apt_mark, .apt_mark_2')
                    if status_span:
                        status = status_span.inner_text().strip()
                        date_str = status_span.get_attribute('title')
                        if date_str:
                            date_str = date_str.split()[-1]

                        if status.startswith(('예', '대')):
                            facility_entry["dates"].append({
                                "date": date_str,
                                "status": status
                            })
                            date_count += 1

                if facility_entry["dates"]:
                    result_data.append(facility_entry)

            return result_data

        except Exception as e:
            print(f"❌ {context_info['region']} 스크래핑 오류: {str(e)}")
            return None

    def test_single_region(self, region_code, region_name):
        """단일 지역 테스트 실행"""
        print(f"\n🧪 [{region_name}] 테스트 시작...")

        try:
            # 1. 월 선택 (6월 - 첫 번째 옵션)
            month_options = self.get_select_options('#monthSelectBox')
            if month_options:
                # 6월에 해당하는 옵션 찾기 (202506)
                june_option = next((opt for opt in month_options if '6월' in opt['text']), month_options[0])
                self.smart_select('#monthSelectBox', june_option['value'], 'value')
                print(f"📅 월 선택: {june_option['text']}")
                selected_month = june_option['text']
            else:
                print("⚠️ 월 옵션을 찾을 수 없습니다.")
                return False

            # 2. 지역 선택
            self.smart_select('#srchSido', region_code, 'value')
            print(f"🌏 지역 선택: {region_name}")

            # 3. 자연휴양림 로딩 대기 및 첫 번째 선택
            self.page.wait_for_function('''
                () => document.querySelector('#srchInstt').children.length > 1
            ''', timeout=10000)

            forest_options = self.get_select_options('#srchInstt')
            if forest_options:
                # 첫 번째 휴양림 선택
                first_forest = forest_options[0]
                self.smart_select('#srchInstt', first_forest['value'], 'value')
                print(f"🌲 휴양림 선택: {first_forest['text']}")
                selected_forest = first_forest['text']
            else:
                print(f"⚠️ {region_name}에 휴양림이 없습니다.")
                return False

            # 4. 숙박시설 로딩 대기 및 첫 번째 선택
            self.page.wait_for_function('''
                () => document.querySelector('#srchForest').children.length > 1
            ''', timeout=10000)

            accommodation_options = self.get_select_options('#srchForest')
            if accommodation_options:
                # 첫 번째 숙박시설 선택
                first_accommodation = accommodation_options[0]
                self.smart_select('#srchForest', first_accommodation['value'], 'value')
                print(f"🏠 숙박시설 선택: {first_accommodation['text']}")
                selected_accommodation = first_accommodation['text']
            else:
                print(f"⚠️ {region_name}에 숙박시설이 없습니다.")
                return False

            # 5. 시설 전체 선택
            self.page.wait_for_selector('#srchForest2 option:nth-child(1)', state='attached')
            self.smart_select('#srchForest2', 0, 'index')
            print("🏘️ 시설 전체 선택")

            # 6. 검색 실행
            self.safe_click('#searchBtn')
            self.page.wait_for_load_state('networkidle')
            self.page.wait_for_timeout(3000)
            print("🔍 검색 실행 완료")

            # 7. 컨텍스트 정보 생성
            context_info = {
                "month": selected_month,
                "region": region_name,
                "region_code": region_code,
                "forest": selected_forest,
                "accommodation": selected_accommodation
            }

            # 8. 스크래핑 실행
            result_data = self.scrape_region_data(context_info)

            if result_data:
                print(f"✅ 데이터 수집 완료 ({len(result_data)}개 시설)")

                # 9. 해당 지역 채팅방으로 텔레그램 전송
                self.telegram_sender.send_to_region(region_code, context_info, result_data)
                print(f"📱 {region_name} 채팅방 전송 완료")
                return True
            else:
                print(f"⚠️ {region_name}에서 예약 가능한 데이터 없음")

                # 빈 데이터라도 테스트용으로 전송
                test_data = [{
                    "name": f"[테스트] {region_name} 샘플 시설",
                    "dates": [{"date": "2025.06.15", "status": "예"}]
                }]
                self.telegram_sender.send_to_region(region_code, context_info, test_data)
                print(f"📱 {region_name} 테스트 메시지 전송 완료")
                return True

        except Exception as e:
            print(f"❌ {region_name} 테스트 실패: {str(e)}")
            self.page.screenshot(path=f'error_{region_name}.png')
            return False

    def run_all_regions_test(self):
        """9개 지역 전체 테스트 실행"""
        print("🚀 9개 지역 전체 테스트 시작...")

        try:
            self.page.wait_for_load_state('networkidle')
            print("📄 월별예약 페이지 로딩 완료")

            # 9개 지역 정의
            regions = [
                ("1", "서울/인천/경기"),
                ("2", "강원"),
                ("3", "충북"),
                ("4", "대전/충남"),
                ("5", "전북"),
                ("6", "광주/전남"),
                ("7", "대구/경북"),
                ("8", "부산/경남"),
                ("9", "제주")
            ]

            success_count = 0
            total_count = len(regions)

            print(f"📊 총 {total_count}개 지역 테스트 예정")

            for idx, (region_code, region_name) in enumerate(regions, 1):
                print(f"\n{'=' * 50}")
                print(f"🔄 진행률: [{idx}/{total_count}] {region_name}")
                print(f"{'=' * 50}")

                success = self.test_single_region(region_code, region_name)
                if success:
                    success_count += 1

                # 지역 간 딜레이 (서버 부하 방지)
                if idx < total_count:  # 마지막 지역이 아니면
                    print(f"⏱️ 다음 지역 테스트까지 5초 대기...")
                    time.sleep(5)

            print(f"\n🎉 전체 지역 테스트 완료!")
            print(f"📊 성공: {success_count}/{total_count} 지역")
            print(f"📈 성공률: {(success_count / total_count) * 100:.1f}%")

            # 최종 완료 메시지를 모든 채팅방에 전송
            final_message = f"✅ 9개 지역 테스트 완료!\n성공: {success_count}/{total_count} 지역"
            self.telegram_sender.send_to_all_regions(final_message)

            return success_count == total_count

        except Exception as e:
            print(f"❌ 전체 테스트 실패: {str(e)}")
            self.page.screenshot(path='all_regions_test_error.png')
            return False


def main():
    print("🧪 9개 지역 전체 텔레그램 전송 테스트 시작...")

    page = None
    try:
        # 1. 로그인 실행
        page = foresttrip_login()
        if not page:
            print("❌ 로그인 실패로 테스트 중단")
            return

        print("✅ 로그인 완료")

        # 2. 전체 지역 테스트 시스템 초기화
        tester = AllRegionsTest(page)

        # 3. 9개 지역 전체 테스트 실행
        success = tester.run_all_regions_test()

        if success:
            print("🎉 모든 지역 테스트 성공!")
        else:
            print("⚠️ 일부 지역에서 테스트 실패")

    except Exception as e:
        print(f"❌ 테스트 실행 실패: {str(e)}")
    finally:
        if page:
            input("Press Enter to close browser...")  # 브라우저 유지 (결과 확인용)
            page.close()


if __name__ == "__main__":
    main()