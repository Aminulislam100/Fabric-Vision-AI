import os
import cv2
import numpy as np
import streamlit as st
import shutil

st.set_page_config(page_title="Fabric Vision Ultimate Pro", layout="wide")
st.title("🧵 Fabric Vision AI - Ultimate QC System")

BENCHMARK_DIR = "benchmark"
os.makedirs(BENCHMARK_DIR, exist_ok=True)

st.sidebar.header("⚙️ Settings & Modes")

# ইনস্পেকশন মোড সিলেক্ট করার অপশন
inspection_mode = st.sidebar.selectbox(
    "🔍 ইনস্পেকশন মোড বেছে নিন",
    ("🎨 কালার + ডিজাইন (উভয়ই)", "👕 শুধুমাত্র কালার/শেডিং (সলিড কাপড়)", "✨ শুধুমাত্র ডিজাইন/প্রিনট")
)
pass_threshold = st.sidebar.slider("Minimum Match Score (%)", 50.0, 99.0, 75.0, 1.0)

st.sidebar.markdown("---")

# ==========================================
# নতুন ফিচার: অ্যাপ থেকেই বেঞ্চমার্ক কন্ট্রোল
# ==========================================
st.sidebar.subheader("📂 বেঞ্চমার্ক কন্ট্রোল প্যানেল")
new_benchmarks = st.sidebar.file_uploader(
    "নতুন মাস্টার স্যাম্পল আপলোড করুন (একাধিক দেওয়া যাবে)", 
    accept_multiple_files=True, 
    type=['png', 'jpg', 'jpeg']
)

if st.sidebar.button("🗑️ আগের বেঞ্চমার্ক মুছে নতুনগুলো সেভ করুন"):
    # আগের সব ফাইল ডিলিট করা
    for f in os.listdir(BENCHMARK_DIR):
        os.remove(os.path.join(BENCHMARK_DIR, f))
    
    # নতুন আপলোড করা ফাইলগুলো ফোল্ডারে সেভ করা
    if new_benchmarks:
        for i, file in enumerate(new_benchmarks):
            with open(os.path.join(BENCHMARK_DIR, f"master_{i+1}.jpg"), "wb") as f:
                f.write(file.getbuffer())
        st.sidebar.success("✅ নতুন বেঞ্চমার্ক সফলভাবে সেট করা হয়েছে!")
        st.rerun() # সাথে সাথে অ্যাপ রিফ্রেশ হবে
    else:
        st.sidebar.warning("⚠️ আপনি কোনো নতুন ছবি দেননি, তাই বেঞ্চমার্ক ফোল্ডার এখন খালি!")
        st.rerun()

# ==========================================
# মূল এনালাইসিস ফাংশন (আপডেটেড ORB)
# ==========================================
def get_image_features(image):
    blur = cv2.GaussianBlur(image, (15, 15), 0)
    lab = cv2.cvtColor(blur, cv2.COLOR_BGR2LAB)
    hist = cv2.calcHist([lab], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
    cv2.normalize(hist, hist)
    hist_flat = hist.flatten()
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # প্যাটার্ন ডিটেকশন ক্যাপাসিটি বাড়ানো হয়েছে (১০০০)
    orb = cv2.ORB_create(nfeatures=1000) 
    kp, des = orb.detectAndCompute(gray, None)
    
    return hist_flat, des

benchmark_files = [f for f in os.listdir(BENCHMARK_DIR) if f.endswith(('.png', '.jpg', '.jpeg'))]

if not benchmark_files:
    st.warning("⚠️ কোনো বেঞ্চমার্ক স্যাম্পল নেই! বামদিকের মেনু থেকে নতুন মাস্টার স্যাম্পল আপলোড করে 'সেভ' বাটনে ক্লিক করুন।")
else:
    st.success(f"✅ {len(benchmark_files)} টি বেঞ্চমার্ক স্যাম্পল লোড আছে।")
    benchmark_data = []
    for b_file in benchmark_files:
        b_path = os.path.join(BENCHMARK_DIR, b_file)
        img = cv2.imread(b_path)
        if img is not None:
            img = cv2.resize(img, (500, 500))
            hist, des = get_image_features(img)
            benchmark_data.append((b_file, hist, des))

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📷 স্ক্যান / আপলোড (টেস্টিং)")
        
        input_method = st.radio("টেস্ট করার মাধ্যম:", ("📁 ছবি আপলোড (Recomended)", "🔴 লাইভ স্ক্যানার"))
        
        camera_image = None
        if input_method == "📁 ছবি আপলোড (Recomended)":
            camera_image = st.file_uploader("টেস্ট করার জন্য নতুন কাপড়ের ছবি আপলোড করুন", type=['png', 'jpg', 'jpeg'], key="test_upload")
        else:
            camera_image = st.camera_input("লাইভ স্ক্যান করুন")
        
    with col2:
        st.subheader("📊 এনালাইসিস রিপোর্ট")
        if camera_image:
            bytes_data = camera_image.getvalue()
            cv_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
            cv_img = cv2.resize(cv_img, (500, 500))
            cam_hist, cam_des = get_image_features(cv_img)
            
            best_match_score = 0.0
            best_match_name = ""
            
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            
            for name, b_hist, b_des in benchmark_data:
                # কালার স্কোর
                color_score = cv2.compareHist(b_hist, cam_hist, cv2.HISTCMP_CORREL)
                color_pct = max(0, color_score * 100)
                
                # প্যাটার্ন স্কোর (আপডেটেড লজিক)
                pattern_pct = 0.0
                if b_des is not None and cam_des is not None:
                    matches = bf.match(b_des, cam_des)
                    # টলারেন্স ৬০ করা হয়েছে যেন আইডেন্টিক্যাল ছবি ফেইল না করে
                    good_matches = [m for m in matches if m.distance < 60] 
                    pattern_pct = min(100.0, (len(good_matches) / 25.0) * 100)
                
                # ফাইনাল স্কোর ক্যালকুলেশন
                if "শুধুমাত্র কালার/শেডিং" in inspection_mode:
                    final_score = color_pct
                elif "শুধুমাত্র ডিজাইন/প্রিনট" in inspection_mode:
                    final_score = pattern_pct
                else:
                    final_score = (color_pct * 0.4) + (pattern_pct * 0.6)
                
                if final_score > best_match_score:
                    best_match_score = final_score
                    best_match_name = name
                    
            st.write(f"**চেকিং মোড:** `{inspection_mode}`")
            st.write(f"**ম্যাচিং একুরেসি:** `{best_match_score:.2f}%`")
            
            st.markdown("---")
            if best_match_score >= pass_threshold:
                st.success(f"### 🎉 PASS - প্রোডাক্ট কোয়ালিটি সঠিক আছে!")
            else:
                st.error(f"### ❌ FAIL - রিজেক্টেড! (পার্থক্য পাওয়া গেছে)")