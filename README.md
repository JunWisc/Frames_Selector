프로그램 작동 시 설치할 사항.
1. Python 3.9+
   
2. pip install opencv-python
   
3. pip install opencv-python Pillow


프레임 선택 도구 (GUI).
: Tkinter (윈도우/MAC 은 기본 포함)


각 파일들 설명.
1. run.py: 앱 실행 엔트리포인트 — 비디오/출력 경로 등 설정을 읽고 FrameSelectorApp을 시작합니다.

2. video_to_frames.py: OpenCV로 구간 프레임을 PNG로 저장하고 메타데이터(FPS/총프레임)를 제공합니다.

3. frame_selector.py: Tkinter GUI — 시간 구간 입력 → 썸네일 3단계 표시/넘김 → 최대 2장 선택/해제/삭제/확인 및 복사 저장까지 처리합니다.


작동 방법.
run.py에서 경로를 본인 환경에 맞게 수정합니다.
- VIDEO_PATH : 원본 동영상 경로
- OUTPUT_BASE : 프레임이 저장될 루트 폴더

그리고 TERMINAL에
```bash
python run.py
'''

python run.py를 하면 OUTPUT_BASE 에 작성된 주소와 폴더가 자동으로 생성됩니다.
이때, 폴더 명은 비디오 이름과 같습니다.
시간을 설정하고 확인을 누르면 생성된 폴더에 프레임들이 생성됩니다.
