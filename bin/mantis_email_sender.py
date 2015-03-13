#!/usr/bin/env python
# -*- coding: utf8 -*-

import warnings
warnings.filterwarnings ( "ignore", "the sets module", DeprecationWarning )

import MySQLdb, MySQLdb.cursors
import os, sys, re, subprocess
import smtplib, time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import mantis_statistics_cfg as cfg

RE_BUG_ID = re.compile ( "Bug id" )


def send_mail ( user_data, attachments ):
	msg = MIMEMultipart ()
	msg [ "Subject" ] = cfg.MAIL_SUBJECT
	msg [ "From" ] = cfg.MAIL_SENDER
	msg [ "To" ] = user_data [ "email" ]

	intro = MIMEText ( cfg.MAIL_INTRO )
	msg.attach ( intro )

	for attach in attachments:
		html = MIMEText ( attach, "html" )
		msg.attach ( html )

	server = smtplib.SMTP ( cfg.MAIL_SMTP_SERVER )
	server.sendmail ( msg [ "From" ], msg [ "To" ], msg.as_string () )
	server.quit ()


def check_user_type ( user_data, include_sections = None ):
	try:
		sect, name = user_data [ "username" ].split ( ".", 1 )

	except ValueError:
		print "Cannot parse the user name: no prefix available."
		return False

	if ( include_sections != None ) and ( sect not in include_sections ):
		print "Processing disabled for user type: %s." % sect
		return False

	try:
		transitions = cfg.SECTION_TRANSITIONS [ sect ]
		user_data [ "transitions" ] = transitions

	except KeyError:
		print "Cannot find the transitions for type: %s." % sect
		return False

	return True


def process_user ( user_data, include_sections = None ):
	print "Processing user: %s" % user_data

	if not check_user_type ( user_data, include_sections ): return

	attachments = []

	for transition in user_data [ "transitions" ]:
		cmd = cfg.MANTIS_STATISTICS_COMMAND % { "user": user_data [ "username" ], "transition": transition }
		p = subprocess.Popen ( cmd, stdout = subprocess.PIPE, shell = True )

		try:
			p.wait ()
			buffer = p.stdout.read ()

		finally:
			p.stdout.close ()

		if RE_BUG_ID.search ( buffer ):
			attachments.append ( buffer )

	if len ( attachments ):
		send_mail ( user_data, attachments )
		print "Message sent."

	else:
		print "No reports."


def main ():
	print "\n\n========== %s ==========\n" % time.strftime( "%a, %d %b %Y %H:%M:%S" )

	db = cur = None

	try:
		db = MySQLdb.connect ( host = cfg.MYSQL_HOST, user = cfg.MYSQL_USER, passwd = cfg.MYSQL_PASSWD, db = cfg.MYSQL_DB, cursorclass = MySQLdb.cursors.DictCursor )
		cur = db.cursor ()

		cur.execute ( "select username, email from mantis_user_table where enabled = 1" )
		record = cur.fetchone ()

		while record:
			username = record [ "username" ]
			if ( "test" in username ) or ( "prova" in username ):
				print "Skipping user: %s" % username

			else:
				process_user ( record, cfg.INCLUDE_SECTIONS )

			record = cur.fetchone ()

	finally:
		if cur: cur.close ()
		if db: db.close ()




if __name__ == '__main__':
	main ()

