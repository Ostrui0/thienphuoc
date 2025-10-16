import io
import uvicorn
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List

# --- 2. Cấu hình Matplotlib ---
matplotlib.use('Agg')


# --- 3. Pydantic Models: Định nghĩa cấu trúc dữ liệu đầu vào ---

# Model cho Endpoint 1 (/generate-chart/)
class ChartRequest(BaseModel):
    chart_data: dict
    last_month_str: str
    prev_month_str: str
    width: int = 10
    height: int = 8
    dpi: int = 100

# Model cho Endpoint 2 (/generate-grouped-barchart/)
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

# Model cho Endpoint 3 (/generate-new-user-chart/)
class NewUserChartData(BaseModel):
    labels: List[str]
    new_user_last_month: List[int]
    new_user_prev_month: List[int]

class NewUserChartRequest(BaseModel):
    chart_data: NewUserChartData
    last_month_str: str
    prev_month_str: str
    width: int = 10
    height: int = 7
    dpi: int = 100


# --- 4. Logic vẽ biểu đồ ---

# Hàm 1: Logic cho biểu đồ cột nhóm doanh thu (giữ nguyên)
def create_revenue_chart(chart_data: dict, last_month_str: str, prev_month_str: str, width: int, height: int, dpi: int):
    def format_large_number(num, pos=None):
        if num >= 1_000_000_000: return f'{num / 1_000_000_000:.2f} tỷ'
        if num >= 1_000_000: return f'{num / 1_000_000:.2f} tr'
        if num >= 1_000: return f'{num / 1_000:.1f} k'
        return f'{num:,.0f}'
    labels = chart_data['labels']
    last_month_revenues = chart_data['last_month']['revenue']
    last_month_shares = chart_data['last_month']['share']
    prev_month_revenues = chart_data['prev_month']['revenue']
    prev_month_shares = chart_data['prev_month']['share']
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
    fig, ax = plt.subplots(figsize=(width, height))
    x = np.arange(len(labels))
    bar_width = 0.35
    rects1 = ax.bar(x - bar_width/2, last_month_revenues, bar_width, label=f'Doanh thu {last_month_str}', color='skyblue')
    rects2 = ax.bar(x + bar_width/2, prev_month_revenues, bar_width, label=f'Doanh thu {prev_month_str}', color='lightcoral')
    def add_labels(rects, shares):
        for i, rect in enumerate(rects):
            height = rect.get_height()
            share = shares[i]
            revenue_text = format_large_number(height)
            label_text = f'{revenue_text}\n({share}%)'
            ax.annotate(label_text, xy=(rect.get_x() + rect.get_width() / 2, height), xytext=(0, 4), textcoords="offset points", ha='center', va='bottom', fontsize=8, fontweight='bold')
    add_labels(rects1, last_month_shares)
    add_labels(rects2, prev_month_shares)
    ax.set_title(f'Doanh thu công ty tháng {last_month_str} và tháng {prev_month_str}', fontsize=14, fontweight='bold', pad=20)
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
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi)
    buf.seek(0)
    plt.close(fig)
    return buf

# Hàm 2: Logic cho biểu đồ thanh ngang nhóm doanh thu (giữ nguyên)
def create_horizontal_grouped_barchart(chart_data: dict, last_month_str: str, prev_month_str: str, width: int, height: int, dpi: int):
    def format_large_number(num, pos=None):
        if abs(num) >= 1_000_000_000: return f'{num / 1_000_000_000:.2f} tỷ'
        if abs(num) >= 1_000_000: return f'{num / 1_000_000:.1f} tr'
        if abs(num) >= 1_000: return f'{num / 1_000:.1f} k'
        return f'{num:,.0f}'
    labels = np.array(chart_data['labels'])
    last_month_revenues = np.array(chart_data['last_month_revenue'])
    prev_month_revenues = np.array(chart_data['prev_month_revenue'])
    sorted_indices = np.argsort(last_month_revenues)[::-1]
    labels, last_month_revenues, prev_month_revenues = labels[sorted_indices], last_month_revenues[sorted_indices], prev_month_revenues[sorted_indices]
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
            ax.annotate(format_large_number(width_val), xy=(width_val, rect.get_y() + rect.get_height() / 2), xytext=(3, 0), textcoords="offset points", ha='left', va='center', fontsize=8, fontweight='bold')
    add_labels(rects1)
    add_labels(rects2)
    ax.set_title(f'Doanh thu công ty theo CP tháng {last_month_str} và tháng {prev_month_str}', fontsize=14, fontweight='bold', pad=20)
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

