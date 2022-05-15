# -*- coding: utf-8 -*-
from google.appengine.ext.webapp import template

#from google.appengine.ext import db
#import datetime
import re
import logging
import os.path
import webapp2
from google.appengine.api import mail

from google.appengine.api import memcache#, taskqueue#, urlfetch
from update import pobierz_notowania, Simple_str, Ncav_str, Ent_str, Generic_str, mom_str

from dashboard import policz_parametry

from webapp2_extras import auth, sessions#, jinja2
from webapp2_extras.auth import InvalidAuthIdError
from webapp2_extras.auth import InvalidPasswordError
#import webapp2_extras
#import webapp2_extras.appengine.auth.models

########## czyszczenie UserToken za pomocą GQL:
## SELECT * FROM UserToken WHERE updated < DATETIME('2015-12-13 13:00:00')
##  AND subject = 'auth'
###########################


def user_required(handler):
	"""
		Decorator that checks if there's a user associated with the current session.
		Will also fail if there's no session present.
	"""
	def check_login(self, *args, **kwargs):
		auth = self.auth
		if not auth.get_user_by_session():
			self.redirect(self.uri_for('login')+'?req_url='+self.request.path, abort=True)
		else:
			return handler(self, *args, **kwargs)

	return check_login

class BaseHandler(webapp2.RequestHandler):
	@webapp2.cached_property
	def auth(self):
		"""Shortcut to access the auth instance as a property."""
		return auth.get_auth()

	@webapp2.cached_property
	def user_info(self):
		"""Shortcut to access a subset of the user attributes that are stored
		in the session.

		The list of attributes to store in the session is specified in
			config['webapp2_extras.auth']['user_attributes'].
		:returns
			A dictionary with most user information
		"""
		return self.auth.get_user_by_session()

	@webapp2.cached_property
	def user(self):
		"""Shortcut to access the current logged in user.

		Unlike user_info, it fetches information from the persistence layer and
		returns an instance of the underlying model.

		:returns
			The instance of the user model associated to the logged in user.
		"""
		u = self.user_info
		return self.user_model.get_by_id(u['user_id']) if u else None

	@webapp2.cached_property
	def user_model(self):
		"""Returns the implementation of the user model.

		It is consistent with config['webapp2_extras.auth']['user_model'], if set.
		"""		
		return self.auth.store.user_model

	@webapp2.cached_property
	def session(self):
			"""Shortcut to access the current session."""
			return self.session_store.get_session(backend="datastore")

	def render_template(self, view_filename, params=None):
		if not params:
			params = {}
		user = self.user_info
		params['user'] = user
		params['host'] = self.request.host
		#params['sec_url'] = 
		path = os.path.join(os.path.dirname(__file__), 'templates', view_filename)
		self.response.out.write(template.render(path, params))

	def display_message(self, message):
		"""Utility function to display a template with a simple message."""
		params = {
			'message': message
		}
		self.render_template('message.html', params)

	# this is needed for webapp2 sessions to work
	def dispatch(self):
			# Get a session store for this request.
			self.session_store = sessions.get_store(request=self.request)

			try:
					# Dispatch the request.
					webapp2.RequestHandler.dispatch(self)
			finally:
					# Save all sessions.
					self.session_store.save_sessions(self.response)

class MainHandler(BaseHandler):
	def get(self):
		self.render_template('home.html')

