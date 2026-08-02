import os
import cv2
import numpy as np
import streamlit as st
import time

# ==========================================
# বেসিক সেটআপ ও কাস্টম CSS স্টাইল
# ==========================================
st.set_page_config(page_title="Shadding_Design_GSM_Checker", layout="wide")

st.markdown("""
<style>
/* কন্টেইনারগুলোর বেস স্টাইল */
[data-testid="stContainer"] {
    border-radius: 0 0 16px 16px !important;
    padding: 24px !important;
    background-color: #ffffff !important;
    margin-bottom: 30px !important;
}

/* ধাপ ১ কন্টেইনার: মোটা অ্যাম্বার/কমলা বর্ডার ও শ্যাডো */
[data-testid="stContainer"]:nth-of-type(1) {
    border: 6px solid #c2410c !important;
    border-top: none !important;
    box-shadow: 0 15px 35px rgba(194, 65, 12, 0.22) !important;
}

/* ধাপ ২ কন্টেইনার: মোটা গাঢ় সবুজ বর্ডার ও শ্যাডো */
[data-testid="stContainer"]:nth-of-type(2) {
    border: 6px solid #047857 !important;
    border-top: none !important;
    box-shadow: 0 15px 35px rgba(4, 120, 87, 0.22) !important;
}
</style>
""", unsafe_allow_html=True)

# স্টাইলিশ অ্যাপ টাইটেল (রয়্যাল ব্লু/ইন্ডিগো গ্রেডিয়েন্ট ও থ্রিডি শ্যাডো)
st.markdown("""
<div style="
    background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 50%, #1d4ed8 100%);
    padding: 32px 20px;
    border-radius: 18px;
    box-shadow: 0 15px 35px rgba(29, 78, 216, 0.4), inset 0 2px 6px rgba(255,255,255,0.3);
    border: 2px solid rgba(255, 255, 255, 0.25);
    text-align: center;
    margin-bottom: 30px;
">
    <h1 style="
        color: #ffffff; 
        margin: 0; 
        font-size: 29px; 
        font-weight: 800; 
        text-shadow: 3px 3px 6px rgba(0,0,0,0.6), 0 0 25px rgba(255,255,255,0.4);
        letter-spacing: 0.6px;
    ">
        🧵 Shadding_Design_GSM Checker
    </h1>
    <p style="
        color: #e0f2fe; 
        margin: 10px 0 0 0; 
        font-size: 15px; 
        font-weight: 600; 
        text-shadow: 1px 1px 3px rgba(0,0,0,0.5);
    ">
        Automated Fabric Inspection & Quality Control System
    </p>
</div>
""", unsafe_allow_html=True)

BENCHMARK_DIR = "benchmark"
os.makedirs(BENCHMARK_DIR, exist_ok=True)

# Session States
if 'captured_benchmarks' not in st.session_state:
    st.session_state.captured_benchmarks = []
if 'last_cam_hash' not in st.session_state:
    st.session_state.last_cam_hash = None
if 'cam_key' not in st.session_state:
    st.session_state.cam_key = 0

# ==========================================
# সাইডবার: সেটিংস ও মোড 
# ==========================================
st.sidebar.header("⚙️ Settings & Modes")
inspection_mode = st.sidebar.selectbox(
    "🔍 ইনস্পেকশন মোড বেছে নিন",
    (
        "🌟 ফুল চেক (কালার + ডিজাইন + টেক্সচার ডেনসিটি)", 
        "🎨 কালার + ডিজাইন (উভয়ই)", 
        "👕 শুধুমাত্র কালার/শেডিং (সলিড কাপড়)", 
        "✨ শুধুমাত্র ডিজাইন/প্রিনট",
        "🧶 সুতার ঘনত্ব / টেক্সচার (GSM Density Check)"
    )
)
pass_threshold = st.sidebar.slider("Minimum Match Score (%)", 50.0, 99.0, 75.0, 1.0)
st.sidebar.info("💡 **টিপস:** পাসিং মার্ক সাধারণত ৭৫-৮৫% এর মধ্যে রাখলে সবচেয়ে ভালো রেজাল্ট পাওয়া যায়।")

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# মেইন পেজ - ধাপ ১: বেঞ্চমার্ক বক্স (অ্যাম্বার/কমলা থিম হেডার + খুব মোটা বর্ডার)
# ==========================================
st.markdown("""
<div style="
    background: linear-gradient(135deg, #c2410c 0%, #ea580c 100%); 
    padding: 16px 22px; 
    border-radius: 14px 14px 0 0; 
    color: white; 
    font-weight: bold; 
    font-size: 18px; 
    box-shadow: 0 6px 15px rgba(194,65,12,0.35); 
    border: 6px solid #c2410c;
    border-bottom: none;
">
    🏆 ধাপ ১: বেঞ্চমার্ক ইনপুট (Master Sample Setup)
</div>
""", unsafe_allow_html=True)

