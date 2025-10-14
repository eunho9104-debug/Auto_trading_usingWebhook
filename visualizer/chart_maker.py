import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 한글 폰트 설정 (Windows 기준)
font_path = "C:/Windows/Fonts/malgun.ttf"  # 또는 NanumGothic, 돋움 등
font_prop = fm.FontProperties(fname=font_path)
plt.rcParams["font.family"] = font_prop.get_name()


import seaborn as sns
import matplotlib.pyplot as plt
import os

def plot_price_chart(df, symbol, interval):
    plt.figure(figsize=(12, 6))
    sns.lineplot(data=df, x=df.index, y="close")
    plt.title(f"{symbol} {interval} 종가 흐름")
    plt.xlabel("시간")
    plt.ylabel("종가")
    plt.xticks(rotation=45)
    plt.tight_layout()

    # 이미지 저장
    os.makedirs("visualizer/charts", exist_ok=True)
    filename = f"visualizer/charts/{symbol}_{interval}.png"
    plt.savefig(filename)
    plt.show()  # 👈 이 줄 추가!
    plt.close()
    print(f"✅ 시각화 저장 완료: {filename}")