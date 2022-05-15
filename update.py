# -*- coding: utf-8 -*-
'''
SELECT * FROM Symbol WHERE __key__= KEY('Symbol','PGE')
Created on 01-09-2011

klasy handlerow tutaj zdefiniowanych maja byc wywolywane z CRON-a. 
pobierane sa:
- aktualne notowania wszystkich spolek i zapisuje w Datastore jako Symbol
- dywidendy
- raporty finansowe

@author: plamik
'''
from gdata import service
from google.appengine.api import app_identity
import os
import atom
import gdata
import xlrd

import webapp2 as webapp
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
import urllib2 
import re
import logging

from BeautifulSoup import BeautifulSoup, SoupStrainer
from models import Symbol, Raport, Portfel 
from google.appengine.api import memcache, taskqueue, urlfetch
import cStringIO
import cloudstorage as gcs

import traceback
import codecs
from models import HtmlFragment
#import os
import gc
from datetime import datetime
import urllib
import cookielib
from datetime import date
import csv
from google.appengine.ext.db import StringListProperty
from string import upper
#from google.storage.speckle.proto.client_pb2 import RowSetProto
#from google.appengine.ext.db import StringListProperty

user_agent = 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729)'
headers = { 'User-Agent' : user_agent, 'Cache-Control' : 'max-age=0, must-revalidate' }
nr_kwartalu = {'I':1, 'II':2,'III':3,'IV':4}
Simple_str = 'simple'
Ncav_str = 'ncav'
Ent_str = 'ent'
Generic_str = 'gen'
mom_str = 'mom'

dokladnosc = "%.2f"

mapa_isin_indeksow = {
"WIG": "PL9999999995",  
"WIG30": "PL9999999375",
#"WIG50" : "PL9999999334",
#"WIG250" : "PL9999999326",               
"RESPECT": "PL9999999540",
#"InvestorMS": "PL9999999672",
"WIG-Ukrain": "PL9999999458",
"WIG-BANKI": "PL9999999904",
"WIG-BUDOW": "PL9999999896",
"WIG-CHEMIA": "PL9999999847",
"WIG-DEWEL": "PL9999999706",
"WIG-ENERG": "PL9999999516",
"WIG-INFO": "PL9999999771",
"WIG-MEDIA": "PL9999999755",
"WIG-PALIWA": "PL9999999722",
"WIG-SPOZYW": "PL9999999888",
"WIG-SUROWC": "PL9999999466",
"WIG-TELKOM": "PL9999999870",
"WIGdiv": "PL9999999482",
#"WIG-Plus": "PL9999999441",
"WIG-Poland": "PL9999999599",
"WIG20": "PL9999999987",
"mWIG40": "PL9999999912",
"sWIG80": "PL9999999979"

}

q = {'I' : '1', 'II' : '2', 'III': '3', 'IV':'4', '':''} 
    
def zaladuj_notowania_html_generic(symbole, keys):
    '''
    zaladuj_notowania()
    Pobiera notowania z bazy danych, przechodzi po wynikach i generuje HTML
    
    symbole- slownik obiektow Symbol z ktorych ma byc wygenerowana tabelka HTML
    jako klucz mamy nazwę symbolu (ticker) 
    
    Zwraca:
        String z HTML-em w ktorym jest formularz i tabelka z notowaniami
    '''
    
    buf = cStringIO.StringIO()
    codecinfo = codecs.lookup("utf8")
    html_table_output = codecs.StreamReaderWriter(buf, codecinfo.streamreader, codecinfo.streamwriter)      

    #chcemy uzyskac posortowana liste, wiec sortujemy klucze i robimy z tego liste
    #keys = sorted(symbole)
    
    for k in keys:

        if symbole.has_key(k):
            s = symbole[k]
            if not s: continue
            try:
                if (date.today() - date(int(s.kurs_data[0:4]),int(s.kurs_data[-4:-2]),int(s.kurs_data[-2:])  ) ).days>30: continue
            except:
                pass
        else:
            if k is not None: logging.warn("brakuje w symbole: "+k)
            else: logging.warn("pusty klucz w symbole")
            continue

        html_table_output.write(u'<tr><td align="left">%s<a href="/s/%s">%s</a></td> \
        <td align="left" title="%s">%s</td> \
        <td>%s</td><td title="%s">%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td> %s %s %s <td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % 
          (
           u'<img class="top" src="/icons/warning.ico" alt="'+s.bankrut_opis+u'" title="'+s.bankrut_opis+u'"/>&nbsp;' if s.bankrut else u'',
           s.ticker,s.ticker,   #,\xea\x80\x80abcd\xde\xb4
           s.udzial_w_indeksach_str,
           s.udzial_w_indeksach_str,#idx if len(idx)<16 else idx[0:13]+'&hellip;',                
           s.ostatni_raport_kw if s.ostatni_raport_kw else '-',
                          s.kurs_data,# + ' '+s.kurs_czas if s.kurs_czas!=None else '-', 
           s.kurs_ostatni if s.kurs_ostatni else '',

           s.c_do_z_avg if s.c_do_z_avg is not None else '-',
           s.il_cz_cwk if s.il_cz_cwk else '-',
           s.c_wk_grahama if s.c_wk_grahama != None else '-',
           s.c_do_z  if s.c_do_z is not None else '-',
           s.c_do_wk  if s.c_do_wk is not None else '-',
            
           u'<td title="'+(s.biezaca_dywidenda[2:] if (s.biezaca_dywidenda is not None and len(s.biezaca_dywidenda)>0) else '')+'">'+(s.dyw_stopa if s.dyw_stopa is not None else '')+'</td>' ,
           u'<td >'+ (s.zysk_za_ile_lat if s.zysk_za_ile_lat is not None else '')+'</td>',
           u'<td title="'+s.wzrost_zyskow+'">'  + ('tak' if s.wzrost_zyskow is not None else '' ) +'</td>' if s.wzrost_zyskow is not None else '<td></td>',
           "%.2f" % s.acr_f if s.acr_f is not None and not (s.acr_f != s.acr_f) else '',
           "%.2f" % s.cr_f if s.cr_f is not None and not (s.cr_f != s.cr_f) else '-',                   
           s.dlug_do_kap_obr if s.dlug_do_kap_obr else '', #nieujemne prezentujemy
           s.kw_do_akt if s.kw_do_akt and s.kw_do_akt[0]!='-' else '-',
           s.f_score if s.f_score else ''
           ))

    ret = u''+html_table_output.getvalue()
    buf.close()
    return  ret
  
def zaladuj_notowania_html_ent(symbole, keys):
        '''
        zaladuj_notowania()
        Pobiera notowania z bazy danych, przechodzi po wynikach i generuje HTML
        
        symbole- slownik obiektow Symbol z ktorych ma byc wygenerowana tabelka HTML
        jako klucz mamy nazwę symbolu (ticker) 
        
        Zwraca:
            String z HTML-em w ktorym jest formularz i tabelka z notowaniami
        '''
        
        buf = cStringIO.StringIO()
        codecinfo = codecs.lookup("utf8")
        html_table_output = codecs.StreamReaderWriter(buf, codecinfo.streamreader, codecinfo.streamwriter)      
  
        #chcemy uzyskac posortowana liste, wiec sortujemy klucze i robimy z tego liste
        #keys = sorted(symbole)
        portfel_ent = Portfel(key_name="ent", czy_indeks = False, nazwa_pelna=u'Spółki spełniające kryteria <a href="http://blog.akcjegrahama.pl/2012/05/czy-w-oparciu-o-ksiazke-grahama.html">przedsiębiorczego inwestora</a>')
        
        for k in keys:

            if symbole.has_key(k):
                s = symbole[k]
                if not s: continue
                try:
                    if (date.today() - date(int(s.kurs_data[0:4]),int(s.kurs_data[-4:-2]),int(s.kurs_data[-2:])  ) ).days>30: continue
                except:
                    pass

            else:
                if k is not None:
                    logging.warn("brakuje w symbole: "+k)
                else:
                    logging.warn("pusty klucz w symbole")
                continue
            
            # wstępna redukcja ilości wyników prezentowanych w tabelce            
            try:
                if s.c_do_z is None or float(s.c_do_z)>15.0: 
                    continue 
                if s.c_do_wk is None or float(s.c_do_wk)>2.0:
                    continue

            except Exception, e:
                logging.error(str(e))
                logging.error(s.ticker)
                continue

            #### tutaj robimy odsiewanie pasujących spółek
            if (s.dyw_stopa is not None and \
                s.zysk_za_ile_lat == "+++++" and \
                s.c_do_z is not None and s.c_do_z !="x" and float(s.c_do_z)<=9 and \
                s.c_do_wk is not None and s.c_do_wk !="x" and float(s.c_do_wk)<=1.2 and \
                s.dlug_do_kap_obr is not None  and float(s.dlug_do_kap_obr) <=1.1 and \
                s.cr_f >=1.5 and \
                s.wzrost_zyskow is not None and not s.bankrut ):
                
                #print s.ticker
                portfel_ent.sklad_tickery.append('<a href="http://www.akcjegrahama.pl/s/'+s.ticker+'">'+s.ticker+'</a>')
            ####

            html_table_output.write(u'<tr><td align="left">%s<a href="/s/%s">%s</a></td> \
            <td align="left" title="%s">%s</td> \
            <td>%s</td><td title="%s">%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td> %s %s %s <td>%s</td><td>%s</td><td>%s</td></tr>' % 
              (
               u'<img class="top" src="/icons/warning.ico" alt="'+s.bankrut_opis+u'" title="'+s.bankrut_opis+u'"/>&nbsp;' if s.bankrut else u'',
               s.ticker,  s.ticker, #,\xea\x80\x80abcd\xde\xb4
               s.udzial_w_indeksach_str,
               s.udzial_w_indeksach_str,#idx if len(idx)<16 else idx[0:13]+'&hellip;',                
               s.ostatni_raport_kw if s.ostatni_raport_kw != None else '-',
                              s.kurs_data,# + ' '+s.kurs_czas if s.kurs_czas!=None else '-', 
               s.kurs_ostatni,

               s.c_do_z_avg if s.c_do_z_avg is not None else '-',
            
               s.il_cz_cwk if s.il_cz_cwk != None else '',
               s.c_do_z  if s.c_do_z is not None else '-',
               s.c_do_wk  if s.c_do_wk is not None else '-',
                
               u'<td title="'+(s.biezaca_dywidenda[2:] if (s.biezaca_dywidenda is not None and len(s.biezaca_dywidenda)>0) else '')+'">'+(s.dyw_stopa if s.dyw_stopa is not None else '')+'</td>' ,
               u'<td >'+ (s.zysk_za_ile_lat if s.zysk_za_ile_lat is not None else '')+'</td>',
               u'<td title="'+s.wzrost_zyskow+'">'  + ('tak' if s.wzrost_zyskow is not None else '' ) +'</td>' if s.wzrost_zyskow is not None else '<td></td>',
               "%.2f" % s.cr_f if s.cr_f is not None and not (s.cr_f != s.cr_f) else '',                   
               s.dlug_do_kap_obr if s.dlug_do_kap_obr is not None and s.dlug_do_kap_obr[0] != '-' else '', #nieujemne prezentujemy
               s.f_score if s.f_score != None else ''
               ))

        ret = u''+html_table_output.getvalue()
        buf.close()
        portfel_ent.put()
        return  ret        

def zaladuj_notowania_html_simple(symbole, keys):
        '''
        zaladuj_notowania()
        Pobiera notowania z bazy danych, przechodzi po wynikach i generuje HTML
        
        symbole- slownik obiektow Symbol z ktorych ma byc wygenerowana tabelka HTML
        jako klucz mamy nazwę symbolu (ticker) 
        
        Zwraca:
            String z HTML-em w ktorym jest formularz i tabelka z notowaniami
        '''
        
        buf = cStringIO.StringIO()
        codecinfo = codecs.lookup("utf8")
        html_table_output = codecs.StreamReaderWriter(buf, codecinfo.streamreader, codecinfo.streamwriter) 
  
        #chcemy uzyskac posortowana liste, wiec sortujemy klucze i robimy z tego liste
        #keys = sorted(symbole)
        
        for k in keys:

            if symbole.has_key(k):
                s = symbole[k]
                if s is None: continue
                try:
                    if (date.today() - date(int(s.kurs_data[0:4]),int(s.kurs_data[-4:-2]),int(s.kurs_data[-2:])  ) ).days>30: continue
                except:
                    pass

            else:
                if k is not None:
                    logging.warn("brakuje w symbole: "+k)
                else:
                    logging.warn("pusty klucz w symbole")
                continue
            try:
                if s.c_do_z is None or float(s.c_do_z) > 10.0:
                    continue
            except:
                pass
            if s.kw_do_akt and float(s.kw_do_akt) < 0.5:
                continue

            html_table_output.write(u'<tr><td align="left">%s<a href="/s/%s">%s</a></td> \
            <td align="left" title="%s">%s</td> \
            <td>%s</td><td title="%s">%s</td><td>%s</td><td>%s</td><td>%s</td> %s %s %s <td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % 
              (
               u'<img class="top" src="/icons/warning.ico" alt="'+s.bankrut_opis+u'" title="'+s.bankrut_opis+u'"/>&nbsp;' if s.bankrut else u'',
               s.ticker, s.ticker,  #,\xea\x80\x80abcd\xde\xb4
               s.udzial_w_indeksach_str,
               s.udzial_w_indeksach_str,#idx if len(idx)<16 else idx[0:13]+'&hellip;',                
               s.ostatni_raport_kw if s.ostatni_raport_kw != None else '-',
                              s.kurs_data,# + ' '+s.kurs_czas if s.kurs_czas!=None else '-', 
               s.kurs_ostatni,

               s.c_do_z_avg if s.c_do_z_avg is not None else '-',
            
               
               s.c_do_z  if s.c_do_z is not None else '-',
               s.c_do_wk  if s.c_do_wk is not None else '-',
                
               u'<td title="'+(s.biezaca_dywidenda[2:] if (s.biezaca_dywidenda is not None and len(s.biezaca_dywidenda)>0) else '')+'">'+(s.dyw_stopa if s.dyw_stopa is not None else '')+'</td>' ,
               u'<td >'+ (s.zysk_za_ile_lat if s.zysk_za_ile_lat is not None else '')+'</td>',
               u'<td title="'+s.wzrost_zyskow+'">'  + ('tak' if s.wzrost_zyskow is not None else '' ) +'</td>' if s.wzrost_zyskow is not None else '<td></td>',
               "%.2f" % s.cr_f if s.cr_f is not None and not (s.cr_f != s.cr_f) else '',                   
               s.dlug_do_kap_obr if s.dlug_do_kap_obr is not None and s.dlug_do_kap_obr[0] != '-' else '', #nieujemne prezentujemy
               s.kw_do_akt if s.kw_do_akt != None else '',
               s.f_score if s.f_score != None else ''
               ))

        ret = u''+html_table_output.getvalue()
        buf.close()
        return  ret   

