import io
import uvicorn
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# --- 2. Cấu hình Matplotlib ---
# Rất quan trọng: Cấu hình Matplotlib để chạy ở chế độ "headless"
# (không cần giao diện đồ họa), tránh lỗi khi triển khai trên server.
matplotlib.use('Agg')


# --- 3. Pydantic Model: Định nghĩa cấu trúc dữ liệu đầu vào ---
class ChartRequest(BaseModel):
    """
    Định nghĩa cấu trúc dữ liệu mà API endpoint sẽ nhận vào.
    FastAPI sẽ dùng model này để validate và chuyển đổi kiểu dữ liệu tự động.
    """
    chart_data: dict
    last_month_str: str
    prev_month_str: str
    width: int = 10
    height: int = 6
    dpi: int = 100


# --- 4. Logic vẽ biểu đồ ---
def create_revenue_chart(chart_data: dict, last_month_str: str, prev_month_str: str, width: int, height: int, dpi: int):
    """
    Vẽ biểu đồ so sánh doanh thu và trả về một buffer ảnh.
    Hàm này là logic "thuần túy", không phụ thuộc vào framework web.
    """
    # Hàm phụ để rút gọn số liệu
    def format_large_number(num, pos=None):
        if num >= 1_000_000_000:
            return f'{num / 1_000_000_000:.2f} tỷ'
        if num >= 1_000_000:
            return f'{num / 1_000_000:.2f} tr'
        if num >= 1_000:
            return f'{num / 1_000:.1f} k'
        return f'{num:,.0f}'

    # Trích xuất dữ liệu
    labels = chart_data['labels']
    last_month_revenues = chart_data['last_month']['revenue']
    last_month_shares = chart_data['last_month']['share']
    prev_month_revenues = chart_data['prev_month']['revenue']
    prev_month_shares = chart_data['prev_month']['share']

    # Cấu hình font chữ và tạo biểu đồ
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
    fig, ax = plt.subplots(figsize=(width, height))

    # Vẽ các cột
    x = np.arange(len(labels))
    bar_width = 0.35

    rects1 = ax.bar(x - bar_width/2, last_month_revenues, bar_width,
                    label=f'Doanh thu {last_month_str}', color='skyblue')
    rects2 = ax.bar(x + bar_width/2, prev_month_revenues, bar_width,
                    label=f'Doanh thu {prev_month_str}', color='lightcoral')

    # Thêm nhãn dữ liệu
    def add_labels(rects, shares):
        for i, rect in enumerate(rects):
            height = rect.get_height()
            share = shares[i]
            revenue_text = format_large_number(height)
            label_text = f'{revenue_text}\n({share}%)'
            ax.annotate(label_text,
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 4), textcoords="offset points",
                        ha='center', va='bottom', fontsize=8.5, fontweight='bold')

    add_labels(rects1, last_month_shares)
    add_labels(rects2, prev_month_shares)

    # Định dạng và trang trí biểu đồ
    ax.set_title(f'Doanh thu công ty tháng {last_month_str} và tháng {prev_month_str}',
                 fontsize=15, fontweight='bold', pad=15)
    ax.set_ylabel('Doanh thu (VNĐ)', fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.legend(loc='upper right')
    ax.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(format_large_number))
    ax.set_ylim(0, max(max(last_month_revenues), max(prev_month_revenues)) * 1.3)
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()

    # Lưu vào buffer trong bộ nhớ
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi)
    buf.seek(0)
    plt.close(fig) # Đóng figure để giải phóng bộ nhớ
    return buf


# --- 5. Logic API: Khởi tạo ứng dụng và các Endpoints ---
app = FastAPI(
    title="Chart Generation API",
    description="API để nhận dữ liệu và tạo biểu đồ doanh thu."
)
# Cấu hình CORS để cho phép truy cập từ mọi nguồn (quan trọng khi n8n gọi API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Chart API is running. Use the /generate-chart/ endpoint to create a chart."}


@app.post("/generate-chart/")
def generate_chart_endpoint(request: ChartRequest):
    """
    Endpoint chính để tạo biểu đồ.
    Nhận dữ liệu theo cấu trúc của ChartRequest và trả về hình ảnh PNG.
    """
    image_buffer = create_revenue_chart(
        chart_data=request.chart_data,
        last_month_str=request.last_month_str,
        prev_month_str=request.prev_month_str,
        width=request.width,
        height=request.height,
        dpi=request.dpi
    )
    
    # Trả về buffer ảnh trực tiếp với đúng media type.
    # Đây là cách hiệu quả nhất để gửi file qua API.
    return StreamingResponse(image_buffer, media_type="image/png")


# --- 6. Chạy Server ---
if __name__ == "__main__":
    # Chạy server trên tất cả các địa chỉ IP của máy, cổng 1234
    uvicorn.run(app, host="0.0.0.0", port=1234)