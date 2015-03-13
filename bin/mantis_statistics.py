#!/usr/bin/env python
# -*- coding: utf8 -*-

import warnings
warnings.filterwarnings ( "ignore", "the sets module", DeprecationWarning )

import MySQLdb, MySQLdb.cursors, time
from datetime import timedelta, datetime
import sys, optparse, calendar
import mantis_statistics_cfg as cfg


# **********************************************************************
# User
# **********************************************************************

class User ( object ):
	def __init__ ( self, name ):
		self.name = name

	def get_ids ( self, cur ):
		if self.name.find ( ',' ) != -1:
			cond = "username in ( %s )" % ','.join ( "'%s'" % n for n in self.name.split ( ',' ) )
		else:
			cond = "username like '%s%%'" % self.name

		cur.execute ( "select id, username from mantis_user_table where %s" % cond )
		records = cur.fetchall ()
		if len ( records ) == 0:
			raise ValueError ( "No user named %s" % self.name )

		self.ids = [ c [ "id" ] for c in records ]
		self.usernames = [ c [ "username" ] for c in records ]


# **********************************************************************
# History
# **********************************************************************

class History ( object ):
	FIELDS = "user_id, field_name, old_value, new_value, type, date_modified"

	def __init__ ( self, fields ):
		self.__dict__.update ( fields )


	def __str__ ( self ):
		return ', '.join ( "%s = '%s'" % ( k, v ) for k, v in self.__dict__.iteritems () if not callable ( v ) )


# **********************************************************************
# Bug
# **********************************************************************

# {{{ Severity
class Severity ( object ):
	FEATURE = 10
	TRIVIAL = 20
	TEXT = 30
	TWEAK = 40
	MINOR = 50
	MAJOR = 60
	CRASH = 70
	BLOCK = 80
# }}}
# {{{ Priority
class Priority ( object ):
	NONE = 10
	LOW = 20
	NORMAL = 30
	HIGH = 40
	URGENT = 50
	IMMEDIATE = 60

	DESCRIPTIONS = {
		NONE: "None",
		LOW: "Low",
		NORMAL: "Normal",
		HIGH: "High",
		URGENT: "Urgent",
		IMMEDIATE: "Immediate"
	}

	@classmethod
	def descr ( cls, value ):
		return cls.DESCRIPTIONS.get ( value, "" )
# }}}
# {{{ Status
class Status ( object ):
	NEW = 10
	FEEDBACK = 20
	ACKNOWLEDGED = 30
	CONFIRMED = 40
	ASSIGNED = 50
	RESOLVED = 80
	VERIFIED = 83
	VALIDATED = 84
	TO_BE_PUBLISHED = 86
	CLOSED = 90

	DESCRIPTIONS = {
		NEW: "New",
		FEEDBACK: "Feedback",
		ACKNOWLEDGED: "Acknowledged",
		CONFIRMED: "Confirmed",
		ASSIGNED: "Assigned",
		RESOLVED: "Resolved",
		VERIFIED: "Verified",
		VALIDATED: "Validated",
		TO_BE_PUBLISHED: "To be published",
		CLOSED: "Closed"
	}

	@classmethod
	def descr ( cls, value ):
		return cls.DESCRIPTIONS.get ( value, "" )
# }}}