# Hàm 3: Logic cho biểu đồ cột nhóm người dùng mới
def create_new_user_chart(chart_data: dict, last_month_str: str, prev_month_str: str, width: int, height: int, dpi: int):
    def format_simple_number(num, pos=None): return f'{int(num):,}'
    labels = np.array(chart_data['labels'])
    last_month_users = np.array(chart_data['new_user_last_month'])
    prev_month_users = np.array(chart_data['new_user_prev_month'])
    sorted_indices = np.argsort(last_month_users)[::-1]
    labels, last_month_users, prev_month_users = labels[sorted_indices], last_month_users[sorted_indices], prev_month_users[sorted_indices]
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
    fig, ax = plt.subplots(figsize=(width, height))
    x = np.arange(len(labels))
    bar_width = 0.35
    rects1 = ax.bar(x - bar_width/2, last_month_users, bar_width, label=f'Lượt đăng ký mới {last_month_str}', color='skyblue')
    rects2 = ax.bar(x + bar_width/2, prev_month_users, bar_width, label=f'Lượt đăng ký mới {prev_month_str}', color='lightcoral')
    def add_labels(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(format_simple_number(height), xy=(rect.get_x() + rect.get_width() / 2, height), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8, fontweight='bold')
    add_labels(rects1)
    add_labels(rects2)
    ax.set_title(f'Lượt đăng ký mới theo top 5 CP tháng {last_month_str} và tháng {prev_month_str}', fontsize=14, fontweight='bold', pad=20)
    ax.set_ylabel('Lượt đăng ký mới', fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=10)
    ax.legend(loc='upper right')
    ax.get_yaxis().set_major_formatter(mticker.FuncFormatter(format_simple_number))
    ax.set_ylim(0, max(max(last_month_users), max(prev_month_users)) * 1.2)
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi)
    buf.seek(0)
    plt.close(fig)
    return buf


# --- 5. Logic API: Khởi tạo ứng dụng và các Endpoints ---
app = FastAPI(title="Chart Generation API", description="API tạo các loại biểu đồ báo cáo.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"message": "Chart API is running. See /docs for available endpoints."}

# Endpoint 1: Biểu đồ cột nhóm doanh thu (giữ nguyên)
@app.post("/generate-chart/")
def generate_chart_endpoint(request: ChartRequest):
    image_buffer = create_revenue_chart(chart_data=request.chart_data, last_month_str=request.last_month_str, prev_month_str=request.prev_month_str, width=request.width, height=request.height, dpi=request.dpi)
    return StreamingResponse(image_buffer, media_type="image/png")

# Endpoint 2: Biểu đồ thanh ngang nhóm doanh thu (giữ nguyên)
@app.post("/generate-grouped-barchart/")
def generate_grouped_barchart_endpoint(request: GroupedChartRequest):
    image_buffer = create_horizontal_grouped_barchart(chart_data=request.chart_data.model_dump(), last_month_str=request.last_month_str, prev_month_str=request.prev_month_str, width=request.width, height=request.height, dpi=request.dpi)
    return StreamingResponse(image_buffer, media_type="image/png")

# Endpoint 3: Biểu đồ cột nhóm người dùng mới
@app.post("/generate-new-user-chart/")
def generate_new_user_chart_endpoint(request: NewUserChartRequest):
    """
    Tạo biểu đồ cột nhóm so sánh lượng người dùng mới theo CP.
    """
    image_buffer = create_new_user_chart(chart_data=request.chart_data.model_dump(), last_month_str=request.last_month_str, prev_month_str=request.prev_month_str, width=request.width, height=request.height, dpi=request.dpi)
    return StreamingResponse(image_buffer, media_type="image/png")


# --- 6. Chạy Server ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=1234)