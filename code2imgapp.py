# from https://docs.streamlit.io/develop/tutorials/llms/build-conversational-apps

import streamlit as st
from code2img import code2img

code = """
import matplotlib.pyplot as plt

# Define the SWOT analysis data
strengths = ['전문성과 경험', '목표와 목적의 명확성', '자원, 예산, 시간 확보']
weaknesses = ['협업과 의사소통의 부족', '일정 및 예산 관리의 미흡', '기술, 지식, 경험의 부족']
opportunities = ['전문성과 명성 향상', '새로운 고객과 파트너 유치', '비즈니스 모델 개발과 확장']
threats = ['경쟁사의 등장과 시장 환경 변화', '자원, 예산, 시간 부족', '기술, 지식, 경험의 부족']

# Create a bar chart for the SWOT analysis
fig, ax = plt.subplots()
ax.barh(range(len(strengths)), strengths, color='green', label='강점')
ax.barh(range(len(strengths), len(strengths)+len(weaknesses)), weaknesses, color='red', label='약점')
ax.barh(range(len(strengths)+len(weaknesses), len(strengths)+len(weaknesses)+len(opportunities)), opportunities, color='blue', label='기회')
ax.barh(range(len(strengths)+len(weaknesses)+len(opportunities), len(strengths)+len(weaknesses)+len(opportunities)+len(threats)), threats, color='orange', label='위협')

# Set the chart title and axis labels
ax.set_title('SWOT Analysis')
ax.set_xlabel('강도')
ax.set_ylabel('카테고리')

# Add a legend to the chart
ax.legend()

plt.show()
"""

if __name__ == "__main__":
    st.title("🌞 Solar Code to Img")

    code = st.text_area("Write your context or problems here", code, height=200)

    button = st.button("Let's Solve!")

    if button and code:
        img, msg = code2img(code)
        if img:
            st.image(img, caption="Generated Diagram")
        else:
            st.error(msg)