class Bug ( object ):
	FIELDS = "id, priority, severity, date_submitted, due_date, last_updated, handler_id, summary, reporter_id"

	DAYS = {
		Priority.NORMAL: timedelta ( days = 8 ),
		Priority.HIGH:   timedelta ( days = 4 ),
		Priority.URGENT: timedelta ( days = 2 )
	}

	START_STATUS = Status.ASSIGNED
	END_STATUS = Status.RESOLVED


	@classmethod
	def set_transition ( cls, start, end ):
		cls.START_STATUS = getattr ( Status, start.upper () )
		cls.END_STATUS = getattr ( Status, end.upper () )


	@classmethod
	def set_times ( cls, t_normal, t_high, t_urgent ):
		cls.DAYS [ Priority.NORMAL ] = timedelta ( days = int ( t_normal ) )
		cls.DAYS [ Priority.HIGH ] =   timedelta ( days = int ( t_high ) )
		cls.DAYS [ Priority.URGENT ] = timedelta ( days = int ( t_urgent ) )


	def __init__ ( self, fields ):
		self.__dict__.update ( fields )
		self.cur = None
		self.expired = False
		self.start_status_time = None
		self.transition_delta = None
		self.is_valid = False

		self.transition_threshold = self.DAYS.get ( self.priority, self.DAYS [ Priority.NORMAL ] )


	def search_history ( self ):
		self.cur.execute ( "select %s from mantis_bug_history_table where bug_id = %%s order by date_modified" % History.FIELDS, self.id )
		self.history = map ( History, self.cur.fetchall () )

	# {{{ build_stats_old
	def build_stats_old ( self, user ):
		users = user.ids

		self.assigned_time = None
		resolved_time = None

		for h in self.history:
			if ( h.field_name == "handler_id" ) and ( int ( h.new_value ) in users ) and ( not self.assigned_time ):
				self.assigned_time = h.date_modified
			if h.field_name == "status" and int ( h.new_value ) == Status.RESOLVED:
				resolved_time = h.date_modified

		if self.assigned_time:
			if not resolved_time: resolved_time = time.time ()
			# self.resolution_delta = timedelta ( seconds = resolved_time - self.assigned_time )
			self.resolution_delta = self.compute_work_days ( self.assigned_time, resolved_time )
			if self.resolution_delta > self.resolution_threshold:
				self.expired = True
	# }}}

	def build_stats ( self, user ):
		"""
		build_stats ( user )

Controlla la history del bug per determinare se il bug non e' stato completato
in tempo. Per "completato" si intende che il bug e' passato dallo stato
``START_STATUS`` allo stato ``END_STATUS``. Per non essere considerato "scaduto"
il passaggio di stato deve completarsi entro i giorni indicati in
``transition_threshold``, altrimenti l'attributo ``expired`` viene impostato a
True. Durante questo processo vengono impostati anche altri due attributi
dell'oggetto:

- ``start_status_time``: indica il momento in cui il bug ha assunto lo stato
  ``START_STATUS``;
- ``transition_delta``: indica il tempo impiegato per passare allo stato
  ``END_STATUS``.

Il parametro ``user`` e' un'istanza della classe ``User`` e contiene gli id
degli utenti che avevano il compito di modificare lo stato del bug. Se durante
la lavorazione del bug compare almeno uno degli utenti richiesti il bug e'
considerato valido ed e' compreso nelle statistiche. A questo punto se il
passaggio di stato da controllare e' avvenuto per opera di uno degli utenti
richiesti viene misurato il tempo della transizione, altrimenti il baco viene
annoverato tra quelli scaduti perche' gli utenti che l'avevano in carico non si
sono mossi per tempo.

L'algoritmo scorre la history del bug e a seconda del tipo di record intraprende
diverse azioni. Per il cambio di stato:

- se lo stato e' ``START_STATUS`` viene registrata la data;
- se lo stato e' ``END_STATUS`` e segue ``START_STATUS`` e l'utente che ha
  cambiato stato e' ``user`` viene registrata la data;

Se questa sequenza di stati dovesse ripetersi piu' volte viene considerata
solo l'ultima occorrenza. Se lo stato ``END_STATUS`` non fosse presente la data
registrata e' quella del giorno corrente. Se lo stato ``START_STATUS`` non fosse
presente il bug non sarebbe considerato valido e quindi non sarebbe incluso
nelle statistiche.

La faccenda si complica nel caso in cui venga richiesto come ``START_STATUS``
l'atto di assegnazione del bug a un utente. La difficolta' e' legata al fatto
che l'informazione dell'utente assegnatario non risiede in un record di tipo
``status`` ma in un altro record di tipo ``handler_id``. In tal caso non e'
sufficiente che l'utente appaia nella history di lavorazione del bug, ma deve
essere quello a cui il bug e' ancora assegnato. Se il bug e' stato riassegnato
piu' volte viene considerata l'ultima assegnazione e nel caso non riguardi
l'utente richiesto il bug non e' considerato valido. Se gli utenti da
controllare sono piu' di uno e le riassegnazioni contigue riguardano questi
utenti senza interruzione (ovvero senza che in mezzo il bug sia assegnato a
qualcuno fuori dal gruppo) viene considerata la prima data di assegnazione e non
le successive.

"""

		users = user.ids

		self.expired = False
		# se l'utente e' colui che ha inserito il bug allora il bug e' valido
		self.is_valid = ( self.START_STATUS != Status.ASSIGNED ) and ( self.reporter_id in users )

		self.start_status_time = None
		start_time_temp = None
		end_status_time = None

		for h in self.history:
			if h.field_name == "status":
				# se lo stato e' quello iniziale
				if ( self.START_STATUS != Status.ASSIGNED ) and ( int ( h.new_value ) == self.START_STATUS ):
					# registro la data
					start_time_temp = h.date_modified
					end_status_time = None
					#print "Bug: %s, user: %s, status: %s, date: %s" % ( self.id, h.user_id, h.new_value, start_time_temp )

				# se lo stato e' quello finale e l'utente e' uno di quelli richiesti e
				# ho gia' incontrato lo stato iniziale
				if ( int ( h.new_value ) == self.END_STATUS ) and ( int ( h.user_id ) in users ) and start_time_temp:
					# registro la data
					end_status_time = h.date_modified
					# salvo la data dello stato iniziale
					self.start_status_time = start_time_temp
					# mi preparo a incontrare eventualmente un'altra volta lo stato
					# iniziale
					start_time_temp = None
					#print "Bug: %s, user: %s, status: %s, date: %s" % ( self.id, h.user_id, h.new_value, end_status_time )

			elif ( h.field_name == "handler_id" ):
				# se lo stato da controllare e' quello di "bug assegnato"
				if self.START_STATUS == Status.ASSIGNED:
					# se l'assegnatario e' tra gli utenti richiesti
					if int ( h.new_value ) in users:
						# se il bug non era gia' assegnato a uno degli utenti richiesti
						if not self.is_valid:
							# registro la data
							start_time_temp = h.date_modified

						self.is_valid = True
						end_status_time = None
						#print "Bug: %s, user: %s, assigned to: %s, date: %s; valid: %s" % ( self.id, h.user_id, h.new_value, start_time_temp, self.is_valid )

					else:
						# se l'assegnatario non e' tra gli utenti richiesti il bug non e'
						# valido
						self.is_valid = False
						self.start_status_time = start_time_temp = end_status_time = None
						#print "Bug: %s, user: %s, assigned to: %s, date: %s; valid: %s" % ( self.id, h.user_id, h.new_value, start_time_temp, self.is_valid )

				# se lo stato da controllare non e' l'assegnazione del bug
				else:
					# se uno degli utenti richiesti ha assegnato il bug o gli e' stato
					# assegnato, il bug e' valido. In altre parole: l'utente e' stato
					# coinvolto nella lavorazione del bug, quindi posso controllare le
					# transizioni di stato a suo carico
					if ( int ( h.new_value ) in users ) or ( int ( h.user_id ) in users ):
						self.is_valid = True


		# nel caso non l'abbia ancora fatto (per esempio quando non si incontra lo
		# stato finale) salvo la data iniziale
		if start_time_temp: self.start_status_time = start_time_temp
		# se non ho incontrato lo stato finale la data e' quella di oggi
		if not end_status_time: end_status_time = time.time ()

		if ( self.is_valid ) and ( self.start_status_time ):
			#print "Bug: %s, start_status_time: %s, end_status_time: %s" % ( self.id, self.start_status_time, end_status_time )
			# calcolo quanto e' durata la transizione e decido se il bug e' scaduto
			self.transition_delta = self.compute_work_days ( self.start_status_time, end_status_time )
			if self.transition_delta > self.transition_threshold:
				self.expired = True


	def compute_work_days ( self, start_ts, end_ts ):
		"""
		compute_work_days ( start_ts, end_ts ) -> timedelta

		Calcola il numero di giorni lavorativi compresi tra i timestamp "start_ts" e
		"end_ts"; il risultato viene restituito come oggetto timedelta.

		Il calcolo procede nel seguente modo:

		| LMMGVSD | LMMGVSD | LMMGVSD | LMMGVSD | LMMGVSD | LMMGVSD | LMMGVSD |
		    ^                                         ^
		    start_ts                                  end_ts

		     |--|  <- first_interval
         |----------------------------------------|  <- interval

		"interval" contiene il numero di giorni che separano la data di inizio dalla
		data di fine. Per calcolare il numero di giorni lavorativi si deve sottrarre
		da "interval" il numero di finesettimana (moltiplicati per i due giorni che
		li compongono) e il numero di festivita'.
		"first_interval" contiene il numero di giorni che separano "start_ts"
		dalla fine della settimana. Se "interval" e' maggiore di "first_interval"
		significa che vi e' almeno un finesettimana; quindi si sottrae
		"first_interval" dal numero di giorni di "interval" e si imposta a 1 il
		numero di finesettimana. Dividendo per 7 i giorni cosi' rimasti si ottiene il
		numero di finesettimana presenti in "interval" dopo il primo.
		"""

		date_start = datetime.fromtimestamp ( start_ts )
		date_end = datetime.fromtimestamp ( end_ts )

		weekday = date_start.isoweekday ()
		first_interval = 7 - weekday
		interval = date_end - date_start
		if interval.days < first_interval:
			weekends = 0
			workdays = interval.days

		else:
			weekends = 1
			workdays = interval.days - first_interval

		weekends += workdays // 7

		# il "+1" tiene conto del giorno iniziale
		return timedelta ( days = interval.days - 2 * weekends + 1 )



