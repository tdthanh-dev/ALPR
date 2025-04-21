from ultralytics import YOLO
import cv2
import os
import numpy as np
from flask import Flask, request, jsonify, send_from_directory, send_file
import base64
import io
import time

app = Flask(__name__, static_folder='static')

# Load các mô hình
model_plate = YOLO('best.pt')         # Nhận diện biển số
model_char = YOLO('best-char.pt')     # Nhận diện ký tự

output_crop_path = 'cropped_plates'
os.makedirs(output_crop_path, exist_ok=True)

def process_image(img, img_name=None):
    """
    Xử lý ảnh để nhận dạng biển số xe
    
    Tham số:
    - img: ảnh đầu vào dạng numpy array
    - img_name: tên ảnh (để lưu file, nếu cần)
    
    Trả về:
    - Danh sách các biển số được phát hiện và thông tin chi tiết
    """
    results = []
    
    results_plate = model_plate(img)[0]
    
    for i, box in enumerate(results_plate.boxes):
        plate_info = {}
        
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        plate_crop = img[y1:y2, x1:x2]
        h, w = plate_crop.shape[:2]
        
        plate_info["bbox"] = [x1, y1, x2, y2]
        
        min_height = 200
        if h < min_height:
            scale = min_height / h
            new_w, new_h = int(w * scale), int(h * scale)
            plate_crop = cv2.resize(plate_crop, (new_w, new_h))
        
        _, buffer = cv2.imencode('.jpg', plate_crop)
        plate_info["crop_base64"] = base64.b64encode(buffer).decode('utf-8')
        
        if img_name:
            output_path = os.path.join(output_crop_path, f"{img_name}_plate_{i+1}.jpg")
            cv2.imwrite(output_path, plate_crop)
        
        results_char = model_char(plate_crop)[0]
        
        char_list = []
        for box in results_char.boxes:
            if float(box.conf) < 0.5:
                continue
            x1c, y1c, x2c, y2c = map(int, box.xyxy[0].tolist())
            label = model_char.names[int(box.cls[0])]
            if label == "license plates":
                continue
            x_center = (x1c + x2c) // 2
            y_center = (y1c + y2c) // 2
            char_list.append((x_center, y_center, label))
        
        if not char_list:
            continue
        
        y_values = [y for _, y, _ in char_list]
        y_sorted = sorted(y_values)
        y_diff = [y_sorted[i+1] - y_sorted[i] for i in range(len(y_sorted)-1)]
        
        threshold = 20
        line_break = 0
        for j, diff in enumerate(y_diff):
            if diff > threshold:
                line_break = (y_sorted[j] + y_sorted[j+1]) // 2
                break
        
        if line_break:
            top_line = [(x, y, c) for x, y, c in char_list if y < line_break]
            bottom_line = [(x, y, c) for x, y, c in char_list if y >= line_break]
        else:
            top_line = char_list
            bottom_line = []
        
        top_line.sort(key=lambda x: x[0])
        bottom_line.sort(key=lambda x: x[0])
        
        top_text = ''.join([c for _, _, c in top_line])
        bottom_text = ''.join([c for _, _, c in bottom_line])
        
        plate_info["top_text"] = top_text
        plate_info["bottom_text"] = bottom_text
        
        if len(bottom_text) >= 5:
            formatted = f"{top_text} {bottom_text[:3]} {bottom_text[3:]}"
        else:
            formatted = f"{top_text} {bottom_text}"
        
        plate_info["formatted_text"] = formatted
        
        plate_info["characters"] = [
            {"x": x, "y": y, "label": c} for x, y, c in char_list
        ]
        
        results.append(plate_info)
    
    return results

@app.route('/detect_license_plate', methods=['POST'])
def detect_license_plate():
    """
    API endpoint để nhận diện biển số xe
    
    Request: 
    - image: ảnh đầu vào dạng base64 hoặc file
    
    Response:
    - Danh sách các biển số xe được phát hiện cùng thông tin chi tiết
    """
    if 'image' not in request.files and 'image_base64' not in request.json:
        return jsonify({"error": "Không tìm thấy ảnh trong yêu cầu"}), 400
    
    try:
        # Xử lý ảnh từ file hoặc base64
        img_name = None
        
        if 'image' in request.files:
            file = request.files['image']
            img_bytes = file.read()
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if file.filename:
                img_name = os.path.splitext(os.path.basename(file.filename))[0]
        else:
            img_base64 = request.json['image_base64']
            img_data = base64.b64decode(img_base64)
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if 'filename' in request.json:
                img_name = os.path.splitext(os.path.basename(request.json['filename']))[0]
            else:
                img_name = f"image_{int(time.time())}"
        
        results = process_image(img, img_name)
        
        return jsonify({
            "status": "success",
            "plates_count": len(results),
            "plates": results
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """API endpoint kiểm tra trạng thái hoạt động của hệ thống"""
    return jsonify({"status": "ok", "message": "Hệ thống đang hoạt động bình thường"})

@app.route('/')
def index():
    """Phục vụ trang chủ"""
    return send_file('index.html')

@app.route('/web')
def web():
    """Phục vụ trang nhận dạng biển số"""
    return send_file('web.html')

@app.route('/login')
def login():
    """Phục vụ trang đăng nhập"""
    return send_file('login.html')

@app.route('/admin')
def admin():
    """Phục vụ trang quản lý"""
    return send_file('admin.html')

@app.route('/web.html')
def web_html():
    """Phục vụ trang nhận dạng biển số với đường dẫn .html"""
    return send_file('web.html')

@app.route('/admin.html')
def admin_html():
    """Phục vụ trang quản lý với đường dẫn .html"""
    return send_file('admin.html')

@app.route('/login.html')
def login_html():
    """Phục vụ trang đăng nhập với đường dẫn .html"""
    return send_file('login.html')

@app.route('/members')
def members():
    """Phục vụ trang quản lý thành viên"""
    return send_file('members.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)