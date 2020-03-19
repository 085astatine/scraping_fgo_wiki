#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import List, TypedDict
import lxml.html
import requests


_Servant = TypedDict(
        '_Servant',
        {'id': int,
         'class': str,
         'rarity': int,
         'name': str,
         'url': str},
        total=False)


def _parse_servant_table():
    # URL: サーヴァント > 一覧 > 番号順
    url = 'https://w.atwiki.jp/f_go/pages/713.html'
    # 入手不可サーヴァントID
    ignore_servant_ids = (
            83,  # ソロモン
            149,  # ティアマト
            151,  # ゲーティア
            152,  # ソロモン
            168,  # ビーストIII/R
            240)  # ビーストIII/L
    # クラス変換
    to_servant_class = {
            '剣': 'Saber',  # セイバー
            '弓': 'Archer',  # アーチャー
            '槍': 'Lancer',  # ランサー
            '騎': 'Rider',  # ライダー
            '術': 'Caster',  # キャスター
            '殺': 'Assassin',  # アサシン
            '狂': 'Berserker',  # バーサーカー
            '盾': 'Shielder',  # シールダー
            '裁': 'Ruler',  # ルーラー
            '讐': 'Avenger',  # アヴェンジャー
            '分': 'AlterEgo',  # アルターエゴ
            '月': 'MoonCancer',  # ムーンキャンサー
            '降': 'Foreigner',  # フォーリナー
            '獣': 'Beast'}  # ビースト
    # access
    response = requests.get(url)
    etree = lxml.html.fromstring(response.text)
    xpath = ('/html/body//div[@id="wikibody"]/div[2]/div/'
             'table/tbody/tr[td]')
    # サーヴァントリスト作成
    result: List[_Servant] = []
    for row in etree.xpath(xpath):
        servant_id = int(row.xpath('td[1]')[0].text)
        if servant_id in ignore_servant_ids:
            continue
        rarity = int(row.xpath('td[2]')[0].text)
        servant_name = row.xpath('td[3]//a')[0].text
        servant_class = to_servant_class[row.xpath('td[4]')[0].text.strip()]
        servant_url = row.xpath('td[3]//a')[0].get('href')
        result.append({
                'id': servant_id,
                'class': servant_class,
                'rarity': rarity,
                'name': servant_name,
                'url': servant_url})
    return result


def servant_list():
    servant_list = _parse_servant_table()
    print(servant_list)
