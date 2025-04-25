# 핑/퐁 기능과 재연결 개선
import asyncio
import websockets
import json
import threading
import time
import logging
import re

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("DOT_WS_Server")

# 전역 데이터 저장 변수
dot_data = {
    "DOT1": {"roll": 0, "pitch": 0, "yaw": 0},  # 손등 센서
    "DOT2": {"roll": 0, "pitch": 0, "yaw": 0},  # 손가락 센서
}

# 선택된 손가락 인덱스
selected_fingers = [1]  # 기본적으로 검지와 중지 선택

# 웹소켓 연결 객체와 상태 관리
active_connection = None
connection_lock = threading.Lock()
server_running = True
connection_timeout = 180  # 연결 타임아웃 (초)
ping_interval = 10  # 핑 간격 (초)

# 연결 상태 및 데이터 수신 시간 추적
connection_status = False
last_data_time = 0

# 재연결 관련 변수
reconnect_attempts = 0
max_reconnect_attempts = 10
reconnect_interval = 5  # 초


def select_fingers(*finger_indices):
    """
    제어할 손가락 선택 함수
    :param finger_indices: 손가락 인덱스 (0: 엄지, 1: 검지, 2: 중지, 3: 약지, 4: 소지)
    """
    global selected_fingers
    selected_fingers = list(finger_indices)
    logger.info(f"선택된 손가락: {selected_fingers}")
    return selected_fingers


# 클라이언트에 핑 메시지를 보내는 함수
async def send_ping(websocket):
    """웹소켓 연결 유지를 위한 핑 전송"""
    try:
        # 연결 후 즉시 데이터 요청 메시지 전송
        await websocket.send(
            json.dumps(
                {"type": "request_data", "message": "데이터 스트리밍을 시작해주세요"}
            )
        )
        logger.info("클라이언트에 데이터 요청 메시지 전송됨")

        # 이후 정기적인 핑 메시지 전송
        while True:
            await asyncio.sleep(ping_interval)
            try:
                await websocket.send(
                    json.dumps({"type": "ping", "timestamp": time.time()})
                )
                logger.debug("핑 메시지 전송")
            except websockets.exceptions.ConnectionClosed:
                logger.warning("웹소켓 연결이 닫혀 있어 핑 전송을 중단합니다.")
                break
    except websockets.exceptions.ConnectionClosed:
        logger.warning("핑 전송 중 연결이 닫혔습니다.")
    except Exception as e:
        logger.error(f"핑 전송 오류: {e}")


async def handle_websocket(websocket):
    global active_connection, dot_data, last_data_time, connection_status

    # 연결 정보 저장
    with connection_lock:
        active_connection = websocket
        connection_status = True  # 연결됨 표시

    client_address = websocket.remote_address
    logger.info(f"클라이언트 연결됨: {client_address[0]}:{client_address[1]}")
    last_data_time = time.time()  # 연결 시 시간 초기화

    try:
        # 환영 메시지 전송
        await websocket.send(
            json.dumps({"type": "server_ready", "message": "연결 성공"})
        )

        # 핑 전송 태스크 시작
        ping_task = asyncio.create_task(send_ping(websocket))

        # 클라이언트 메시지 수신
        async for message in websocket:
            try:
                # 핑-퐁 처리
                if message.startswith("{") and '"type":"pong"' in message:
                    logger.debug("퐁 메시지 수신")
                    last_data_time = time.time()  # 핑-퐁 메시지도 활동으로 간주
                    continue

                # JSON 형식 처리 (DOT 센서 데이터)
                if message.startswith("{") and '"type":"dotSensorData"' in message:
                    # deviceId 추출
                    id_match = re.search(r'"deviceId":"(.*?)"', message)
                    device_id = id_match.group(1) if id_match else ""

                    # Roll, Pitch, Yaw 값 추출
                    roll_match = re.search(r'"r":"?([-\d.]+)"?', message)
                    pitch_match = re.search(r'"p":"?([-\d.]+)"?', message)
                    yaw_match = re.search(r'"y":"?([-\d.]+)"?', message)

                    # 값 변환
                    roll = float(roll_match.group(1)) if roll_match else 0
                    pitch = float(pitch_match.group(1)) if pitch_match else 0
                    yaw = float(yaw_match.group(1)) if yaw_match else 0

                    # 장치별 데이터 저장
                    if device_id in ["DOT1", "DOT2"]:
                        dot_data[device_id] = {"roll": roll, "pitch": pitch, "yaw": yaw}
                        last_data_time = time.time()  # 마지막 데이터 수신 시간 업데이트
                        logger.debug(
                            f"{device_id} 데이터 수신: roll={roll:.1f}°, pitch={pitch:.1f}°, yaw={yaw:.1f}°"
                        )
                else:
                    logger.debug(f"기타 메시지: {message}")
                    last_data_time = time.time()  # 모든 메시지 수신을 활동으로 간주

            except Exception as e:
                logger.error(f"메시지 처리 오류: {e}")

    except websockets.exceptions.ConnectionClosed:
        logger.warning("클라이언트 연결 종료됨")
    except Exception as e:
        logger.error(f"웹소켓 처리 중 오류 발생: {e}")
    finally:
        # 핑 태스크 취소
        if "ping_task" in locals():
            ping_task.cancel()

        # 연결 종료 시 정리
        with connection_lock:
            if active_connection == websocket:
                active_connection = None
                connection_status = False  # 연결 끊김 표시
                logger.info("웹소켓 연결 객체 정리 완료")


