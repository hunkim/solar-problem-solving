import requests
import base64
import streamlit as st
import urllib
import json
import re
import time

def extract_first_code_block_from_markdown(markdown_content):
    # Define a regular expression to match code blocks in Markdown
    code_block_pattern = r"```(?:\w+\n)?(.*?)```"

    # Use re.search to find the first code block in the Markdown content
    match = re.search(code_block_pattern, markdown_content, re.DOTALL)

    if match:
        return match.group(1)  # Return the content of the first code block
    else:
        return None  # Return None if no code block is found


def remove_show(plot_code: str):
    # remove 'plt.show()' from the code
    return plot_code.replace("plt.show()", "")


def code2img(markdown_content: str):
    code = extract_first_code_block_from_markdown(markdown_content)
    print(code)

    if code is None:
        code = markdown_content

    code = remove_show(code)

    headers = {
        "Authorization": st.secrets["PLOT_API_KEY"],
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:106.0) Gecko/20100101 Firefox/106.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    data = json.dumps(code).encode('utf-8')
    url = st.secrets["PLOT_API_URL"]
    request = urllib.request.Request(url, data=data, headers=headers)

    retries = 3
    backoff = 2

    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request) as response:
                if response.status == 200:
                    img_base64 = response.read().decode('utf-8')
                    print(img_base64[:100])
                    img_data = base64.b64decode(img_base64)
                    return img_data
                else:
                    print(f"Error: {response.read().decode('utf-8')}")
                    return None
        except urllib.error.HTTPError as e:
            print(f"HTTPError: {e.reason}, Code: {e.code}")
        except urllib.error.URLError as e:
            print(f"URLError: {e.reason}")
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
        
        time.sleep(backoff)
        backoff *= 2  # Exponential backoff
    else:
        return None


    response = requests.post(st.secrets["PLOT_API_URL"], data=code, headers=headers)
    if response.status_code == 200:
        # Get the base64-encoded image string from the response
        img_base64 = response.text
        print(img_base64[:100])
        # Decode the base64-encoded image string to obtain binary data
        img_data = base64.b64decode(img_base64)
        return img_data
    else:
        print(f"Error: {response.text}")
        return None


if __name__ == "__main__":
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
    img = code2img(code)
    if img:
        with open("plot.png", "wb") as f:
            f.write(img)
        print("Image saved as plot.png")
