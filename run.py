from pathlib import Path
from video_to_frames import info
from frame_selector import FrameSelectorApp

# 사용자 환경 설정
VIDEO_PATH = Path(r"your\video\path") # 비디오 위치 (+ 비디오 이름)
OUTPUT_BASE = Path(r"Generated\frames\folder\locationc") # 생성될 frames 폴더 위치
ZERO_PAD = 6 # 저장 프레임의 자릿 수 (ex. 000000.png)
THUMB_SIZE = (860, 440) # 프레임 크기 설정.

if __name__ == "__main__":
    if not VIDEO_PATH.exists():
        raise FileNotFoundError(f"[error] video not found: {VIDEO_PATH}")

    # (정보) 실행 시 콘솔에 경로 정보 출력
    info(f"selected sequence dir: {VIDEO_PATH.stem}")
    info(f"output directory: {(OUTPUT_BASE / VIDEO_PATH.stem).resolve()}")

    # (중요) GUI 앱 실행 진입점
    app = FrameSelectorApp(
        video_path=VIDEO_PATH,
        output_base=OUTPUT_BASE,
        zero_pad=ZERO_PAD,
        # start_index=START_INDEX,  # 필요 시 위에 START_INDEX 정의 후 주석 해제
        thumb_size=THUMB_SIZE
    )
    app.mainloop()
