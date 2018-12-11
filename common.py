#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  common.py
#  
#  Copyright 2018 Egor <egor@l26-1310-ubu>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  

import nltk
import re
import requests
from bs4 import BeautifulSoup as BS

from wordcloud import WordCloud, STOPWORDS
from nltk.corpus import stopwords
from nltk.tokenize import wordpunct_tokenize, word_tokenize, sent_tokenize, MWETokenizer

from nltk.collocations import BigramCollocationFinder, TrigramCollocationFinder
from nltk.metrics import BigramAssocMeasures, TrigramAssocMeasures, distance

from pymystem3 import Mystem

import string

from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
import time
import sqlalchemy as sa
import glob

import locale

import matplotlib.pyplot as plt

stop_w=set(stopwords.words('russian'))
stop_w.update(string.punctuation)

def show_cloud(text='', title=None, stop_words=stop_w, fig_size=(9, 9), 
               max_words=200, width=400, height=200, filename=None, freq_array=None):
    wc=WordCloud(background_color='white', stopwords=stop_w, max_words=max_words, collocations=True,
                 max_font_size=40, scale=3, random_state=1, width=width, height=height)
    if freq_array:
        wc.fit_words(freq_array)
    else:
        wc.generate(str(text))
    fig=plt.figure(figsize=fig_size)
    plt.axis('off')
    if title:
        fig.suptitle(title, fontsize=14)
        fig.subplots_adjust(top=2.3)
    plt.imshow(wc)
    plt.tight_layout()
    plt.show();
    if filename:
        plt.savefig(filename);

req_headers={'accept': 'text/plain, text/html',
'accept-encoding': 'gzip, deflate, br',
'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
'cache-control': 'max-age=0',
'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/69.0.3497.81 Chrome/69.0.3497.81 Safari/537.36'}

def iterate_group(iterator, count):
    itr=iter(iterator)
    for i in range(0, len(iterator), count):
        yield iterator[i:i+count]

class ArticlesDataFrame(pd.DataFrame):

    @property
    def _constructor(self):
        return ArticlesDataFrame

    def to_sql(self, name, con, flavor='sqlite', schema=None, if_exists='fail', index=True,
               index_label=None, chunksize=1000, dtype=None):

        def drop_table(strTName):
            meta=sa.MetaData(bind=con)
            try:
                tbl_=sa.Table(strTName, meta, autoload=True, autoload_with=con)
                tbl_.drop(con, checkfirst=False)
            except:
                pass
        
        def create_table(strTName, strIndName):
            metadata=sa.MetaData(bind=con)
            bname_t=sa.Table(strTName, metadata,
                        sa.Column(strIndName, sa.Text, primary_key=True, nullable=False, autoincrement=False),
                        *[sa.Column(c_name, sa.Text, nullable=True) for c_name in self.columns])
            metadata.create_all()

        def buff_insert(alch_table, insert_prefix, values, buff_size=chunksize):
            for i in iterate_group(values, buff_size):
                inserter = alch_table.insert(prefixes=insert_prefix, values=i)
                con.execute(inserter)
             
        if if_exists=='replace':
            drop_table(name)
            if_exists='fail'
        
        if not con.dialect.has_table(con, name):
            create_table(name, self.index.name)
            
        meta=sa.MetaData(bind=con)
        tbl_names=sa.Table(name, meta, autoload=True, autoload_with=con)
        vals=self.reset_index().to_dict(orient='records')
        #print(vals)
        inserter=None

        if if_exists in ['append', 'ignore']:
            #inserter = tbl_names.insert(prefixes=['OR IGNORE'], values=vals)
            buff_insert(tbl_names, ['OR IGNORE'], vals, buff_size=chunksize)
        elif if_exists in ['update', 'upsert']:
            buff_insert(tbl_names, ['OR REPLACE'], vals, buff_size=chunksize)
        else:
            buff_insert(tbl_names, [''], vals, buff_size=chunksize)

