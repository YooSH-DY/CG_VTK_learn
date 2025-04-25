# 테스트용 웹소켓 서버 (별도 파일로 저장)
import asyncio
import websockets


async def echo(websocket):
    print("클라이언트 연결됨!")
    try:
        async for message in websocket:
            print(f"수신: {message}")
            await websocket.send(f"에코: {message}")
    except websockets.exceptions.ConnectionClosed:
        print("클라이언트 연결 종료됨")
    except Exception as e:
        print(f"오류 발생: {e}")


async def main():
    async with websockets.serve(echo, "0.0.0.0", 5678):
        print(f"웹소켓 서버 시작 - 0.0.0.0:5678")
        await asyncio.Future()  # 무한 실행


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("서버가 중지되었습니다.")
