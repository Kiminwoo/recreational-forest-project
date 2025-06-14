import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchFrameException
import configparser

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('login_script.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_config():
    """config.ini 파일에서 설정 로드"""
    config = configparser.ConfigParser()
    config_file = 'config.ini'
    
    if not os.path.exists(config_file):
        logger.error(f"설정 파일 {config_file}을(를) 찾을 수 없습니다")
        raise FileNotFoundError(f"설정 파일 {config_file}을(를) 찾을 수 없습니다")
        
    config.read(config_file, encoding='utf-8')
    return {
        'chromedriver_path': config['DEFAULT']['CHROMEDRIVER_PATH'],
        'username': config['CREDENTIALS']['USERNAME'],
        'password': config['CREDENTIALS']['PASSWORD'],
        'url': config['DEFAULT']['LOGIN_URL']
    }

def initialize_driver(chromedriver_path, headless=False):
    """Chrome WebDriver 초기화"""
    try:
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(5)
        return driver
    except WebDriverException as e:
        logger.error(f"WebDriver 초기화 실패: {str(e)}")
        raise

def inspect_page(driver):
    """로그인 실패 시 페이지 소스 및 요소 검사"""
    logger.info("디버깅을 위해 페이지 검사 시작...")
    try:
        # 페이지 제목
        logger.info(f"페이지 제목: {driver.title}")
        
        # 페이지 URL
        logger.info(f"현재 URL: {driver.current_url}")
        
        # 페이지 소스 일부
        page_source = driver.page_source[:2000]  # 2000자로 확장
        logger.info(f"페이지 소스 (일부): {page_source}")
        
        # iframe 확인
        try:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            if iframes:
                logger.info(f"{len(iframes)}개의 iframe 발견")
                for i, iframe in enumerate(iframes):
                    logger.info(f"Iframe {i}: src={iframe.get_attribute('src')}, id={iframe.get_attribute('id')}, name={iframe.get_attribute('name')}")
            else:
                logger.info("iframe 없음")
        except Exception as e:
            logger.error(f"iframe 확인 오류: {str(e)}")
        
        # 입력 요소 확인
        try:
            inputs = driver.find_elements(By.TAG_NAME, "input")
            if inputs:
                logger.info("발견된 입력 요소:")
                for i, inp in enumerate(inputs):
                    logger.info(f"Input {i}: ID={inp.get_attribute('id')}, Name={inp.get_attribute('name')}, Type={inp.get_attribute('type')}, Class={inp.get_attribute('class')}")
            else:
                logger.info("입력 요소 없음")
        except Exception as e:
            logger.error(f"입력 요소 검사 오류: {str(e)}")
            
        # 버튼 요소 확인
        try:
            buttons = driver.find_elements(By.TAG_NAME, "button")
            if buttons:
                logger.info("발견된 버튼 요소:")
                for i, btn in enumerate(buttons):
                    logger.info(f"Button {i}: ID={btn.get_attribute('id')}, Name={btn.get_attribute('name')}, Type={btn.get_attribute('type')}, Text={btn.text}")
            else:
                logger.info("버튼 요소 없음")
        except Exception as e:
            logger.error(f"버튼 요소 검사 오류: {str(e)}")
            
    except Exception as e:
        logger.error(f"페이지 검사 중 오류: {str(e)}")

def login(driver, username, password, url):
    """로그인 수행 (재시도 및 iframe 처리 포함)"""
    try:
        logger.info(f"로그인 페이지로 이동: {url}")
        driver.get(url)
        
        # 페이지 로드 대기
        time.sleep(5)  # 동적 콘텐츠를 위해 대기 시간 5초로 증가
        
        # iframe 처리
        try:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for i, iframe in enumerate(iframes):
                try:
                    logger.info(f"iframe {i} (id={iframe.get_attribute('id')}, src={iframe.get_attribute('src')})로 전환 시도")
                    driver.switch_to.frame(iframe)
                    logger.info(f"iframe {i}로 전환 성공")
                    break
                except NoSuchFrameException:
                    logger.warning(f"iframe {i}로 전환 실패")
                    driver.switch_to.default_content()
                    continue
        except Exception as e:
            logger.warning(f"iframe 처리 중 오류: {str(e)}")
        
        # 사용자 이름 필드 선택자
        selectors = [
            (By.ID, "userId"),
            (By.NAME, "userId"),
            (By.ID, "loginId"),
            (By.NAME, "username"),
            (By.ID, "id"),
            (By.NAME, "login"),
            (By.CSS_SELECTOR, "input[name='userId']"),
            (By.CSS_SELECTOR, "input[name='username']"),
            (By.CSS_SELECTOR, "input[name='login']"),
            (By.CSS_SELECTOR, "input[type='text']:not([type='hidden'])")
        ]
        
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            logger.info(f"로그인 시도 {attempt}/{max_attempts}")
            id_input = None
            for by, value in selectors:
                try:
                    logger.info(f"{by}: {value}로 사용자 이름 필드 찾기 시도")
                    id_input = WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((by, value))
                    )
                    logger.info(f"{by}: {value}로 사용자 이름 필드 찾음")
                    break
                except TimeoutException:
                    logger.warning(f"{by}: {value}로 사용자 이름 필드 찾기 실패")
                    continue
            
            if not id_input:
                logger.error("사용자 이름 입력 필드를 찾을 수 없음")
                inspect_page(driver)
                return False
                
            id_input.clear()
            id_input.send_keys(username)
            
            # 비밀번호 필드
            logger.info("비밀번호 입력")
            try:
                pw_input = WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.ID, "userPwd"))
                )
                pw_input.clear()
                pw_input.send_keys(password)
            except TimeoutException:
                logger.error("비밀번호 입력 필드를 찾을 수 없음")
                inspect_page(driver)
                return False
            
            # 로그인 버튼
            logger.info("로그인 버튼 클릭")
            button_selectors = [
                (By.ID, "loginBtn"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "button:contains('로그인')"),
                (By.XPATH, "//button[contains(text(), '로그인')]")
            ]
            login_btn = None
            for by, value in button_selectors:
                try:
                    logger.info(f"{by}: {value}로 로그인 버튼 찾기 시도")
                    login_btn = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((by, value))
                    )
                    logger.info(f"{by}: {value}로 로그인 버튼 찾음")
                    break
                except TimeoutException:
                    logger.warning(f"{by}: {value}로 로그인 버튼 찾기 실패")
                    continue
            
            if not login_btn:
                logger.error("로그인 버튼을 찾을 수 없음")
                inspect_page(driver)
                return False
                
            login_btn.click()
            
            # 로그인 성공 확인
            try:
                driver.switch_to.default_content()
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.ID, "goLogout"))
                )
                logger.info("로그인 성공")
                return True
            except TimeoutException:
                logger.warning(f"로그인 시도 {attempt} 실패, 재시도...")
                time.sleep(3)
                driver.switch_to.default_content()
                continue
                
    except TimeoutException as e:
        logger.error(f"로그인 중 타임아웃: {str(e)}")
        inspect_page(driver)
        return False
    except Exception as e:
        logger.error(f"로그인 실패: {str(e)}")
        inspect_page(driver)
        return False

def main():
    """로그인 프로세스 실행"""
    try:
        config = load_config()
        driver = initialize_driver(config['chromedriver_path'], headless=False)
        
        try:
            if login(driver, config['username'], config['password'], config['url']):
                logger.info("로그인 프로세스 성공")
                time.sleep(2)
            else:
                logger.error("로그인 프로세스 실패")
                
        finally:
            logger.info("브라우저 닫기")
            driver.quit()
            
    except Exception as e:
        logger.error(f"스크립트 실행 실패: {str(e)}")
        raise

if __name__ == "__main__":
    main()