# **********************************************************************
# Project
# **********************************************************************

class Project ( object ):
	FIELDS = "id, name"

	def __init__ ( self, fields ):
		self.__dict__.update ( fields )
		self.cur = None


	def search_bugs ( self, user, full_stats, categories ):
		conds = ""

		if len ( categories ):
			self.cur.execute ( "select id from mantis_category_table where name in ( %s )" % ','.join ( "'%s'" % c for c in categories.split ( ',' ) ) )
			conds += " and category_id in ( %s )" % ','.join ( "'%s'" % record [ 'id' ] for record in self.cur.fetchall () )

		if not full_stats:
			conds += " and ( status >= %s and status < %s )" % ( Bug.START_STATUS, Bug.END_STATUS )

		self.cur.execute ( "select %s from mantis_bug_table where project_id = %%s %s order by priority desc" % ( Bug.FIELDS, conds ), self.id )
		self.bugs = map ( Bug, self.cur.fetchall () )
		for b in self.bugs:
			b.cur = self.cur
			b.search_history ()


	def build_stats ( self, username ):
		for b in self.bugs:
			b.build_stats ( username )


# **********************************************************************
# Functions to dump statistics
# **********************************************************************

# {{{ dump_stats_full_ascii
def dump_stats_full_ascii ( project, counters ):
	NUMBER_WIDTH = 3

	cell_width = NUMBER_WIDTH * 2 + 4
	separator = "+" + ( "-" * cell_width + "+" ) * 12
	# calculations for months padding
	spaces = ( cell_width - len ( calendar.month_abbr [ 1 ] ) ) // 2
	extra_padding = cell_width - len ( calendar.month_abbr [ 1 ] ) - spaces * 2
	spaces = " " * spaces
	extra_padding = " " * extra_padding
	months_row = "|" + "|".join ( "%s%s%s%s" % ( spaces, n, spaces, extra_padding ) for n in calendar.month_abbr [ 1: ] ) + "|"
	# calculations for year padding
	spaces = ( len ( months_row ) - 6 ) // 2
	extra_padding = len ( months_row ) - 6 - spaces * 2
	spaces = " " * spaces
	extra_padding = " " * extra_padding
	year_row = "|%s%%s%s%s|" % ( spaces, spaces, extra_padding )

	print "Report for project: %s" % project.name

	# pretty printing of results
	for year in counters:
		cyear = counters [ year ]
		print separator
		print year_row % year
		print separator
		print months_row
		print separator
		row = "|"
		for month in range ( 1, 13 ):
			cmonth = cyear.get ( month, ( 0, 0 ) )
			row += " %*s, %*s |" % ( NUMBER_WIDTH, cmonth [ 0 ], NUMBER_WIDTH, cmonth [ 1 ] )

		print row
		print separator

	print ""
