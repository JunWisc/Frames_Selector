import threading
import tkinter.font as tkfont  # frame GUI
import random
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk
import shutil
import os

from video_to_frames import (
    info, warn, done,
    get_video_meta, extract_frames_range
)


class FrameSelectorApp(tk.Tk):
    def __init__(self, video_path: Path, output_base: Path,
                 zero_pad: int = 6, start_index: int = 0,
                 thumb_size=(600, 400)):  # 썸네일 크기
        super().__init__()
        self.title("Frame Range")
        self.geometry("1280x900")  # (설정) 창 크기. UI 전체 스케일에 영향

        # (설정) 전역 폰트 - 버튼/라벨/입력창 기본 크기
        self.ui_font = tkfont.Font(family="Arial", size=14)
        self.ui_font_big = tkfont.Font(family="Arial", size=16)
        self.ui_font_huge = tkfont.Font(family="Arial", size=18)

        # (설정) 입출력/이름 포맷
        self.video_path = video_path
        self.output_base = output_base    # 예: C:\...\zzalkak\frames
        self.zero_pad = zero_pad          # 저장 파일명 0패딩 자릿수
        self.start_index = start_index    # 저장 시작 인덱스
        self.thumb_size = thumb_size      # (설정) 중앙 썸네일 표시 크기

        self.video_stem = self.video_path.stem               # 예: "zzalkak_video"
        self.output_dir = self.output_base / self.video_stem # 실제 저장 폴더; 예: C:\...\zzalkak\frames\zzalkak_video
        self.output_dir.mkdir(parents=True, exist_ok=True)   # 폴더 실제 생성

        # 메타
        self.total_frames, self.fps = get_video_meta(self.video_path)
        self.duration_sec = (self.total_frames / self.fps) if (self.fps > 0 and self.total_frames > 0) else 0.0

        # 상태
        self.all_frame_files = []
        self.shown_stages = []        # 각 stage별 파일 리스트
        self.selected_files = []      # 사용자가 고른 파일 경로 (최대 2)
        self.index_map = {}           # (중요) 파일경로 -> 전역 번호(1~12) 매핑

        # (설정) 스테이지(페이지) 관련
        self.stage = 0
        self.stage_idx = -1
        self.max_stages = 3           # (설정) 총 스테이지 수. 변경 시 번호(1~12) 범위도 함께 바뀜

        # UI 루트 요소 참조
        self.thumb_panel = None
        self.retry_btn = None
        self.prev_btn = None
        self.loading_label = None
        self.time_form = None
        self.time_form_inner = None
        self.retime_btn = None

        # 상단바 컨테이너 (시간 다시 설정 버튼)
        self.top_bar = None

        # (레이아웃) 왼쪽(썸네일/네비 영역) + 중앙 정렬 래퍼
        self.left_container = None
        self.center_wrapper = None

        # 우측 선택 사이드패널
        self.selected_panel = None
        self._sel_tkimgs = []

        # (초기 화면) 시간 입력 폼부터
        self._build_time_form()

    # 스테이지별 번호 부여 유틸
    def _assign_numbers_for_stage(self, stage_index: int, file_list: list[str]):
        """
        stage_index: 0,1,2 ...
        file_list: 해당 스테이지에서 표시될 4개(또는 그 이하) 파일 경로 리스트.
        전역 번호는 스테이지 순서 * 4 + (해당 스테이지 내 위치 0..3) + 1
        예) stage_index=0 -> 1~4, stage_index=1 -> 5~8 ...
        """
        base = stage_index * 4
        for i, fp in enumerate(file_list):
            if fp not in self.index_map:
                self.index_map[fp] = base + i + 1

    # 우측 선택 패널
    def _build_selected_panel(self):
        if self.selected_panel:
            self.selected_panel.destroy()
        self.selected_panel = tk.Frame(self, bd=1, relief=tk.GROOVE)
        self.selected_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=12, pady=12)

        header = tk.Label(self.selected_panel, text="선택된 이미지 (최대 2)",
                          font=self.ui_font_big)
        header.pack(pady=(6, 10))

        self.selected_list = tk.Frame(self.selected_panel)
        self.selected_list.pack(fill=tk.Y, expand=False)

        self.selected_hint = tk.Label(
            self.selected_panel,
            text="아직 선택 없음",
            fg="#666",
            font=self.ui_font
        )
        self.selected_hint.pack(pady=(10, 4))

        btns = tk.Frame(self.selected_panel)
        btns.pack(pady=(12, 4), fill=tk.X)

        # (동작) 삭제 버튼: 선택이 1장이상일 때만 활성화
        self.delete_btn = tk.Button(
            btns, text="삭제", font=self.ui_font_big,
            command=self._on_delete_selected, state=tk.DISABLED
        )
        self.delete_btn.pack(side=tk.LEFT, padx=(0, 6), fill=tk.X, expand=True)

        # (동작) 확인 버튼: 선택이 정확히 2장일 때만 활성화
        self.confirm_btn_sel = tk.Button(
            btns, text="확인", font=self.ui_font_big,
            command=self._on_confirm_selected, state=tk.DISABLED
        )
        self.confirm_btn_sel.pack(side=tk.LEFT, padx=(6, 0), fill=tk.X, expand=True)

    def _refresh_selected_panel(self):
        if not self.selected_panel:
            return

        # (UI 갱신) 기존 썸네일 클리어
        for child in self.selected_list.winfo_children():
            child.destroy()
        self._sel_tkimgs = []

        count = len(self.selected_files)
        if count == 0:
            self.selected_hint.config(text="아직 선택 없음")
        else:
            self.selected_hint.config(text=f"{count}/2 선택됨")

        # (설정) 선택된 이미지 박스 미리보기 배율
        #  - 중앙 썸네일(self.thumb_size) 대비 상대 크기
        scale = 0.5
        sel_w = int(self.thumb_size[0] * scale)
        sel_h = int(self.thumb_size[1] * scale)
        sel_size = (sel_w, sel_h)

        for _, fp in enumerate(self.selected_files[:2], start=1):
            try:
                img = Image.open(fp).convert("RGB")
                img.thumbnail(sel_size)
                tkimg = ImageTk.PhotoImage(img)
                self._sel_tkimgs.append(tkimg)

                box = tk.Frame(self.selected_list)
                box.pack(pady=6)

                # 선택 썸네일(항상 파란 테두리)
                lbl = tk.Label(
                    box, image=tkimg,
                    bd=2, relief=tk.SOLID,
                    highlightthickness=2,
                    highlightbackground="#00AEEF",
                    highlightcolor="#00AEEF"
                )
                lbl.pack()

                # (중요) 파일명 대신 전역 번호만 아래에 표시 (예: "7")
                num = self.index_map.get(fp, "?")
                cap = tk.Label(box, text=str(num), font=self.ui_font)
                cap.pack(pady=(4, 0))
            except Exception as e:
                warn(f"cannot open selected thumbnail: {fp} ({e})")

        # (버튼 상태) 삭제/확인 활성화 조건
        self.delete_btn.config(state=(tk.NORMAL if len(self.selected_files) >= 1 else tk.DISABLED))
        self.confirm_btn_sel.config(state=(tk.NORMAL if len(self.selected_files) == 2 else tk.DISABLED))

    # 시간 폼
    def _build_time_form(self):
        self.time_form = tk.Frame(self)
        self.time_form.pack(fill=tk.BOTH, expand=True)

        # (레이아웃) 시간 입력 폼을 화면 정중앙에 배치
        self.time_form_inner = tk.Frame(self.time_form)
        self.time_form_inner.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(self.time_form_inner, text="Start (mm:ss)", font=self.ui_font_big).grid(
            row=0, column=0, padx=8, pady=8, sticky="e"
        )
        self.start_min = tk.Entry(self.time_form_inner, width=6, font=self.ui_font)
        self.start_sec = tk.Entry(self.time_form_inner, width=6, font=self.ui_font)
        self.start_min.insert(0, "0")
        self.start_sec.insert(0, "0")
        self.start_min.grid(row=0, column=1, padx=4, pady=4, sticky="w")
        self.start_sec.grid(row=0, column=2, padx=4, pady=4, sticky="w")

        tk.Label(self.time_form_inner, text="End (mm:ss)", font=self.ui_font_big).grid(
            row=1, column=0, padx=8, pady=8, sticky="e"
        )
        self.end_min = tk.Entry(self.time_form_inner, width=6, font=self.ui_font)
        self.end_sec = tk.Entry(self.time_form_inner, width=6, font=self.ui_font)
        total_m = int(self.duration_sec // 60)
        total_s = int(round(self.duration_sec - total_m * 60))
        self.end_min.insert(0, str(total_m))
        self.end_sec.insert(0, str(total_s))
        self.end_min.grid(row=1, column=1, padx=4, pady=4, sticky="w")
        self.end_sec.grid(row=1, column=2, padx=4, pady=4, sticky="w")

        self.confirm_btn = tk.Button(
            self.time_form_inner, text="확인", command=self.on_confirm_time,
            font=self.ui_font_huge, padx=12, pady=6
        )
        self.confirm_btn.grid(row=2, column=0, columnspan=3, pady=(14, 6))

        tk.Label(
            self.time_form_inner,
            text=f"Video length: {total_m:02d}:{total_s:02d} (mm:ss)",
            font=self.ui_font
        ).grid(row=3, column=0, columnspan=3, pady=8)

    def _parse_mmss(self, m_entry: tk.Entry, s_entry: tk.Entry):
        try:
            m = int(m_entry.get().strip())
            s = int(s_entry.get().strip())
            if m < 0 or s < 0 or s >= 60:
                return None
            return m * 60 + s
        except Exception:
            return None

    def on_confirm_time(self):
        start_s = self._parse_mmss(self.start_min, self.start_sec)
        end_s   = self._parse_mmss(self.end_min, self.end_sec)

        if start_s is None or end_s is None:
            messagebox.showwarning("Invalid", "Please enter the time again.")
            return
        if self.duration_sec <= 0:
            messagebox.showwarning("Invalid", "Video duration unknown/invalid.")
            return
        if start_s < 0 or end_s < 0 or start_s >= end_s:
            messagebox.showwarning("Invalid", "Please enter the time again.")
            return
        if start_s > self.duration_sec or end_s > self.duration_sec:
            messagebox.showwarning("Invalid", "Please enter the time again.")
            return

        # (동작) 시간 확정 후 입력 비활성화
        self.confirm_btn.config(state=tk.DISABLED)
        for w in (self.start_min, self.start_sec, self.end_min, self.end_sec):
            w.config(state=tk.DISABLED)

        # (설정) 로딩 문구 위치/크기: 화면 세로 75% 높이 중앙
        #  - 더 위로: rely=0.2 / 더 아래로: rely=0.8
        self.loading_label = tk.Label(self, text="Loading..", font=self.ui_font_huge)
        self.loading_label.place(relx=0.5, rely=0.75, anchor="center")

        # (성능) 프레임 추출은 스레드로 처리하여 GUI 멈춤 방지
        t = threading.Thread(target=self._extract_and_then_show, args=(start_s, end_s), daemon=True)
        t.start()

    # 프레임 추출 & 썸네일
    def _extract_and_then_show(self, start_s: float, end_s: float):
        if not self.video_path.exists():
            self.after(0, lambda: messagebox.showerror("Error", f"Video not found:\n{self.video_path}"))
            return

        info(f"output directory: {self.output_dir.resolve()}")
        try:
            extract_frames_range(
                video_path=self.video_path,
                output_dir=self.output_dir,   # 위에서 만든 "frames/동영상이름" 경로
                start_sec=start_s,
                end_sec=end_s,
                zero_pad=self.zero_pad,
                start_index=self.start_index
            )
        except Exception as e:
            msg = str(e)
            self.after(0, lambda m=msg: messagebox.showerror("Error", m))
            return

        # (중요) 추출된 프레임을 정렬하여 표시 대상 리스트 구성
        self.all_frame_files = [str(p) for p in sorted(self.output_dir.glob("*.png"))]
        self.after(0, self._after_loading)

    def _after_loading(self):
        if self.loading_label:
            self.loading_label.destroy()
            self.loading_label = None

        if self.time_form:
            self.time_form.pack_forget()

        # (레이아웃) 상단 버튼(썸네일 위, 오른쪽 정렬) 먼저 배치
        self._show_retime_button()

        # (레이아웃) 썸네일 영역 구성 후 첫 스테이지 렌더
        self._build_thumb_panel()
        self._reset_stages()
        self._next_stage()

        # (레이아웃) 우측 선택 패널은 썸네일이 뜬 뒤 생성
        self._build_selected_panel()
        self._refresh_selected_panel()

    # 스테이지 상태 초기화
    def _reset_stages(self):
        self.selected_files = []
        self.shown_stages = []
        self.index_map = {}      # (중요) 번호 매핑 초기화
        self.stage_idx = -1
        self.stage = 0

    def _build_thumb_panel(self):
        # (레이아웃) 왼쪽 전체 컨테이너
        if self.left_container:
            self.left_container.destroy()
            self.left_container = None
        self.left_container = tk.Frame(self)
        self.left_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # (레이아웃) 중앙 정렬용 래퍼
        if self.center_wrapper:
            self.center_wrapper.destroy()
            self.center_wrapper = None
        self.center_wrapper = tk.Frame(self.left_container)
        self.center_wrapper.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # (레이아웃) 썸네일 그리드 패널
        if self.thumb_panel:
            self.thumb_panel.destroy()
        self.thumb_panel = tk.Frame(self.center_wrapper)
        self.thumb_panel.pack(padx=16, pady=12, anchor='n')  # (설정) 썸네일 주변 여백

        # (레이아웃) 페이지 네비게이션 버튼 컨트롤 바
        ctrl = tk.Frame(self.center_wrapper)
        ctrl.pack(pady=(0, 12), anchor='n')

        # (동작) 이전 페이지 버튼: 첫 스테이지에서는 비활성
        self.prev_btn = tk.Button(
            ctrl, text="Previous Page", command=self._on_prev,
            font=self.ui_font_big, padx=10, pady=6, state=tk.DISABLED
        )
        self.prev_btn.pack(side=tk.LEFT, padx=(0, 8))

        # (동작) 다음 페이지 버튼: 마지막 스테이지에서 비활성
        self.retry_btn = tk.Button(
            ctrl, text="Next Page", command=self._on_retry,
            font=self.ui_font_big, padx=10, pady=6
        )
        self.retry_btn.pack(side=tk.LEFT, padx=(8, 0))

    def _on_prev(self):
        if self.stage_idx > 0:
            self.stage_idx -= 1
            self.stage = self.stage_idx + 1
            self._render_thumbs(self.shown_stages[self.stage_idx])
            if self.stage_idx == 0:
                self.prev_btn.config(state=tk.DISABLED)
            self._update_next_btn_state()

    def _on_retry(self):
        if self.stage_idx + 1 < len(self.shown_stages):
            self.stage_idx += 1
            self.stage = self.stage_idx + 1
            self._render_thumbs(self.shown_stages[self.stage_idx])
        else:
            if len(self.shown_stages) >= self.max_stages:
                self._update_next_btn_state()
                return
            self._next_stage()

        if self.stage_idx >= 1:
            self.prev_btn.config(state=tk.NORMAL)
        self._update_next_btn_state()

    def _update_next_btn_state(self):
        # (동작) 마지막 스테이지에서는 Next Page 비활성화
        if len(self.shown_stages) >= self.max_stages and self.stage_idx == self.max_stages - 1:
            self.retry_btn.config(state=tk.DISABLED)
        else:
            self.retry_btn.config(state=tk.NORMAL)

    def _next_stage(self):
        if len(self.shown_stages) >= self.max_stages:
            self._update_next_btn_state()
            return

        # (로직) 이미 보인 프레임 제외하고 랜덤 샘플링
        shown_set = set(sum(self.shown_stages, []))
        candidates = [p for p in self.all_frame_files if p not in shown_set]
        if len(candidates) == 0 and len(self.all_frame_files) > 0:
            candidates = list(self.all_frame_files)

        k = min(4, len(candidates))  # (설정) 한 페이지당 썸네일 수
        if k == 0:
            return

        stage_files = random.sample(candidates, k)
        self.shown_stages.append(stage_files)

        self.stage_idx += 1
        self.stage = self.stage_idx + 1

        # (중요) 이 스테이지의 전역 번호를 미리 부여
        self._assign_numbers_for_stage(self.stage_idx, stage_files)

        self._render_thumbs(stage_files)

        if self.stage_idx >= 1:
            self.prev_btn.config(state=tk.NORMAL)
        self._update_next_btn_state()

    def _render_thumbs(self, file_list):
        # (UI 갱신) 이전 썸네일 제거
        for child in self.thumb_panel.winfo_children():
            child.destroy()

        self._thumb_imgs = []

        # 혹시 번호가 비어있다면 현재 스테이지 기준으로 보정
        self._assign_numbers_for_stage(self.stage_idx, file_list)

        # 썸네일 클릭 토글: 선택 ↔ 해제
        def toggle_select(filepath):
            if filepath in self.selected_files:
                self.selected_files.remove(filepath)
            else:
                if len(self.selected_files) >= 2:
                    messagebox.showinfo("Limit", "최대 2장까지만 선택할 수 있어요.")
                    return
                self.selected_files.append(filepath)
            # (UI) 테두리/라벨 반영 위해 재렌더 + 우측 패널 즉시 갱신
            self._render_thumbs(file_list)
            self._refresh_selected_panel()

        cols = 2  # (설정) 썸네일 그리드 열 수
        for i, fp in enumerate(file_list):
            try:
                img = Image.open(fp).convert("RGB")
                img.thumbnail(self.thumb_size)  # (설정) 중앙 썸네일 크기 적용
                tkimg = ImageTk.PhotoImage(img)
                self._thumb_imgs.append(tkimg)

                is_selected = fp in self.selected_files

                # (UI) 선택 시 파란 테두리 강조
                relief = tk.SOLID if is_selected else tk.FLAT
                bd = 3 if is_selected else 1
                hl_thick = 2 if is_selected else 1
                hl_color = "#00AEEF" if is_selected else "#CCCCCC"

                # (레이아웃) 셀 컨테이너: 번호 라벨(위) + 캔버스(아래)
                cell = tk.Frame(self.thumb_panel)
                cell.grid(row=i // cols, column=i % cols, padx=12, pady=12)

                num = self.index_map.get(fp, "?")

                # (UI) 번호 라벨 - 이미지 '바깥' 상단(왼쪽 정렬)
                num_label = tk.Label(
                    cell,
                    text=str(num),
                    font=self.ui_font_big,
                    anchor='w'
                )
                num_label.pack(side=tk.TOP, anchor='w')

                # (UI) 이미지 표시 캔버스 + 선택 테두리 스타일
                canvas = tk.Canvas(
                    cell,
                    width=tkimg.width(),
                    height=tkimg.height(),
                    bd=bd,
                    relief=relief,
                    highlightthickness=hl_thick,
                    highlightbackground=hl_color,
                    highlightcolor=hl_color
                )
                canvas.pack(side=tk.TOP)

                canvas.create_image(0, 0, anchor='nw', image=tkimg)

                # (동작) 이미지/번호 라벨 클릭 -> 선택 토글
                num_label.bind("<Button-1>", lambda e, F=fp: toggle_select(F))
                canvas.bind("<Button-1>", lambda e, F=fp: toggle_select(F))

            except Exception as e:
                warn(f"cannot open/thumbnail: {fp} ({e})")

        # (안내 문구) 마지막 스테이지에서는 '필요시 Next Page.' 제외
        base_text = f"Stage {self.stage}/{self.max_stages} — 이미지를 클릭해 선택 (최대 2장)."
        if self.stage < self.max_stages:
            guide_text = base_text + " 필요시 Next Page."
        else:
            guide_text = base_text

        guide = tk.Label(
            self.thumb_panel,
            text=guide_text,
            font=self.ui_font_big
        )
        guide.grid(row=(len(file_list) + 1) // cols + 1, column=0, columnspan=cols, pady=(8, 0))

        if self.stage == self.max_stages:
            tail = tk.Label(
                self.thumb_panel,
                text="(우측 '확인' 버튼으로 진행하세요.)",
                fg="#666",
                font=self.ui_font
            )
            tail.grid(row=(len(file_list) + 1) // cols + 2, column=0, columnspan=cols, pady=(4, 0))

    #  저장 유틸
    def _unique_dest_path(self, dest_dir: Path, base_name: str) -> Path:
        """이름 충돌 시 *_1, *_2 ... 붙여서 고유 경로 생성"""
        dest_path = dest_dir / base_name
        if not dest_path.exists():
            return dest_path
        stem, ext = os.path.splitext(base_name)
        i = 1
        while True:
            cand = dest_dir / f"{stem}_{i}{ext}"
            if not cand.exists():
                return cand
            i += 1

    def _copy_selected_to_dir(self, dest_dir: Path) -> list[Path]:
        """
        선택 파일들을 dest_dir에 복사, 최종 목적지 경로 리스트 반환
        - 실제로 유저가 선택한 최종 두 장만 지정한 폴더에 복사한다.
        """
        saved_paths = []
        dest_dir.mkdir(parents=True, exist_ok=True)
        for src in self.selected_files[:2]:
            src_path = Path(src)
            target = self._unique_dest_path(dest_dir, src_path.name)
            shutil.copy2(str(src_path), str(target))
            saved_paths.append(target)
        return saved_paths

    def _cleanup_frames_dir(self):
        """
        (정리용) frames/<video_name> 임시 프레임 폴더 전체 삭제.
        - 선택/다운로드가 끝나면 더 이상 필요 없으므로 자동 정리해서
          디스크/메모리 사용량을 줄인다.
        """
        try:
            if self.output_dir.exists():
                shutil.rmtree(self.output_dir)
                info(f"cleanup: deleted frames directory: {self.output_dir}")
            else:
                info(f"cleanup: frames directory not found (skip): {self.output_dir}")
        except Exception as e:
            # 삭제에 실패해도 앱이 죽지 않도록 경고만 남김
            warn(f"cleanup failed for {self.output_dir}: {e}")

    def _on_delete_selected(self):
        # (동작) 한 번 누르면 마지막(두 번째)만 제거, 다시 누르면 남은 한 장 제거
        if len(self.selected_files) == 0:
            return
        self.selected_files.pop()
        self._refresh_selected_panel()
        if 0 <= self.stage_idx < len(self.shown_stages):
            self._render_thumbs(self.shown_stages[self.stage_idx])

    def _on_confirm_selected(self):
        if len(self.selected_files) != 2:
            messagebox.showinfo("안내", "이미지 2장을 선택해야 합니다.")
            return
        self._finish_selection()

    def _finish_selection(self):
        """
        (최종 동작)
        - 선택된 2장의 이미지를 사용자가 지정한 폴더에 복사.
        - 그 후 frames/<video_name> 임시 프레임 폴더와 내부 프레임들을 모두 삭제.
        """
        chosen = self.selected_files[:2]
        info("selected files:")
        for p in chosen:
            info(f" - {p}")

        try:
            # (동작) 사용자에게 최종 저장할 폴더 선택 받기
            dest = filedialog.askdirectory(title="저장할 폴더를 선택하세요")
            if dest:
                try:
                    dest_dir = Path(dest)
                    saved_paths = self._copy_selected_to_dir(dest_dir)
                    done("selection complete and saved.")
                    lines = "\n".join(str(p) for p in saved_paths)
                    messagebox.showinfo("저장 완료", f"다음 위치에 저장했습니다:\n{lines}")
                except Exception as e:
                    # (오류 처리) 선택된 프레임 복사 중 문제 발생
                    error_msg = f"저장 중 오류: {e}"
                    warn(error_msg)
                    messagebox.showerror("오류", error_msg)
            else:
                # (취소) 저장 폴더 선택을 취소한 경우에도 선택은 완료된 상태
                done("selection complete (저장 경로 선택 취소).")
                messagebox.showinfo("완료", "2장의 이미지를 선택했습니다.\n(저장 폴더 선택이 취소되었습니다.)")
        finally:
            # (중요) 선택/저장 절차가 끝나면 임시 프레임 폴더 자동 삭제
            self._cleanup_frames_dir()

        # (UI 종료) 앱 창 닫기
        self.destroy()

    # 상단 시간 다시 설정
    def _show_retime_button(self):
        # (정리) 기존 버튼/상단바 제거
        if self.retime_btn:
            try:
                self.retime_btn.destroy()
            except Exception:
                pass
            self.retime_btn = None
        if self.top_bar:
            try:
                self.top_bar.destroy()
            except Exception:
                pass
            self.top_bar = None

        # (레이아웃) 상단 가로바 만들고, 그 안 오른쪽에 버튼 배치
        self.top_bar = tk.Frame(self)
        self.top_bar.pack(side=tk.TOP, fill=tk.X, pady=(8, 6))

        self.retime_btn = tk.Button(
            self.top_bar, text="시간 다시 설정",
            command=self._reset_to_time_form,
            font=self.ui_font_big, padx=10, pady=6
        )
        self.retime_btn.pack(side=tk.RIGHT, padx=(0, 12))  # (설정) 오른쪽 정렬/여백

    def _hide_retime_button(self):
        if self.retime_btn:
            self.retime_btn.destroy()
            self.retime_btn = None
        if self.top_bar:
            self.top_bar.destroy()
            self.top_bar = None

    def _reset_to_time_form(self):
        # (정리) 썸네일/네비/선택패널 등 모두 제거 후 초기 상태로 복귀
        if self.thumb_panel:
            self.thumb_panel.destroy()
            self.thumb_panel = None

        if self.center_wrapper:
            self.center_wrapper.destroy()
            self.center_wrapper = None
        if self.left_container:
            self.left_container.destroy()
            self.left_container = None

        if self.prev_btn:
            self.prev_btn.destroy()
            self.prev_btn = None
        if self.retry_btn:
            self.retry_btn.destroy()
            self.retry_btn = None

        if self.selected_panel:
            self.selected_panel.destroy()
            self.selected_panel = None

        self.selected_files = []
        self.shown_stages = []
        self.index_map = {}   # (중요) 번호 매핑 초기화
        self.stage_idx = -1
        self.stage = 0

        self._hide_retime_button()

        # (레이아웃) 시간 폼 다시 중앙에 표시
        if self.time_form:
            self.time_form.pack(fill=tk.BOTH, expand=True)
        if self.time_form_inner:
            self.time_form_inner.place(relx=0.5, rely=0.5, anchor="center")

        # (동작) 입력창 재활성화
        for w in (self.start_min, self.start_sec, self.end_min, self.end_sec):
            w.config(state=tk.NORMAL)
        self.confirm_btn.config(state=tk.NORMAL)
