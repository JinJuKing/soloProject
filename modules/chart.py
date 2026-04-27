import plotly.graph_objects as go
from plotly.subplots import make_subplots

from modules.formatting import format_krw


def build_candle_chart(history, current_price, position=None):
    chart_data = history.copy()
    if chart_data.empty:
        return None

    last_index = chart_data.index[-1]
    chart_data.loc[last_index, "현재가"] = current_price
    chart_data.loc[last_index, "고가"] = max(float(chart_data.loc[last_index, "고가"]), current_price)
    chart_data.loc[last_index, "저가"] = min(float(chart_data.loc[last_index, "저가"]), current_price)

    increasing_color = "#ef4444"
    decreasing_color = "#2563eb"
    volume_colors = [
        increasing_color if close_price >= open_price else decreasing_color
        for open_price, close_price in zip(chart_data["시가"], chart_data["현재가"])
    ]

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.76, 0.24],
    )
    fig.add_trace(
        go.Candlestick(
            x=chart_data.index,
            open=chart_data["시가"],
            high=chart_data["고가"],
            low=chart_data["저가"],
            close=chart_data["현재가"],
            increasing_line_color=increasing_color,
            increasing_fillcolor=increasing_color,
            decreasing_line_color=decreasing_color,
            decreasing_fillcolor=decreasing_color,
            name="가격",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            x=chart_data.index,
            y=chart_data["거래량"],
            marker_color=volume_colors,
            opacity=0.45,
            name="거래량",
        ),
        row=2,
        col=1,
    )

    fig.add_hline(
        y=current_price,
        line_dash="dot",
        line_color=increasing_color,
        annotation_text=f"현재가 {format_krw(current_price)}",
        annotation_position="right",
        row=1,
        col=1,
    )

    if position:
        line_specs = [
            ("가상 진입가", position["buy_price"], "#64748b"),
            ("목표가", position["target_price"], "#16a34a"),
            ("손절가", position["stop_price"], "#f97316"),
        ]
        for label, price, color in line_specs:
            fig.add_hline(
                y=price,
                line_dash="dash",
                line_color=color,
                annotation_text=f"{label} {format_krw(price)}",
                annotation_position="right",
                row=1,
                col=1,
            )

    fig.update_layout(
        height=560,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
        hovermode="x unified",
        showlegend=False,
        xaxis_rangeslider_visible=False,
    )
    fig.update_xaxes(showgrid=True, gridcolor="#e5e7eb", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#e5e7eb", zeroline=False, tickformat=",", row=1, col=1)
    fig.update_yaxes(showgrid=False, zeroline=False, tickformat=",.0f", row=2, col=1)
    return fig
