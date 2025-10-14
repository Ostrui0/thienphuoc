import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import io
import base64  # ✅ Thêm dòng này
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse  # ✅ Thêm dòng này
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Request(BaseModel):
    chart_data: dict
    last_month_str: str
    prev_month_str: str
    width: int = 10
    height: int = 6
    dpi: int = 100


def create_revenue_chart(request: Request):
    """Vẽ biểu đồ so sánh doanh thu và lưu vào buffer."""
    def format_large_number(num, pos=None):
        if num >= 1_000_000_000:
            return f'{num / 1_000_000_000:.2f} tỷ'
        if num >= 1_000_000:
            return f'{num / 1_000_000:.2f} tr'
        if num >= 1_000:
            return f'{num / 1_000:.1f} k'
        return f'{num:,.0f}'

    labels = request.chart_data['labels']
    last_month_revenues = request.chart_data['last_month']['revenue']
    last_month_shares = request.chart_data['last_month']['share']
    prev_month_revenues = request.chart_data['prev_month']['revenue']
    prev_month_shares = request.chart_data['prev_month']['share']

    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
    fig, ax = plt.subplots(figsize=(request.width, request.height))

    x = np.arange(len(labels))
    bar_width = 0.35

    rects1 = ax.bar(x - bar_width/2, last_month_revenues, bar_width,
                    label=f'Doanh thu {request.last_month_str}', color='skyblue')
    rects2 = ax.bar(x + bar_width/2, prev_month_revenues, bar_width,
                    label=f'Doanh thu {request.prev_month_str}', color='lightcoral')

    def add_labels(rects, shares):
        for i, rect in enumerate(rects):
            height = rect.get_height()
            share = shares[i]
            revenue_text = format_large_number(height)
            label_text = f'{revenue_text}\n({share}%)'
            ax.annotate(label_text,
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 4),
                        textcoords="offset points",
                        ha='center', va='bottom',
                        fontsize=8.5, fontweight='bold')

    add_labels(rects1, last_month_shares)
    add_labels(rects2, prev_month_shares)

    ax.set_title(f'Doanh thu công ty tháng {request.last_month_str} và tháng {request.prev_month_str}',
                 fontsize=15, fontweight='bold', pad=15)
    ax.set_ylabel('Doanh thu (VNĐ)', fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.legend(loc='upper right')

    ax.get_yaxis().set_major_formatter(
        matplotlib.ticker.FuncFormatter(format_large_number))
    ax.set_ylim(0, max(max(last_month_revenues), max(prev_month_revenues)) * 1.3)
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=request.dpi)
    buf.seek(0)
    plt.close(fig)
    return buf


@app.post("/create_revenue_chart")
async def create_revenue_chart_endpoint(request: Request):
    buf = create_revenue_chart(request)
    # ✅ Convert buffer -> Base64 string
    img_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return JSONResponse(content={"image": img_base64})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=1234)
