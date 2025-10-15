import io
import uvicorn
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List

# --- 2. Cấu hình Matplotlib ---
matplotlib.use('Agg')


# --- 3. Pydantic Models: Định nghĩa cấu trúc dữ liệu đầu vào ---

# Model cho route gốc (/generate-chart/)
class ChartRequest(BaseModel):
    chart_data: dict
    last_month_str: str
    prev_month_str: str
    width: int = 10
    height: int = 8  # <<< ĐÃ SỬA: Đồng nhất chiều cao mặc định thành 8
    dpi: int = 100

# Model mới cho route biểu đồ thanh ngang nhóm (/generate-grouped-barchart/)
class GroupedChartData(BaseModel):
    labels: List[str]
    last_month_revenue: List[float]
    prev_month_revenue: List[float]

class GroupedChartRequest(BaseModel):
    chart_data: GroupedChartData
    last_month_str: str
    prev_month_str: str
    width: int = 10
    height: int = 8
    dpi: int = 100


# --- 4. Logic vẽ biểu đồ ---

# Hàm 1: Logic cho biểu đồ cột nhóm gốc
def create_revenue_chart(chart_data: dict, last_month_str: str, prev_month_str: str, width: int, height: int, dpi: int):
    # (Giữ nguyên logic của hàm gốc của bạn ở đây...)
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
                        ha='center', va='bottom', fontsize=8, fontweight='bold') # <<< ĐÃ SỬA: Đồng nhất cỡ chữ thành 8

    add_labels(rects1, last_month_shares)
    add_labels(rects2, prev_month_shares)
    
    # Định dạng
    ax.set_title(f'Doanh thu công ty tháng {last_month_str} và tháng {prev_month_str}',
                 fontsize=14, fontweight='bold', pad=20)
    ax.set_ylabel('Doanh thu (VNĐ)', fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.legend(loc='upper right')
    ax.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(format_large_number))
    ax.set_ylim(0, max(max(last_month_revenues), max(prev_month_revenues)) * 1.3)
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()

    # Lưu vào buffer
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi)
    buf.seek(0)
    plt.close(fig)
    return buf

# Hàm 2: Logic mới cho biểu đồ thanh ngang nhóm
def create_horizontal_grouped_barchart(chart_data: dict, last_month_str: str, prev_month_str: str, width: int, height: int, dpi: int):
    """
    Vẽ biểu đồ thanh ngang nhóm so sánh doanh thu 2 tháng, sắp xếp theo doanh thu tháng gần nhất.
    """
    def format_large_number(num, pos=None):
        if abs(num) >= 1_000_000_000: return f'{num / 1_000_000_000:.2f} tỷ'
        if abs(num) >= 1_000_000: return f'{num / 1_000_000:.1f} tr'
        if abs(num) >= 1_000: return f'{num / 1_000:.1f} k'
        return f'{num:,.0f}'

    labels = np.array(chart_data['labels'])
    last_month_revenues = np.array(chart_data['last_month_revenue'])
    prev_month_revenues = np.array(chart_data['prev_month_revenue'])

    sorted_indices = np.argsort(last_month_revenues)[::-1]
    labels = labels[sorted_indices]
    last_month_revenues = last_month_revenues[sorted_indices]
    prev_month_revenues = prev_month_revenues[sorted_indices]

    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
    fig, ax = plt.subplots(figsize=(width, height))

    y = np.arange(len(labels))
    bar_height = 0.35

    rects1 = ax.barh(y - bar_height/2, last_month_revenues, bar_height, label=f'Doanh thu {last_month_str}', color='skyblue')
    rects2 = ax.barh(y + bar_height/2, prev_month_revenues, bar_height, label=f'Doanh thu {prev_month_str}', color='lightcoral')

    def add_labels(rects):
        for rect in rects:
            width_val = rect.get_width()
            ax.annotate(format_large_number(width_val),
                        xy=(width_val, rect.get_y() + rect.get_height() / 2),
                        xytext=(3, 0), textcoords="offset points",
                        ha='left', va='center', fontsize=8, fontweight='bold')

    add_labels(rects1)
    add_labels(rects2)

    ax.set_title(f'Doanh thu công ty theo CP tháng {last_month_str} và tháng {prev_month_str}',
                 fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('Doanh thu (VNĐ)', fontsize=10)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=10)
    ax.legend(loc='lower right')
    ax.invert_yaxis()
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(format_large_number))
    ax.set_xlim(0, max(max(last_month_revenues), max(prev_month_revenues)) * 1.2)
    ax.grid(axis='x', linestyle='--', alpha=0.7)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi)
    buf.seek(0)
    plt.close(fig)
    return buf


# --- 5. Logic API: Khởi tạo ứng dụng và các Endpoints ---
app = FastAPI(
    title="Chart Generation API",
    description="API để nhận dữ liệu và tạo các loại biểu đồ doanh thu."
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Chart API is running. Use the /generate-chart/ or /generate-grouped-barchart/ endpoint."}


# Endpoint 1: Biểu đồ cột nhóm gốc
@app.post("/generate-chart/")
def generate_chart_endpoint(request: ChartRequest):
    image_buffer = create_revenue_chart(
        chart_data=request.chart_data,
        last_month_str=request.last_month_str,
        prev_month_str=request.prev_month_str,
        width=request.width, height=request.height, dpi=request.dpi
    )
    return StreamingResponse(image_buffer, media_type="image/png")

# Endpoint 2: Biểu đồ thanh ngang nhóm mới
@app.post("/generate-grouped-barchart/")
def generate_grouped_barchart_endpoint(request: GroupedChartRequest):
    """
    Endpoint chính để tạo biểu đồ thanh ngang nhóm so sánh doanh thu theo CP.
    """
    image_buffer = create_horizontal_grouped_barchart(
        # Chuyển đổi Pydantic model thành dict để hàm có thể sử dụng
        chart_data=request.chart_data.model_dump(),
        last_month_str=request.last_month_str,
        prev_month_str=request.prev_month_str,
        width=request.width,
        height=request.height,
        dpi=request.dpi
    )
    return StreamingResponse(image_buffer, media_type="image/png")


# --- 6. Chạy Server ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=1234)