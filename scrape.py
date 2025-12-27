from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup 
import time

# --- Setup Chrome options ---
chrome_options = Options()
chrome_options.add_argument("--headless")  
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")

# --- Path to your chromedriver ---
service = Service("/home/wanyi/Downloads/chromedriver-linux64/chromedriver")
driver = webdriver.Chrome(service=service, options=chrome_options)

# --- Load the page ---
def get_info(year, unit_code):
    """
    Load unit information from the Monash Handbook based on intake year and unit code
    It retrieves the unit name, semester availability, and assessment breakdown

    @param year: The intake year to search for
    @param unit_code: The unit code to search for

    @return: unit_name, semester_str, assign, test, final
             (each can replace the user database directly after changes made)
    """
    url = f"https://handbook.monash.edu/{year}/units/{unit_code}"
    driver.get(url)
    time.sleep(3)

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    unit_name = extract_unit_name(soup)
    if not unit_name:
        return None, None, None, None, None

    semesters_str = extract_semesters(soup)
    expand_assessment_sections(driver)
    assign, test, final = extract_assessments(driver)

    return unit_name, semesters_str, assign, test, final


# -------------------- Helper Functions --------------------

def extract_unit_name(soup):
    """
    Extract the unit name from the Monash Handbook page
    @param soup: BeautifulSoup object of the page
    @return: unit name as a string, or None if not found
    """
    h2_tag = soup.find("h2", {"data-testid": "ai-header"})
    if not h2_tag:
        return None

    text = h2_tag.get_text(strip=True)
    return text.split("-", 1)[1].strip() if "-" in text else text.strip()


def extract_semesters(soup):
    """
    Extract which semesters the unit is available in Malaysia campus
    @param soup: BeautifulSoup object of the page
    @return: A string of semester numbers separated by semicolons (e.g., "1;2")
    """
    semester_headers = soup.find_all(
        "h4",
        class_="css-3d3idg-AccordionRowComponent--SDefaultHeading evoq1ba0"
    )
    semesters_set = set()
    for h in semester_headers:
        text = h.get_text(strip=True).  upper()
        if "-MALAYSIA-" in text:
            if "S1" in text:
                semesters_set.add("1")
            if "S2" in text:
                semesters_set.add("2")
    return ";".join(sorted(semesters_set, key=int)) if semesters_set else "NONE"


def expand_assessment_sections(driver):
    """
    Expand all assessment accordion sections on the page to make them visible for scraping
    @param driver: Selenium WebDriver instance
    """
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[id^='Assessment-']"))
        )
        accordion_buttons = driver.find_elements(By.CSS_SELECTOR, "div[id^='Assessment-'] button")

        for button in accordion_buttons:
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", button)
                time.sleep(0.3)
                if button.get_attribute("aria-expanded") != "true":
                    driver.execute_script("arguments[0].click();", button)
                    time.sleep(0.5)
            except:
                continue
        time.sleep(1)
    except:
        pass


def extract_assessments(driver):
    """
    Extract assessment components (assignment, test, final exam) and their weightings
    @param driver: Selenium WebDriver instance
    @return: Tuple of (assign, test, final) strings
    """
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    assign_list, test_list, final_list = [], [], []

    assessment_section = soup.find("div", id=lambda x: x and x.startswith("Assessment-"))
    if assessment_section:
        sections = assessment_section.find_all(
            "h4", class_="css-3d3idg-AccordionRowComponent--SDefaultHeading"
        )
        for section in sections:
            section_title = section.get_text(strip=True).lower()
            accordion_row = section.find_parent(
                "div", class_=lambda x: x and "SAccordionItemHeader" in str(x)
            )

            if accordion_row:
                content_div = accordion_row.find_next_sibling()
                if content_div:
                    value_divs = content_div.find_all(
                        "div", class_=lambda x: x and "CardBody" in str(x)
                    )
                    for vdiv in value_divs:
                        text = vdiv.get_text(strip=True)
                        if "Value %" in text or "Value%" in text:
                            value = (
                                text.replace("Value %", "")
                                .replace("Value%", "")
                                .replace(":", "")
                                .strip()
                            )
                            if "quiz" in section_title or "test" in section_title:
                                test_list.append(value)
                            elif "examination" in section_title or "final" in section_title:
                                final_list.append(value)
                            else:
                                assign_list.append(value)
                            break

    assign = ";".join(assign_list) if assign_list else "NONE"
    test = ";".join(test_list) if test_list else "NONE"
    final = ";".join(final_list) if final_list else "NONE"
    return assign, test, final

