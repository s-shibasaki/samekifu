import re
import sys
import time
import urllib.parse

import requests
from bs4 import BeautifulSoup
from prettytable import PrettyTable
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-position=-2400,-2400")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    return driver


def search_position(sfen, driver):
    if sfen.startswith("sfen "):
        sfen = sfen[5:]

    encoded_sfen = urllib.parse.quote(sfen)
    url = f"https://shogidb2.com/same?sfen={encoded_sfen}"

    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    results = []
    for game in soup.select("div.join.join-vertical.w-full > a"):
        date_event = game.select_one("p:nth-of-type(1)").text.strip()
        black = game.select_one("p:nth-of-type(2)").text.strip().replace("Black ", "")
        white = game.select_one("p:nth-of-type(3)").text.strip().replace("White ", "")
        strategy = (
            game.select_one("p:nth-of-type(4)").text.strip().replace("Strategy: ", "")
        )
        handicap = (
            game.select_one("p:nth-of-type(5)").text.strip().replace("Handicap: ", "")
        )

        date, event = date_event.split(" ", 1)

        result_url = "https://shogidb2.com" + game["href"]
        result_info = get_result_info(result_url, driver)

        results.append([date, event, black, white, strategy, handicap, result_info])

    return results


def get_result_info(url, driver):
    driver.get(url)

    try:
        # 最後の手まで進めるボタンをクリック
        last_move_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[@phx-click="last"]'))
        )
        last_move_button.click()

        # 200ミリ秒待機
        time.sleep(0.2)

        # JavaScriptを使用してSVG内のテキストを取得
        script = """
        var texts = document.querySelectorAll('#shogiboard svg text');
        return Array.from(texts).map(t => t.textContent).join('|');
        """
        svg_texts = driver.execute_script(script)

        # 結果を解析
        texts = svg_texts.split("|")
        for text in texts:
            match = re.search(
                r"(\d+)手目\s*(投了|千日手|持将棋|切れ負け|反則勝ち|反則負け|入玉勝ち|入玉引き分け)",
                text,
            )
            if match:
                moves = int(match.group(1))
                result = match.group(2)

                if result == "投了":
                    if moves % 2 == 1:
                        return f"{moves}手で後手勝ち（先手{result}）"
                    else:
                        return f"{moves}手で先手勝ち（後手{result}）"
                elif result in ["千日手", "持将棋", "入玉引き分け"]:
                    return f"{moves}手で{result}"
                elif result == "切れ負け":
                    if moves % 2 == 1:
                        return f"{moves}手で後手勝ち（先手{result}）"
                    else:
                        return f"{moves}手で先手勝ち（後手{result}）"
                elif result == "反則勝ち":
                    if moves % 2 == 1:
                        return f"{moves}手で先手の{result}"
                    else:
                        return f"{moves}手で後手の{result}"
                elif result == "反則負け":
                    if moves % 2 == 1:
                        return f"{moves}手で後手の{result}"
                    else:
                        return f"{moves}手で先手の{result}"
                elif result == "入玉勝ち":
                    if moves % 2 == 1:
                        return f"{moves}手で先手の{result}"
                    else:
                        return f"{moves}手で後手の{result}"

        return "結果不明"
    except Exception as e:
        print(f"Error getting result: {e}")
        return "結果不明"


def display_results(results):
    table = PrettyTable()
    table.field_names = ["日付", "大会", "先手", "後手", "戦型", "手合", "結果"]
    table.align = "l"
    for row in results:
        table.add_row(row)
    print(table)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("使用方法: python script.py <SFEN>")
        sys.exit(1)

    sfen = sys.argv[1]
    driver = setup_driver()
    try:
        results = search_position(sfen, driver)
        if results:
            display_results(results)
        else:
            print("結果が見つかりませんでした。")
    finally:
        driver.quit()
