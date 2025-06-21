import requests
import configparser
import time


def format_facility(facility):
    """시설 정보 포맷팅 (최대 3,900자로 제한)"""
    facility_str = f"🏡 <b>{facility['name']}</b>\n"
    date_count = 0
    max_dates = 100  # 최대 100개 날짜만 표시

    for entry in facility['dates']:
        if date_count >= max_dates:
            remaining = len(facility['dates']) - max_dates
            facility_str += f"  └ ... 외 {remaining}개 더\n"
            break

        line = f"  └ {entry['date']} : <b>{entry['status']}</b>\n"
        # UTF-8 바이트 길이 기반 체크 추가
        if len(facility_str.encode('utf-8')) + len(line.encode('utf-8')) > 3900:
            remaining = len(facility['dates']) - date_count
            facility_str += f"  └ ... 외 {remaining}개 더\n"
            break

        facility_str += line
        date_count += 1

    return facility_str + "\n"


def safe_split(text, max_len=4000):  # 4096 - 96 (안전 마진)
    """메시지를 안전하게 분할 (UTF-8 바이트 길이 기반)"""
    parts = []
    encoded_text = text.encode('utf-8')
    total_bytes = len(encoded_text)

    start_index = 0
    while total_bytes - start_index > max_len:
        # 현재 청크의 최대 바이트 범위 내에서 분할 포인트 찾기
        end_index = start_index + max_len
        chunk = encoded_text[start_index:end_index]

        # 마지막 유효한 분할 지점 찾기 (개행 > 공백 > 강제)
        split_pos = -1
        for marker in [b'\n\n', b'\n', b'. ', b'! ', b'? ', b' ']:
            pos = chunk.rfind(marker)
            if pos != -1:
                split_pos = pos
                break

        if split_pos == -1:
            split_pos = len(chunk) - 50  # 안전 마진

        # 실제 분할 위치 계산
        actual_split = start_index + split_pos + len(marker) if split_pos != -1 else end_index
        parts.append(encoded_text[start_index:actual_split].decode('utf-8', 'ignore'))
        start_index = actual_split

    # 마지막 청크 추가
    if start_index < total_bytes:
        parts.append(encoded_text[start_index:].decode('utf-8', 'ignore'))

    return parts


def send_telegram_message(context_info, result_data):
    """분할 전송이 포함된 스크래핑 데이터 전송"""
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')

    token = config.get('TELEGRAM', 'TOKEN')
    chat_id = config.get('TELEGRAM', 'CHAT_ID')

    if not result_data or len(result_data) == 0:
        return

    # 1. 헤더 생성
    header = f"🔄 <b>예약 현황 발견!</b>\n"
    header += f"📅 {context_info['month']}\n"
    header += f"🌍 {context_info['region']}\n"
    header += f"🌲 {context_info['forest']}\n"
    header += f"🏠 {context_info['accommodation']}\n"
    header += f"{'=' * 30}\n"

    # 2. 시설 정보 포맷팅
    full_message = header
    for facility in result_data:
        if facility['dates']:
            full_message += format_facility(facility)

    # 3. 메시지 분할
    byte_length = len(full_message.encode('utf-8'))
    print(f"📏 전체 메시지 크기: {byte_length} 바이트")

    if byte_length > 4000:
        chunks = safe_split(full_message)
        # 첫 청크에 요약 정보 추가
        summary = f"📊 총 {len(result_data)}개 시설 | "
        summary += f"예약 일자: {sum(len(f['dates']) for f in result_data)}개\n"
        chunks[0] = summary + chunks[0]
    else:
        chunks = [full_message]

    # 4. 분할 전송
    for i, chunk in enumerate(chunks):
        # 최종 UTF-8 바이트 길이 검증
        chunk_bytes = len(chunk.encode('utf-8'))
        if chunk_bytes > 4096:
            print(f"⚠️ 경고! 청크 {i + 1} 길이 초과 ({chunk_bytes}/4096). 축소 중...")
            # UTF-8 바이트 기준으로 정확히 축소
            encoded = chunk.encode('utf-8')
            safe_chunk = encoded[:4090].decode('utf-8', 'ignore') + "..."
            chunk = safe_chunk

        if i > 0:
            chunk = f"📄 [이어서] ({i + 1}/{len(chunks)})\n" + chunk

        print(f"📤 청크 {i + 1}/{len(chunks)} 전송 ({len(chunk)}자, {len(chunk.encode('utf-8'))}바이트)")
        _send_message(token, chat_id, chunk)
        time.sleep(0.5)  # 전송 간 간격


def _send_message(token, chat_id, message):
    """실제 메시지 전송 (UTF-8 바이트 길이 최종 검증)"""
    # 최종 안전장치: UTF-8 바이트 길이 확인
    byte_length = len(message.encode('utf-8'))
    if byte_length > 4096:
        print(f"❌ 치명적 오류! 메시지 길이 초과: {byte_length}바이트")
        # 메시지 강제 축소
        safe_msg = message.encode('utf-8')[:4090].decode('utf-8', 'ignore')
        safe_msg += "... [TRUNCATED]"
        message = safe_msg

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, data=payload, timeout=15)
        if response.ok:
            print("✅ 텔레그램 전송 성공")
        else:
            print(f"❌ 전송 실패: {response.text}")
            # 실패 응답 전체 기록
            print(f"응답 상세: {response.json()}")
    except Exception as e:
        print(f"❌ 전송 오류: {str(e)}")