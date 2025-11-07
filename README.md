프로그램 작동 시 설치할 사항.
: Python 3.9+
: pip install opencv-python
: pip install opencv-python Pillow


프레임 선택 도구 (GUI)
: Tkinter (윈도우/MAC 은 기본 포함)


각 파일들 설명
1. run.py: 앱 실행 엔트리포인트 — 비디오/출력 경로 등 설정을 읽고 FrameSelectorApp을 시작합니다.

2. video_to_frames.py: OpenCV로 구간 프레임을 PNG로 저장하고 메타데이터(FPS/총프레임)를 제공합니다.

3. frame_selector.py: Tkinter GUI — 시간 구간 입력 → 썸네일 3단계 표시/넘김 → 최대 2장 선택/해제/삭제/확인 및 복사 저장까지 처리합니다.


작동 방법.

run.py에서 경로를 본인 환경에 맞게 수정합니다.
- VIDEO_PATH : 원본 동영상 경로
- OUTPUT_BASE : 프레임이 저장될 루트 폴더

그리고 TERMINAL에
: python run.py