def get_normalized_roll(value, max_angle=80):
    """
    Roll 값을 -max_angle~max_angle 범위로 정규화하는 함수
    :param value: 원본 Roll 값 (-180~180)
    :param max_angle: 최대 각도 (기본값: 80도)
    :return: -max_angle~max_angle 사이의 값
    """
    # 부호 유지하면서 크기 제한
    if value < 0:
        # 음수(앞으로 구부림) - 최대 각도까지 허용
        return max(value, -max_angle)
    else:
        # 양수(뒤로 젖힘) - 최대 20도까지만 허용
        return min(value, 20)  # 뒤로는 20도까지만


# 자동 재연결 함수
async def monitor_connection():
    """연결 상태를 모니터링하고 필요시 재연결을 시도하는 함수"""
    global reconnect_attempts, connection_status, last_data_time, server

    while server_running:
        current_time = time.time()

        # 연결이 끊겼거나 데이터가 일정 시간 이상 수신되지 않은 경우
        if not connection_status or (
            current_time - last_data_time > connection_timeout and last_data_time > 0
        ):
            logger.warning("연결이 끊겼거나 데이터 수신이 없습니다. 재연결 시도...")

            if reconnect_attempts < max_reconnect_attempts:
                reconnect_attempts += 1
                logger.info(
                    f"재연결 시도 중 ({reconnect_attempts}/{max_reconnect_attempts})..."
                )

                # 기존 서버 객체 정리
                if "server" in globals():
                    server.close()

                try:
                    # 새 서버 시작
                    server = await websockets.serve(
                        handle_websocket,
                        "192.168.0.213",
                        5678,
                        ping_interval=10,
                        ping_timeout=30,
                        close_timeout=10,
                    )
                    logger.info("웹소켓 서버 재시작 성공")
                    reconnect_attempts = 0  # 성공 시 카운터 리셋
                except Exception as e:
                    logger.error(f"재연결 실패: {e}")
            else:
                logger.error("최대 재연결 시도 횟수 초과")
                reconnect_attempts = 0  # 일정 시간 후 다시 시도할 수 있도록 리셋
                await asyncio.sleep(60)  # 1분 대기 후 다시 시도

        # 연결 모니터링 간격
        await asyncio.sleep(10)


async def websocket_server():
    global server_running, last_data_time, server

    last_data_time = time.time()

    # 연결 시간 설정 - 타임아웃 방지
    server = await websockets.serve(
        handle_websocket,
        "192.168.0.213",
        5678,
        ping_interval=10,  # 10초마다 웹소켓 내부 핑 (더 자주)
        ping_timeout=30,  # 핑 타임아웃 시간 (초)
        close_timeout=10,  # 연결 종료 시간 (초)
    )

    logger.info("웹소켓 서버 시작 (192.168.0.213:5678)")
    logger.info("클라이언트 연결 대기 중... 앱에서 연결을 시작해주세요.")

    # 연결 모니터링 태스크 시작
    monitor_task = asyncio.create_task(monitor_connection())

    try:
        while server_running:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        logger.info("웹소켓 서버 태스크 취소됨")
    finally:
        monitor_task.cancel()
        server.close()
        await server.wait_closed()
        logger.info("웹소켓 서버 종료됨")


def start_websocket_server_thread():
    """별도 스레드에서 웹소켓 서버 실행"""

    def run_server():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(websocket_server())
        except Exception as e:
            logger.error(f"웹소켓 서버 실행 중 오류 발생: {e}")
        finally:
            loop.close()

    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True  # 메인 스레드 종료 시 함께 종료
    server_thread.start()
    logger.info("웹소켓 서버 스레드 시작됨")
    logger.info("연결 대기 중... 이 메시지가 보이면 서버가 성공적으로 시작된 것입니다.")
    return server_thread


# 호환성을 위한 기존 함수
def start_websocket_client_thread():
    """호환성을 위한 래퍼 함수"""
    return start_websocket_server_thread()


# 테스트 코드
if __name__ == "__main__":
    logger.info("웹소켓 서버 단독 실행 모드")

    # 웹소켓 서버 시작
    start_websocket_server_thread()

    try:
        # 현재 DOT 데이터 주기적으로 출력
        while True:
            logger.info(f"DOT1: {dot_data['DOT1']} (연결 상태: {connection_status})")
            logger.info(f"DOT2: {dot_data['DOT2']} (선택된 손가락: {selected_fingers})")

            # 마지막 데이터 수신 시간과 경과 시간 출력
            if last_data_time > 0:
                elapsed = time.time() - last_data_time
                logger.info(f"마지막 데이터 수신 후 경과 시간: {elapsed:.1f}초")

            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("프로그램 종료")
        server_running = False