with st.container(border=True):
    st.markdown("বায়ারের অনুমোদিত নিখুঁত কাপড়ের ছবি দিয়ে সিস্টেমকে প্রস্তুত করুন।")
    
    bench_method = st.radio(
        "মাস্টার স্যাম্পল কিভাবে দেবেন?", 
        ("📁 গ্যালারি / ব্যাক ক্যামেরা (Recommended)", "📸 লাইভ ক্যামেরা"),
        horizontal=True
    )
    
    st.markdown("---")
    
    # --- অপশন এ: গ্যালারি / ব্যাক ক্যামেরা ---
    if bench_method == "📁 গ্যালারি / ব্যাক ক্যামেরা (Recommended)":
        new_benchmarks = st.file_uploader(
            "ছবি আপলোড বা ব্যাক ক্যামেরা দিয়ে তুলুন", 
            accept_multiple_files=True, 
            type=['png', 'jpg', 'jpeg'],
            key="bench_upload"
        )
        
        if new_benchmarks:
            st.write("📂 **সেভ করার অপশন বেছে নিন:**")
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("➕ বর্তমান স্যাম্পলগুলোর সাথে যোগ করুন", type="secondary", use_container_width=True):
                    current_files = [f for f in os.listdir(BENCHMARK_DIR) if f.endswith(('.png', '.jpg', '.jpeg'))]
                    existing_count = len(current_files)
                    
                    for i, file in enumerate(new_benchmarks):
                        new_name = f"master_{existing_count + i + 1}.jpg"
                        with open(os.path.join(BENCHMARK_DIR, new_name), "wb") as f:
                            f.write(file.getbuffer())
                    st.success(f"✅ আরও {len(new_benchmarks)} টি স্যাম্পল সফলভাবে যোগ করা হয়েছে!")
                    time.sleep(1)
                    st.rerun()
                    
            with col_btn2:
                if st.button("🔄 আগের সব মুছে শুধু এগুলো সেভ করুন", type="primary", use_container_width=True):
                    for f in os.listdir(BENCHMARK_DIR):
                        os.remove(os.path.join(BENCHMARK_DIR, f))
                        
                    for i, file in enumerate(new_benchmarks):
                        with open(os.path.join(BENCHMARK_DIR, f"master_{i+1}.jpg"), "wb") as f:
                            f.write(file.getbuffer())
                    st.success("✅ পুরানো সব মুছে নতুন স্যাম্পল সেভ হয়েছে!")
                    time.sleep(1)
                    st.rerun()

    # --- অপশন বি: লাইভ ক্যামেরা ---
    else:
        bench_cam = st.camera_input("মাস্টার স্যাম্পলের ছবি তুলুন", key=f"bench_cam_input_{st.session_state.cam_key}")
        
        if bench_cam:
            cam_bytes = bench_cam.getvalue()
            if st.session_state.last_cam_hash != cam_bytes:
                st.session_state.captured_benchmarks.append(cam_bytes)
                st.session_state.last_cam_hash = cam_bytes
                
        if len(st.session_state.captured_benchmarks) > 0:
            st.info(f"🟢 **{len(st.session_state.captured_benchmarks)} টি ছবি মেমোরিতে আছে।** (আরও ছবি তুলতে ক্যামেরার স্ক্রিনের ওপরের 'Clear photo' বাটনে ক্লিক করে আবার ছবি নিন)")
            
            st.write("📂 **ফাইনাল সেভ করার অপশন:**")
            col_save1, col_save2, col_save3 = st.columns(3)
            
            with col_save1:
                if st.button("➕ বর্তমানগুলোর সাথে যোগ করুন", type="secondary", use_container_width=True):
                    current_files = [f for f in os.listdir(BENCHMARK_DIR) if f.endswith(('.png', '.jpg', '.jpeg'))]
                    existing_count = len(current_files)
                    
                    for i, img_bytes in enumerate(st.session_state.captured_benchmarks):
                        new_name = f"master_cam_{existing_count + i + 1}.jpg"
                        with open(os.path.join(BENCHMARK_DIR, new_name), "wb") as f:
                            f.write(img_bytes)
                            
                    st.session_state.captured_benchmarks = []
                    st.session_state.last_cam_hash = None
                    st.session_state.cam_key += 1
                    st.success("✅ নতুন ছবিগুলো সফলভাবে যোগ হয়েছে!")
                    time.sleep(1)
                    st.rerun()
                    
            with col_save2:
                if st.button("🔄 আগের সব মুছে সেভ করুন", type="primary", use_container_width=True):
                    for f in os.listdir(BENCHMARK_DIR):
                        os.remove(os.path.join(BENCHMARK_DIR, f))
                        
                    for i, img_bytes in enumerate(st.session_state.captured_benchmarks):
                        with open(os.path.join(BENCHMARK_DIR, f"master_cam_{i+1}.jpg"), "wb") as f:
                            f.write(img_bytes)
                            
                    st.session_state.captured_benchmarks = []
                    st.session_state.last_cam_hash = None
                    st.session_state.cam_key += 1
                    st.success("✅ পুরানো সব মুছে নতুন ছবি সেভ হয়েছে!")
                    time.sleep(1)
                    st.rerun()
                    
            with col_save3:
                if st.button("❌ ক্যানসেল", use_container_width=True):
                    st.session_state.captured_benchmarks = []
                    st.session_state.last_cam_hash = None
                    st.session_state.cam_key += 1
                    st.rerun()

    # --- লাইভ গ্যালারি ---
    st.markdown("---")
    updated_files = [f for f in os.listdir(BENCHMARK_DIR) if f.endswith(('.png', '.jpg', '.jpeg'))]
    
    if updated_files:
        st.success(f"✅ **সিস্টেমে বর্তমানে {len(updated_files)} টি মাস্টার স্যাম্পল একটিভ আছে।**")
        cols = st.columns(min(len(updated_files), 5) if len(updated_files) > 0 else 1)
        for idx, file in enumerate(updated_files):
            with cols[idx % 5]:
                img_path = os.path.join(BENCHMARK_DIR, file)
                st.image(img_path, caption=file, use_container_width=True)
                
        if st.button("🗑️ সব স্যাম্পল ম্যানুয়ালি মুছুন", type="secondary"):
            for f in os.listdir(BENCHMARK_DIR):
                os.remove(os.path.join(BENCHMARK_DIR, f))
            st.rerun()
    else:
        st.warning("⚠️ বর্তমানে কোনো মাস্টার স্যাম্পল সেভ করা নেই!")

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# মূল এনালাইসিস ফাংশন (কালার, প্যাটার্ন ও টেক্সচার/GSM ডেনসিটি)
# ==========================================
def get_image_features(image):
    blur = cv2.GaussianBlur(image, (15, 15), 0)
    lab = cv2.cvtColor(blur, cv2.COLOR_BGR2LAB)
    hist = cv2.calcHist([lab], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
    cv2.normalize(hist, hist)
    hist_flat = hist.flatten()
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(nfeatures=1000) 
    kp, des = orb.detectAndCompute(gray, None)
    
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    edges = cv2.Canny(gray, 100, 200)
    edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1]) * 100
    
    return hist_flat, des, laplacian_var, edge_density

