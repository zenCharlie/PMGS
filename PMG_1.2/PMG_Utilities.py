import logging
import os
import sys
import time
import datetime
import smtplib
import traceback
from PMG_Exceptions import PMGUtilitiesErrorMessage

class DateTimeSplit:
	def __init__(self, in_date, in_time):
		self.year, self.month, self.day = in_date.split('-')
		self.hour, self.mintue, self.second = in_time.split(':')
		if self.hour == '24': self.hour = 0
		if sys.platform == 'win32':
			if int(self.year) < 1970:
				self.year = 1970
				self.month = 1
				self.day = 1
				self.hour = 0
				self.mintue = 0
				self.second = 0

def make_directory(parent_dir, directory):
	path = os.path.join(parent_dir, directory) 
	try: 
		os.makedirs(path, exist_ok = True) 
	except OSError as error: 
		raise PMGUtilitiesErrorMessage(error, traceback.format_exc())

def get_current_time(current_time=None):
	if current_time != None:
		return time.strftime("%a %b %d %H:%M:%S %Y", time.localtime(current_time))
	else:
		return time.strftime("%a %b %d %H:%M:%S %Y", time.localtime(time.time()))

def date_time_string(in_date, in_time):
	date_time = DateTimeSplit(in_date, in_time)
	return datetime.datetime.combine(datetime.date(int(date_time.year), int(date_time.month), int(date_time.day)),\
		datetime.time(int(date_time.hour), int(date_time.mintue), int(date_time.second)))

def get_total_time(seconds, decimal_places=6):
	hrs = int(seconds / 3600)
	mins = int((seconds - (hrs*3600))/ 60)
	secs = seconds - (mins*60) - (hrs*3600)
	if decimal_places == 0:
		int_places = 2
	else:
		int_places = 3
	return '%02d:%02d:%0*.*f' % (hrs, mins, int_places+decimal_places, decimal_places, secs)

def time_to_seconds(in_date, in_time):
	'''
	Converts the character time of d (date) and t(time), into a
	float value of seconds past the epoch.
	'''
	try:
		date_time = DateTimeSplit(in_date, in_time)
		return time.mktime((int(date_time.year), int(date_time.month), int(date_time.day), \
			int(date_time.hour), int(date_time.mintue), int(date_time.second), 0, 0, -1))
	except Exception as e:
		error_str = str(e)+' '+'Time conversion error in time_to_seconds().'
		raise PMGUtilitiesErrorMessage(error_str, traceback.format_exc())
	

def case_insentive_sort_new(e):
	return e.upper()
	
def case_insentive_sort(a, b):
	"""caseInsensitiveSort: Determine case sensitivity:**NOT USED"""
	try:
		if a.upper() > b.upper():
			return 1
		elif b.upper() > a.upper():
			return -1
		else:
			return 0
	except Exception as e:
		error_str = str(e)+' '+'in case_insentive_sort()'
		raise PMGUtilitiesErrorMessage(error_str, traceback.format_exc())
	
	



	


