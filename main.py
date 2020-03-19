#!/usr/bin/env python
# -*- coding: utf-8 -*-

import selenium.webdriver
import lib.servant


def main():
    options = selenium.webdriver.ChromeOptions()
    options.add_argument('--headless')

    driver = selenium.webdriver.Chrome(options=options)

    lib.servant.servant_list(driver)

    driver.close()


if __name__ == '__main__':
    main()