def zaladuj_notowania_html_ncav(symbole, keys):
        '''
        zaladuj_notowania()
        Pobiera notowania z bazy danych, przechodzi po wynikach i generuje HTML
        
        symbole- slownik obiektow Symbol z ktorych ma byc wygenerowana tabelka HTML
        jako klucz mamy nazwę symbolu (ticker) 
        
        Zwraca:
            String z HTML-em w ktorym jest formularz i tabelka z notowaniami
        '''
        
        buf = cStringIO.StringIO()
        codecinfo = codecs.lookup("utf8")
        html_table_output = codecs.StreamReaderWriter(buf, codecinfo.streamreader, codecinfo.streamwriter) 
  
        #chcemy uzyskac posortowana liste, wiec sortujemy klucze i robimy z tego liste
        #keys = sorted(symbole)
        portfel_ncav = Portfel(key_name="ncav", czy_indeks = False, nazwa_pelna=u'Spółki spełniające kryterium <a href="http://blog.akcjegrahama.pl/2012/03/czy-w-oparciu-o-ksiazke-grahama.html">C/WK Grahama</a>')
        
        for k in keys:

            if symbole.has_key(k):
                s = symbole[k]
                if s is None: continue
                try:
                    if (date.today() - date(int(s.kurs_data[0:4]),int(s.kurs_data[-4:-2]),int(s.kurs_data[-2:])  ) ).days>30: continue
                except:
                    pass

            else:
                if k is not None:
                    logging.warn("brakuje w symbole: "+k)
                else:
                    logging.warn("pusty klucz w symbole")
                continue
            if s.c_wk_grahama is None or float(s.c_wk_grahama) > 1.5 or s.sektor == 'kap' or s.sektor == 'ban' or s.sektor == 'fin':
                continue
            
            #### tutaj robimy odsiewanie pasujących spółek
            if ( s.c_wk_grahama is not None and not s.bankrut and float(s.c_wk_grahama)<0.67 and float(s.c_wk_grahama)>0.0):
                portfel_ncav.sklad_tickery.append('<a href="http://www.akcjegrahama.pl/s/'+s.ticker+'">'+s.ticker+'</a>')
            ####
            
            html_table_output.write(u'<tr><td align="left">%s<a href="/s/%s">%s</a></td> \
            <td align="left" title="%s">%s</td> \
            <td>%s</td><td title="%s">%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td> %s %s %s <td>%s</td><td>%s</td><td>%s</td></tr>' % 
              (
               u'<img class="top" src="/icons/warning.ico" alt="'+s.bankrut_opis+u'" title="'+s.bankrut_opis+u'"/>&nbsp;' if s.bankrut else u'',
               s.ticker, s.ticker,  #,\xea\x80\x80abcd\xde\xb4
               s.udzial_w_indeksach_str,
               s.udzial_w_indeksach_str,#idx if len(idx)<16 else idx[0:13]+'&hellip;',                
               s.ostatni_raport_kw if s.ostatni_raport_kw != None else '-',
                              s.kurs_data,# + ' '+s.kurs_czas if s.kurs_czas!=None else '-', 
               s.kurs_ostatni,

               s.c_do_z_avg if s.c_do_z_avg is not None else '-',
            
               s.c_wk_grahama if s.c_wk_grahama != None else '',
               s.c_do_z  if s.c_do_z is not None else '-',
               s.c_do_wk  if s.c_do_wk is not None else '-',
                
               u'<td title="'+(s.biezaca_dywidenda[2:] if (s.biezaca_dywidenda is not None and len(s.biezaca_dywidenda)>0) else '')+'">'+(s.dyw_stopa if s.dyw_stopa is not None else '')+'</td>' ,
               u'<td >'+ (s.zysk_za_ile_lat if s.zysk_za_ile_lat is not None else '')+'</td>',
               u'<td title="'+s.wzrost_zyskow+'">'  + ('tak' if s.wzrost_zyskow is not None else '' ) +'</td>' if s.wzrost_zyskow is not None else '<td></td>',
               "%.2f" % s.cr_f if s.cr_f is not None and not (s.cr_f != s.cr_f) else '',                   
               s.dlug_do_kap_obr if s.dlug_do_kap_obr is not None and s.dlug_do_kap_obr[0] != '-' else '', #nieujemne prezentujemy
               s.kw_do_akt if s.kw_do_akt != None else ''
               ))

        ret = u''+html_table_output.getvalue()
        buf.close()
        portfel_ncav.put()
#        for t in portfel_ncav.sklad_tickery:
#            print t
        return  ret   

def zaladuj_notowania_html_mom(symbole, keys):
        '''
        zaladuj_notowania()
        Pobiera notowania z bazy danych, przechodzi po wynikach i generuje HTML
        
        symbole- slownik obiektow Symbol z ktorych ma byc wygenerowana tabelka HTML
        jako klucz mamy nazwę symbolu (ticker) 
        
        Zwraca:
            String z HTML-em w ktorym jest formularz i tabelka z notowaniami
        '''
        buf = cStringIO.StringIO()
        codecinfo = codecs.lookup("utf8")
        html_table_output = codecs.StreamReaderWriter(buf, codecinfo.streamreader, codecinfo.streamwriter) 
  
        #chcemy uzyskac posortowana liste, wiec sortujemy klucze i robimy z tego liste
        #keys = sorted(symbole)
        #portfel_mom = Portfel(key_name="mom", czy_indeks = False, nazwa_pelna=u'<a>Spółki spełniające kryterium "momentum"</a>')

        bucket_name = os.environ.get('BUCKET_NAME', app_identity.get_default_gcs_bucket_name())
        #self.response.headers['Content-Type'] = 'text/plain'
        #self.response.write('Demo GCS Application running from Version: '
        #              + os.environ['CURRENT_VERSION_ID'] + '\n')
        #self.response.write('Using bucket name: ' + bucket_name + '\n\n')
        #koniunktura_ok = True
        gcs_file = gcs.open('/'+bucket_name+'/wig.csv') 
        koniunktura = gcs_file.read()      
        koniunktura_ok = koniunktura == 'True' 
        gcs_file.close()
   
        bucket = '/'+bucket_name
        filename = bucket + '/stocksontherun.csv'
        '''
        self.response.write('Creating file %s\n' % filename)
    
        write_retry_params = gcs.RetryParams(backoff_factor=1.1)
        gcs_file = gcs.open(filename,
                            'w',
                            content_type='text/plain',
                            options={'x-goog-meta-foo': 'foo',
                                     'x-goog-meta-bar': 'bar'},
                            retry_params=write_retry_params)
        gcs_file.write('abcde\n')
        gcs_file.write('f'*1024*4 + '\n')
        gcs_file.close()
        #self.tmp_filenames_to_clean_up.append(filename)
        self.response.write('\n\n')
        '''
        
        '''
        page_size = 1
        stats = gcs.listbucket(bucket + '/', max_keys=page_size)
        while True:
            count = 0
            for stat in stats:
                #self.response.write('aaa')
                count += 1
                self.response.write(repr(stat))
                self.response.write('\n')
        
            if count != page_size or count == 0:
                break
            stats = gcs.listbucket(bucket + '/', max_keys=page_size,
                                 marker=stat.filename)
   
        '''


        gcs_file = gcs.open(filename)
        
        with gcs_file:
            reader = csv.DictReader(gcs_file, delimiter=',')
            for row in reader:
                try:
                    ticker = row['Ticker']
                    s= symbole[upper(ticker)]
                    s.sma100=float(row['SMA100'])
                    s.zaILE = float (row['ZaIle'])
                    s.rank = float (row['Rank'])
                    #s.Close =
                    s.kurs_nad_sma = s.sma100 < float(row['Close'])

                    html_table_output.write(u'<tr><td align="left">%s<a href="/s/%s">%s</a></td> \
                    <td align="left" title="%s">%s</td> \
                    <td>%s</td><td title="%s">%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td> %s %s <td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % 
                      (
                       u'<img class="top" src="/icons/warning.ico" alt="WIG pod SMA200" title="WIG pod SMA200"/>&nbsp;' if not koniunktura_ok else u'',
                       s.ticker, s.ticker,  #,\xea\x80\x80abcd\xde\xb4
                       s.udzial_w_indeksach_str,
                       s.udzial_w_indeksach_str,#idx if len(idx)<16 else idx[0:13]+'&hellip;',                
                       s.ostatni_raport_kw if s.ostatni_raport_kw != None else '-',
                       row['Date'],# + ' '+s.kurs_czas if s.kurs_czas!=None else '-', 
                       "%.2f" % float(row['Close']),
                       "%.0f" % float(100000.0*0.001/float(row['ATR20'])),
                       "%.0f" % s.zaILE,
                       "%.2f" % s.rank,
                       s.c_do_wk  if s.c_do_wk is not None else '-',
                       u'<td >'+('tak' if (s.kurs_nad_sma) else '-')+'</td>',
                       u'<td >'+ (s.zysk_za_ile_lat if s.zysk_za_ile_lat is not None else '')+'</td>',
                       #u'<td title="'+s.wzrost_zyskow+'">'  + ('tak' if s.wzrost_zyskow is not None else '' ) +'</td>' if s.wzrost_zyskow is not None else '<td></td>',
                       "%.2f" % s.cr_f if s.cr_f is not None and not (s.cr_f != s.cr_f) else '',                   
                       s.dlug_do_kap_obr if s.dlug_do_kap_obr else '', #nieujemne prezentujemy
                       s.kw_do_akt if s.kw_do_akt and s.kw_do_akt[0]!='-' else '',
                       s.f_score if s.f_score else ''
                       ))

                
                except Exception, e:

                    logging.warn("problem z "+ticker)
                    stacktrace = traceback.format_exc()
                    logging.error(e)
                    logging.error('%s', stacktrace)
        #contents = gcs_file.read()
        gcs_file.close()
                
        ret = u''+html_table_output.getvalue()
        buf.close()
        #portfel_mom.put()
#        for t in portfel_ncav.sklad_tickery:
#            print t

        return ret

def pobierz_notowania( jakie=''):
    '''
    pobierz_notowania()
    Pobiera notowania z pamieci podrecznej, a jak nie ma, to pobiera i wstawia je tam
    jakie - przyrostek nazwy klucza w memcache lub datastore
    Zwraca:
        String z HTML-em w ktorym jest tabelka z notowaniami
    '''
    
    notowania = None
    if jakie is None: jakie =''
    klucz = "notowania"+jakie
    
    #return zaladuj_notowania_html_simple(get_symbole_all())
    try:
        
        notowania = memcache.get(klucz) #@UndefinedVariable
        
        if notowania is None:            
            h = HtmlFragment.get_by_key_name(klucz)
            
            if h is None:
                logging.error("nie ma w datastore obiektu HtmlFragment z kluczem "+klucz)
                return ''#zaladuj_notowania_html_ent(get_symbole_all())
            else:
                notowania = h.tresc 
                if not memcache.set(klucz, notowania): #@UndefinedVariable
                    logging.error("Memcache set failed: "+klucz)
    except Exception, e:
        stacktrace = traceback.format_exc()
        logging.error(e)
        logging.error('%s', stacktrace)
    return notowania  

def query_symbole_all():
    '''
    pobiera z datastore liste wszystkich obiektow Symbol
    tworzy na jej podstawie slownik ticker->obiektSYmbol
    '''
    dict_symbole = {}
    for s in Symbol.all():
        dict_symbole[s.ticker] = s
    
    return dict_symbole

def get_symbole_all():
    '''
    zwraca slownik ticker->Symbol - pobiera z memcache a jak tam nie ma to pobiera z datastore'a i zapisuje w memcache
    '''
    #symbole_dict = {}
    #symbole = Symbol.all()
    #for s in symbole:
    #    symbole_dict[s.ticker] = s
    
    keys = [ k.name() for k in Symbol.all(keys_only=True)]
    symbole_dict = memcache.get_multi(keys = keys, key_prefix="symbol_") #@UndefinedVariable
    
    if symbole_dict is not None and len(symbole_dict)>0:
        if len(keys) > len(symbole_dict):  # to znaczy ze ktorychs symboli nie bylo w cache
            
            # tutaj sprawdzamy ktore symbole nie zostaly pobrane z cache - wtedy je pobieramy z datastore
            # usuwamy z listy kluczy te ktore udalo sie pobrać
            for ticker in symbole_dict.keys():
                keys.remove(ticker) # usuwamy ten ticker z kolekcji tickerow do pobrania
                
            symbole_z_ds = {}
            for ticker in keys:
                s = db.get(db.Key.from_path('Symbol', ticker))
                if s: 
                    symbole_z_ds[ticker] = s
                            
            logging.info("w memcache brakowalo " + str(len(symbole_z_ds))+" Symboli.")
            #dopisz z powrotem te brakujące symbole do memcache
            res = memcache.set_multi(symbole_z_ds, key_prefix="symbol_") #@UndefinedVariable
            if len(res)>0:
                logging.warn("nie udalo sie dodac do cache: "+str(res))
            
            # dopisz pobrane z datastore do wynikow ktore zostana zwrocone.
            symbole_dict.update(symbole_z_ds)  
        
        # mamy wsszystkie symbole w symbole_dict
        #return symbole_dict
    
    else:
        symbole_dict = query_symbole_all()
        if symbole_dict is not None:
            # wstaw do cache'a 
            res = memcache.set_multi(symbole_dict, key_prefix="symbol_") #@UndefinedVariable
            if len(res)>0:
                logging.warn("nie udalo sie dodac do cache: "+str(res))
        else:
            logging.warn("query_symbole_all - brak danych")
            return {}
    
    return symbole_dict