# }}}
# {{{ dump_stats_full_html_head
def dump_stats_full_html_head ():
	print """<html>
<head>
<style>
div.project {
	font-size: 18px;
	font-weight: bold;
	margin-top: 20px;
}
table.statistics
{
	border: 1px solid black;
	border-collapse: collapse;
}
table.statistics td {
	border: 1px solid black;
	width: 60px;
	text-align: center;
}
table.statistics td.year {
	font-weight: bold;
	background-color: lightblue;
}
table.statistics td.month {
	font-style: italic;
	background-color: lightgreen;
} 
table.statistics td.warn {
	background-color: pink;
}
table.statistics td.alert {
	background-color: red;
}
</style>
</head>
<body>
"""
# }}}
# {{{ dump_stats_full_html_tail
def dump_stats_full_html_tail ():
	print """</body>
</html>
"""
# }}}
# {{{ dump_stats_full_html
def dump_stats_full_html ( project, counters ):
	print '<div class="project">%s</div>' % project.name

	months_row = '<tr class="month">' + ''.join ( '<td class="month">%s</td>' % n for n in calendar.month_abbr [ 1: ] ) + '</tr>'

	for year in counters:
		cyear = counters [ year ]
		print '<table class="statistics">'
		print '<tr class="year"><td class="year" colspan="12">%s</td></tr>' % year
		print months_row
		print '<tr class="counters">'
		for month in range ( 1, 13 ):
			css_class = ""
			cmonth = cyear.get ( month, ( 0, 0 ) )
			if cmonth [ 0 ] > 0:
				css_class = "warn"
				if float ( cmonth [ 0 ] ) / cmonth [ 1 ] > 0.5:
					css_class = "alert"

			print '<td class="counters %s">%s, %s</td>' % ( css_class, cmonth [ 0 ], cmonth [ 1 ] )

		print '</tr>'
		print '</table>'
