# -*- coding: utf-8 -*-
'''
Created on 30-08-2011
plik zawiera definicje encji danych przechowywanych w datastore
@author: plamik
'''

from google.appengine.ext import db
from google.appengine.ext import ndb

#from google.appengine.api import users

#class UserPrefs(db.Model):
#    user = db.ReferenceProperty(users.User)
#    zgoda = db.BooleanProperty(required=False,default=False,indexed=False)
#    aktywny_do = db.DateProperty(required=False,default=None,indexed=False)

import time
import webapp2_extras.appengine.auth.models

from webapp2_extras import security

class User(webapp2_extras.appengine.auth.models.User):
    
    subscription_end = ndb.model.DateProperty()
    
    def set_password(self, raw_password):
        """Sets the password for the current user
        
        :param raw_password:
            The raw password which will be hashed and stored
        """
        self.password = security.generate_password_hash(raw_password, length=12)

    @classmethod
    def get_by_auth_token(cls, user_id, token, subject='auth'):
        """Returns a user object based on a user ID and token.
        
        :param user_id:
            The user_id of the requesting user.
        :param token:
            The token string to be verified.
        :returns:
            A tuple ``(User, timestamp)``, with a user object and
            the token timestamp, or ``(None, None)`` if both were not found.
        """
        token_key = cls.token_model.get_key(user_id, subject, token)
        user_key = ndb.Key(cls, user_id)
        # Use get_multi() to save a RPC call.
        valid_token, user = ndb.get_multi([token_key, user_key])
        if valid_token and user:
            timestamp = int(time.mktime(valid_token.created.timetuple()))
            return user, timestamp
        
        return None, None
    
class Portfel(db.Model):
    nazwa_pelna = db.StringProperty(required=True) # czyli np. WIG20, mWIG40, sWIG80
    czy_indeks = db.BooleanProperty(indexed=True, default=False, required=True)
    sklad = db.ListProperty(item_type = db.Key) # lista Spolek - odnosniki zamiast nazw
    sklad_tickery = db.StringListProperty(indexed=True) # opcjonalnie - lista tickerow
    owner = db.UserProperty(indexed=True) # gdy puste, to pewnie jest to wtedy indeks
    
class Indeks(Portfel):
    pass

class HtmlFragment(db.Model):
    #kod  = db.StringProperty(indexed = True)
    tresc = db.TextProperty(indexed = False)

#class SymbolQuotes(db.Model):
#    ticker          = db.StringProperty(required = True, indexed=False) # np. TAURONPE
#    skrot           = db.StringProperty(indexed=False) # np. TPE - nie to samo co ticker TAURONPE
    