def save_symbole(symbole_dict):
    '''
    symbole_dict -> slownik zawierajacy pary: ticker->obiekt Symbol, np. TAURONPE->obiekt Symbol
    '''
    if type(symbole_dict) is not dict:
        raise "symbole_dict musi byc slownikiem"
        return
    if symbole_dict is None:
        logging.warn("otrzymalem pusty slownik")
        return

    db.put(symbole_dict.values())
    
    res = memcache.set_multi(symbole_dict, key_prefix="symbol_") #@UndefinedVariable
    if len(res)>0:
        logging.warn("nie udalo sie dodac do cache: "+str(res))
            
    # aktualizuj takze cache z HTML-em
    #notowania = zaladuj_notowania_html_ent(symbole_dict.values())
    #if not memcache.set("notowania", notowania): #@UndefinedVariable
    #    logging.error("Memcache set failed.")

def updatedywidendy(rok, symbole_dict, page=1):
        
    try:        
        url = 'http://finanse.wp.pl/do,'+str(int(rok))+'-12-31,isin,,mq,,od,'+str(int(rok-1))+'-01-01,page,'+str(int(page))+',sector,,sort,a1,gielda-dywidendy.html'         
        
        req = urllib2.Request(url, headers= headers)
        response = urllib2.urlopen(req)
        tables = SoupStrainer('table', {'class':'tabela'})
        rows = BeautifulSoup(response.read(), parseOnlyThese = tables).findAll('table')[0].findAll('tr')

    except urllib2.HTTPError, e:
        logging.error(str(e))

#    
#spółka     data ustalenia praw     ex-date     dywidenda na akcje     prop./uchw.     data wypłaty     data WZA     stopa dywidendy (%)     łączna kwota #dywidendy (tys. zł)
#PGSSOFT     2013-04-12     2013-04-10     0,18 PLN     p     2013-04-26     2013-04-05     5,71     4 975
#KINOPOL     2013-02-21     2013-02-19     0,50 PLN     u     2013-02-28     2012-12-06     3,29     6 935
    
    # dane są posortowane po drugiej kolumnie (dacie ustalenia praw)  
    visited = {}
    
    try:
        if len(rows) >1:
            for r in rows[1:]:         
                entry = [ str(x).replace('&nbsp;', '').strip() for x in r.findAll('td',text=re.compile(r"[^\n\t]"))]
                #if entry[3] != 'u': # chce zapisywac tylko uchwalone (czyli 'u')
                #    continue                
                
                ticker = entry[0]
                        
                if symbole_dict.has_key(ticker):
                    if visited.has_key(ticker):
                        if visited[ticker][1] == 'u' or (visited[ticker][1] == 'p' and visited[ticker][0]!=entry[1]): 
                            #znaczy że poprzednio odczytał uchwaloną - zlewamy 'p' - proponowane i ze starszych lat.
                            # zapisaliśmy już propnowaną na nowszy rok, więc starszą uchwaloną ignorujemy
                            # TODO:
                            #if teraz_jest_też_'uchwalona" i mamy ten sam dzień ustalenia - przypadek KGHM'2012
                            # czyli wypłata dywidendy w dwóch ratach de facto, ale ten sam dzien ustalenia
                                # wtedy DODAJEMY kwotę do poprzedniej i aktualizujemy SYMBOL o sumę
                            #else teraz 
                            continue
    #                print ticker
                    
                    symbole_dict[ticker].biezaca_dywidenda = '   Ustalenie praw '+entry[1] + \
                        ', ostatnie notowanie z prawem: '+entry[2]+', kwota '+('proponowana ' if entry[4]=='p' else 'uchwalona ')+entry[3]
                    symbole_dict[ticker].dyw_na_akcje = entry[3].split()[0].replace(',','.')
    #                print symbole_dict[ticker].biezaca_dywidenda     
                    visited[ticker] = entry[1], entry[4]
                
            
            
            # rekurencyjnie wywolaj update dywidendy dla kolejnych stron
            #taskqueue.add(url='/update-dywidendy?page='+ str(int(page)+1), method='GET')#print a
            updatedywidendy(rok, symbole_dict, page=page+1)
        else:
            # na tej stronie nie ma już wyników, jest tylko wiersz nagłówka - koniec update'owania dywidend
            logging.info('brak wynikow na: '+url)
            return 
    except Exception, e:
        logging.error(str(e))
    

def calc_fscore(raport):
    fscore= 0
    co_sprawdzam =''
    try:
        #--The return on assets for the last fiscal year is positive. 
        co_sprawdzam = 'ROA>0'
        #print raport.r_roa
        if raport.r_roa[0] != '':
            if float(raport.r_roa[0]) > 0:
                fscore = fscore + 1
        elif float(raport.r_aktywa[0])>0 and float(raport.r_zysk_netto[0])>0:
                fscore = fscore + 1                 
        
        #--Cash from operations for the last fiscal year is positive. 
        co_sprawdzam = 'CF_OP>0'
        if float(raport.r_cf_op[0]) > 0:
            fscore = fscore + 1
        
        #--The return on assets ratio for the last fiscal year is greater than the return on assets ratio for the fiscal year two years ago. 
        co_sprawdzam = 'ROA wzrost'
        if raport.r_roa[0] != '' and raport.r_roa[1]!='': # mamy dane za oba lata            
            if float(raport.r_roa[0]) > float(raport.r_roa[1]):
                fscore = fscore + 1
        elif raport.r_roa[0] != '' and raport.r_roa[1]=='': # strata 2 lata wstecz, ale teraz ROA dodatnie
            fscore = fscore + 1
        #--Cash from operations for the last fiscal year is greater than income after taxes for the last fiscal year. 
        co_sprawdzam = 'CF_OP > zysk netto'
        if float(raport.r_cf_op[0]) > float(raport.r_zysk_netto[0]):
            fscore = fscore + 1
            
        # --The long-term debt-to-assets ratio for the last fiscal year is less than the long-term debt to assets ratio for the fiscal year two years ago. 
        co_sprawdzam = 'zob_dl/akt spadek'
        if float(raport.r_zob_dl[0])/float(raport.r_aktywa[0]) < float(raport.r_zob_dl[1])/float(raport.r_aktywa[1]):
            fscore = fscore +1
        
        #--The average shares outstanding for the last fiscal year is less than or equal to the average number of shares outstanding for the fiscal year two years ago. 
        co_sprawdzam = 'emisja akcji'
        if float(raport.r_n_akcji[0]) <= float(raport.r_n_akcji[1]):
            fscore = fscore +1
        
        #--The gross margin for the last fiscal year is greater than the gross margin for the fiscal year two years ago. 
        co_sprawdzam = 'marza zysku wzrost'
 
        r_m_zysku_brutto_sprzedazy_0 = float( raport.r_zysk_op[0])/float( raport.r_przychody_netto[0])
        r_m_zysku_brutto_sprzedazy_1 = float( raport.r_zysk_op[1])/float( raport.r_przychody_netto[1])
        #print raport.r_m_zysku_brutto_sprzedazy[1]
        #if raport.r_m_zysku_brutto_sprzedazy[0]!='' and  raport.r_m_zysku_brutto_sprzedazy[0]!='':                               
        if (r_m_zysku_brutto_sprzedazy_0 > r_m_zysku_brutto_sprzedazy_1):
            fscore = fscore +1
        #elif raport.r_m_zysku_brutto_sprzedazy[0]!='' and  raport.r_m_zysku_brutto_sprzedazy[0]=='':
        #    fscore = fscore +1
        
        #--The asset turnover for the last fiscal year is greater than the asset turnover for the fiscal year two years ago.
        co_sprawdzam = 'przychody/akt wzrost'
        if float(raport.r_przychody_netto[0])/float(raport.r_aktywa[0]) > float(raport.r_przychody_netto[1])/float(raport.r_aktywa[1]):
            fscore = fscore +1
        
        # na koniec
        
        #--The current ratio for the last fiscal year is greater than the current ratio for the fiscal year two years ago. 
        co_sprawdzam = 'CR wzrost'
        if len(raport.r_cr)>1 and raport.r_cr[0] != '' and raport.r_cr[1] != '':            
            if float(raport.r_cr[0]) > float(raport.r_cr[1]):
                fscore = fscore +1
        else: # to samo ale z wykorzystaniem innych danych
            if (float(raport.kw_kap_pracujacy[0])+ float(raport.kw_zob_kr[0]))/float(raport.kw_zob_kr[0]) > (float(raport.kw_kap_pracujacy[1])+ float(raport.kw_zob_kr[1]))/float(raport.kw_zob_kr[1]):
                fscore = fscore +1  

    except Exception, e:
        fscore = None 
        logging.warn('calc_fscore: '+str(raport.ticker)+': '+ str(e) +' ' +co_sprawdzam)
        
         
    return fscore

def update_symbol_raportem(raport, s):
    
    #---------------------------- zapisanie danych takze w SYMBOL - zeby szybkie byly obliczenia
    if raport is None:
        #logging.warn("brak raportu dla: "+str(s.ticker))
        return
    
    try:        
        #s.zagraniczna = None #s.zagraniczna = True if raport.waluta != 'PLN' else False
        s.waluta = raport.waluta
        roczny = False
        liczba_akcji = s.liczba_akcji/1000000.0
        try:
            
            if len(raport.kw_aktywa_b)>0 and raport.kw_aktywa_b[0] != '':
                s.wk_g_na_akcje = (float(raport.kw_aktywa_b[0]) - float(raport.kw_zob_kr[0])-float(raport.kw_zob_dl[0])) / liczba_akcji
                #print s.wk_g_na_akcje
#                s.wk_g_na_akcje = (float(raport.kw_cr[0]) * float(raport.kw_zob_kr[0])- \
#                                         -float(raport.kw_zob_dl[0])-float(raport.kw_zob_kr[0])) \
#                                        / liczba_akcji
##                print s.wk_g_na_akcje
#            elif len(raport.kw_kap_wlasny)>0 and len(raport.kw_aktywa)>0 and len(raport.kw_kap_pracujacy)>0 and len(raport.kw_zob_kr)>0:
#                s.wk_g_na_akcje = (float(raport.kw_kap_wlasny[0])-(float(raport.kw_aktywa[0]) - (float(raport.kw_kap_pracujacy[0]) + float(raport.kw_zob_kr[0]))))/ liczba_akcji
#                
#            elif len(raport.r_kap_wlasny)>0 and len(raport.r_aktywa)>0 and len(raport.r_kap_pracujacy)>0 and len(raport.r_zob_kr)>0:
#                s.wk_g_na_akcje = (float(raport.r_kap_wlasny [0])-(float(raport.r_aktywa[0]) - (float(raport.r_kap_pracujacy[0]) + float(raport.r_zob_kr[0]))))/ liczba_akcji
#                roczny = True
#            else:
#                s.wk_g_na_akcje = None
        except Exception, e:
            stacktrace = traceback.format_exc()
            logging.error(e)
            logging.error(s.ticker)
            logging.error('%s', stacktrace)
            s.wk_g_na_akcje = None
      
        # accrual ratio
        if len(raport.r_cf_op)>0 and len(raport.r_cf_inw)>0 and len(raport.r_zysk_netto)>0 and len(raport.r_aktywa)>0:
            #if float(raport.r_cf_netto[0])>0 and float(raport.r_zysk_netto[0])>0 and float(raport.r_aktywa[0])>0:           
            s.acr_f = round( ( float(raport.r_zysk_netto[0])*1000.0 - (float(raport.r_cf_op[0])+float(raport.r_cf_inw[0]))  )/(float(raport.r_aktywa[0])*1000.0)*100,1)
            
        # Current ratio    
        try:
            if len(raport.kw_aktywa_b)>0 and raport.kw_aktywa_b[0]!='':
                s.cr_f = round(float(raport.kw_aktywa_b[0])/float(raport.kw_zob_kr[0]),2) # current ratio z ostatniego kwartału
        except:
            logging.info(s.ticker +": problem z kw_aktywa_b / cr_f")

#        elif len(raport.r_cr)>0 and raport.r_cr[0]!='':
#            s.cr_f = float(raport.r_cr[0]) # current ratio z ostatniego kwartału
#            roczny = True
#        else:
#            s.cr_f = None
        
        # Dług/Kap.obrotowy  
        try:
            if len(raport.kw_zob_dl)>0 and len(raport.kw_zob_kr)>0 and len(raport.kw_aktywa_b)>0:
                dlko = (float(raport.kw_zob_dl[0]) / (float(raport.kw_aktywa_b[0])-float(raport.kw_zob_kr[0]) ))
                s.dlug_do_kap_obr = "%.2f" % dlko if dlko>0 else None
        except:
            logging.info(s.ticker+": problem z dlug_do_kap_obr")

#        elif len(raport.r_zob_dl)>0 and len(raport.r_zob_kr)>0 and len(raport.r_aktywa_b)>0:
#            dlko = (float(raport.r_zob_dl[0]) / (float(raport.r_aktywa_b[0])-float(raport.r_zob_kr[0]) ))
#            s.dlug_do_kap_obr = "%.2f" % dlko if dlko>0 else None
#            roczny = True
        
        s.f_score = calc_fscore(raport)

        if len(raport.kw_zysk_netto)>=4:
            s.suma_zyskow_4kw = sum([float(z) for z in raport.kw_zysk_netto[:4]])
        else:
            s.suma_zyskow_4kw = float(raport.r_zysk_netto[0])
            roczny = True
        # suma zyskow za ostatnie 3 lata, ale zyski sprawdzamy za 5 lat
        # sprawdzanie wzrostu zyskow
         
        s.wzrost_zyskow = None
        s.sr_zyski_z_3lat = None
#        if len(raport.r_zysk_netto)> 0: # mamy jakies raporty
#            zyski = [ Decimal(v) for v in raport.r_zysk_netto[:5] ] # za PIEC LAT
        
        s.zysk_za_ile_lat = ''.join(["+" if float(z) > 0 else "-" for z in raport.r_zysk_netto])
            
        if len(raport.r_zysk_netto)> 4 and len(raport.kw_zysk_netto)>4: # podsumujemy zysk za 4 ostatnie kwartały
            z = float(raport.kw_zysk_netto[0])+float(raport.kw_zysk_netto[1])+float(raport.kw_zysk_netto[2])+float(raport.kw_zysk_netto[3])
            if z>float(raport.r_zysk_netto[4]):
                s.wzrost_zyskow = '+'
        elif len(raport.r_zysk_netto)> 4: #liczymy lata
            if float(raport.r_zysk_netto[0]) >float(raport.r_zysk_netto[4]):
                s.wzrost_zyskow = '+'
                          
        # policz jeszcze sredni zysk za 3 lata
        if len(raport.r_zysk_netto)>2:
            s.sr_zyski_z_3lat = sum([float(z) for z in raport.r_zysk_netto [:3]])
        else:
            s.sr_zyski_z_3lat = None
        
        # kw/akt
        if len(raport.kw_kap_wlasny)>0 and len(raport.kw_aktywa)>0:
            s.kw_do_akt = "%.2f" % (float(raport.kw_kap_wlasny[0]) / float(raport.kw_aktywa[0]))
        elif len(raport.r_kap_wlasny)>0 and len(raport.r_aktywa)>0:
            s.kw_do_akt = "%.2f" % (float(raport.r_kap_wlasny[0]) / float(raport.r_aktywa[0]))
            roczny = True
                
        #rap = raport.kw_data_konca[0] if len(raport.kw_data_konca)>0 else None
