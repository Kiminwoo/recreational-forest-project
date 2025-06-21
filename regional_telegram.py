import requests
import configparser
import time
import html


class RegionalTelegramSender:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini', encoding='utf-8')
        self.token = self.config.get('TELEGRAM', 'TOKEN')

        # 지역별 chat_id 매핑
        self.region_chat_ids = {}
        self.region_names = {}

        for region_code in self.config['REGION_CHAT_IDS']:
            self.region_chat_ids[region_code] = self.config.get('REGION_CHAT_IDS', region_code)
            self.region_names[region_code] = self.config.get('REGION_NAMES', region_code)

    def _format_facility(self, facility):
        """시설 정보 포맷팅 (UTF-8 바이트 기반)"""
        safe_name = html.escape(facility['name'])
        facility_str = f"🏡 <b>{safe_name}</b>\n"
        byte_count = len(facility_str.encode('utf-8'))

        date_count = 0
        for entry in facility['dates']:
            safe_date = html.escape(entry['date'])
            safe_status = html.escape(entry['status'])
            line = f"  └ {safe_date} : <b>{safe_status}</b>\n"
            line_bytes = len(line.encode('utf-8'))

            if byte_count + line_bytes > 3900:
                remaining = len(facility['dates']) - date_count
                facility_str += f"  └ ... 외 {remaining}개 더\n"
                break

            facility_str += line
            byte_count += line_bytes
            date_count += 1

        return facility_str + "\n\n"  # 시설 간 2줄 간격

    def _chunk_by_facilities(self, header, facilities):
        """시설 단위 분할 보장 청킹 시스템"""
        chunks = []
        current_chunk = header
        current_size = len(header.encode('utf-8'))

        for facility in facilities:
            fac_str = self._format_facility(facility)
            fac_bytes = len(fac_str.encode('utf-8'))

            # 현재 청크에 추가 가능한지 확인
            if current_size + fac_bytes > 4000:
                chunks.append(current_chunk)
                current_chunk = "📄 [이어서]\n" + fac_str
                current_size = len(current_chunk.encode('utf-8'))
            else:
                current_chunk += fac_str
                current_size += fac_bytes

        # 마지막 청크 처리
        if current_chunk != header:
            chunks.append(current_chunk)

        return chunks

    # def send_to_region(self, region_code, context_info, result_data):
    #     """특정 지역 채팅방으로 메시지 전송 (분할 포함)"""
    #     if region_code not in self.region_chat_ids:
    #         print(f"⚠️ 지역 코드 {region_code}에 해당하는 채팅방이 없습니다.")
    #         return
    #
    #     chat_id = self.region_chat_ids[region_code]
    #     region_name = self.region_names[region_code]
    #
    #     if not result_data or len(result_data) == 0:
    #         return
    #
    #     # 1. 헤더 생성 (HTML 이스케이프 적용)
    #     header = f"🏞️ <b>{html.escape(region_name)} 휴양림 예약 현황</b>\n\n"
    #     header += f"📅 {html.escape(context_info['month'])}\n"
    #     header += f"🌲 {html.escape(context_info['forest'])}\n"
    #     header += f"🏠 {html.escape(context_info['accommodation'])}\n"
    #     header += f"{'=' * 30}\n"
    #
    #     # 2. 요약 정보 생성
    #     summary = f"📊 총 {len(result_data)}개 시설 | "
    #     summary += f"예약 일자: {sum(len(f['dates']) for f in result_data)}개\n"
    #
    #     # 3. 시설 단위 청크 분할
    #     chunks = self.chunk_by_facilities(header, result_data)
    #
    #     # 4. 첫 청크에 요약 정보 추가
    #     if chunks:
    #         chunks[0] = summary + chunks[0]
    #
    #     # 5. 전송 (재시도 포함)
    #     for i, chunk in enumerate(chunks):
    #         print(f"📤 {region_name} - 청크 {i + 1}/{len(chunks)} ({len(chunk.encode('utf-8'))}바이트)")
    #         self._send_with_retry(chat_id, chunk, region_name)

    def _send_with_retry(self, chat_id, message, region_name, chunk_info):
        """강화된 재시도 메커니즘"""
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }

        for attempt in range(3):
            try:
                response = requests.post(url, json=payload, timeout=15)
                if response.status_code == 200:
                    print(f"✅ {region_name} {chunk_info} - 전송 성공 (시도 {attempt + 1})")
                    return True
                else:
                    print(f"⚠️ {region_name} {chunk_info} - 시도 {attempt + 1} 실패: {response.status_code}")
            except Exception as e:
                print(f"⚠️ {region_name} {chunk_info} - 시도 {attempt + 1} 예외: {str(e)}")

            time.sleep(2 ** attempt)  # 지수 백오프

        print(f"❌ {region_name} {chunk_info} - 최종 전송 실패")
        return False

    def send_to_region(self, region_code, context_info, result_data):
        """데이터 무결성 보장 전송 시스템"""
        if region_code not in self.region_chat_ids:
            print(f"⚠️ 지역 코드 {region_code}에 해당하는 채팅방이 없습니다.")
            return

        chat_id = self.region_chat_ids[region_code]
        region_name = self.region_names[region_code]

        if not result_data or len(result_data) == 0:
            return

        # 헤더 생성 (HTML 이스케이프 필수)
        header = f"🏞️ <b>{html.escape(region_name)} 휴양림 예약 현황</b>\n\n"
        header += f"📅 {html.escape(context_info['month'])}\n"
        header += f"🌲 {html.escape(context_info['forest'])}\n"
        header += f"🏠 {html.escape(context_info['accommodation'])}\n"
        header += f"{'=' * 30}\n"

        # 요약 정보 생성
        total_facilities = len(result_data)

        total_dates = sum(len(f['dates']) for f in result_data)
        summary = f"📊 총 {total_facilities}개 시설 | 예약 일자: {total_dates}개\n"

        # 시설 단위 청크 분할
        chunks = self._chunk_by_facilities(header, result_data)

        # 첫 청크에 요약 정보 추가
        if chunks:
            chunks[0] = summary + chunks[0]

        # 청크별 전송 + 무결성 검증
        sent_facilities = 0
        for i, chunk in enumerate(chunks):
            chunk_info = f"청크 {i + 1}/{len(chunks)}"
            facilities_in_chunk = chunk.count("🏡")

            # 전송 전 검증
            print(f"📤 {region_name} {chunk_info} - 시설: {facilities_in_chunk}개, 바이트: {len(chunk.encode('utf-8'))}")

            if self._send_with_retry(chat_id, chunk, region_name, chunk_info):
                sent_facilities += facilities_in_chunk

        # 최종 무결성 검증
        if sent_facilities == total_facilities:
            print(f"✅ {region_name} - 모든 시설 전송 완료 ({sent_facilities}/{total_facilities})")
        else:
            print(f"❌ {region_name} - 시설 누락 발생! ({sent_facilities}/{total_facilities})")





    def send_to_all_regions(self, message):
        """모든 지역 채팅방에 공통 메시지 전송"""
        for region_code, chat_id in self.region_chat_ids.items():
            region_name = self.region_names[region_code]
            regional_message = f"📢 <b>전체 공지</b>\n\n{message}"
            self._send_with_retry(chat_id, regional_message, region_name)

    def test_all_connections(self):
        """모든 지역 채팅방 연결 테스트"""
        test_message = "🔧 <b>연결 테스트</b>\n\n휴양림 알림 봇이 정상적으로 연결되었습니다."
        for region_code, chat_id in self.region_chat_ids.items():
            region_name = self.region_names[region_code]
            self._send_with_retry(chat_id, test_message, region_name)