from foresttrip_headless_login import foresttrip_login
from forest_headless_reservation import ForestReservationSystem
from send_telegram import send_telegram_message


def main():
    browser = None
    page = None

    try:
        # 1. 로그인 및 브라우저 인스턴스 획득
        page = foresttrip_login()

        # 2. 예약 시스템 초기화 (로그인 세션 전달)
        reservation = ForestReservationSystem(page)

        # 3. 예약 프로세스 실행
        result_data = reservation.run_reservation_flow()

        # reservation.run_june_region_test()  # 새 메서드 호출

        print(result_data)
        # 4. 텔레그램 전송
        # 모든 데이터 기준 한번에 전송
        # if result_data:
        #     send_telegram_message(result_data)
        # else:
        #     print("⚠️ 스크래핑 데이터 없음")
    except Exception as e:
            print(f"🚨 전체 프로세스 오류: {str(e)}")

    finally:
        print("휴양림 스크래핑 완료")
        # if page:
        #     page.stop()

        # test code
        if page:
            input("Press Enter to close browser...")  # 브라우저 유지 (결과 확인용)
            page.close()

if __name__ == "__main__":
    main()