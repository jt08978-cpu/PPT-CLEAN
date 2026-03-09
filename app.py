import streamlit as st
from pptx import Presentation
import easyocr
import cv2
import numpy as np
import io
from PIL import Image

st.set_page_config(page_title="NBLM 圖片去中文字工具", layout="centered")
st.title("🖼️ NBLM 簡報圖片去中文字工具 (修正版)")

# 讓使用者選擇語言，避免 EasyOCR 衝突
lang_option = st.radio(
    "請選擇圖片中的主要中文類型：",
    ('繁體中文', '簡體中文'),
    index=0
)

# 根據選擇設定語言零件
@st.cache_resource
def load_ocr(lang_choice):
    if lang_choice == '繁體中文':
        return easyocr.Reader(['ch_tra', 'en'])
    else:
        return easyocr.Reader(['ch_sim', 'en'])

reader = load_ocr(lang_option)

uploaded_file = st.file_uploader("請上傳您的 PPTX 檔案", type="pptx")

if uploaded_file:
    if st.button("🚀 開始一鍵去中文字"):
        with st.spinner('正在分析圖片並抹除文字中...請稍候...'):
            prs = Presentation(uploaded_file)
            
            # 遍歷每一頁
            for slide in prs.slides:
                for shape in slide.shapes:
                    # 判斷是否為圖片 (類型 13)
                    if shape.shape_type == 13: 
                        try:
                            # 1. 讀取圖片
                            img_bytes = shape.image.blob
                            nparr = np.frombuffer(img_bytes, np.uint8)
                            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                            
                            if img is None: continue
                            
                            # 2. 辨識文字
                            results = reader.readtext(img)
                            
                            # 3. 建立遮罩修補
                            mask = np.zeros(img.shape[:2], dtype=np.uint8)
                            found_text = False
                            
                            for (bbox, text, prob) in results:
                                # 只要偵測到文字就處理 (不分中英)
                                found_text = True
                                (tl, tr, br, bl) = bbox
                                pts = np.array([tl, tr, br, bl], np.int32)
                                cv2.fillPoly(mask, [pts], 255)
                            
                            if found_text:
                                # 執行影像修補
                                dst = cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)
                                
                                # 4. 將新圖存回 PPT
                                _, buffer = cv2.imencode(".png", dst)
                                new_img_stream = io.BytesIO(buffer)
                                
                                # 紀錄原圖位置
                                left, top, width, height = shape.left, shape.top, shape.width, shape.height
                                
                                # 插入新圖並移除舊圖
                                slide.shapes.add_picture(new_img_stream, left, top, width, height)
                                pic_element = shape._element
                                pic_element.getparent().remove(pic_element)
                        except Exception as e:
                            st.warning(f"某一頁圖片處理時跳過 (錯誤: {e})")
                            continue

            # 存檔供下載
            output = io.BytesIO()
            prs.save(output)
            st.success("✅ 處理完成！")
            st.download_button(
                label="📥 下載處理後的 PPTX",
                data=output.getvalue(),
                file_name="cleaned_nblm_file.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
            )