#        if rap is not None:
#           s.ostatni_raport_kw = 'Q'+q[rap[0]] + "'"+rap[1]
#       else:
#           s.ostatni_raport_kw = None
            
        if roczny:
            s.ostatni_raport_kw = raport.r_data_konca[0]
        else:
            s.ostatni_raport_kw = raport.kw_data_konca[0]

        s.ostatni_raport_r =  raport.r_data_konca[0] if len(raport.r_data_konca)>0 else None


    except Exception, e:
        stacktrace = traceback.format_exc()
        logging.error(e)
        logging.error(s.ticker)
        logging.error('%s', stacktrace)
    
    save_symbol(s)
    
def pobierz_raport_money(isin, prefix, t, o, raport):
    '''
    # p = period np. Y / Q
    # t= type   np. f=jednostkowe / t=skonsolidowane
    # o= offset np.4
    '''
    p='Y' if prefix == "r_" else 'Q'  
    url = "http://www.money.pl/ajax/gielda/finanse/"
    res = urlfetch.fetch(url=url, method = urlfetch.POST,deadline=60 , 
                         headers= headers,payload='isin='+isin+'&p='+p+'&t='+t+'&o='+o )
    logging.info("pobieram raport " +t+" dla "+raport.ticker+ " z url: "+url)
    soup =BeautifulSoup(res.content) 
    
    #tab_opis = soup.findAll('')
    tabelki = soup.findAll('table')
    if len(tabelki)<1:
        logging.warn("brak tabelki money.pl dla "+raport.ticker)
        return 
    
    tab = tabelki[0]
    
    rows = tab.findAll('tr')
    i=0
    for r in rows: #[rows[5],rows[6],rows[7],rows[14]]:
        entry = [ (x.string or '').strip().replace(",",".").replace(" ","") for x in r.findAll(['td', 'th'])]
        if   i==0:
            # data: 2014-12-31
            setattr(raport , prefix+"data_konca"  , entry)

        elif   i==1:
            #Przychody netto ze sprzedaży produktów, towarów i materiałów
            setattr(raport , prefix+"przychody_netto"  , [ unicode("%.2f" % (float(x)/1000.0)) if x!='-' else '' for x in entry])
        elif i==2:
            #Zysk (strata) z działalności operacyjnej
            setattr(raport , prefix+"zysk_op"  , [ unicode("%.2f" % (float(x)/1000.0)) if x!='-' else '' for x in entry])
        elif i==3:
            #Zysk (strata) brutto
            setattr(raport , prefix+"zysk_brutto"  , [ unicode("%.2f" % (float(x)/1000.0)) if x!='-' else '' for x in entry])
        elif i==4:
            #Zysk (strata) netto *
            setattr(raport , prefix+"zysk_netto"  , [ unicode("%.2f" % (float(x)/1000.0)) if x!='-' else '' for x in entry])
        elif i==6:
            #print "Przepływy netto z działalności operacyjnej "+ str(entry)
            setattr(raport , prefix+"cf_op"  , entry )
        elif i==7:
            #print "Przepływy netto z działalności inwestycyjnej "+ str(entry)
            setattr(raport , prefix+"cf_inw"  , entry )
        elif i==8:
            #print "Przepływy netto z działalności finansowej "+ str(entry)
            setattr(raport , prefix+"cf_fin"  , entry )
        elif i==9:
            #Aktywa razem
            setattr(raport , prefix+"aktywa"  , [ unicode("%.2f" % (float(x)/1000.0)) if x!='-' else '' for x in entry])
        elif i==11:
            #
            setattr(raport , prefix+"zob_dl"  , [ unicode("%.2f" % (float(x)/1000.0)) if x!='-' else '' for x in entry])
        elif i==12:
            #
            setattr(raport , prefix+"zob_kr"  , [ unicode("%.2f" % (float(x)/1000.0)) if x!='-' else '' for x in entry])
        elif i==13:
            #
            setattr(raport , prefix+"kap_wlasny"  , [ unicode("%.2f" % (float(x)/1000.0)) if x!='-' else '' for x in entry])

        elif i==15:
            #print "Liczba akcji (tys. szt.) "+ str(entry)
            setattr(raport , prefix+"n_akcji"  , entry )
        
        i=i+1
            
def pobierz_raport_MSN(raport, url,prefix):
    
    logging.info("pobieram raport z url: "+url)
    response = urlfetch.fetch(url, method=urlfetch.GET, deadline=60 , headers= headers)
    #ucontent = unicode(response.content, 'utf8')
    
    soup = BeautifulSoup(response.content)

    # tutaj pobieram lata / kwartały
    divs = soup.findAll('div', attrs={ 'class':'table-rows'})
    if len(divs)<1: 
        logging.info("dla spolki "+raport.ticker +" brak raportu MSN")
        return 
    nagl = divs[0].findNext('ul')
    entry = [ x.div.p.string for x in nagl.findAll('li') ] 
     
    if Raport.nazwa_atr.has_key(entry[0]):
        atr = prefix + Raport.nazwa_atr[entry[0]]
        setattr(raport ,atr  , [str(x) for x in list(reversed(entry[1:] ))]) #odetnij nazwe naglowka 

    # tutaj pobieram już konkretne wskaźniki wraz z wartościami w powyżej określonych okresach    
    table_rows = soup.findAll('div', attrs={ 'class':'table-data-rows'})
    for r in table_rows[0].findAll('ul', attrs={ 'class':'level0'}):
        entry = [ x.p.string.replace(",",".").replace("&#160;","") if x.p else '' for x in r.findAll('li') ] 
        #print entry
        if Raport.nazwa_atr.has_key(entry[0]):
            atr = prefix + Raport.nazwa_atr[entry[0]]
            setattr(raport ,atr  , list(reversed(entry[1:])) ) #odetnij nazwe naglowka

 
def pobierz_raporty(ticker, skrot, isin, raport_typ):
    
    try:        
        #logging.info("pobieram raport z url: "+url)
        raport = Raport(key_name=ticker, ticker = ticker)
        if raport_typ =="H":
            pobierz_raport_money(isin, 'r_', 't', '0', raport)
            pobierz_raport_money(isin, 'kw_', 't', '0', raport)
        else:
            pobierz_raport_money(isin, 'r_', 'f', '0', raport)
            pobierz_raport_money(isin, 'kw_', 'f', '0', raport)
        
        if skrot is None or skrot =='':
            logging.warn('pusty skrot dla '+ticker)
            return
            
        msn_urlcore = 'http://www.msn.com/pl-pl/finanse/notowania-akcji/finanse/'
        
        # https://www.msn.com/pl-pl/finanse/notowania-akcji/finanse/fi-42.1.PGN.WAR
        
        msn_urls_kw = [msn_urlcore+'balance_sheet/Quarterly/fi-42.1.'+skrot+'.WAR?ver=2.0.5617.39813',
                msn_urlcore+'income_statement/Quarterly/fi-42.1.'+skrot+'.WAR?ver=2.0.5617.39813']           
                #urlcore+'cash_flow/Quarterly/fi-42.1.'+skrot+'.WAR?ver=2.0.5617.39813',
        
        msn_urls_r = [msn_urlcore+'income_statement/Annual/fi-42.1.'+skrot+'.WAR?ver=2.0.5617.39813',
                  msn_urlcore+'balance_sheet/Annual/fi-42.1.'+skrot+'.WAR?ver=2.0.5617.39813']        
                #   ,urlcore+'cash_flow/Annual/fi-42.1.'+skrot+'.WAR?ver=2.0.5617.39813',
           
        for url in msn_urls_r:
            pobierz_raport_MSN(raport, url, 'r_')          
            
        for url in msn_urls_kw:
            pobierz_raport_MSN(raport, url, 'kw_')
    
        #s.dlug_do_kap_obr = "%.2f" % dlko if dlko>0 else None
        
        # obliczanie ROA
        try:  
            for i in range(0,len(raport.r_zysk_netto)):      
                raport.r_roa.append(  "%.2f" % (float(raport.r_zysk_netto[i]) / float(raport.r_aktywa[i])))
        except:
            logging.info(ticker+": problem z r_zysk_netto")
    
        # oNonebliczanie Current Ratio  
        try:
            for i in range(0,len(raport.kw_aktywa_b)):      
                raport.kw_cr.append(  "%.2f" % (float(raport.kw_aktywa_b[i]) / float(raport.kw_zob_kr[i])))
        except:
            logging.info(ticker+": problem z kw_aktywa_b")
        
        try:    
            for i in range(0,len(raport.r_aktywa_b)):      
                raport.r_cr.append(  "%.2f" % (float(raport.r_aktywa_b[i]) / float(raport.r_zob_kr[i])))
        except:
            logging.info(ticker+": problem z r_aktywa_b")
        ### TODO: tutaj musi być pobranie raportu z MONEY.PL
        # w zakresie: cashflow-y różne, oraz liczba akcji (w poszczególnych latach
        raport.put()
        update_symbol_raportem(raport, get_symbol(ticker))
 
    except urllib2.HTTPError, e:
        logging.error(str(e))        
        return
    
    return
    
def query_raport(ticker):
    key = db.Key.from_path('Raport', ticker)
    r = db.get(key)
    if not r:
        return None
    return r

def get_raport(ticker):
    '''
    zwraca z memcache jeden obiekt Raport o kluczu podanym w tickerz-e
    albo pobiera z datastore'a
    '''    
    if not ticker:
        return None   
    
    r = memcache.get("raport_"+ticker) #@UndefinedVariable
    
    if r is not None:
        return r
    else:
        r = query_raport(ticker)
        if r is not None:
            # wstaw skrot do cache'a na 5 minut
            if not memcache.add("raport_"+ticker, r): #@UndefinedVariable
                logging.error("Memcache set failed: Raport dla "+ticker)            
        else:
        #    r = Raport(key_name=ticker,ticker=ticker)
            return None
        return r

def save_symbol(symbol):
    if type(symbol) is not Symbol:
        
        raise Exception( "oczekiwano obiektu typu Symbol, otrzymano: "+str(type(symbol)))
    if symbol is None:
        return
    
    symbol.put()
    
    if not memcache.set("symbol_"+symbol.key().name(), symbol): #@UndefinedVariable
        logging.error("Memcache set failed: symbol "+symbol.ticker)

def query_symbol(ticker=None):
    key = db.Key.from_path('Symbol', ticker)
    s = db.get(key)
    if not s:
        return None
    return s

def get_symbol(ticker=None):
    ''' 
    pobiera obiekt z bazy albo tworzy - nie uzywa memcache.
    '''
    
    if not ticker:
        return None   
    
    
    symbol = None #memcache.get("symbol_"+ticker)
    if symbol is not None:
        return symbol
    else:
        symbol = query_symbol(ticker)
        if symbol is not None:
            # wstaw skrot do cache'a na 5 minut
            if not memcache.set("symbol_"+symbol.key().name(), symbol): #@UndefinedVariable
                logging.error("Memcache set failed: "+symbol.ticker)
            pass            
        else:
            symbol = Symbol(key_name=ticker,ticker=ticker)
        return symbol   

def policz_wskazniki(s, kursy_walut):
    '''
    s - obiekt typu Symbol
    kursy_walut- słownik z wartościami 'HUF' -> float 0.22, 'EUR'-> float("4.34")
    '''    
    if s is None: return

    cena_f = float(s.kurs_ostatni)
    x = 1.0
    if s.waluta != 'PLN' and s.waluta != None:
        if not kursy_walut.has_key(s.waluta): 
            logging.warn('Waluty '+s.waluta+' nie ma w tabeli kursow dla: '+str(s.ticker))
            return
        x = kursy_walut[s.waluta]
        if x is None: # znaczy że NaN 
            logging.error('Waluta '+s.waluta+' nie ma ustawionego kursu')
            return
       
    try:
        if s.sr_zyski_z_3lat and s.liczba_akcji and s.sr_zyski_z_3lat > 0.0:
            s.c_do_z_avg = dokladnosc % (cena_f*s.liczba_akcji*3.0/ (x*1000000.0*s.sr_zyski_z_3lat))
        else:
            s.c_do_z_avg = None    
    except Exception, e:
        stacktrace = traceback.format_exc()
        #logging.warn(e)
        logging.warn(s.ticker)
        logging.warn('%s', stacktrace) 
        s.c_do_z_avg = None
        
    try:
        if s.c_do_wk and s.c_do_z:
            s.il_cz_cwk =  dokladnosc % (float(s.c_do_wk)*float(s.c_do_z))
        else:
            s.il_cz_cwk = None   
    except Exception, e:
        stacktrace = traceback.format_exc()
        #logging.warn(e)
        #logging.warn(s.ticker)
        #logging.warn('%s', stacktrace)
        s.il_cz_cwk = None
    
    try:
        if s.dyw_na_akcje and s.dyw_na_akcje != '':
            s.dyw_stopa = dokladnosc % (100.00*(float(s.dyw_na_akcje)/cena_f))
        else: 
            s.dyw_stopa = None
    except Exception, e:
        stacktrace = traceback.format_exc()
        logging.warn(e)
        logging.warn(s.ticker)
        logging.warn('%s', stacktrace)
        s.dyw_stopa = None
        
    try:
        if s.wk_g_na_akcje > 0.0:
            s.c_wk_grahama =  dokladnosc % (cena_f / (x*s.wk_g_na_akcje)) 
        else: 
            s.c_wk_grahama = None
    except Exception, e:
        stacktrace = traceback.format_exc()
        #logging.warn(e)
        logging.warn(s.ticker)
        logging.warn('%s', stacktrace)
        s.c_wk_grahama = None
        