class SignupHandler(BaseHandler):
		
	def get(self):
		self.render_template('signup.html')
	
	def post(self):
		

		user_name = self.request.get('username')
		name = self.request.get('username')
		last_name = self.request.get('lastname')
		email = self.request.get('email')
		password = self.request.get('password')		
		signup = self.request.get('signup')
	
		error_msg = ''
		
		if len(user_name)==0 or len(email)==0 or len(password)==0: #or len(password2)==0:
			error_msg = u'Należy wypełnić wszystkie pola formularza. '						
		elif len(user_name)<3 or len(user_name)>40 or re.match(r"^[a-zA-Z0-9]{3,40}$", user_name) is None:
			error_msg =u'Nazwa użytkownika musi składać się z min. 3 i maks. 40 liter i/lub cyfr.'
		elif re.match(r"[^@\s]+@[^@\s]+\.[a-zA-Z0-9]+$", email) is None:
			error_msg = u'Podany ciąg znaków nie jest prawidłowym adresem email!'
		elif len(password)<6:
			error_msg = u'Hasło musi składać się z minimum 6 znaków!'
		elif len(email)>254:
			error_msg = u'Adres email nie może być dłuższy niż 100 znaków!'

		if signup ==0 or error_msg != '':
			params = {
			    'username': user_name,
				'email': email,
				'password': password,
				'error_msg': error_msg				 
			}
			self.render_template("signup.html", params)
			return

		### else ####

		unique_properties = ['email_address', 'name']
		user_data = self.user_model.create_user(user_name.lower(),
			unique_properties,
			email_address=email, name=name, last_name = last_name, password_raw=password, verified=False)
		if not user_data[0]: #user_data is a tuple
			error_msg = u'Nie udało się zarejestrować użytkownika "%s", gdyż użytkownik o podanej nazwie lub adresie email \
			 już istnieje. Spróbuj użyć innej nazwy lub adresu email.' % user_name
			params = {
			    'username': user_name,
				'email': email,
				'password': password,
				'error_msg': error_msg				 
			}
			self.render_template("signup.html", params)
			# \
			#	duplicate keys %s' % (user_name, user_data[1]))
			return
		
		user = user_data[1]
		user_id = user.get_id()

		token = self.user_model.create_signup_token(user_id)

		verification_url = self.uri_for('verification', type='v', user_id=user_id,
			signup_token=token, _full=True)

		msg = u"""Witamy,

Dla adresu """+email+u""" oraz nazwy użytkownika """+user_name+u""" została zarejestrowana próba utworzenia
konta w serwisie Akcjegrahama.pl. 

Aby potwierdzić rejestrację kliknij poniższy link:
"""+verification_url+u"""

Dziękujemy za zainteresowanie serwisem i zachęcamy do częstego korzystania."""
#This is a confidential e-mail intended solely for the use of the addressee(s). Unauthorized publication, use, dissemination or disclosure of this message, either in whole or in part is strictly prohibited. If you have received this message in error please send it back to the sender and delete it.
#Treść tej wiadomości zawiera informacje poufne, przeznaczone tylko dla adresata. Udostępnianie, ujawnianie, powielanie, rozpowszechnianie bądź powoływanie się na jakikolwiek jej fragment przez inne osoby jest zabronione. W razie przypadkowego otrzymania tej wiadomości, prosimy o powiadomienie o tym nadawcy oraz trwałe jej usunięcie.
# 
#"""
		mail.send_mail(sender="Akcjegrahama.pl <admin@akcjegrahama.pl>",
		              to='%s' % email,
		              subject="Akcjegrahama.pl - Aktywacja konta",
		              body=msg.encode('utf-8'))


		msg = u'Na podany adres email została wysłana wiadomość z linkiem. \
					Otwórz wiadomość i kliknij w link aby aktywować konto.' # <a href="{url}">{url}</a>

		self.display_message(msg.format(url=verification_url))

class ForgotPasswordHandler(BaseHandler):
	def get(self):
		self._serve_page()

	def post(self):
		
		username = self.request.get('username').lower()
		#self.user_model.get_by_key_name()
		user = self.user_model.get_by_auth_id(username)
	
		if not user:
			logging.info(u'Nie odnaleziono użytkownika o nazwie %s', username)
			self._serve_page(not_found=True)
			return

		user_id = user.get_id()
		
		token = self.user_model.create_signup_token(user_id)
		

		verification_url = self.uri_for('verification', type='p', user_id=user_id,
			signup_token=token, _full=True)
	
		#print user.email_address
	
		msg = u"""
Witamy,

Dla użytkownika: """+username+u"""  została zarejestrowana próba wygenerowania nowego hasła.

Jeżeli chcesz ustanowić nowe hasło, kliknij w poniższy link lub skopiuj
go do paska adresów przeglądarki:
"""+verification_url+u"""

Nastąpi przekierowanie z wykorzystaniem bezpiecznego połączenia na naszą stronę, \
gdzie możliwe będzie podanie nowego hasła.

Kiedy już hasło zostanie zmienione, możliwe będzie zalogowanie się przy użyciu nowego hasła.

Zapraszamy do korzystania z serwisu.
"""
		
		#logging.info(u'Wysylam link do zminay hasla do usera %s, email: %s', username, user.email_address)
		mail.send_mail(sender=u"Akcjegrahama.pl <admin@akcjegrahama.pl>",
		              to='%s' % user.email_address ,
		              subject=u"Hasło do serwisu Akcjegrahama.pl",
		              body=msg.encode('utf-8'))