# ==========================================
# মেইন পেজ - ধাপ ২: টেস্টিং বক্স (গ্রিন থিম হেডার + খুব মোটা বর্ডার)
# ==========================================
st.markdown("""
<div style="
    background: linear-gradient(135deg, #065f46 0%, #047857 100%); 
    padding: 16px 22px; 
    border-radius: 14px 14px 0 0; 
    color: white; 
    font-weight: bold; 
    font-size: 18px; 
    box-shadow: 0 6px 15px rgba(4,120,87,0.35); 
    border: 6px solid #047857;
    border-bottom: none;
">
    🔬 ধাপ ২: টেস্টিং স্ক্যানার (Production Check)
</div>
""", unsafe_allow_html=True)

with st.container(border=True):
    st.markdown("প্রোডাকশন লাইন থেকে আসা নতুন কাপড়ের ছবি দিন। সিস্টেম অটোমেটিক চেক করবে।")
    
    final_benchmark_files = [f for f in os.listdir(BENCHMARK_DIR) if f.endswith(('.png', '.jpg', '.jpeg'))]
    
    if not final_benchmark_files:
        st.error("⚠️ টেস্টিং শুরু করার আগে 'ধাপ ১' থেকে মাস্টার স্যাম্পল সেভ করুন।")
    else:
        benchmark_data = []
        for b_file in final_benchmark_files:
            b_path = os.path.join(BENCHMARK_DIR, b_file)
            img = cv2.imread(b_path)
            if img is not None:
                img = cv2.resize(img, (500, 500))
                b_hist, b_des, b_lap, b_edge = get_image_features(img)
                benchmark_data.append((b_file, b_path, b_hist, b_des, b_lap, b_edge))

        col_test1, col_test2 = st.columns(2)
        
        with col_test1:
            st.info("📷 **নতুন কাপড় স্ক্যান করুন**")
            input_method = st.radio("কীভাবে স্ক্যান করবেন?", ("📁 ব্যাক ক্যামেরা / আপলোড", "🔴 লাইভ ক্যামেরা"), horizontal=True)
            
            camera_image = None
            if input_method == "📁 ব্যাক ক্যামেরা / আপলোড":
                camera_image = st.file_uploader("টেস্ট করার জন্য নতুন ছবি দিন", type=['png', 'jpg', 'jpeg'], key="test_upload")
            else:
                camera_image = st.camera_input("লাইভ স্ক্যান করুন", key="test_cam")
            
        with col_test2:
            st.info("📊 **এনালাইসিস রিপোর্ট**")
            if camera_image:
                bytes_data = camera_image.getvalue()
                cv_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
                cv_img = cv2.resize(cv_img, (500, 500))
                cam_hist, cam_des, cam_lap, cam_edge = get_image_features(cv_img)
                
                best_match_score = 0.0
                best_match_path = ""
                best_match_name = ""
                
                bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
                
                for name, b_path, b_hist, b_des, b_lap, b_edge in benchmark_data:
                    color_score = cv2.compareHist(b_hist, cam_hist, cv2.HISTCMP_CORREL)
                    color_pct = max(0, color_score * 100)
                    
                    pattern_pct = 0.0
                    if b_des is not None and cam_des is not None:
                        matches = bf.match(b_des, cam_des)
                        good_matches = [m for m in matches if m.distance < 60] 
                        pattern_pct = min(100.0, (len(good_matches) / 25.0) * 100)
                    
                    texture_diff = abs(b_lap - cam_lap)
                    texture_pct = max(0.0, 100.0 - (texture_diff / (b_lap + 1e-5) * 100))
                    
                    if "শুধুমাত্র কালার/শেডিং" in inspection_mode:
                        final_score = color_pct
                    elif "শুধুমাত্র ডিজাইন/প্রিনট" in inspection_mode:
                        final_score = pattern_pct
                    elif "সুতার ঘনত্ব / টেক্সচার" in inspection_mode:
                        final_score = texture_pct
                    elif "ফুল চেক" in inspection_mode:
                        final_score = (color_pct * 0.3) + (pattern_pct * 0.4) + (texture_pct * 0.3)
                    else:
                        final_score = (color_pct * 0.4) + (pattern_pct * 0.6)
                    
                    if final_score > best_match_score:
                        best_match_score = final_score
                        best_match_path = b_path
                        best_match_name = name
                        
                st.write(f"**চেকিং মোড:** `{inspection_mode}`")
                st.markdown(f"### **ফাইনাল একুরেসি:** `{best_match_score:.2f}%`")
                
                if best_match_score >= pass_threshold:
                    st.success(f"### 🎉 PASS - প্রোডাক্ট কোয়ালিটি সঠিক আছে!")
                else:
                    st.error(f"### ❌ FAIL - রিজেক্টেড! (পার্থক্য পাওয়া গেছে)")
                    
                st.markdown("---")
                st.write("🔍 **ভিজ্যুয়াল কম্পারিজন (কোন স্যাম্পলের সাথে মিলেছে):**")
                
                cv_img_rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
                best_b_img = cv2.imread(best_match_path)
                best_b_img_rgb = cv2.cvtColor(best_b_img, cv2.COLOR_BGR2RGB)
                
                v_col1, v_col2 = st.columns(2)
                with v_col1:
                    st.image(cv_img_rgb, caption="আপনার স্ক্যান (Test)", use_container_width=True)
                with v_col2:
                    st.image(best_b_img_rgb, caption=f"ম্যাচিং মাস্টার: {best_match_name}", use_container_width=True)
                    
            else:
                st.write("ফলাফল দেখার জন্য বামদিকে ছবি আপলোড বা স্ক্যান করুন।")
