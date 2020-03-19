#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import lib


def main():
    logger = logging.getLogger('lib')
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.formatter = logging.Formatter(
                fmt='%(name)s::%(levelname)s::%(message)s')
    logger.addHandler(handler)

    lib.servant.servant_list()


if __name__ == '__main__':
    main()
