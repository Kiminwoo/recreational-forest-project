from foresttrip_headless_login import foresttrip_login
from forest_headless_reservation import ForestReservationSystem


def main():
    browser = None
    page = None

    try:
        # 1. 로그인 및 브라우저 인스턴스 획득
        page = foresttrip_login()

        # 2. 예약 시스템 초기화 (로그인 세션 전달)
        reservation = ForestReservationSystem(page)

        # 3. 예약 프로세스 실행
        reservation.run_reservation_flow()

    except Exception as e:
            print(f"🚨 전체 프로세스 오류: {str(e)}")

    finally:
        if page:
            page.stop()

if __name__ == "__main__":
    main()