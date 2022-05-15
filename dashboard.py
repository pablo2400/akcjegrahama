# -*- coding: utf-8 -*-
from update import get_raport, get_symbol
import logging
import traceback

def policz_parametry(ticker):
    
    hdr = "['Rok',''],"
    raport_0=raport_1=raport_2=raport_3=raport_4=raport_5= hdr
    brak_danych = True
    parametry = {}
    
    try:
        r = get_raport(ticker) 
        s = get_symbol(ticker)
        
        parametry['bankrut'] = s.bankrut
        if s.bankrut:
            op = s.bankrut_opis.rsplit(' ',2)
            parametry['bankrut_opis'] = op[1]+' '+op[2]
        else:
            parametry['bankrut_opis'] = '' 
        
        if r is not None:
            brak_danych = False
            
            lata = [rok.replace("R'",'20') for rok in r.r_data_konca]
            ### --- przychody netto --- ###
            for t in zip(r.r_przychody_netto, lata):
                raport_0 += "['%s', %s]," % (t[1],t[0] if t[0]!='' else '0.0') 
            
            ### --- zysk netto --- ###            
            for t in zip(r.r_zysk_netto, lata):
                raport_1 += "['%s', %s]," % (t[1],t[0] if t[0]!='' else '0.0')  
            ### --- zysk na akcję --- ###
            for t in zip(r.r_zysk_na_akcje, lata):
                raport_2 += "['%s', %s]," % (t[1],t[0] if t[0]!='' else '0.0') 
                
            ### --- Przepływy pieniężne netto z dział. op. --- ###
            for t in zip(r.r_cf_op, lata):
                raport_3 += "['%s', %s]," % (t[1],t[0] if t[0]!='' else '0.0') 
                
            ### --- Total assets --- ###
            for t in zip(r.r_aktywa, lata):
                raport_4 += "['%s', %s]," % (t[1],t[0] if t[0]!='' else '0.0') 
                
            ### --- Total debt --- ###
            for t in zip(r.r_zob_dl, lata):
                raport_5 += "['%s', %s]," % (t[1].replace("R'",'20'),t[0] if t[0]!='' else '0.0')            
            
            parametry['waluta'] = '' #r.waluta TODO: aktualizacja waluty
            l = len(hdr)
        
            parametry['raport_0'] = raport_0[:-1] if len(raport_0)> l else hdr+"['',0]"
            parametry['raport_1'] = raport_1[:-1] if len(raport_1)> l else hdr+"['',0]"
            parametry['raport_2'] = raport_2[:-1] if len(raport_2)> l else hdr+"['',0]"
            parametry['raport_3'] = raport_3[:-1] if len(raport_3)> l else hdr+"['',0]"
            parametry['raport_4'] = raport_4[:-1] if len(raport_4)> l else hdr+"['',0]"
            parametry['raport_5'] = raport_5[:-1] if len(raport_5)> l else hdr+"['',0]"
            
            # teraz czas na policzenie ROA, ROE, marży itp
            if len(r.r_roa)>0:
                parametry['roa'] = "%.2g%%" %  (float(r.r_roa[0])*100.0)
            if len(r.r_roi_kap_wlasny)>0:
                parametry['roe'] = "%.2g%%" %  (float(r.r_roi_kap_wlasny[0])*100.0)
#            if len(r.r_m_zysku_brutto_sprzedazy)>0:
#                parametry['m_brutto'] = "%.2g%%" %  (float(r.r_m_zysku_brutto_sprzedazy[0])*100.0)
#            if len(r.r_m_zysku_op)>0: 
#                parametry['m_zysku_op'] = "%.2g%%" %  (float(r.r_m_zysku_op[0])*100.0)
#            if len(r.r_m_zysku_netto)>0:
#                parametry['m_zysku_netto'] = "%.2g%%" %  (float(r.r_m_zysku_netto[0])*100.0)
            #if 
#            if len(r.r_zysk_na_akcje)>0:
#                for z in [0:len(r.r_zysk_na_akcje)]: # na indeksie zero są najnowsze dane 
#                    wzrost = float(r.r_zysk_na_akcje[z]) - float(r.r_zysk_na_akcje[z])
#                parametry['zyski_wzrost'] = "%.2g%%" %  (float(r.r_m_zysku_netto[0])*100.0)
            if len(r.r_cr)>0:
                parametry['cr'] = r.r_cr[0]
#                if float(r.r_cr[0]) >= 1.9:
#                    parametry['cr_ok'] = "background-color:#2BFA14;" 
            
            #cr >= 1 + zob.dl./zob.kr
            
#            if len(r.r_cr)>0:                
#                #parametry['cr2'] = r.r_cr[0]
#                if float(r.r_cr[0]) >= (1+ float (r.r_zob_dl)/float(r.r_zob_kr)) :
#                    parametry['cr2_ok'] = '<span style="background-color:#2BFA14;">Aktywa obrotowe >= Całk. Zadłużenie<span>' 
        
        #--- koniec if-a czy raport jest null
                    # :-1 jest po to aby usunac koncowy przecinek.
        
    except Exception, e:
        stacktrace = traceback.format_exc()
        logging.warn(e)
        logging.warn(ticker)
        logging.warn('%s', stacktrace)
    
    return parametry, brak_danych