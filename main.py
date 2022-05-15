# -*- coding: utf-8 -*-
import os
import logging
import webapp2
import handlers

from webapp2 import WSGIApplication, Route


# webapp2 config
app_config = {
  'webapp2_extras.sessions': {
    'cookie_name': '_akcjegrahama_ses',
    'secret_key': "074oel61o70pz54d3n88b7dl62v37bxp817g3b1ye329m1n25b"
  },
  'webapp2_extras.auth': {
    'user_model': 'models.User',
    'user_attributes': ['subscription_end','name']#,'aktywny_do','zarejestrowany', 'zarejestrowany_od']
  }
}


routes = [ 
          Route('/',            handlers.MainHandler, name='home'),
          Route('/<strategia:(ent|gen|simple|ncav|mom|najprostsza-metoda-inwestowania|przedsiebiorczy-inwestor|akcje-gpw)>',
                            handlers.StrategieHandler),
          Route('/t/<page>',            handlers.TrescHandler, name="tresc"),
          Route(r'/s/<ticker>',   handlers.DashboardHandler, name="spolka"),
 
        #webapp2.Route('/', MainHandler, name='home'),
        webapp2.Route('/signup', handlers.SignupHandler),
        webapp2.Route('/<type:v|p>/<user_id:\d+>-<signup_token:.+>', handler=handlers.VerificationHandler, name='verification'),
        webapp2.Route('/password', handlers.SetPasswordHandler),
        webapp2.Route('/login', handlers.LoginHandler, name='login'),
        webapp2.Route('/logout', handlers.LogoutHandler, name='logout'),
        webapp2.Route('/forgot', handlers.ForgotPasswordHandler, name='forgot'),
        webapp2.Route('/authenticated', handlers.AuthenticatedHandler, name='authenticated')]

debug = os.environ['SERVER_SOFTWARE'].startswith('Dev') or os.environ['HTTP_HOST'].endswith('appspot.com')
        
app = WSGIApplication(routes, config= app_config, debug=debug)

def handle_404(request, response, exception):
    logging.exception(exception)
#    template_values = {
#           'title' : 'Akcje Grahama - wyszukiwanie akcji z użyciem kryteriów Grahama',
#           'base_html': 'base.html'
#                       }
#    path = os.path.join(os.path.dirname(__file__), './templates/404.html')
    response.set_status(404)

def handle_500(request, response, exception):
    logging.exception(exception)
    response.write('Serwis jest chwilowo niedostępny, spróbuj za jakiś czas lub skontatkuj sie z administratorem serwisu: admin@akcjegrahama.pl')
    response.set_status(500)

class Webapp2HandlerAdapter(webapp2.BaseHandlerAdapter):
    def __call__(self, request, response, exception):
        request.route_args = {}
        request.route_args['exception'] = exception
        handler = self.handler(request, response)
        #handler.dispatch()
        return handler.get()

class Handle404(handlers.BaseHandler):
    def get(self):
        self.render('404.html',{'title' : 'Akcje Grahama - błąd 404 - nie znaleziono strony'}) ##exception=self.request.route_args['exception']


#app.error_handlers[404] = Webapp2HandlerAdapter(Handle404)
app.error_handlers[500] = handle_500
     