def update_skrocone_nazwy(symbole_dict):
    urls = ['http://www.gpwinfostrefa.pl/GPWIS2/pl/emitents/marketlist/MAIN/',
            'http://www.gpwinfostrefa.pl/GPWIS2/pl/emitents/marketlist/PARALLEL/',
            'http://www.gpwinfostrefa.pl/GPWIS2/pl/emitents/marketlist/SNP/'
            ]
    
    for url in urls:
        response = urlfetch.fetch(url, method=urlfetch.GET, deadline=60 , headers= headers)
        soup = BeautifulSoup(response.content).findAll('table', attrs={'id':'emitentsList'})
        
        #print url
        for r in soup[0].findAll('tr')[1:]:
            cells = r.findAll('td')
            ticker = cells[2].string.replace("&nbsp;",'').strip()
            if symbole_dict.has_key(ticker):
                raport = symbole_dict[ticker]
                raport.skrot =cells[3].string.replace("&nbsp;",'').strip() 
    #### TODO: lista alertów ###
    # http://www.gpwinfostrefa.pl/GPWIS2/pl/emitents/marketlist/ALERTS/ - wystarczy przeiterować.                

def update_ISIN():
    symbole_dict = get_symbole_all()
    # tu by trzeba wyczyścić wszystkie sybmole, bo robimy aktualizację.
    update_wskazniki_z_gpw(symbole_dict)
    update_skrocone_nazwy(symbole_dict)
    save_symbole(symbole_dict)
        
def wyodrebnij_wskazniki_z_gpw(symbole_dict, ucontent, tables, isin_ticker_map):
    tab = BeautifulSoup(ucontent, parseOnlyThese = tables).findAll('table') #, attrs={ 'class':'tabela big'}
    rows = tab[0].findAll('tr')

#  Lp, Kod, Nazwa, Sektor, Liczba akcji, wartość rynkowa, wart.księgoewa, raport fin data, raport fin typ, c/wk, c/z, stopa dyw
    for r in rows[1:]:
        #print r
        entry = [ str(x.text.encode("utf-8")).replace('&nbsp;', '') for x in r.findAll('td')]

        
        ticker = entry[2] 
        if symbole_dict.has_key(ticker):
            s = symbole_dict[ticker]
        else:
            logging.warn("w symbole_dict brakowalo: "+ticker+" - dodalem")
            s = Symbol(key_name=ticker, ticker=ticker)
            symbole_dict[ticker] = s
        #s.segment = entry[2] # M/S/B/BA/SA/L
        #s.sektor = entry[3]
        s.isin = entry[1]
        isin_ticker_map[s.isin] = ticker
        s.bankrut = False
        s.bankrut_opis = None
        s.raport_typ = entry[8]
        s.zagraniczna = False if s.isin[0:2] == 'PL' else True 
        s.liczba_akcji = float(entry[4])
        s.c_do_wk = entry[9].replace(',','.') if not str(entry[8]).startswith('-') else None  
        s.c_do_z = entry[10].replace(',','.') if  str(entry[9]) != 'x' else None
        #print ticker
        #print s.c_do_wk
        #print s.c_do_z

            
        
def update_wskazniki_z_gpw(symbole_dict):
    '''
    pobiera ze strony GPW kody ISIN dla spółek, te kody są potrzebne do konstruowania URL-a do pobierania 
    raportów ze strony GIELDA.WP.PL.
    Przy okazji pobieramy informacje o sektorze i segmencie spółki oraz czy spółka jest zagraniczna. 
    
    # krajowe_czy_zagraniczne : id tabelki HTML to footable_Z albo footable_K 
    
    '''
    isin_ticker_map = {}
    
    # posortowane od najniższego C/Z
    #url =r"http://www.gpw.pl/wskazniki_spolek?ph_tresc_glowna_order=gws_cz&ph_tresc_glowna_order_type=ASC"
    #'url =r"http://www.gpw.pl/wskazniki_spolek_full?ph_tresc_glowna_order=gws_cz&ph_tresc_glowna_order_type=ASC"
    url = r"http://www.gpw.pl/wskazniki"
    try:     
        req = urllib2.Request(url, headers= headers)
        response = urllib2.urlopen(req)
        
        content = response.read()
        encoding = response.headers['content-type'].split('charset=')[-1]
        #print encoding
        ucontent = unicode(content, encoding)
        # //*[@id="footable_K"]
        tables = SoupStrainer('table',attrs={ 'id':'footable_K'})
        tables2 = SoupStrainer('table',attrs={ 'id':'footable_Z'})
        
        wyodrebnij_wskazniki_z_gpw(symbole_dict, ucontent, tables, isin_ticker_map)
        wyodrebnij_wskazniki_z_gpw(symbole_dict, ucontent, tables2, isin_ticker_map)
         

    except urllib2.HTTPError, e:
        logging.error("Blad przy aktualizacji isin i wskaznikow.")
        logging.error(str(e))  
        return    
    ########################   a teraz poszukujemy spółek które są w upadłości #######
    # http://www.gpw.pl/lista_spolek?search=1&query=upad%C5%82o%C5%9Bci&country=&voivodship=&sector=&x=33&y=10
    '''
    # ścieżka xpath
    # /html/body/div[3]/div[3]/div[2]/div/div[2]/div/table
    url =r"http://www.gpw.pl/lista_spolek?search=1&query=upad%C5%82o%C5%9Bci&country=&voivodship=&sector=&x=33&y=10"
    try:     
        #response = urlfetch.fetch(url, method=urlfetch.GET, deadline=60 , headers= headers)
        req = urllib2.Request(url, headers= headers)
        response = urllib2.urlopen(req)
        
        content = response.read()
        encoding = response.headers['content-type'].split('charset=')[-1]
        #print encoding
        ucontent = unicode(content, encoding)
        
        tables = SoupStrainer('table',attrs={ 'class':'tab02'})
        
        tab = BeautifulSoup(ucontent, parseOnlyThese = tables).findAll('table') #, attrs={ 'class':'tabela big'}
        #print tab
        rows = tab[0].findAll('tr')
    
        #pierwszy wiersz pomijamy
        for r in rows[1:]:                
            a = r.findAll('a',href=True)[1]
            isin = a['href'][31:-1]
            if not isin_ticker_map.has_key(isin):
                logging.warn("w isin_ticker_map brakowalo "+isin)  
                continue
            ticker = isin_ticker_map[isin]
            symbole_dict[ticker].bankrut = True
            # TODO: naprawic problem z generowanie tabelki z notowaniami, ze nie akceptuje unikodu!!
            if a.text.endswith(u'W UPADŁOŚCI LIKWIDACYJNEJ'):
                symbole_dict[ticker].bankrut_opis = 'w upadlosci likwidacyjnej'#u'Spółka w upadłości likwidacyjnej'
            elif a.text.endswith(u'W UPADŁOŚCI UKŁADOWEJ'):  
                symbole_dict[ticker].bankrut_opis = 'w upadlosci ukladowej'#u'Spółka w upadłości układowej'
            else:
                symbole_dict[ticker].bankrut_opis = 'w upadlosci'#u'Spółka w updałości'

    except urllib2.HTTPError, e:
        logging.error("Blad przy aktualizacji info o bankrutach.")
        logging.error(str(e))  
        return
    '''
    # --------------- 2014-04-13 ---------- pobieranie 'wlid' dla spolek z interii, zeby moc potem pobierac wg tego wlid raporty z interii    
#    for i in range(1,10):
#        url = "http://mojeinwestycje.interia.pl/gie/notgpw/full?rodzaj=walory&typ=CI&czas_odsw=15&Submit=1&rodzaj_waloru=3&reks=15&lp="+str(i)
#        response = urlfetch.fetch(url=url, method=urlfetch.GET, deadline=60 , headers= headers)
#        
#        tabs = BeautifulSoup(response.content).findAll('table') #, parseOnlyThese = tables
#        
#        rows = tabs[15].findAll('tr')
#        for r in rows:
#            entry = [ (x['href'], x.text) for x in r.findAll(['a'],href=True)]
#            if len(entry)>0:       
#                wlid =  entry[1][0].split("wlid=")[1].split("&")[0] # wlid
#                ticker =  entry[1][1].split("&")[0] # ticker
#                if symbole_dict.has_key(ticker):
#                    symbole_dict[ticker].wlid = wlid
#                else:
#                    logging.info(ticker+" nie znaleziono w symbole_dict")    
    
    return symbole_dict  

def pobierz_kursy_walut():
    kursy_dict = {}

    url = 'http://bossa.pl/pub/waluty/mstock/sesjanbp/sesjanbp.prn'
    try:     
        req = urllib2.Request(url, headers= headers)
        response = urllib2.urlopen(req)
        r = response.read()
        for w in r.split('\n'):
            entry = w.split(',')
            if len(entry)< 3: #zazwyczaj ostatnia linijka to jeden wpis '\n'
                continue 
            kursy_dict[entry[0]] = float(entry[2]) if entry[0] != 'HUF' else (float(entry[2])/100.00)
    
    except Exception, e:
        stacktrace = traceback.format_exc()
        logging.error(e)
        logging.error(entry)
        logging.error('%s', stacktrace)
        
    return kursy_dict

def updatequotes():
    url = r"http://bossa.pl/pub/metastock/mstock/sesjaall/sesjaall.prn"

    try:     
        req = urllib2.Request(url, headers= headers)
        response = urllib2.urlopen(req)
        n = response.read()
        
    except urllib2.HTTPError, e:
        logging.error("Blad przy aktualizacji notowan.")
        logging.error(str(e))  
        return
    # aktualizacja linkow do danych finansowych
    #raporty = get_raporty()
    
    # takie podejscie rozwiazuje problem znikajacych notowan typu BORYSZEW-PDA - po prostu od nowa tworzymy, a potem na podstawie tej kolekcji tworzymy HTML-a
    try:        
        symbole_dict = get_symbole_all()
        symbole_dict = update_wskazniki_z_gpw(symbole_dict)
        tab_kursow = pobierz_kursy_walut()
        
        for r in n.split('\n'):
            entry = r.split(',')
            
            #['06MAGNA', '20120127', '0.43', '0.43', '0.41', '0.42', '483894\r']
            ticker = entry[0]
            if ticker == '': continue
            
            # FIXME: rozwiazac problem znikajacych notowan typu BORYSZEW-PDA        
            if symbole_dict.has_key(ticker):
                s = symbole_dict[ticker]
                try:
                    if (s.isin is None): #or (s.ostatni_raport_kw and int(s.ostatni_raport_kw[-2:])+1 < datetime.now().year-2000): # za stary raport
                        symbole_dict.pop(ticker)# nie przetwarzamy ...
                        continue # pomijamy wszystkie opcje, kontrakty, notowania z NC itp        
                except Exception, e:
                    logging.error(str(e))
                    logging.error(s.ticker)
            else: # nie mamy tego symbolu w bazie, ale to nic, bo ma go dodawac updateisin.                
                #logging.warn("w symbole_dict brakowalo: "+ticker+" - NIE dodalem - ma to dodac updateisin")
                continue

            s.kurs_ostatni= entry[5].replace(",",".")        # aktualny kurs
            #s.wolumen     = entry[6].replace('\r','')
            s.kurs_data   = entry[1]
            
            policz_wskazniki(s,tab_kursow)
                
        save_symbole(symbole_dict)      
        
        gc.collect()
        # wygeneruj i zapisz HTML do bazy
        # to jako task
        
        keys = sorted(symbole_dict)
        
        h = HtmlFragment(key_name = "notowania"+Generic_str)#h = HtmlFragment(key_name = "notowania"+str(os.environ['CURRENT_VERSION_ID']).split('.')[0]+Generic_str)
        h.tresc = zaladuj_notowania_html_generic( symbole_dict, keys ) # przekazujemy slownik
        gc.collect()
        h.put()
        # po zapisaniu w bazie - skasuj to co jest w memcache
        memcache.delete("notowania"+Generic_str) #@UndefinedVariable
 
        
        h = HtmlFragment(key_name = "notowania"+Ent_str)
        h.tresc = zaladuj_notowania_html_ent( symbole_dict, keys ) # przekazujemy slownik
        gc.collect()
        h.put()
        # po zapisaniu w bazie - skasuj to co jest w memcache
        memcache.delete("notowania"+Ent_str) #@UndefinedVariable
        
        # i jeszcze zapisujemy tabelke simple:
        try:
            h2 = HtmlFragment(key_name = "notowania"+Simple_str)
            h2.tresc = zaladuj_notowania_html_simple( symbole_dict, keys ) # przekazujemy slownik
            gc.collect()
            h2.put()
            # po zapisaniu w bazie - skasuj to co jest w memcache
            memcache.delete("notowania"+Simple_str) #@UndefinedVariable
        except Exception,e:
            stacktrace = traceback.format_exc()
            logging.error(e)
            logging.error('%s', stacktrace)

        # i jeszcze zapisujemy tabelke simple:
        h2 = HtmlFragment(key_name = "notowania"+Ncav_str)
        h2.tresc = zaladuj_notowania_html_ncav( symbole_dict, keys ) # przekazujemy slownik
        gc.collect()
        h2.put()
        # po zapisaniu w bazie - skasuj to co jest w memcache
        memcache.delete("notowania"+Ncav_str) #@UndefinedVariable
        
                # i jeszcze zapisujemy tabelke momentum:
        h2 = HtmlFragment(key_name = "notowania"+mom_str)
        h2.tresc = zaladuj_notowania_html_mom( symbole_dict, keys ) # przekazujemy slownik
        gc.collect()
        h2.put()
        # po zapisaniu w bazie - skasuj to co jest w memcache
        memcache.delete("notowania"+mom_str) #@UndefinedVariable
        
        # FIXME: laduj obiekty Symbol albo obiekt notowania z dwoma listami (tickers, vals) w oparciu o te dane
    except Exception, e:
        stacktrace = traceback.format_exc()
        logging.error(e)
        logging.error('%s', stacktrace) 
        