#		msg = u'Na podany adres email została wysłana wiadomość z linkiem. \
#					Otwórz wiadomość i kliknij w link aby aktywować konto.' # <a href="{url}">{url}</a>

	
		msg = u'Na adres email użytkownika '+username+u' została właśnie wysłana wiadomość z linkiem służącym do ustanowienia nowego hasła. \
			  Otwórz wiadomość i kliknij w link aby utworzyć nowe hasło. \
			  Email zazwyczaj dochodzi prawie natychmiast, ale czasami może to zająć odrobinę dłużej. \
			  Sprawdź skrzynkę i kliknij w podany w treści link.<br>Następnie <a href="/login">zaloguj się</href>.'#<a href="{url}">{url}</a>' # 
#		msg = 'Send an email to user in order to reset their password. \
#					They will be able to do so by visiting <a href="{url}">{url}</a>'

		self.display_message(msg.format(url=verification_url))
	
	def _serve_page(self, not_found=False):
		username = self.request.get('username')
		params = {
			'username': username,
			'not_found': not_found
		}
		self.render_template('forgot.html', params)


class VerificationHandler(BaseHandler):
	def get(self, *args, **kwargs):
		user = None
		user_id = kwargs['user_id'].lower()
		signup_token = kwargs['signup_token']
		verification_type = kwargs['type']

		# it should be something more concise like
		# self.auth.get_user_by_token(user_id, signup_token)
		# unfortunately the auth interface does not (yet) allow to manipulate
		# signup tokens concisely
		user, ts = self.user_model.get_by_auth_token(int(user_id), signup_token,
			'signup')

		if not user:
			logging.info('Nie odnaleziono użytkownika o id "%s" oraz o kluczu rejestracji "%s"',
				user_id, signup_token)
			self.abort(404)
		
		# store user data in the session
		self.auth.set_session(self.auth.store.user_to_dict(user), remember=True)

		if verification_type == 'v':
			# remove signup token, we don't want users to come back with an old link
			self.user_model.delete_signup_token(user.get_id(), signup_token)

			if not user.verified:
				user.verified = True
				user.put()

			self.display_message(u'Adres email został poprawnie zweryfikowany. Konto zostało aktywowane.')
			return
		elif verification_type == 'p':
			# supply user to the page
			params = {
				'user': user,
				'token': signup_token
			}
			self.render_template('resetpassword.html', params)
		else:
			logging.info('ten sposób weryfikacji nie jest obecnie wspierany')
			self.abort(404)

class SetPasswordHandler(BaseHandler):

	@user_required
	def post(self):
		password = self.request.get('password')
		old_token = self.request.get('t')

		if not password or password != self.request.get('confirm_password'):
			self.display_message(u'Hasła się różnią')
			return
		
		if len(password)<6:
			error_msg = u'Hasło musi składać się z minimum 6 znaków!'
			self.display_message(error_msg)
			return

		user = self.user
		user.set_password(password)
		user.put()

		# remove signup token, we don't want users to come back with an old link
		self.user_model.delete_signup_token(user.get_id(), old_token)
		
		self.display_message(u'Hasło zostało pomyślnie zmienione.')

class LoginHandler(BaseHandler):
	def get(self):

