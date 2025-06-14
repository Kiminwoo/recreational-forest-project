from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# ChromeDriver 경로 지정
service = Service("chromedriver.exe")  # 환경에 맞게 수정

options = webdriver.ChromeOptions()
driver = webdriver.Chrome(service=service, options=options)
driver.get("https://www.foresttrip.go.kr/com/login.do?targetUrl=/com/index.do")

# 약간 대기
time.sleep(3)

# iframe 전환
iframe = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#ifrm"))
)
driver.switch_to.frame(iframe)

# 로그인 입력창 찾기
user_id = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.NAME, "userId"))
)
password = driver.find_element(By.NAME, "userPwd")

# 로그인 정보 입력
user_id.send_keys("id")
password.send_keys("pw")

# 로그인 버튼 클릭
login_button = driver.find_element(By.XPATH, "//a[@onclick='goLogin()']")
login_button.click()

# 결과 대기
time.sleep(5)