'''
def updateraporty(url_page, raporty):
    ### url_page musi być liczbą naturalną 1,2,3....
    url = r"http://gielda.wp.pl/page,"+str(url_page)+",sort,91,type,netto,spolki_wyniki_finansowe.html"
    print url
    #przejsc po kazdej stronie, sprawdzic czy dany raport mamy juz zaladowany. jak nie - dodac do kolejki
    symbole = get_symbole_all()
    try:        
        response = urlfetch.fetch(url, method=urlfetch.GET, deadline=60 , headers= headers)
        tables = SoupStrainer('div',attrs={ 'class':'rapKwaJ'})
        tab = BeautifulSoup(response.content, parseOnlyThese = tables).findAll('div')
        r = tab[0].div.div.table.findAll('td')#, attrs={'class':'name'})
    except urllib2.HTTPError, e:
        logging.error("Blad przy aktualizacji raportow.")
        logging.error(str(e))  
    
    try:
#        #jeżeli data pierwszego raportu na liście jest większa niż (dzisiaj - tydzień) 
#        # wtedy -> wczytaj raporty z tej strony a potem przewiń stronę i znowu: jeżeli etc...
#        data = datetime.strptime(r[0].text, "%d.%m.%Y")  # na przykład "14.12.2012"
#        #data = datetime.strptime('1.3.2012', "%d.%m.%Y") 
#        if (data - (datetime.today()-timedelta(days=30))).days < 0: # data pierwszego raportu na liscie jest starsza niz tydzien temu, nie wczytujemy, bo zakladam ze juz to tydzien temu wczytalem.
#            logging.info("raport z "+r[0].text+", url "+ url+" - juz nie ladujemy")
#            return
        
        #print raporty
        #print "############"
        r = tab[0].div.div.table.findAll('td', attrs={'class':'name'})
        for d in r:
            a= d.findAll("a", href=True)[1]
            if symbole.has_key(a.text) and a.text in raporty: 
                #http://finanse.wp.pl/isin,PLMSTZB00018,notowania-raporty.html
                taskqueue.add(url='/update-raporty-task', params={'ticker': a.text, 'url' : 'http://gielda.wp.pl'+a['href'], 'raport_typ' : symbole[a.text].raport_typ })#print a
                #raporty.remove(a.text)
            else:
                logging.warn("brakowalo symbolu "+a.text+ " podczas proby aktualizacji raportu")
        
        # !!!!! - wywołujemy ładowanie raportów dla następnej strony
        
        # --- 2012-08-25 - wyłączam to,trzeba napisać lepszy mechanizm 
        #updateraporty(str(int(url_page)+1))
        #print "tralala"
        ## !!!!!
        
    except Exception, e:
        stacktrace = traceback.format_exc()
        logging.error(e)
        logging.error('%s', stacktrace)
'''

'''
class UpdateRaportyRecent(webapp.RequestHandler):
    def get(self):     
        p = self.request.get('p') 
        kw = self.request.get('kw')
        
        if p is None: p = "0" 
        
        raporty = Raport.all()
        raporty_do_update = []
        for r in raporty:
            if len(r.kw_data_konca)>0 and r.kw_data_konca[0] != kw:
                raporty_do_update.append(r.ticker)
        #print raporty_do_update
    
        try:
            if int(p)<0 or int(p)>24: 
                logging.error("parametr p mniejszy od 0 lub wiekszy od 24")
                return
            updateraporty(int(p),raporty_do_update)
            taskqueue.add(url='/update-raporty-recent', method='GET', params={'p': str(min(int(p)+1,25)), 'kw' : kw })#print a

        except Exception, e:
            stacktrace = traceback.format_exc()
            logging.error(e)
            logging.error('%s', stacktrace)
'''
           
class UpdateRaporty(webapp.RequestHandler):
    '''
    UpdateRaporty(webapp.RequestHandler):
    uruchamiany ma byc przez CRON-a
    kolejkuje zadania - Taski - dla kazdego ticker - zeby zaladowane zostaly wskazniki finansowe
    aktualizowane sa c/z, c/wk i 3-letnie c/z
    '''
    def get(self):        
        symbole = Symbol.all().fetch(2000)

        for s in symbole:
            taskqueue.add(url='/update-raporty-task', 
                          params={'ticker': s.ticker, 'skrot' : s.skrot, 'isin': s.isin,
                                  'raport_typ' : s.raport_typ })

class UpdateRaportyTask(webapp.RequestHandler):
    def post(self):
        
        ticker = self.request.get('ticker')
        skrot = self.request.get('skrot') # na przykład PGN albo AGO
        isin = self.request.get('isin')
        raport_typ = self.request.get('raport_typ')
        logging.info("pobieram raport dla ticker: "+ticker+" skrot: "+skrot+" typ: "+raport_typ)
        
        pobierz_raporty(ticker, skrot, isin, raport_typ)
        logging.info("Skonczone pobieranie raportow dla "+ticker)

class UpdateNotowania(webapp.RequestHandler):   
    def get(self):
        #self.response.out.write(os.environ['CURRENT_VERSION_ID'])
        
        updatequotes()

class UpdateIndeksyTask(webapp.RequestHandler):
    
    def get(self):
        self.post()
        
    def post(self):
        try:
            k = self.request.get('k')
            url = self.request.get('url')
            #print url
            #if k=='': k="sWIG80"
            #if url=='': url="http://www.gpw.pl/ajaxindex.php?action=GPWPortfele&start=listForIndex&isin=PL9999999979&lang=PL"
            
            try:     
                    req = urllib2.Request(url, headers= headers)
                    response = urllib2.urlopen(req)
                    
                    content = response.read()
                    tab = BeautifulSoup(content).findAll('table', {'id':'footable'})
                    rows = tab[0].findAll('tr')
                    po = Portfel(key_name = k, nazwa_pelna=k, czy_indeks = True)
                    
                    for r in rows[1:]:
                        #print r
                        entry = [ str(x.text.encode("utf-8")).replace('&nbsp;', '') for x in r.findAll('td')]
                        
                        po.sklad_tickery.append(entry[0])

        
        
            
            except urllib2.HTTPError, e:
                    logging.error("Blad przy aktualizacji notowan.")
                    logging.error(str(e))  
                    return

            po.put()
        except Exception, e:
            stacktrace = traceback.format_exc()
            logging.error(e)
            logging.error('%s', stacktrace)
        
class UpdateIndeksy(webapp.RequestHandler):
    def get(self):
        '''
        uwaga, moge tu miec duzo wiecej danych,
        ale narazie laduje tylko dane - jaka spolka w jakim indeksie i koniec - bez udzialu procentowego.
        '''
            
        for k in mapa_isin_indeksow.keys():
            # dla pierwszego z indeksów pobieramy skład
            #url = "http://www.gpw.pl/ajaxindex.php?action=GPWPortfele&start=listForIndex&isin="+mapa_isin_indeksow[k]+"&lang=PL"
            #url = "https://www.gpw.pl/indeks?isin="+mapa_isin_indeksow[k]
            url =  "https://www.gpw.pl/ajaxindex.php?action=GPWIndexes&start=ajaxPortfolio&format=html&lang=PL&isin="+mapa_isin_indeksow[k] #+"&cmng_id=11&time=1503158652299
            taskqueue.add(url='/update-indeksy-task', 
                          params={'k': k, 'url' : url})
        
        #taskqueue.add(url='/update-indeksy-na-symbolach', params={'k': k, 'url' : url})
            # okej, mamy listę spółek w danym indeksie
        # koniec przegladania wszystkich indeksów
        #save_symbole(symbole_dict) 
        #self.response.out.write("Finished.</body></html>")        

class StworzSymbole(webapp.RequestHandler):
    '''
    po usunieciu wszystkich obiektow typu Symbol z datastore nalezy uruchomic ten handler aby zapelnic od nowa Symbolami baze.
    '''
    def get(self):
        update_ISIN()

class UpdateNotowaniaTask(webapp.RequestHandler):
    
    def get(self):    

        
        symbole_dict = get_symbole_all()
        keys = sorted(symbole_dict)
        
        h2 = HtmlFragment(key_name = "notowania"+mom_str)
        h2.tresc = zaladuj_notowania_html_mom( symbole_dict, keys ) # przekazujemy slownik
        gc.collect()
        h2.put()
        # po zapisaniu w bazie - skasuj to co jest w memcache
        memcache.delete("notowania"+mom_str) #@UndefinedVariable       

    
    def post(self):
        uploaded_file = self.request.POST.get("notowania")
        ticker = uploaded_file.filename.split(".")[0]
        
        symbol = Symbol.get_by_key_name(ticker)
        
        lines = uploaded_file.file.readlines()[1:]
        lines.reverse()
        del symbol.h_date[:]
        del symbol.h_open[:]
        del symbol.h_high[:]
        del symbol.h_low[:]
        del symbol.h_close[:]
        del symbol.h_vol[:]
        # Date,Time,Open,High,Low,Close,Vol,OI,Annotation
        for line in lines:
            items = line.split(",")
            date = items[0]
            ope = float(items[2])
            hi = float(items[3])
            lo = float(items[4])
            cl = float(items[5])
            vol = int(items[6])
            
            symbol.h_date.append(date)
            symbol.h_open.append(ope)
            symbol.h_high.append(hi)
            symbol.h_low.append(lo)
            symbol.h_close.append(cl)
            symbol.h_vol.append(vol)
        #######
        # teraz moge policzyc SMA100 oraz smaVOL
        srednia = 0.0
        for i in range(100):
            srednia += symbol.h_close[ i ]
        
        symbol.sma100 = srednia/100.0
        symbol.kurs_nad_sma = symbol.h_close[0] > symbol.sma100
        ######
        # teraz smaVOL
        srednia = 0
        for i in range(60):
            srednia += symbol.h_vol[ i ]
        
        symbol.smaVol = srednia/60
        symbol.zaILE = symbol.h_close[0] * symbol.smaVol * 0.02 # trzymamy się zasady max 2%     
        
        #####
        # TODO: teraz trzeba policzyć ATR
        
        ####
        # TODO: teraz policzyć SLOPE
        
        ####
        # TODO: teraz policzyć R2
        
        #######
        symbol.put()
             

class UpdateDywidendy(webapp.RequestHandler):
    def get(self):
        page = self.request.get('page')
        
        if page is None or page=='': 
            page = 1
        symbole_dict = get_symbole_all()
    
        # wykasuje wszystkie dane dot. dywidendy
        for s in symbole_dict.values():
            s.dyw_na_akcje = ''
            s.biezaca_dywidenda = ''

        #updatedywidendy(datetime.now().year -1, symbole_dict)        
        updatedywidendy(datetime.now().year, symbole_dict, page)
        
        save_symbole(symbole_dict)
        
class UpdateSymboleRaportami(webapp.RequestHandler):
    def get(self):
        '''
        jak mamy raporty w bazie, ale symbole byly wywalone z bazy i na nowo utworzone,
        to aby zapelnic w symbolach dane typu zysk/akcje czy wk/akcje
        uruchamia sie ta metode.
        '''
        #raporty = get_raport(ticker,s)
        symbole_dict = get_symbole_all()
        for s in symbole_dict.values():
            update_symbol_raportem(get_raport(s.ticker), s)

class UpdateISIN(webapp.RequestHandler):
    def get(self):
        '''
        jak mamy raporty w bazie, ale symbole byly wywalone z bazy i na nowo utworzone,
        to aby zapelnic w symbolach dane typu zysk/akcje czy wk/akcje
        uruchamia sie ta metode.
        '''
        #raporty = get_raport(ticker,s)
        update_ISIN()

class UpdatePanel(webapp.RequestHandler):
    
    def post(self):
        
        tickers = self.request.get("tickers").split()
        avoid = self.request.get("avoid").split()
        res = set(tickers)-set(avoid)
        
        symbole = Symbol.all().fetch(10000)

        for s in symbole:
            if s.ticker in res:
                #logging.info(s.ticker)
                #logging.info( s.isin)
                #logging.info( s.raport_typ)
                taskqueue.add(url='/update-raporty-task', 
                          params={'ticker': s.ticker, 'skrot' : s.skrot, 'isin': s.isin,
                                  'raport_typ' : s.raport_typ })            
        
        lista = self.request.get_all("ticker")
        for a in lista: 
            ab = a.split('#')
            isin = ab[0]
            raport_typ = ab[1]
            ticker = ab[2]
            
            typ_operacji = self.request.get("typ_operacji")
            if typ_operacji == 'raport':
    
                taskqueue.add(url='/update-raporty-task', params={'ticker': ticker, 'isin' : isin, 'raport_typ' : raport_typ })
                #pobierz_raporty(ticker, isin, raport_typ )
            elif typ_operacji == 'kasuj_symbole_bez_isin':
                to_delete = []
                symbole_dict = get_symbole_all()
                for s in symbole_dict.values():
                    if s.isin is None:
                        to_delete.append(s)
                db.delete(to_delete)
        
    def get(self):
        
            
        self.response.out.write("""
        <html>
        <body>
        <FORM id="tickersForm" action="/update-panel" method="post">
        <P>
            <LABEL for="tickers">Tickery: </LABEL>
            <input type="text" size="100" name="tickers">
                      <BR>
            <LABEL for="avoid">Pomiń: </LABEL>
            <input type="text" size="100" name="avoid">
                <BR>
            <INPUT type="submit" value="Send"> 
            <INPUT type="reset">
            </P>
         </FORM>
       <FORM action="/update-panel" method="post">
            <P>
            <LABEL for="ticker">Ticker: </LABEL>
                      <select size="35" name="ticker" multiple="true">""")

        symbole = Symbol.all().fetch(10000)
        for s in symbole:
            if s is not None and s.ticker is not None:
                typ = 'H' if  s.raport_typ is None else s.raport_typ
                self.response.out.write('<option value="'+s.isin+'#'+typ+'#'+s.ticker+'">'+s.ticker+'</option>')
        
        self.response.out.write("""
                      </select>
                      <BR>
            <LABEL for="action">Update type: </LABEL>
                    <SELECT name="typ_operacji">
                      <OPTION type="text" value="raport">Raport<BR>
                      <OPTION type="text" value="kasuj_symbole_bez_isin">Kasuj symbole bez ISIN<BR>
                    </SELECT>
            <INPUT type="submit" value="Send"> 
            <INPUT type="reset">
            </P>
         </FORM>
        """
        )
        
        
        self.response.out.write("""
        </body>
        </html>
        
        """
        )

class UpdateTable(webapp.RequestHandler):
    def get(self):
        pass


class UpdateIndeksyNaSymbolach(webapp.RequestHandler):
    def get(self):
        symbole_dict = get_symbole_all()
        for s in symbole_dict.values(): #czyścimy przypisania do indeksów
            s.udzial_w_indeksach = []
        gc.collect()
        portfele = Portfel.all() # weź aktualne składy indeksów
        portfele.order("-nazwa_pelna")
        for p in portfele:
            if not p.czy_indeks: #odrzucamy portfele które nie są składem indeksu, tylko są strategią
                continue 
            for ticker in p.sklad_tickery:
                if symbole_dict.has_key(ticker):
                    symbole_dict[ticker].udzial_w_indeksach.append(p.nazwa_pelna)
        for s in symbole_dict.values(): # zapisz dogodny format dla prezentacji
            s.udzial_w_indeksach_str =  ', '.join(s.udzial_w_indeksach)
        gc.collect()
        save_symbole(symbole_dict)
    