def get_expert_ribbon(strURL=r'http://expert.ru/dossier/podrubrika/economics/'):
    def get_item(strUrl):
        #print(strUrl)
        r=sessExp.get(strUrl)
        soup=BS(r.text, 'html.parser')
        
        pcut=soup.findAll('p', class_='cutting')
        
        div_item=soup.find('div', id="doc_body")
        ps=div_item.findAll('p', class_='')
        heads=div_item.findAll(['h2', 'h3'])
        time.sleep(1)
        return {'text':'\n'.join([p.text.strip() for p in ps]), 'heads':'\n'.join([h.text.strip() for h in heads]), 
            'cuts':'\n'.join([p.text.strip() for p in pcut])}
     
        
    sessExp=requests.session()
    sessExp.headers.update(req_headers)
    
    r=sessExp.get(strURL)
    soup=BS(r.text, 'html.parser')

    articles=soup.findAll('article', class_='box-tags-news')

    rubr_pre=''
    lst_ret=[]
    for a in articles:
    
        rubr=a.find('a', class_='vremena_base__red')
        span_date=a.find('span', class_='date')
        exp_num_link=span_date.find('a')
        art_title= a.find('h2')
        art_link=art_title.find('a')
        art_date=None
        expert_num=None
        a_pre=None
        if art_title.text.strip() =='Коротко':
            continue
        p_short=None
        try:
            p_short=a.find('p').text
        except:
            pass
        
        try:
            a_pre=rubr.text.strip()
        except:
            pass

        if exp_num_link:
            rf=re.match(r'.*/(?P<year>\d{4})/(?P<num>\d{1,2})', exp_num_link['href'])
            expert_num=rf['num']
            ar = sessExp.get('http://expert.ru/' + art_link['href'])
            spp=BS(ar.text, 'html.parser')
            div=spp.find('section', class_='panel-info')

            strArtDate=div.text[div.text.index(',')+1:].strip()
            dt=datetime.strptime(strArtDate, '%d.%m.%Y')
            
            art_date=dt
        else:
            rf=re.match(r'.*/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})', art_link['href'])
            art_date=date(int(rf['year']), int(rf['month']), int(rf['day']))
        link='http://expert.ru' + art_link['href']
        dct_ret={'title':a.h2.text, 'rubrica': a_pre, 'link':link, 
               'date':art_date, 'num':expert_num, 'short':p_short}
        dct_ret.update(get_item(link))
        lst_ret.append(dct_ret)
        #print(dct)
        print('Done for ', a.h2.text)
    return lst_ret
    
def get_parts(strPara):
    strText=re.sub(r'— ', r' .', strPara) #.replace('—', ' .')
    #print(strText)
    m_engs=re.compile(r'(?P<engs>[A-Za-z-]+[A-Za-z& ]*)')
    m_ru=re.compile(r'(?<![.?!…-] )(?<=[ \(])([А-Я]+[А-Яа-я-]*\b\s*(?:[А-Я«]+[а-я»]*)*\s*(?:[А-Я]+[а-я]*)*\s*(?:[А-Я]+[а-я]*)*)')
    m_qt=re.compile(r'«(?P<quoted>[^»]+)»') # ? - " `` etc
    
    m_split=re.compile(r'([.\n\r?!]+)')
    
    engs=list(filter(None, [i.strip() for i in m_engs.findall(strText) if i.strip() not in ['', '-']]))
    rus=list(filter(None, [i.strip() for i in m_ru.findall(strText[1:])]))
    quoted=list(filter(None, [i.strip() for i in m_qt.findall(strText)]))
    
    sents=[i.strip() for i in m_split.split(strText)]
    #print(quoted)
    
    return {'abr_eng':engs, 'abr_ru':rus, 'quoted':quoted, 
            'sents':list(filter(None, sents[0::2])), 'ends':sents[1::2]}
                              
def make_exp_items_df(link, text, name):
    def make_row(text):
        for k, i in enumerate(list(filter(None, text))):
            emm=get_parts(i)
            emm.update({'link':link, 'name':name})
            yield emm
    #print(link, name, text[3])
    return pd.DataFrame([r for r in make_row(text)])
