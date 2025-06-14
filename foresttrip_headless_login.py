from playwright.sync_api import sync_playwright
import configparser
import re

config = configparser.ConfigParser()
config.read('config.ini')


def handle_dynamic_popup(page):
    """동적 팝업 닫기 처리 함수"""
    try:
        # 1. 팝업 감지 (부분 일치)
        popup = page.wait_for_selector('[id^="enterPopup"]', timeout=3000)
        if popup:
            popup_id = popup.get_attribute('id')
            print(f"팝업 감지: {popup_id}")

            # 팝업 번호 추출 (예: enterPopup10333 → 10333)
            popup_number = re.search(r'\d+', popup_id).group()

            # 2. 방법 1: 닫기 버튼 직접 클릭
            close_selectors = [
                f'#{popup_id} .day_close',  # 첫 번째 닫기 버튼
                f'#{popup_id} .ep_cookie_close a',  # 쿠키 닫기 버튼
                f'#{popup_id} img[alt=""]',  # 닫기 이미지
                f'[onclick*="closePopup(\'{popup_number}\')"]'  # onclick 속성으로 직접 찾기
            ]

            for selector in close_selectors:
                try:
                    close_btn = page.query_selector(selector)
                    if close_btn:
                        close_btn.click()
                        print(f"팝업 닫기 성공 (선택자: {selector})")
                        # 팝업이 사라질 때까지 대기
                        page.wait_for_selector(f'#{popup_id}', state='hidden', timeout=2000)
                        return True
                except:
                    continue

            # 3. 방법 2: JavaScript 함수 직접 호출
            try:
                page.evaluate(f"closePopup('{popup_number}')")
                print(f"closePopup('{popup_number}') 함수 호출 성공")
                page.wait_for_selector(f'#{popup_id}', state='hidden', timeout=2000)
                return True
            except:
                pass

            # 4. 방법 3: jQuery hide() 직접 실행
            try:
                page.evaluate(f"$('#{popup_id}').hide()")
                print(f"jQuery hide() 실행: #{popup_id}")
                return True
            except:
                pass

            # 5. 방법 4: 강제 DOM 제거
            try:
                page.evaluate(f"""
                    const popup = document.getElementById('{popup_id}');
                    if (popup) {{
                        popup.style.display = 'none';
                        popup.classList.remove('show');
                    }}
                """)
                print("강제 DOM 숨김 처리")
                return True
            except:
                pass

    except Exception as e:
        print(f"팝업 처리 중 오류: {str(e)}")

    return False




def foresttrip_login():
    with sync_playwright() as p:
        # 브라우저 설정
        browser = p.chromium.launch_persistent_context(
            user_data_dir='./user_data',
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--auto-open-devtools-for-tabs'
            ]
        )

        page = browser.new_page()

        try:
            # 1. 로그인 페이지 이동
            page.goto(config['DEFAULT']['LOGIN_URL'], timeout=60000)
            page.wait_for_selector('#fripPotForm', state='attached')

            # 2. CSRF 토큰 추출
            csrf_token = page.query_selector('input[name="_csrf"]').get_attribute('value')

            # 3. 계정 정보 입력 (보안 강화 방식)
            page.evaluate(f"""() => {{
                document.querySelector('#mmberId').value = '{config['CREDENTIALS']['USERNAME']}';
                document.querySelector('#gnrlMmberPssrd').value = '{config['CREDENTIALS']['PASSWORD']}';
            }}""")

            # 4. 추가 보안 요소 처리
            page.click('#saveId')
            page.wait_for_timeout(1000)

            # 5. 폼 제출
            with page.expect_navigation():
                page.click('.loginBtn')

            # 6. 레이어 팝업 처리
            # 동적 팝업 처리 (핵심 부분)
            # 동적 팝업 처리 (개선된 로직)
            popup_closed = handle_dynamic_popup(page)

            if popup_closed:
                print("✅ 팝업 닫기 완료")
            else:
                print("ℹ️ 팝업 없음 또는 이미 닫힘")

            # 로그인 성공 확인
            page.wait_for_timeout(2000)  # 팝업 닫힌 후 안정화 대기

        except Exception as e:
            page.screenshot(path='login_error.png')
            print(f'에러 발생: {str(e)}')

        finally:
            browser.close()


if __name__ == "__main__":
    foresttrip_login()