#		u= self.auth.store.user_model.get_by_auth_id(u'Rys')
#		#print u
#		if u is not None:
#			u.auth_ids.append("rys")
#			u.put()
		self._serve_page(req_url = self.request.get('req_url'))
		

		
		
		
		

	def post(self):
		username = self.request.get('username').lower()
		password = self.request.get('password')
		req_url = self.request.get('req_url') 
		try:
			u = self.auth.get_user_by_password(username, password, remember=False,
				save_session=True)
			#sprawdzamy czy jest email zostal zweryfikowany
			if not self.user.verified:
				self.auth.unset_session()
				self.display_message(u'Adres email nie został zweryfikowany. Konto <strong>%s</strong> jest nieaktywne. \
				<br>Aktywuj konto poprzez kliknięcie linku zawartego w wiadomości email otrzymanej na podany uprzednio \
				adres lub utwórz nowe konto.' % username)
				return

			#self.redirect(self.uri_for('home'))
			if req_url == None or req_url == '':
				req_url = '/'
			self.redirect(req_url)
			
		except (InvalidAuthIdError, InvalidPasswordError) as e:
			logging.info('Login failed for user %s because of %s', username, type(e))
			#TODO: InvalidPasswordError -> tutaj można zaimplementować licznik nieudanych logowań i
			# opóźniać każdy następny login.
			# ale to jakbym kiedyś miał kłopoty, teraz nie ma sensu (2015-12-15)
			self._serve_page(True, req_url=req_url)

	def _serve_page(self, failed=False, req_url=''):
		username = self.request.get('username')
		params = {
			'username': username,
			'failed': failed,
			'req_url': req_url 
		}
		self.render_template('login.html', params)

class LogoutHandler(BaseHandler):
	def get(self):
		self.auth.unset_session()
		self.redirect(self.uri_for('home'))

class AuthenticatedHandler(BaseHandler):
	@user_required
	def get(self):
		self.render_template('authenticated.html')



#class RootHandler(BaseHandler):
#		def get(self):							
#				self.render('home.html', {																 
#							 'title' : u'Akcje Grahama - wybieraj akcje jak Inteligentny Inwestor giełdowy - online'
#													 })

#class ProfileHandler(BaseHandler):
#		
#		@user_required
#		def get(self):
#				"""Handles GET /profile"""		
#				self.render('profil.html', {
#						'user': self.current_user, 
#						'session': self.auth.get_user_by_session()
#					})

class TrescHandler(BaseHandler):
		def get(self, page):
				self.render_template(
										page+'.html', {
'title' : u'Akcje Grahama - wybieraj akcje jak Inteligentny Inwestor giełdowy - online'
									 })


class StrategieHandler(BaseHandler):
		@user_required
		def get(self,strategia):
								

				if strategia == 'ent' or strategia == 'przedsiebiorczy-inwestor':
						self.render_template('enterprising.html', {
						'title' : u'Akcje Grahama - sprawdzona metoda wyboru akcji dla przedsiębiorczych inwestorów',
						'tabelka': pobierz_notowania(Ent_str)
						})
				elif strategia == 'gen' or strategia == 'akcje-gpw':
						self.render_template('generic.html', {
						 'title' : u'Akcje Grahama - wyszukiwanie akcji z użyciem kryteriów Grahama',
						'tabelka': pobierz_notowania(Generic_str)
						})
				elif strategia == 'ncav':
						self.render_template('ncav.html', {
						'title' : u'Akcje Grahama - C/WK Grahama - wyszukaj tanie akcje',
						'tabelka': pobierz_notowania(Ncav_str)
						})
				elif strategia == 'simple' or strategia == 'najprostsza-metoda-inwestowania':
						self.render_template('simple.html', {
						'title' : u'Akcje Grahama - najprostsza metoda wyboru akcji w okazyjnych cenach',
						'tabelka': pobierz_notowania(Simple_str)
						})
				elif strategia == 'mom':
						self.render_template('momentum.html', {
						'title' : u'Akcje Grahama - Momentum - wyszukaj akcje w ruchu w górę',
						'tabelka': pobierz_notowania(mom_str)
						})

				
class DashboardHandler(BaseHandler):
		def get(self, ticker):
				if ticker is None:
						logging.error("ticker pusty: "+ticker)
						
				ticker = ticker.upper()
				
				# probujemy z memcache pobrac.
				
				response = memcache.get("wykresy_"+ticker) #@UndefinedVariable
				if response is not None:
						self.response.out.write(response)
						return
				else:										
				# teraz policzymy wszystkie parametry jakie przekazujemy do template'a
						parametry, brak_danych = policz_parametry(ticker)	
						
				
						if not memcache.set("wykresy_"+ticker, response): #@UndefinedVariable
								logging.error("Memcache set failed: "+"wykresy_"+ticker)
		
						self.render_template('spolka.html', {'title' : ticker+' sytuacja finansowa - akcjegrahama.pl',											 
											 'ticker': ticker,	
											 'parametry' : parametry,
											 'brak_danych' :brak_danych
											 } )