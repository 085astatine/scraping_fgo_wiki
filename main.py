#!/usr/bin/env python
# -*- coding: utf-8 -*-

import selenium.webdriver


def main():
    url = 'https://w.atwiki.jp/f_go/'

    options = selenium.webdriver.ChromeOptions()
    options.add_argument('--headless')

    driver = selenium.webdriver.Chrome(options=options)
    driver.get(url)
    print(driver.page_source)
    driver.close()


if __name__ == '__main__':
    main()
