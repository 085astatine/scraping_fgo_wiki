# -*- coding: utf-8 -*-

import logging
from .item import Item, item_list
from .servant import servant_list
from .text import Dictionary, Text


logging.getLogger(__package__).addHandler(logging.NullHandler())