def update_blog():
    
    blogger_service = service.GDataService('akcjeg@gmail.com', '15%rocznie')
    blogger_service.source = 'pawel-akcjegrahama-1.0'
    blogger_service.service = 'blogger'
    blogger_service.account_type = 'GOOGLE'
    blogger_service.server = 'www.blogger.com'
    blogger_service.ProgrammaticLogin()
    
#    query = service.Query()
#    query.feed = '/feeds/default/blogs'
#    #feed = blogger_service.Get(query.ToUri())
#    
#    #print feed.title.text #'Paweł's blogs'
#    
#    #for entry in feed.entry:
#    #    print "\t" + entry.title.text
#        #blog_id =  entry.GetSelfLink().href.split("/")[-1] #blog id
#        #print "###"
#    #today = str(datetime.now().month)+''+str(datetime.now().day)
    today = str(datetime.now().day).zfill(2)+'/'+str(datetime.now().month).zfill(2)
    portfele = Portfel.gql('WHERE czy_indeks = FALSE')
    msg =''
    for p in portfele:
        #if len(p.sklad_tickery)>0:
        msg += p.nazwa_pelna +" ("+str(len(p.sklad_tickery))+"): "
        msg += ", ".join(sorted(p.sklad_tickery))
        msg += '\n\n'
        #else:
        #    msg += 'Brak '+p.nazwa_pelna+".\n\n"
    msg += u"Spółki w upadłości nie są uwzględniane."
    CreatePublicPost(blogger_service, 2066533151149389176, # 1413823615252489882 = test-gae
    title='Akcje Grahama ('+today+')', content=msg)
    
def CreatePublicPost(blogger_service, blog_id, title, content):
    entry = gdata.GDataEntry()
    entry.title = atom.Title('xhtml', title)
    entry.content = atom.Content(content_type='html', text=content)
    return blogger_service.Post(entry, '/feeds/%s/posts/default' % blog_id)

    
        
def testuj_ft():
    
########################## DAJ USTAWIC CIASTECZKO #####################
    
    url =r"http://markets.ft.com/research/Markets/Overview"
         
    jar = cookielib.FileCookieJar("cookies")  
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(jar))
    
    req = urllib2.Request(url, headers= headers)
    response = opener.open(req)
    response.read() #ignoruj wyniki

    ########################## ZALOGUJ SIE #####################
    url ='https://registration.ft.com/registration/barrier/login'
    form_fields = {
      "username": "wostok@poczta.fm",
      "password": "123qwe",
      "rememberme": "on",
      "x": "0",
      "y": "0" #---------------------> skąd pobrać akurat tą wartość, gdzie jest mapowanie że to jest POLNORD?????
    }
    payload = urllib.urlencode(form_fields)
    req = urllib2.Request(url, data = payload, headers = headers)
    response = opener.open(req) #urllib2.urlopen(req)
    response.read()
    ######################### Zaladuj screener #####################

    url ='http://markets.ft.com/screener/customScreen.asp?criteria=B64ENCW3siZmllbGQiOiJDb3VudHJ5Q29kZSIsInZhbHVlcyI6WyJMSUtFOkFULEJFLEJBLEJHLEhSLENZLENaLERLLEVFLEZJLEZSLERFLEdSLEhVLElTLElFLElULExWLExULExVLE1LLE1ULE5MLE5PLFBMLFBULFJPLFNLLFNJLEVTLFNFLENILFRSLFVBLEdCLFlVLFJVIl19LHsiZmllbGQiOiJJbmR1c3RyeUNvZGUiLCJ2YWx1ZXMiOlsiTElLRToxMDAzLDEwMDYsMTAxMiwxMDE1LDEwMTgsMTAyMSwxMDI0LDEwMjcsMTAzMCwxMDMzLDEwMzYsMTEwMywxMTA2LDExMDksMTExMiwxMTE1LDExMTgsMTIwMywxMjA2LDEyMDksMDkxNSwwOTU3LDA2MDYsMDEwMywwMTA2LDAxMDksMDExMiwwMTE1LDAxMTgsMDEyMSwwMTI0LDAxMjcsMDEzMCwwMTMzLDAyMDMsMDIwNiwwMjA5LDAyMTIsMDIxNSwwMjE4LDAyMjEsMDMwMywwNDAzLDA0MDYsMDQwOSwwNDEyLDA0MTUsMDQxOCwwNDIxLDA0MjQsMDQyNywwNDMwLDA0MzMsMDQzNiwwNTAzLDA1MDYsMDUwOSwwNTEyLDA1MTUsMDUxOCwwNTIxLDA1MjQsMDYwMywwNjA5LDA2MTIsMDgwMywwODA2LDA4MDksMDgxMiwwOTAzLDA5MDYsMDkwOSwwOTEyLDA5MTgsMDkyMSwwOTI0LDA5MjcsMDkzMCwwOTMzLDA5MzYsMDkzOSwwOTQyLDA5NDUsMDk0OCwwOTUxLDA5NTQsMDk2MCwwOTYzLDA5NjYsMDk2OSwwOTcyLDA5NzUiXX0seyJmaWVsZCI6Ik1hcmtldENhcCJ9LHsiZmllbGQiOiJEaXZpZGVuZFlpZWxkIn0seyJmaWVsZCI6IkN1cnJlbnRSYXRpbyIsInZhbHVlcyI6WyJHRVE6MS4zfExFUToiXX0seyJmaWVsZCI6IlByaWNlVG9Cb29rTVJRIiwidmFsdWVzIjpbIkxFUTowLjd8R0VROiJdfSx7ImZpZWxkIjoiUHJpY2VUb0Nhc2hGbG93VFRNIiwidmFsdWVzIjpbIkdFUTowLjAxfExFUToiXX0seyJmaWVsZCI6IlBFRXhjbFhJdGVtc1RUTSIsInZhbHVlcyI6WyJHRVE6MC4wMXxMRVE6Il19XQ=='
    #req = urllib2.Request(url, headers = headers)
    response = urlfetch.fetch(url=url, method=urlfetch.GET, deadline=60 , headers= headers)
    print response.content

     

class UpdateRecznie(webapp.RequestHandler):
    def get(self):   
        s = self.response.out
        s.write('''
        <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1">
<title>Test</title>
</head>
<body>
        
        ''') 
        s.write('<form action="/update-raport-recznie" method="POST" enctype="multipart/form-data">')
        s.write('<input type="file" name="excel"/>')
        s.write('<input type="submit" value="Submit"/>')
        s.write('</form></body>')    
    
    def post(self):   

        book = xlrd.open_workbook(file_contents=self.request.get("excel"))
  
        ticker = self.request.params["excel"].filename.split(".")[0]
        raport = Raport(key_name=ticker, ticker = ticker)

        #sh = book.sheet_by_index(0)
        for prefix in ["kw_", "r_"]:
            sh = book.sheet_by_name(prefix)          
            for rowN in range(sh.nrows):
                row = sh.row_values(rowN)
                if not Raport.nazwa_atr.has_key(row[0]):
                    continue
        
                setattr(raport , prefix + Raport.nazwa_atr[row[0]] , [ str(x) for x in row[1:] ]) #odetnij nazwe naglowka         
        raport.put()
        update_symbol_raportem(raport, get_symbol(ticker))

    
    
    # Refer to docs for more details.
    # Feedback on API is welcomed.
    
#        r = Raport.get_by_key_name("AGORA")
#        #self.response.out.write()
#        atrybuty = Raport.nazwa_atr.values()
#        #setattr(raport , prefix + Raport.nazwa_atr[entry[0]] , [ x.replace(",",".").replace(" ","") for x in entry[1:] ]) #odetnij nazwe naglowka
#        s = self.response.out 
#
#        for prefix in ["kw_", "r_"]:
#            s.write("Raporty "+prefix+": <BR>")
#            for atr_name in atrybuty:
#                atr = getattr(r, prefix+atr_name)
#                if isinstance(atr, list):                
#                    s.write( atr) 
#                    s.write("<BR>")               
#                else:
#                    # to jakiś błąd!!
#                    pass
            
        

class UpdateBlog(webapp.RequestHandler):
    def get(self):
        
