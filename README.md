# FrameExtractorAndSceneTo3D
Algorithm that extracts frames from a YouTube video or uploaded clip that can then be used to create a 3D model of the scene

"main.py" is a Streamlit implementation that enables browser-based functionality, whereas "local_extract.py" is something you can run locally to extract frames from a YT video. Because of the large size of the 3D reconstruction model mast3r and high compute power required, I use the HuggingFace demo (https://huggingface.co/spaces/naver/MASt3R) rather than run the entire model locally (which I don't have the resources for).