# }}}
# {{{ dump_stats_full_csv
def dump_stats_full_csv ( project, counters ):
	for year in counters:
		cyear = counters [ year ]

		row = '"%s";"%s"' %  ( project.name, year )

		for month in range ( 1, 13 ):
			cmonth = cyear.get ( month, ( 0, 0 ) )
			row += ';"%s";"%s"' % ( cmonth [ 0 ], cmonth [ 1 ] )

		print row
# }}}
# {{{ dump_stats_full
def dump_stats_full ( user, projects, format ):
	"""
	dump_stats_full ( user, projects, format )

	Scorre i progetti e i bug e crea un dizionario con i conteggi dei bug divisi
	per anno e per mese. Il dizionario generato e' del tipo:

	{
	  '2012': {
	    '1': ( 2, 3 ),
	    '2': ( 0, 0 ),
	    '3': ( 27, 81 ),
      ...
    },
    '2013': {
      '1': ( 1, 3 ),
      ...
    },
    ...
  }

	Il conteggio per mese e' una coppia di interi di cui il primo rappresenta il
	numero di bug scaduti e il secondo il numero totale di bug. La data del bug
	che viene utilizzata per collocarlo temporalmente e' la data dello stato
	iniziale da controllare.

	"""

	if format == "htmlstandalone":
		dump_stats_full_html_head ()

	if format.startswith ( "html" ):
		print '<div class="users">Report for users: %s. Transition: %s -&gt; %s</div>' % (
			', '.join ( user.usernames ),
			Status.descr ( Bug.START_STATUS ),
			Status.descr ( Bug.END_STATUS ) )

	elif format == "csv":
		header = '"Project";"Year";'
		header += ';'.join ( '"%s Exp";"%s Tot"' % ( n, n ) for n in calendar.month_abbr [ 1: ] )
		print header

	for p in projects:
		if len ( p.bugs ) == 0: continue

		# count total bugs and expired bugs by year and month
		counters = {}

		for b in p.bugs:
			if b.is_valid:
				try:
					assigned_date = datetime.fromtimestamp ( b.start_status_time )
					e, t = counters.setdefault ( assigned_date.year, {} ).setdefault ( assigned_date.month, ( 0, 0 ) )
					t += 1
	
					# DEBUG
					#print "Bug id: %s" % b.id
	
					if b.expired: e += 1
					counters [ assigned_date.year ] [ assigned_date.month ] = ( e, t )
	
				except TypeError:
					#print "*** %s" % b.id
					pass

		if len ( counters ) == 0: continue

		# print the results
		if format == "ascii":
			dump_stats_full_ascii ( p, counters )

		elif format.startswith ( "html" ):
			dump_stats_full_html ( p, counters )

		elif format == "csv":
			dump_stats_full_csv ( p, counters )
	#end for

	if format == "htmlstandalone":
		dump_stats_full_html_tail ()