#        self.response.out.write(
#"""
#<html>
#<header></header>
#<body>
#<form action="https://www.paypal.com/cgi-bin/webscr" method="post">
#<input type="hidden" name="cmd" value="_s-xclick">
#<input type="hidden" name="encrypted" value="-----BEGIN PKCS7-----MIIHTwYJKoZIhvcNAQcEoIIHQDCCBzwCAQExggEwMIIBLAIBADCBlDCBjjELMAkGA1UEBhMCVVMxCzAJBgNVBAgTAkNBMRYwFAYDVQQHEw1Nb3VudGFpbiBWaWV3MRQwEgYDVQQKEwtQYXlQYWwgSW5jLjETMBEGA1UECxQKbGl2ZV9jZXJ0czERMA8GA1UEAxQIbGl2ZV9hcGkxHDAaBgkqhkiG9w0BCQEWDXJlQHBheXBhbC5jb20CAQAwDQYJKoZIhvcNAQEBBQAEgYAVEoQRr/k/1UFgdKugymcXM7LnZKqzGaowVm/C2oevyTWL1lEjLCLNOB8lohRVT+R/6c7UmazWoCwl/TRlTH39bEJ/KppWsUqGDEzmhlg6lWrAY1G/Zpau+sRNuDu0oUWbSUXGnkbKXAkB5pZIrFk34DaitVOue78cwkyUwbBzgjELMAkGBSsOAwIaBQAwgcwGCSqGSIb3DQEHATAUBggqhkiG9w0DBwQIHOBwi2XLorKAgagoZgVfJGZmt/QIftQabnW254Sfd1e4RdpFRz+vI2BniLtOZCw5Bjru9+fa1B9aXc0Hxp418/rEtCsY6uYRbE1rBQYyF4xmimqYE03siJc7xhIMtiRhA8HhO/RzJHX1ThMOvr3MEgYYA0ZRrAfbBPFBuYxgq9nhrhxttKw3G8vU5j8be13ZR4wg5a9B9++4WukWmqJhtvRpe4k2NskRwI6dArOi8e/RwNKgggOHMIIDgzCCAuygAwIBAgIBADANBgkqhkiG9w0BAQUFADCBjjELMAkGA1UEBhMCVVMxCzAJBgNVBAgTAkNBMRYwFAYDVQQHEw1Nb3VudGFpbiBWaWV3MRQwEgYDVQQKEwtQYXlQYWwgSW5jLjETMBEGA1UECxQKbGl2ZV9jZXJ0czERMA8GA1UEAxQIbGl2ZV9hcGkxHDAaBgkqhkiG9w0BCQEWDXJlQHBheXBhbC5jb20wHhcNMDQwMjEzMTAxMzE1WhcNMzUwMjEzMTAxMzE1WjCBjjELMAkGA1UEBhMCVVMxCzAJBgNVBAgTAkNBMRYwFAYDVQQHEw1Nb3VudGFpbiBWaWV3MRQwEgYDVQQKEwtQYXlQYWwgSW5jLjETMBEGA1UECxQKbGl2ZV9jZXJ0czERMA8GA1UEAxQIbGl2ZV9hcGkxHDAaBgkqhkiG9w0BCQEWDXJlQHBheXBhbC5jb20wgZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBAMFHTt38RMxLXJyO2SmS+Ndl72T7oKJ4u4uw+6awntALWh03PewmIJuzbALScsTS4sZoS1fKciBGoh11gIfHzylvkdNe/hJl66/RGqrj5rFb08sAABNTzDTiqqNpJeBsYs/c2aiGozptX2RlnBktH+SUNpAajW724Nv2Wvhif6sFAgMBAAGjge4wgeswHQYDVR0OBBYEFJaffLvGbxe9WT9S1wob7BDWZJRrMIG7BgNVHSMEgbMwgbCAFJaffLvGbxe9WT9S1wob7BDWZJRroYGUpIGRMIGOMQswCQYDVQQGEwJVUzELMAkGA1UECBMCQ0ExFjAUBgNVBAcTDU1vdW50YWluIFZpZXcxFDASBgNVBAoTC1BheVBhbCBJbmMuMRMwEQYDVQQLFApsaXZlX2NlcnRzMREwDwYDVQQDFAhsaXZlX2FwaTEcMBoGCSqGSIb3DQEJARYNcmVAcGF5cGFsLmNvbYIBADAMBgNVHRMEBTADAQH/MA0GCSqGSIb3DQEBBQUAA4GBAIFfOlaagFrl71+jq6OKidbWFSE+Q4FqROvdgIONth+8kSK//Y/4ihuE4Ymvzn5ceE3S/iBSQQMjyvb+s2TWbQYDwcp129OPIbD9epdr4tJOUNiSojw7BHwYRiPh58S1xGlFgHFXwrEBb3dgNbMUa+u4qectsMAXpVHnD9wIyfmHMYIBmjCCAZYCAQEwgZQwgY4xCzAJBgNVBAYTAlVTMQswCQYDVQQIEwJDQTEWMBQGA1UEBxMNTW91bnRhaW4gVmlldzEUMBIGA1UEChMLUGF5UGFsIEluYy4xEzARBgNVBAsUCmxpdmVfY2VydHMxETAPBgNVBAMUCGxpdmVfYXBpMRwwGgYJKoZIhvcNAQkBFg1yZUBwYXlwYWwuY29tAgEAMAkGBSsOAwIaBQCgXTAYBgkqhkiG9w0BCQMxCwYJKoZIhvcNAQcBMBwGCSqGSIb3DQEJBTEPFw0xMjA0MTMwOTI0MzVaMCMGCSqGSIb3DQEJBDEWBBTaPIvA39E2oW3LZA6aW2pNLfiFiTANBgkqhkiG9w0BAQEFAASBgBz9w1KUtUfQFlboKw3yJAgUgS6rfW6nzjkhYTLucneohFiVXb/Xtzu16TAmiZgtFpJ86uFvlMJYxSqb0CH3VdQJ3WwWsMObgHp1gsf1pOowYcSKaWOgwxSuI0fgRyj3kAw8M3n14GbblcsQGmu1t/Q/9C8eepjBMPuwn7e+P3vq-----END PKCS7-----
#">
#<input type="image" src="https://www.paypalobjects.com/pl_PL/PL/i/btn/btn_donateCC_LG.gif" border="0" name="submit" alt="PayPal — Płać wygodnie i bezpiecznie">
#<img alt="" border="0" src="https://www.paypalobjects.com/pl_PL/i/scr/pixel.gif" width="1" height="1">
#</form>
#
#</body>
#</html>
#                                
#""" )
        
        update_blog()
        return
        a ="""
        \u003ctable data-ajax-content=\"true\"\u003e\u003cthead\u003e\u003ctr\u003e\u003ctd class=\"label\"\u003eFiscal Year Ending Dec 31 2011\u003c/td\u003e\u003ctd\u003eDec 31 2011\u003c/td\u003e\u003ctd\u003eSep 30 2011\u003c/td\u003e\u003ctd\u003eJun 30 2011\u003c/td\u003e\u003c/tr\u003e\u003c/thead\u003e\u003ctbody\u003e\u003ctr class=\"section even\"\u003e\u003ctd colspan=\"4\"\u003eASSETS\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"odd\"\u003e\u003ctd class=\"label\"\u003eCash And Short Term Investments\u003c/td\u003e\u003ctd\u003e125\u003c/td\u003e\u003ctd\u003e124\u003c/td\u003e\u003ctd\u003e128\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"even\"\u003e\u003ctd class=\"label\"\u003eTotal Receivables, Net\u003c/td\u003e\u003ctd\u003e161\u003c/td\u003e\u003ctd\u003e146\u003c/td\u003e\u003ctd\u003e235\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"odd\"\u003e\u003ctd class=\"label\"\u003eTotal Inventory\u003c/td\u003e\u003ctd\u003e1,173\u003c/td\u003e\u003ctd\u003e1,253\u003c/td\u003e\u003ctd\u003e1,249\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"even\"\u003e\u003ctd class=\"label\"\u003ePrepaid expenses\u003c/td\u003e\u003ctd\u003e--\u003c/td\u003e\u003ctd\u003e--\u003c/td\u003e\u003ctd\u003e--\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"odd\"\u003e\u003ctd class=\"label\"\u003eOther current assets, total\u003c/td\u003e\u003ctd\u003e7.30\u003c/td\u003e\u003ctd\u003e8.15\u003c/td\u003e\u003ctd\u003e12\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"Bold even\"\u003e\u003ctd class=\"label\"\u003eTotal current assets\u003c/td\u003e\u003ctd\u003e1,467\u003c/td\u003e\u003ctd\u003e1,531\u003c/td\u003e\u003ctd\u003e1,624\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"odd\"\u003e\u003ctd class=\"label\"\u003eProperty, plant &amp; equipment, net\u003c/td\u003e\u003ctd\u003e15\u003c/td\u003e\u003ctd\u003e14\u003c/td\u003e\u003ctd\u003e18\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"even\"\u003e\u003ctd class=\"label\"\u003eGoodwill, net\u003c/td\u003e\u003ctd\u003e130\u003c/td\u003e\u003ctd\u003e130\u003c/td\u003e\u003ctd\u003e130\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"odd\"\u003e\u003ctd class=\"label\"\u003eIntangibles, net\u003c/td\u003e\u003ctd\u003e0.93\u003c/td\u003e\u003ctd\u003e0.89\u003c/td\u003e\u003ctd\u003e0.94\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"even\"\u003e\u003ctd class=\"label\"\u003eLong term investments\u003c/td\u003e\u003ctd\u003e541\u003c/td\u003e\u003ctd\u003e534\u003c/td\u003e\u003ctd\u003e526\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"odd\"\u003e\u003ctd class=\"label\"\u003eNote receivable - long term\u003c/td\u003e\u003ctd\u003e37\u003c/td\u003e\u003ctd\u003e36\u003c/td\u003e\u003ctd\u003e33\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"even\"\u003e\u003ctd class=\"label\"\u003eOther long term assets\u003c/td\u003e\u003ctd\u003e--\u003c/td\u003e\u003ctd\u003e0.33\u003c/td\u003e\u003ctd\u003e0.32\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"Bold odd\"\u003e\u003ctd class=\"label\"\u003eTotal assets\u003c/td\u003e\u003ctd\u003e2,221\u003c/td\u003e\u003ctd\u003e2,276\u003c/td\u003e\u003ctd\u003e2,359\u003c/td\u003e\u003c/tr\u003e\u003c/tbody\u003e\u003ctbody\u003e\u003ctr class=\"section even\"\u003e\u003ctd colspan=\"4\"\u003eLIABILITIES\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"odd\"\u003e\u003ctd class=\"label\"\u003eAccounts payable\u003c/td\u003e\u003ctd\u003e--\u003c/td\u003e\u003ctd\u003e--\u003c/td\u003e\u003ctd\u003e--\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"even\"\u003e\u003ctd class=\"label\"\u003eAccrued expenses\u003c/td\u003e\u003ctd\u003e24\u003c/td\u003e\u003ctd\u003e5.45\u003c/td\u003e\u003ctd\u003e6.11\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"odd\"\u003e\u003ctd class=\"label\"\u003eNotes payable/short-term debt\u003c/td\u003e\u003ctd\u003e239\u003c/td\u003e\u003ctd\u003e124\u003c/td\u003e\u003ctd\u003e142\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"even\"\u003e\u003ctd class=\"label\"\u003eCurrent portion long-term debt/capital leases\u003c/td\u003e\u003ctd\u003e146\u003c/td\u003e\u003ctd\u003e125\u003c/td\u003e\u003ctd\u003e116\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"odd\"\u003e\u003ctd class=\"label\"\u003eOther current liabilities, total\u003c/td\u003e\u003ctd\u003e127\u003c/td\u003e\u003ctd\u003e180\u003c/td\u003e\u003ctd\u003e172\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"Bold even\"\u003e\u003ctd class=\"label\"\u003eTotal current liabilities\u003c/td\u003e\u003ctd\u003e572\u003c/td\u003e\u003ctd\u003e471\u003c/td\u003e\u003ctd\u003e496\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"odd\"\u003e\u003ctd class=\"label\"\u003eTotal long term debt\u003c/td\u003e\u003ctd\u003e318\u003c/td\u003e\u003ctd\u003e465\u003c/td\u003e\u003ctd\u003e524\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"even\"\u003e\u003ctd class=\"label\"\u003eTotal debt\u003c/td\u003e\u003ctd\u003e703\u003c/td\u003e\u003ctd\u003e714\u003c/td\u003e\u003ctd\u003e782\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"Bold odd\"\u003e\u003ctd class=\"label\"\u003eDeferred income tax\u003c/td\u003e\u003ctd\u003e45\u003c/td\u003e\u003ctd\u003e65\u003c/td\u003e\u003ctd\u003e63\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"even\"\u003e\u003ctd class=\"label\"\u003eMinority interest\u003c/td\u003e\u003ctd\u003e--\u003c/td\u003e\u003ctd\u003e--\u003c/td\u003e\u003ctd\u003e--\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"odd\"\u003e\u003ctd class=\"label\"\u003eOther liabilities, total\u003c/td\u003e\u003ctd\u003e3.35\u003c/td\u003e\u003ctd\u003e4.10\u003c/td\u003e\u003ctd\u003e2.41\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"Bold even\"\u003e\u003ctd class=\"label\"\u003eTotal liabilities\u003c/td\u003e\u003ctd\u003e939\u003c/td\u003e\u003ctd\u003e1,005\u003c/td\u003e\u003ctd\u003e1,085\u003c/td\u003e\u003c/tr\u003e\u003c/tbody\u003e\u003ctbody\u003e\u003ctr class=\"section even\"\u003e\u003ctd colspan=\"4\"\u003eSHAREHOLDERS EQUITY\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"odd\"\u003e\u003ctd class=\"label\"\u003eCommon stock\u003c/td\u003e\u003ctd\u003e48\u003c/td\u003e\u003ctd\u003e48\u003c/td\u003e\u003ctd\u003e48\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"even\"\u003e\u003ctd class=\"label\"\u003eAdditional paid-in capital\u003c/td\u003e\u003ctd\u003e1,011\u003c/td\u003e\u003ctd\u003e1,011\u003c/td\u003e\u003ctd\u003e1,011\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"odd\"\u003e\u003ctd class=\"label\"\u003eRetained earnings (accumulated deficit)\u003c/td\u003e\u003ctd\u003e223\u003c/td\u003e\u003ctd\u003e212\u003c/td\u003e\u003ctd\u003e215\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"even\"\u003e\u003ctd class=\"label\"\u003eTreasury stock - common\u003c/td\u003e\u003ctd\u003e0\u003c/td\u003e\u003ctd\u003e0\u003c/td\u003e\u003ctd\u003e0.00\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"odd\"\u003e\u003ctd class=\"label\"\u003eUnrealized gain (loss)\u003c/td\u003e\u003ctd\u003e--\u003c/td\u003e\u003ctd\u003e--\u003c/td\u003e\u003ctd\u003e--\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"even\"\u003e\u003ctd class=\"label\"\u003eOther equity, total\u003c/td\u003e\u003ctd\u003e0.88\u003c/td\u003e\u003ctd\u003e0.05\u003c/td\u003e\u003ctd\u003e(0.44)\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"Bold odd\"\u003e\u003ctd class=\"label\"\u003eTotal equity\u003c/td\u003e\u003ctd\u003e1,283\u003c/td\u003e\u003ctd\u003e1,271\u003c/td\u003e\u003ctd\u003e1,274\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"Bold even\"\u003e\u003ctd class=\"label\"\u003eTotal liabilities &amp; shareholders\u0027 equity\u003c/td\u003e\u003ctd\u003e2,221\u003c/td\u003e\u003ctd\u003e2,276\u003c/td\u003e\u003ctd\u003e2,359\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"odd\"\u003e\u003ctd class=\"label\"\u003eTotal common shares outstanding\u003c/td\u003e\u003ctd\u003e24\u003c/td\u003e\u003ctd\u003e24\u003c/td\u003e\u003ctd\u003e24\u003c/td\u003e\u003c/tr\u003e\u003ctr class=\"even\"\u003e\u003ctd class=\"label\"\u003eTreasury shares - common primary issue\u003c/td\u003e\u003ctd\u003e--\u003c/td\u003e\u003ctd\u003e--\u003c/td\u003e\u003ctd\u003e--\u003c/td\u003e\u003c/tr\u003e\u003c/tbody\u003e\u003c/table\u003e
        """
        #print a
#        return
#        url =r"http://markets.ft.com/Research/Markets/Tearsheets/Financials?s=PND:WSE&subview=BalanceSheet"
#        
#        try:     
#            jar = cookielib.FileCookieJar("cookies")  
#            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(jar))
#            
#            req = urllib2.Request(url, headers= headers)
#            response = opener.open(req)
#            output = response.read()
#            p = re.compile('\<td class=\"text first\"\>\<span\>([-+]?[0-9]*\.?[0-9]*)\</span\>' )
#            m = p.findall(output)
#            cena = m[0]
#            print cena # to ma być cena
#
#            # teraz przejście na interim results
#            form_fields = {
#              "statementType": "BalanceSheet",
#              "timeperiod": "q",
#              "wsodIssue": "231703" ---------------------> skąd pobrać akurat tą wartość, gdzie jest mapowanie że to jest POLNORD?????
#            }
#            payload = urllib.urlencode(form_fields)
#            
#            #response = urlfetch.fetch(url=url, payload= form_data, method=urlfetch.POST, deadline=60 , headers= headers)
#            url = r"http://markets.ft.com/RESEARCH/Remote/UK/Tearsheets/UpdateFinancialStatement"
#            req = urllib2.Request(url, data = payload, headers = headers)
#            
#            response = opener.open(req) #urllib2.urlopen(req)
#            
#            output = response.read()
        # TODO: pobierać też datę za jaki kwartał są dane!!
        # sprawdzić czy jak już raz pobiorę ciasteczko, czy mogę trzaskać już w usuługę AJAX-ową - szybka!
        output =a
        p = re.compile('Total current assets\\\u003c\/td\\\u003e\\\u003ctd\\\u003e(.*?)\\\u003c' )
        m = p.findall(output)
        tot_current_assets = m[0].replace(',','')
        print tot_current_assets
            
        p = re.compile('Total liabilities\\\u003c\/td\\\u003e\\\u003ctd\\\u003e(.*?)\\\u003c' )
        m = p.findall(output)
        tot_liabilities = m[0].replace(',','')
        print tot_liabilities 
        
        p = re.compile('Total common shares outstanding\\\u003c\/td\\\u003e\\\u003ctd\\\u003e(.*?)\\\u003c' )
        m = p.findall(output)
        tot_shares = m[0].replace(',','')
        print tot_shares
       
        ncav = (float(tot_current_assets) - float(tot_liabilities))/ float(tot_shares)
        
        print ncav 
        
            #self.response.out.write(response.content)
#            tables = SoupStrainer('table',attrs={ 'class':'tab03'})
#            
#            tab = BeautifulSoup(response.content, parseOnlyThese = tables).findAll('table') #, attrs={ 'class':'tabela big'}
#            rows = tab[0].findAll('tr')
        try:
            pass
        except urllib2.HTTPError, e:
            logging.error("Blad przy aktualizacji notowan.")
            logging.error(str(e))  
            return
            

application = webapp.WSGIApplication([('/update-panel',             UpdatePanel),
                                      ('/update-notowania',         UpdateNotowania),
                                      ('/update-notowania-task',    UpdateNotowaniaTask),
                                      ('/update-raporty',           UpdateRaporty),
                                      ('/update-raporty-task',      UpdateRaportyTask),
                                      #('/update-raporty-recent',    UpdateRaportyRecent),
                                      ('/update-stworz-symbole',    StworzSymbole),
                                      ('/update-indeksy',           UpdateIndeksy), #uruchamiac to w CRON w sobote lub niedziele raz na miesiac
                                      ('/update-indeksy-task',      UpdateIndeksyTask), #uruchamiac to w CRON w sobote lub niedziele raz na miesiac
                                      ('/update-indeksy-na-symbolach', UpdateIndeksyNaSymbolach),
                                      ('/update-dywidendy',         UpdateDywidendy), #uruchamiac to w CRON w sobote lub niedziele raz na miesiac
                                      ('/update-symbole-raportami', UpdateSymboleRaportami),
                                      ('/update-table',             UpdateTable),
                                      ('/update-isin',              UpdateISIN),
                                      ('/update-raport-recznie',    UpdateRecznie),
                                      
                                      ('/update-blog', UpdateBlog)
                                      ], debug=True)

def main():
    
    run_wsgi_app(application)

if __name__ == "__main__":
    main()