from django.urls import path
from burgerkarte import views as burger

urlpatterns = [
  path('', burger.home, name = 'home'),

	### APIs ###
	path('api/user/get/<str:uid>/', burger.getUserAPI, name = 'get_user_api'),
  path('api/user/edit/<str:uid>/', burger.changeUserAPI, name = 'change_user_api'),
  path('api/poster/<str:lang>/', burger.viewPosterAPI, name = 'view_poster_api'),
  path('api/book/get/<str:isbn>/', burger.getBookAPI, name = 'get_book_api'),
  path('api/book/borrow/<str:isbn>/', burger.borrowBookAPI, name = 'borrow_book_api'),
  path('api/book/return/<str:isbn>/', burger.returnBookAPI, name = 'return_book_api'),

	### Login + Registrierung ###
	path('login/', burger.login, name='login'),
	path('registrierung/', burger.registrierung, name='registrierung'),
  path('logout/', burger.logout, name='logout'),

	### Admin ###
	path('admin_dashboard/', burger.admin_dashboard, name='admin_dashboard'),
	path('userverwaltung/', burger.user_verwaltung, name='user_verwaltung'),
	path('userverwaltung/bearbeiten/<str:user_id>/', burger.user_bearbeiten, name='user_bearbeiten'),	
	path('userverwaltung/loeschen/<str:user_id>/', burger.user_loeschen, name='user_loeschen'),
  path('libraryverwaltung/', burger.libraryverwaltung, name='libraryverwaltung'),
  path('buch_freigeben/', burger.buch_freigeben, name='buch_freigeben'),
	
	### Service ###
	# path('dashboard/service/library/', burger.service_dashboard_library, name='service_dashboard_library'),
	# path('dashboard/service/transport/', burger.service_dashboard_transport, name='service_dashboard_transport'),
	# path('dashboard/service/payment/', burger.service_dashboard_payment, name='service_dashboard_payment'),

	### user ###
	path('user_dashboard/', burger.user_dashboard, name='user_dashboard'),

	path('bibliothek/', burger.bibliothek, name='bibliothek'),
	path('buch_ausleihen/', burger.buch_ausleihen, name='buch_ausleihen'),
	path('buch_verlaengern/', burger.buch_verlaengern, name='buch_verlaengern'),	#i.p.
  path('gebuehren_begleichen/', burger.gebuehren_begleichen, name='gebuehren_begleichen'),


	path('bezahlkarte/', burger.bezahlkarte, name='bezahlkarte'),
	path('aufladen', burger.aufladen, name='aufladen'),

	path('tickets/', burger.tickets, name='tickets'),
	path("ticket_kaufen/", burger.ticket_kaufen, name="ticket_kaufen"),
  path("ticket_loeschen/", burger.ticket_loeschen, name="ticket_loeschen"),
	#i.P.	path('einzelfahrt_suchen/', burger.einzelfahrt_suchen, name='einzelfahrt_suchen'),


	path('termine/', burger.termine, name='termine'),
	path("termin_absagen/", burger.termin_absagen, name="termin_absagen"),
	path('buchung_abschicken/', burger.buchung_abschicken, name='buchung_abschicken'),

	path('historie/', burger.historie, name='historie'),

]