# }}}
# {{{ dump_stats_expired_html_head
def dump_stats_expired_html_head ():
	print """<html>
<head>
<style>
div.project {
	font-size: 18px;
	font-weight: bold;
	margin-top: 20px;
}
table.expired
{
	border: 1px solid black;
	border-collapse: collapse;
}
table.expired td {
	border: 1px solid black;
	text-align: left;
}
table.expired td.title {
	font-style: italic;
	background-color: lightgreen;
} 
table.expired td.warn {
	background-color: pink;
}
table.expired td.alert {
	background-color: red;
}
</style>
</head>
<body>
"""
# }}}
# {{{ dump_stats_expired
def dump_stats_expired ( user, projects, format, add_links ):
	"""
	dump_stats_expired ( user, projects, format, add_links )

	Scorre i progetti e i bug e stampa in output soltanto i bug che hanno
	l'attributo ``expired`` a True.
	"""

	if format == "htmlstandalone":
		dump_stats_expired_html_head ()

	if format.startswith ( "html" ):
		print '<div class="users">Report for users: %s. Transition: %s -&gt; %s</div>' % (
			', '.join ( user.usernames ),
			Status.descr ( Bug.START_STATUS ),
			Status.descr ( Bug.END_STATUS ) )

	elif format == "csv":
		print '"Project";"Bug id";"Summary";"Priority";"Elapsed"'

	for p in projects:
		expired = []

		for b in p.bugs:
			if b.is_valid and b.expired:
				summary = b.summary.decode( 'latin1' ).encode ( 'ascii', 'xmlcharrefreplace' )

				if format in ( "html", "htmlstandalone" ):
					bug_id = b.id
					if add_links and len ( add_links ):
						domain = ""
						if format == "htmlstandalone": domain = add_links if add_links.endswith ( "/" ) else add_links + "/"
						bug_id = '<a href="%sview.php?id=%s" target="_new">%s</a>' % ( domain, bug_id, bug_id )

					row = "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % ( bug_id, summary, Priority.descr ( b.priority ), b.transition_delta.days )
				elif format == "csv":
					row = '"%s";"%s";"%s";"%s";"%s"' % ( p.name, b.id, b.summary.replace ( '"', "'" ), Priority.descr ( b.priority ), b.transition_delta.days )
				else:
					row = "Bug id: %s; summary: %s; priority: %s; time elapsed: %s" % ( b.id, b.summary, Priority.descr ( b.priority ), b.transition_delta.days )

				expired.append ( row )

		if len ( expired ):
			if format.startswith ( "html" ):
				print '<div class="project">%s</div>' % p.name
				print '<table class="expired">'
				print '<tr class="title"><td class="title">Bug id</td><td class="title">Summary</td><td class="title">Priority</td><td class="title">Elapsed</td></tr>'
				print '\n'.join ( expired )
				print '</table>'

			elif format == "csv":
				print '\n'.join ( expired )

			else:
				print "Report for project: %s" % p.name
				print '\n'.join ( expired )
				print ""

	if format == "htmlstandalone":
		dump_stats_full_html_tail ()
