import requests
import re
from bs4 import BeautifulSoup
import sqlite3
import time
import pandas as pd
from itertools import islice

strNounURL=r'https://ru.wiktionary.org/wiki/%D0%9A%D0%B0%D1%82%D0%B5%D0%B3%D0%BE%D1%80%D0%B8%D1%8F:%D0%A0%D1%83%D1%81%D1%81%D0%BA%D0%B8%D0%B5_%D1%81%D1%83%D1%89%D0%B5%D1%81%D1%82%D0%B2%D0%B8%D1%82%D0%B5%D0%BB%D1%8C%D0%BD%D1%8B%D0%B5'
strUrlBase=r'https://ru.wiktionary.org'

req_header={'accept':r'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
'accept-encoding':'gzip, deflate, sdch', 'accept-language':'ru,en-US;q=0.8,en;q=0.6,sr;q=0.4,hr;q=0.2',
'user-agent':r'Mozilla/5.0 (Windows NT 5.2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36}'}


def read_main_list(session, strUrl):
    def find_link(tag):
        return tag.name=='a' and tag.has_attr('title') and tag.string==tag['title']

    nt=session.get(strUrl)
    nt.encoding=nt.apparent_encoding
    soup=BeautifulSoup(nt.text, 'html.parser')

    next_page = soup.find(text='Следующая страница')
    ret_dict = {a.string: strUrlBase + a['href'] for a in soup.findAll(find_link)}

    print(list(ret_dict.keys())[0], list(ret_dict.keys())[-1])

    time.sleep(1)

    if next_page and next_page.parent.name == 'a':
        ret_dict.update(read_main_list(session, strUrlBase + next_page.parent['href']))
        print(len(ret_dict))
        return ret_dict
    else:
        print(ret_dict)
        return ret_dict

def get_noun_list(sess, save_to_csv=True):
    # get full list of russ. nouns
    pdf_nouns = pd.Series(read_main_list(sess, strNounURL))
    if save_to_csv:
        pdf_nouns.to_csv('ru_nouns.csv', sep=';')
    return  pdf_nouns

def chunk(it, size):
    it=iter(it)
    return iter(lambda: tuple(islice(it, size)), ())

def get_nouns_info(sess):
    
    def split_on_tags(lst_tags):
        lst_ret=list()
        lst_cnt=len(lst_tags)
        for i in range(lst_cnt):
            lst_siblings=list(lst_tags[i].next_siblings)
            if i<lst_cnt-1:
                lst_ret.append(' '.join([str(t) for t in lst_siblings[:lst_siblings.index(lst_tags[i+1])]]))
            else:
                lst_ret.append(' '.join([str(t) for t in lst_siblings]))
        
        return lst_ret
            
    def get_morfo(p_tag):
        dct={'morf0':p_tag[0].text.strip()}
        strP1=p_tag[1].text.strip().lower()
        print(strP1)
        sklZ=re.search(r'тип склонения (?P<sklz>.+) по классификации', strP1)
        dct.update(dict(zip(['type', 'anima', 'gender', 'declen'], strP1[:strP1.find('(')].split(','))))
        dct.update({'declen_Z':sklZ['sklz']})
        strP2=p_tag[2].text[:p_tag[2].text.find('[')].lower().replace('корень', 'root').replace('корни', 'root')
        strP2=strP2.replace('ы', '').replace('суффикс', 'suff')
        strP2=strP2.replace('окончание', 'ends').replace('окончания', 'ends')
        strP2=strP2.replace('приставка', 'pre').replace('приставки', 'pre')
        lst_morf=list(filter(None, re.split(r'[:;.]', strP2)))
        dct.update(dict(zip(lst_morf[0::2], lst_morf[1::2])))
        return {k:v.strip().lower() for k, v in dct.items()}
        
    def parse_item(strURL, strName):
        #https://ru.wiktionary.org/wiki/%D0%BA%D0%BE%D1%88%D0%BA%D0%B0 - testing string - кошка
        ht=sess.get(strURL)
        ht.encoding=ht.apparent_encoding
        soup=BeautifulSoup(ht.text, 'html.parser')
        hs=[h.parent for h in soup.findAll('span', class_='mw-headline', text=re.compile(strName))]
        work_list=None
        
        if hs:
            work_list=[BeautifulSoup(t, 'html.parser') for t in split_on_tags(hs)]
        else:
            h1=soup.find('span', class_='mw-headline', id='Русский', text='Русский').parent
            work_list=[BeautifulSoup(' '.join([str(t) for t in h1.next_siblings]), 'html.parser')]
        
        for sp in work_list[:1]:
            sp3s=[BeautifulSoup(h, 'html.parser') for h in split_on_tags(sp.find_all('h3'))]
           
            mrf_p=sp3s[0].find_all('p')
            print(get_morfo(mrf_p))
            
            
            #print(sp.text)
            #str_Tesst='Существительное, одушевлённое, женский род, 1-е склонение (тип склонения 3*a по классификации А. А. Зализняка). '
            #pm1=sp.find('p', text=re.compile('Существительное .*'))
            #print(pm1)
            
            #mrf=re.search(r'тип склонения (?P<sklo>.+\b) по классификации А. А. Зализняка', sp.text)
            #print(mrf['sklo'])
        #for h2 in heads:
        #    tbl=h2.find_next('a', text='падеж').parent.parent.parent.parent
        #    h_morf=h2.find_next('h3', text='Морфологические и синтаксические свойства')
            
            #print(tbl)
        #print(parts)
        #print(html_parts[0])
        
                
        
    
    pdfn=pd.read_csv('ru_nouns.csv', sep=';', index_col=0)
    #pdfn.sort_index().to_csv('ru_nouns.csv', sep=';')
    #parse_item(r'https://ru.wiktionary.org/wiki/%D0%BA%D0%B0%D1%80%D1%82%D0%BE%D1%88%D0%B5%D1%87%D0%BA%D0%B0', 'картошечка')
    #parse_item(r'https://ru.wiktionary.org/wiki/%D0%BA%D0%BE%D1%88%D0%BA%D0%B0', 'кошка')
    #parse_item(r'https://ru.wiktionary.org/wiki/%D0%BF%D1%80%D0%B8%D0%B2%D0%BE%D1%80%D0%BE%D1%82', 'приворот')
    parse_item(r'https://ru.wiktionary.org/wiki/%D0%BA%D0%BE%D1%87%D0%B5%D1%82', 'кочет')
    

def main():
    sess=requests.session()
    sess.headers.update(req_header)

    get_nouns_info(sess)
    #print(re.search(r'тип склонения (?P<rrr>.+)  по классификации', 'Существительное, одушевлённое, женский род, 1-е склонение (тип склонения 3*a  по классификации А. А. Зализняка).')['rrr'])



if __name__ == "__main__":
    main()