import streamlit as st
from pptx import Presentation
from pptx.util import Inches
import easyocr
import cv2
import numpy as np
from PIL import Image
import io
import os

st.set_page_config(page_title="NBLM 圖片去中文字工具", layout="centered")
st.title("🖼️ NBLM 簡報圖片去中文字工具")
st.info("這是一個專門為 AI 小白設計的工具，上傳 PPTX 後會自動處理圖片中的中文文字。")

@st.cache_resource
def load_ocr():
    # 支援繁體、簡體與英文
    return easyocr.Reader(['ch_tra', 'ch_sim', 'en'])

reader = load_ocr()

uploaded_file = st.file_uploader("請上傳您的 PPTX 檔案", type="pptx")

if uploaded_file:
    if st.button("🚀 開始一鍵去中文字"):
        with st.spinner('AI 正在努力辨識並塗抹文字中，請稍候...'):
            prs = Presentation(uploaded_file)
            
            for slide in prs.slides:
                for shape in slide.shapes:
                    if shape.shape_type == 13: # 13 代表圖片
                        # 讀取圖片數據
                        img_bytes = shape.image.blob
                        nparr = np.frombuffer(img_bytes, np.uint8)
                        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        
                        # OCR 辨識文字
                        results = reader.readtext(img)
                        
                        # 建立遮罩來修補文字
                        mask = np.zeros(img.shape[:2], dtype=np.uint8)
                        found_chinese = False
                        
                        for (bbox, text, prob) in results:
                            # 判斷是否包含中文字
                            if any('\u4e00' <= char <= '\u9fff' for char in text):
                                found_chinese = True
                                (tl, tr, br, bl) = bbox
                                pts = np.array([tl, tr, br, bl], np.int32)
                                cv2.fillPoly(mask, [pts], 255)
                        
                        if found_chinese:
                            # 執行影像修補 (Inpainting)
                            dst = cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)
                            
                            # 將處理後的圖片保存到內存
                            _, buffer = cv2.imencode(".png", dst)
                            new_img_stream = io.BytesIO(buffer)
                            
                            # 替換原圖 (保留位置)
                            left, top, width, height = shape.left, shape.top, shape.width, shape.height
                            new_shape = slide.shapes.add_picture(new_img_stream, left, top, width, height)
                            
                            # 移除舊圖片
                            old_pic = shape._element
                            old_pic.getparent().remove(old_pic)

            # 存檔提供下載
            output = io.BytesIO()
            prs.save(output)
            st.success("✅ 處理完成！")
            st.download_button(
                label="📥 下載處理後的 PPTX",
                data=output.getvalue(),
                file_name="cleaned_nblm_file.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
            )