# }}}
# {{{ dump_stats
def dump_stats ( user, projects, full_stats, format, add_links ):
	if full_stats: return dump_stats_full ( user, projects, format )
	dump_stats_expired ( user, projects, format, add_links )
# }}}


# **********************************************************************
# Other functions
# **********************************************************************

def get_projects ( cur ):
	cur.execute ( "select %s from mantis_project_table where enabled = 1 order by name" % Project.FIELDS )
	return map ( Project, cur.fetchall () )

def parse_args ():
	paramparse = optparse.OptionParser ( description = "Generate Mantis statistics" )
	paramparse.add_option ( "-u", "--user", type = "string", action = "store", help = "User name, or prefix of user names, or comma separated list (no spaces allowed)" )
	paramparse.add_option ( "-s", "--stats", action = "store_true", default = False, help = "Display full statistics. Without this flag only expired bugs are displayed" )
	paramparse.add_option ( "-f", "--format", type = "string", action = "store", default = "ascii", help = "Output format: ascii (default), html, htmlstandalone, csv" )
	paramparse.add_option ( "-t", "--transition", type = "string", action = "store", help = "Status transition to be checked; default: assigned,resolved" )
	paramparse.add_option ( "-d", "--days", type = "string", action = "store", help = "Time (in days) after which a bug expires; default: 2,4,8" )
	paramparse.add_option ( "-l", "--link", type = "string", action = "store", help = "Add mantis link to bug id (only for html expired bug report). Put Mantis domain in the value, e.g.: http://eemantis.wki.it" )
	paramparse.add_option ( "-c", "--categories", type = "string", action = "store", help = "Include only the specified categories (comma separated list)." )

	opts, args = paramparse.parse_args ()

	if not opts.user:
		print "Missing user name (-u)"
		sys.exit ( 1 )

	if opts.format not in ( "ascii", "html", "htmlstandalone", "csv" ):
		opts.format = "ascii"

	if not opts.link: opts.link = ""
	if not opts.categories: opts.categories = ""

	return opts, args


def main ():
	opts, args = parse_args ()

	db = cur = None

	try:
		db = MySQLdb.connect ( host = cfg.MYSQL_HOST, user = cfg.MYSQL_USER, passwd = cfg.MYSQL_PASSWD, db = cfg.MYSQL_DB, cursorclass = MySQLdb.cursors.DictCursor )
		cur = db.cursor ()

		user = User ( opts.user )

		try:
			user.get_ids ( cur )

		except ValueError:
			if opts.format.startswith ( "html" ):
				print '<div class="error">No user named: %s</div>' % user.name
			return

		if opts.transition: Bug.set_transition ( *opts.transition.split ( ',' ) )
		if opts.days: Bug.set_times ( *opts.days.split ( ',' ) )

		projects = get_projects ( cur )
		for p in projects:
			p.cur = cur
			p.search_bugs ( user, opts.stats, opts.categories )
			p.build_stats ( user )

		dump_stats ( user, projects, opts.stats, opts.format, opts.link )

	finally:
		if cur: cur.close ()
		if db: db.close ()




if __name__ == '__main__':
	main ()

