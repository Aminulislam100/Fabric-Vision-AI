import os
import cv2
import numpy as np
import streamlit as st
import time
from skimage.metrics import structural_similarity as ssim

# ==========================================
# বেসিক সেটআপ ও কাস্টম CSS স্টাইল
# ==========================================
st.set_page_config(page_title="Advanced Fabric AI Checker", layout="wide")

st.markdown("""
<style>
[data-testid="stContainer"] { border-radius: 0 0 16px 16px !important; padding: 24px !important; background-color: #ffffff !important; margin-bottom: 30px !important; }
[data-testid="stContainer"]:nth-of-type(1) { border: 6px solid #c2410c !important; border-top: none !important; box-shadow: 0 15px 35px rgba(194, 65, 12, 0.22) !important; }
[data-testid="stContainer"]:nth-of-type(2) { border: 6px solid #047857 !important; border-top: none !important; box-shadow: 0 15px 35px rgba(4, 120, 87, 0.22) !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 50%, #1d4ed8 100%); padding: 32px 20px; border-radius: 18px; box-shadow: 0 15px 35px rgba(29, 78, 216, 0.4), inset 0 2px 6px rgba(255,255,255,0.3); border: 2px solid rgba(255, 255, 255, 0.25); text-align: center; margin-bottom: 30px;">
    <h1 style="color: #ffffff; margin: 0; font-size: 29px; font-weight: 800; text-shadow: 3px 3px 6px rgba(0,0,0,0.6), 0 0 25px rgba(255,255,255,0.4); letter-spacing: 0.6px;">
        🧵 Advanced Fabric Quality Checker
    </h1>
    <p style="color: #e0f2fe; margin: 10px 0 0 0; font-size: 15px; font-weight: 600; text-shadow: 1px 1px 3px rgba(0,0,0,0.5);">
        AI-Driven Automated Inspection for Complex, Multi-shade & Striped Fabrics
    </p>
</div>
""", unsafe_allow_html=True)

BENCHMARK_DIR = "benchmark"
os.makedirs(BENCHMARK_DIR, exist_ok=True)

if 'captured_benchmarks' not in st.session_state:
    st.session_state.captured_benchmarks = []
if 'last_cam_hash' not in st.session_state:
    st.session_state.last_cam_hash = None
if 'cam_key' not in st.session_state:
    st.session_state.cam_key = 0

# ==========================================
# Aspect Ratio ঠিক রেখে রিসাইজ ফাংশন
# ==========================================
def resize_with_aspect_ratio(image, width=None, height=None, inter=cv2.INTER_AREA):
    dim = None
    (h, w) = image.shape[:2]
    if width is None and height is None:
        return image
    if width is None:
        r = height / float(h)
        dim = (int(w * r), height)
    else:
        r = width / float(w)
        dim = (width, int(h * r))
    return cv2.resize(image, dim, interpolation=inter)

# ==========================================
# সাইডবার: সেটিংস ও মোড
# ==========================================
st.sidebar.header("⚙️ Settings & Modes")
inspection_mode = st.sidebar.selectbox(
    "🔍 ইনস্পেকশন মোড বেছে নিন",
    (
        "🌟 ফুল চেক (কালার + ডিজাইন + স্ট্রাকচার + টেক্সচার)", 
        "🎨 কালার + ডিজাইন (উভয়ই)", 
        "👕 শুধুমাত্র কালার/শেডিং (সলিড কাপড়)", 
        "✨ শুধুমাত্র ডিজাইন/প্রিনট (SSIM + SIFT)",
        "🧶 সুতার ঘনত্ব / টেক্সচার (GSM Density Check)"
    )
)
pass_threshold = st.sidebar.slider("Minimum Match Score (%)", 50.0, 99.0, 75.0, 1.0)
st.sidebar.info("💡 **টিপস:** জটিল স্ট্রাইপ ও মাল্টি-শেড কাপড়ের জন্য ৭৫-৮০% থ্রেশহোল্ড ভালো কাজ করে।")

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# মেইন পেজ - ধাপ ১: বেঞ্চমার্ক বক্স
# ==========================================
st.markdown("""
<div style="background: linear-gradient(135deg, #c2410c 0%, #ea580c 100%); padding: 16px 22px; border-radius: 14px 14px 0 0; color: white; font-weight: bold; font-size: 18px; box-shadow: 0 6px 15px rgba(194,65,12,0.35); border: 6px solid #c2410c; border-bottom: none;">
    🏆 ধাপ ১: বেঞ্চমার্ক ইনপুট (Master Sample Setup)
</div>
""", unsafe_allow_html=True)

