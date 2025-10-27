import os
import shutil
import zipfile
import tempfile
import cv2
import streamlit as st
from yt_dlp import YoutubeDL
from urllib.parse import urlparse, parse_qs

if 'video_path' not in st.session_state:
    st.session_state.video_path = None
if 'video_label' not in st.session_state:
    st.session_state.video_label = None 
if 'total_frames' not in st.session_state:
    st.session_state.total_frames = 0
if 'frames_dir' not in st.session_state:
    st.session_state.frames_dir = os.path.join(os.getcwd(), 'frames')
if 'idx' not in st.session_state:
    st.session_state.idx = 0


def make_label_from_path(path: str) -> str:
    name = os.path.splitext(os.path.basename(path))[0]
    return name


def make_label_from_url(url: str) -> str:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    vid = qs.get('v', [''])[0]
    return vid or parsed.path.replace('/', '_')[:10]

def download_video(youtube_url: str, output_path: str, progress_bar) -> str:
    def _hook(d):
        if d.get('status') == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            if total:
                progress = min(downloaded / total, 1.0)
                progress_bar.progress(progress)
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/mp4",
        "outtmpl": output_path,                
        "merge_output_format": "mp4",
        "noplaylist": True,
        "geo_bypass": True,
        "concurrent_fragment_downloads": 3,
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        },
        "quiet": True,
        "no_warnings": False,
        'progress_hooks': [_hook],
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=True)
        return ydl.prepare_filename(info)

def load_video(path: str):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        st.error('Failed to open video file')
        return None
    st.session_state.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    st.session_state.idx = max(0, min(st.session_state.idx, st.session_state.total_frames - 1))
    return cap

def get_frame(cap, idx: int):
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ret, frame = cap.read()
    if not ret:
        return None
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

def zip_frames(frames_dir: str) -> str:
    zip_path = os.path.join(tempfile.gettempdir(), 'frames.zip')
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for root, _, files in os.walk(frames_dir):
            for file in files:
                zipf.write(os.path.join(root, file), arcname=file)
    return zip_path

st.title('Video Frame Extractor')

source = st.radio('Select video source:', ['Upload File', 'YouTube URL'], index=0)
col1, col2 = st.columns([4,1])

if source == 'Upload File':
    if not st.session_state.video_path:
        uploaded = col1.file_uploader('Upload Video', type=['mp4', 'mov', 'avi'], key='uploader')
        if uploaded:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded.name)[1])
            tmp.write(uploaded.getbuffer()); tmp.close()
            st.session_state.video_path = tmp.name
            st.session_state.video_label = make_label_from_path(uploaded.name)
            os.makedirs(st.session_state.frames_dir, exist_ok=True)
elif source == 'YouTube URL':
    if st.session_state.video_path is None:
        yt_link = col1.text_input('YouTube URL', key='yt_link')
        if col2.button('Download Video', key='yt_download') and yt_link:
            os.makedirs(st.session_state.frames_dir, exist_ok=True)
            progress_bar = st.progress(0.0)
            with st.spinner('Downloading video...'):
                try:
                    path = download_video(yt_link, 'temp_video.%(ext)s', progress_bar)
                    st.session_state.video_path = path
                    st.session_state.video_label = make_label_from_url(yt_link)
                    st.session_state.idx = 0
                except Exception:
                    st.error('Please enter a valid YouTube video link')
            progress_bar.empty()

if st.session_state.video_path:
    colA, colB = st.columns([1,1])
    if colA.button('Reset Video', key='reset_video'):
        try:
            os.remove(st.session_state.video_path)
        except:
            pass
        
        st.session_state.video_path = None
        st.session_state.video_label = None
        st.session_state.total_frames = 0
        st.session_state.idx = 0

        if 'yt_link' in st.session_state:
            st.session_state.yt_link = ''

    if st.session_state.video_path:
        with open(st.session_state.video_path, 'rb') as vf:
            colB.download_button('Download Video (MP4)', vf, file_name=os.path.basename(st.session_state.video_path), key='download_mp4')

if st.session_state.video_path:
    cap = load_video(st.session_state.video_path)
    if cap:
        nav = st.columns([1,1,6,1,1])

        if nav[0].button('⏪', key='jump_back_10'):
            st.session_state.idx = max(st.session_state.idx - 10, 0)
            
        if nav[1].button('⬅️', key='step_back'):
            st.session_state.idx = max(st.session_state.idx - 1, 0)

        st.session_state.idx = nav[2].slider('Frame', 0, st.session_state.total_frames - 1, st.session_state.idx, key='frame_slider')

        if nav[3].button('➡️', key='step_forward'):
            st.session_state.idx = min(st.session_state.idx + 1, st.session_state.total_frames - 1)
 
        if nav[4].button('⏩', key='jump_forward_10'):
            st.session_state.idx = min(st.session_state.idx + 10, st.session_state.total_frames - 1)

        frame = get_frame(cap, st.session_state.idx)
        if frame is not None:
            st.image(frame, use_container_width=True)
            if st.button('Save Frame', key='save_frame'):
                label = st.session_state.video_label or 'video'
                fname = f"{label}_frame_{st.session_state.idx:06d}.jpg"
                out = os.path.join(st.session_state.frames_dir, fname)
                cv2.imwrite(out, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        cap.release()

colF1, colF2 = st.columns([1,3])
with colF1:
    if st.button('Reset Frames', key='reset_frames'):
        shutil.rmtree(st.session_state.frames_dir, ignore_errors=True)
        os.makedirs(st.session_state.frames_dir, exist_ok=True)
with colF2:
    saved = sorted(os.listdir(st.session_state.frames_dir)) if os.path.exists(st.session_state.frames_dir) else []
    st.write('Saved Frames:' if saved else 'Saved Frames: None')
    for f in saved: st.write('-', f)

if saved:
    zip_path = zip_frames(st.session_state.frames_dir)
    with open(zip_path, 'rb') as f:
        st.download_button('Download Frames ZIP', f, file_name='frames.zip')