class Symbol(db.Model):
    
    #mnoznik         = db.IntegerProperty(indexed=False) # moznik dla raportow - np. jak byl split
    nazwa_pelna     = db.StringProperty(indexed=False) # np. Tauron Polska Energia S.A.
    ticker          = db.StringProperty(required = True, indexed=False) # np. TAURONPE
    isin            = db.StringProperty(indexed=False) # np. PLTAURN00011
    bankrut         = db.BooleanProperty(indexed=False) # tak/nie
    bankrut_opis    = db.StringProperty(indexed=False)
    skrot           = db.StringProperty(indexed=False) # np. TPE - nie to samo co ticker TAURONPE
    segment         = db.StringProperty(indexed=False) # moze trzeba bedzie z tego zrobic liste
    sektor          = db.StringProperty(indexed=False) # moze trzeba bedzie z tego zrobic liste
    kapitalizacja   = db.StringProperty(indexed=False) # a moze string property?
    #wolumen         = db.StringProperty(indexed=False) # a moze string property? moze to jest niepotrzebne?
    #obrot           = db.StringProperty(indexed=False) # a moze string property? moze to jest niepotrzebne?
    #sredni_wol      = db.StringProperty(indexed=False) # wazne, ale za ile sesji to jest srednia?
    ostatni_raport_kw = db.StringProperty(indexed=False) # np. " 2010-03-31"
    ostatni_raport_r = db.StringProperty(indexed=False) # np. "2011-12-31"
    raport_typ       = db.StringProperty(indexed=False) # H = skonsolidowany, J = jednostkowy
    zagraniczna      = db.BooleanProperty(indexed=False) # tak/nie
    waluta = db.StringProperty(indexed=False)
    
    # TODO: moze to wyodrebnic w osobny obiekt w tym samym Entity Group?
    kurs_ostatni    = db.StringProperty(indexed=False)
    kurs_data       = db.StringProperty(indexed=False)
    
    h_date = db.StringListProperty(indexed=False)
    h_open = db.ListProperty(item_type=float, indexed=False)
    h_high = db.ListProperty(item_type=float, indexed=False)
    h_low = db.ListProperty(item_type=float, indexed=False)
    h_close = db.ListProperty(item_type=float, indexed=False)
    h_vol = db.ListProperty(item_type=int, indexed=False)
    
    kurs_nad_sma    = db.BooleanProperty(indexed=False)
    sma100          = db.FloatProperty(indexed=False)
    smaVol          = db.IntegerProperty(indexed=False)
    zaILE          = db.FloatProperty(indexed=False) # za ile mogę kupić by nie przekroczyć 2% średnich obrotów za ostatnie 60 sesji?
    rank            = db.FloatProperty(indexed=False)
    
    #kurs_czas       = db.StringProperty(indexed=False)
    #kurs_zmiana     = db.StringProperty(indexed=False)
    #kurs_zmiana_proc= db.StringProperty(indexed=False)
    #kurs_otw        = db.StringProperty(indexed=False)
    #kurs_max        = db.StringProperty(indexed=False)
    #kurs_min        = db.StringProperty(indexed=False)
    #kurs_52_min     = db.StringProperty(indexed=False)
    #kurs_52_max     = db.StringProperty(indexed=False)
    
    
    # pozycje wyliczane przy aktualizacji raportu
    suma_zyskow_4kw   = db.FloatProperty(indexed=False)
    #sr_zyski_4ostkw   = DecimalProperty(indexed=False)
    sr_zyski_z_3lat = db.FloatProperty(indexed=False)
    liczba_akcji      = db.FloatProperty(indexed=False)
    wk_na_akcje_f       = db.FloatProperty(indexed=False)
    wk_g_na_akcje     = db.FloatProperty(indexed=False)
    zysk_za_ile_lat   = db.StringProperty(indexed=False) # za ile ostatnich lat byly zyski
    wzrost_zyskow     = db.StringProperty(indexed=False) # wartosc wieksza od zera oznacza ile procent wzrosly
    #liczba_akcji           = db.IntegerProperty(indexed=False)
    
    # pozycje wyliczane przy aktualizacji notowan   
    c_do_z          = db.StringProperty(indexed=False) # kwartalne zannualizowane
    c_do_z_avg      = db.StringProperty(indexed=False) # srednie c/z za ost. kilka lat - np. 5
    c_do_wk         = db.StringProperty(indexed=False)
    il_cz_cwk       = db.StringProperty(indexed=False)
    
    # pozycja uzupelniana po aktualizacji danych o dywidendach
    biezaca_dywidenda = db.StringProperty(indexed=False) 
    dyw_na_akcje = db.StringProperty(indexed=False)
    dyw_stopa = db.StringProperty(indexed=False)
    
    # current ratio   
    cr_f = db.FloatProperty(indexed=False)
    
    # accrual ratio - http://www.stockopedia.co.uk/ratios/accrual-ratio-trailing-12m-555/
    acr_f = db.FloatProperty(indexed=False)
    
    # kapital wlasny / aktywa
    kw_do_akt = db.StringProperty(indexed=False)
    
    # Debt/ net current assets <110%
    dlug_do_kap_obr = db.StringProperty(indexed=False)
    
    # c/wk grahama
    c_wk_grahama = db.StringProperty(indexed = False)
    
    # Piotroski F-Score
    f_score = db.IntegerProperty(indexed = False) 
    
    #wlid = db.StringProperty(indexed = False) # potrzebne do aktulaizacji raportow na podstawie strony interia
    
    udzial_w_indeksach = db.StringListProperty(indexed=False) # np ['WIG20', 'WIG_DIV', 'WIG']
    udzial_w_indeksach_str = db.StringProperty(indexed=False)   