with st.container(border=True):
    bench_method = st.radio("মাস্টার স্যাম্পল কিভাবে দেবেন?", ("📁 গ্যালারি / ব্যাক ক্যামেরা", "📸 লাইভ ক্যামেরা"), horizontal=True)
    st.markdown("---")
    
    if bench_method == "📁 গ্যালারি / ব্যাক ক্যামেরা":
        new_benchmarks = st.file_uploader("ছবি আপলোড বা ব্যাক ক্যামেরা দিয়ে তুলুন", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'], key="bench_upload")
        
        if new_benchmarks:
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            with col_btn1:
                if st.button("➕ বর্তমান স্যাম্পলের সাথে যোগ করুন", use_container_width=True):
                    existing_count = len([f for f in os.listdir(BENCHMARK_DIR)])
                    for i, file in enumerate(new_benchmarks):
                        with open(os.path.join(BENCHMARK_DIR, f"master_{existing_count + i + 1}.jpg"), "wb") as f:
                            f.write(file.getbuffer())
                    st.success("✅ যোগ করা হয়েছে!")
                    time.sleep(1)
                    st.rerun()
            with col_btn2:
                if st.button("🔄 আগের সব মুছে নতুন সেভ করুন", type="primary", use_container_width=True):
                    for f in os.listdir(BENCHMARK_DIR): os.remove(os.path.join(BENCHMARK_DIR, f))
                    for i, file in enumerate(new_benchmarks):
                        with open(os.path.join(BENCHMARK_DIR, f"master_{i+1}.jpg"), "wb") as f:
                            f.write(file.getbuffer())
                    st.success("✅ নতুন স্যাম্পল সেভ হয়েছে!")
                    time.sleep(1)
                    st.rerun()
            with col_btn3:
                if st.button("❌ ক্যানসেল / বাদ দিন", use_container_width=True):
                    st.rerun()
    else:
        bench_cam = st.camera_input("মাস্টার স্যাম্পলের ছবি তুলুন", key=f"bench_cam_input_{st.session_state.cam_key}")
        if bench_cam:
            cam_bytes = bench_cam.getvalue()
            if st.session_state.last_cam_hash != cam_bytes:
                st.session_state.captured_benchmarks.append(cam_bytes)
                st.session_state.last_cam_hash = cam_bytes
                
        if len(st.session_state.captured_benchmarks) > 0:
            st.info(f"📸 তোলা হয়েছে: {len(st.session_state.captured_benchmarks)} টি স্যাম্পল")
            col_save1, col_save2, col_save3 = st.columns(3)
            with col_save1:
                if st.button("➕ বর্তমান স্যাম্পলের সাথে যোগ করুন", use_container_width=True):
                    existing_count = len([f for f in os.listdir(BENCHMARK_DIR)])
                    for i, img_bytes in enumerate(st.session_state.captured_benchmarks):
                        with open(os.path.join(BENCHMARK_DIR, f"master_cam_{existing_count + i + 1}.jpg"), "wb") as f: f.write(img_bytes)
                    st.session_state.captured_benchmarks = []; st.session_state.cam_key += 1
                    st.success("✅ যোগ করা হয়েছে!")
                    time.sleep(1)
                    st.rerun()
            with col_save2:
                if st.button("🔄 আগের সব মুছে নতুন সেভ করুন", type="primary", use_container_width=True):
                    for f in os.listdir(BENCHMARK_DIR): os.remove(os.path.join(BENCHMARK_DIR, f))
                    for i, img_bytes in enumerate(st.session_state.captured_benchmarks):
                        with open(os.path.join(BENCHMARK_DIR, f"master_cam_{i+1}.jpg"), "wb") as f: f.write(img_bytes)
                    st.session_state.captured_benchmarks = []; st.session_state.cam_key += 1
                    st.success("✅ নতুন সেভ হয়েছে!")
                    time.sleep(1)
                    st.rerun()
            with col_save3:
                if st.button("❌ ক্যানসেল / রিটেক", use_container_width=True):
                    st.session_state.captured_benchmarks = []
                    st.session_state.last_cam_hash = None
                    st.session_state.cam_key += 1
                    st.rerun()

    st.markdown("---")
    updated_files = [f for f in os.listdir(BENCHMARK_DIR) if f.endswith(('.png', '.jpg', '.jpeg'))]
    if updated_files:
        st.write(f"**📂 সেভ করা মাস্টার স্যাম্পল ({len(updated_files)} টি):**")
        cols = st.columns(min(len(updated_files), 5) if len(updated_files) > 0 else 1)
        for idx, file in enumerate(updated_files):
            with cols[idx % 5]:
                st.image(os.path.join(BENCHMARK_DIR, file), caption=file, use_container_width=True)
        if st.button("🗑️ সব মাস্টার স্যাম্পল মুছুন"):
            for f in os.listdir(BENCHMARK_DIR): os.remove(os.path.join(BENCHMARK_DIR, f))
            st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 🧠 অ্যাডভান্সড এনালাইসিস ফাংশন (3x3 Grid, SIFT, SSIM)
# ==========================================
def get_image_features(image):
    h, w = image.shape[:2]
    
    # ১. ৩×৩ স্পেশিয়াল কালার গ্রিড (৯টি সেক্টরে নিখুঁত কালার চেক)
    h_step, w_step = max(1, h // 3), max(1, w // 3)
    hist_features = []
    
    for i in range(3):
        for j in range(3):
            sub_crop = image[i*h_step:(i+1)*h_step, j*w_step:(j+1)*w_step]
            if sub_crop.size > 0:
                blur = cv2.GaussianBlur(sub_crop, (7, 7), 0)
                lab = cv2.cvtColor(blur, cv2.COLOR_BGR2LAB)
                hist = cv2.calcHist([lab], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
                cv2.normalize(hist, hist)
                hist_features.extend(hist.flatten())
            
    hist_flat = np.array(hist_features, dtype=np.float32)

    # ২. SIFT ফিচার এক্সট্রাকশন
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    sift = cv2.SIFT_create(nfeatures=1500)
    kp, des = sift.detectAndCompute(gray, None)
    
    # ৩. টেক্সচার ও মেটেরিয়াল ডেনসিটি
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    edges = cv2.Canny(gray, 100, 200)
    edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1]) * 100
    
    return hist_flat, des, laplacian_var, edge_density, gray

# ==========================================
# 🚀 ক্যাশিং ফাংশন (মাস্টার স্যাম্পল প্রসেসিং ফাস্ট করতে)
# ==========================================
@st.cache_data(show_spinner=False)
def load_cached_benchmarks(file_list, bench_dir):
    data = []
    for b_file in file_list:
        b_path = os.path.join(bench_dir, b_file)
        img = cv2.imread(b_path)
        if img is not None:
            # Aspect Ratio ঠিক রেখে ৫শ পিক্সেল চওড়া করা হচ্ছে
            img = resize_with_aspect_ratio(img, width=500)
            b_hist, b_des, b_lap, b_edge, b_gray = get_image_features(img)
            data.append((b_file, b_path, b_hist, b_des, b_lap, b_edge, b_gray))
    return data

# ==========================================
# মেইন পেজ - ধাপ ২: টেস্টিং স্ক্যানার
# ==========================================
st.markdown("""
<div style="background: linear-gradient(135deg, #065f46 0%, #047857 100%); padding: 16px 22px; border-radius: 14px 14px 0 0; color: white; font-weight: bold; font-size: 18px; box-shadow: 0 6px 15px rgba(4,120,87,0.35); border: 6px solid #047857; border-bottom: none;">
    🔬 ধাপ ২: টেস্টিং স্ক্যানার (Production Check)
</div>
""", unsafe_allow_html=True)

with st.container(border=True):
    final_benchmark_files = [f for f in os.listdir(BENCHMARK_DIR) if f.endswith(('.png', '.jpg', '.jpeg'))]
    
    if not final_benchmark_files:
        st.error("⚠️ টেস্টিং শুরু করার আগে উপরে মাস্টার স্যাম্পল সেভ করুন।")
    else:
        # ডেটা ক্যাশ থেকে কল করা হচ্ছে (এতে প্রতিবার ছবি প্রসেস হবে না, অ্যাপ দ্রুত চলবে)
        benchmark_data = load_cached_benchmarks(tuple(final_benchmark_files), BENCHMARK_DIR)

        col_test1, col_test2 = st.columns([1, 1.2])
        
        with col_test1:
            input_method = st.radio("কীভাবে স্ক্যান করবেন?", ("📁 গ্যালারি / ব্যাক ক্যামেরা", "🔴 লাইভ ক্যামেরা"), horizontal=True)
            if input_method == "📁 গ্যালারি / ব্যাক ক্যামেরা":
                # accept_multiple_files=False যুক্ত করে অ্যাপ ক্র্যাশ প্রতিরোধ করা হয়েছে
                camera_image = st.file_uploader("টেস্টিংয়ের ছবি দিন", type=['png', 'jpg', 'jpeg'], key="test_upload", accept_multiple_files=False)
            else:
                camera_image = st.camera_input("লাইভ স্ক্যান করুন", key="test_cam")
            
        with col_test2:
            if camera_image:
                bytes_data = camera_image.getvalue()
                cv_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
                
                # টেস্ট ছবিটিরও রেশিও ঠিক রেখে রিসাইজ করা হচ্ছে
                cv_img = resize_with_aspect_ratio(cv_img, width=500)
                cam_hist, cam_des, cam_lap, cam_edge, cam_gray = get_image_features(cv_img)
                
                best_match_score = 0.0
                best_match_path, best_match_name = "", ""
                
                flann = cv2.FlannBasedMatcher(dict(algorithm=1, trees=5), dict(checks=50))
                
                for name, b_path, b_hist, b_des, b_lap, b_edge, b_gray in benchmark_data:
                    # ১. Color Score
                    color_score = cv2.compareHist(b_hist, cam_hist, cv2.HISTCMP_CORREL)
                    color_pct = max(0.0, color_score * 100.0)
                    
                    # ২. Pattern Score (SIFT)
                    pattern_pct = 0.0
                    if b_des is not None and cam_des is not None and len(b_des) >= 2 and len(cam_des) >= 2:
                        try:
                            matches = flann.knnMatch(b_des, cam_des, k=2)
                            good_matches = [m for match_pair in matches if len(match_pair) == 2 for m, n in [match_pair] if m.distance < 0.75 * n.distance]
                            pattern_pct = min(100.0, (len(good_matches) / 50.0) * 100.0)
                        except Exception:
                            pattern_pct = 0.0
                    
                    # ৩. Structural Score (SSIM ক্র্যাশ ফিক্স - ডাইনামিক রিসাইজ)
                    cam_gray_resized = cv2.resize(cam_gray, (b_gray.shape[1], b_gray.shape[0]))
                    score_ssim, _ = ssim(b_gray, cam_gray_resized, full=True)
                    ssim_pct = max(0.0, score_ssim * 100.0)
                    
                    # ৪. Texture Score
                    texture_diff = abs(b_lap - cam_lap)
                    texture_pct = max(0.0, 100.0 - (texture_diff / (b_lap + 1e-5) * 100.0))
                    
                    # মোড অনুযায়ী ডায়নামিক ওয়েটেড স্কোর
                    if "শুধুমাত্র কালার/শেডিং" in inspection_mode:
                        final_score = color_pct
                    elif "শুধুমাত্র ডিজাইন/প্রিনট" in inspection_mode:
                        final_score = (pattern_pct * 0.40) + (ssim_pct * 0.60)
                    elif "সুতার ঘনত্ব / টেক্সচার" in inspection_mode:
                        final_score = texture_pct
                    elif "কালার + ডিজাইন" in inspection_mode:
                        final_score = (color_pct * 0.40) + (pattern_pct * 0.30) + (ssim_pct * 0.30)
                    else:
                        final_score = (color_pct * 0.25) + (pattern_pct * 0.25) + (ssim_pct * 0.30) + (texture_pct * 0.20)
                    
                    if final_score > best_match_score:
                        best_match_score = final_score
                        best_match_path, best_match_name = b_path, name
                        
                st.write(f"**চেকিং মোড:** `{inspection_mode}`")
                st.markdown(f"### **ফাইনাল একুরেসি:** `{best_match_score:.2f}%`")
                
                if best_match_score >= pass_threshold:
                    st.success("### 🎉 PASS - প্রোডাক্ট কোয়ালিটি সঠিক আছে!")
                else:
                    st.error("### ❌ FAIL - রিজেক্টেড! (পার্থক্য পাওয়া গেছে)")
                    
                st.markdown("---")
                v_col1, v_col2 = st.columns(2)
                with v_col1:
                    st.image(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB), caption="আপনার স্ক্যান (Test)", use_container_width=True)
                with v_col2:
                    if best_match_path:
                        st.image(cv2.cvtColor(cv2.imread(best_match_path), cv2.COLOR_BGR2RGB), caption=f"ম্যাচিং মাস্টার: {best_match_name}", use_container_width=True)
