프로그램 작동 시 설치할 사항
1. Python 3.9+
2. pip install opencv-python
3. pip install Pillow

프레임 선택 도구 (GUI)
- Tkinter (Windows / macOS 는 기본 포함)

각 파일들 설명
1. run.py  
   - 앱 실행 엔트리포인트 — 비디오/출력 경로 등 설정을 읽고 FrameSelectorApp을 시작합니다.

2. video_to_frames.py  
   - OpenCV로 구간 프레임을 PNG로 저장하고 메타데이터(FPS/총 프레임)를 제공합니다.

3. frame_selector.py  
   - Tkinter GUI — 시간 구간 입력 → 썸네일 3단계 표시/넘김 → 최대 2장 선택/해제/삭제/확인 및 복사 저장까지 처리합니다.  
   - 선택 및 저장이 완료되면, 임시 프레임 폴더(영상 이름 폴더)는 자동으로 삭제됩니다.

작동 방법
- run.py에서 경로를 본인 환경에 맞게 수정합니다.
  - VIDEO_PATH : 원본 동영상 경로
  - OUTPUT_BASE : 프레임이 저장될 루트 폴더

그리고 TERMINAL에

```bash
python run.py
```

python run.py를 실행하면 `OUTPUT_BASE`에 작성된 주소와 폴더가 자동으로 생성됩니다.  
이때, 폴더명은 비디오 이름과 같습니다.  
시간을 설정하고 확인 버튼을 누르면, 생성된 폴더 안에 해당 구간의 프레임들이 PNG로 저장됩니다.  
최종적으로 2장의 프레임을 선택해 저장을 완료하면, 생성에 사용된 임시 프레임 폴더는 자동으로 삭제됩니다.