class Raport(db.Model):
    
    ticker = db.StringProperty(indexed=False)
    nazwa_atr = {
u'Wartości w milionach (z wyjątkiem pozycji „na akcję”)': 'data_konca', \
u'Przychody łącznie': 'przychody_netto', \
u'Doch&#243;d operacyjny': 'zysk_op', \
u'Doch&#243;d przed opodatkowaniem': 'zysk_brutto', \
u'Przych&#243;d netto': 'zysk_netto', \

###### TODO  ########
u'Przepływy netto': 'cf_netto', \
u'Przepływy netto z działalności operacyjnej': 'cf_op', \
u'Przepływy netto z działalności inwestycyjnej': 'cf_inw', \
u'Przepływy netto z działalności finansowej': 'cf_fin', \
###############

u'Łączna wielkość aktyw&#243;w': 'aktywa', \
u'Aktywa bieżące łącznie': 'aktywa_b', \
u'Wartość firmy i inne aktywa niematerialne': 'aktywa_niemat', \
u'Zobowiązania niebieżące i udział mniejszościowy łącznie': 'zob_dl', \
u'Zobowiązania bieżące łącznie': 'zob_kr', \
u'Akcje łącznie': 'kap_wlasny', \
#u'Akcje zwykłe w obiegu': 'n_akcji', \   <!----------- to muszę wziąć z MONEY.PL

u'Wartość księgowa na jedną akcję (PLN)': 'wk_na_akcje', \
u'Zysk (strata) na jedną akcję (PLN)': 'zysk_na_akcje', \


#u'Zadeklarowana lub wypłacona dywidenda na jedną akcję (PLN)': 'dywidenda', \
#u'Marża zysku brutto ze sprzedaży' : 'm_zysku_brutto_sprzedazy', \
#u'Marża zysku operacyjnego' : 'm_zysku_op', \
#u'Marża zysku brutto' : 'm_zysku_brutto', \
#u'Marża zysku netto' : 'm_zysku_netto', \
#u'Stopa zwrotu z kapitału własnego' : 'roi_kap_wlasny', \
#u'Stopa zwrotu z kapitału własnego (ROE)': 'roi_kap_wlasny', \
#u'Stopa zwrotu z aktywów' : 'roa', \
#u'Stopa zwrotu z aktywów (ROA)' : 'roa', \
#u'Kapitał pracujący' : 'kap_pracujacy', \
#u'Wskaźnik płynności bieżącej' : 'cr', \
#u'Wskaźnik płynności szybkiej' : 'qr',\
#u'Wskaźnik podwyższonej płynności' : 'hr', \
#u'Rotacja należności' : 'rot_nal', \
#u'Rotacja zapasów' : 'rot_zap', \
#u'Cykl operacyjny' : 'cykl_op', \
#u'Rotacja zobowiązań' : 'rot_zob', \
#u'Cykl konwersji gotówki' : 'cykl_konw_got', \
#u'Rotacja aktywów obrotowych' : 'rot_akt_obr', \
#u'Rotacja aktywów' : 'rot_akt', \
#u'Wskaźnik pokrycia majątku' : 'wsk_pok_maj', \
#u'Stopa zadłużenia' : 'stopa_zadl', \
#u'EBITDA/odsetki' : 'ebitda_odsetki', \
#u'Dług/EBITDA' : 'dlug_ebitda'\
                 }

    czy_skonsolidowany = db.BooleanProperty(indexed=False) 
    waluta = db.StringProperty(indexed=False)
    
    ######################## kwartalny ###########################
    # kw_dlug_ebitda          = db.StringListProperty(indexed=False)
    # kw_ebitda_odsetki       = db.StringListProperty(indexed=False)
    # kw_stopa_zadl           = db.StringListProperty(indexed=False)
    # kw_wsk_pok_maj          = db.StringListProperty(indexed=False)
    # kw_rot_akt              = db.StringListProperty(indexed=False)
    # kw_rot_akt_obr          = db.StringListProperty(indexed=False)
    # kw_cykl_konw_got        = db.StringListProperty(indexed=False)
    # kw_rot_zob              = db.StringListProperty(indexed=False)
    # kw_cykl_op              = db.StringListProperty(indexed=False)
    # kw_rot_zap              = db.StringListProperty(indexed=False)
    kw_roa                  = db.StringListProperty(indexed=False)
    kw_roi_kap_wlasny       = db.StringListProperty(indexed=False)
    kw_kap_pracujacy        = db.StringListProperty(indexed=False)
    #kw_qr                   = db.StringListProperty(indexed=False) # quick ratio
    kw_cr                   = db.StringListProperty(indexed=False) # current ratio
    #kw_hr                   = db.StringListProperty(indexed=False) # wskaźnik podwyższonej płynności
    #kw_rot_nal              = db.StringListProperty(indexed=False) # rotacja należności
    #kw_m_zysku_brutto_sprzedazy       = db.StringListProperty(indexed=False) # marża zysku brutto ze sprzedazy
    #kw_m_zysku_op           = db.StringListProperty(indexed=False) # marza zysku operacyjnego
    #kw_m_zysku_brutto       = db.StringListProperty(indexed=False) # 
    #kw_m_zysku_netto        = db.StringListProperty(indexed=False) #
    kw_data_konca           = db.StringListProperty(indexed=False)
    kw_przychody_netto      = db.StringListProperty(indexed=False)
    kw_zysk_op              = db.StringListProperty(indexed=False)
    kw_zysk_brutto          = db.StringListProperty(indexed=False)
    kw_zysk_netto           = db.StringListProperty(indexed=False)
    kw_cf_netto             = db.StringListProperty(indexed=False)
    kw_cf_op                = db.StringListProperty(indexed=False)
    kw_cf_inw               = db.StringListProperty(indexed=False)
    kw_cf_fin               = db.StringListProperty(indexed=False)
    kw_aktywa               = db.StringListProperty(indexed=False)
    kw_aktywa_b               = db.StringListProperty(indexed=False)
    kw_aktywa_niemat               = db.StringListProperty(indexed=False)
   # kw_zob                  = db.StringListProperty(indexed=False)
    kw_zob_dl               = db.StringListProperty(indexed=False)
    kw_zob_kr               = db.StringListProperty(indexed=False)
    kw_kap_wlasny           = db.StringListProperty(indexed=False)
    #kw_kap_zakl             = db.StringListProperty(indexed=False)
    kw_n_akcji              = db.StringListProperty(indexed=False)
    kw_wk_na_akcje          = db.StringListProperty(indexed=False)
    kw_zysk_na_akcje        = db.StringListProperty(indexed=False)
    #kw_n_akcji_rozwodn      = db.StringListProperty(indexed=False)
    #kw_wk_na_akcje_rozwodn  = db.StringListProperty(indexed=False)
    #kw_zysk_na_akcje_rozwodn = db.StringListProperty(indexed=False)
    kw_dywidenda            = db.StringListProperty(indexed=False)
    
    ######################## roczny  ###########################
   # r_dlug_ebitda          = db.StringListProperty(indexed=False)
    #r_ebitda_odsetki       = db.StringListProperty(indexed=False)
   # r_stopa_zadl           = db.StringListProperty(indexed=False)
   # r_wsk_pok_maj          = db.StringListProperty(indexed=False)
   # r_rot_akt              = db.StringListProperty(indexed=False)
   # r_rot_akt_obr          = db.StringListProperty(indexed=False)
   # r_cykl_konw_got        = db.StringListProperty(indexed=False)
   # r_rot_zob              = db.StringListProperty(indexed=False)
   # r_cykl_op              = db.StringListProperty(indexed=False)
   # r_rot_zap              = db.StringListProperty(indexed=False)
    r_roa                  = db.StringListProperty(indexed=False)
    r_roi_kap_wlasny       = db.StringListProperty(indexed=False)
    r_kap_pracujacy        = db.StringListProperty(indexed=False)
    #r_qr                   = db.StringListProperty(indexed=False) # quick ratio
    r_cr                   = db.StringListProperty(indexed=False) # current ratio
    #r_hr                   = db.StringListProperty(indexed=False) # wskaźnik podwyższonej płynności
    #r_rot_nal              = db.StringListProperty(indexed=False) # rotacja należności
    #r_m_zysku_brutto_sprzedazy       = db.StringListProperty(indexed=False) # marża zysku brutto ze sprzedazy
    #r_m_zysku_op           = db.StringListProperty(indexed=False) # marza zysku operacyjnego
    #r_m_zysku_brutto       = db.StringListProperty(indexed=False) # 
    #r_m_zysku_netto        = db.StringListProperty(indexed=False) #
    r_data_konca           = db.StringListProperty(indexed=False)
    r_przychody_netto      = db.StringListProperty(indexed=False)
    r_zysk_op              = db.StringListProperty(indexed=False)
    r_zysk_brutto          = db.StringListProperty(indexed=False)
    r_zysk_netto           = db.StringListProperty(indexed=False)
    r_cf_netto             = db.StringListProperty(indexed=False)
    r_cf_op                = db.StringListProperty(indexed=False)
    r_cf_inw               = db.StringListProperty(indexed=False)
    r_cf_fin               = db.StringListProperty(indexed=False)
    r_aktywa               = db.StringListProperty(indexed=False)
    r_aktywa_b             = db.StringListProperty(indexed=False)
    r_aktywa_niemat               = db.StringListProperty(indexed=False)
   # r_zob                  = db.StringListProperty(indexed=False)
    r_zob_dl               = db.StringListProperty(indexed=False)
    r_zob_kr               = db.StringListProperty(indexed=False)
    r_kap_wlasny           = db.StringListProperty(indexed=False)
    #r_kap_zakl             = db.StringListProperty(indexed=False)
    r_n_akcji              = db.StringListProperty(indexed=False)
    r_wk_na_akcje          = db.StringListProperty(indexed=False)
    r_zysk_na_akcje        = db.StringListProperty(indexed=False)
    #r_n_akcji_rozwodn      = db.StringListProperty(indexed=False)
    #r_wk_na_akcje_rozwodn  = db.StringListProperty(indexed=False)
    #r_zysk_na_akcje_rozwodn = db.StringListProperty(indexed=False)
    r_dywidenda            = db.StringListProperty(indexed=False)
    