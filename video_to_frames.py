from pathlib import Path
import cv2

def info(msg):  print(f"[info] {msg}")
def warn(msg):  print(f"[warn] {msg}")
def error(msg): print(f"[error] {msg}")
def done(msg):  print(f"[done] {msg}")

def get_video_meta(video_path: Path):
    """
    (메타 읽기) 영상 파일에서 총 프레임 수와 FPS를 읽어온다.
    - 실패 시 RuntimeError 발생.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {video_path}")
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))  # 총 프레임 수
    fps   = float(cap.get(cv2.CAP_PROP_FPS)) or 0.0  # 초당 프레임(FPS)
    cap.release()
    return total, fps

def extract_frames_range(video_path: Path, output_dir: Path,
                         start_sec: float, end_sec: float,
                         zero_pad: int = 6, start_index: int = 0) -> int:
    """
    (프레임 추출 핵심)
    - video_path: 입력 영상 경로
    - output_dir: 프레임 PNG들을 저장할 디렉터리
    - start_sec ~ end_sec: 잘라낼 구간(초 단위)
    - zero_pad: 출력 파일명에 사용할 제로패딩 자릿수 (예: 000123.png)
    - start_index: 저장 파일의 시작 인덱스 (연속 저장 시 유용)

    반환값: 저장한 프레임 수
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {video_path}")

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps   = float(cap.get(cv2.CAP_PROP_FPS)) or 0.0

    # (로그) 입력/출력 정보 표시
    info(f"video: {video_path}")
    info(f"total frames (reported): {total if total > 0 else 'unknown'}")
    info(f"saving to: {output_dir.resolve()}")
    # 파일명 패턴 안내 (예: 000001.png 형태)
    info(f"filename pattern: {{index:0{zero_pad}d}}.png (start={start_index})")

    # FPS가 0 또는 NaN이면 추출 불가
    if fps <= 0:
        cap.release()
        raise RuntimeError("invalid FPS (0 or NaN).")

    # (초 → 프레임 인덱스) 변환 및 유효성 체크
    start_f = max(0, int(round(start_sec * fps)))
    end_f   = max(0, int(round(end_sec   * fps)))
    if end_f < start_f:
        cap.release()
        raise ValueError("end frame is before start frame.")

    # 출력 디렉터리 준비
    output_dir.mkdir(parents=True, exist_ok=True)   # 폴더 보장

    # (중요) 시작 프레임으로 이동
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_f)

    # 저장 인덱스 및 카운터 초기화
    idx_out = start_index  # 저장 파일명 인덱스 시작값
    saved = 0              # 실제 저장된 프레임 수
    cur_f = start_f        # 현재 읽을 프레임 인덱스

    # (핵심 루프) start_f ~ end_f 구간을 한 프레임씩 읽어 PNG로 저장
    while cur_f <= end_f:
        ok, frame = cap.read()
        if not ok:
            # 영상이 여기서 끝나거나 읽기 실패 시 중단
            break

        # 출력 파일 경로
        out_path = output_dir / f"{idx_out:0{zero_pad}d}.png"  # 예: ...\zzalkak_video\000000.png

        # PNG 저장 실패 시 즉시 에러
        if not cv2.imwrite(str(out_path), frame):   # 프레임 저장
            cap.release()
            raise RuntimeError(f"failed to write image: {out_path}")

        # 100장 단위로 진행 로그
        if idx_out % 100 == 0:
            info(f"saved: {out_path.name}")

        # 다음 프레임/파일 인덱스로 진행
        idx_out += 1
        saved += 1
        cur_f  += 1

    cap.release()
    done(f"saved {saved} frames to {output_dir.resolve()}")
    return saved
